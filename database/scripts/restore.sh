#!/bin/bash

# Suna Database Restore Script
# This script restores a PostgreSQL database from a backup file

set -e

# Configuration
BACKUP_DIR="/backups"
DB_NAME="${POSTGRES_DB:-suna}"
DB_USER="${POSTGRES_USER:-suna_user}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] <backup_file>"
    echo "Options:"
    echo "  -f, --force     Force restore without confirmation"
    echo "  -l, --list      List available backup files"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 suna_backup_20240101_120000.sql.gz"
    echo "  $0 --list"
    echo "  $0 --force /path/to/backup.sql.gz"
}

# Function to list available backups
list_backups() {
    echo "Available backup files in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/suna_backup_*.sql.gz 2>/dev/null || echo "No backup files found"
}

# Parse command line arguments
FORCE=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option $1"
            usage
            exit 1
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Check if backup file is provided
if [ -z "$BACKUP_FILE" ]; then
    echo "ERROR: No backup file specified"
    usage
    exit 1
fi

# If backup file doesn't contain path, assume it's in backup directory
if [[ "$BACKUP_FILE" != /* ]]; then
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    list_backups
    exit 1
fi

# Confirmation prompt unless force flag is used
if [ "$FORCE" = false ]; then
    echo "WARNING: This will completely replace the current database!"
    echo "Database: $DB_NAME"
    echo "Backup file: $BACKUP_FILE"
    echo "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
    echo "Backup date: $(stat -c %y "$BACKUP_FILE")"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Restore cancelled"
        exit 0
    fi
fi

echo "Starting database restore at $(date)"
echo "Restoring from: $BACKUP_FILE"

# Test database connection
echo "Testing database connection..."
PGPASSWORD="$POSTGRES_PASSWORD" psql \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="postgres" \
    --command="SELECT version();" > /dev/null

echo "Database connection successful"

# Restore database from backup
echo "Restoring database..."
gunzip -c "$BACKUP_FILE" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="postgres" \
    --quiet

# Verify restore
echo "Verifying restore..."
TABLE_COUNT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --tuples-only \
    --command="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

echo "Restored database contains $TABLE_COUNT tables"

# Check if extensions are properly installed
EXTENSIONS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --tuples-only \
    --command="SELECT string_agg(extname, ', ') FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector', 'pg_trgm');")

echo "Installed extensions: $EXTENSIONS"

echo "Database restore completed successfully at $(date)"