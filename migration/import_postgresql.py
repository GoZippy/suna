#!/usr/bin/env python3
"""
Suna PostgreSQL Data Import Tool

This script imports exported Supabase data into a PostgreSQL database for self-hosted deployment.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import pandas as pd
from urllib.parse import urlparse

# Configure logging
logger = structlog.get_logger(__name__)

class PostgreSQLImporter:
    """Handles import of data to PostgreSQL"""
    
    def __init__(self, connection_string: str, export_dir: str, schema: str = "public"):
        self.connection_string = connection_string
        self.export_dir = Path(export_dir)
        self.schema = schema
        
        # Import metadata
        self.import_metadata = {
            "import_timestamp": datetime.utcnow().isoformat(),
            "tables_imported": [],
            "records_imported": {},
            "errors": [],
            "warnings": []
        }
        
        # Database connection
        self.conn = None
        self.cursor = None
    
    def connect(self) -> None:
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error("Failed to connect to database", error=str(e))
            raise
    
    def disconnect(self) -> None:
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Disconnected from PostgreSQL database")
    
    def import_all(self) -> Dict[str, Any]:
        """Import all data from export directory"""
        logger.info("Starting PostgreSQL import", export_dir=str(self.export_dir))
        
        try:
            self.connect()
            
            # Check if export directory exists
            if not self.export_dir.exists():
                raise FileNotFoundError(f"Export directory not found: {self.export_dir}")
            
            # Load export metadata
            metadata_file = self.export_dir / "export_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    export_metadata = json.load(f)
                logger.info("Loaded export metadata", 
                           tables_exported=len(export_metadata.get("tables_exported", [])))
            
            # Create schema if needed
            self.create_schema()
            
            # Import schema
            self.import_schema()
            
            # Import functions and triggers
            self.import_functions()
            
            # Import RLS policies
            self.import_policies()
            
            # Import table data
            self.import_tables()
            
            # Import storage metadata
            self.import_storage()
            
            # Validate import
            self.validate_import()
            
            # Commit all changes
            self.conn.commit()
            
            logger.info("PostgreSQL import completed successfully",
                       tables_imported=len(self.import_metadata["tables_imported"]))
            
            return self.import_metadata
            
        except Exception as e:
            logger.error("Import failed", error=str(e))
            self.import_metadata["errors"].append(str(e))
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.disconnect()
    
    def create_schema(self) -> None:
        """Create schema if it doesn't exist"""
        try:
            self.cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
            logger.info("Schema created/verified", schema=self.schema)
        except Exception as e:
            logger.error("Failed to create schema", error=str(e))
            raise
    
    def import_schema(self) -> None:
        """Import database schema"""
        logger.info("Importing database schema")
        
        schema_file = self.export_dir / "schema.json"
        if not schema_file.exists():
            logger.warning("Schema file not found, using default schema")
            self.create_default_schema()
            return
        
        try:
            with open(schema_file, 'r') as f:
                schema_data = json.load(f)
            
            # Create extensions
            for extension in schema_data.get("extensions", []):
                self.create_extension(extension)
            
            # Create tables
            for table_name, table_info in schema_data.get("tables", {}).items():
                self.create_table(table_name, table_info)
            
            logger.info("Schema imported successfully")
            
        except Exception as e:
            logger.error("Failed to import schema", error=str(e))
            self.import_metadata["errors"].append(f"Schema import failed: {e}")
    
    def create_extension(self, extension: str) -> None:
        """Create PostgreSQL extension"""
        try:
            self.cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {extension}")
            logger.info("Extension created", extension=extension)
        except Exception as e:
            logger.warning("Failed to create extension", extension=extension, error=str(e))
            self.import_metadata["warnings"].append(f"Extension {extension} creation failed: {e}")
    
    def create_table(self, table_name: str, table_info: Dict[str, Any]) -> None:
        """Create table from schema definition"""
        try:
            columns = []
            for col_name, col_info in table_info.get("columns", {}).items():
                col_def = f"{col_name} {col_info['type']}"
                
                if col_info.get("primary_key"):
                    col_def += " PRIMARY KEY"
                elif col_info.get("unique"):
                    col_def += " UNIQUE"
                
                if col_info.get("default"):
                    col_def += f" DEFAULT {col_info['default']}"
                
                if not col_info.get("nullable", True):
                    col_def += " NOT NULL"
                
                columns.append(col_def)
            
            if columns:
                create_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.{table_name} (
                    {', '.join(columns)}
                );
                """
                self.cursor.execute(create_sql)
                logger.info("Table created", table=table_name)
            
        except Exception as e:
            logger.error("Failed to create table", table=table_name, error=str(e))
            self.import_metadata["errors"].append(f"Table {table_name} creation failed: {e}")
    
    def create_default_schema(self) -> None:
        """Create default schema for Suna"""
        logger.info("Creating default schema")
        
        # Create extensions
        extensions = ["vector", "uuid-ossp", "pgcrypto"]
        for ext in extensions:
            self.create_extension(ext)
        
        # Create tables
        tables = {
            "users": """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """,
            "agents": """
                CREATE TABLE IF NOT EXISTS agents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    description TEXT,
                    config JSONB,
                    user_id UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """,
            "agent_versions": """
                CREATE TABLE IF NOT EXISTS agent_versions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    agent_id UUID REFERENCES agents(id),
                    version TEXT NOT NULL,
                    config JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """,
            "agent_workflows": """
                CREATE TABLE IF NOT EXISTS agent_workflows (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    agent_id UUID REFERENCES agents(id),
                    name TEXT NOT NULL,
                    steps JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """,
            "knowledge_base": """
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    description TEXT,
                    user_id UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """,
            "documents": """
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    knowledge_base_id UUID REFERENCES knowledge_base(id),
                    title TEXT NOT NULL,
                    content TEXT,
                    embedding vector(1536),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """,
            "files": """
                CREATE TABLE IF NOT EXISTS files (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size BIGINT,
                    mime_type TEXT,
                    user_id UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """
        }
        
        for table_name, create_sql in tables.items():
            try:
                self.cursor.execute(create_sql)
                logger.info("Default table created", table=table_name)
            except Exception as e:
                logger.error("Failed to create default table", table=table_name, error=str(e))
                self.import_metadata["errors"].append(f"Default table {table_name} creation failed: {e}")
    
    def import_functions(self) -> None:
        """Import database functions and triggers"""
        logger.info("Importing functions and triggers")
        
        functions_file = self.export_dir / "functions.sql"
        if not functions_file.exists():
            logger.warning("Functions file not found, creating default functions")
            self.create_default_functions()
            return
        
        try:
            with open(functions_file, 'r') as f:
                functions_sql = f.read()
            
            # Split and execute SQL statements
            statements = [stmt.strip() for stmt in functions_sql.split(';') if stmt.strip()]
            for statement in statements:
                if statement:
                    self.cursor.execute(statement)
            
            logger.info("Functions and triggers imported")
            
        except Exception as e:
            logger.error("Failed to import functions", error=str(e))
            self.import_metadata["errors"].append(f"Functions import failed: {e}")
    
    def create_default_functions(self) -> None:
        """Create default functions and triggers"""
        logger.info("Creating default functions and triggers")
        
        functions = [
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            """,
            """
            CREATE TRIGGER update_users_updated_at 
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """,
            """
            CREATE TRIGGER update_agents_updated_at 
            BEFORE UPDATE ON agents
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """,
            """
            CREATE TRIGGER update_agent_workflows_updated_at 
            BEFORE UPDATE ON agent_workflows
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """,
            """
            CREATE TRIGGER update_knowledge_base_updated_at 
            BEFORE UPDATE ON knowledge_base
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """,
            """
            CREATE TRIGGER update_documents_updated_at 
            BEFORE UPDATE ON documents
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """
        ]
        
        for function in functions:
            try:
                self.cursor.execute(function)
            except Exception as e:
                logger.warning("Failed to create function/trigger", error=str(e))
                self.import_metadata["warnings"].append(f"Function creation failed: {e}")
    
    def import_policies(self) -> None:
        """Import RLS policies"""
        logger.info("Importing RLS policies")
        
        policies_file = self.export_dir / "policies.sql"
        if not policies_file.exists():
            logger.warning("Policies file not found, creating default policies")
            self.create_default_policies()
            return
        
        try:
            with open(policies_file, 'r') as f:
                policies_sql = f.read()
            
            # Split and execute SQL statements
            statements = [stmt.strip() for stmt in policies_sql.split(';') if stmt.strip()]
            for statement in statements:
                if statement and not statement.startswith('--'):
                    self.cursor.execute(statement)
            
            logger.info("RLS policies imported")
            
        except Exception as e:
            logger.error("Failed to import policies", error=str(e))
            self.import_metadata["errors"].append(f"Policies import failed: {e}")
    
    def create_default_policies(self) -> None:
        """Create default RLS policies"""
        logger.info("Creating default RLS policies")
        
        # Note: These are simplified policies for local deployment
        # In production, you'd want more sophisticated RLS policies
        policies = [
            "ALTER TABLE users ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE agents ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE documents ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE files ENABLE ROW LEVEL SECURITY;"
        ]
        
        for policy in policies:
            try:
                self.cursor.execute(policy)
            except Exception as e:
                logger.warning("Failed to create policy", error=str(e))
                self.import_metadata["warnings"].append(f"Policy creation failed: {e}")
    
    def import_tables(self) -> None:
        """Import data from all tables"""
        logger.info("Importing table data")
        
        tables_dir = self.export_dir / "tables"
        if not tables_dir.exists():
            logger.warning("Tables directory not found")
            return
        
        # Import tables in dependency order
        tables = [
            "users",
            "agents",
            "agent_versions", 
            "agent_workflows",
            "knowledge_base",
            "documents",
            "files"
        ]
        
        for table in tables:
            try:
                self.import_table(table, tables_dir)
                self.import_metadata["tables_imported"].append(table)
            except Exception as e:
                logger.error("Failed to import table", table=table, error=str(e))
                self.import_metadata["errors"].append(f"Table {table} import failed: {e}")
    
    def import_table(self, table_name: str, tables_dir: Path) -> None:
        """Import data from a specific table"""
        logger.info("Importing table", table=table_name)
        
        # Try JSON file first, then CSV
        json_file = tables_dir / f"{table_name}.json"
        csv_file = tables_dir / f"{table_name}.csv"
        
        if json_file.exists():
            self.import_table_json(table_name, json_file)
        elif csv_file.exists():
            self.import_table_csv(table_name, csv_file)
        else:
            logger.info("No data file found for table", table=table_name)
    
    def import_table_json(self, table_name: str, json_file: Path) -> None:
        """Import table data from JSON file"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            if not data:
                logger.info("No data to import", table=table_name)
                return
            
            # Get column names from first record
            columns = list(data[0].keys())
            
            # Prepare data for insertion
            values = []
            for record in data:
                row = []
                for col in columns:
                    value = record.get(col)
                    # Handle special data types
                    if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                        # Handle array-like strings
                        try:
                            value = json.loads(value)
                        except:
                            pass
                    row.append(value)
                values.append(row)
            
            # Insert data
            if values:
                placeholders = ','.join(['%s'] * len(columns))
                insert_sql = f"INSERT INTO {self.schema}.{table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                
                self.cursor.executemany(insert_sql, values)
                
                self.import_metadata["records_imported"][table_name] = len(values)
                logger.info("Table imported", 
                           table=table_name, 
                           records=len(values))
            
        except Exception as e:
            logger.error("Failed to import table JSON", table=table_name, error=str(e))
            raise
    
    def import_table_csv(self, table_name: str, csv_file: Path) -> None:
        """Import table data from CSV file"""
        try:
            df = pd.read_csv(csv_file)
            
            if df.empty:
                logger.info("No data to import", table=table_name)
                return
            
            # Convert DataFrame to list of tuples
            values = [tuple(row) for row in df.values]
            columns = list(df.columns)
            
            # Insert data
            if values:
                placeholders = ','.join(['%s'] * len(columns))
                insert_sql = f"INSERT INTO {self.schema}.{table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                
                self.cursor.executemany(insert_sql, values)
                
                self.import_metadata["records_imported"][table_name] = len(values)
                logger.info("Table imported", 
                           table=table_name, 
                           records=len(values))
            
        except Exception as e:
            logger.error("Failed to import table CSV", table=table_name, error=str(e))
            raise
    
    def import_storage(self) -> None:
        """Import storage metadata"""
        logger.info("Importing storage metadata")
        
        storage_file = self.export_dir / "storage_metadata.json"
        if not storage_file.exists():
            logger.info("No storage metadata to import")
            return
        
        try:
            with open(storage_file, 'r') as f:
                storage_data = json.load(f)
            
            # Create storage directories
            storage_dir = Path("storage")
            storage_dir.mkdir(exist_ok=True)
            
            # Create bucket directories
            for bucket in storage_data.get("buckets", []):
                bucket_dir = storage_dir / bucket["name"]
                bucket_dir.mkdir(exist_ok=True)
                logger.info("Created storage bucket directory", bucket=bucket["name"])
            
            # Save file metadata for reference
            files_metadata_file = storage_dir / "files_metadata.json"
            with open(files_metadata_file, 'w') as f:
                json.dump(storage_data.get("files", []), f, indent=2)
            
            logger.info("Storage metadata imported", 
                       buckets=len(storage_data.get("buckets", [])),
                       files=len(storage_data.get("files", [])))
            
        except Exception as e:
            logger.error("Failed to import storage metadata", error=str(e))
            self.import_metadata["errors"].append(f"Storage import failed: {e}")
    
    def validate_import(self) -> None:
        """Validate the import by checking data integrity"""
        logger.info("Validating import")
        
        try:
            # Check table counts
            for table in self.import_metadata["tables_imported"]:
                self.cursor.execute(f"SELECT COUNT(*) FROM {self.schema}.{table}")
                count = self.cursor.fetchone()["count"]
                expected = self.import_metadata["records_imported"].get(table, 0)
                
                if count != expected:
                    logger.warning("Record count mismatch", 
                                 table=table, 
                                 expected=expected, 
                                 actual=count)
                    self.import_metadata["warnings"].append(
                        f"Table {table}: expected {expected} records, got {count}")
                else:
                    logger.info("Table validation passed", table=table, count=count)
            
            # Check foreign key constraints
            self.validate_foreign_keys()
            
            logger.info("Import validation completed")
            
        except Exception as e:
            logger.error("Validation failed", error=str(e))
            self.import_metadata["errors"].append(f"Validation failed: {e}")
    
    def validate_foreign_keys(self) -> None:
        """Validate foreign key relationships"""
        logger.info("Validating foreign key relationships")
        
        # Define foreign key relationships
        fk_checks = [
            ("agents", "user_id", "users", "id"),
            ("agent_versions", "agent_id", "agents", "id"),
            ("agent_workflows", "agent_id", "agents", "id"),
            ("knowledge_base", "user_id", "users", "id"),
            ("documents", "knowledge_base_id", "knowledge_base", "id"),
            ("files", "user_id", "users", "id")
        ]
        
        for table, fk_col, ref_table, ref_col in fk_checks:
            try:
                # Check for orphaned records
                self.cursor.execute(f"""
                    SELECT COUNT(*) FROM {self.schema}.{table} t
                    LEFT JOIN {self.schema}.{ref_table} r ON t.{fk_col} = r.{ref_col}
                    WHERE r.{ref_col} IS NULL AND t.{fk_col} IS NOT NULL
                """)
                orphaned_count = self.cursor.fetchone()["count"]
                
                if orphaned_count > 0:
                    logger.warning("Found orphaned records", 
                                 table=table, 
                                 fk_column=fk_col,
                                 orphaned_count=orphaned_count)
                    self.import_metadata["warnings"].append(
                        f"Table {table}: {orphaned_count} orphaned records in {fk_col}")
                else:
                    logger.info("Foreign key validation passed", 
                              table=table, 
                              fk_column=fk_col)
                    
            except Exception as e:
                logger.warning("Failed to validate foreign key", 
                             table=table, 
                             fk_column=fk_col, 
                             error=str(e))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Import data to PostgreSQL")
    parser.add_argument("--target-db", required=True, help="PostgreSQL connection string")
    parser.add_argument("--export-dir", required=True, help="Export directory path")
    parser.add_argument("--schema", default="public", help="Database schema")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Load config if provided
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
            args.target_db = config.get('target', {}).get('connection_string', args.target_db)
            args.schema = config.get('target', {}).get('schema', args.schema)
    
    try:
        importer = PostgreSQLImporter(
            connection_string=args.target_db,
            export_dir=args.export_dir,
            schema=args.schema
        )
        
        metadata = importer.import_all()
        
        print(f"\nImport completed successfully!")
        print(f"Tables imported: {len(metadata['tables_imported'])}")
        print(f"Total records imported: {sum(metadata['records_imported'].values())}")
        
        if metadata['warnings']:
            print(f"\nWarnings: {len(metadata['warnings'])}")
            for warning in metadata['warnings']:
                print(f"  - {warning}")
        
        if metadata['errors']:
            print(f"\nErrors: {len(metadata['errors'])}")
            for error in metadata['errors']:
                print(f"  - {error}")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error("Import failed", error=str(e))
        print(f"Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()







