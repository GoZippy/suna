#!/bin/bash

echo "Starting Zippy Suna Smart Startup (Simple Version)..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Run the simple smart startup script
echo
echo "Running smart startup..."
python3 start-zippy-simple.py
