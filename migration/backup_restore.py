#!/usr/bin/env python3
"""
Suna Backup and Restore Tool

This script provides comprehensive backup and restore functionality for the Suna self-hosted deployment,
including database backups, file storage backups, and point-in-time recovery.
"""

import argparse
import json
import os
import sys
import time
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import structlog
import psycopg2
from psycopg2.extras import RealDictCursor
import tarfile
import gzip
import hashlib

# Configure logging
logger = structlog.get_logger(__name__)

class BackupManager:
    """Handles backup and restore operations for Suna"""
    
    def __init__(self, config_file: str, backup_dir: str = "backups"):
        self.config_file = Path(config_file)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self.load_config()
        
        # Backup metadata
        self.backup_metadata = {
            "backup_timestamp": datetime.utcnow().isoformat(),
            "backup_type": "",
            "components": [],
            "size": 0,
            "checksum": "",
            "errors": [],
            "warnings": []
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load backup configuration"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load backup configuration", error=str(e))
            # Return default configuration
            return {
                "database": {
                    "host": "localhost",
                    "port": 5491,
                    "database": "suna",
                    "user": "suna",
                    "password": "suna_password"
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
    
    def create_backup(self, backup_type: str = "full", components: List[str] = None) -> Dict[str, Any]:
        """Create a comprehensive backup"""
        logger.info("Starting backup", type=backup_type, components=components)
        
        try:
            # Initialize backup metadata
            self.backup_metadata["backup_type"] = backup_type
            self.backup_metadata["components"] = components or ["database", "storage", "config"]
            
            # Create timestamped backup directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"suna_backup_{backup_type}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            # Create backup components
            if "database" in self.backup_metadata["components"]:
                self.backup_database(backup_path)
            
            if "storage" in self.backup_metadata["components"]:
                self.backup_storage(backup_path)
            
            if "config" in self.backup_metadata["components"]:
                self.backup_configuration(backup_path)
            
            # Create backup archive
            archive_path = self.create_backup_archive(backup_path, backup_name)
            
            # Calculate backup size and checksum
            self.calculate_backup_stats(archive_path)
            
            # Save backup metadata
            self.save_backup_metadata(backup_path, archive_path)
            
            # Cleanup temporary files
            shutil.rmtree(backup_path)
            
            logger.info("Backup completed successfully", 
                       type=backup_type,
                       archive=str(archive_path),
                       size=self.backup_metadata["size"])
            
            return self.backup_metadata
            
        except Exception as e:
            logger.error("Backup failed", error=str(e))
            self.backup_metadata["errors"].append(str(e))
            raise
    
    def backup_database(self, backup_path: Path) -> None:
        """Create database backup"""
        logger.info("Creating database backup")
        
        try:
            db_config = self.config["database"]
            
            # Create database backup using pg_dump
            backup_file = backup_path / "database.sql"
            
            cmd = [
                "pg_dump",
                f"--host={db_config['host']}",
                f"--port={db_config['port']}",
                f"--username={db_config['user']}",
                f"--dbname={db_config['database']}",
                "--verbose",
                "--clean",
                "--if-exists",
                "--create",
                "--no-owner",
                "--no-privileges",
                f"--file={backup_file}"
            ]
            
            # Set password environment variable
            env = os.environ.copy()
            env["PGPASSWORD"] = db_config["password"]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Database backup failed: {result.stderr}")
            
            # Compress the backup if enabled
            if self.config["backup"]["compression"]:
                compressed_file = backup_path / "database.sql.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed file
                backup_file.unlink()
                backup_file = compressed_file
            
            self.backup_metadata["components"].append("database")
            logger.info("Database backup created", file=str(backup_file))
            
        except Exception as e:
            logger.error("Database backup failed", error=str(e))
            self.backup_metadata["errors"].append(f"Database backup failed: {e}")
            raise
    
    def backup_storage(self, backup_path: Path) -> None:
        """Create storage backup"""
        logger.info("Creating storage backup")
        
        try:
            storage_config = self.config["storage"]
            storage_path = Path(storage_config["path"])
            
            if not storage_path.exists():
                logger.warning("Storage path does not exist", path=str(storage_path))
                return
            
            # Create storage backup
            storage_backup_path = backup_path / "storage"
            storage_backup_path.mkdir(exist_ok=True)
            
            # Copy storage files
            shutil.copytree(storage_path, storage_backup_path, dirs_exist_ok=True)
            
            # Create storage metadata
            storage_metadata = {
                "backup_timestamp": datetime.utcnow().isoformat(),
                "source_path": str(storage_path),
                "file_count": 0,
                "total_size": 0,
                "files": []
            }
            
            # Calculate storage statistics
            for file_path in storage_backup_path.rglob("*"):
                if file_path.is_file():
                    storage_metadata["file_count"] += 1
                    storage_metadata["total_size"] += file_path.stat().st_size
                    storage_metadata["files"].append({
                        "path": str(file_path.relative_to(storage_backup_path)),
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
            
            # Save storage metadata
            metadata_file = storage_backup_path / "backup_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(storage_metadata, f, indent=2)
            
            self.backup_metadata["components"].append("storage")
            logger.info("Storage backup created", 
                       path=str(storage_backup_path),
                       file_count=storage_metadata["file_count"])
            
        except Exception as e:
            logger.error("Storage backup failed", error=str(e))
            self.backup_metadata["errors"].append(f"Storage backup failed: {e}")
            raise
    
    def backup_configuration(self, backup_path: Path) -> None:
        """Create configuration backup"""
        logger.info("Creating configuration backup")
        
        try:
            config_backup_path = backup_path / "config"
            config_backup_path.mkdir(exist_ok=True)
            
            # Backup environment files
            env_files = [
                ".env.production",
                ".env.development", 
                ".env.staging",
                ".env.example"
            ]
            
            for env_file in env_files:
                env_path = Path(env_file)
                if env_path.exists():
                    shutil.copy2(env_path, config_backup_path / env_path.name)
            
            # Backup Docker Compose files
            compose_files = [
                "docker-compose.yaml",
                "docker-compose.production.yml",
                "docker-compose.development.yml",
                "docker-compose.self-hosted.yml"
            ]
            
            for compose_file in compose_files:
                compose_path = Path(compose_file)
                if compose_path.exists():
                    shutil.copy2(compose_path, config_backup_path / compose_path.name)
            
            # Backup migration configuration
            migration_config = self.output_dir / "migration_config.json"
            if migration_config.exists():
                shutil.copy2(migration_config, config_backup_path / "migration_config.json")
            
            # Create configuration metadata
            config_metadata = {
                "backup_timestamp": datetime.utcnow().isoformat(),
                "files_backed_up": [],
                "total_size": 0
            }
            
            for file_path in config_backup_path.rglob("*"):
                if file_path.is_file():
                    config_metadata["files_backed_up"].append({
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
                    config_metadata["total_size"] += file_path.stat().st_size
            
            # Save configuration metadata
            metadata_file = config_backup_path / "backup_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(config_metadata, f, indent=2)
            
            self.backup_metadata["components"].append("config")
            logger.info("Configuration backup created", path=str(config_backup_path))
            
        except Exception as e:
            logger.error("Configuration backup failed", error=str(e))
            self.backup_metadata["errors"].append(f"Configuration backup failed: {e}")
            raise
    
    def create_backup_archive(self, backup_path: Path, backup_name: str) -> Path:
        """Create compressed backup archive"""
        logger.info("Creating backup archive")
        
        try:
            archive_path = self.backup_dir / f"{backup_name}.tar.gz"
            
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_path, arcname=backup_name)
            
            logger.info("Backup archive created", archive=str(archive_path))
            return archive_path
            
        except Exception as e:
            logger.error("Failed to create backup archive", error=str(e))
            raise
    
    def calculate_backup_stats(self, archive_path: Path) -> None:
        """Calculate backup size and checksum"""
        try:
            # Calculate size
            self.backup_metadata["size"] = archive_path.stat().st_size
            
            # Calculate checksum
            with open(archive_path, 'rb') as f:
                file_hash = hashlib.sha256()
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                self.backup_metadata["checksum"] = file_hash.hexdigest()
            
        except Exception as e:
            logger.error("Failed to calculate backup stats", error=str(e))
            self.backup_metadata["warnings"].append(f"Failed to calculate backup stats: {e}")
    
    def save_backup_metadata(self, backup_path: Path, archive_path: Path) -> None:
        """Save backup metadata"""
        try:
            # Add archive information
            self.backup_metadata["archive_path"] = str(archive_path)
            self.backup_metadata["archive_name"] = archive_path.name
            
            # Save metadata
            metadata_file = self.backup_dir / f"{archive_path.stem}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(self.backup_metadata, f, indent=2, default=str)
            
            logger.info("Backup metadata saved", file=str(metadata_file))
            
        except Exception as e:
            logger.error("Failed to save backup metadata", error=str(e))
            self.backup_metadata["warnings"].append(f"Failed to save backup metadata: {e}")
    
    def restore_backup(self, backup_file: str, components: List[str] = None, 
                      target_dir: str = None) -> Dict[str, Any]:
        """Restore from backup"""
        logger.info("Starting backup restore", backup_file=backup_file)
        
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")
            
            # Extract backup archive
            extract_path = self.backup_dir / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            extract_path.mkdir(exist_ok=True)
            
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(extract_path)
            
            # Find backup directory
            backup_dirs = list(extract_path.iterdir())
            if not backup_dirs:
                raise Exception("No backup data found in archive")
            
            backup_data_path = backup_dirs[0]
            
            # Restore components
            restore_metadata = {
                "restore_timestamp": datetime.utcnow().isoformat(),
                "backup_file": backup_file,
                "components_restored": [],
                "errors": [],
                "warnings": []
            }
            
            components = components or ["database", "storage", "config"]
            
            if "database" in components:
                self.restore_database(backup_data_path, restore_metadata)
            
            if "storage" in components:
                self.restore_storage(backup_data_path, restore_metadata, target_dir)
            
            if "config" in components:
                self.restore_configuration(backup_data_path, restore_metadata, target_dir)
            
            # Cleanup
            shutil.rmtree(extract_path)
            
            logger.info("Backup restore completed", 
                       backup_file=backup_file,
                       components_restored=restore_metadata["components_restored"])
            
            return restore_metadata
            
        except Exception as e:
            logger.error("Backup restore failed", error=str(e))
            raise
    
    def restore_database(self, backup_data_path: Path, restore_metadata: Dict[str, Any]) -> None:
        """Restore database from backup"""
        logger.info("Restoring database")
        
        try:
            db_config = self.config["database"]
            
            # Find database backup file
            db_backup_file = backup_data_path / "database.sql"
            db_backup_gz = backup_data_path / "database.sql.gz"
            
            if db_backup_gz.exists():
                # Decompress if needed
                with gzip.open(db_backup_gz, 'rb') as f_in:
                    with open(db_backup_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            
            if not db_backup_file.exists():
                raise FileNotFoundError("Database backup file not found")
            
            # Restore database using psql
            cmd = [
                "psql",
                f"--host={db_config['host']}",
                f"--port={db_config['port']}",
                f"--username={db_config['user']}",
                f"--dbname={db_config['database']}",
                "--verbose",
                f"--file={db_backup_file}"
            ]
            
            # Set password environment variable
            env = os.environ.copy()
            env["PGPASSWORD"] = db_config["password"]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Database restore failed: {result.stderr}")
            
            restore_metadata["components_restored"].append("database")
            logger.info("Database restored successfully")
            
        except Exception as e:
            logger.error("Database restore failed", error=str(e))
            restore_metadata["errors"].append(f"Database restore failed: {e}")
            raise
    
    def restore_storage(self, backup_data_path: Path, restore_metadata: Dict[str, Any], 
                       target_dir: str = None) -> None:
        """Restore storage from backup"""
        logger.info("Restoring storage")
        
        try:
            storage_backup_path = backup_data_path / "storage"
            if not storage_backup_path.exists():
                raise FileNotFoundError("Storage backup not found")
            
            # Determine target path
            if target_dir:
                target_path = Path(target_dir) / "storage"
            else:
                target_path = Path(self.config["storage"]["path"])
            
            # Create target directory
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Restore storage files
            shutil.copytree(storage_backup_path, target_path, dirs_exist_ok=True)
            
            restore_metadata["components_restored"].append("storage")
            logger.info("Storage restored successfully", target=str(target_path))
            
        except Exception as e:
            logger.error("Storage restore failed", error=str(e))
            restore_metadata["errors"].append(f"Storage restore failed: {e}")
            raise
    
    def restore_configuration(self, backup_data_path: Path, restore_metadata: Dict[str, Any],
                            target_dir: str = None) -> None:
        """Restore configuration from backup"""
        logger.info("Restoring configuration")
        
        try:
            config_backup_path = backup_data_path / "config"
            if not config_backup_path.exists():
                raise FileNotFoundError("Configuration backup not found")
            
            # Determine target path
            if target_dir:
                target_path = Path(target_dir)
            else:
                target_path = Path(".")
            
            # Restore configuration files
            for file_path in config_backup_path.iterdir():
                if file_path.is_file() and file_path.name != "backup_metadata.json":
                    target_file = target_path / file_path.name
                    shutil.copy2(file_path, target_file)
            
            restore_metadata["components_restored"].append("config")
            logger.info("Configuration restored successfully", target=str(target_path))
            
        except Exception as e:
            logger.error("Configuration restore failed", error=str(e))
            restore_metadata["errors"].append(f"Configuration restore failed: {e}")
            raise
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        logger.info("Listing available backups")
        
        backups = []
        
        try:
            for file_path in self.backup_dir.iterdir():
                if file_path.suffix == ".tar.gz":
                    # Try to find metadata file
                    metadata_file = self.backup_dir / f"{file_path.stem}_metadata.json"
                    
                    backup_info = {
                        "file": file_path.name,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "metadata_available": metadata_file.exists()
                    }
                    
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                                backup_info.update({
                                    "backup_type": metadata.get("backup_type"),
                                    "components": metadata.get("components", []),
                                    "checksum": metadata.get("checksum"),
                                    "errors": metadata.get("errors", [])
                                })
                        except Exception as e:
                            logger.warning("Failed to load backup metadata", file=str(metadata_file), error=str(e))
                    
                    backups.append(backup_info)
            
            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x["modified"], reverse=True)
            
            logger.info("Backup listing completed", count=len(backups))
            return backups
            
        except Exception as e:
            logger.error("Failed to list backups", error=str(e))
            return []
    
    def cleanup_old_backups(self, retention_days: int = None) -> Dict[str, Any]:
        """Clean up old backups based on retention policy"""
        logger.info("Cleaning up old backups")
        
        retention_days = retention_days or self.config["backup"]["retention_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        cleanup_metadata = {
            "cleanup_timestamp": datetime.utcnow().isoformat(),
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "files_removed": [],
            "errors": []
        }
        
        try:
            for file_path in self.backup_dir.iterdir():
                if file_path.suffix == ".tar.gz":
                    file_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_modified < cutoff_date:
                        try:
                            # Remove backup file
                            file_path.unlink()
                            
                            # Remove metadata file if it exists
                            metadata_file = self.backup_dir / f"{file_path.stem}_metadata.json"
                            if metadata_file.exists():
                                metadata_file.unlink()
                            
                            cleanup_metadata["files_removed"].append(file_path.name)
                            logger.info("Removed old backup", file=file_path.name)
                            
                        except Exception as e:
                            logger.error("Failed to remove old backup", file=file_path.name, error=str(e))
                            cleanup_metadata["errors"].append(f"Failed to remove {file_path.name}: {e}")
            
            logger.info("Backup cleanup completed", 
                       files_removed=len(cleanup_metadata["files_removed"]))
            return cleanup_metadata
            
        except Exception as e:
            logger.error("Backup cleanup failed", error=str(e))
            cleanup_metadata["errors"].append(str(e))
            return cleanup_metadata


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Suna Backup and Restore Tool")
    parser.add_argument("--config", required=True, help="Backup configuration file")
    parser.add_argument("--backup-dir", default="backups", help="Backup directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create backup command
    backup_parser = subparsers.add_parser("backup", help="Create backup")
    backup_parser.add_argument("--type", default="full", choices=["full", "incremental"], 
                              help="Backup type")
    backup_parser.add_argument("--components", nargs="+", 
                              choices=["database", "storage", "config"],
                              help="Components to backup")
    
    # Restore backup command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("--backup-file", required=True, help="Backup file to restore")
    restore_parser.add_argument("--components", nargs="+", 
                               choices=["database", "storage", "config"],
                               help="Components to restore")
    restore_parser.add_argument("--target-dir", help="Target directory for restore")
    
    # List backups command
    list_parser = subparsers.add_parser("list", help="List available backups")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old backups")
    cleanup_parser.add_argument("--retention-days", type=int, help="Retention period in days")
    
    args = parser.parse_args()
    
    try:
        backup_manager = BackupManager(
            config_file=args.config,
            backup_dir=args.backup_dir
        )
        
        if args.command == "backup":
            metadata = backup_manager.create_backup(
                backup_type=args.type,
                components=args.components
            )
            
            print(f"\nBackup completed successfully!")
            print(f"Type: {metadata['backup_type']}")
            print(f"Components: {', '.join(metadata['components'])}")
            print(f"Size: {metadata['size']} bytes")
            print(f"Archive: {metadata.get('archive_name', 'N/A')}")
            
            if metadata['errors']:
                print(f"\nErrors: {len(metadata['errors'])}")
                for error in metadata['errors']:
                    print(f"  - {error}")
        
        elif args.command == "restore":
            metadata = backup_manager.restore_backup(
                backup_file=args.backup_file,
                components=args.components,
                target_dir=args.target_dir
            )
            
            print(f"\nRestore completed!")
            print(f"Backup file: {metadata['backup_file']}")
            print(f"Components restored: {', '.join(metadata['components_restored'])}")
            
            if metadata['errors']:
                print(f"\nErrors: {len(metadata['errors'])}")
                for error in metadata['errors']:
                    print(f"  - {error}")
        
        elif args.command == "list":
            backups = backup_manager.list_backups()
            
            print(f"\nAvailable backups ({len(backups)}):")
            for backup in backups:
                print(f"\nFile: {backup['file']}")
                print(f"Size: {backup['size']} bytes")
                print(f"Modified: {backup['modified']}")
                print(f"Type: {backup.get('backup_type', 'Unknown')}")
                print(f"Components: {', '.join(backup.get('components', []))}")
                if backup.get('errors'):
                    print(f"Errors: {len(backup['errors'])}")
        
        elif args.command == "cleanup":
            metadata = backup_manager.cleanup_old_backups(
                retention_days=args.retention_days
            )
            
            print(f"\nCleanup completed!")
            print(f"Retention days: {metadata['retention_days']}")
            print(f"Files removed: {len(metadata['files_removed'])}")
            
            if metadata['files_removed']:
                print("\nRemoved files:")
                for file_name in metadata['files_removed']:
                    print(f"  - {file_name}")
            
            if metadata['errors']:
                print(f"\nErrors: {len(metadata['errors'])}")
                for error in metadata['errors']:
                    print(f"  - {error}")
        
        else:
            parser.print_help()
        
        sys.exit(0)
        
    except Exception as e:
        logger.error("Backup operation failed", error=str(e))
        print(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()







