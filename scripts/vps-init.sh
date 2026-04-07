#!/usr/bin/env bash
# =============================================================================
# Walk for Peace - VPS Initialization Script
# =============================================================================
# Prepares a fresh Ubuntu 22.04/24.04 VPS for running the Walk for Peace
# application stack (FastAPI + React + PostgreSQL via Docker Compose).
#
# Usage:  sudo ./vps-init.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { printf '\n\033[1;32m>>> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARN: %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
[[ $EUID -eq 0 ]] || die "This script must be run as root (use sudo)."

# Ensure we are on a supported Ubuntu release
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    if [[ "${ID:-}" != "ubuntu" ]]; then
        warn "This script is designed for Ubuntu. Detected: ${ID}. Proceeding anyway."
    fi
else
    warn "Cannot detect OS. Proceeding anyway."
fi

# ---------------------------------------------------------------------------
# 1. System updates
# ---------------------------------------------------------------------------
log "Updating system packages"
apt-get update -y
apt-get upgrade -y

# ---------------------------------------------------------------------------
# 2. Install Docker (official repository)
# ---------------------------------------------------------------------------
log "Installing Docker Engine and Docker Compose plugin"

# Install prerequisites
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker GPG key
install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
fi

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify Docker is working
docker --version || die "Docker installation failed."
docker compose version || die "Docker Compose plugin installation failed."

# Enable Docker to start on boot
systemctl enable docker
systemctl start docker

# ---------------------------------------------------------------------------
# 3. Create deploy user
# ---------------------------------------------------------------------------
DEPLOY_USER="deploy"

log "Creating deploy user: ${DEPLOY_USER}"

if id "${DEPLOY_USER}" &>/dev/null; then
    warn "User '${DEPLOY_USER}' already exists. Ensuring docker group membership."
else
    adduser --disabled-password --gecos "Deploy User" "${DEPLOY_USER}"
fi

# Add to docker group so the user can run docker without sudo
usermod -aG docker "${DEPLOY_USER}"

# ---------------------------------------------------------------------------
# 4. Configure UFW firewall
# ---------------------------------------------------------------------------
log "Configuring UFW firewall (allow SSH, HTTP, HTTPS)"

apt-get install -y ufw

# Allow SSH first so we don't lock ourselves out
ufw allow 22/tcp   comment "SSH"
ufw allow 80/tcp   comment "HTTP"
ufw allow 443/tcp  comment "HTTPS"

# Enable UFW (--force to avoid the interactive prompt)
ufw --force enable
ufw status verbose

# ---------------------------------------------------------------------------
# 5. Create project directory
# ---------------------------------------------------------------------------
APP_DIR="/opt/walkforpeace"

log "Creating project directory: ${APP_DIR}"

mkdir -p "${APP_DIR}"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_DIR}"
chmod 755 "${APP_DIR}"

# ---------------------------------------------------------------------------
# 6. Create systemd service for Docker Compose
# ---------------------------------------------------------------------------
log "Creating systemd service: walkforpeace.service"

cat > /etc/systemd/system/walkforpeace.service <<'UNIT'
[Unit]
Description=Walk for Peace Application Stack (Docker Compose)
Documentation=https://github.com/walkforpeace
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=deploy
WorkingDirectory=/opt/walkforpeace
ExecStart=/usr/bin/docker compose up -d --build --remove-orphans
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose up -d --build --remove-orphans
Restart=on-failure
RestartSec=10
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable walkforpeace.service

# ---------------------------------------------------------------------------
# 7. Summary and next steps
# ---------------------------------------------------------------------------
log "VPS initialization complete!"

cat <<EOF

============================================================
  NEXT STEPS
============================================================

1. Copy your project files to ${APP_DIR}:
     scp -r ./* ${DEPLOY_USER}@<VPS_IP>:${APP_DIR}/

2. Create the .env file:
     cp ${APP_DIR}/.env.example ${APP_DIR}/.env
     nano ${APP_DIR}/.env

   At minimum, set these production values:
     - DB_PASSWORD          (strong random password)
     - JWT_SECRET           (strong random secret)
     - CREDENTIAL_SECRET    (strong random secret)
     - APP_URL              (https://walkforpeacelk.org)
     - ENVIRONMENT          (production)
     - ADMIN_DEFAULT_PASSWORD (strong admin password)
     - SMTP_* variables     (for email delivery)
     - R2_* variables       (for media storage)

3. Start the application:
     sudo systemctl start walkforpeace
     # or: cd ${APP_DIR} && docker compose up -d --build

4. Set up SSL with Let's Encrypt:
     cd ${APP_DIR}/scripts && sudo ./ssl-setup.sh walkforpeacelk.org

5. (Optional) Set up SSH key for the deploy user:
     ssh-copy-id ${DEPLOY_USER}@<VPS_IP>

============================================================
EOF
