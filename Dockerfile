# ============================================================
# AiEC-Bot — Google Cloud Run Dockerfile
# Multi-stage build: slim runtime with ffmpeg for audio
# ============================================================

FROM python:3.12-slim AS base

# Metadata
LABEL org.opencontainers.image.title="aiec-bot"
LABEL org.opencontainers.image.description="AIEC Telegram Bot — voice-to-text on Google Cloud Run"
LABEL org.opencontainers.image.licenses="MIT"

# System dependencies
#   ffmpeg   — required by pydub for audio transcoding
#   libsndfile1 — recommended for audio file I/O
#   curl     — for self-health checks inside container
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version | head -1

# Create non-root user (Cloud Run best practice)
RUN groupadd -r appuser \
    && useradd -r -g appuser -m -d /home/appuser appuser

# Set working directory
WORKDIR /app

# Install Python dependencies first (leverages Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure the knowledge_base and audio_logs directories exist
RUN mkdir -p /app/knowledge_base/audio_logs

# Make sure non-root user owns the app files
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Flask / Cloud Run: bind to 0.0.0.0:$PORT
# Cloud Run injects PORT env var (default 8080)
EXPOSE 8080

# Use gunicorn for production serving (matches render.yaml / Procfile)
CMD ["sh", "-c", "exec gunicorn --workers 1 --threads 4 --bind 0.0.0.0:$PORT app:app"]