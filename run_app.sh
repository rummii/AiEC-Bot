#!/bin/bash
# ============================================================
# AiEC-Bot Launch Script
# Tokens are provided via environment variables (GitHub Environment Secrets)
# ============================================================

# Ensure config.py uses env-var-based defaults
if [ ! -f config.py ]; then
    cat > config.py << 'EOF'
# AiEC-Bot Configuration
# Secrets are loaded from environment variables (e.g., GitHub Environment Secrets)
# Set these as environment variables in your deployment (GitHub, cPanel, etc.)

# Telegram Bot Token - set via environment variable TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_TOKEN = None

# Telegram Chat ID - set via environment variable TELEGRAM_CHAT_ID
TELEGRAM_CHAT_ID = None

# DeepSeek API Key - set via environment variable DEEPSEEK_API_KEY
DEEPSEEK_API_KEY = None

# Telegram Webhook URL - set via environment variable TELEGRAM_WEBHOOK_URL
TELEGRAM_WEBHOOK_URL = None
EOF
    echo "✅ Created config.py with env-var placeholder defaults"
fi

echo "🧹 Clearing lingering port 5000 processes..."
fuser -k 5000/tcp || true
kill -9 $(lsof -t -i:5000) 2>/dev/null || true

echo "🚀 Launching Python Application..."
python app.py
