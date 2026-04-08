#!/usr/bin/env bash
# backup-db.sh — Dump PostgreSQL, compress, upload to Cloudflare R2, prune old backups.
# Usage: ./scripts/backup-db.sh
# Requires: aws CLI configured for R2, docker access
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────
COMPOSE_DIR="/docker/walkforpeace"
ENV_FILE="${COMPOSE_DIR}/.env"
STATUS_FILE="${COMPOSE_DIR}/backup-status.json"
CONTAINER_NAME="walkforpeace-postgres-1"
DB_USER="walkforpeace"
DB_NAME="walkforpeace"
KEEP_BACKUPS=30
BACKUP_PREFIX="backups"
TIMESTAMP=$(date -u +"%Y-%m-%d-%H%M%S")
DUMP_FILE="/tmp/walkforpeace-${TIMESTAMP}.sql.gz"

# Load R2 credentials from .env
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

R2_ENDPOINT="${R2_ENDPOINT_URL:?R2_ENDPOINT_URL not set in ${ENV_FILE}}"
R2_KEY="${R2_ACCESS_KEY_ID:?R2_ACCESS_KEY_ID not set in ${ENV_FILE}}"
R2_SECRET="${R2_SECRET_ACCESS_KEY:?R2_SECRET_ACCESS_KEY not set in ${ENV_FILE}}"
R2_BUCKET="${R2_BUCKET_NAME:-walkforpeace-lk}"

export AWS_ACCESS_KEY_ID="$R2_KEY"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET"
export AWS_DEFAULT_REGION="auto"

S3_ENDPOINT="--endpoint-url ${R2_ENDPOINT}"
R2_KEY_NAME="${BACKUP_PREFIX}/walkforpeace-${TIMESTAMP}.sql.gz"

log() { echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] $*"; }

# ─── Step 1: pg_dump ─────────────────────────────────────────────────
log "Starting database backup..."
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl \
    | gzip -9 > "$DUMP_FILE"

DUMP_SIZE=$(stat -c%s "$DUMP_FILE" 2>/dev/null || stat -f%z "$DUMP_FILE")
DUMP_SIZE_HR=$(numfmt --to=iec "$DUMP_SIZE" 2>/dev/null || echo "${DUMP_SIZE} bytes")
log "Dump complete: ${DUMP_FILE} (${DUMP_SIZE_HR})"

# ─── Step 2: Upload to R2 ────────────────────────────────────────────
log "Uploading to R2: s3://${R2_BUCKET}/${R2_KEY_NAME}"
aws s3 cp "$DUMP_FILE" "s3://${R2_BUCKET}/${R2_KEY_NAME}" \
    $S3_ENDPOINT \
    --content-type "application/gzip" \
    --quiet

log "Upload complete."

# ─── Step 3: Clean up local dump ─────────────────────────────────────
rm -f "$DUMP_FILE"
log "Local dump removed."

# ─── Step 4: Prune old backups (keep last $KEEP_BACKUPS) ─────────────
log "Pruning old backups (keeping last ${KEEP_BACKUPS})..."

# List all backups sorted by key name (which includes timestamp, so alphabetical = chronological)
ALL_BACKUPS=$(aws s3api list-objects-v2 \
    $S3_ENDPOINT \
    --bucket "$R2_BUCKET" \
    --prefix "${BACKUP_PREFIX}/" \
    --query "Contents[].Key" \
    --output text 2>/dev/null | tr '\t' '\n' | sort)

BACKUP_COUNT=$(echo "$ALL_BACKUPS" | grep -c . || true)

if [ "$BACKUP_COUNT" -gt "$KEEP_BACKUPS" ]; then
    DELETE_COUNT=$((BACKUP_COUNT - KEEP_BACKUPS))
    TO_DELETE=$(echo "$ALL_BACKUPS" | head -n "$DELETE_COUNT")
    for key in $TO_DELETE; do
        log "  Deleting old backup: ${key}"
        aws s3 rm "s3://${R2_BUCKET}/${key}" $S3_ENDPOINT --quiet
    done
    log "Pruned ${DELETE_COUNT} old backup(s)."
else
    log "No pruning needed (${BACKUP_COUNT}/${KEEP_BACKUPS} backups)."
fi

# ─── Step 5: Write status file ───────────────────────────────────────
cat > "$STATUS_FILE" <<STATUSEOF
{
    "last_backup_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "last_backup_size": ${DUMP_SIZE},
    "last_backup_size_hr": "${DUMP_SIZE_HR}",
    "last_backup_key": "${R2_KEY_NAME}",
    "total_backups": $((BACKUP_COUNT > KEEP_BACKUPS ? KEEP_BACKUPS : BACKUP_COUNT)),
    "status": "success"
}
STATUSEOF

log "Backup complete. Status written to ${STATUS_FILE}"
log "Key: ${R2_KEY_NAME} | Size: ${DUMP_SIZE_HR} | Total: ${BACKUP_COUNT} backups"
