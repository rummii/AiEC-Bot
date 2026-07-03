#!/bin/bash
# Complete cPanel Deployment Script for AiEC-Bot
# Domain: https://aiexperiencecenter.ph/
# App: aiec-bot
# 
# Usage: Copy and paste each section into your cPanel SSH terminal
# OR: Save as deploy.sh and run: bash deploy.sh

set -e  # Exit on any error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     AiEC-Bot Deployment Script for cPanel                 ║"
echo "║     Domain: aiexperiencecenter.ph                         ║"
echo "║     App Path: aiec-bot                                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
CPANEL_USER=$(whoami)
APP_NAME="aiec-bot"
APP_PATH="/home/$CPANEL_USER/public_html/$APP_NAME"
DOMAIN="https://aiexperiencecenter.ph"
WEBHOOK_URL="$DOMAIN/$APP_NAME/webhook"

echo "📋 Configuration:"
echo "   User: $CPANEL_USER"
echo "   App Path: $APP_PATH"
echo "   Domain: $DOMAIN"
echo "   Webhook URL: $WEBHOOK_URL"
echo ""

# Step 1: Create app directory
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1️⃣ : Create app directory"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
mkdir -p "$APP_PATH"
cd "$APP_PATH"
echo "✅ Created: $APP_PATH"
echo ""

# Step 2: Clone repository
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2️⃣ : Clone AiEC-Bot repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d ".git" ]; then
    echo "ℹ️  Repository already exists, pulling latest..."
    git pull origin main
else
    echo "📥 Cloning repository..."
    git clone https://github.com/rummii/AiEC-Bot.git .
fi
echo "✅ Repository ready"
echo ""

# Step 3: Create virtual environment
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3️⃣ : Create Python virtual environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created"
echo ""

# Step 4: Install dependencies
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4️⃣ : Install Python dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Step 5: Create config.py
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5️⃣ : Create config.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Read Telegram credentials
echo "⚠️  Enter your Telegram Bot Token (from @BotFather):"
read -r TELEGRAM_BOT_TOKEN

echo "⚠️  Enter your Telegram Chat ID:"
read -r TELEGRAM_CHAT_ID

echo "⚠️  Enter your DeepSeek API Key (or press Enter to skip):"
read -r DEEPSEEK_API_KEY

# Create config.py
cat > config.py << EOF
# AiEC-Bot Configuration
# Generated for cPanel deployment

TELEGRAM_BOT_TOKEN = "$TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "$TELEGRAM_CHAT_ID"
DEEPSEEK_API_KEY = "$DEEPSEEK_API_KEY"
TELEGRAM_WEBHOOK_URL = "$WEBHOOK_URL"
EOF

echo "✅ config.py created"
echo "   Location: $APP_PATH/config.py"
echo "   Webhook URL: $WEBHOOK_URL"
echo ""

# Step 6: Create passenger_wsgi.py for cPanel
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 6️⃣ : Create passenger_wsgi.py (cPanel entry point)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat > passenger_wsgi.py << 'EOF'
import sys
import os

# Add app directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Activate virtual environment
VENV_DIR = os.path.join(os.path.dirname(__file__), 'venv')
if os.path.exists(VENV_DIR):
    activate_this = os.path.join(VENV_DIR, 'bin', 'activate_this.py')
    if os.path.exists(activate_this):
        with open(activate_this) as f:
            exec(f.read(), {'__file__': activate_this})

# Import Flask app
from app import app

# Passenger WSGI application
application = app

if __name__ == "__main__":
    app.run()
EOF

echo "✅ passenger_wsgi.py created"
echo ""

# Step 7: Create necessary directories
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 7️⃣ : Create required directories"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
mkdir -p knowledge_base/audio_logs
mkdir -p templates
echo "✅ Directories created"
echo ""

# Step 8: Set permissions
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 8️⃣ : Set file permissions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
chmod 755 "$APP_PATH"
chmod 755 "$APP_PATH"/*
chmod 644 config.py
chmod 644 app.py
chmod 644 passenger_wsgi.py
chmod 755 knowledge_base
chmod 777 knowledge_base/audio_logs
echo "✅ Permissions set"
echo ""

# Step 9: Verify installation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 9️⃣ : Verify installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python
echo "✓ Python version:"
python3 --version

# Check Flask
echo "✓ Flask installed:"
python3 -c "import flask; print(f'  Flask {flask.__version__}')" 2>/dev/null || echo "  Flask check failed"

# Check pydub
echo "✓ pydub installed:"
python3 -c "import pydub; print('  pydub OK')" 2>/dev/null || echo "  pydub check failed"

# Check speech_recognition
echo "✓ speech_recognition installed:"
python3 -c "import speech_recognition; print('  speech_recognition OK')" 2>/dev/null || echo "  speech_recognition check failed"

# Check config
echo "✓ config.py:"
if [ -f config.py ]; then
    echo "  ✅ Found at $APP_PATH/config.py"
    echo "  Webhook URL: $WEBHOOK_URL"
else
    echo "  ❌ NOT FOUND"
fi

echo ""

# Step 10: Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  ✅ DEPLOYMENT COMPLETE                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 App Location: $APP_PATH"
echo "🌐 Domain: $DOMAIN"
echo "📡 Webhook URL: $WEBHOOK_URL"
echo ""
echo "🔗 NEXT STEPS IN cPanel:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Log into cPanel"
echo "2. Go to: Software → Setup Python App"
echo "3. Create new app with:"
echo "   - Python version: 3.9 or higher"
echo "   - Application root: /home/$CPANEL_USER/public_html/$APP_NAME"
echo "   - Application startup file: app.py"
echo "   - Application URL: Use your domain path"
echo "4. cPanel will auto-create/detect passenger_wsgi.py"
echo ""
echo "✅ TESTING:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Check webhook status:"
echo "   $DOMAIN/$APP_NAME/webhook-status"
echo ""
echo "2. Send text command to Telegram bot:"
echo "   /status"
echo ""
echo "3. Send voice message via Telegram microphone button"
echo ""
echo "4. Check knowledge base file:"
echo "   cat $APP_PATH/knowledge_base/company_data.txt"
echo ""
echo "📋 Check Logs:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SSH tail logs:"
echo "   tail -50 $APP_PATH/logs/error_log"
echo ""
echo "🎉 All set! Deploy to cPanel now."
echo ""
