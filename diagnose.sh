#!/bin/bash
# Скрипт диагностики проблемы с ngrok

echo "=== 1. Проверка запущенных контейнеров ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n=== 2. Проверка healthcheck telegram_bot ==="
docker inspect kinotavr_telegram_bot --format='{{json .State.Health}}' | jq

echo -e "\n=== 3. Логи telegram_bot (последние 30 строк) ==="
docker logs kinotavr_telegram_bot --tail 30

echo -e "\n=== 4. Проверка - слушает ли бот на порту 8081 внутри контейнера ==="
docker exec kinotavr_telegram_bot netstat -tuln 2>/dev/null || docker exec kinotavr_telegram_bot ss -tuln 2>/dev/null || echo "netstat/ss не установлен"

echo -e "\n=== 5. Проверка - доступен ли порт 8081 изнутри контейнера ==="
docker exec kinotavr_telegram_bot curl -s http://localhost:8081/ | head -c 100 || echo "FAIL: curl не может подключиться"

echo -e "\n=== 6. Логи ngrok (последние 20 строк) ==="
docker logs kinotavr_ngrok --tail 20

echo -e "\n=== 7. Проверка на каком хосте/порту запущен веб-сервер в main.py ==="
docker exec kinotavr_telegram_bot grep -n "TCPSite" main.py

echo -e "\n=== 8. Проверка маппинга портов ==="
docker port kinotavr_telegram_bot

echo -e "\n=== 9. Проверка сети Docker ==="
docker network inspect kinotavr_network | jq '.[0].Containers | with_entries(select(.value.Name | contains("telegram_bot") or contains("ngrok")))'
