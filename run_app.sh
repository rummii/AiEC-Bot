#!/bin/bash

echo "⚙️ Writing verified case-sensitive credentials to config.py..."
cat << 'CONFIG' > config.py
TELEGRAM_BOT_TOKEN = "8624026555:AAHZsOh95QmuqhoPOYuVhcfk0eIfJGH7P54"
TELEGRAM_CHAT_ID = "6027602817"
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_KEY_HERE"
CONFIG

echo "🧹 Clearing lingering port 5000 processes..."
fuser -k 5000/tcp || true
kill -9 $(lsof -t -i:5000) 2>/dev/null || true

echo "🚀 Launching Python Application..."
python app.py
