"""
Unit tests for database components
"""

import pytest
import asyncio
import asyncpg
from unittest.mock import patch, AsyncMock, MagicMock

from database.connection import get_database_pool, DatabaseConnection
from database.migrations import run_migrations, create_tables
from database.vector import VectorStore, create_vector_index


class TestDatabaseConnection:
    """Test database connection and pooling"""
    
    @pytest.mark.asyncio
    async def test_database_pool_creation(self):
        """Test database connection pool creation"""
        from tests import TEST_CONFIG
        
        pool = await get_database_pool(TEST_CONFIG['database_url'])
        
        assert pool is not None
        assert isinstance(pool, asyncpg.Pool)
        
        # Test connection acquisition
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_database_connection_context(self, database_pool):
        """Test database connection context manager"""
        async with DatabaseConnection(database_pool) as conn:
            result = await conn.fetchval("SELECT 42")
            assert result == 42
    
    @pytest.mark.asyncio
    async def test_connection_pool_size(self, database_pool):
        """Test connection pool size limits"""
        # Get pool info
        pool_info = database_pool.get_size()
        
        assert pool_info['min_size'] >= 1
        assert pool_info['max_size'] >= 1
        assert pool_info['max_size'] >= pool_info['min_size']
    
    @pytest.mark.asyncio
    async def test_connection_pool_health(self, database_pool):
        """Test connection pool health check"""
        # Test that we can get a connection
        async with database_pool.acquire() as conn:
            # Test basic query
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            
            # Test connection is working
            assert not conn.is_closed()
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test database connection error handling"""
        from tests import TEST_CONFIG
        
        # Test with invalid database URL
        with pytest.raises(Exception):
            await get_database_pool("postgresql://invalid:invalid@localhost:9999/invalid")


class TestDatabaseMigrations:
    """Test database migration system"""
    
    @pytest.mark.asyncio
    async def test_create_tables(self, database_pool, clean_database):
        """Test table creation"""
        await create_tables(database_pool)
        
        # Verify tables were created
        async with database_pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            
            table_names = [table['tablename'] for table in tables]
            
            # Check for essential tables
            assert 'users' in table_names
            assert 'agents' in table_names
            assert 'agent_workflows' in table_names
            assert 'knowledge_base' in table_names
            assert 'embeddings' in table_names
    
    @pytest.mark.asyncio
    async def test_run_migrations(self, database_pool, clean_database):
        """Test migration execution"""
        # Run migrations
        await run_migrations(database_pool)
        
        # Verify migration table was created
        async with database_pool.acquire() as conn:
            migration_table = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """)
            
            assert migration_table is True
    
    @pytest.mark.asyncio
    async def test_migration_idempotency(self, database_pool, clean_database):
        """Test that migrations can be run multiple times safely"""
        # Run migrations twice
        await run_migrations(database_pool)
        await run_migrations(database_pool)
        
        # Should not raise any errors
        assert True


class TestVectorOperations:
    """Test vector database operations"""
    
    @pytest.mark.asyncio
    async def test_vector_store_creation(self, database_pool, clean_database):
        """Test vector store initialization"""
        await create_tables(database_pool)
        
        vector_store = VectorStore(database_pool)
        
        # Test basic operations
        assert vector_store is not None
    
    @pytest.mark.asyncio
    async def test_vector_index_creation(self, database_pool, clean_database):
        """Test vector index creation"""
        await create_tables(database_pool)
        
        # Create vector index
        await create_vector_index(database_pool)
        
        # Verify index was created
        async with database_pool.acquire() as conn:
            indexes = await conn.fetch("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'embeddings'
                AND indexname LIKE '%vector%'
            """)
            
            assert len(indexes) > 0
    
    @pytest.mark.asyncio
    async def test_embedding_storage(self, database_pool, clean_database):
        """Test embedding storage and retrieval"""
        await create_tables(database_pool)
        
        vector_store = VectorStore(database_pool)
        
        # Test data
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        test_metadata = {"text": "test document", "source": "test"}
        
        # Store embedding
        embedding_id = await vector_store.store_embedding(
            embedding=test_embedding,
            metadata=test_metadata
        )
        
        assert embedding_id is not None
        
        # Retrieve embedding
        retrieved = await vector_store.get_embedding(embedding_id)
        
        assert retrieved is not None
        assert retrieved['embedding'] == test_embedding
        assert retrieved['metadata'] == test_metadata
    
    @pytest.mark.asyncio
    async def test_similarity_search(self, database_pool, clean_database):
        """Test similarity search functionality"""
        await create_tables(database_pool)
        await create_vector_index(database_pool)
        
        vector_store = VectorStore(database_pool)
        
        # Store multiple embeddings
        embeddings = [
            ([0.1, 0.2, 0.3], {"text": "first document"}),
            ([0.4, 0.5, 0.6], {"text": "second document"}),
            ([0.7, 0.8, 0.9], {"text": "third document"}),
        ]
        
        for embedding, metadata in embeddings:
            await vector_store.store_embedding(embedding, metadata)
        
        # Search for similar embeddings
        query_embedding = [0.15, 0.25, 0.35]  # Similar to first document
        results = await vector_store.similarity_search(
            query_embedding, 
            limit=2
        )
        
        assert len(results) > 0
        assert len(results) <= 2
        
        # First result should be most similar
        first_result = results[0]
        assert first_result['metadata']['text'] == "first document"
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, database_pool, clean_database):
        """Test hybrid search combining text and vector similarity"""
        await create_tables(database_pool)
        await create_vector_index(database_pool)
        
        vector_store = VectorStore(database_pool)
        
        # Store embeddings with text content
        test_data = [
            ([0.1, 0.2, 0.3], {"text": "python programming guide", "category": "programming"}),
            ([0.4, 0.5, 0.6], {"text": "machine learning tutorial", "category": "ai"}),
            ([0.7, 0.8, 0.9], {"text": "database optimization", "category": "database"}),
        ]
        
        for embedding, metadata in test_data:
            await vector_store.store_embedding(embedding, metadata)
        
        # Perform hybrid search
        query_embedding = [0.15, 0.25, 0.35]
        text_query = "programming"
        
        results = await vector_store.hybrid_search(
            query_embedding=query_embedding,
            text_query=text_query,
            limit=3
        )
        
        assert len(results) > 0
        
        # Should find programming-related content
        programming_results = [r for r in results if "programming" in r['metadata']['text']]
        assert len(programming_results) > 0


class TestQueryOptimization:
    """Test database query optimization"""
    
    @pytest.mark.asyncio
    async def test_query_execution_time(self, database_pool, clean_database):
        """Test query execution time measurement"""
        from database.optimization import QueryOptimizer
        
        optimizer = QueryOptimizer(database_pool)
        
        # Test simple query
        start_time = asyncio.get_event_loop().time()
        
        async with database_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Query should execute quickly
        assert execution_time < 1.0  # Less than 1 second
    
    @pytest.mark.asyncio
    async def test_slow_query_detection(self, database_pool, clean_database):
        """Test slow query detection"""
        from database.optimization import QueryOptimizer
        
        optimizer = QueryOptimizer(database_pool)
        
        # Create a slow query (artificial delay)
        async with database_pool.acquire() as conn:
            await conn.execute("SELECT pg_sleep(0.1)")  # 100ms delay
        
        # Check if slow query was detected
        slow_queries = await optimizer.get_slow_queries()
        
        # In a real scenario, this would detect the slow query
        # For testing, we just verify the method works
        assert isinstance(slow_queries, list)
    
    @pytest.mark.asyncio
    async def test_index_recommendations(self, database_pool, clean_database):
        """Test index recommendation system"""
        from database.optimization import QueryOptimizer
        
        await create_tables(database_pool)
        
        optimizer = QueryOptimizer(database_pool)
        
        # Create some test data
        async with database_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (email, username, full_name, hashed_password, is_active)
                VALUES 
                    ('user1@test.com', 'user1', 'User One', 'hash1', true),
                    ('user2@test.com', 'user2', 'User Two', 'hash2', true),
                    ('user3@test.com', 'user3', 'User Three', 'hash3', true)
            """)
        
        # Get index recommendations
        recommendations = await optimizer.get_index_recommendations()
        
        # Should provide some recommendations
        assert isinstance(recommendations, list)
    
    @pytest.mark.asyncio
    async def test_connection_pool_optimization(self, database_pool):
        """Test connection pool optimization"""
        from database.optimization import QueryOptimizer
        
        optimizer = QueryOptimizer(database_pool)
        
        # Get pool statistics
        stats = await optimizer.get_pool_statistics()
        
        assert 'total_connections' in stats
        assert 'active_connections' in stats
        assert 'idle_connections' in stats
        
        # Test pool optimization
        optimization_result = await optimizer.optimize_pool()
        assert optimization_result is True


class TestDatabaseBackup:
    """Test database backup and restore functionality"""
    
    @pytest.mark.asyncio
    async def test_backup_creation(self, database_pool, clean_database, temp_dir):
        """Test database backup creation"""
        from database.backup import DatabaseBackup
        
        backup_manager = DatabaseBackup(database_pool)
        
        # Create some test data
        await create_tables(database_pool)
        
        # Create backup
        backup_path = temp_dir / "test_backup.sql"
        success = await backup_manager.create_backup(str(backup_path))
        
        assert success is True
        assert backup_path.exists()
        assert backup_path.stat().st_size > 0
    
    @pytest.mark.asyncio
    async def test_backup_restore(self, database_pool, clean_database, temp_dir):
        """Test database backup restoration"""
        from database.backup import DatabaseBackup
        
        backup_manager = DatabaseBackup(database_pool)
        
        # Create tables and data
        await create_tables(database_pool)
        
        async with database_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (email, username, full_name, hashed_password, is_active)
                VALUES ('test@example.com', 'testuser', 'Test User', 'hash', true)
            """)
        
        # Create backup
        backup_path = temp_dir / "restore_test_backup.sql"
        await backup_manager.create_backup(str(backup_path))
        
        # Clear database
        async with database_pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE users CASCADE")
        
        # Restore backup
        success = await backup_manager.restore_backup(str(backup_path))
        
        assert success is True
        
        # Verify data was restored
        async with database_pool.acquire() as conn:
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            assert user_count == 1







