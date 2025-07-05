#!/bin/bash
# Backup script for JimBot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TAG=${1:-$TIMESTAMP}
BACKUP_NAME="jimbot-backup-$TAG"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME.tar.gz"

echo -e "${GREEN}Creating JimBot backup: $BACKUP_NAME${NC}"

# Create backup directory
mkdir -p "$BACKUP_DIR"
TEMP_DIR=$(mktemp -d)

# Function to check if service is running
is_running() {
    docker ps --format "{{.Names}}" | grep -q "^$1$"
}

# Backup Docker volumes
echo "Backing up Docker volumes..."
mkdir -p "$TEMP_DIR/volumes"

for volume in memgraph_data questdb_data eventstore_data redis_data; do
    if docker volume ls --format "{{.Name}}" | grep -q "jimbot_$volume"; then
        echo "  - Backing up $volume..."
        docker run --rm -v "jimbot_$volume:/data" -v "$TEMP_DIR/volumes:/backup" \
            alpine tar -cf "/backup/$volume.tar" -C /data .
    fi
done

# Backup configuration
echo "Backing up configuration..."
mkdir -p "$TEMP_DIR/config"
cp .env "$TEMP_DIR/config/" 2>/dev/null || echo "  - No .env file found"
cp docker-compose.yml "$TEMP_DIR/config/"
cp -r scripts "$TEMP_DIR/config/" 2>/dev/null || true

# Backup model checkpoints
echo "Backing up model checkpoints..."
if [[ -d "./checkpoints" ]]; then
    cp -r ./checkpoints "$TEMP_DIR/"
else
    echo "  - No checkpoints directory found"
fi

# Export Docker images (optional, can be large)
if [[ "$INCLUDE_IMAGES" == "true" ]]; then
    echo "Exporting Docker images..."
    images=$(docker compose config | grep "image:" | awk '{print $2}' | sort -u)
    docker save $images > "$TEMP_DIR/images.tar"
fi

# Backup Memgraph schema and data
if is_running "jimbot-memgraph"; then
    echo "Backing up Memgraph schema..."
    docker exec jimbot-memgraph sh -c "echo 'CALL mg.dump_all();' | mgconsole" > "$TEMP_DIR/memgraph_dump.cypher" 2>/dev/null || \
        echo "  - Could not dump Memgraph data"
fi

# Create backup metadata
echo "Creating backup metadata..."
cat > "$TEMP_DIR/metadata.json" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "tag": "$TAG",
    "version": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "services": $(docker compose ps --format json 2>/dev/null || echo '[]'),
    "host": "$(hostname)",
    "backup_size": "$(du -sh $TEMP_DIR | cut -f1)"
}
EOF

# Create tarball
echo "Creating backup archive..."
tar -czf "$BACKUP_PATH" -C "$TEMP_DIR" .

# Clean up
rm -rf "$TEMP_DIR"

# Show backup info
BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo -e "${GREEN}Backup created successfully!${NC}"
echo "  - Path: $BACKUP_PATH"
echo "  - Size: $BACKUP_SIZE"

# Cleanup old backups (keep last 7 by default)
KEEP_BACKUPS=${BACKUP_RETENTION:-7}
echo "Cleaning up old backups (keeping last $KEEP_BACKUPS)..."
ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -n +$((KEEP_BACKUPS + 1)) | xargs -r rm -f

# Upload to S3 if configured
if [[ -n "$BACKUP_S3_BUCKET" ]]; then
    echo "Uploading to S3..."
    aws s3 cp "$BACKUP_PATH" "s3://$BACKUP_S3_BUCKET/jimbot-backups/" || \
        echo -e "${YELLOW}Warning: S3 upload failed${NC}"
fi

echo -e "${GREEN}Backup completed!${NC}"