#!/bin/bash
# Database Restore Script for Suna Self-Hosted
# This script restores the PostgreSQL database from backup

set -e

# Configuration
BACKUP_DIR="./backups"
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5491}
DB_NAME=${DB_NAME:-suna}
DB_USER=${DB_USER:-suna}
DB_PASSWORD=${DB_PASSWORD:-suna_password}

# Check if backup file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/*.backup 2>/dev/null || echo "No backup files found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    # Try with backup directory prefix
    if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        echo "❌ Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

echo "Starting database restore from: $BACKUP_FILE"

# Confirm action
read -p "⚠️  This will overwrite the current database. Are you sure? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Set PGPASSWORD environment variable
export PGPASSWORD="$DB_PASSWORD"

# Terminate active connections to the database
echo "Terminating active connections..."
psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();"

# Drop and recreate database
echo "Dropping and recreating database..."
psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d postgres \
  -c "DROP DATABASE IF EXISTS $DB_NAME;"

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d postgres \
  -c "CREATE DATABASE $DB_NAME;"

# Restore from backup
echo "Restoring database from backup..."
pg_restore \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --clean \
  --if-exists \
  --create \
  --exit-on-error \
  "$BACKUP_FILE"

# Run post-restore migrations if needed
echo "Running post-restore migrations..."
# Add migration commands here if needed

# Unset password
unset PGPASSWORD

echo "✅ Database restore completed successfully!"
echo "🔄 Database: $DB_NAME"
echo "📁 Backup file: $BACKUP_FILE"
echo "🌐 Host: $DB_HOST:$DB_PORT"





