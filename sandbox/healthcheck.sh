#!/bin/bash

# Health check script for Suna Agent Sandbox Container
# This script verifies that all essential services are running

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
    else
        echo -e "${RED}✗${NC} $message"
    fi
}

# Check if running as correct user
check_user() {
    if [ "$(whoami)" = "suna" ]; then
        print_status "OK" "Running as suna user"
        return 0
    else
        print_status "ERROR" "Not running as suna user (current: $(whoami))"
        return 1
    fi
}

# Check VNC server
check_vnc() {
    if pgrep -f "Xtigervnc.*:1" > /dev/null; then
        print_status "OK" "VNC server is running on display :1"
        return 0
    else
        print_status "ERROR" "VNC server is not running"
        return 1
    fi
}

# Check desktop environment
check_desktop() {
    if pgrep -f "xfce4-session" > /dev/null; then
        print_status "OK" "XFCE4 desktop environment is running"
        return 0
    else
        print_status "WARN" "XFCE4 desktop environment is not running"
        return 1
    fi
}

# Check Python installation
check_python() {
    if python3 --version | grep -q "3.11"; then
        print_status "OK" "Python 3.11+ is available"
        return 0
    else
        print_status "ERROR" "Python 3.11+ is not available"
        return 1
    fi
}

# Check Node.js installation
check_nodejs() {
    if node --version | grep -q "v20"; then
        print_status "OK" "Node.js 20+ is available"
        return 0
    else
        print_status "ERROR" "Node.js 20+ is not available"
        return 1
    fi
}

# Check essential Python packages
check_python_packages() {
    local packages=("requests" "playwright" "selenium" "fastapi")
    local failed=0
    
    for package in "${packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            print_status "OK" "Python package '$package' is available"
        else
            print_status "ERROR" "Python package '$package' is missing"
            failed=1
        fi
    done
    
    return $failed
}

# Check workspace directory
check_workspace() {
    if [ -d "/workspace" ] && [ -w "/workspace" ]; then
        print_status "OK" "Workspace directory is accessible and writable"
        return 0
    else
        print_status "ERROR" "Workspace directory is not accessible or writable"
        return 1
    fi
}

# Check supervisor
check_supervisor() {
    if pgrep -f "supervisord" > /dev/null; then
        print_status "OK" "Supervisor is running"
        return 0
    else
        print_status "ERROR" "Supervisor is not running"
        return 1
    fi
}

# Check browser automation
check_browsers() {
    if playwright --version > /dev/null 2>&1; then
        print_status "OK" "Playwright is available"
        
        # Check if browsers are installed (check both user and system locations)
        if [ -d "/home/suna/.cache/ms-playwright" ] || [ -d "/usr/local/lib/python3.11/dist-packages/playwright" ]; then
            print_status "OK" "Playwright browsers are installed"
            return 0
        else
            print_status "WARN" "Playwright browsers may not be installed"
            return 1
        fi
    else
        print_status "ERROR" "Playwright is not available"
        return 1
    fi
}

# Check noVNC web interface
check_novnc() {
    if pgrep -f "websockify.*6080" > /dev/null; then
        print_status "OK" "noVNC web interface is running on port 6080"
        return 0
    else
        print_status "WARN" "noVNC web interface is not running"
        return 1
    fi
}

# Main health check function
main() {
    echo "Suna Agent Sandbox Container Health Check"
    echo "========================================"
    
    local failed=0
    
    # Run all checks
    check_user || failed=1
    check_supervisor || failed=1
    check_vnc || failed=1
    check_desktop || failed=1
    check_python || failed=1
    check_nodejs || failed=1
    check_python_packages || failed=1
    check_workspace || failed=1
    check_browsers || failed=1
    check_novnc || failed=1
    
    echo "========================================"
    
    if [ $failed -eq 0 ]; then
        print_status "OK" "All health checks passed"
        exit 0
    else
        print_status "ERROR" "Some health checks failed"
        exit 1
    fi
}

# Run health check
main "$@"