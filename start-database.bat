@echo off
REM Suna Database Startup Script for Windows
REM This script starts the PostgreSQL and Redis containers

echo Starting Suna Database Services...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker first.
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env
    echo Please edit .env file with your configuration before running again.
    exit /b 1
)

REM Create necessary directories
if not exist database\backups mkdir database\backups
if not exist database\logs mkdir database\logs

REM Start database services
echo Starting PostgreSQL and Redis...
docker-compose -f docker-compose.db.yml up -d

REM Wait for services to be ready
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check if services are healthy
echo Checking service health...
docker-compose -f docker-compose.db.yml ps

REM Test database connection
echo Testing database connection...
where python >nul 2>&1
if errorlevel 1 (
    where python3 >nul 2>&1
    if errorlevel 1 (
        echo Python not found. Please install Python to test the connection.
    ) else (
        cd database && python3 test_connection.py
    )
) else (
    cd database && python test_connection.py
)

echo.
echo Database services started successfully!
echo PostgreSQL: localhost:5432
echo Redis: localhost:6379
echo.
echo To stop services: docker-compose -f docker-compose.db.yml down
echo To view logs: docker-compose -f docker-compose.db.yml logs -f

pause