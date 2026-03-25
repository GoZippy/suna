# Suna Self-Hosted Migration Tools

This directory contains tools and scripts for migrating from Supabase-based Suna installations to the new self-hosted PostgreSQL-based system.

## Overview

The migration process involves:
1. **Data Export**: Extracting data from Supabase
2. **Schema Migration**: Converting Supabase schemas to PostgreSQL
3. **Data Import**: Loading data into the new PostgreSQL database
4. **Configuration Migration**: Converting external service configs to local
5. **Validation**: Ensuring data integrity and completeness
6. **Rollback**: Procedures for reverting if needed

## Prerequisites

- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- Supabase CLI (for data export)
- Access to source Supabase project
- Target PostgreSQL database running

## Quick Start

```bash
# 1. Export data from Supabase
python migration/export_supabase.py --project-ref your-project-ref

# 2. Import data to PostgreSQL
python migration/import_postgresql.py --target-db postgresql://user:pass@localhost:5491/suna

# 3. Validate migration
python migration/validate_migration.py --source-db supabase --target-db postgresql://user:pass@localhost:5491/suna

# 4. Run configuration migration
python migration/migrate_config.py --config-file config.json
```

## Migration Components

### 1. Data Export (`export_supabase.py`)
- Exports all tables from Supabase
- Handles RLS policies and permissions
- Exports file storage metadata
- Creates backup of current state

### 2. Schema Migration (`migrate_schema.py`)
- Converts Supabase schemas to PostgreSQL
- Handles pgvector extensions
- Sets up proper indexes and constraints
- Creates RLS policies for PostgreSQL

### 3. Data Import (`import_postgresql.py`)
- Imports exported data to PostgreSQL
- Handles data type conversions
- Validates foreign key relationships
- Creates proper sequences and IDs

### 4. Configuration Migration (`migrate_config.py`)
- Converts external service configs to local
- Updates API endpoints and URLs
- Migrates authentication settings
- Updates file storage paths

### 5. Validation (`validate_migration.py`)
- Compares source and target data
- Validates data integrity
- Checks for missing or corrupted data
- Generates migration report

### 6. Backup & Restore (`backup_restore.py`)
- Creates database backups
- Implements point-in-time recovery
- Handles incremental backups
- Provides restore procedures

## Configuration

Create a `migration_config.json` file:

```json
{
  "source": {
    "type": "supabase",
    "project_ref": "your-project-ref",
    "api_key": "your-api-key",
    "url": "https://your-project.supabase.co"
  },
  "target": {
    "type": "postgresql",
    "connection_string": "postgresql://user:pass@localhost:5491/suna",
    "schema": "public"
  },
  "options": {
    "backup_before_migration": true,
    "validate_after_import": true,
    "create_rollback_point": true,
    "parallel_import": true
  }
}
```

## Safety Features

- **Backup Creation**: Automatic backup before migration
- **Validation**: Data integrity checks at each step
- **Rollback Points**: Ability to revert changes
- **Dry Run**: Test migration without making changes
- **Progress Tracking**: Detailed logging and progress reporting

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check database credentials and network connectivity
2. **Permission Errors**: Ensure proper database permissions
3. **Data Type Mismatches**: Review schema conversion logs
4. **Memory Issues**: Use batch processing for large datasets

### Recovery Procedures

```bash
# Rollback to previous state
python migration/rollback.py --backup-file backup_2024-01-01.sql

# Validate current state
python migration/validate_migration.py --detailed

# Repair corrupted data
python migration/repair_data.py --table users
```

## Performance Considerations

- Use batch processing for large datasets
- Enable parallel imports where possible
- Monitor memory usage during migration
- Use appropriate indexes for validation queries

## Security Notes

- Store credentials securely (use environment variables)
- Encrypt backup files
- Validate all input data
- Use secure connections for database access
- Audit migration logs for security events







