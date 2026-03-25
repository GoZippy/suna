#!/bin/bash

echo "Setting up Zippy Suna Local Development Environment..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Run the setup script
echo
echo "Running local environment setup..."
python3 setup-local-environment.py


