pipeline {
    agent any
    environment {
        PROJECT_NAME = 'KinoTavr'
        DOCKER_COMPOSE_FILE = 'docker-compose.yml'

        // Секреты (извлекаются из Jenkins Credentials)
        OPENAI_API_KEY = credentials('openai-api-key')
        TELEGRAM_BOT_TOKEN = credentials('telegram-bot-token')
        KP_API_KEY = credentials('kp-api-key')
        WEBAPP_URL = credentials('webapp-url')
        DB_PASSWORD = credentials('db-password')
        
        // Путь к проекту на хосте (Jenkins workspace будет смонтирован)
        HOST_WORKSPACE = "${WORKSPACE}"
    }
  
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code from Git...'
                checkout scm
            }
        }

        stage('Validate Structure') {
            steps {
                echo 'Validating project structure...'
                sh '''
                    test -f docker-compose.yml || (echo "docker-compose.yml not found" && exit 1)
                    test -f Dockerfile.ai || (echo "Dockerfile.ai not found" && exit 1)
                    test -f tgBot/Dockerfile || (echo "tgBot/Dockerfile not found" && exit 1)
                    test -f db_kinotavr/backend/Dockerfile || (echo "backend Dockerfile not found" && exit 1)
                    test -f db_kinotavr/parser/Dockerfile || (echo "parser Dockerfile not found" && exit 1)
                    echo "All required files are present."
                '''
            }
        }

        stage('Prepare Environment') {
            steps {
                echo 'Creating .env file on host...'
                sh '''
                    # Создаем .env файл в текущем воркспейсе
                    cat > ${WORKSPACE}/.env << EOF
OPENAI_API_KEY=${OPENAI_API_KEY}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
KP_API_KEY=${KP_API_KEY}
WEBAPP_URL=${WEBAPP_URL}
DB_HOST=db
DB_NAME=movies_db
DB_USER=user_admin
DB_PASSWORD=${DB_PASSWORD}
DB_PORT=5432
EOF
                    chmod 600 ${WORKSPACE}/.env
                '''
            }
        }

        stage('Test & Validate DB') {
            steps {
                echo 'Running integration tests for Database...'
                sh '''
                    # Переходим в директорию проекта и запускаем через хостовый Docker
                    cd ${WORKSPACE}
                    
                    # Запускаем контейнер базы данных для проверки
                    docker compose up -d db

                    # Ожидаем готовности PostgreSQL (до 30 попыток)
                    for i in {1..30}; do
                        if docker compose exec -T db pg_isready -U user_admin -d movies_db; then
                            echo "Database is ready!"
                            break
                        fi
                        echo "Waiting for database response... ($i/30)"
                        sleep 2
                    done

                    # Проверяем структуру (вывод списка таблиц)
                    docker compose exec -T db psql -U user_admin -d movies_db -c "\\dt"

                    # Останавливаем тестовую БД и очищаем тома
                    docker compose down -v
                '''
            }
        }

        stage('Cleanup Old Deployment') {
            steps {
                echo 'Stopping and removing old containers...'
                sh '''
                    cd ${WORKSPACE}
                    
                    # Останавливаем старые контейнеры (если есть)
                    docker compose down --remove-orphans || true
                    
                    # Удаляем старые образы приложения (опционально)
                    # docker images | grep "${PROJECT_NAME}" | awk '{print $3}' | xargs -r docker rmi -f || true
                '''
            }
        }

        stage('Build Images') {
            steps {
                echo 'Building Docker images on host machine...'
                sh '''
                    cd ${WORKSPACE}
                    
                    # Собираем образы без кэша
                    docker compose build --no-cache
                    
                    # Выводим список собранных образов
                    docker compose images
                '''
            }
        }

        stage('Deploy Services') {
            steps {
                echo 'Deploying services on host machine...'
                sh '''
                    cd ${WORKSPACE}
                    
                    # Запускаем все сервисы в detached режиме
                    docker compose up -d
                    
                    # Показываем статус контейнеров
                    docker compose ps
                '''
            }
        }

        stage('Health Check') {
            steps {
                echo 'Verifying services health...'
                sh '''
                    cd ${WORKSPACE}
                    
                    echo "Giving services 10 seconds to initialize..."
                    sleep 10

                    # Проверяем статус контейнеров через docker compose
                    docker compose ps

                    # Проверка AI бэкенда
                    echo "Checking AI Backend..."
                    for i in {1..30}; do
                        if docker compose exec -T ai-backend curl -f http://localhost:8001/ping > /dev/null 2>&1; then
                            echo "[✓] AI Backend is healthy."
                            break
                        fi
                        if [ $i -eq 30 ]; then
                            echo "[🔴] AI Backend check failed!"
                            docker compose logs ai-backend
                            exit 1
                        fi
                        sleep 2
                    done

                    # Проверка DB бэкенда
                    echo "Checking DB Backend..."
                    for i in {1..30}; do
                        if docker compose exec -T backend curl -f http://localhost:8000/api/v1/colors > /dev/null 2>&1; then
                            echo "[✓] DB Backend is healthy."
                            break
                        fi
                        if [ $i -eq 30 ]; then
                            echo "[🔴] DB Backend check failed!"
                            docker compose logs backend
                            exit 1
                        fi
                        sleep 2
                    done
                '''
            }
        }

        stage('Smoke Tests') {
            steps {
                echo 'Running smoke tests...'
                sh '''
                    cd ${WORKSPACE}
                    
                    # Получаем ID контейнеров для проверки
                    AI_CONTAINER=$(docker compose ps -q ai-backend)
                    DB_CONTAINER=$(docker compose ps -q backend)
                    
                    # Smoke test для DB API
                    docker exec $DB_CONTAINER curl -s http://localhost:8000/api/v1/colors | grep -q 'deep_blue' || \
                        (echo "Smoke test failed on DB API" && exit 1)
                    
                    # Smoke test для AI API
                    docker exec $AI_CONTAINER curl -s http://localhost:8001/ping | grep -q 'alive' || \
                        (echo "Smoke test failed on AI API" && exit 1)
                    
                    echo 'All smoke tests passed successfully!'
                '''
            }
        }

        stage('Display Service Info') {
            steps {
                echo 'Deployment summary...'
                sh '''
                    cd ${WORKSPACE}
                    
                    echo "=== Running Containers ==="
                    docker compose ps
                    
                    echo ""
                    echo "=== Container Resource Usage ==="
                    docker stats --no-stream $(docker compose ps -q)
                    
                    echo ""
                    echo "=== Service Endpoints ==="
                    echo "AI Backend: http://$(hostname -I | awk '{print $1}'):8001"
                    echo "DB Backend: http://$(hostname -I | awk '{print $1}'):8000"
                '''
            }
        }
    }

    post {
        success {
            echo '✅ Deployment finished successfully!'
            sh '''
                cd ${WORKSPACE}
                echo "Active services:"
                docker compose ps --format "table {{.Name}}\\t{{.Status}}\\t{{.Ports}}"
            '''
        }
        failure {
            echo '❌ Deployment failed!'
            sh '''
                cd ${WORKSPACE}
                echo "=== Service Logs ==="
                docker compose logs --tail=50
                
                echo ""
                echo "=== Cleaning up failed deployment ==="
                docker compose down || true
            '''
        }
        always {
            echo 'Cleaning up temporal build artifacts...'
            sh '''
                # Удаляем секреты из воркспейса
                rm -f ${WORKSPACE}/.env
            '''
        }
    }
}