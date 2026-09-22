# ============================================================
# AiEC-Bot — Google Cloud Run Deployment Script (PowerShell)
# ============================================================
# Prerequisites:
#   1. gcloud CLI installed & authenticated
#   2. Project selected: gcloud config set project [PROJECT_ID]
#   3. APIs enabled: run.googleapis.com artifactregistry.googleapis.com
#
# Usage:
#   .\deploy_cloud_run.ps1
#
# ============================================================
Continue = "Stop"

# --- Configuration ---
 = "aiec-bot"
 = "us-central1"
 = "512Mi"
 = "1000m"
 = "1"

Write-Host "📦  AiEC-Bot → Google Cloud Run" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

# --- Check gcloud is available ---
if (!(Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "❌ gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install" -ForegroundColor Red
    exit 1
}

# --- Check authentication ---
 = gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>\
if (!) {
    Write-Host "❌ Not authenticated. Run: gcloud auth login" -ForegroundColor Red
    exit 1
}

 = gcloud config get-value project 2>\
if (!) {
    Write-Host "❌ No GCP project set. Run: gcloud config set project [PROJECT_ID]" -ForegroundColor Red
    exit 1
}

Write-Host "   Project : " -ForegroundColor Yellow
Write-Host "   Service : " -ForegroundColor Yellow
Write-Host "   Region  : " -ForegroundColor Yellow
Write-Host "" -ForegroundColor Gray

# --- Enable required APIs ---
Write-Host "🔧 Enabling APIs..." -ForegroundColor Cyan
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
Write-Host "✅ APIs enabled" -ForegroundColor Green

# --- Build & deploy ---
Write-Host "" -ForegroundColor Gray
Write-Host "🏗️  Building container and deploying to Cloud Run..." -ForegroundColor Cyan
gcloud run deploy  
    --source . 
    --region  
    --memory  
    --cpu  
    --concurrency  
    --allow-unauthenticated 
    --platform managed

Write-Host "" -ForegroundColor Gray
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host "" -ForegroundColor Gray

# Set webhook URL for secrets
 = gcloud run services describe  
    --region  
    --format "value(status.url)" 2>\

Write-Host "Webhook URL: /webhook" -ForegroundColor Green
