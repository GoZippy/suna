# Suna Comprehensive Testing Suite

This directory contains a comprehensive testing suite for the Suna self-hosted migration project. The testing suite covers all aspects of the system including unit tests, integration tests, end-to-end tests, performance tests, migration tests, and security tests.

## 📋 Test Categories

The testing suite is organized into the following categories:

| Category | Description | Location |
|----------|-------------|----------|
| **Unit Tests** | Individual component testing | `tests/unit/` |
| **Integration Tests** | Multi-service interaction testing | `tests/integration/` |
| **End-to-End Tests** | Complete user workflow testing | `tests/e2e/` |
| **Performance Tests** | Load testing and performance validation | `tests/performance/` |
| **Migration Tests** | Data migration and rollback testing | `tests/migration/` |
| **Security Tests** | Security and vulnerability testing | `tests/security/` |

## 🚀 Quick Start

### Prerequisites

1. **Python Dependencies**
   ```bash
   pip install pytest pytest-asyncio pytest-cov pytest-xdist aiohttp redis asyncpg
   ```

2. **Test Database**
   ```bash
   # Create test database
   createdb suna_test
   
   # Set environment variables
   export TEST_DATABASE_URL="postgresql://test:test@localhost:5491/suna_test"
   export TEST_REDIS_URL="redis://localhost:6391"
   ```

3. **Test Services**
   ```bash
   # Start test services (if not already running)
   docker-compose up -d postgres redis
   ```

### Running Tests

#### Basic Test Execution

```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --categories unit integration

# Run tests with specific markers
python tests/run_tests.py --markers security performance
```

#### Advanced Test Execution

```bash
# Run tests in parallel with coverage
python tests/run_tests.py --parallel --coverage

# Generate JSON report
python tests/run_tests.py --output-format json --save-report

# Run against staging environment
python tests/run_tests.py --env staging
```

#### Direct Pytest Usage

```bash
# Run unit tests only
pytest tests/unit/ -v

# Run integration tests with coverage
pytest tests/integration/ --cov=. --cov-report=html

# Run performance tests (slow tests)
pytest tests/performance/ -m "slow" -v

# Run security tests
pytest tests/security/ -m "security" -v
```

## 📊 Test Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_DATABASE_URL` | `postgresql://test:test@localhost:5491/suna_test` | Test database connection |
| `TEST_REDIS_URL` | `redis://localhost:6391` | Test Redis connection |
| `TEST_API_URL` | `http://localhost:8091` | Test API base URL |
| `TEST_FRONTEND_URL` | `http://localhost:3091` | Test frontend URL |
| `TEST_TIMEOUT` | `30` | Test timeout in seconds |
| `PERFORMANCE_THRESHOLD` | `2.0` | Performance threshold for tests |
| `LOAD_TEST_DURATION` | `60` | Load test duration in seconds |
| `LOAD_TEST_USERS` | `10` | Number of concurrent users for load tests |

### Test Markers

| Marker | Description | Usage |
|--------|-------------|-------|
| `unit` | Unit tests | `pytest -m unit` |
| `integration` | Integration tests | `pytest -m integration` |
| `e2e` | End-to-end tests | `pytest -m e2e` |
| `performance` | Performance tests | `pytest -m performance` |
| `migration` | Migration tests | `pytest -m migration` |
| `security` | Security tests | `pytest -m security` |
| `slow` | Slow running tests | `pytest -m slow` |

## 🧪 Test Components

### 1. Unit Tests (`tests/unit/`)

Unit tests focus on individual components and functions:

- **Authentication Tests** (`test_auth.py`)
  - Password hashing and verification
  - JWT token creation and validation
  - User model validation
  - Authentication service functions

- **Database Tests** (`test_database.py`)
  - Database connection and pooling
  - Migration system
  - Vector operations
  - Query optimization
  - Backup and restore

### 2. Integration Tests (`tests/integration/`)

Integration tests verify multi-service interactions:

- **API Endpoint Tests** (`test_api_endpoints.py`)
  - Authentication endpoints
  - Agent management endpoints
  - Workflow endpoints
  - Knowledge base endpoints
  - File management endpoints
  - Search endpoints
  - Monitoring endpoints

### 3. End-to-End Tests (`tests/e2e/`)

E2E tests simulate complete user workflows:

- **User Registration Workflow** (`test_end_to_end.py`)
  - Complete user registration to first agent
  - User onboarding flow

- **Agent Workflow Execution**
  - Agent workflow creation and execution
  - Agent interaction workflow

- **File Management Workflow**
  - File upload and processing

- **Knowledge Base Workflow**
  - Knowledge base management

- **System Integration Workflow**
  - Complete user journey
  - Multi-user collaboration

### 4. Performance Tests (`tests/performance/`)

Performance tests validate system performance:

- **Load Testing** (`test_load_testing.py`)
  - Concurrent user registration
  - Concurrent agent creation
  - Database query performance

- **Stress Testing**
  - High concurrency stress
  - Memory leak detection

- **Performance Monitoring**
  - Metrics collection
  - Bottleneck identification

### 5. Migration Tests (`tests/migration/`)

Migration tests ensure data migration reliability:

- **Data Migration** (`test_migration.py`)
  - Supabase data export
  - PostgreSQL data import
  - Schema migration
  - Configuration migration
  - Data validation

- **Rollback Procedures**
  - Migration rollback
  - Incremental rollback
  - Backup verification
  - Backup cleanup

- **Migration Validation**
  - Data consistency checks
  - Referential integrity
  - Data completeness
  - Performance validation

### 6. Security Tests (`tests/security/`)

Security tests validate system security:

- **Authentication Security** (`test_security.py`)
  - Password strength validation
  - SQL injection prevention
  - JWT token security
  - Brute force protection
  - Session management

- **Input Validation**
  - XSS prevention
  - Path traversal prevention
  - Command injection prevention
  - Content type validation

- **Authorization Security**
  - Unauthorized access prevention
  - Resource isolation
  - Admin access control
  - Method authorization

- **Data Protection**
  - Sensitive data exposure
  - Error information disclosure
  - Logging sanitization

- **Network Security**
  - HTTPS enforcement
  - CORS configuration
  - Security headers

- **Vulnerability Scanning**
  - Dependency vulnerability checks
  - Container vulnerability scanning
  - Secret scanning

## 🔧 Test Fixtures

The testing suite provides comprehensive fixtures in `conftest.py`:

### Database Fixtures
- `database_pool`: Database connection pool
- `clean_database`: Database cleanup between tests
- `test_user`: Test user for authentication
- `test_agent`: Test agent for agent-related tests
- `test_workflow`: Test workflow for workflow-related tests

### Service Fixtures
- `redis_client`: Redis client
- `aiohttp_client`: HTTP client for API testing
- `cache_manager`: Cache manager for testing
- `temp_dir`: Temporary directory for file operations

### Mock Fixtures
- `mock_ollama_client`: Mock Ollama client
- `mock_docker_client`: Mock Docker client
- `mock_prometheus_client`: Mock Prometheus client

## 📈 Test Reporting

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Generate coverage report in terminal
pytest --cov=. --cov-report=term-missing

# Generate JSON coverage report
pytest --cov=. --cov-report=json:coverage.json
```

### Test Reports

```bash
# Generate JSON test report
python tests/run_tests.py --output-format json --save-report

# Generate JUnit XML report
python tests/run_tests.py --output-format junit
```

### Performance Reports

Performance tests generate detailed metrics including:
- Response times (average, min, max, p95, p99)
- Throughput (requests per second)
- Error rates
- Resource utilization

## 🚨 Continuous Integration

### GitHub Actions

The testing suite is integrated with GitHub Actions:

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: suna_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5491:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6391:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov pytest-xdist aiohttp redis asyncpg
      
      - name: Run tests
        run: |
          python tests/run_tests.py --parallel --coverage --save-report
        env:
          TEST_DATABASE_URL: postgresql://postgres:test@localhost:5491/suna_test
          TEST_REDIS_URL: redis://localhost:6391
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.json
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Ensure PostgreSQL is running
   sudo systemctl start postgresql
   
   # Create test database
   createdb suna_test
   
   # Check connection
   psql -h localhost -p 5491 -U test -d suna_test
   ```

2. **Redis Connection Errors**
   ```bash
   # Ensure Redis is running
   sudo systemctl start redis
   
   # Check connection
   redis-cli -h localhost -p 6391 ping
   ```

3. **Test Timeout Issues**
   ```bash
   # Increase timeout for slow tests
   export TEST_TIMEOUT=60
   
   # Run only fast tests
   pytest -m "not slow"
   ```

4. **Memory Issues**
   ```bash
   # Run tests with reduced parallelism
   pytest -n 2
   
   # Run tests sequentially
   pytest -n 0
   ```

### Debug Mode

```bash
# Run tests with debug output
pytest -v -s --tb=long

# Run specific test with debug
pytest tests/unit/test_auth.py::TestPasswordHashing::test_hash_password -v -s
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Aiohttp Testing Guide](https://docs.aiohttp.org/en/stable/testing.html)
- [AsyncPG Documentation](https://magicstack.github.io/asyncpg/)

## 🤝 Contributing

When adding new tests:

1. **Follow the existing structure** and place tests in appropriate categories
2. **Use descriptive test names** that explain what is being tested
3. **Add appropriate markers** for test categorization
4. **Include comprehensive assertions** to validate behavior
5. **Add documentation** for complex test scenarios
6. **Ensure tests are isolated** and don't depend on each other
7. **Use fixtures** for common setup and teardown

### Test Naming Convention

- Test files: `test_<component>.py`
- Test classes: `Test<Component>`
- Test methods: `test_<scenario>_<expected_behavior>`

Example:
```python
class TestAuthentication:
    def test_user_login_with_valid_credentials_returns_token(self):
        # Test implementation
        pass
```







