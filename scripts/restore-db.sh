#!/usr/bin/env bash
# restore-db.sh — Download a backup from R2 and restore into PostgreSQL.
# Usage:
#   ./scripts/restore-db.sh                     # restores the latest backup
#   ./scripts/restore-db.sh <backup-key>        # restores a specific backup
#   ./scripts/restore-db.sh --list              # list available backups
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────
COMPOSE_DIR="/docker/walkforpeace"
ENV_FILE="${COMPOSE_DIR}/.env"
CONTAINER_NAME="walkforpeace-postgres-1"
DB_USER="walkforpeace"
DB_NAME="walkforpeace"
BACKUP_PREFIX="backups"

# Load R2 credentials from .env
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

R2_ENDPOINT="${R2_ENDPOINT_URL:?R2_ENDPOINT_URL not set}"
R2_KEY="${R2_ACCESS_KEY_ID:?R2_ACCESS_KEY_ID not set}"
R2_SECRET="${R2_SECRET_ACCESS_KEY:?R2_SECRET_ACCESS_KEY not set}"
R2_BUCKET="${R2_BUCKET_NAME:-walkforpeace-lk}"

export AWS_ACCESS_KEY_ID="$R2_KEY"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET"
export AWS_DEFAULT_REGION="auto"

S3_ENDPOINT="--endpoint-url ${R2_ENDPOINT}"

log() { echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] $*"; }

# ─── List mode ────────────────────────────────────────────────────────
if [ "${1:-}" = "--list" ]; then
    echo "Available backups in s3://${R2_BUCKET}/${BACKUP_PREFIX}/:"
    echo "────────────────────────────────────────────────────────"
    aws s3api list-objects-v2 \
        $S3_ENDPOINT \
        --bucket "$R2_BUCKET" \
        --prefix "${BACKUP_PREFIX}/" \
        --query "Contents[].{Key:Key,Size:Size,LastModified:LastModified}" \
        --output table 2>/dev/null || echo "No backups found."
    exit 0
fi

# ─── Determine which backup to restore ────────────────────────────────
if [ -n "${1:-}" ]; then
    BACKUP_KEY="$1"
    log "Using specified backup: ${BACKUP_KEY}"
else
    log "Finding latest backup..."
    BACKUP_KEY=$(aws s3api list-objects-v2 \
        $S3_ENDPOINT \
        --bucket "$R2_BUCKET" \
        --prefix "${BACKUP_PREFIX}/" \
        --query "Contents | sort_by(@, &LastModified) | [-1].Key" \
        --output text 2>/dev/null)

    if [ -z "$BACKUP_KEY" ] || [ "$BACKUP_KEY" = "None" ]; then
        log "ERROR: No backups found in s3://${R2_BUCKET}/${BACKUP_PREFIX}/"
        exit 1
    fi
    log "Latest backup: ${BACKUP_KEY}"
fi

# ─── Download ─────────────────────────────────────────────────────────
RESTORE_FILE="/tmp/walkforpeace-restore.sql.gz"
log "Downloading s3://${R2_BUCKET}/${BACKUP_KEY}..."
aws s3 cp "s3://${R2_BUCKET}/${BACKUP_KEY}" "$RESTORE_FILE" \
    $S3_ENDPOINT --quiet

RESTORE_SIZE=$(stat -c%s "$RESTORE_FILE" 2>/dev/null || stat -f%z "$RESTORE_FILE")
RESTORE_SIZE_HR=$(numfmt --to=iec "$RESTORE_SIZE" 2>/dev/null || echo "${RESTORE_SIZE} bytes")
log "Downloaded: ${RESTORE_SIZE_HR}"

# ─── Confirm ─────────────────────────────────────────────────────────
echo ""
echo "  WARNING: This will DROP and RECREATE all tables in database '${DB_NAME}'."
echo "  Backup: ${BACKUP_KEY}"
echo "  Size:   ${RESTORE_SIZE_HR}"
echo ""
read -p "  Continue? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Restore cancelled."
    rm -f "$RESTORE_FILE"
    exit 0
fi

# ─── Restore ──────────────────────────────────────────────────────────
log "Stopping API container to prevent connections..."
docker stop walkforpeace-api-1 2>/dev/null || true

log "Dropping and recreating database..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();
"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

log "Restoring from dump..."
gunzip -c "$RESTORE_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" --quiet

log "Cleaning up..."
rm -f "$RESTORE_FILE"

# ─── Verify ──────────────────────────────────────────────────────────
log "Verifying restored tables..."
TABLES=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' ORDER BY table_name;
" | sed '/^$/d' | sed 's/^ *//')

EXPECTED_TABLES=("admin_users" "alembic_version" "credentials" "media_applications" "verification_logs" "verify_sessions")
MISSING=()

echo ""
echo "  Restored tables:"
for t in $TABLES; do
    echo "    [OK] $t"
done

for expected in "${EXPECTED_TABLES[@]}"; do
    if ! echo "$TABLES" | grep -q "^${expected}$"; then
        MISSING+=("$expected")
    fi
done

echo ""
if [ ${#MISSING[@]} -eq 0 ]; then
    log "All expected tables present. Restore verified."
else
    log "WARNING: Missing tables: ${MISSING[*]}"
    log "The application's init_db() will create missing tables on startup."
fi

# ─── Restart API ──────────────────────────────────────────────────────
log "Starting API container..."
docker start walkforpeace-api-1
log "Restore complete."

# Record counts
echo ""
echo "  Record counts:"
for t in $TABLES; do
    COUNT=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT count(*) FROM ${t};" 2>/dev/null | tr -d ' ')
    echo "    ${t}: ${COUNT} rows"
done
echo ""
