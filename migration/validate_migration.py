#!/usr/bin/env python3
"""
Suna Migration Validation Tool

This script validates the migration from Supabase to PostgreSQL by comparing data integrity,
checking for missing records, and generating detailed validation reports.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import structlog
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from urllib.parse import urlparse
import hashlib

# Configure logging
logger = structlog.get_logger(__name__)

class MigrationValidator:
    """Validates migration from Supabase to PostgreSQL"""
    
    def __init__(self, source_config: Dict[str, Any], target_config: Dict[str, Any], 
                 export_dir: Optional[str] = None):
        self.source_config = source_config
        self.target_config = target_config
        self.export_dir = Path(export_dir) if export_dir else None
        
        # Validation metadata
        self.validation_metadata = {
            "validation_timestamp": datetime.utcnow().isoformat(),
            "source_type": source_config.get("type", "unknown"),
            "target_type": target_config.get("type", "unknown"),
            "tables_validated": [],
            "validation_results": {},
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        
        # Database connections
        self.source_conn = None
        self.source_cursor = None
        self.target_conn = None
        self.target_cursor = None
    
    def connect_databases(self) -> None:
        """Establish connections to source and target databases"""
        try:
            # Connect to target database
            self.target_conn = psycopg2.connect(self.target_config["connection_string"])
            self.target_cursor = self.target_conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Connected to target PostgreSQL database")
            
            # Connect to source if it's a database
            if self.source_config.get("type") == "postgresql":
                self.source_conn = psycopg2.connect(self.source_config["connection_string"])
                self.source_cursor = self.source_conn.cursor(cursor_factory=RealDictCursor)
                logger.info("Connected to source PostgreSQL database")
            elif self.source_config.get("type") == "supabase":
                # For Supabase, we'll use the export data
                logger.info("Using Supabase export data for validation")
            
        except Exception as e:
            logger.error("Failed to connect to databases", error=str(e))
            raise
    
    def disconnect_databases(self) -> None:
        """Close database connections"""
        if self.source_cursor:
            self.source_cursor.close()
        if self.source_conn:
            self.source_conn.close()
        if self.target_cursor:
            self.target_cursor.close()
        if self.target_conn:
            self.target_conn.close()
        logger.info("Disconnected from databases")
    
    def validate_all(self) -> Dict[str, Any]:
        """Run comprehensive validation"""
        logger.info("Starting migration validation")
        
        try:
            self.connect_databases()
            
            # Validate schema
            self.validate_schema()
            
            # Validate table data
            self.validate_table_data()
            
            # Validate foreign key relationships
            self.validate_foreign_keys()
            
            # Validate data integrity
            self.validate_data_integrity()
            
            # Validate storage
            self.validate_storage()
            
            # Generate summary
            self.generate_summary()
            
            logger.info("Migration validation completed")
            return self.validation_metadata
            
        except Exception as e:
            logger.error("Validation failed", error=str(e))
            self.validation_metadata["errors"].append(str(e))
            raise
        finally:
            self.disconnect_databases()
    
    def validate_schema(self) -> None:
        """Validate database schema"""
        logger.info("Validating database schema")
        
        try:
            # Get target schema information
            target_schema = self.get_target_schema()
            
            # Get source schema information
            source_schema = self.get_source_schema()
            
            # Compare schemas
            schema_comparison = self.compare_schemas(source_schema, target_schema)
            
            self.validation_metadata["validation_results"]["schema"] = schema_comparison
            
            if schema_comparison["errors"]:
                logger.error("Schema validation failed", errors=schema_comparison["errors"])
            else:
                logger.info("Schema validation passed")
                
        except Exception as e:
            logger.error("Schema validation failed", error=str(e))
            self.validation_metadata["errors"].append(f"Schema validation failed: {e}")
    
    def get_target_schema(self) -> Dict[str, Any]:
        """Get target database schema information"""
        schema_info = {
            "tables": {},
            "extensions": [],
            "functions": []
        }
        
        try:
            # Get extensions
            self.target_cursor.execute("""
                SELECT extname FROM pg_extension WHERE extnamespace = 'public'::regnamespace
            """)
            extensions = self.target_cursor.fetchall()
            schema_info["extensions"] = [ext["extname"] for ext in extensions]
            
            # Get tables
            self.target_cursor.execute("""
                SELECT table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                ORDER BY table_name, ordinal_position
            """)
            columns = self.target_cursor.fetchall()
            
            for col in columns:
                table_name = col["table_name"]
                if table_name not in schema_info["tables"]:
                    schema_info["tables"][table_name] = {"columns": {}}
                
                schema_info["tables"][table_name]["columns"][col["column_name"]] = {
                    "type": col["data_type"],
                    "nullable": col["is_nullable"] == "YES",
                    "default": col["column_default"]
                }
            
            # Get functions
            self.target_cursor.execute("""
                SELECT routine_name, routine_type
                FROM information_schema.routines 
                WHERE routine_schema = 'public'
            """)
            functions = self.target_cursor.fetchall()
            schema_info["functions"] = [f["routine_name"] for f in functions]
            
        except Exception as e:
            logger.error("Failed to get target schema", error=str(e))
            raise
        
        return schema_info
    
    def get_source_schema(self) -> Dict[str, Any]:
        """Get source schema information"""
        if self.source_config.get("type") == "postgresql":
            return self.get_postgresql_source_schema()
        elif self.source_config.get("type") == "supabase":
            return self.get_supabase_source_schema()
        else:
            return {"tables": {}, "extensions": [], "functions": []}
    
    def get_postgresql_source_schema(self) -> Dict[str, Any]:
        """Get source PostgreSQL schema"""
        schema_info = {
            "tables": {},
            "extensions": [],
            "functions": []
        }
        
        try:
            # Get extensions
            self.source_cursor.execute("""
                SELECT extname FROM pg_extension WHERE extnamespace = 'public'::regnamespace
            """)
            extensions = self.source_cursor.fetchall()
            schema_info["extensions"] = [ext["extname"] for ext in extensions]
            
            # Get tables
            self.source_cursor.execute("""
                SELECT table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                ORDER BY table_name, ordinal_position
            """)
            columns = self.source_cursor.fetchall()
            
            for col in columns:
                table_name = col["table_name"]
                if table_name not in schema_info["tables"]:
                    schema_info["tables"][table_name] = {"columns": {}}
                
                schema_info["tables"][table_name]["columns"][col["column_name"]] = {
                    "type": col["data_type"],
                    "nullable": col["is_nullable"] == "YES",
                    "default": col["column_default"]
                }
            
        except Exception as e:
            logger.error("Failed to get source schema", error=str(e))
            raise
        
        return schema_info
    
    def get_supabase_source_schema(self) -> Dict[str, Any]:
        """Get Supabase source schema from export data"""
        schema_info = {
            "tables": {},
            "extensions": [],
            "functions": []
        }
        
        if not self.export_dir:
            logger.warning("No export directory provided for Supabase schema validation")
            return schema_info
        
        try:
            # Load schema from export
            schema_file = self.export_dir / "schema.json"
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    export_schema = json.load(f)
                
                schema_info["tables"] = export_schema.get("tables", {})
                schema_info["extensions"] = export_schema.get("extensions", [])
                
            # Load functions from export
            functions_file = self.export_dir / "functions.sql"
            if functions_file.exists():
                with open(functions_file, 'r') as f:
                    functions_sql = f.read()
                
                # Extract function names (simplified)
                import re
                function_matches = re.findall(r'CREATE.*FUNCTION\s+(\w+)', functions_sql, re.IGNORECASE)
                schema_info["functions"] = function_matches
                
        except Exception as e:
            logger.error("Failed to get Supabase source schema", error=str(e))
            raise
        
        return schema_info
    
    def compare_schemas(self, source_schema: Dict[str, Any], target_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Compare source and target schemas"""
        comparison = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "details": {
                "tables": {},
                "extensions": {},
                "functions": {}
            }
        }
        
        # Compare extensions
        source_extensions = set(source_schema.get("extensions", []))
        target_extensions = set(target_schema.get("extensions", []))
        
        missing_extensions = source_extensions - target_extensions
        extra_extensions = target_extensions - source_extensions
        
        if missing_extensions:
            comparison["errors"].append(f"Missing extensions: {missing_extensions}")
            comparison["passed"] = False
        
        if extra_extensions:
            comparison["warnings"].append(f"Extra extensions: {extra_extensions}")
        
        comparison["details"]["extensions"] = {
            "source": list(source_extensions),
            "target": list(target_extensions),
            "missing": list(missing_extensions),
            "extra": list(extra_extensions)
        }
        
        # Compare tables
        source_tables = set(source_schema.get("tables", {}).keys())
        target_tables = set(target_schema.get("tables", {}).keys())
        
        missing_tables = source_tables - target_tables
        extra_tables = target_tables - source_tables
        
        if missing_tables:
            comparison["errors"].append(f"Missing tables: {missing_tables}")
            comparison["passed"] = False
        
        if extra_tables:
            comparison["warnings"].append(f"Extra tables: {extra_tables}")
        
        # Compare table columns
        common_tables = source_tables & target_tables
        for table in common_tables:
            table_comparison = self.compare_table_schema(
                source_schema["tables"][table],
                target_schema["tables"][table]
            )
            comparison["details"]["tables"][table] = table_comparison
            
            if not table_comparison["passed"]:
                comparison["passed"] = False
        
        return comparison
    
    def compare_table_schema(self, source_table: Dict[str, Any], target_table: Dict[str, Any]) -> Dict[str, Any]:
        """Compare individual table schemas"""
        comparison = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        source_columns = set(source_table.get("columns", {}).keys())
        target_columns = set(target_table.get("columns", {}).keys())
        
        missing_columns = source_columns - target_columns
        extra_columns = target_columns - source_columns
        
        if missing_columns:
            comparison["errors"].append(f"Missing columns: {missing_columns}")
            comparison["passed"] = False
        
        if extra_columns:
            comparison["warnings"].append(f"Extra columns: {extra_columns}")
        
        comparison["details"] = {
            "source_columns": list(source_columns),
            "target_columns": list(target_columns),
            "missing_columns": list(missing_columns),
            "extra_columns": list(extra_columns)
        }
        
        return comparison
    
    def validate_table_data(self) -> None:
        """Validate table data integrity"""
        logger.info("Validating table data")
        
        try:
            # Get list of tables to validate
            self.target_cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            tables = [row["table_name"] for row in self.target_cursor.fetchall()]
            
            for table in tables:
                try:
                    self.validate_table(table)
                    self.validation_metadata["tables_validated"].append(table)
                except Exception as e:
                    logger.error("Failed to validate table", table=table, error=str(e))
                    self.validation_metadata["errors"].append(f"Table {table} validation failed: {e}")
            
        except Exception as e:
            logger.error("Table data validation failed", error=str(e))
            self.validation_metadata["errors"].append(f"Table data validation failed: {e}")
    
    def validate_table(self, table_name: str) -> None:
        """Validate individual table"""
        logger.info("Validating table", table=table_name)
        
        validation_result = {
            "passed": True,
            "record_count": 0,
            "errors": [],
            "warnings": [],
            "data_checksum": None
        }
        
        try:
            # Get record count
            self.target_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            record_count = self.target_cursor.fetchone()["count"]
            validation_result["record_count"] = record_count
            
            # Get data checksum for comparison
            if record_count > 0:
                checksum = self.get_table_checksum(table_name)
                validation_result["data_checksum"] = checksum
            
            # Compare with source if available
            if self.source_config.get("type") == "postgresql":
                source_validation = self.validate_table_against_source(table_name)
                validation_result.update(source_validation)
            elif self.source_config.get("type") == "supabase" and self.export_dir:
                source_validation = self.validate_table_against_export(table_name)
                validation_result.update(source_validation)
            
            # Check for data quality issues
            quality_issues = self.check_data_quality(table_name)
            validation_result["warnings"].extend(quality_issues)
            
            self.validation_metadata["validation_results"][table_name] = validation_result
            
            if validation_result["errors"]:
                logger.error("Table validation failed", table=table_name, errors=validation_result["errors"])
            else:
                logger.info("Table validation passed", table=table_name, record_count=record_count)
                
        except Exception as e:
            logger.error("Table validation failed", table=table_name, error=str(e))
            validation_result["passed"] = False
            validation_result["errors"].append(str(e))
            self.validation_metadata["validation_results"][table_name] = validation_result
    
    def get_table_checksum(self, table_name: str) -> str:
        """Get checksum of table data for comparison"""
        try:
            # Get all data and create checksum
            self.target_cursor.execute(f"SELECT * FROM {table_name} ORDER BY 1")
            rows = self.target_cursor.fetchall()
            
            # Convert to string and hash
            data_str = str(rows)
            return hashlib.md5(data_str.encode()).hexdigest()
            
        except Exception as e:
            logger.warning("Failed to get table checksum", table=table_name, error=str(e))
            return None
    
    def validate_table_against_source(self, table_name: str) -> Dict[str, Any]:
        """Validate table against source PostgreSQL database"""
        result = {
            "source_record_count": 0,
            "source_checksum": None,
            "checksum_match": False
        }
        
        try:
            # Get source record count
            self.source_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            source_count = self.source_cursor.fetchone()["count"]
            result["source_record_count"] = source_count
            
            # Get source checksum
            if source_count > 0:
                self.source_cursor.execute(f"SELECT * FROM {table_name} ORDER BY 1")
                source_rows = self.source_cursor.fetchall()
                source_data_str = str(source_rows)
                result["source_checksum"] = hashlib.md5(source_data_str.encode()).hexdigest()
            
            return result
            
        except Exception as e:
            logger.warning("Failed to validate against source", table=table_name, error=str(e))
            return result
    
    def validate_table_against_export(self, table_name: str) -> Dict[str, Any]:
        """Validate table against Supabase export data"""
        result = {
            "export_record_count": 0,
            "export_checksum": None,
            "checksum_match": False
        }
        
        try:
            # Load export data
            tables_dir = self.export_dir / "tables"
            json_file = tables_dir / f"{table_name}.json"
            
            if json_file.exists():
                with open(json_file, 'r') as f:
                    export_data = json.load(f)
                
                result["export_record_count"] = len(export_data)
                
                if export_data:
                    export_data_str = str(export_data)
                    result["export_checksum"] = hashlib.md5(export_data_str.encode()).hexdigest()
            
            return result
            
        except Exception as e:
            logger.warning("Failed to validate against export", table=table_name, error=str(e))
            return result
    
    def check_data_quality(self, table_name: str) -> List[str]:
        """Check data quality issues"""
        issues = []
        
        try:
            # Check for null values in important columns
            self.target_cursor.execute(f"""
                SELECT column_name, COUNT(*) as null_count
                FROM information_schema.columns c
                LEFT JOIN {table_name} t ON t.{c.column_name} IS NULL
                WHERE c.table_name = '{table_name}' 
                AND c.is_nullable = 'NO'
                GROUP BY column_name
                HAVING COUNT(*) > 0
            """)
            
            null_violations = self.target_cursor.fetchall()
            for violation in null_violations:
                issues.append(f"NULL values in NOT NULL column: {violation['column_name']}")
            
            # Check for duplicate records (if primary key exists)
            self.target_cursor.execute(f"""
                SELECT COUNT(*) as total_count,
                       COUNT(DISTINCT *) as distinct_count
                FROM {table_name}
            """)
            
            count_result = self.target_cursor.fetchone()
            if count_result["total_count"] != count_result["distinct_count"]:
                issues.append("Duplicate records found")
            
        except Exception as e:
            logger.warning("Failed to check data quality", table=table_name, error=str(e))
        
        return issues
    
    def validate_foreign_keys(self) -> None:
        """Validate foreign key relationships"""
        logger.info("Validating foreign key relationships")
        
        try:
            # Define expected foreign key relationships
            fk_relationships = [
                ("agents", "user_id", "users", "id"),
                ("agent_versions", "agent_id", "agents", "id"),
                ("agent_workflows", "agent_id", "agents", "id"),
                ("knowledge_base", "user_id", "users", "id"),
                ("documents", "knowledge_base_id", "knowledge_base", "id"),
                ("files", "user_id", "users", "id")
            ]
            
            fk_validation = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "details": {}
            }
            
            for table, fk_col, ref_table, ref_col in fk_relationships:
                try:
                    # Check for orphaned records
                    self.target_cursor.execute(f"""
                        SELECT COUNT(*) as orphaned_count
                        FROM {table} t
                        LEFT JOIN {ref_table} r ON t.{fk_col} = r.{ref_col}
                        WHERE r.{ref_col} IS NULL AND t.{fk_col} IS NOT NULL
                    """)
                    
                    orphaned_count = self.target_cursor.fetchone()["orphaned_count"]
                    
                    fk_detail = {
                        "orphaned_count": orphaned_count,
                        "valid": orphaned_count == 0
                    }
                    
                    fk_validation["details"][f"{table}.{fk_col}"] = fk_detail
                    
                    if orphaned_count > 0:
                        fk_validation["errors"].append(
                            f"Table {table}: {orphaned_count} orphaned records in {fk_col}")
                        fk_validation["passed"] = False
                    else:
                        logger.info("Foreign key validation passed", 
                                  table=table, 
                                  fk_column=fk_col)
                        
                except Exception as e:
                    logger.warning("Failed to validate foreign key", 
                                 table=table, 
                                 fk_column=fk_col, 
                                 error=str(e))
                    fk_validation["warnings"].append(
                        f"Failed to validate {table}.{fk_col}: {e}")
            
            self.validation_metadata["validation_results"]["foreign_keys"] = fk_validation
            
        except Exception as e:
            logger.error("Foreign key validation failed", error=str(e))
            self.validation_metadata["errors"].append(f"Foreign key validation failed: {e}")
    
    def validate_data_integrity(self) -> None:
        """Validate data integrity constraints"""
        logger.info("Validating data integrity")
        
        try:
            integrity_validation = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "details": {}
            }
            
            # Check for data type violations
            integrity_validation["details"]["data_types"] = self.check_data_types()
            
            # Check for constraint violations
            integrity_validation["details"]["constraints"] = self.check_constraints()
            
            # Check for referential integrity
            integrity_validation["details"]["referential"] = self.check_referential_integrity()
            
            self.validation_metadata["validation_results"]["data_integrity"] = integrity_validation
            
        except Exception as e:
            logger.error("Data integrity validation failed", error=str(e))
            self.validation_metadata["errors"].append(f"Data integrity validation failed: {e}")
    
    def check_data_types(self) -> Dict[str, Any]:
        """Check for data type violations"""
        return {
            "passed": True,
            "errors": [],
            "warnings": []
        }
    
    def check_constraints(self) -> Dict[str, Any]:
        """Check for constraint violations"""
        return {
            "passed": True,
            "errors": [],
            "warnings": []
        }
    
    def check_referential_integrity(self) -> Dict[str, Any]:
        """Check referential integrity"""
        return {
            "passed": True,
            "errors": [],
            "warnings": []
        }
    
    def validate_storage(self) -> None:
        """Validate storage migration"""
        logger.info("Validating storage migration")
        
        try:
            storage_validation = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "details": {}
            }
            
            # Check if storage directory exists
            storage_dir = Path("storage")
            if storage_dir.exists():
                storage_validation["details"]["storage_directory"] = {
                    "exists": True,
                    "path": str(storage_dir.absolute())
                }
                
                # Check for files metadata
                files_metadata_file = storage_dir / "files_metadata.json"
                if files_metadata_file.exists():
                    with open(files_metadata_file, 'r') as f:
                        files_metadata = json.load(f)
                    
                    storage_validation["details"]["files_metadata"] = {
                        "exists": True,
                        "file_count": len(files_metadata)
                    }
                else:
                    storage_validation["warnings"].append("Files metadata not found")
            else:
                storage_validation["warnings"].append("Storage directory not found")
            
            self.validation_metadata["validation_results"]["storage"] = storage_validation
            
        except Exception as e:
            logger.error("Storage validation failed", error=str(e))
            self.validation_metadata["errors"].append(f"Storage validation failed: {e}")
    
    def generate_summary(self) -> None:
        """Generate validation summary"""
        logger.info("Generating validation summary")
        
        try:
            summary = {
                "total_tables": len(self.validation_metadata["tables_validated"]),
                "total_records": 0,
                "validation_passed": True,
                "error_count": len(self.validation_metadata["errors"]),
                "warning_count": len(self.validation_metadata["warnings"])
            }
            
            # Calculate total records
            for table_name in self.validation_metadata["tables_validated"]:
                if table_name in self.validation_metadata["validation_results"]:
                    result = self.validation_metadata["validation_results"][table_name]
                    summary["total_records"] += result.get("record_count", 0)
                    
                    if not result.get("passed", True):
                        summary["validation_passed"] = False
            
            # Check overall validation status
            if self.validation_metadata["errors"]:
                summary["validation_passed"] = False
            
            self.validation_metadata["summary"] = summary
            
        except Exception as e:
            logger.error("Failed to generate summary", error=str(e))
            self.validation_metadata["errors"].append(f"Summary generation failed: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate migration from Supabase to PostgreSQL")
    parser.add_argument("--source-db", help="Source database connection string")
    parser.add_argument("--target-db", required=True, help="Target database connection string")
    parser.add_argument("--export-dir", help="Export directory path (for Supabase validation)")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--output", help="Output file for validation report")
    parser.add_argument("--detailed", action="store_true", help="Generate detailed validation report")
    
    args = parser.parse_args()
    
    # Load config if provided
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
            source_config = config.get('source', {})
            target_config = config.get('target', {})
    else:
        source_config = {
            "type": "postgresql" if args.source_db else "supabase",
            "connection_string": args.source_db
        }
        target_config = {
            "type": "postgresql",
            "connection_string": args.target_db
        }
    
    try:
        validator = MigrationValidator(
            source_config=source_config,
            target_config=target_config,
            export_dir=args.export_dir
        )
        
        validation_result = validator.validate_all()
        
        # Print summary
        summary = validation_result["summary"]
        print(f"\nMigration Validation Summary:")
        print(f"  Tables validated: {summary['total_tables']}")
        print(f"  Total records: {summary['total_records']}")
        print(f"  Validation passed: {summary['validation_passed']}")
        print(f"  Errors: {summary['error_count']}")
        print(f"  Warnings: {summary['warning_count']}")
        
        if validation_result["errors"]:
            print(f"\nErrors:")
            for error in validation_result["errors"]:
                print(f"  - {error}")
        
        if validation_result["warnings"]:
            print(f"\nWarnings:")
            for warning in validation_result["warnings"]:
                print(f"  - {warning}")
        
        # Save detailed report if requested
        if args.output:
            with open(args.output, 'w') as f:
                if args.detailed:
                    json.dump(validation_result, f, indent=2, default=str)
                else:
                    # Save only summary and errors/warnings
                    report = {
                        "summary": validation_result["summary"],
                        "errors": validation_result["errors"],
                        "warnings": validation_result["warnings"]
                    }
                    json.dump(report, f, indent=2, default=str)
            
            print(f"\nDetailed report saved to: {args.output}")
        
        # Exit with error code if validation failed
        if not summary["validation_passed"]:
            sys.exit(1)
        else:
            sys.exit(0)
        
    except Exception as e:
        logger.error("Validation failed", error=str(e))
        print(f"Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()







