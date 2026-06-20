#!/bin/bash

# Скрипт для автоматического обновления WEBAPP_URL после запуска ngrok
# Использование: ./update_webapp_url.sh

set -e

echo "🔍 Waiting for ngrok to start..."
sleep 5

# Получаем ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

if [ -z "$NGROK_URL" ] || [ "$NGROK_URL" == "null" ]; then
    echo "❌ Error: Cannot get ngrok URL"
    echo "Make sure ngrok is running: docker-compose up -d"
    exit 1
fi

echo "✅ New ngrok URL: $NGROK_URL"

# Обновляем .env
if [ -f .env ]; then
    sed -i.bak "s|WEBAPP_URL=.*|WEBAPP_URL=$NGROK_URL|g" .env
    echo "📝 Updated .env file"
else
    echo "⚠️  Warning: .env file not found"
fi

# Перезапускаем бота
echo "🔄 Restarting telegram bot..."
docker-compose restart telegram_bot

echo "✅ Bot restarted successfully!"
echo "📱 Mini App URL: $NGROK_URL"
echo "🌐 ngrok dashboard: http://localhost:4040"
