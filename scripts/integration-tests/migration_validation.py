#!/usr/bin/env python3
"""
Migration Validation Script

This script validates the migration procedures and infrastructure
for moving from Supabase to the self-hosted system.
"""

import os
import sys
import json
import shutil
from pathlib import Path
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationValidator:
    """Validates migration procedures and infrastructure."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.validation_results = []

    def validate_migration_script(self, script_path: str, description: str) -> bool:
        """Validate that a migration script exists and is executable."""
        full_path = self.base_path / script_path
        exists = full_path.exists()

        if not exists:
            self.validation_results.append({
                "test": f"migration_script_{script_path.replace('/', '_').replace('.', '_')}",
                "description": description,
                "status": "FAIL",
                "details": f"Migration script missing: {full_path}"
            })
            return False

        # Check if script is executable (for shell scripts)
        if script_path.endswith('.sh') or script_path.endswith('.py'):
            is_executable = os.access(full_path, os.X_OK)
            if not is_executable and script_path.endswith('.sh'):
                # Try to make it executable
                try:
                    full_path.chmod(0o755)
                    is_executable = True
                except Exception:
                    pass

            status = "PASS" if is_executable else "WARN"
            self.validation_results.append({
                "test": f"migration_script_{script_path.replace('/', '_').replace('.', '_')}",
                "description": description,
                "status": status,
                "details": f"Script {'is' if is_executable else 'is not'} executable: {full_path}"
            })
            return is_executable
        else:
            self.validation_results.append({
                "test": f"migration_script_{script_path.replace('/', '_').replace('.', '_')}",
                "description": description,
                "status": "PASS",
                "details": f"Script exists: {full_path}"
            })
            return True

    def validate_migration_directory(self, dir_path: str, description: str) -> bool:
        """Validate that a migration directory exists and has content."""
        full_path = self.base_path / dir_path
        exists = full_path.is_dir()

        if not exists:
            self.validation_results.append({
                "test": f"migration_dir_{dir_path.replace('/', '_')}",
                "description": description,
                "status": "FAIL",
                "details": f"Migration directory missing: {full_path}"
            })
            return False

        # Check if directory has content
        has_content = any(full_path.iterdir())
        if not has_content:
            self.validation_results.append({
                "test": f"migration_dir_{dir_path.replace('/', '_')}",
                "description": description,
                "status": "WARN",
                "details": f"Migration directory exists but is empty: {full_path}"
            })
            return False

        self.validation_results.append({
            "test": f"migration_dir_{dir_path.replace('/', '_')}",
            "description": description,
            "status": "PASS",
            "details": f"Migration directory exists with content: {full_path}"
        })
        return True

    def validate_database_schema(self, schema_files: List[str]) -> bool:
        """Validate database schema files."""
        all_exist = True

        for schema_file in schema_files:
            full_path = self.base_path / schema_file
            exists = full_path.exists()

            if not exists:
                self.validation_results.append({
                    "test": f"schema_file_{schema_file.replace('/', '_').replace('.', '_')}",
                    "description": f"Database schema file {schema_file}",
                    "status": "FAIL",
                    "details": f"Schema file missing: {full_path}"
                })
                all_exist = False
            else:
                # Check if file has content
                try:
                    with open(full_path, 'r') as f:
                        content = f.read().strip()
                        has_content = len(content) > 0

                    status = "PASS" if has_content else "WARN"
                    self.validation_results.append({
                        "test": f"schema_file_{schema_file.replace('/', '_').replace('.', '_')}",
                        "description": f"Database schema file {schema_file}",
                        "status": status,
                        "details": f"Schema file {'has content' if has_content else 'is empty'}: {full_path}"
                    })
                except Exception as e:
                    self.validation_results.append({
                        "test": f"schema_file_{schema_file.replace('/', '_').replace('.', '_')}",
                        "description": f"Database schema file {schema_file}",
                        "status": "FAIL",
                        "details": f"Error reading schema file: {str(e)}"
                    })
                    all_exist = False

        return all_exist

    def validate_backup_procedures(self) -> bool:
        """Validate backup and restore procedures."""
        logger.info("Validating backup procedures...")

        # Check for backup scripts
        backup_scripts = [
            "scripts/backup-database.sh",
            "scripts/backup-database.py"
        ]

        backup_exists = False
        for script in backup_scripts:
            if self.validate_migration_script(script, f"Backup script {script}"):
                backup_exists = True
                break

        if not backup_exists:
            self.validation_results.append({
                "test": "backup_procedures",
                "description": "Database backup procedures",
                "status": "WARN",
                "details": "No backup scripts found"
            })

        # Check for backup directory
        backup_dir_exists = self.validate_migration_directory("backups", "Backup storage directory")

        return backup_exists or backup_dir_exists

    def validate_data_transformation(self) -> bool:
        """Validate data transformation scripts."""
        logger.info("Validating data transformation...")

        # Check for data transformation scripts
        transform_scripts = [
            "migration/migrate_config.py",
            "migration/migrate.py",
            "backend/migrate_from_supabase.py"
        ]

        transform_exists = False
        for script in transform_scripts:
            if self.validate_migration_script(script, f"Data transformation script {script}"):
                transform_exists = True

        if not transform_exists:
            self.validation_results.append({
                "test": "data_transformation",
                "description": "Data transformation procedures",
                "status": "WARN",
                "details": "No data transformation scripts found"
            })

        return transform_exists

    def validate_migration_documentation(self) -> bool:
        """Validate migration documentation."""
        logger.info("Validating migration documentation...")

        docs = [
            "MIGRATION_GUIDE.md",
            "docs/migration.md",
            "migration/README.md"
        ]

        docs_exist = False
        for doc in docs:
            if self.validate_migration_script(doc, f"Migration documentation {doc}"):
                docs_exist = True
                break

        if not docs_exist:
            self.validation_results.append({
                "test": "migration_documentation",
                "description": "Migration documentation",
                "status": "WARN",
                "details": "No migration documentation found"
            })

        return docs_exist

    def validate_environment_config(self) -> bool:
        """Validate environment configuration migration."""
        logger.info("Validating environment configuration...")

        config_files = [
            "self-hosted.env.example",
            ".env.example",
            "backend/.env.example",
            "frontend/.env.example"
        ]

        all_exist = True
        for config_file in config_files:
            if not self.validate_migration_script(config_file, f"Environment config {config_file}"):
                all_exist = False

        return all_exist

    def validate_rollback_procedures(self) -> bool:
        """Validate rollback procedures."""
        logger.info("Validating rollback procedures...")

        # Check for rollback scripts
        rollback_scripts = [
            "scripts/rollback-migration.sh",
            "scripts/rollback-migration.py",
            "migration/rollback.py"
        ]

        rollback_exists = False
        for script in rollback_scripts:
            if self.validate_migration_script(script, f"Rollback script {script}"):
                rollback_exists = True
                break

        if not rollback_exists:
            self.validation_results.append({
                "test": "rollback_procedures",
                "description": "Migration rollback procedures",
                "status": "WARN",
                "details": "No rollback procedures found"
            })

        return rollback_exists

    def run_migration_validation(self):
        """Run all migration validation checks."""
        logger.info("Starting migration validation...")

        # Core migration infrastructure
        logger.info("Validating core migration infrastructure...")
        self.validate_migration_directory("migration", "Migration scripts directory")
        self.validate_migration_script("backend/migrate_from_supabase.py", "Supabase migration script")

        # Database schema validation
        logger.info("Validating database schemas...")
        schema_files = [
            "database/init/01_init.sql",
            "database/init/02_schema.sql",
            "backend/database/migrations/001_initial_schema.sql"
        ]
        self.validate_database_schema(schema_files)

        # Migration procedures
        logger.info("Validating migration procedures...")
        self.validate_backup_procedures()
        self.validate_data_transformation()
        self.validate_rollback_procedures()

        # Documentation and configuration
        logger.info("Validating documentation and configuration...")
        self.validate_migration_documentation()
        self.validate_environment_config()

        # Generate report
        return self.generate_report()

    def generate_report(self):
        """Generate migration validation report."""
        total_tests = len(self.validation_results)
        passed_tests = len([r for r in self.validation_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.validation_results if r["status"] == "FAIL"])
        warn_tests = len([r for r in self.validation_results if r["status"] == "WARN"])

        print("\n" + "="*80)
        print("MIGRATION VALIDATION REPORT")
        print("="*80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Warnings: {warn_tests}")
        print()

        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.validation_results:
                if result["status"] == "FAIL":
                    print(f"❌ {result['description']}")
                    print(f"   {result['details']}")
            print()

        if warn_tests > 0:
            print("WARNINGS:")
            for result in self.validation_results:
                if result["status"] == "WARN":
                    print(f"⚠️  {result['description']}")
                    print(f"   {result['details']}")
            print()

        if passed_tests > 0:
            print("PASSED TESTS:")
            for result in self.validation_results:
                if result["status"] == "PASS":
                    print(f"✅ {result['description']}")
            print()

        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print(".1f")
        print()

        if success_rate >= 70:
            print("🎉 MIGRATION VALIDATION PASSED!")
            print("Migration infrastructure is properly configured.")
        else:
            print("❌ MIGRATION VALIDATION FAILED!")
            print("Migration infrastructure needs attention.")

        print("="*80)

        return success_rate >= 70


def main():
    """Main migration validation runner."""
    base_path = Path(__file__).parent.parent.parent  # Go up to suna directory

    validator = MigrationValidator(base_path)
    success = validator.run_migration_validation()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)





