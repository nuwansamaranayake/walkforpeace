#!/usr/bin/env bash
# migrate-uploads-to-r2.sh — Upload local files to R2 and update database URLs.
# Run on VPS: ./scripts/migrate-uploads-to-r2.sh
set -euo pipefail

COMPOSE_DIR="/docker/walkforpeace"
ENV_FILE="${COMPOSE_DIR}/.env"
CONTAINER_NAME="walkforpeace-postgres-1"
DB_USER="walkforpeace"
DB_NAME="walkforpeace"

# Load R2 credentials
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

R2_ENDPOINT="${R2_ENDPOINT_URL:?R2_ENDPOINT_URL not set}"
R2_BUCKET="${R2_BUCKET_NAME:-walkforpeace-lk}"
R2_PUBLIC="${R2_PUBLIC_URL:?R2_PUBLIC_URL not set}"

export AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID:?}"
export AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY:?}"
export AWS_DEFAULT_REGION="auto"
S3_ENDPOINT="--endpoint-url ${R2_ENDPOINT}"

log() { echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] $*"; }

# Step 1: Copy files from the Docker volume to a temp dir
log "Extracting uploads from Docker volume..."
TEMP_DIR=$(mktemp -d)
docker cp walkforpeace-api-1:/app/uploads/. "$TEMP_DIR/"

FILE_COUNT=$(find "$TEMP_DIR" -type f | wc -l)
log "Found ${FILE_COUNT} files in /app/uploads/"

if [ "$FILE_COUNT" -eq 0 ]; then
    log "No files to migrate."
    rm -rf "$TEMP_DIR"
    exit 0
fi

# Step 2: Upload each file to R2
log "Uploading files to R2..."
UPLOADED=0
find "$TEMP_DIR" -type f | while read -r filepath; do
    # Get relative path (e.g., id-documents/abc123.jpg)
    relative="${filepath#${TEMP_DIR}/}"

    # Determine content type
    case "$relative" in
        *.jpg|*.jpeg) CT="image/jpeg" ;;
        *.png)        CT="image/png" ;;
        *.pdf)        CT="application/pdf" ;;
        *)            CT="application/octet-stream" ;;
    esac

    log "  Uploading: ${relative} (${CT})"
    aws s3 cp "$filepath" "s3://${R2_BUCKET}/${relative}" \
        $S3_ENDPOINT \
        --content-type "$CT" \
        --quiet
    UPLOADED=$((UPLOADED + 1))
done

log "Uploaded files to R2."

# Step 3: Update database URLs from /uploads/... to R2 public URL
log "Updating database URLs..."

# media_applications: id_document_url, face_photo_url
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
    UPDATE media_applications
    SET id_document_url = REPLACE(id_document_url, '/uploads/', '${R2_PUBLIC}/')
    WHERE id_document_url LIKE '/uploads/%';
"

docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
    UPDATE media_applications
    SET face_photo_url = REPLACE(face_photo_url, '/uploads/', '${R2_PUBLIC}/')
    WHERE face_photo_url LIKE '/uploads/%';
"

# credentials: qr_code_url, badge_pdf_url
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
    UPDATE credentials
    SET qr_code_url = REPLACE(qr_code_url, '/uploads/', '${R2_PUBLIC}/')
    WHERE qr_code_url LIKE '/uploads/%';
"

docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
    UPDATE credentials
    SET badge_pdf_url = REPLACE(badge_pdf_url, '/uploads/', '${R2_PUBLIC}/')
    WHERE badge_pdf_url LIKE '/uploads/%';
"

log "Database URLs updated."

# Step 4: Verify
log "Verifying updated URLs..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT 'id_document_url: ' || COALESCE(id_document_url, 'NULL') FROM media_applications;
"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT 'face_photo_url: ' || COALESCE(face_photo_url, 'NULL') FROM media_applications;
"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT 'qr_code_url: ' || COALESCE(qr_code_url, 'NULL') FROM credentials;
"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT 'badge_pdf_url: ' || COALESCE(badge_pdf_url, 'NULL') FROM credentials;
"

# Cleanup
rm -rf "$TEMP_DIR"
log "Migration complete. All local uploads are now on R2."
