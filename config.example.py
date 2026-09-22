# Required environment variables (set these in your deployment):
# - TELEGRAM_BOT_TOKEN: Your Telegram Bot Token from @BotFather
# - TELEGRAM_CHAT_ID: The target chat ID for notifications
# - DEEPSEEK_API_KEY: Your DeepSeek API key for AI responses
# - TELEGRAM_WEBHOOK_URL: Public URL where Telegram can send updates (optional if using polling)
# - TELEGRAM_WEBHOOK_SECRET: Secret token proving inbound webhook calls come from Telegram.
#     Strongly recommended. Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
#     Telegram returns the same value in the X-Telegram-Bot-Api-Secret-Token header.
#     When set, /webhook rejects any request lacking a matching header (HTTP 403).
# 
# Example (do NOT commit actual values):
# TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
# TELEGRAM_CHAT_ID=987654321
# DEEPSEEK_API_KEY=sk-abcdefghijklmnopqrstuvwxyz1234567890ab
# TELEGRAM_WEBHOOK_SECRET=replace_with_a_long_random_string
TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = None
DEEPSEEK_API_KEY = None
TELEGRAM_WEBHOOK_SECRET = None
