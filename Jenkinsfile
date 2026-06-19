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
		        cleanWs()
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

        stage('Test & Validate DB') {
            steps {
                echo 'Running integration tests for Database...'
                sh '''
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

        stage('Deploy via Docker Compose') {
            steps {
                echo 'Deploying project directly to the host server via socket...'
                sh '''
                    # Создаем .env файл в текущем воркспейсе
                    cat > .env << EOF
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
                    echo "Stopping old microservices if they are running..."
                    docker compose down || true

                    echo "Building new images without cache..."
                    docker compose build --no-cache

                    echo "Launching all services in detached mode..."
                    docker compose up -d
                '''
            }
        }

        stage('Health Check') {
            steps {
                echo 'Verifying services health...'
                sh '''
                    echo "Giving services 10 seconds to initialize..."
                    sleep 10

                    # Проверяем статус контейнеров через docker compose
                    docker compose ps

                    # Проверка AI бэкенда
                    for i in {1..30}; do
                        if curl -f http://localhost:8001/ping > /dev/null 2>&1; then
                            echo "[✓] AI Backend is healthy."
                            break
                        fi
                        if [ $i -eq 30 ]; then
                            echo "[🔴] AI Backend check failed!" && exit 1;
                        fi
                        sleep 2
                    done

                    # Проверка DB бэкенда
                    for i in {1..30}; do
                        if curl -f http://localhost:8000/api/v1/colors > /dev/null 2>&1; then
                            echo "[✓] DB Backend is healthy."
                            break
                        fi
                        if [ $i -eq 30 ]; then
                            echo "[🔴] DB Backend check failed!" && exit 1;
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
                    curl -s http://localhost:8000/api/v1/colors | grep -q 'deep_blue' || (echo "Smoke test failed on DB API" && exit 1)
                    curl -s http://localhost:8001/ping | grep -q 'alive' || (echo "Smoke test failed on AI API" && exit 1)
                    echo 'All smoke tests passed successfully!'
                '''
            }
        }
    }

    post {
        success {
            echo 'Deployment finished successfully!'
        }
        failure {
            echo 'Deployment failed!'
        }
        always {
            echo 'Cleaning up temporal build artifacts...'
            // Гарантированно удаляем секреты из воркспейса по окончании сборки
            sh 'rm -f .env'
        }
    }
}
