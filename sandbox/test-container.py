#!/usr/bin/env python3
"""
Test script to verify agent sandbox container functionality
"""

import subprocess
import time
import requests
import sys
import os

def run_command(cmd, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_container_build():
    """Test if the container builds successfully"""
    print("Testing container build...")
    success, stdout, stderr = run_command("docker build -t suna/agent-sandbox:test .")
    if success:
        print("✓ Container build successful")
        return True
    else:
        print(f"✗ Container build failed: {stderr}")
        return False

def test_container_start():
    """Test if the container starts successfully"""
    print("Testing container startup...")
    
    # Stop any existing test container
    run_command("docker stop suna-sandbox-test 2>/dev/null", capture_output=False)
    run_command("docker rm suna-sandbox-test 2>/dev/null", capture_output=False)
    
    # Start new test container
    success, stdout, stderr = run_command(
        "docker run -d --name suna-sandbox-test -p 5902:5901 suna/agent-sandbox:test"
    )
    
    if success:
        print("✓ Container started successfully")
        time.sleep(10)  # Wait for services to start
        return True
    else:
        print(f"✗ Container start failed: {stderr}")
        return False

def test_vnc_server():
    """Test if VNC server is running"""
    print("Testing VNC server...")
    success, stdout, stderr = run_command(
        "docker exec suna-sandbox-test ps aux | grep vnc"
    )
    
    if success and "Xvnc" in stdout:
        print("✓ VNC server is running")
        return True
    else:
        print("✗ VNC server not found")
        return False

def test_python_installation():
    """Test Python installation and packages"""
    print("Testing Python installation...")
    
    # Test Python version
    success, stdout, stderr = run_command(
        "docker exec suna-sandbox-test python3 --version"
    )
    
    if success and "3.11" in stdout:
        print(f"✓ Python version: {stdout.strip()}")
    else:
        print(f"✗ Python version check failed: {stderr}")
        return False
    
    # Test key packages
    packages = ["requests", "playwright", "selenium", "fastapi", "pytest"]
    for package in packages:
        success, stdout, stderr = run_command(
            f"docker exec suna-sandbox-test python3 -c 'import {package}; print(\"{package} OK\")'"
        )
        if success:
            print(f"✓ {package} package available")
        else:
            print(f"✗ {package} package missing")
            return False
    
    return True

def test_nodejs_installation():
    """Test Node.js installation and packages"""
    print("Testing Node.js installation...")
    
    # Test Node.js version
    success, stdout, stderr = run_command(
        "docker exec suna-sandbox-test node --version"
    )
    
    if success and stdout.startswith("v20"):
        print(f"✓ Node.js version: {stdout.strip()}")
    else:
        print(f"✗ Node.js version check failed: {stderr}")
        return False
    
    # Test npm packages
    packages = ["typescript", "yarn", "pnpm"]
    for package in packages:
        success, stdout, stderr = run_command(
            f"docker exec suna-sandbox-test which {package}"
        )
        if success:
            print(f"✓ {package} available")
        else:
            print(f"✗ {package} missing")
            return False
    
    return True

def test_browser_automation():
    """Test browser automation capabilities"""
    print("Testing browser automation...")
    
    # Test Playwright
    playwright_test = '''
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("data:text/html,<h1>Test</h1>")
        title = page.inner_text("h1")
        browser.close()
        print("Playwright test successful:", title)
except Exception as e:
    print("Playwright test failed:", e)
    exit(1)
'''
    
    success, stdout, stderr = run_command(
        f"docker exec suna-sandbox-test python3 -c '{playwright_test}'"
    )
    
    if success and "Playwright test successful" in stdout:
        print("✓ Playwright browser automation working")
        return True
    else:
        print(f"✗ Playwright test failed: {stderr}")
        return False

def test_workspace_permissions():
    """Test workspace directory permissions"""
    print("Testing workspace permissions...")
    
    # Test file creation in workspace
    success, stdout, stderr = run_command(
        "docker exec -u suna suna-sandbox-test touch /workspace/test-file.txt"
    )
    
    if success:
        print("✓ Workspace write permissions OK")
        
        # Test file ownership
        success, stdout, stderr = run_command(
            "docker exec suna-sandbox-test ls -la /workspace/test-file.txt"
        )
        
        if success and "suna suna" in stdout:
            print("✓ File ownership correct")
            return True
        else:
            print(f"✗ File ownership incorrect: {stdout}")
            return False
    else:
        print(f"✗ Workspace write test failed: {stderr}")
        return False

def cleanup_test_container():
    """Clean up test container"""
    print("Cleaning up test container...")
    run_command("docker stop suna-sandbox-test 2>/dev/null", capture_output=False)
    run_command("docker rm suna-sandbox-test 2>/dev/null", capture_output=False)
    run_command("docker rmi suna/agent-sandbox:test 2>/dev/null", capture_output=False)

def main():
    """Run all tests"""
    print("Starting Suna Agent Sandbox Container Tests")
    print("=" * 50)
    
    tests = [
        test_container_build,
        test_container_start,
        test_vnc_server,
        test_python_installation,
        test_nodejs_installation,
        test_browser_automation,
        test_workspace_permissions
    ]
    
    passed = 0
    total = len(tests)
    
    try:
        for test in tests:
            if test():
                passed += 1
            print()
    
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    
    finally:
        cleanup_test_container()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Container is ready for use.")
        return 0
    else:
        print("✗ Some tests failed. Please check the container configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())