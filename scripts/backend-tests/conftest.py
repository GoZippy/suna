import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import your FastAPI app
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from api import app
from services.supabase import DBConnection
from utils.config import config

# Test database configuration
TEST_DATABASE_URL = "postgresql://test:test@localhost:5491/suna_test"
TEST_REDIS_URL = "redis://localhost:6391"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_db():
    """Create test database connection."""
    engine = create_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    # Base.metadata.create_all(bind=engine)
    
    yield TestingSessionLocal()
    
    # Cleanup
    engine.dispose()

@pytest.fixture
def db_session(test_db):
    """Create a fresh database session for each test."""
    yield test_db
    test_db.rollback()

@pytest.fixture
def client() -> Generator:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_user():
    """Mock user data for testing."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "role": "user",
        "tier": "free",
        "is_active": True
    }

@pytest.fixture
def mock_agent():
    """Mock agent data for testing."""
    return {
        "id": "test-agent-id",
        "name": "Test Agent",
        "description": "A test agent",
        "user_id": "test-user-id",
        "is_active": True,
        "tools_count": 5
    }

@pytest.fixture
def mock_thread():
    """Mock thread data for testing."""
    return {
        "id": "test-thread-id",
        "user_id": "test-user-id",
        "agent_id": "test-agent-id",
        "title": "Test Thread",
        "is_active": True
    }

@pytest.fixture
def auth_headers(mock_user):
    """Generate authentication headers for testing."""
    # Mock JWT token generation
    token = "mock-jwt-token"
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers(mock_user):
    """Generate admin authentication headers for testing."""
    mock_user["role"] = "admin"
    token = "mock-admin-jwt-token"
    return {"Authorization": f"Bearer {token}"}

# Test utilities
class TestUtils:
    @staticmethod
    def create_test_user(db_session, user_data=None):
        """Create a test user in the database."""
        if user_data is None:
            user_data = {
                "email": "test@example.com",
                "password_hash": "hashed_password",
                "role": "user",
                "tier": "free"
            }
        # Implementation depends on your user model
        pass

    @staticmethod
    def create_test_agent(db_session, agent_data=None):
        """Create a test agent in the database."""
        if agent_data is None:
            agent_data = {
                "name": "Test Agent",
                "description": "A test agent",
                "user_id": "test-user-id"
            }
        # Implementation depends on your agent model
        pass

    @staticmethod
    def cleanup_test_data(db_session):
        """Clean up test data from the database."""
        # Implementation depends on your models
        pass

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_security" in item.nodeid:
            item.add_marker(pytest.mark.security)
        else:
            item.add_marker(pytest.mark.unit)







