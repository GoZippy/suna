#!/usr/bin/env python3
"""
Suna Database Migration Script
Handles database schema migrations and version management
"""

import os
import sys
import psycopg2
import argparse
from pathlib import Path
from datetime import datetime
import hashlib
import json

class DatabaseMigrator:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.migrations_dir = Path(__file__).parent.parent / 'migrations'
        self.migrations_dir.mkdir(exist_ok=True)
        
    def connect(self):
        """Create database connection"""
        return psycopg2.connect(self.db_url)
    
    def ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        checksum VARCHAR(64) NOT NULL,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        execution_time_ms INTEGER
                    )
                """)
                conn.commit()
    
    def get_applied_migrations(self):
        """Get list of applied migrations"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT version, name, checksum, applied_at 
                    FROM schema_migrations 
                    ORDER BY version
                """)
                return cur.fetchall()
    
    def get_pending_migrations(self):
        """Get list of pending migrations"""
        applied = {row[0] for row in self.get_applied_migrations()}
        
        pending = []
        for migration_file in sorted(self.migrations_dir.glob('*.sql')):
            version = migration_file.stem
            if version not in applied:
                pending.append(migration_file)
        
        return pending
    
    def calculate_checksum(self, content):
        """Calculate SHA-256 checksum of migration content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def apply_migration(self, migration_file):
        """Apply a single migration"""
        version = migration_file.stem
        content = migration_file.read_text(encoding='utf-8')
        checksum = self.calculate_checksum(content)
        
        print(f"Applying migration: {version}")
        
        start_time = datetime.now()
        
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    # Execute migration
                    cur.execute(content)
                    
                    # Record migration
                    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    cur.execute("""
                        INSERT INTO schema_migrations (version, name, checksum, execution_time_ms)
                        VALUES (%s, %s, %s, %s)
                    """, (version, migration_file.name, checksum, execution_time))
                    
                    conn.commit()
                    print(f"✓ Migration {version} applied successfully ({execution_time}ms)")
                    
                except Exception as e:
                    conn.rollback()
                    print(f"✗ Migration {version} failed: {e}")
                    raise
    
    def migrate(self):
        """Apply all pending migrations"""
        self.ensure_migrations_table()
        
        pending = self.get_pending_migrations()
        if not pending:
            print("No pending migrations")
            return
        
        print(f"Found {len(pending)} pending migrations")
        
        for migration_file in pending:
            self.apply_migration(migration_file)
        
        print("All migrations applied successfully")
    
    def status(self):
        """Show migration status"""
        self.ensure_migrations_table()
        
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print(f"Applied migrations: {len(applied)}")
        for version, name, checksum, applied_at in applied:
            print(f"  ✓ {version} - {name} ({applied_at})")
        
        print(f"\nPending migrations: {len(pending)}")
        for migration_file in pending:
            print(f"  ○ {migration_file.stem} - {migration_file.name}")
    
    def create_migration(self, name):
        """Create a new migration file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        version = f"{timestamp}_{name}"
        filename = f"{version}.sql"
        
        migration_file = self.migrations_dir / filename
        
        template = f"""-- Migration: {name}
-- Created: {datetime.now().isoformat()}
-- Description: Add description here

BEGIN;

-- Add your migration SQL here

COMMIT;
"""
        
        migration_file.write_text(template, encoding='utf-8')
        print(f"Created migration: {migration_file}")
        return migration_file
    
    def rollback(self, target_version=None):
        """Rollback migrations (basic implementation)"""
        print("WARNING: Rollback functionality is limited.")
        print("Consider restoring from backup for complex rollbacks.")
        
        if target_version:
            print(f"Rolling back to version: {target_version}")
            # Implementation would depend on having rollback scripts
        else:
            print("Please specify target version for rollback")

def main():
    parser = argparse.ArgumentParser(description='Suna Database Migration Tool')
    parser.add_argument('--db-url', help='Database URL (or use DATABASE_URL env var)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Apply pending migrations')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('name', help='Migration name')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migrations')
    rollback_parser.add_argument('--to', help='Target version to rollback to')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        migrator = DatabaseMigrator(args.db_url)
        
        if args.command == 'migrate':
            migrator.migrate()
        elif args.command == 'status':
            migrator.status()
        elif args.command == 'create':
            migrator.create_migration(args.name)
        elif args.command == 'rollback':
            migrator.rollback(args.to)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()