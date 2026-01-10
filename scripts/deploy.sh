#!/bin/bash
# Deploy bz2-video-transcriber to TrueNAS server
#
# Prerequisites:
# - sshpass installed: brew install sshpass (Mac) or apt install sshpass (Linux)
# - .env.local with credentials in project root

set -e

# Load credentials
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/.env.local" ]; then
    source "$PROJECT_DIR/.env.local"
else
    echo "Error: .env.local not found in $PROJECT_DIR"
    echo "Create .env.local with DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASSWORD, DEPLOY_PATH"
    exit 1
fi

# Validate required variables
if [ -z "$DEPLOY_HOST" ] || [ -z "$DEPLOY_USER" ] || [ -z "$DEPLOY_PASSWORD" ] || [ -z "$DEPLOY_PATH" ]; then
    echo "Error: Missing required variables in .env.local"
    echo "Required: DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASSWORD, DEPLOY_PATH"
    exit 1
fi

echo "Deploying bz2-video-transcriber..."
echo "Target: $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH"

# Sync files
echo "Syncing files..."
sshpass -p "$DEPLOY_PASSWORD" rsync -avz --delete \
    --exclude 'node_modules' \
    --exclude 'frontend/dist' \
    --exclude '.git' \
    --exclude '.env.local' \
    --exclude 'temp' \
    --exclude '__pycache__' \
    --exclude '.venv' \
    --exclude '.vscode' \
    --exclude '.idea' \
    --exclude '*.pyc' \
    "$PROJECT_DIR/" "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/"

# Rebuild and restart containers (--no-cache to ensure code changes are picked up)
echo "Rebuilding containers..."
sshpass -p "$DEPLOY_PASSWORD" ssh "${DEPLOY_USER}@${DEPLOY_HOST}" \
    "cd ${DEPLOY_PATH} && echo '$DEPLOY_PASSWORD' | sudo -S docker compose build --no-cache && echo '$DEPLOY_PASSWORD' | sudo -S docker compose up -d"

echo ""
echo "Deployed successfully!"
echo "App: http://100.64.0.1:8801"
echo "Health: curl http://100.64.0.1:8801/health"
