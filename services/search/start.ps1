# Start Local Search and Scraping Services (PowerShell)
# This script starts SearXNG, Redis, and the scraping service

Write-Host "Starting Suna Local Search & Scraping Services..." -ForegroundColor Green

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "Error: Docker is not running. Please start Docker first." -ForegroundColor Red
    exit 1
}

# Create necessary directories
New-Item -ItemType Directory -Force -Path ".\searxng", ".\redis", ".\scraping\data" | Out-Null

# Start services
Write-Host "Starting services with Docker Compose..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services to be ready
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Health checks
Write-Host "Checking service health..." -ForegroundColor Yellow

# Check SearXNG
try {
    Invoke-WebRequest -Uri "http://localhost:8080/healthz" -UseBasicParsing | Out-Null
    Write-Host "✓ SearXNG is running on http://localhost:8080" -ForegroundColor Green
} catch {
    Write-Host "✗ SearXNG health check failed" -ForegroundColor Red
}

# Check Redis
try {
    docker exec suna_search_redis redis-cli ping | Out-Null
    Write-Host "✓ Redis is running on port 6380" -ForegroundColor Green
} catch {
    Write-Host "✗ Redis health check failed" -ForegroundColor Red
}

# Check Scraping Service
try {
    Invoke-WebRequest -Uri "http://localhost:8081/health" -UseBasicParsing | Out-Null
    Write-Host "✓ Scraping Service is running on http://localhost:8081" -ForegroundColor Green
} catch {
    Write-Host "✗ Scraping Service health check failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "Services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Available endpoints:" -ForegroundColor Cyan
Write-Host "- SearXNG Web UI: http://localhost:8080"
Write-Host "- Scraping Service API: http://localhost:8081"
Write-Host "- API Documentation: http://localhost:8081/docs"
Write-Host ""
Write-Host "To test the services, run:" -ForegroundColor Cyan
Write-Host "python client.py"
Write-Host ""
Write-Host "To stop services, run:" -ForegroundColor Cyan
Write-Host "docker-compose down"