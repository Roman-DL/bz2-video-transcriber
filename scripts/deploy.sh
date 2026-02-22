#!/bin/bash
# Deploy bz2-video-transcriber to TrueNAS server
#
# Usage:
#   /bin/bash scripts/deploy.sh          # Standard deploy (uses Docker layer cache)
#   /bin/bash scripts/deploy.sh --pull   # Force update base images before build
#
# Prerequisites:
# - sshpass installed: brew install sshpass (Mac) or apt install sshpass (Linux)
# - .env.local with credentials in project root

set -euo pipefail

# --- Configuration ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION=$(cat "$PROJECT_DIR/VERSION" 2>/dev/null || echo "0.0.0")

BASE_IMAGES=("python:3.12-slim" "node:20-alpine" "nginx:alpine")
HEALTH_URL="https://transcriber.home/health"
PULL_RETRIES=3
PULL_RETRY_DELAY=10
HEALTH_RETRIES=5
HEALTH_RETRY_DELAY=5

# --- Load credentials ---

if [ -f "$PROJECT_DIR/.env.local" ]; then
    source "$PROJECT_DIR/.env.local"
else
    echo "Error: .env.local not found in $PROJECT_DIR"
    echo "Create .env.local with DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASSWORD, DEPLOY_PATH"
    exit 1
fi

if [ -z "$DEPLOY_HOST" ] || [ -z "$DEPLOY_USER" ] || [ -z "$DEPLOY_PASSWORD" ] || [ -z "$DEPLOY_PATH" ]; then
    echo "Error: Missing required variables in .env.local"
    echo "Required: DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASSWORD, DEPLOY_PATH"
    exit 1
fi

# --- Parse arguments ---

FORCE_PULL=false
for arg in "$@"; do
    case "$arg" in
        --pull) FORCE_PULL=true ;;
        *) echo "Unknown argument: $arg"; echo "Usage: deploy.sh [--pull]"; exit 1 ;;
    esac
done

# --- SSH helpers ---

# SSH options: disable pubkey to avoid "Too many authentication failures" with many keys in agent
SSH_OPTS="-o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o PreferredAuthentications=password"

remote() {
    sshpass -p "$DEPLOY_PASSWORD" ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" "$1"
}

remote_sudo() {
    remote "echo '$DEPLOY_PASSWORD' | sudo -S bash -c '$1'"
}

# --- Step 1: Sync files ---

echo "==> Deploying bz2-video-transcriber v${VERSION}..."
echo "    Target: $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH"

echo ""
echo "==> Syncing files..."
sshpass -p "$DEPLOY_PASSWORD" rsync -avz --delete \
    -e "ssh $SSH_OPTS" \
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
    --exclude '.build_number' \
    "$PROJECT_DIR/" "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/"

# --- Step 2: Create .env on server ---

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo ""
    echo "==> Updating .env on server..."
    remote_sudo "echo ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY > ${DEPLOY_PATH}/.env"
fi

# --- Step 2.5: Increment build number ---

echo ""
echo "==> Incrementing build number..."
BUILD_NUM=$(remote "cat ${DEPLOY_PATH}/.build_number 2>/dev/null || echo 0")
BUILD_NUM=$((BUILD_NUM + 1))
remote "echo $BUILD_NUM > ${DEPLOY_PATH}/.build_number"
echo "    Version: v${VERSION} (build ${BUILD_NUM})"

# --- Step 3: Pull base images (with retry) ---

pull_image() {
    local image="$1"
    local attempt=1
    while [ $attempt -le $PULL_RETRIES ]; do
        echo "    Pulling $image (attempt $attempt/$PULL_RETRIES)..."
        if remote_sudo "docker pull $image" 2>&1; then
            return 0
        fi
        echo "    Failed to pull $image, retrying in ${PULL_RETRY_DELAY}s..."
        sleep $PULL_RETRY_DELAY
        attempt=$((attempt + 1))
    done
    echo "    ERROR: Failed to pull $image after $PULL_RETRIES attempts"
    return 1
}

if [ "$FORCE_PULL" = true ]; then
    echo ""
    echo "==> Updating base images (--pull)..."
    for image in "${BASE_IMAGES[@]}"; do
        pull_image "$image"
    done
else
    echo ""
    echo "==> Checking base images..."
    for image in "${BASE_IMAGES[@]}"; do
        if ! remote_sudo "docker image inspect $image > /dev/null 2>&1"; then
            echo "    Image $image not found, pulling..."
            pull_image "$image"
        else
            echo "    $image — OK"
        fi
    done
fi

# --- Step 4: Build ---

echo ""
echo "==> Building containers..."
BUILD_LOG=$(mktemp)
if remote_sudo "cd ${DEPLOY_PATH} && BUILD_NUMBER=$BUILD_NUM docker compose build 2>&1" > "$BUILD_LOG" 2>&1; then
    echo "    Build successful"
else
    echo "    ERROR: Build failed! Last 30 lines:"
    echo "    ---"
    tail -30 "$BUILD_LOG" | sed 's/^/    /'
    echo "    ---"
    rm -f "$BUILD_LOG"
    exit 1
fi
rm -f "$BUILD_LOG"

# --- Step 5: Start containers ---

echo ""
echo "==> Starting containers..."
remote_sudo "cd ${DEPLOY_PATH} && BUILD_NUMBER=$BUILD_NUM docker compose up -d"

# --- Step 6: Health check ---

echo ""
echo "==> Health check ($HEALTH_URL)..."
attempt=1
while [ $attempt -le $HEALTH_RETRIES ]; do
    sleep $HEALTH_RETRY_DELAY
    if curl -sf -k "$HEALTH_URL" > /dev/null 2>&1; then
        echo "    Health check passed!"
        break
    fi
    echo "    Attempt $attempt/$HEALTH_RETRIES — not ready, retrying in ${HEALTH_RETRY_DELAY}s..."
    attempt=$((attempt + 1))
done

if [ $attempt -gt $HEALTH_RETRIES ]; then
    echo "    WARNING: Health check failed after $HEALTH_RETRIES attempts"
    echo "    App may still be starting. Check manually: curl -k $HEALTH_URL"
    echo ""
    echo "    Container logs (last 20 lines):"
    remote_sudo "docker logs bz2-transcriber --tail 20 2>&1" | sed 's/^/    /' || true
fi

# --- Done ---

echo ""
echo "==> Deploy complete! v${VERSION} (build ${BUILD_NUM})"
echo "    App:    https://transcriber.home"
echo "    Health: https://transcriber.home/health"
