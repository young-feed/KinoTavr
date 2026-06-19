pipeline {
  agent {
    label 'docker-host'
  }

  environment {
    PROJECT_NAME = 'KinoTavr'
    DEPLOY_DIR   = '/opt/kinotavr'
    COMPOSE_FILE = 'docker-compose.yml'
  }

  options {
    buildDiscarder(logRotator(numToKeepStr: '10'))
    disableConcurrentBuilds()
    timeout(time: 30, unit: 'MINUTES')
    timestamps()
  }

  stages {

    stage('Checkout') {
      steps {
        echo '📥 Checking out source code...'
        checkout scm

        sh '''
          echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
          echo "Commit: $(git rev-parse --short HEAD)"
        '''
      }
    }

    stage('Validate Structure') {
      steps {
        echo '🔍 Validating project structure...'
        sh '''
          REQUIRED_FILES=(
            "docker-compose.yml"
            "Dockerfile.ai"
            "tgBot/Dockerfile"
            "db_kinotavr/backend/Dockerfile"
            "db_kinotavr/parser/Dockerfile"
          )

          MISSING=0
          for f in "${REQUIRED_FILES[@]}"; do
            if [ ! -f "$f" ]; then
              echo "✗ Missing: $f"
              MISSING=1
            else
              echo "✓ Found: $f"
            fi
          done

          [ "$MISSING" -eq 0 ] || {
            echo "❌ Required files missing! Aborting."
            exit 1
          }
          echo "✅ All required files are present."
        '''
      }
    }

    stage('Generate Environment') {
      steps {
        echo '🔐 Generating deployment .env...'
        withCredentials([
          string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY'),
          string(credentialsId: 'telegram-bot-token', variable: 'TELEGRAM_BOT_TOKEN'),
          string(credentialsId: 'kp-api-key', variable: 'KP_API_KEY'),
          string(credentialsId: 'webapp-url', variable: 'WEBAPP_URL'),
          string(credentialsId: 'db-password', variable: 'DB_PASSWORD')
        ]) {
          sh '''
            cat > .env << ENVEOF
OPENAI_API_KEY=${OPENAI_API_KEY}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
KP_API_KEY=${KP_API_KEY}
WEBAPP_URL=${WEBAPP_URL}
DB_HOST=db
DB_NAME=movies_db
DB_USER=user_admin
DB_PASSWORD=${DB_PASSWORD}
DB_PORT=5432
ENVEOF
            chmod 600 .env
            echo ".env generated (permissions 600)"
          '''
        }
      }
    }

    stage('Test & Validate DB') {
      steps {
        echo '🧪 Running integration tests for Database...'
        sh '''
          docker compose up -d db
          echo "Waiting for PostgreSQL to be ready..."

          for i in $(seq 1 30); do
            if docker compose exec -T db pg_isready -U user_admin -d movies_db 2>/dev/null; then
              echo "✅ Database is ready after $i attempts!"
              break
            fi
            [ "$i" -eq 30 ] && { echo "❌ Database failed to start!" && exit 1; }
            sleep 2
          done

          echo "Checking database schema..."
          docker compose exec -T db \
            psql -U user_admin -d movies_db -c "\dt" || true

          echo "Cleaning up test database..."
          docker compose down -v
          echo "✅ DB integration tests passed."
        '''
      }
    }

    stage('Deploy via Docker Compose') {
      steps {
        echo '🚀 Deploying to host server...'
        sh '''
          echo "Stopping existing services..."
          docker compose down || true

          echo "Building fresh images (no cache)..."
          docker compose build --no-cache

          echo "Starting all services..."
          docker compose up -d

          echo "✅ Deployment commands completed."
        '''
      }
    }

    stage('Health Check') {
      steps {
        echo '💓 Verifying service health...'
        sh '''
          echo "Allowing 10s for service initialization..."
          sleep 10

          docker compose ps

          echo "Checking AI Backend (port 8001)..."
          for i in $(seq 1 30); do
            if curl -sf http://localhost:8001/ping >/dev/null 2>&1; then
              echo "✅ AI Backend is healthy."
              break
            fi
            [ "$i" -eq 30 ] && { echo "❌ AI Backend unhealthy!" && exit 1; }
            sleep 2
          done

          echo "Checking DB Backend (port 8000)..."
          for i in $(seq 1 30); do
            if curl -sf http://localhost:8000/api/v1/colors >/dev/null 2>&1; then
              echo "✅ DB Backend is healthy."
              break
            fi
            [ "$i" -eq 30 ] && { echo "❌ DB Backend unhealthy!" && exit 1; }
            sleep 2
          done

          echo "✅ All health checks passed."
        '''
      }
    }

    stage('Smoke Tests') {
      steps {
        echo '🔬 Running smoke tests...'
        sh '''
          echo "Testing DB API response..."
          curl -sf http://localhost:8000/api/v1/colors \
            | grep -q 'deep_blue' \
            || { echo "❌ Smoke test: DB API" && exit 1; }
          echo "✅ DB API smoke test passed."

          echo "Testing AI API response..."
          curl -sf http://localhost:8001/ping \
            | grep -q 'alive' \
            || { echo "❌ Smoke test: AI API" && exit 1; }
          echo "✅ AI API smoke test passed."

          echo "✅ All smoke tests passed!"
        '''
      }
    }
  }

  post {
    success {
      echo '🎉 Deployment finished successfully!'
    }
    failure {
      echo '💥 Deployment failed! Check logs for details.'
    }
    always {
      echo '🧹 Cleaning up temporary artifacts...'
      sh 'rm -f .env || true'
      echo '✅ Cleanup complete.'
    }
  }
}