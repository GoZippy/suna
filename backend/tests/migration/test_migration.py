"""
Migration testing and rollback validation for Suna system
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch, AsyncMock

from tests import TEST_CONFIG


class TestDataMigration:
    """Test data migration procedures"""
    
    @pytest.mark.migration
    async def test_supabase_data_export(self, database_pool, clean_database):
        """Test Supabase data export functionality"""
        from migration.supabase_export import SupabaseExporter
        
        # Create test data in the database
        await self._create_test_data(database_pool)
        
        # Initialize exporter
        exporter = SupabaseExporter(database_pool)
        
        # Export data
        export_data = await exporter.export_all_data()
        
        # Verify export structure
        assert "users" in export_data
        assert "agents" in export_data
        assert "agent_workflows" in export_data
        assert "knowledge_base" in export_data
        assert "embeddings" in export_data
        
        # Verify data integrity
        assert len(export_data["users"]) > 0
        assert len(export_data["agents"]) > 0
        
        # Verify user data structure
        user = export_data["users"][0]
        assert "id" in user
        assert "email" in user
        assert "username" in user
        assert "full_name" in user
        assert "is_active" in user
        assert "created_at" in user
        
        # Verify agent data structure
        agent = export_data["agents"][0]
        assert "id" in agent
        assert "name" in agent
        assert "description" in agent
        assert "user_id" in agent
        assert "config" in agent
    
    @pytest.mark.migration
    async def test_postgresql_data_import(self, database_pool, clean_database):
        """Test PostgreSQL data import functionality"""
        from migration.postgresql_import import PostgreSQLImporter
        
        # Create test export data
        export_data = self._create_test_export_data()
        
        # Initialize importer
        importer = PostgreSQLImporter(database_pool)
        
        # Import data
        import_result = await importer.import_data(export_data)
        
        # Verify import success
        assert import_result["success"] is True
        assert import_result["imported_tables"] > 0
        assert import_result["imported_records"] > 0
        
        # Verify data was imported correctly
        await self._verify_imported_data(database_pool, export_data)
    
    @pytest.mark.migration
    async def test_schema_migration(self, database_pool, clean_database):
        """Test database schema migration"""
        from migration.schema_migration import SchemaMigrator
        
        # Initialize migrator
        migrator = SchemaMigrator(database_pool)
        
        # Get current schema version
        current_version = await migrator.get_current_version()
        
        # Run migrations
        migration_result = await migrator.run_migrations()
        
        # Verify migration success
        assert migration_result["success"] is True
        assert migration_result["migrations_applied"] >= 0
        
        # Verify schema version was updated
        new_version = await migrator.get_current_version()
        assert new_version >= current_version
    
    @pytest.mark.migration
    async def test_configuration_migration(self, database_pool, clean_database):
        """Test configuration migration from external services"""
        from migration.config_migration import ConfigMigrator
        
        # Create test external configuration
        external_config = self._create_test_external_config()
        
        # Initialize migrator
        migrator = ConfigMigrator(database_pool)
        
        # Migrate configuration
        migration_result = await migrator.migrate_configuration(external_config)
        
        # Verify migration success
        assert migration_result["success"] is True
        assert migration_result["migrated_configs"] > 0
        
        # Verify configuration was migrated correctly
        await self._verify_migrated_config(database_pool, external_config)
    
    @pytest.mark.migration
    async def test_data_validation(self, database_pool, clean_database):
        """Test data validation after migration"""
        from migration.data_validation import DataValidator
        
        # Create test data
        await self._create_test_data(database_pool)
        
        # Initialize validator
        validator = DataValidator(database_pool)
        
        # Validate data integrity
        validation_result = await validator.validate_data_integrity()
        
        # Verify validation success
        assert validation_result["success"] is True
        assert validation_result["total_records"] > 0
        assert validation_result["valid_records"] > 0
        assert validation_result["invalid_records"] == 0
        
        # Verify foreign key constraints
        fk_validation = await validator.validate_foreign_keys()
        assert fk_validation["success"] is True
        assert fk_validation["orphaned_records"] == 0
    
    async def _create_test_data(self, database_pool):
        """Create test data for migration testing"""
        async with database_pool.acquire() as conn:
            # Create test users
            await conn.execute("""
                INSERT INTO users (email, username, full_name, hashed_password, is_active)
                VALUES 
                    ('user1@test.com', 'user1', 'Test User 1', 'hash1', true),
                    ('user2@test.com', 'user2', 'Test User 2', 'hash2', true),
                    ('user3@test.com', 'user3', 'Test User 3', 'hash3', true)
            """)
            
            # Get user IDs
            users = await conn.fetch("SELECT id FROM users ORDER BY id")
            
            # Create test agents
            for i, user in enumerate(users):
                await conn.execute("""
                    INSERT INTO agents (name, description, user_id, is_active, config)
                    VALUES ($1, $2, $3, $4, $5)
                """, f"Test Agent {i+1}", f"Agent {i+1} description", user['id'], True,
                     {"model": "llama2:7b", "temperature": 0.7})
            
            # Get agent IDs
            agents = await conn.fetch("SELECT id FROM agents ORDER BY id")
            
            # Create test workflows
            for i, agent in enumerate(agents):
                await conn.execute("""
                    INSERT INTO agent_workflows (name, description, user_id, agent_id, steps, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, f"Test Workflow {i+1}", f"Workflow {i+1} description", 
                     users[i % len(users)]['id'], agent['id'],
                     [{"step": 1, "action": "search", "params": {"query": "test"}}], True)
    
    def _create_test_export_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Create test export data structure"""
        return {
            "users": [
                {
                    "id": 1,
                    "email": "user1@test.com",
                    "username": "user1",
                    "full_name": "Test User 1",
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": 2,
                    "email": "user2@test.com",
                    "username": "user2",
                    "full_name": "Test User 2",
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ],
            "agents": [
                {
                    "id": 1,
                    "name": "Test Agent 1",
                    "description": "Agent 1 description",
                    "user_id": 1,
                    "is_active": True,
                    "config": {"model": "llama2:7b", "temperature": 0.7},
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": 2,
                    "name": "Test Agent 2",
                    "description": "Agent 2 description",
                    "user_id": 2,
                    "is_active": True,
                    "config": {"model": "llama2:7b", "temperature": 0.8},
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ],
            "agent_workflows": [
                {
                    "id": 1,
                    "name": "Test Workflow 1",
                    "description": "Workflow 1 description",
                    "user_id": 1,
                    "agent_id": 1,
                    "steps": [{"step": 1, "action": "search", "params": {"query": "test"}}],
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ],
            "knowledge_base": [
                {
                    "id": 1,
                    "title": "Test Document",
                    "content": "Test document content",
                    "user_id": 1,
                    "source": "test",
                    "tags": ["test", "documentation"],
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ],
            "embeddings": [
                {
                    "id": 1,
                    "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "metadata": {"text": "test document", "source": "test"},
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
    
    def _create_test_external_config(self) -> Dict[str, Any]:
        """Create test external configuration"""
        return {
            "supabase": {
                "url": "https://test.supabase.co",
                "key": "test-key",
                "secret": "test-secret"
            },
            "openai": {
                "api_key": "test-openai-key",
                "organization": "test-org"
            },
            "stripe": {
                "secret_key": "test-stripe-key",
                "webhook_secret": "test-webhook-secret"
            },
            "email": {
                "smtp_host": "smtp.test.com",
                "smtp_port": 587,
                "username": "test@test.com",
                "password": "test-password"
            }
        }
    
    async def _verify_imported_data(self, database_pool, export_data):
        """Verify that imported data matches export data"""
        async with database_pool.acquire() as conn:
            # Verify users
            users = await conn.fetch("SELECT * FROM users ORDER BY id")
            assert len(users) == len(export_data["users"])
            
            for i, user in enumerate(users):
                export_user = export_data["users"][i]
                assert user["email"] == export_user["email"]
                assert user["username"] == export_user["username"]
                assert user["full_name"] == export_user["full_name"]
            
            # Verify agents
            agents = await conn.fetch("SELECT * FROM agents ORDER BY id")
            assert len(agents) == len(export_data["agents"])
            
            for i, agent in enumerate(agents):
                export_agent = export_data["agents"][i]
                assert agent["name"] == export_agent["name"]
                assert agent["description"] == export_agent["description"]
                assert agent["user_id"] == export_agent["user_id"]
    
    async def _verify_migrated_config(self, database_pool, external_config):
        """Verify that configuration was migrated correctly"""
        async with database_pool.acquire() as conn:
            # Check if configuration was stored
            configs = await conn.fetch("SELECT * FROM system_config WHERE key LIKE 'migrated_%'")
            assert len(configs) > 0
            
            # Verify specific configurations
            for config in configs:
                assert config["key"].startswith("migrated_")
                assert config["value"] is not None


class TestRollbackProcedures:
    """Test rollback procedures for failed migrations"""
    
    @pytest.mark.migration
    async def test_migration_rollback(self, database_pool, clean_database):
        """Test migration rollback functionality"""
        from migration.rollback import MigrationRollback
        
        # Create initial state
        await self._create_test_data(database_pool)
        
        # Create backup
        rollback = MigrationRollback(database_pool)
        backup_id = await rollback.create_backup("test_migration")
        
        # Verify backup was created
        assert backup_id is not None
        
        # Modify data (simulate failed migration)
        async with database_pool.acquire() as conn:
            await conn.execute("UPDATE users SET email = 'modified@test.com' WHERE id = 1")
        
        # Verify modification
        async with database_pool.acquire() as conn:
            user = await conn.fetchrow("SELECT email FROM users WHERE id = 1")
            assert user["email"] == "modified@test.com"
        
        # Rollback to backup
        rollback_result = await rollback.rollback_to_backup(backup_id)
        
        # Verify rollback success
        assert rollback_result["success"] is True
        
        # Verify data was restored
        async with database_pool.acquire() as conn:
            user = await conn.fetchrow("SELECT email FROM users WHERE id = 1")
            assert user["email"] == "user1@test.com"  # Original value
    
    @pytest.mark.migration
    async def test_incremental_rollback(self, database_pool, clean_database):
        """Test incremental rollback functionality"""
        from migration.rollback import MigrationRollback
        
        # Create initial state
        await self._create_test_data(database_pool)
        
        # Create multiple backups
        rollback = MigrationRollback(database_pool)
        backup1 = await rollback.create_backup("step1")
        backup2 = await rollback.create_backup("step2")
        backup3 = await rollback.create_backup("step3")
        
        # Modify data in steps
        async with database_pool.acquire() as conn:
            await conn.execute("UPDATE users SET email = 'step1@test.com' WHERE id = 1")
        
        backup4 = await rollback.create_backup("step4")
        
        async with database_pool.acquire() as conn:
            await conn.execute("UPDATE users SET email = 'step2@test.com' WHERE id = 1")
        
        # Rollback to step 1
        rollback_result = await rollback.rollback_to_backup(backup1)
        assert rollback_result["success"] is True
        
        # Verify rollback to step 1
        async with database_pool.acquire() as conn:
            user = await conn.fetchrow("SELECT email FROM users WHERE id = 1")
            assert user["email"] == "user1@test.com"  # Original value
    
    @pytest.mark.migration
    async def test_backup_verification(self, database_pool, clean_database):
        """Test backup verification functionality"""
        from migration.rollback import MigrationRollback
        
        # Create test data
        await self._create_test_data(database_pool)
        
        # Create backup
        rollback = MigrationRollback(database_pool)
        backup_id = await rollback.create_backup("test_verification")
        
        # Verify backup
        verification_result = await rollback.verify_backup(backup_id)
        
        # Verify backup is valid
        assert verification_result["success"] is True
        assert verification_result["backup_id"] == backup_id
        assert verification_result["record_count"] > 0
        assert verification_result["checksum_valid"] is True
    
    @pytest.mark.migration
    async def test_backup_cleanup(self, database_pool, clean_database):
        """Test backup cleanup functionality"""
        from migration.rollback import MigrationRollback
        
        # Create multiple backups
        rollback = MigrationRollback(database_pool)
        backup1 = await rollback.create_backup("backup1")
        backup2 = await rollback.create_backup("backup2")
        backup3 = await rollback.create_backup("backup3")
        
        # List backups
        backups = await rollback.list_backups()
        assert len(backups) >= 3
        
        # Clean up old backups
        cleanup_result = await rollback.cleanup_old_backups(keep_count=1)
        assert cleanup_result["success"] is True
        assert cleanup_result["deleted_backups"] >= 2
        
        # Verify only one backup remains
        remaining_backups = await rollback.list_backups()
        assert len(remaining_backups) == 1


class TestMigrationValidation:
    """Test migration validation procedures"""
    
    @pytest.mark.migration
    async def test_data_consistency_check(self, database_pool, clean_database):
        """Test data consistency validation"""
        from migration.validation import MigrationValidator
        
        # Create test data
        await self._create_test_data(database_pool)
        
        # Initialize validator
        validator = MigrationValidator(database_pool)
        
        # Check data consistency
        consistency_result = await validator.check_data_consistency()
        
        # Verify consistency
        assert consistency_result["success"] is True
        assert consistency_result["total_checks"] > 0
        assert consistency_result["passed_checks"] > 0
        assert consistency_result["failed_checks"] == 0
    
    @pytest.mark.migration
    async def test_referential_integrity_check(self, database_pool, clean_database):
        """Test referential integrity validation"""
        from migration.validation import MigrationValidator
        
        # Create test data
        await self._create_test_data(database_pool)
        
        # Initialize validator
        validator = MigrationValidator(database_pool)
        
        # Check referential integrity
        integrity_result = await validator.check_referential_integrity()
        
        # Verify integrity
        assert integrity_result["success"] is True
        assert integrity_result["foreign_key_checks"] > 0
        assert integrity_result["orphaned_records"] == 0
        assert integrity_result["broken_references"] == 0
    
    @pytest.mark.migration
    async def test_data_completeness_check(self, database_pool, clean_database):
        """Test data completeness validation"""
        from migration.validation import MigrationValidator
        
        # Create test data
        await self._create_test_data(database_pool)
        
        # Initialize validator
        validator = MigrationValidator(database_pool)
        
        # Check data completeness
        completeness_result = await validator.check_data_completeness()
        
        # Verify completeness
        assert completeness_result["success"] is True
        assert completeness_result["total_records"] > 0
        assert completeness_result["complete_records"] > 0
        assert completeness_result["incomplete_records"] == 0
    
    @pytest.mark.migration
    async def test_performance_validation(self, database_pool, clean_database):
        """Test performance validation after migration"""
        from migration.validation import MigrationValidator
        
        # Create test data
        await self._create_test_data(database_pool)
        
        # Initialize validator
        validator = MigrationValidator(database_pool)
        
        # Check performance
        performance_result = await validator.check_performance()
        
        # Verify performance metrics
        assert performance_result["success"] is True
        assert performance_result["query_performance"] > 0
        assert performance_result["index_usage"] > 0
        assert performance_result["slow_queries"] == 0


class TestMigrationTools:
    """Test migration utility tools"""
    
    @pytest.mark.migration
    async def test_migration_logging(self, database_pool, clean_database):
        """Test migration logging functionality"""
        from migration.logging import MigrationLogger
        
        # Initialize logger
        logger = MigrationLogger(database_pool)
        
        # Log migration events
        await logger.log_event("test_migration", "started", {"step": "initialization"})
        await logger.log_event("test_migration", "progress", {"step": "data_export", "progress": 50})
        await logger.log_event("test_migration", "completed", {"step": "finalization"})
        
        # Retrieve logs
        logs = await logger.get_migration_logs("test_migration")
        
        # Verify logs
        assert len(logs) == 3
        assert logs[0]["event_type"] == "started"
        assert logs[1]["event_type"] == "progress"
        assert logs[2]["event_type"] == "completed"
    
    @pytest.mark.migration
    async def test_migration_monitoring(self, database_pool, clean_database):
        """Test migration monitoring functionality"""
        from migration.monitoring import MigrationMonitor
        
        # Initialize monitor
        monitor = MigrationMonitor(database_pool)
        
        # Start monitoring
        await monitor.start_monitoring("test_migration")
        
        # Simulate migration progress
        await monitor.update_progress("test_migration", 25)
        await monitor.update_progress("test_migration", 50)
        await monitor.update_progress("test_migration", 75)
        await monitor.update_progress("test_migration", 100)
        
        # Get migration status
        status = await monitor.get_migration_status("test_migration")
        
        # Verify status
        assert status["migration_id"] == "test_migration"
        assert status["progress"] == 100
        assert status["status"] == "completed"
        
        # Stop monitoring
        await monitor.stop_monitoring("test_migration")
    
    @pytest.mark.migration
    async def test_migration_reporting(self, database_pool, clean_database):
        """Test migration reporting functionality"""
        from migration.reporting import MigrationReporter
        
        # Create test data
        await self._create_test_data(database_pool)
        
        # Initialize reporter
        reporter = MigrationReporter(database_pool)
        
        # Generate migration report
        report = await reporter.generate_report("test_migration")
        
        # Verify report structure
        assert "migration_id" in report
        assert "start_time" in report
        assert "end_time" in report
        assert "duration" in report
        assert "status" in report
        assert "records_migrated" in report
        assert "errors" in report
        assert "warnings" in report
        
        # Verify report content
        assert report["migration_id"] == "test_migration"
        assert report["status"] == "completed"
        assert report["records_migrated"] > 0
        assert len(report["errors"]) == 0







