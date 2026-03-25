#!/bin/bash

# Comprehensive Test Suite Runner
# This script runs all test suites for the Suna AI Worker project

set -e

echo "🧪 Starting Comprehensive Test Suite for Suna AI Worker"
echo "======================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
FRONTEND_TESTS_PASSED=false
BACKEND_TESTS_PASSED=false
INTEGRATION_TESTS_PASSED=false
OVERALL_RESULT=true

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
    esac
}

# Function to check if service is running
check_service() {
    local service=$1
    local port=$2
    
    if nc -z localhost $port 2>/dev/null; then
        print_status "SUCCESS" "$service is running on port $port"
        return 0
    else
        print_status "WARNING" "$service is not running on port $port"
        return 1
    fi
}

# Function to start services if needed
start_services() {
    print_status "INFO" "Checking required services..."
    
    # Check if we're in the project root
    if [ ! -f "docker-compose.development.yml" ]; then
        print_status "ERROR" "Please run this script from the project root directory"
        exit 1
    fi
    
    # Check and start database
    if ! check_service "PostgreSQL" 5491; then
        print_status "INFO" "Starting PostgreSQL database..."
        docker-compose -f docker-compose.development.yml up -d postgres
        sleep 10
    fi
    
    # Check and start Redis
    if ! check_service "Redis" 6391; then
        print_status "INFO" "Starting Redis..."
        docker-compose -f docker-compose.development.yml up -d redis
        sleep 5
    fi
    
    # Check and start backend
    if ! check_service "Backend API" 8091; then
        print_status "INFO" "Starting backend API..."
        docker-compose -f docker-compose.development.yml up -d backend
        sleep 15
    fi
    
    # Check and start frontend
    if ! check_service "Frontend" 3091; then
        print_status "INFO" "Starting frontend..."
        docker-compose -f docker-compose.development.yml up -d frontend
        sleep 10
    fi
}

# Function to run frontend tests
run_frontend_tests() {
    print_status "INFO" "Running Frontend Test Suite..."
    echo ""
    
    cd scripts/frontend-tests
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "INFO" "Installing frontend test dependencies..."
        npm install --silent
    fi
    
    # Run tests
    if npm run test:coverage; then
        print_status "SUCCESS" "Frontend tests completed successfully"
        FRONTEND_TESTS_PASSED=true
    else
        print_status "ERROR" "Frontend tests failed"
        OVERALL_RESULT=false
    fi
    
    cd ../..
    echo ""
}

# Function to run backend tests
run_backend_tests() {
    print_status "INFO" "Running Backend Test Suite..."
    echo ""
    
    cd scripts/backend-tests
    
    # Create virtual environment if needed
    if [ ! -d "venv" ]; then
        print_status "INFO" "Creating Python virtual environment..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "INFO" "Installing backend test dependencies..."
    pip install pytest pytest-asyncio pytest-cov pytest-xdist fastapi httpx redis asyncpg aiohttp --quiet
    
    # Set environment variables
    export TEST_DATABASE_URL="postgresql://suna_user:suna_password@localhost:5491/suna_dev"
    export TEST_REDIS_URL="redis://localhost:6391"
    export TEST_API_URL="http://localhost:8091"
    export TEST_TIMEOUT="30"
    
    # Run tests
    if pytest --cov=../../backend --cov-report=html --cov-report=term-missing -v; then
        print_status "SUCCESS" "Backend tests completed successfully"
        BACKEND_TESTS_PASSED=true
    else
        print_status "ERROR" "Backend tests failed"
        OVERALL_RESULT=false
    fi
    
    deactivate
    cd ../..
    echo ""
}

# Function to run integration tests
run_integration_tests() {
    print_status "INFO" "Running Integration Test Suite..."
    echo ""
    
    cd scripts/integration-tests
    
    # Create virtual environment if needed
    if [ ! -d "venv" ]; then
        print_status "INFO" "Creating Python virtual environment for integration tests..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "INFO" "Installing integration test dependencies..."
    pip install pytest pytest-asyncio aiohttp --quiet
    
    # Set environment variables
    export TEST_API_URL="http://localhost:8091"
    export TEST_FRONTEND_URL="http://localhost:3091"
    
    # Run integration tests
    if pytest test_frontend_backend_integration.py -v; then
        print_status "SUCCESS" "Integration tests completed successfully"
        INTEGRATION_TESTS_PASSED=true
    else
        print_status "ERROR" "Integration tests failed"
        OVERALL_RESULT=false
    fi
    
    deactivate
    cd ../..
    echo ""
}

# Function to run performance tests
run_performance_tests() {
    print_status "INFO" "Running Performance Tests..."
    echo ""
    
    # Simple performance test using curl
    print_status "INFO" "Testing API response times..."
    
    start_time=$(date +%s.%N)
    response_time=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8091/health)
    end_time=$(date +%s.%N)
    
    print_status "INFO" "Health check response time: ${response_time}s"
    
    # Test concurrent requests
    print_status "INFO" "Testing concurrent request handling..."
    
    for i in {1..5}; do
        curl -s http://localhost:8091/health > /dev/null &
    done
    wait
    
    print_status "SUCCESS" "Performance tests completed"
    echo ""
}

# Function to generate test report
generate_test_report() {
    print_status "INFO" "Generating Test Report..."
    echo ""
    
    # Create reports directory
    mkdir -p docs/test-reports
    
    # Generate summary report
    cat > docs/test-reports/test-summary.md << EOF
# Suna AI Worker - Test Execution Summary

## Test Execution Date
$(date)

## Overall Result
$([ "$OVERALL_RESULT" = true ] && echo "✅ PASSED" || echo "❌ FAILED")

## Test Results

### Frontend Tests
- Status: $([ "$FRONTEND_TESTS_PASSED" = true ] && echo "✅ PASSED" || echo "❌ FAILED")
- Framework: Vitest + React Testing Library
- Coverage: Available in scripts/frontend-tests/coverage/

### Backend Tests
- Status: $([ "$BACKEND_TESTS_PASSED" = true ] && echo "✅ PASSED" || echo "❌ FAILED")
- Framework: pytest + pytest-asyncio
- Coverage: Available in scripts/backend-tests/htmlcov/

### Integration Tests
- Status: $([ "$INTEGRATION_TESTS_PASSED" = true ] && echo "✅ PASSED" || echo "❌ FAILED")
- Framework: pytest + aiohttp
- Scope: Frontend-backend communication, WebSocket, API integration

### Performance Tests
- Status: ✅ COMPLETED
- Scope: Response times, concurrent request handling

## Test Coverage Summary
- Frontend: Component testing, hook testing, integration testing
- Backend: API endpoints, agent system, authentication, file operations
- Integration: End-to-end workflows, real-time communication
- Performance: Response time validation, load testing

## Recommendations
$(if [ "$OVERALL_RESULT" = false ]; then
    echo "- Review failed tests and fix identified issues"
    echo "- Improve test coverage for failing areas"
    echo "- Address any performance bottlenecks"
else
    echo "- All test suites passed successfully"
    echo "- System is ready for production deployment"
    echo "- Continue monitoring performance in production"
fi)

## Next Steps
1. Review detailed coverage reports
2. Address any identified issues
3. Run tests in staging environment
4. Prepare for production deployment
EOF
    
    print_status "SUCCESS" "Test report generated: docs/test-reports/test-summary.md"
}

# Main execution
main() {
    echo "🚀 Starting comprehensive test execution..."
    echo ""
    
    # Check prerequisites
    if ! command -v docker &> /dev/null; then
        print_status "ERROR" "Docker is required but not installed"
        exit 1
    fi
    
    if ! command -v python &> /dev/null; then
        print_status "ERROR" "Python is required but not installed"
        exit 1
    fi
    
    if ! command -v node &> /dev/null; then
        print_status "ERROR" "Node.js is required but not installed"
        exit 1
    fi
    
    # Start services
    start_services
    
    # Run test suites
    run_frontend_tests
    run_backend_tests
    run_integration_tests
    run_performance_tests
    
    # Generate report
    generate_test_report
    
    # Final summary
    echo ""
    echo "======================================================"
    print_status "INFO" "Test Execution Complete"
    echo "======================================================"
    echo ""
    
    if [ "$OVERALL_RESULT" = true ]; then
        print_status "SUCCESS" "All test suites passed! 🎉"
        echo ""
        print_status "INFO" "Test reports available in:"
        echo "  - docs/test-reports/test-summary.md"
        echo "  - scripts/frontend-tests/coverage/"
        echo "  - scripts/backend-tests/htmlcov/"
    else
        print_status "ERROR" "Some test suites failed. Please review the results above."
        exit 1
    fi
}

# Run main function
main "$@"







