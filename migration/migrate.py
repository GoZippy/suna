#!/usr/bin/env python3
"""
Suna Complete Migration Orchestrator

This script orchestrates the complete migration process from Supabase to self-hosted PostgreSQL,
including data export, import, validation, and configuration migration.
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
import subprocess

# Import migration components
from export_supabase import SupabaseExporter
from import_postgresql import PostgreSQLImporter
from validate_migration import MigrationValidator
from migrate_config import ConfigurationMigrator
from backup_restore import BackupManager

# Configure logging
logger = structlog.get_logger(__name__)

class MigrationOrchestrator:
    """Orchestrates the complete migration process"""
    
    def __init__(self, config_file: str, output_dir: str = "migration_output"):
        self.config_file = Path(config_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load migration configuration
        self.config = self.load_config()
        
        # Migration metadata
        self.migration_metadata = {
            "migration_start": datetime.utcnow().isoformat(),
            "steps_completed": [],
            "errors": [],
            "warnings": [],
            "summary": {}
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load migration configuration"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load migration configuration", error=str(e))
            raise
    
    def run_migration(self, steps: List[str] = None) -> Dict[str, Any]:
        """Run the complete migration process"""
        logger.info("Starting complete migration process")
        
        try:
            # Define migration steps
            all_steps = [
                "backup_source",
                "export_supabase", 
                "migrate_config",
                "import_postgresql",
                "validate_migration",
                "backup_target"
            ]
            
            steps_to_run = steps or all_steps
            
            for step in steps_to_run:
                if step not in all_steps:
                    logger.warning("Unknown migration step", step=step)
                    continue
                
                try:
                    logger.info(f"Starting migration step: {step}")
                    
                    if step == "backup_source":
                        self.backup_source()
                    elif step == "export_supabase":
                        self.export_supabase()
                    elif step == "migrate_config":
                        self.migrate_configuration()
                    elif step == "import_postgresql":
                        self.import_postgresql()
                    elif step == "validate_migration":
                        self.validate_migration()
                    elif step == "backup_target":
                        self.backup_target()
                    
                    self.migration_metadata["steps_completed"].append(step)
                    logger.info(f"Completed migration step: {step}")
                    
                except Exception as e:
                    logger.error(f"Migration step failed: {step}", error=str(e))
                    self.migration_metadata["errors"].append(f"Step {step} failed: {e}")
                    
                    # Ask user if they want to continue
                    if not self.should_continue_after_error(step):
                        break
            
            # Generate migration summary
            self.generate_migration_summary()
            
            logger.info("Migration process completed")
            return self.migration_metadata
            
        except Exception as e:
            logger.error("Migration process failed", error=str(e))
            self.migration_metadata["errors"].append(str(e))
            raise
    
    def backup_source(self) -> None:
        """Create backup of source system"""
        logger.info("Creating source system backup")
        
        try:
            # Create backup configuration
            backup_config = {
                "database": {
                    "host": self.config["source"]["host"],
                    "port": self.config["source"]["port"],
                    "database": self.config["source"]["database"],
                    "user": self.config["source"]["user"],
                    "password": self.config["source"]["password"]
                },
                "storage": {
                    "path": "storage",
                    "include_files": True,
                    "max_backup_size": "10GB"
                },
                "backup": {
                    "retention_days": 30,
                    "compression": True,
                    "encryption": False,
                    "incremental": True
                }
            }
            
            backup_config_file = self.output_dir / "backup_config.json"
            with open(backup_config_file, 'w') as f:
                json.dump(backup_config, f, indent=2)
            
            # Create backup
            backup_manager = BackupManager(
                config_file=str(backup_config_file),
                backup_dir=str(self.output_dir / "source_backups")
            )
            
            backup_metadata = backup_manager.create_backup(
                backup_type="full",
                components=["database", "storage", "config"]
            )
            
            logger.info("Source backup completed", metadata=backup_metadata)
            
        except Exception as e:
            logger.error("Source backup failed", error=str(e))
            raise
    
    def export_supabase(self) -> None:
        """Export data from Supabase"""
        logger.info("Exporting data from Supabase")
        
        try:
            exporter = SupabaseExporter(
                project_ref=self.config["source"]["project_ref"],
                api_key=self.config["source"]["api_key"],
                url=self.config["source"]["url"],
                output_dir=str(self.output_dir / "supabase_export")
            )
            
            export_metadata = exporter.export_all()
            
            logger.info("Supabase export completed", metadata=export_metadata)
            
        except Exception as e:
            logger.error("Supabase export failed", error=str(e))
            raise
    
    def migrate_configuration(self) -> None:
        """Migrate configuration from external to local services"""
        logger.info("Migrating configuration")
        
        try:
            # Find source configuration file
            source_config_file = self.config.get("source_config_file", "config.json")
            
            migrator = ConfigurationMigrator(
                config_file=source_config_file,
                output_dir=str(self.output_dir / "migrated_configs")
            )
            
            migration_metadata = migrator.migrate_all()
            
            logger.info("Configuration migration completed", metadata=migration_metadata)
            
        except Exception as e:
            logger.error("Configuration migration failed", error=str(e))
            raise
    
    def import_postgresql(self) -> None:
        """Import data to PostgreSQL"""
        logger.info("Importing data to PostgreSQL")
        
        try:
            # Find export directory
            export_dir = self.output_dir / "supabase_export"
            export_dirs = list(export_dir.glob("supabase_export_*"))
            
            if not export_dirs:
                raise Exception("No Supabase export found")
            
            # Use the most recent export
            latest_export = max(export_dirs, key=lambda x: x.stat().st_mtime)
            
            importer = PostgreSQLImporter(
                connection_string=self.config["target"]["connection_string"],
                export_dir=str(latest_export),
                schema=self.config["target"].get("schema", "public")
            )
            
            import_metadata = importer.import_all()
            
            logger.info("PostgreSQL import completed", metadata=import_metadata)
            
        except Exception as e:
            logger.error("PostgreSQL import failed", error=str(e))
            raise
    
    def validate_migration(self) -> None:
        """Validate the migration"""
        logger.info("Validating migration")
        
        try:
            # Find export directory for comparison
            export_dir = self.output_dir / "supabase_export"
            export_dirs = list(export_dir.glob("supabase_export_*"))
            
            if not export_dirs:
                logger.warning("No Supabase export found for validation")
                return
            
            latest_export = max(export_dirs, key=lambda x: x.stat().st_mtime)
            
            validator = MigrationValidator(
                source_config={"type": "supabase"},
                target_config=self.config["target"],
                export_dir=str(latest_export)
            )
            
            validation_metadata = validator.validate_all()
            
            logger.info("Migration validation completed", metadata=validation_metadata)
            
        except Exception as e:
            logger.error("Migration validation failed", error=str(e))
            raise
    
    def backup_target(self) -> None:
        """Create backup of target system"""
        logger.info("Creating target system backup")
        
        try:
            # Create backup configuration for target
            backup_config = {
                "database": {
                    "host": self.config["target"]["host"],
                    "port": self.config["target"]["port"],
                    "database": self.config["target"]["database"],
                    "user": self.config["target"]["user"],
                    "password": self.config["target"]["password"]
                },
                "storage": {
                    "path": "storage",
                    "include_files": True,
                    "max_backup_size": "10GB"
                },
                "backup": {
                    "retention_days": 30,
                    "compression": True,
                    "encryption": False,
                    "incremental": True
                }
            }
            
            backup_config_file = self.output_dir / "target_backup_config.json"
            with open(backup_config_file, 'w') as f:
                json.dump(backup_config, f, indent=2)
            
            # Create backup
            backup_manager = BackupManager(
                config_file=str(backup_config_file),
                backup_dir=str(self.output_dir / "target_backups")
            )
            
            backup_metadata = backup_manager.create_backup(
                backup_type="full",
                components=["database", "storage", "config"]
            )
            
            logger.info("Target backup completed", metadata=backup_metadata)
            
        except Exception as e:
            logger.error("Target backup failed", error=str(e))
            raise
    
    def should_continue_after_error(self, step: str) -> bool:
        """Ask user if they want to continue after an error"""
        try:
            response = input(f"\nStep '{step}' failed. Continue with remaining steps? (y/N): ")
            return response.lower() in ['y', 'yes']
        except KeyboardInterrupt:
            return False
    
    def generate_migration_summary(self) -> None:
        """Generate migration summary"""
        logger.info("Generating migration summary")
        
        try:
            summary = {
                "migration_start": self.migration_metadata["migration_start"],
                "migration_end": datetime.utcnow().isoformat(),
                "steps_completed": len(self.migration_metadata["steps_completed"]),
                "total_steps": 6,
                "success_rate": len(self.migration_metadata["steps_completed"]) / 6 * 100,
                "errors": len(self.migration_metadata["errors"]),
                "warnings": len(self.migration_metadata["warnings"]),
                "completed_steps": self.migration_metadata["steps_completed"],
                "next_steps": [
                    "1. Review the migrated configuration files",
                    "2. Update environment-specific values",
                    "3. Test the self-hosted deployment",
                    "4. Update DNS and domain configurations",
                    "5. Monitor the system for any issues",
                    "6. Plan the production cutover"
                ]
            }
            
            self.migration_metadata["summary"] = summary
            
            # Save summary to file
            summary_file = self.output_dir / "migration_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(self.migration_metadata, f, indent=2, default=str)
            
            logger.info("Migration summary generated", file=str(summary_file))
            
        except Exception as e:
            logger.error("Failed to generate migration summary", error=str(e))
            self.migration_metadata["errors"].append(f"Summary generation failed: {e}")
    
    def create_migration_config_template(self) -> None:
        """Create a migration configuration template"""
        logger.info("Creating migration configuration template")
        
        template = {
            "source": {
                "type": "supabase",
                "project_ref": "your-project-ref",
                "api_key": "your-api-key",
                "url": "https://your-project.supabase.co",
                "host": "db.your-project.supabase.co",
                "port": 5432,
                "database": "postgres",
                "user": "postgres",
                "password": "your-database-password"
            },
            "target": {
                "type": "postgresql",
                "connection_string": "postgresql://suna:suna_password@localhost:5491/suna",
                "host": "localhost",
                "port": 5491,
                "database": "suna",
                "user": "suna",
                "password": "suna_password",
                "schema": "public"
            },
            "source_config_file": "config.json",
            "options": {
                "backup_before_migration": True,
                "validate_after_import": True,
                "create_rollback_point": True,
                "parallel_import": True,
                "compression": True,
                "encryption": False
            }
        }
        
        template_file = self.output_dir / "migration_config_template.json"
        with open(template_file, 'w') as f:
            json.dump(template, f, indent=2)
        
        logger.info("Migration configuration template created", file=str(template_file))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Suna Complete Migration Orchestrator")
    parser.add_argument("--config", required=True, help="Migration configuration file")
    parser.add_argument("--output-dir", default="migration_output", help="Output directory")
    parser.add_argument("--steps", nargs="+", 
                       choices=["backup_source", "export_supabase", "migrate_config", 
                               "import_postgresql", "validate_migration", "backup_target"],
                       help="Specific steps to run")
    parser.add_argument("--create-template", action="store_true", 
                       help="Create migration configuration template")
    
    args = parser.parse_args()
    
    try:
        orchestrator = MigrationOrchestrator(
            config_file=args.config,
            output_dir=args.output_dir
        )
        
        if args.create_template:
            orchestrator.create_migration_config_template()
            print("Migration configuration template created!")
            return
        
        metadata = orchestrator.run_migration(steps=args.steps)
        
        # Print summary
        summary = metadata["summary"]
        print(f"\nMigration Summary:")
        print(f"  Start time: {summary['migration_start']}")
        print(f"  End time: {summary['migration_end']}")
        print(f"  Steps completed: {summary['steps_completed']}/{summary['total_steps']}")
        print(f"  Success rate: {summary['success_rate']:.1f}%")
        print(f"  Errors: {summary['errors']}")
        print(f"  Warnings: {summary['warnings']}")
        
        print(f"\nCompleted steps:")
        for step in summary['completed_steps']:
            print(f"  ✓ {step}")
        
        if metadata['errors']:
            print(f"\nErrors encountered:")
            for error in metadata['errors']:
                print(f"  ✗ {error}")
        
        if metadata['warnings']:
            print(f"\nWarnings:")
            for warning in metadata['warnings']:
                print(f"  ⚠ {warning}")
        
        print(f"\nNext steps:")
        for step in summary['next_steps']:
            print(f"  {step}")
        
        print(f"\nMigration output saved to: {args.output_dir}")
        
        # Exit with error code if there were errors
        if metadata['errors']:
            sys.exit(1)
        else:
            sys.exit(0)
        
    except Exception as e:
        logger.error("Migration orchestration failed", error=str(e))
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()







