# AiEC-Bot — Google Cloud Run Deployment Guide

This guide covers deploying AiEC-Bot to **Google Cloud Run** (fully managed).  
The same application code also works on Render and Heroku (see `render.yaml` / `Procfile`).

---

## 0. Before You Start

| Requirement | Notes |
|-------------|-------|
| **Google Cloud account** | Billing must be enabled on the project |
| **gcloud CLI** | Install from [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| **Application source** | This repository, with `app.py`, `requirements.txt`, `Dockerfile` |

---

## 1. Authenticate & Select Project

```bash
gcloud auth login

# If you don't have a project yet:
gcloud projects create aiec-bot-project --set-as-default
gcloud config set project aiec-bot-project
```

## 2. Enable APIs

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

## 3. Deploy (Automated)

The easiest path — Cloud Run's `--source` flag builds from source automatically:

```bash
chmod +x deploy_cloud_run.sh
./deploy_cloud_run.sh
```

This script:
1. ✅ Verifies `gcloud` is authenticated and a project is set
2. ✅ Enables required APIs
3. ✅ Builds the container and deploys to Cloud Run
4. ✅ Prints the next-step commands for setting secrets

## 3b. Deploy (Manual — using Dockerfile)

If you prefer to build the image explicitly:

```bash
# 1. Build
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/aiec-bot

# 2. Deploy
gcloud run deploy aiec-bot \
    --image gcr.io/$(gcloud config get-value project)/aiec-bot \
    --region us-central1 \
    --memory 512Mi \
    --concurrency 1 \
    --allow-unauthenticated
```

---

## 4. Configure Environment Variables

Cloud Run **never** stores secrets in code. Set them as **environment variables**:

```bash
# Set secrets (replace [VALUE] with actual values)
gcloud run services update aiec-bot \
    --region us-central1 \
    --set-env-vars \
"TELEGRAM_BOT_TOKEN=[YOUR_BOT_TOKEN],
TELEGRAM_CHAT_ID=[YOUR_CHAT_ID],
DEEPSEEK_API_KEY=[YOUR_DEEPSEEK_KEY]"
```

Or set each individually:

```bash
gcloud run services update aiec-bot \
    --region us-central1 \
    --update-env-vars TELEGRAM_BOT_TOKEN=[YOUR_BOT_TOKEN]

gcloud run services update aiec-bot \
    --region us-central1 \
    --update-env-vars TELEGRAM_CHAT_ID=[YOUR_CHAT_ID]

gcloud run services update aiec-bot \
    --region us-central1 \
    --update-env-vars DEEPSEEK_API_KEY=[YOUR_DEEPSEEK_KEY]
```

### Required Environment Variables

| Variable | Source | Example |
|----------|--------|---------|
| `TELEGRAM_BOT_TOKEN` | @BotFather | `123456789:AAHZ...` |
| `TELEGRAM_CHAT_ID` | Bot → @userinfobot | `123456789` |
| `DEEPSEEK_API_KEY` | console.deepseek.com | `sk-abcdef...` |
| `TELEGRAM_WEBHOOK_URL` | Auto-set after deploy | `https://aiec-bot-xxx-uc.a.run.app` |
| `TELEGRAM_WEBHOOK_SECRET` | Self-generated (recommended) | `secrets.token_urlsafe(32)` |

### Webhook Authentication (recommended)

Generate a secret and store it in Secret Manager, then mount it:

```bash
# Generate
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Store
printf '%s' 'YOUR_GENERATED_SECRET' | \
  gcloud secrets create aiec-telegram-webhook-secret --data-file=- --replication-policy=automatic

# Grant access
gcloud secrets add-iam-policy-binding aiec-telegram-webhook-secret \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Mount
gcloud run services update aiec-bot --region us-central1 \
  --update-secrets="TELEGRAM_WEBHOOK_SECRET=aiec-telegram-webhook-secret:latest"
```

When set, `/webhook` returns **HTTP 403** for any request whose
`X-Telegram-Bot-Api-Secret-Token` header is missing or does not match, and the app
passes the same value to `setWebhook` automatically at startup.

### Get Your Webhook URL

After deployment, Cloud Run prints the service URL. Set it as the webhook:

```bash
SERVICE_URL=$(gcloud run services describe aiec-bot \
    --region us-central1 \
    --format "value(status.url)")

gcloud run services update aiec-bot \
    --region us-central1 \
    --update-env-vars TELEGRAM_WEBHOOK_URL="${SERVICE_URL}/webhook"
```

---

## 5. Set Up Telegram Webhook

The app registers the webhook automatically on startup (via `register_telegram_webhook()`).

To verify:

```bash
# Check webhook status
curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo

# Manual registration (if auto fails)
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
    -F "url=${SERVICE_URL}/webhook"
```

---

## 6. Verify Deployment

```bash
# Check Cloud Run logs
gcloud logging read "resource.labels.service_name=aiec-bot" \
    --limit 50

# Health check
curl https://aiec-bot-xxx.uc.r.appspot.com/
```

---

## Configuration Reference

| Setting | Default | Cloud Run Env Var |
|---------|---------|-------------------|
| Port | `8080` (from `$PORT`) | Injected by Cloud Run |
| Workers | 1 | In Dockerfile CMD |
| Concurrency | 1 | `--concurrency 1` in deploy script |
| Memory | 512Mi | `--memory 512Mi` |
| CPU | 1000m | `--cpu 1000m` |
| Region | us-central1 | `--region us-central1` |

---

## Notes

- **Concurrency = 1**: Speech processing is resource-heavy; one concurrent request per instance
- **Scales to zero**: Cloud Run automatically stops when idle, so this is cost-effective
- **Persistent storage**: Cloud Run uses ephemeral storage — the `knowledge_base/` and `aiec_bot.db` should be backed by Cloud SQL (PostgreSQL) for persistence if needed
- **Dual platform**: The app also deploys to Render (`render.yaml`) and Heroku (`Procfile`) without code changes