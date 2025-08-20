#!/bin/bash

# Suna Database Backup Script
# This script creates compressed backups of the PostgreSQL database

set -e

# Configuration
BACKUP_DIR="/backups"
DB_NAME="${POSTGRES_DB:-suna}"
DB_USER="${POSTGRES_USER:-suna_user}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp for backup filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/suna_backup_$TIMESTAMP.sql.gz"

echo "Starting database backup at $(date)"
echo "Backup file: $BACKUP_FILE"

# Create compressed backup
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --verbose \
    --clean \
    --if-exists \
    --create \
    --format=plain \
    --no-owner \
    --no-privileges | gzip > "$BACKUP_FILE"

# Verify backup was created successfully
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
    echo "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    echo "ERROR: Backup failed or file is empty"
    exit 1
fi

# Clean up old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "suna_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

# List remaining backups
echo "Current backups:"
ls -lh "$BACKUP_DIR"/suna_backup_*.sql.gz 2>/dev/null || echo "No backups found"

echo "Backup process completed at $(date)"