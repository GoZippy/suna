#!/bin/bash

# Backend Test Runner Script
# This script runs the comprehensive backend test suite

set -e

echo "🧪 Starting Backend Test Suite..."
echo "================================="

# Check if we're in the right directory
if [ ! -f "conftest.py" ]; then
    echo "❌ Error: conftest.py not found. Please run this script from the backend-tests directory."
    exit 1
fi

# Check if Python environment is available
if ! command -v python &> /dev/null; then
    echo "❌ Error: Python is not installed or not in PATH."
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

source venv/bin/activate

echo "Installing test dependencies..."
pip install pytest pytest-asyncio pytest-cov pytest-xdist fastapi httpx redis asyncpg

# Set test environment variables
export TEST_DATABASE_URL="postgresql://test:test@localhost:5491/suna_test"
export TEST_REDIS_URL="redis://localhost:6391"
export TEST_API_URL="http://localhost:8091"
export TEST_TIMEOUT="30"

# Run unit tests
echo "🔍 Running unit tests..."
pytest test_api_endpoints.py::TestAPIEndpoints -v --tb=short

# Run agent system tests
echo "🤖 Running agent system tests..."
pytest test_agent_system.py::TestAgentSystem -v --tb=short

# Run integration tests
echo "🔗 Running integration tests..."
pytest -m integration -v --tb=short

# Run security tests
echo "🔒 Running security tests..."
pytest -m security -v --tb=short

# Run performance tests
echo "⚡ Running performance tests..."
pytest -m "slow" -v --tb=short

# Generate coverage report
echo "📊 Generating coverage report..."
pytest --cov=../../backend --cov-report=html --cov-report=term-missing

# Run all tests with coverage
echo "🎯 Running complete test suite with coverage..."
pytest --cov=../../backend --cov-report=html --cov-report=term-missing -v

echo "✅ Backend test suite completed successfully!"
echo "📈 Coverage report available in htmlcov/ directory"

# Deactivate virtual environment
deactivate







