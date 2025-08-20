#!/usr/bin/env python3
"""
Migration script to migrate from Supabase to local PostgreSQL.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.migration_scripts import run_migration, export_only, import_only
from utils.logger import logger

def print_usage():
    print("Usage: python migrate_from_supabase.py [command]")
    print("")
    print("Commands:")
    print("  migrate  - Full migration from Supabase to PostgreSQL (export + import)")
    print("  export   - Export data from Supabase to JSON files only")
    print("  import   - Import data from JSON files to PostgreSQL only")
    print("")
    print("Environment variables required:")
    print("  SUPABASE_URL - Your Supabase project URL")
    print("  SUPABASE_SERVICE_ROLE_KEY - Your Supabase service role key")
    print("  DATABASE_URL - Your PostgreSQL connection string")
    print("")
    print("Example:")
    print("  export SUPABASE_URL='https://your-project.supabase.co'")
    print("  export SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'")
    print("  export DATABASE_URL='postgresql://user:password@localhost:5432/suna'")
    print("  python migrate_from_supabase.py migrate")

async def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command not in ['migrate', 'export', 'import']:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)
    
    try:
        if command == 'migrate':
            logger.info("Starting full migration from Supabase to PostgreSQL...")
            await run_migration()
        elif command == 'export':
            logger.info("Exporting data from Supabase to JSON files...")
            await export_only()
        elif command == 'import':
            logger.info("Importing data from JSON files to PostgreSQL...")
            await import_only()
        
        logger.info(f"Migration command '{command}' completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())