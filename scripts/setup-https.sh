#!/bin/bash
# Setup HTTPS for bz2-video-transcriber via Traefik reverse proxy
#
# This script automates the server-side HTTPS configuration:
# 1. Generate mkcert certificate (all domains + transcriber.home)
# 2. Copy certificate to TrueNAS via scp
# 3. Add Traefik router/service in dynamic.yml via SSH
# 4. (Optional) Add DNS record in Headscale via SSH to VPS
# 5. Restart Traefik and verify HTTPS access
#
# Prerequisites:
# - mkcert installed: brew install mkcert
# - sshpass installed: brew install sshpass
# - .env.local with credentials in project root
# - Tailscale connected

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load credentials
if [ -f "$PROJECT_DIR/.env.local" ]; then
    source "$PROJECT_DIR/.env.local"
else
    echo "Error: .env.local not found in $PROJECT_DIR"
    exit 1
fi

# Configuration
DOMAIN="transcriber.home"
CERTS_DIR="$HOME/Documents/Certificates/home-lab"
TRAEFIK_CERTS_DIR="/mnt/apps-pool/docker/traefik/certs"
TRAEFIK_CONFIG_DIR="/mnt/apps-pool/docker/traefik/config"
FRONTEND_PORT=8802

# All existing domains in the certificate
EXISTING_DOMAINS="media.home cloud.home nas.home radarr.home prowlarr.home torrent.home comfyui.home grafana.home prometheus.home photos.home chat.home whisper.home"

# Headscale VPS (for DNS)
HEADSCALE_HOST="83.222.22.23"
HEADSCALE_USER="root"
HEADSCALE_CONFIG="/opt/beget/headscale/config/config.yaml"

SSH_OPTS="-o StrictHostKeyChecking=no"

ssh_server() {
    sshpass -p "$DEPLOY_PASSWORD" ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" "$1"
}

sudo_server() {
    ssh_server "echo '$DEPLOY_PASSWORD' | sudo -S bash -c '$1'"
}

echo "=== HTTPS Setup for $DOMAIN ==="
echo ""

# Step 1: Generate mkcert certificate
echo "[1/5] Generating mkcert certificate..."
if ! command -v mkcert &> /dev/null; then
    echo "Error: mkcert not installed. Run: brew install mkcert"
    exit 1
fi

mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

mkcert -cert-file cert.pem -key-file key.pem \
    $EXISTING_DOMAINS \
    "$DOMAIN" \
    home

echo "  Certificate generated: $CERTS_DIR/cert.pem"

# Step 2: Copy certificate to TrueNAS
echo "[2/5] Copying certificate to TrueNAS..."
sshpass -p "$DEPLOY_PASSWORD" scp $SSH_OPTS \
    "$CERTS_DIR/cert.pem" "$CERTS_DIR/key.pem" \
    "${DEPLOY_USER}@${DEPLOY_HOST}:/tmp/"

sudo_server "cp /tmp/cert.pem /tmp/key.pem $TRAEFIK_CERTS_DIR/ && chmod 644 $TRAEFIK_CERTS_DIR/*.pem && rm /tmp/cert.pem /tmp/key.pem"

echo "  Certificate installed to $TRAEFIK_CERTS_DIR/"

# Step 3: Add Traefik router/service
echo "[3/5] Configuring Traefik router..."

# Check if router already exists
if ssh_server "grep -q '$DOMAIN' $TRAEFIK_CONFIG_DIR/dynamic.yml 2>/dev/null"; then
    echo "  Router for $DOMAIN already exists in Traefik config, skipping."
else
    # Add router entry after existing routers
    sudo_server "cat >> /tmp/traefik-transcriber.yml << 'HEREDOC'

# --- transcriber (added by setup-https.sh) ---
# Add to http.routers:
#     transcriber:
#       rule: \"Host(\`transcriber.home\`)\"
#       entryPoints: [websecure]
#       service: transcriber
#       tls: {}
#
# Add to http.services:
#     transcriber:
#       loadBalancer:
#         servers:
#           - url: \"http://192.168.1.152:${FRONTEND_PORT}\"
HEREDOC"

    echo "  WARNING: Automatic Traefik config editing is not safe for YAML."
    echo "  Please add the following manually to $TRAEFIK_CONFIG_DIR/dynamic.yml:"
    echo ""
    echo "  In http.routers:"
    echo "    transcriber:"
    echo "      rule: \"Host(\`$DOMAIN\`)\""
    echo "      entryPoints: [websecure]"
    echo "      service: transcriber"
    echo "      tls: {}"
    echo ""
    echo "  In http.services:"
    echo "    transcriber:"
    echo "      loadBalancer:"
    echo "        servers:"
    echo "          - url: \"http://192.168.1.152:$FRONTEND_PORT\""
    echo ""
    read -p "  Press Enter after adding the config (or Ctrl+C to abort)..."
fi

# Step 4: DNS record in Headscale (optional)
echo "[4/5] DNS record in Headscale..."
read -p "  Add DNS record for $DOMAIN in Headscale? [y/N] " add_dns

if [[ "$add_dns" =~ ^[Yy]$ ]]; then
    echo "  Checking Headscale config on $HEADSCALE_HOST..."

    if ssh $SSH_OPTS "$HEADSCALE_USER@$HEADSCALE_HOST" "grep -q '$DOMAIN' $HEADSCALE_CONFIG 2>/dev/null"; then
        echo "  DNS record for $DOMAIN already exists, skipping."
    else
        echo "  Please add to $HEADSCALE_CONFIG on $HEADSCALE_HOST:"
        echo "    dns:"
        echo "      extra_records:"
        echo "        - name: \"$DOMAIN\""
        echo "          type: \"A\""
        echo "          value: \"100.64.0.1\""
        echo ""
        echo "  Then restart: cd /opt/beget/headscale && docker compose restart headscale"
        read -p "  Press Enter after adding DNS record..."
    fi
else
    echo "  Skipped. Add DNS record manually later if needed."
fi

# Step 5: Restart Traefik and verify
echo "[5/5] Restarting Traefik and verifying..."
sudo_server "docker restart traefik"
echo "  Traefik restarted. Waiting 5 seconds..."
sleep 5

echo "  Verifying HTTPS access..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://$DOMAIN" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo ""
    echo "=== HTTPS setup complete! ==="
    echo "  URL: https://$DOMAIN"
    echo "  Health: https://$DOMAIN/health"
else
    echo ""
    echo "=== HTTPS verification failed (HTTP $HTTP_CODE) ==="
    echo "  Possible issues:"
    echo "  - DNS not propagated yet (wait 1-2 min, restart Tailscale)"
    echo "  - Traefik config not applied (check dynamic.yml)"
    echo "  - Application not running (run ./scripts/deploy.sh first)"
    echo ""
    echo "  Manual check: curl -I https://$DOMAIN"
fi
