#!/bin/bash

# Agent Sandbox Container Build Script
set -e

echo "Building Suna Agent Sandbox Container..."

# Check available ports first
echo "Checking available ports..."
python3 find_ports.py

echo ""
echo "Building Docker image..."

# Build the Docker image
docker build -t suna/agent-sandbox:latest .

echo "Build completed successfully!"

# Optional: Run a test container
read -p "Do you want to start a test container? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting test container..."
    docker-compose up -d
    echo "Container started!"
    echo "VNC access available at localhost:5901 (password: suna123)"
    echo "Web VNC access available at http://localhost:6080/vnc.html"
    echo "To stop the container, run: docker-compose down"
fi

echo "Available commands:"
echo "  docker run -d -p 5901:5901 --name test-sandbox suna/agent-sandbox:latest"
echo "  docker exec -it test-sandbox /bin/bash"
echo "  docker-compose up -d"