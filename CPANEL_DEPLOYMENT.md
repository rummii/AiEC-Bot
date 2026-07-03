# Deploying AiEC-Bot on cPanel

## Prerequisites
- cPanel with Python app support (you have this ✅)
- SSH access to your cPanel server
- Your domain name (e.g., `yourdomain.com`)
- Telegram bot token (already have it)

---

## Step 1: Create Python App in cPanel

### Via cPanel GUI:
1. Login to cPanel
2. Go to **Software** section
3. Click **Setup Python App** (or similar)
4. Create a new Python application:
   - **Python version**: 3.9 or higher
   - **Application root**: `/home/username/aiec-bot` (or any path)
   - **Application URL**: Can be domain or subdirectory
   - **Application startup file**: `app.py`

Note the **WSGI file location** - it will be something like: `/home/username/aiec-bot/passenger_wsgi.py`

---

## Step 2: Clone Your App into cPanel

Connect via SSH:
```bash
ssh username@yourdomain.com
cd /home/username/aiec-bot

# Clone your repo
git clone https://github.com/rummii/AiEC-Bot.git .

# Or if already there, pull latest
git pull origin main
```

---

## Step 3: Install Python Dependencies

```bash
# Navigate to app directory
cd /home/username/aiec-bot

# Create virtual environment (if not auto-created by cPanel)
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## Step 4: Create/Update config.py

Create a `config.py` file in your app root:

```python
# config.py
TELEGRAM_BOT_TOKEN = "8624026555:AAHZsOh95QmuqhoPOYuVhcfk0eIfJGH7P54"
TELEGRAM_CHAT_ID = "6027602817"
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_KEY_HERE"

# Your cPanel deployment URL
TELEGRAM_WEBHOOK_URL = "https://yourdomain.com/aiec-bot/webhook"
```

Replace:
- `yourdomain.com` with your actual domain
- `/aiec-bot` with your actual cPanel app path (if different)

---

## Step 5: Create passenger_wsgi.py

If cPanel didn't auto-create it, create `passenger_wsgi.py` in your app root:

```python
# passenger_wsgi.py
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run Flask app
from app import app

# For Passenger WSGI
application = app

if __name__ == "__main__":
    app.run()
```

---

## Step 6: Set Permissions

```bash
# Make sure permissions are correct
chmod 755 /home/username/aiec-bot
chmod 644 /home/username/aiec-bot/config.py
chmod 644 /home/username/aiec-bot/app.py
```

---

## Step 7: Configure Telegram Webhook

### Option A: Via config.py (Recommended)
Already done in Step 4. Just update the URL to match your cPanel deployment.

### Option B: Via Environment Variables in cPanel

In cPanel Python app settings, add environment variables:
```
TELEGRAM_BOT_TOKEN=8624026555:AAHZsOh95QmuqhoPOYuVhcfk0eIfJGH7P54
TELEGRAM_CHAT_ID=6027602817
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/aiec-bot/webhook
```

---

## Step 8: Check Your Webhook Status

Once deployed, visit:
```
https://yourdomain.com/aiec-bot/webhook-status
```

You should see:
```json
{
  "webhook_configured": true,
  "token_configured": true,
  "webhook_url_configured": true,
  "webhook_url": "https://yourdomain.com/aiec-bot/webhook",
  "telegram_webhook_info": {
    "url": "https://yourdomain.com/aiec-bot/webhook",
    "pending_update_count": 0,
    ...
  }
}
```

---

## Step 9: Test Telegram Voice Messages

1. Send a text command to your bot: `/status`
2. Then send a voice message
3. Check cPanel logs for messages starting with:
   - `[WEBHOOK]`
   - `[TRANSCRIBE]`
   - `[TELEGRAM WEBHOOK]`

---

## Accessing Logs

### Option A: cPanel File Manager
1. Go to cPanel → File Manager
2. Navigate to `/home/username/aiec-bot/`
3. Look for `error_log` or `access_log`

### Option B: SSH
```bash
# View recent logs
tail -50 /home/username/aiec-bot/logs/error_log

# Or if Passenger logs
tail -50 /home/username/aiec-bot/tmp/restart.txt
```

### Option C: cPanel Dashboard
Some cPanel versions show Python app logs in the web interface.

---

## Troubleshooting

### Issue: "Module not found" errors
**Solution:**
```bash
# Make sure all dependencies installed
source /home/username/aiec-bot/venv/bin/activate
pip install -r requirements.txt
```

### Issue: Webhook not registered
**Solution:**
Check `/webhook-status` endpoint:
- Confirm `TELEGRAM_WEBHOOK_URL` is set
- Make sure URL is HTTPS (not HTTP)
- Verify domain/path is correct

### Issue: Voice messages still not received
**Solution:**
1. Check webhook status shows `"webhook_configured": true`
2. Send a test text command first: `/status`
3. Check logs for `[WEBHOOK] Received message`
4. If logs don't show anything, webhook wasn't called by Telegram

### Issue: "Permission denied" errors
**Solution:**
```bash
chmod 755 /home/username/aiec-bot
chmod 755 /home/username/aiec-bot/knowledge_base
chmod 777 /home/username/aiec-bot/knowledge_base/audio_logs
```

---

## File Structure Expected by cPanel

```
/home/username/aiec-bot/
├── app.py                    ← Main Flask app
├── passenger_wsgi.py        ← Entry point for cPanel
├── config.py                ← Your Telegram credentials
├── requirements.txt         ← Python dependencies
├── index.html               ← Web interface
├── templates/               ← More templates
├── knowledge_base/          ← Data files
│   ├── company_data.txt
│   └── audio_logs/          ← Voice recordings
├── tests/                   ← Unit tests
└── venv/                    ← Virtual environment (optional)
```

---

## Webhook URL Examples

If your cPanel app is at:
- **Root domain**: `https://yourdomain.com/webhook`
- **Subdirectory**: `https://yourdomain.com/myapp/webhook`
- **Subdomain**: `https://app.yourdomain.com/webhook`

Use that exact path in your `config.py`:
```python
TELEGRAM_WEBHOOK_URL = "https://yourdomain.com/myapp/webhook"
```

---

## Environment Variables (cPanel)

In cPanel Python app setup, you can add:
```
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_CHAT_ID=your-chat-id
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
```

These override `config.py` values.

---

## Testing the Deployment

### 1. Test Webhook Endpoint (Browser/curl)
```bash
curl https://yourdomain.com/aiec-bot/webhook-status
```

### 2. Test Web UI
```
https://yourdomain.com/aiec-bot/
```

You should see the control panel.

### 3. Test Text Command
Send message to Telegram bot: `/status`

### 4. Test Voice Message
Send a voice note via Telegram microphone button

---

## Production Recommendations

### 1. HTTPS/SSL
- Make sure your domain has SSL certificate
- cPanel usually provides free SSL via AutoSSL
- Telegram **requires** HTTPS for webhooks

### 2. Security
- Don't commit `config.py` with real tokens to git
- Use cPanel environment variables instead
- Keep tokens secure

### 3. Monitoring
- Check logs regularly
- Monitor app restarts
- Watch for Telegram API errors

### 4. Backups
```bash
# Backup knowledge base
tar -czf knowledge_base_backup.tar.gz knowledge_base/

# Backup config
cp config.py config.py.backup
```

---

## Quick Checklist

- [ ] Python app created in cPanel
- [ ] Code cloned to cPanel path
- [ ] Dependencies installed
- [ ] config.py created with correct webhook URL
- [ ] passenger_wsgi.py exists
- [ ] File permissions set correctly
- [ ] Test `/webhook-status` endpoint
- [ ] Test text command to Telegram bot
- [ ] Test voice message to Telegram bot
- [ ] Check logs for `[WEBHOOK]` messages
- [ ] Voice text appears in knowledge_base/company_data.txt

---

## Support

If you get stuck:
1. Check the logs first
2. Visit `/webhook-status` to see configuration
3. Verify TELEGRAM_WEBHOOK_URL matches your cPanel path
4. Make sure Telegram bot token is valid
5. Check that Flask app can write to knowledge_base/ folder
