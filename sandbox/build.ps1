# Agent Sandbox Container Build Script for Windows
param(
    [switch]$Test = $false
)

Write-Host "Building Suna Agent Sandbox Container..." -ForegroundColor Green

try {
    # Check available ports first
    Write-Host "Checking available ports..." -ForegroundColor Yellow
    python find_ports.py
    
    Write-Host "`nBuilding Docker image..." -ForegroundColor Yellow
    
    # Build the Docker image
    docker build -t suna/agent-sandbox:latest .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Build completed successfully!" -ForegroundColor Green
        
        if ($Test) {
            Write-Host "Starting test container..." -ForegroundColor Yellow
            docker-compose up -d
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Container started!" -ForegroundColor Green
                Write-Host "VNC access available at localhost:5901 (password: suna123)" -ForegroundColor Green
                Write-Host "Web VNC access available at http://localhost:6080/vnc.html" -ForegroundColor Green
                Write-Host "To stop the container, run: docker-compose down" -ForegroundColor Yellow
            }
        } else {
            $response = Read-Host "Do you want to start a test container? (y/n)"
            if ($response -eq "y" -or $response -eq "Y") {
                Write-Host "Starting test container..." -ForegroundColor Yellow
                docker-compose up -d
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Container started!" -ForegroundColor Green
                    Write-Host "VNC access available at localhost:5901 (password: suna123)" -ForegroundColor Green
                    Write-Host "Web VNC access available at http://localhost:6080/vnc.html" -ForegroundColor Green
                    Write-Host "To stop the container, run: docker-compose down" -ForegroundColor Yellow
                }
            }
        }
        
        Write-Host "`nAvailable commands:" -ForegroundColor Cyan
        Write-Host "  docker run -d -p 5901:5901 --name test-sandbox suna/agent-sandbox:latest"
        Write-Host "  docker exec -it test-sandbox /bin/bash"
        Write-Host "  docker-compose up -d"
    } else {
        Write-Host "Build failed!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}