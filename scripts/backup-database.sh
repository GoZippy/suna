#!/bin/bash
# Database Backup Script for Suna Self-Hosted
# This script creates backups of the PostgreSQL database

set -e

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="suna_backup_${TIMESTAMP}"
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5491}
DB_NAME=${DB_NAME:-suna}
DB_USER=${DB_USER:-suna}
DB_PASSWORD=${DB_PASSWORD:-suna_password}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting database backup: $BACKUP_NAME"

# Set PGPASSWORD environment variable
export PGPASSWORD="$DB_PASSWORD"

# Create database dump
pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  --compress=9 \
  --format=custom \
  --file="$BACKUP_DIR/${BACKUP_NAME}.backup"

# Create compressed SQL dump as well
pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  | gzip > "$BACKUP_DIR/${BACKUP_NAME}.sql.gz"

# Create metadata file
cat > "$BACKUP_DIR/${BACKUP_NAME}.meta" << EOF
BACKUP_TIMESTAMP=$TIMESTAMP
DATABASE_HOST=$DB_HOST
DATABASE_PORT=$DB_PORT
DATABASE_NAME=$DB_NAME
BACKUP_TYPE=full
COMPRESSION=gzip+custom
CREATED_BY=backup-script
EOF

# Clean up old backups (keep last 30 days)
find "$BACKUP_DIR" -name "*.backup" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.meta" -mtime +30 -delete

echo "✅ Database backup completed: $BACKUP_DIR/${BACKUP_NAME}"
echo "📊 Backup size: $(du -sh "$BACKUP_DIR/${BACKUP_NAME}.backup" | cut -f1)"
echo "📊 Compressed size: $(du -sh "$BACKUP_DIR/${BACKUP_NAME}.sql.gz" | cut -f1)"

# Unset password
unset PGPASSWORD

echo "🎉 Backup process completed successfully!"





