"""
Data migration scripts for migrating from Supabase to local PostgreSQL.
Provides utilities to export data from Supabase and import into local database.
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncpg
from supabase import create_async_client, AsyncClient
from utils.logger import logger
from utils.config import config

class SupabaseMigrator:
    """Handles migration from Supabase to local PostgreSQL"""
    
    def __init__(self, supabase_url: str, supabase_key: str, postgres_url: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.postgres_url = postgres_url
        self.supabase_client: Optional[AsyncClient] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize connections to both databases"""
        try:
            # Initialize Supabase client
            self.supabase_client = await create_async_client(
                self.supabase_url,
                self.supabase_key
            )
            
            # Initialize PostgreSQL connection
            self.postgres_pool = await asyncpg.create_pool(
                self.postgres_url,
                min_size=2,
                max_size=10
            )
            
            logger.info("Migration connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize migration connections: {e}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self.postgres_pool:
            await self.postgres_pool.close()
        
        if self.supabase_client:
            await self.supabase_client.close()
    
    async def export_table_data(self, table_name: str, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Export all data from a Supabase table"""
        try:
            all_data = []
            offset = 0
            
            while True:
                # Fetch batch of data
                result = await self.supabase_client.table(table_name).select("*").range(offset, offset + batch_size - 1).execute()
                
                if not result.data:
                    break
                
                all_data.extend(result.data)
                logger.info(f"Exported {len(result.data)} records from {table_name} (total: {len(all_data)})")
                
                # If we got fewer records than batch_size, we've reached the end
                if len(result.data) < batch_size:
                    break
                
                offset += batch_size
            
            logger.info(f"Completed export of {table_name}: {len(all_data)} total records")
            return all_data
            
        except Exception as e:
            logger.error(f"Error exporting table {table_name}: {e}")
            raise
    
    async def import_table_data(self, table_name: str, data: List[Dict[str, Any]], batch_size: int = 100):
        """Import data into PostgreSQL table"""
        try:
            if not data:
                logger.info(f"No data to import for table {table_name}")
                return
            
            async with self.postgres_pool.acquire() as conn:
                # Get table columns
                columns_result = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = $1
                    ORDER BY ordinal_position
                """, table_name)
                
                if not columns_result:
                    logger.error(f"Table {table_name} not found in PostgreSQL database")
                    return
                
                available_columns = {row['column_name'] for row in columns_result}
                
                # Process data in batches
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    
                    for record in batch:
                        # Filter out columns that don't exist in the target table
                        filtered_record = {k: v for k, v in record.items() if k in available_columns}
                        
                        if not filtered_record:
                            continue
                        
                        # Convert datetime strings to proper format
                        for key, value in filtered_record.items():
                            if isinstance(value, str) and value.endswith('Z'):
                                try:
                                    # Convert ISO string to datetime
                                    filtered_record[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except ValueError:
                                    pass
                        
                        # Build INSERT query
                        columns = list(filtered_record.keys())
                        placeholders = [f'${i+1}' for i in range(len(columns))]
                        values = list(filtered_record.values())
                        
                        query = f"""
                            INSERT INTO {table_name} ({', '.join(columns)})
                            VALUES ({', '.join(placeholders)})
                            ON CONFLICT DO NOTHING
                        """
                        
                        try:
                            await conn.execute(query, *values)
                        except Exception as e:
                            logger.warning(f"Failed to insert record into {table_name}: {e}")
                            logger.debug(f"Failed record: {filtered_record}")
                    
                    logger.info(f"Imported batch {i//batch_size + 1} for {table_name}")
            
            logger.info(f"Completed import of {table_name}: {len(data)} records processed")
            
        except Exception as e:
            logger.error(f"Error importing table {table_name}: {e}")
            raise
    
    async def migrate_table(self, table_name: str, batch_size: int = 1000):
        """Migrate a single table from Supabase to PostgreSQL"""
        logger.info(f"Starting migration of table: {table_name}")
        
        try:
            # Export data from Supabase
            data = await self.export_table_data(table_name, batch_size)
            
            # Import data to PostgreSQL
            await self.import_table_data(table_name, data, batch_size // 10)
            
            logger.info(f"Successfully migrated table: {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to migrate table {table_name}: {e}")
            raise
    
    async def migrate_all_tables(self):
        """Migrate all tables in the correct order to handle foreign key constraints"""
        # Define migration order to handle foreign key dependencies
        migration_order = [
            'users',
            'user_tiers',
            'projects',
            'threads',
            'messages',
            'knowledge_base',
            'document_collections',
            'knowledge_collection_items',
            'usage_logs',
            'monthly_usage',
            'api_keys',
            'user_sessions',
            'project_collaborators',
            'sandbox_instances',
            'search_history',
            'system_config',
            'user_preferences',
            'audit_logs',
            'background_jobs',
            'email_queue',
            'websocket_connections'
        ]
        
        logger.info("Starting full database migration")
        
        for table_name in migration_order:
            try:
                await self.migrate_table(table_name)
            except Exception as e:
                logger.error(f"Failed to migrate table {table_name}: {e}")
                # Continue with other tables even if one fails
                continue
        
        logger.info("Database migration completed")
    
    async def export_to_json(self, output_dir: str = "./migration_export"):
        """Export all Supabase data to JSON files for backup"""
        os.makedirs(output_dir, exist_ok=True)
        
        tables = [
            'users', 'projects', 'threads', 'messages', 'knowledge_base',
            'document_collections', 'usage_logs', 'api_keys', 'user_sessions'
        ]
        
        for table_name in tables:
            try:
                logger.info(f"Exporting {table_name} to JSON...")
                data = await self.export_table_data(table_name)
                
                output_file = os.path.join(output_dir, f"{table_name}.json")
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                logger.info(f"Exported {len(data)} records from {table_name} to {output_file}")
                
            except Exception as e:
                logger.error(f"Failed to export {table_name}: {e}")
    
    async def import_from_json(self, input_dir: str = "./migration_export"):
        """Import data from JSON files to PostgreSQL"""
        if not os.path.exists(input_dir):
            logger.error(f"Input directory {input_dir} does not exist")
            return
        
        # Import in dependency order
        import_order = [
            'users', 'projects', 'threads', 'messages', 'knowledge_base',
            'document_collections', 'usage_logs', 'api_keys', 'user_sessions'
        ]
        
        for table_name in import_order:
            json_file = os.path.join(input_dir, f"{table_name}.json")
            
            if not os.path.exists(json_file):
                logger.warning(f"JSON file for {table_name} not found, skipping")
                continue
            
            try:
                logger.info(f"Importing {table_name} from JSON...")
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                await self.import_table_data(table_name, data)
                logger.info(f"Successfully imported {len(data)} records to {table_name}")
                
            except Exception as e:
                logger.error(f"Failed to import {table_name}: {e}")

async def run_migration():
    """Main migration function"""
    # Get configuration
    supabase_url = config.SUPABASE_URL
    supabase_key = config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_ANON_KEY
    postgres_url = config.DATABASE_URL or 'postgresql://suna_user:suna_password@localhost:5432/suna'
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase configuration not found. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return
    
    migrator = SupabaseMigrator(supabase_url, supabase_key, postgres_url)
    
    try:
        await migrator.initialize()
        
        # First export to JSON as backup
        logger.info("Creating JSON backup of Supabase data...")
        await migrator.export_to_json()
        
        # Then migrate to PostgreSQL
        logger.info("Starting migration to PostgreSQL...")
        await migrator.migrate_all_tables()
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await migrator.close()

async def export_only():
    """Export Supabase data to JSON files only"""
    supabase_url = config.SUPABASE_URL
    supabase_key = config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_ANON_KEY
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase configuration not found")
        return
    
    migrator = SupabaseMigrator(supabase_url, supabase_key, "")
    migrator.supabase_client = await create_async_client(supabase_url, supabase_key)
    
    try:
        await migrator.export_to_json()
        logger.info("Export completed successfully!")
    finally:
        if migrator.supabase_client:
            await migrator.supabase_client.close()

async def import_only():
    """Import data from JSON files to PostgreSQL only"""
    postgres_url = config.DATABASE_URL or 'postgresql://suna_user:suna_password@localhost:5432/suna'
    
    migrator = SupabaseMigrator("", "", postgres_url)
    migrator.postgres_pool = await asyncpg.create_pool(postgres_url, min_size=2, max_size=10)
    
    try:
        await migrator.import_from_json()
        logger.info("Import completed successfully!")
    finally:
        if migrator.postgres_pool:
            await migrator.postgres_pool.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "export":
            asyncio.run(export_only())
        elif command == "import":
            asyncio.run(import_only())
        elif command == "migrate":
            asyncio.run(run_migration())
        else:
            print("Usage: python migration_scripts.py [export|import|migrate]")
    else:
        asyncio.run(run_migration())