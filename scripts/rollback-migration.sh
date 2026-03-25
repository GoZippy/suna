#!/bin/bash
# Migration Rollback Script for Suna Self-Hosted
# This script rolls back database migrations

set -e

# Configuration
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5491}
DB_NAME=${DB_NAME:-suna}
DB_USER=${DB_USER:-suna}
DB_PASSWORD=${DB_PASSWORD:-suna_password}
ROLLBACK_STEPS=${1:-1}

echo "Starting migration rollback: $ROLLBACK_STEPS steps"

# Confirm action
read -p "⚠️  This will rollback the last $ROLLBACK_STEPS migration(s). Are you sure? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# Set PGPASSWORD environment variable
export PGPASSWORD="$DB_PASSWORD"

# Get current migration version
CURRENT_VERSION=$(psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -t \
  -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;" 2>/dev/null || echo "0")

if [ "$CURRENT_VERSION" = "0" ]; then
    echo "❌ No migrations found to rollback"
    exit 1
fi

echo "Current migration version: $CURRENT_VERSION"

# Calculate target version
TARGET_VERSION=$((CURRENT_VERSION - ROLLBACK_STEPS))
if [ $TARGET_VERSION -lt 0 ]; then
    TARGET_VERSION=0
fi

echo "Rolling back to version: $TARGET_VERSION"

# Find migrations to rollback
MIGRATIONS_TO_ROLLBACK=$(psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -t \
  -c "SELECT version, name FROM schema_migrations WHERE version > $TARGET_VERSION ORDER BY version DESC;")

if [ -z "$MIGRATIONS_TO_ROLLBACK" ]; then
    echo "❌ No migrations to rollback"
    exit 1
fi

echo "Migrations to rollback:"
echo "$MIGRATIONS_TO_ROLLBACK"

# Execute rollback for each migration
echo "$MIGRATIONS_TO_ROLLBACK" | while read -r line; do
    if [ -n "$line" ]; then
        VERSION=$(echo "$line" | cut -d'|' -f1 | tr -d ' ')
        NAME=$(echo "$line" | cut -d'|' -f2 | tr -d ' ')

        echo "Rolling back migration: $VERSION - $NAME"

        # Look for rollback file
        ROLLBACK_FILE="./backend/database/migrations/${VERSION}_${NAME}_rollback.sql"
        if [ -f "$ROLLBACK_FILE" ]; then
            echo "Executing rollback file: $ROLLBACK_FILE"
            psql \
              -h "$DB_HOST" \
              -p "$DB_PORT" \
              -U "$DB_USER" \
              -d "$DB_NAME" \
              -f "$ROLLBACK_FILE"
        else
            echo "⚠️  No rollback file found for migration $VERSION"
            # You might want to implement automatic rollback generation here
        fi

        # Remove migration record
        psql \
          -h "$DB_HOST" \
          -p "$DB_PORT" \
          -U "$DB_USER" \
          -d "$DB_NAME" \
          -c "DELETE FROM schema_migrations WHERE version = $VERSION;"
    fi
done

# Unset password
unset PGPASSWORD

echo "✅ Migration rollback completed successfully!"
echo "🔄 Rolled back $ROLLBACK_STEPS migration(s)"
echo "📊 Current version: $TARGET_VERSION"





