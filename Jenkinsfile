pipeline {
    agent any
    environment {
        PROJECT_NAME = 'KinoTavr' [cite: 1]
        DOCKER_COMPOSE_FILE = 'docker-compose.yml' [cite: 1]

        // Секреты (извлекаются из Jenkins Credentials)
        OPENAI_API_KEY = credentials('openai-api-key') [cite: 1]
        TELEGRAM_BOT_TOKEN = credentials('telegram-bot-token') [cite: 1]
        KP_API_KEY = credentials('kp-api-key') [cite: 1]
        WEBAPP_URL = credentials('webapp-url') [cite: 1]
        DB_PASSWORD = credentials('db-password') [cite: 1]
    }
  
    options {
        buildDiscarder(logRotator(numToKeepStr: '10')) [cite: 2]
        disableConcurrentBuilds() [cite: 2]
        timeout(time: 30, unit: 'MINUTES') [cite: 2]
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code from Git...'
                // Автоматически клонирует ветку, которая триггернула пайплайн
                checkout scm [cite: 3]
            }
        }

        stage('Validate Structure') {
            steps {
                echo 'Validating project structure...'
                sh '''
                    test -f docker-compose.yml || (echo "docker-compose.yml not found" && exit 1) [cite: 4, 5]
                    test -f Dockerfile.ai || (echo "Dockerfile.ai not found" && exit 1) [cite: 5, 6]
                    test -f tgBot/Dockerfile || (echo "tgBot/Dockerfile not found" && exit 1) [cite: 6, 7]
                    test -f db_kinotavr/backend/Dockerfile || (echo "backend Dockerfile not found" && exit 1) [cite: 7, 8]
                    test -f db_kinotavr/parser/Dockerfile || (echo "parser Dockerfile not found" && exit 1) [cite: 8, 9]
                    echo "All required files are present." [cite: 9]
                '''
            }
        }

        stage('Test & Validate DB') {
            steps {
                echo 'Running integration tests for Database...'
                sh '''
                    # Запускаем только контейнер базы данных для проверки
                    docker compose up -d db [cite: 11]

                    # Ожидаем готовности PostgreSQL (до 30 попыток)
                    for i in {1..30}; do [cite: 11, 12]
                        if docker compose exec -T db pg_isready -U user_admin -d movies_db; then [cite: 12, 13]
                            echo "Database is ready!" [cite: 13]
                            break [cite: 14]
                        fi
                        echo "Waiting for database response... ($i/30)" [cite: 14]
                        sleep 2 [cite: 14]
                    done

                    # Проверяем структуру (вывод списка таблиц)
                    docker compose exec -T db psql -U user_admin -d movies_db -c "\\dt" [cite: 15]

                    # Останавливаем тестовую БД и очищаем тома
                    docker compose down -v [cite: 15, 16]
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
                    # За счет проброса /var/run/docker.sock команды управляют хостом [cite: 17, 18]
                    echo "Stopping old microservices if they are running..."
                    docker compose down || true [cite: 18, 19]

                    echo "Building new images without cache..."
                    docker compose build --no-cache [cite: 19]

                    echo "Launching all services in detached mode..."
                    docker compose up -d [cite: 19]
                '''
            }
        }

        stage('Health Check') {
            steps {
                echo 'Verifying services health...'
                sh '''
                    echo "Giving services 10 seconds to initialize..." [cite: 21]
                    sleep 10 [cite: 21]

                    # Проверяем статус контейнеров через docker compose
                    docker compose ps [cite: 21]

                    # Проверка AI бэкенда
                    for i in {1..30}; do [cite: 22, 23]
                        if curl -f http://localhost:8001/ping > /dev/null 2>&1; then [cite: 23, 24]
                            echo "[✓] AI Backend is healthy." [cite: 24]
                            break [cite: 25]
                        fi
                        if [ $i -eq 30 ]; then [cite: 25, 26]
                            echo "[🔴] AI Backend check failed!" && exit 1; [cite: 26]
                        fi
                        sleep 2 [cite: 26]
                    done

                    # Проверка DB бэкенда
                    for i in {1..30}; do [cite: 27, 28]
                        if curl -f http://localhost:8000/api/v1/colors > /dev/null 2>&1; then [cite: 28, 29]
                            echo "[✓] DB Backend is healthy." [cite: 29]
                            break [cite: 30]
                        fi
                        if [ $i -eq 30 ]; then [cite: 30, 31]
                            echo "[🔴] DB Backend check failed!" && exit 1; [cite: 31]
                        fi
                        sleep 2 [cite: 31]
                    done
                '''
            }
        }

        stage('Smoke Tests') {
            steps { [cite: 33]
                echo 'Running smoke tests...'
                sh '''
                    curl -s http://localhost:8000/api/v1/colors | grep -q 'deep_blue' || (echo "Smoke test failed on DB API" && exit 1) [cite: 33, 34]
                    curl -s http://localhost:8001/ping | grep -q 'alive' || (echo "Smoke test failed on AI API" && exit 1) [cite: 34, 35]
                    echo 'All smoke tests passed successfully!' [cite: 35]
                '''
            }
        }
    }

    post {
        success {
            echo 'Deployment finished successfully!' [cite: 37]
        }
        failure {
            echo 'Deployment failed!' [cite: 38]
        }
        always {
            echo 'Cleaning up temporal build artifacts...' [cite: 38]
            // Удаляем файл с секретами из воркспейса в целях безопасности
            sh 'rm -f .env'
        }
    }
}