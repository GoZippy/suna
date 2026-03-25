@echo off
echo Setting up Zippy Suna Local Development Environment...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Run the setup script
echo.
echo Running local environment setup...
python setup-local-environment.py

pause


