#!/bin/bash

# Suna Database Startup Script
# This script starts the PostgreSQL and Redis containers

set -e

echo "Starting Suna Database Services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration before running again."
    exit 1
fi

# Load environment variables
source .env

# Create necessary directories
mkdir -p database/backups
mkdir -p database/logs

# Make scripts executable
chmod +x database/scripts/*.sh
chmod +x database/scripts/*.py

# Start database services
echo "Starting PostgreSQL and Redis..."
docker-compose -f docker-compose.db.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check if services are healthy
echo "Checking service health..."
docker-compose -f docker-compose.db.yml ps

# Test database connection
echo "Testing database connection..."
if command -v python3 &> /dev/null; then
    cd database && python3 test_connection.py
else
    echo "Python3 not found. Please install Python3 to test the connection."
fi

echo ""
echo "Database services started successfully!"
echo "PostgreSQL: localhost:${POSTGRES_PORT:-5432}"
echo "Redis: localhost:${REDIS_PORT:-6379}"
echo ""
echo "To stop services: docker-compose -f docker-compose.db.yml down"
echo "To view logs: docker-compose -f docker-compose.db.yml logs -f"