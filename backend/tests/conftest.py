"""
Pytest configuration and fixtures for Suna testing suite
"""

import pytest
import asyncio
import aiohttp
import asyncpg
import redis
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from tests import TEST_CONFIG
from auth.models import User, UserCreate
from auth.jwt import create_access_token
from database.connection import get_database_pool
from services.cache import CacheManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def database_pool():
    """Create a database connection pool for testing."""
    pool = await asyncpg.create_pool(
        TEST_CONFIG['database_url'],
        min_size=1,
        max_size=10
    )
    yield pool
    await pool.close()


@pytest.fixture(scope="session")
async def redis_client():
    """Create a Redis client for testing."""
    client = redis.from_url(TEST_CONFIG['redis_url'])
    yield client
    client.close()


@pytest.fixture
async def clean_database(database_pool):
    """Clean the database before each test."""
    async with database_pool.acquire() as conn:
        # Get all table names
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'pg_%'
        """)
        
        # Disable foreign key checks and truncate all tables
        await conn.execute('SET session_replication_role = replica;')
        for table in tables:
            await conn.execute(f'TRUNCATE TABLE {table["tablename"]} CASCADE;')
        await conn.execute('SET session_replication_role = DEFAULT;')


@pytest.fixture
async def clean_redis(redis_client):
    """Clean Redis before each test."""
    redis_client.flushdb()


@pytest.fixture
async def test_user(database_pool) -> User:
    """Create a test user for authentication tests."""
    async with database_pool.acquire() as conn:
        user_data = UserCreate(
            email="test@example.com",
            password="testpassword123",
            username="testuser",
            full_name="Test User"
        )
        
        # Hash password
        from auth.password import hash_password
        hashed_password = hash_password(user_data.password)
        
        # Insert user
        user = await conn.fetchrow("""
            INSERT INTO users (email, username, full_name, hashed_password, is_active)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, email, username, full_name, is_active, created_at
        """, user_data.email, user_data.username, user_data.full_name, 
             hashed_password, True)
        
        return User(**dict(user))


@pytest.fixture
async def auth_headers(test_user) -> dict:
    """Create authentication headers for API tests."""
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def aiohttp_client():
    """Create an aiohttp client for API testing."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file operations."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
async def cache_manager(redis_client):
    """Create a cache manager for testing."""
    manager = CacheManager(TEST_CONFIG['redis_url'])
    yield manager
    await manager.cleanup()


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing."""
    mock_client = AsyncMock()
    mock_client.generate.return_value = {
        "response": "This is a test response",
        "done": True,
        "model": "llama2:7b"
    }
    mock_client.embeddings.return_value = {
        "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]]
    }
    return mock_client


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for container testing."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "test-container-id"
    mock_container.status = "running"
    mock_container.ports = {"8080/tcp": [{"HostPort": "8080"}]}
    mock_client.containers.get.return_value = mock_container
    mock_client.containers.run.return_value = mock_container
    return mock_client


@pytest.fixture
def mock_prometheus_client():
    """Mock Prometheus client for monitoring tests."""
    mock_client = MagicMock()
    mock_client.Counter.return_value = MagicMock()
    mock_client.Gauge.return_value = MagicMock()
    mock_client.Histogram.return_value = MagicMock()
    return mock_client


@pytest.fixture
async def test_agent(database_pool, test_user):
    """Create a test agent for agent-related tests."""
    async with database_pool.acquire() as conn:
        agent = await conn.fetchrow("""
            INSERT INTO agents (name, description, user_id, is_active, config)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, name, description, user_id, is_active, config
        """, "Test Agent", "A test agent", test_user.id, True, 
             {"model": "llama2:7b", "temperature": 0.7})
        
        return dict(agent)


@pytest.fixture
async def test_workflow(database_pool, test_user, test_agent):
    """Create a test workflow for workflow-related tests."""
    async with database_pool.acquire() as conn:
        workflow = await conn.fetchrow("""
            INSERT INTO agent_workflows (name, description, user_id, agent_id, steps, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, name, description, user_id, agent_id, steps, is_active
        """, "Test Workflow", "A test workflow", test_user.id, test_agent['id'],
             [{"step": 1, "action": "search", "params": {"query": "test"}}], True)
        
        return dict(workflow)


@pytest.fixture
def performance_threshold():
    """Get performance threshold for tests."""
    return TEST_CONFIG['performance_threshold']


@pytest.fixture
def load_test_config():
    """Get load test configuration."""
    return {
        'duration': TEST_CONFIG['load_test_duration'],
        'users': TEST_CONFIG['load_test_users'],
        'base_url': TEST_CONFIG['api_base_url']
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "migration: mark test as a migration test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "migration" in str(item.fspath):
            item.add_marker(pytest.mark.migration)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        
        # Add slow marker for tests that take longer
        if any(keyword in item.name.lower() for keyword in ['load', 'stress', 'performance']):
            item.add_marker(pytest.mark.slow)







