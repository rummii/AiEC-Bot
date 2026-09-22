#!/bin/bash
# ============================================================
# AiEC-Bot — Google Cloud Run Deployment Script
# ============================================================
# Prerequisites:
#   1. gcloud CLI installed & authenticated (https://cloud.google.com/sdk)
#   2. Project selected: gcloud config set project [PROJECT_ID]
#   3. APIs enabled:
#        gcloud services enable run.googleapis.com artifactregistry.googleapis.com
#
# Usage:
#   ./deploy_cloud_run.sh
#
# Env vars consumed (set these in Cloud Run after first deploy):
#   TELEGRAM_BOT_TOKEN      — Bot token from @BotFather
#   TELEGRAM_CHAT_ID        — Target chat ID for notifications
#   DEEPSEEK_API_KEY        — DeepSeek API key for AI responses
#   TELEGRAM_WEBHOOK_URL    — Public Cloud Run URL (auto-set by Cloud Run)
# ============================================================

set -euo pipefail

# --- Configuration ---
SERVICE_NAME="aiec-bot"
REGION="us-central1"
MEMORY="512Mi"
CPU="1000m"
CONCURRENCY="1"

echo "📦  AiEC-Bot → Google Cloud Run"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- Check gcloud is available ---
if ! command -v gcloud &>/dev/null; then
    echo "❌ gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# --- Check authentication ---
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated. Run: gcloud auth login"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No GCP project set. Run: gcloud config set project [PROJECT_ID]"
    exit 1
fi

echo "   Project : $PROJECT_ID"
echo "   Service : $SERVICE_NAME"
echo "   Region  : $REGION"
echo ""

# --- Enable required APIs ---
echo "🔧 Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com
echo "✅ APIs enabled"

# --- Build & deploy ---
echo ""
echo "🏗️  Building container and deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --memory "$MEMORY" \
    --cpu "$CPU" \
    --concurrency "$CONCURRENCY" \
    --allow-unauthenticated \
    --platform managed

echo ""
echo "✅ Deployment complete!"
echo ""
echo "──────────────────────────────────────"
echo " NEXT STEPS: Configure secrets"
echo "──────────────────────────────────────"
echo ""
echo "Set these environment variables in Cloud Run:"
echo "  TELEGRAM_BOT_TOKEN  — Bot token from @BotFather"
echo "  TELEGRAM_CHAT_ID    — Target chat ID"
echo "  DEEPSEEK_API_KEY    — Your DeepSeek API key"
echo "  TELEGRAM_WEBHOOK_URL — Your Cloud Run URL (set after deploy)"
echo ""
echo "Run this to set them:"
echo "  gcloud run services update $SERVICE_NAME \\"
echo "    --region $REGION \\"
echo "    --set-env-vars \\"
echo "TELEGRAM_BOT_TOKEN=[YOUR_TOKEN],TELEGRAM_CHAT_ID=[YOUR_CHAT_ID],DEEPSEEK_API_KEY=[YOUR_KEY]"
echo ""
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --format "value(status.url)" 2>/dev/null || echo "YOUR_CLOUD_RUN_URL")
echo "Webhook URL: ${SERVICE_URL}/webhook"