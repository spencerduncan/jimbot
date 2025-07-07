#!/bin/bash
# Rollback script for JimBot deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
VERSION=${1:-"previous"}
DRY_RUN=${2:-false}

echo -e "${YELLOW}Rolling back JimBot to version: $VERSION${NC}"

# Check if backup exists
BACKUP_DIR="./backups"
if [[ "$VERSION" == "previous" ]]; then
    # Find the most recent backup
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -n 2 | tail -n 1)
    if [[ -z "$BACKUP_FILE" ]]; then
        echo -e "${RED}Error: No previous backup found${NC}"
        exit 1
    fi
else
    BACKUP_FILE="$BACKUP_DIR/jimbot-backup-$VERSION.tar.gz"
    if [[ ! -f "$BACKUP_FILE" ]]; then
        echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
        exit 1
    fi
fi

echo "Using backup: $BACKUP_FILE"

# Confirmation prompt
if [[ "$DRY_RUN" != "true" ]]; then
    echo -e "${YELLOW}Warning: This will replace the current deployment!${NC}"
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo "Rollback cancelled"
        exit 0
    fi
fi

# Create rollback directory
ROLLBACK_DIR="./rollback-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ROLLBACK_DIR"

# Extract backup
echo "Extracting backup..."
tar -xzf "$BACKUP_FILE" -C "$ROLLBACK_DIR"

# Stop current services
echo "Stopping current services..."
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] docker compose down"
else
    docker compose down
fi

# Backup current state (just in case)
echo "Backing up current state..."
if [[ "$DRY_RUN" != "true" ]]; then
    ./scripts/backup.sh "pre-rollback"
fi

# Restore Docker images
if [[ -f "$ROLLBACK_DIR/images.tar" ]]; then
    echo "Loading Docker images..."
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] docker load < $ROLLBACK_DIR/images.tar"
    else
        docker load < "$ROLLBACK_DIR/images.tar"
    fi
fi

# Restore volumes
echo "Restoring data volumes..."
for volume in memgraph_data questdb_data eventstore_data redis_data; do
    if [[ -f "$ROLLBACK_DIR/volumes/$volume.tar" ]]; then
        echo "Restoring $volume..."
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Restore $volume"
        else
            # Remove existing volume
            docker volume rm "jimbot_$volume" 2>/dev/null || true
            
            # Create new volume
            docker volume create "jimbot_$volume"
            
            # Restore data
            docker run --rm -v "jimbot_$volume:/restore" -v "$ROLLBACK_DIR/volumes:/backup" \
                alpine tar -xf "/backup/$volume.tar" -C /restore
        fi
    fi
done

# Restore configuration
if [[ -f "$ROLLBACK_DIR/config/.env" ]]; then
    echo "Restoring configuration..."
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] cp $ROLLBACK_DIR/config/.env .env"
    else
        cp "$ROLLBACK_DIR/config/.env" .env
    fi
fi

# Restore model checkpoints
if [[ -d "$ROLLBACK_DIR/checkpoints" ]]; then
    echo "Restoring model checkpoints..."
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Restore checkpoints"
    else
        rm -rf ./checkpoints
        cp -r "$ROLLBACK_DIR/checkpoints" ./
    fi
fi

# Start services with rolled back version
echo "Starting services..."
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] ./scripts/deploy.sh --no-build"
else
    ./scripts/deploy.sh --no-build
fi

# Verify rollback
echo "Verifying rollback..."
if [[ "$DRY_RUN" != "true" ]]; then
    sleep 30  # Wait for services to stabilize
    ./scripts/health.sh all
    
    # Run smoke tests
    ./scripts/smoke-test.sh
fi

# Clean up
echo "Cleaning up..."
if [[ "$DRY_RUN" != "true" && -d "$ROLLBACK_DIR" ]]; then
    rm -rf "$ROLLBACK_DIR"
fi

echo -e "${GREEN}Rollback completed successfully!${NC}"

# Log rollback event
if [[ "$DRY_RUN" != "true" ]]; then
    echo "$(date): Rolled back to $VERSION from $BACKUP_FILE" >> ./logs/rollback.log
fi