#!/bin/bash

# Start Local Search and Scraping Services
# This script starts SearXNG, Redis, and the scraping service

set -e

echo "Starting Suna Local Search & Scraping Services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Create necessary directories
mkdir -p ./searxng ./redis ./scraping/data

# Set permissions
chmod +x ./scraping/main.py

# Start services
echo "Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Health checks
echo "Checking service health..."

# Check SearXNG
if curl -f http://localhost:8080/healthz > /dev/null 2>&1; then
    echo "✓ SearXNG is running on http://localhost:8080"
else
    echo "✗ SearXNG health check failed"
fi

# Check Redis
if docker exec suna_search_redis redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis is running on port 6380"
else
    echo "✗ Redis health check failed"
fi

# Check Scraping Service
if curl -f http://localhost:8081/health > /dev/null 2>&1; then
    echo "✓ Scraping Service is running on http://localhost:8081"
else
    echo "✗ Scraping Service health check failed"
fi

echo ""
echo "Services started successfully!"
echo ""
echo "Available endpoints:"
echo "- SearXNG Web UI: http://localhost:8080"
echo "- Scraping Service API: http://localhost:8081"
echo "- API Documentation: http://localhost:8081/docs"
echo ""
echo "To test the services, run:"
echo "python client.py"
echo ""
echo "To stop services, run:"
echo "docker-compose down"