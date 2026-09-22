#!/bin/bash
# ============================================================
# AiEC-Bot — Test Telegram Token Validation
# Uses environment variables for security
# ============================================================
# Set these before running:
#   export TELEGRAM_BOT_TOKEN="your_token_here"
#   export TELEGRAM_CHAT_ID="your_chat_id_here"
# ============================================================

TOKEN="${TELEGRAM_BOT_TOKEN:-None}"
CHAT_ID="${TELEGRAM_CHAT_ID:-None}"

if [ "$TOKEN" = "None" ] || [ "$CHAT_ID" = "None" ]; then
    echo "❌ Error: Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables"
    echo "   Example:"
    echo "   export TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    echo "   export TELEGRAM_CHAT_ID=987654321"
    exit 1
fi

echo "🔐 Running direct script validation payload..."
echo "   (Using token from environment - last 4 chars: ${TOKEN: -4})"
curl -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
     -d "chat_id=${CHAT_ID}" \
     -d "text=⚡ Executive Hub: Automated script pipeline online."
echo -e "\nDone."
