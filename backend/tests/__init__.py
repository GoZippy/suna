"""
Suna Comprehensive Testing Suite

This package contains all testing components for the self-hosted migration:
- Unit tests for authentication and database components
- Integration tests for multi-service interactions
- End-to-end tests for complete user workflows
- Performance testing and load testing procedures
- Migration testing and rollback validation
- Security testing and vulnerability scanning
"""

import os
import sys
import pytest
from pathlib import Path

# Add the backend directory to the Python path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Test configuration
TEST_CONFIG = {
    'database_url': os.getenv('TEST_DATABASE_URL', 'postgresql://test:test@localhost:5491/suna_test'),
    'redis_url': os.getenv('TEST_REDIS_URL', 'redis://localhost:6391'),
    'api_base_url': os.getenv('TEST_API_URL', 'http://localhost:8091'),
    'frontend_url': os.getenv('TEST_FRONTEND_URL', 'http://localhost:3091'),
    'test_timeout': int(os.getenv('TEST_TIMEOUT', '30')),
    'performance_threshold': float(os.getenv('PERFORMANCE_THRESHOLD', '2.0')),
    'load_test_duration': int(os.getenv('LOAD_TEST_DURATION', '60')),
    'load_test_users': int(os.getenv('LOAD_TEST_USERS', '10')),
}

# Test categories
TEST_CATEGORIES = {
    'unit': 'Unit tests for individual components',
    'integration': 'Integration tests for service interactions',
    'e2e': 'End-to-end tests for complete workflows',
    'performance': 'Performance and load testing',
    'migration': 'Migration and rollback testing',
    'security': 'Security and vulnerability testing',
}

__all__ = ['TEST_CONFIG', 'TEST_CATEGORIES']







