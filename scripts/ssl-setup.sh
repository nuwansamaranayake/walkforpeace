#!/usr/bin/env bash
# =============================================================================
# Walk for Peace - SSL / Let's Encrypt Setup Script
# =============================================================================
# Obtains an SSL certificate via Let's Encrypt (certbot), configures nginx for
# HTTPS, updates docker-compose.yml to expose port 443 and mount cert volumes,
# and sets up automatic certificate renewal.
#
# Usage:  sudo ./ssl-setup.sh <domain>
# Example: sudo ./ssl-setup.sh walkforpeacelk.org
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { printf '\n\033[1;32m>>> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARN: %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Arguments and pre-flight checks
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    die "Usage: $0 <domain>  (e.g. $0 walkforpeacelk.org)"
fi

DOMAIN="$1"
WWW_DOMAIN="www.${DOMAIN}"

[[ $EUID -eq 0 ]] || die "This script must be run as root (use sudo)."

# Determine project root (parent of the scripts/ directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
NGINX_SSL_CONF="${PROJECT_DIR}/nginx/nginx-ssl.conf"
NGINX_CONF="${PROJECT_DIR}/nginx/nginx.conf"
CERTBOT_WEBROOT="/var/www/certbot"

[[ -f "${COMPOSE_FILE}" ]] || die "docker-compose.yml not found at ${COMPOSE_FILE}"
[[ -f "${NGINX_SSL_CONF}" ]] || die "nginx-ssl.conf not found at ${NGINX_SSL_CONF}"

# ---------------------------------------------------------------------------
# 1. Install certbot
# ---------------------------------------------------------------------------
log "Installing certbot"

if command -v certbot &>/dev/null; then
    warn "certbot is already installed: $(certbot --version 2>&1)"
else
    apt-get update -y
    apt-get install -y certbot
fi

# ---------------------------------------------------------------------------
# 2. Prepare webroot directory for ACME challenge
# ---------------------------------------------------------------------------
log "Preparing ACME challenge webroot: ${CERTBOT_WEBROOT}"
mkdir -p "${CERTBOT_WEBROOT}"

# ---------------------------------------------------------------------------
# 3. Stop nginx container temporarily so certbot can bind to port 80,
#    or use webroot if the stack is already running with the ACME location.
# ---------------------------------------------------------------------------
log "Obtaining SSL certificate for ${DOMAIN} and ${WWW_DOMAIN}"

# Check if docker compose is running
NGINX_RUNNING=false
if docker compose -f "${COMPOSE_FILE}" ps --status running 2>/dev/null | grep -q nginx; then
    NGINX_RUNNING=true
fi

if [[ "${NGINX_RUNNING}" == "true" ]]; then
    # nginx is running -- use webroot mode (requires the /.well-known/acme-challenge
    # location to be proxied to the certbot webroot). We add a temporary volume
    # mount if needed, but the ssl conf already has the location block.
    log "nginx is running -- attempting webroot mode"
    certbot certonly \
        --webroot \
        -w "${CERTBOT_WEBROOT}" \
        -d "${DOMAIN}" \
        -d "${WWW_DOMAIN}" \
        --non-interactive \
        --agree-tos \
        --email "admin@${DOMAIN}" \
        --keep-until-expiring
else
    # nginx is not running -- use standalone mode (certbot binds to port 80)
    log "nginx is not running -- using standalone mode"
    certbot certonly \
        --standalone \
        -d "${DOMAIN}" \
        -d "${WWW_DOMAIN}" \
        --non-interactive \
        --agree-tos \
        --email "admin@${DOMAIN}" \
        --keep-until-expiring
fi

# Verify the certificate exists
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
[[ -f "${CERT_DIR}/fullchain.pem" ]] || die "Certificate not found at ${CERT_DIR}/fullchain.pem"

log "Certificate obtained successfully at ${CERT_DIR}"

# ---------------------------------------------------------------------------
# 4. Replace nginx.conf with the SSL-enabled version
# ---------------------------------------------------------------------------
log "Replacing nginx.conf with SSL configuration"

# Update server_name directives in the SSL conf to match the provided domain
# (in case the domain differs from the hardcoded one in nginx-ssl.conf)
sed \
    -e "s/walkforpeacelk\.org/${DOMAIN}/g" \
    -e "s/www\.walkforpeacelk\.org/www.${DOMAIN}/g" \
    "${NGINX_SSL_CONF}" > "${NGINX_CONF}"

log "nginx.conf updated with SSL configuration for ${DOMAIN}"

# ---------------------------------------------------------------------------
# 5. Update docker-compose.yml to expose port 443 and mount cert volumes
# ---------------------------------------------------------------------------
log "Updating docker-compose.yml for SSL"

# Back up the original compose file
BACKUP="${COMPOSE_FILE}.pre-ssl.bak"
if [[ ! -f "${BACKUP}" ]]; then
    cp "${COMPOSE_FILE}" "${BACKUP}"
    log "Backed up original docker-compose.yml to ${BACKUP}"
fi

# Use Python (available on Ubuntu) to safely modify the YAML without breaking it
python3 <<PYEOF
import copy, sys

# Minimal YAML-safe approach: read the file, do targeted text replacements.
# We avoid importing pyyaml since it may not be installed.

compose_path = "${COMPOSE_FILE}"

with open(compose_path, 'r') as f:
    content = f.read()

# --- Add port 443 to the nginx service ---
if '"443:443"' not in content and "'443:443'" not in content and '443:443' not in content:
    # Find the nginx ports section and add 443
    content = content.replace(
        '      - "80:80"',
        '      - "80:80"\n      - "443:443"'
    )

# --- Add certificate and certbot volume mounts to nginx ---
if '/etc/letsencrypt' not in content:
    # Find the nginx volumes section and add cert mounts
    # We look for the last volume in the nginx volumes block
    content = content.replace(
        '      - uploads:/app/uploads:ro',
        '      - uploads:/app/uploads:ro\n'
        '      - /etc/letsencrypt:/etc/letsencrypt:ro\n'
        '      - /var/www/certbot:/var/www/certbot:ro'
    )

with open(compose_path, 'w') as f:
    f.write(content)

print("docker-compose.yml updated successfully.")
PYEOF

# ---------------------------------------------------------------------------
# 6. Create cron job for automatic certificate renewal
# ---------------------------------------------------------------------------
log "Setting up automatic certificate renewal cron job"

CRON_CMD="0 3 * * * certbot renew --quiet --deploy-hook 'docker compose -f ${COMPOSE_FILE} exec nginx nginx -s reload' >> /var/log/certbot-renew.log 2>&1"

# Add the cron job if it doesn't already exist
if crontab -l 2>/dev/null | grep -qF "certbot renew"; then
    warn "Certbot renewal cron job already exists. Skipping."
else
    (crontab -l 2>/dev/null || true; echo "${CRON_CMD}") | crontab -
    log "Cron job added: certificate renewal runs daily at 03:00"
fi

# ---------------------------------------------------------------------------
# 7. Restart the application stack with SSL
# ---------------------------------------------------------------------------
log "Restarting Docker Compose stack with SSL configuration"

cd "${PROJECT_DIR}"
docker compose down
docker compose up -d --build

# Wait briefly and verify nginx is healthy
sleep 5
if docker compose ps --status running 2>/dev/null | grep -q nginx; then
    log "nginx is running with SSL!"
else
    warn "nginx may not have started. Check logs with: docker compose logs nginx"
fi

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
log "SSL setup complete!"

cat <<EOF

============================================================
  SSL SETUP COMPLETE
============================================================

  Domain:       https://${DOMAIN}
  Also:         https://${WWW_DOMAIN}
  Certificate:  ${CERT_DIR}/fullchain.pem
  Key:          ${CERT_DIR}/privkey.pem

  Auto-renewal: cron runs daily at 03:00 AM

  Files modified:
    - ${NGINX_CONF}  (replaced with SSL version)
    - ${COMPOSE_FILE} (port 443 + cert volumes added)
    - Backup: ${BACKUP}

  Verify it works:
    curl -I https://${DOMAIN}

  View certificate expiry:
    certbot certificates

  Force renewal test:
    certbot renew --dry-run

============================================================
EOF
