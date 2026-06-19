pipeline {
    agent any

    environment {
        // Настройки проекта
        PROJECT_NAME = 'kinotavr'
        DOCKER_COMPOSE_FILE = 'docker-compose.yml'

        // Удаленный сервер
        REMOTE_USER = credentials('ubuntu-server-user')
        REMOTE_HOST = credentials('ubuntu-server-host')
        REMOTE_PATH = '/opt/kinotavr'

        // Секреты (настроить в Jenkins Credentials)
        OPENAI_API_KEY = credentials('openai-api-key')
        TELEGRAM_BOT_TOKEN = credentials('telegram-bot-token')
        KP_API_KEY = credentials('kp-api-key')
        WEBAPP_URL = credentials('webapp-url')

        // Database credentials
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
                echo 'Checking out code...'
                checkout scm
                sh 'git submodule update --init --recursive || true'
            }
        }

        stage('Validate') {
            steps {
                echo 'Validating project structure...'
                sh '''
                    # Проверка наличия необходимых файлов
                    test -f docker-compose.yml || (echo "docker-compose.yml not found" && exit 1)
                    test -f Dockerfile.ai || (echo "Dockerfile.ai not found" && exit 1)
                    test -f tgBot/Dockerfile || (echo "tgBot/Dockerfile not found" && exit 1)
                    test -f db_kinotavr/backend/Dockerfile || (echo "backend Dockerfile not found" && exit 1)
                    test -f db_kinotavr/parser/Dockerfile || (echo "parser Dockerfile not found" && exit 1)

                    echo "All required files present"
                '''
            }
        }

        stage('Build Docker Images Locally') {
            steps {
                echo 'Building Docker images locally for validation...'
                sh '''
                    docker-compose build --no-cache
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Running tests...'
                sh '''
                    # Запуск контейнеров для тестирования
                    docker-compose up -d db

                    # Ждем готовности БД
                    for i in {1..30}; do
                        if docker-compose exec -T db pg_isready -U user_admin -d movies_db; then
                            echo "Database is ready"
                            break
                        fi
                        echo "Waiting for database... ($i/30)"
                        sleep 2
                    done

                    # Проверка схемы БД
                    docker-compose exec -T db psql -U user_admin -d movies_db -c "\\dt"

                    # Остановка тестовых контейнеров
                    docker-compose down -v
                '''
            }
        }

        stage('Prepare Deployment Package') {
            steps {
                echo 'Preparing deployment package...'
                sh '''
                    # Создаем директорию для деплоя
                    rm -rf deploy_package
                    mkdir -p deploy_package

                    # Копируем необходимые файлы
                    cp docker-compose.yml deploy_package/
                    cp Dockerfile.ai deploy_package/
                    cp -r db_kinotavr deploy_package/
                    cp -r tgBot deploy_package/
                    cp main.py requirements.txt deploy_package/

                    # Создаем .env файл
                    cat > deploy_package/.env << EOF
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

                    # Создаем deployment скрипт
                    cat > deploy_package/deploy.sh << 'DEPLOY_SCRIPT'
#!/bin/bash
set -e

echo "=== Starting Kinotavr deployment ==="

# Останавливаем старые контейнеры
echo "Stopping old containers..."
docker-compose down || true

# Удаляем старые образы
echo "Removing old images..."
docker-compose down --rmi local || true

# Собираем новые образы
echo "Building new images..."
docker-compose build --no-cache

# Запускаем сервисы
echo "Starting services..."
docker-compose up -d

# Ждем готовности
echo "Waiting for services to be ready..."
sleep 10

# Проверяем статус
echo "Checking services status..."
docker-compose ps

# Проверяем здоровье сервисов
echo "Health checks:"
for i in {1..30}; do
    if curl -f http://localhost:8001/ping > /dev/null 2>&1; then
        echo "✓ AI Backend is healthy"
        break
    fi
    echo "Waiting for AI Backend... ($i/30)"
    sleep 2
done

for i in {1..30}; do
    if curl -f http://localhost:8000/api/v1/colors > /dev/null 2>&1; then
        echo "✓ DB Backend is healthy"
        break
    fi
    echo "Waiting for DB Backend... ($i/30)"
    sleep 2
done

echo "=== Deployment completed successfully ==="
docker-compose logs --tail=50
DEPLOY_SCRIPT

                    chmod +x deploy_package/deploy.sh

                    # Создаем архив
                    tar -czf kinotavr-deploy.tar.gz deploy_package/
                '''
            }
        }

        stage('Backup Remote') {
            steps {
                echo 'Creating backup on remote server...'
                sshagent(credentials: ['ubuntu-server-ssh-key']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "
                            if [ -d ${REMOTE_PATH} ]; then
                                echo 'Creating backup...'
                                timestamp=\$(date +%Y%m%d_%H%M%S)
                                sudo mkdir -p ${REMOTE_PATH}_backups
                                sudo cp -r ${REMOTE_PATH} ${REMOTE_PATH}_backups/backup_\$timestamp

                                # Сохраняем данные БД
                                if [ -d ${REMOTE_PATH} ]; then
                                    cd ${REMOTE_PATH}
                                    if docker-compose ps | grep -q kinotavr_postgres; then
                                        echo 'Backing up database...'
                                        docker-compose exec -T db pg_dump -U user_admin movies_db > ${REMOTE_PATH}_backups/db_backup_\$timestamp.sql
                                    fi
                                fi

                                # Оставляем только последние 5 бэкапов
                                cd ${REMOTE_PATH}_backups
                                ls -t | tail -n +6 | xargs -r rm -rf

                                echo 'Backup completed'
                            else
                                echo 'No previous installation found, skipping backup'
                            fi
                        "
                    '''
                }
            }
        }

        stage('Deploy to Server') {
            steps {
                echo 'Deploying to Ubuntu server...'
                sshagent(credentials: ['ubuntu-server-ssh-key']) {
                    sh '''
                        # Копируем архив на сервер
                        scp -o StrictHostKeyChecking=no kinotavr-deploy.tar.gz ${REMOTE_USER}@${REMOTE_HOST}:/tmp/

                        # Разворачиваем и запускаем
                        ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "
                            set -e

                            # Создаем директорию если не существует
                            sudo mkdir -p ${REMOTE_PATH}
                            sudo chown ${REMOTE_USER}:${REMOTE_USER} ${REMOTE_PATH}

                            # Распаковываем
                            cd ${REMOTE_PATH}
                            tar -xzf /tmp/kinotavr-deploy.tar.gz --strip-components=1
                            rm /tmp/kinotavr-deploy.tar.gz

                            # Запускаем деплой скрипт
                            bash deploy.sh
                        "
                    '''
                }
            }
        }

        stage('Health Check') {
            steps {
                echo 'Performing health checks...'
                sshagent(credentials: ['ubuntu-server-ssh-key']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "
                            cd ${REMOTE_PATH}

                            echo 'Container status:'
                            docker-compose ps

                            echo 'Testing endpoints...'

                            # AI Backend
                            if curl -f http://localhost:8001/ping; then
                                echo '✓ AI Backend is accessible'
                            else
                                echo '✗ AI Backend is not accessible'
                                exit 1
                            fi

                            # DB Backend
                            if curl -f http://localhost:8000/api/v1/colors; then
                                echo '✓ DB Backend is accessible'
                            else
                                echo '✗ DB Backend is not accessible'
                                exit 1
                            fi

                            # Database
                            if docker-compose exec -T db pg_isready -U user_admin -d movies_db; then
                                echo '✓ Database is accessible'
                            else
                                echo '✗ Database is not accessible'
                                exit 1
                            fi

                            echo 'All health checks passed!'
                        "
                    '''
                }
            }
        }

        stage('Smoke Tests') {
            steps {
                echo 'Running smoke tests...'
                sshagent(credentials: ['ubuntu-server-ssh-key']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "
                            # Проверка API endpoints
                            echo 'Testing colors endpoint...'
                            curl -s http://localhost:8000/api/v1/colors | grep -q 'deep_blue' || exit 1

                            echo 'Testing ping endpoint...'
                            curl -s http://localhost:8001/ping | grep -q 'alive' || exit 1

                            echo 'Smoke tests passed!'
                        "
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'Deployment successful!'
            emailext (
                subject: "SUCCESS: Kinotavr Deployment - Build #${BUILD_NUMBER}",
                body: """
                    Deployment to Ubuntu server completed successfully!

                    Build: ${BUILD_NUMBER}
                    Branch: ${GIT_BRANCH}
                    Commit: ${GIT_COMMIT}

                    All services are running and health checks passed.
                """,
                to: "${env.NOTIFICATION_EMAIL}",
                attachLog: false
            )
        }

        failure {
            echo 'Deployment failed!'
            sshagent(credentials: ['ubuntu-server-ssh-key']) {
                sh '''
                    # Попытка отката к последнему бэкапу
                    ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "
                        cd ${REMOTE_PATH}_backups
                        latest_backup=\$(ls -t | grep backup_ | head -1)
                        if [ -n \"\$latest_backup\" ]; then
                            echo 'Rolling back to \$latest_backup'
                            sudo rm -rf ${REMOTE_PATH}
                            sudo cp -r \$latest_backup ${REMOTE_PATH}
                            cd ${REMOTE_PATH}
                            docker-compose up -d
                        fi
                    " || true
                '''
            }

            emailext (
                subject: "FAILURE: Kinotavr Deployment - Build #${BUILD_NUMBER}",
                body: """
                    Deployment to Ubuntu server failed!

                    Build: ${BUILD_NUMBER}
                    Branch: ${GIT_BRANCH}
                    Commit: ${GIT_COMMIT}

                    Check Jenkins console output for details.
                    Automatic rollback attempted.
                """,
                to: "${env.NOTIFICATION_EMAIL}",
                attachLog: true
            )
        }

        always {
            echo 'Cleaning up...'
            sh '''
                # Очистка локальных образов
                docker-compose down -v || true

                # Очистка временных файлов
                rm -rf deploy_package kinotavr-deploy.tar.gz
            '''
        }
    }
}
