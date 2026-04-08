#!/usr/bin/env bash
# setup-backup-cron.sh — Install backup cron jobs on the VPS.
# Every 6 hours during registration (now through April 20)
# Every 1 hour on event day (April 21)
# Logs to /var/log/walkforpeace-backup.log
set -euo pipefail

SCRIPT_DIR="/docker/walkforpeace/scripts"
LOG_FILE="/var/log/walkforpeace-backup.log"
CRON_TAG="# walkforpeace-backup"

# Ensure AWS CLI is installed
if ! command -v aws &>/dev/null; then
    echo "Installing AWS CLI..."
    apt-get update -qq && apt-get install -y -qq awscli
    echo "AWS CLI installed."
fi

# Make backup scripts executable
chmod +x "${SCRIPT_DIR}/backup-db.sh"
chmod +x "${SCRIPT_DIR}/restore-db.sh"

# Create log file
touch "$LOG_FILE"

# Remove existing walkforpeace backup cron entries
crontab -l 2>/dev/null | grep -v "$CRON_TAG" > /tmp/cron-clean || true

# Add new cron entries
cat >> /tmp/cron-clean <<CRON

# Walk for Peace — Database backups ${CRON_TAG}
# Every 6 hours during registration period (April 8 - April 20) ${CRON_TAG}
0 */6 8-20 4 * ${SCRIPT_DIR}/backup-db.sh >> ${LOG_FILE} 2>&1 ${CRON_TAG}

# Every 1 hour on event day (April 21) ${CRON_TAG}
0 * 21 4 * ${SCRIPT_DIR}/backup-db.sh >> ${LOG_FILE} 2>&1 ${CRON_TAG}

# Daily backup at midnight for the rest of the time ${CRON_TAG}
0 0 * * * ${SCRIPT_DIR}/backup-db.sh >> ${LOG_FILE} 2>&1 ${CRON_TAG}

CRON

crontab /tmp/cron-clean
rm -f /tmp/cron-clean

echo "Cron jobs installed:"
crontab -l | grep "$CRON_TAG"
echo ""
echo "Backup log: ${LOG_FILE}"
echo "Done."
