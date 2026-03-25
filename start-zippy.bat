@echo off
echo Starting Zippy Suna Smart Startup (Simple Version)...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Run the simple smart startup script
echo.
echo Running smart startup...
python start-zippy-simple.py

pause
