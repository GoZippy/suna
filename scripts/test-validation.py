#!/usr/bin/env python3
"""
Test Infrastructure Validation Script
This script validates the testing infrastructure without requiring full system startup.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def print_status(status, message):
    """Print colored status messages."""
    colors = {
        "INFO": "\033[94m",    # Blue
        "SUCCESS": "\033[92m", # Green
        "WARNING": "\033[93m", # Yellow
        "ERROR": "\033[91m",   # Red
    }
    reset = "\033[0m"
    
    color = colors.get(status, "")
    icon = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌"
    }.get(status, "")
    
    print(f"{color}{icon} {message}{reset}")

def check_file_structure():
    """Check if all required test files exist."""
    print_status("INFO", "Validating test file structure...")
    
    required_files = [
        "scripts/frontend-tests/vitest.config.ts",
        "scripts/frontend-tests/setup.ts",
        "scripts/frontend-tests/package.json",
        "scripts/backend-tests/conftest.py",
        "scripts/backend-tests/test_api_endpoints.py",
        "scripts/backend-tests/test_agent_system.py",
        "scripts/integration-tests/test_frontend_backend_integration.py",
        "scripts/run-all-tests.sh"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print_status("SUCCESS", f"Found: {file_path}")
    
    if missing_files:
        print_status("ERROR", f"Missing files: {missing_files}")
        return False
    
    print_status("SUCCESS", "All required test files found")
    return True

def validate_frontend_tests():
    """Validate frontend test configuration."""
    print_status("INFO", "Validating frontend test configuration...")
    
    try:
        # Check if package.json is valid JSON
        with open("scripts/frontend-tests/package.json", "r") as f:
            package_data = json.load(f)
        
        required_scripts = ["test", "test:coverage", "test:unit", "test:components"]
        missing_scripts = [script for script in required_scripts if script not in package_data.get("scripts", {})]
        
        if missing_scripts:
            print_status("WARNING", f"Missing scripts in package.json: {missing_scripts}")
        else:
            print_status("SUCCESS", "Frontend package.json validation passed")
        
        # Check vitest config
        if os.path.exists("scripts/frontend-tests/vitest.config.ts"):
            print_status("SUCCESS", "Vitest configuration found")
        else:
            print_status("ERROR", "Vitest configuration missing")
            return False
        
        return True
        
    except Exception as e:
        print_status("ERROR", f"Frontend test validation failed: {e}")
        return False

def validate_backend_tests():
    """Validate backend test configuration."""
    print_status("INFO", "Validating backend test configuration...")
    
    try:
        # Check if conftest.py exists and is valid Python
        conftest_path = "scripts/backend-tests/conftest.py"
        if not os.path.exists(conftest_path):
            print_status("ERROR", "conftest.py not found")
            return False
        
        # Try to import conftest (basic syntax check)
        result = subprocess.run([sys.executable, "-m", "py_compile", conftest_path], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print_status("ERROR", f"conftest.py has syntax errors: {result.stderr}")
            return False
        
        print_status("SUCCESS", "Backend test configuration validation passed")
        return True
        
    except Exception as e:
        print_status("ERROR", f"Backend test validation failed: {e}")
        return False

def validate_integration_tests():
    """Validate integration test configuration."""
    print_status("INFO", "Validating integration test configuration...")
    
    try:
        integration_test_path = "scripts/integration-tests/test_frontend_backend_integration.py"
        
        if not os.path.exists(integration_test_path):
            print_status("ERROR", "Integration test file not found")
            return False
        
        # Check syntax
        result = subprocess.run([sys.executable, "-m", "py_compile", integration_test_path], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print_status("ERROR", f"Integration test has syntax errors: {result.stderr}")
            return False
        
        print_status("SUCCESS", "Integration test configuration validation passed")
        return True
        
    except Exception as e:
        print_status("ERROR", f"Integration test validation failed: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are available."""
    print_status("INFO", "Checking required dependencies...")
    
    required_tools = {
        "python": "Python interpreter",
        "node": "Node.js runtime",
        "npm": "Node package manager",
        "docker": "Docker container runtime"
    }
    
    missing_tools = []
    for tool, description in required_tools.items():
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                print_status("SUCCESS", f"{description}: {version}")
            else:
                missing_tools.append(tool)
        except FileNotFoundError:
            missing_tools.append(tool)
    
    if missing_tools:
        print_status("WARNING", f"Missing tools: {missing_tools}")
        return False
    
    print_status("SUCCESS", "All required dependencies available")
    return True

def generate_validation_report(results):
    """Generate validation report."""
    print_status("INFO", "Generating validation report...")
    
    # Create reports directory
    os.makedirs("docs/test-reports", exist_ok=True)
    
    # Get current date in a cross-platform way
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_content = f"""# Test Infrastructure Validation Report

## Validation Date
{current_date}

## Overall Result
{'✅ PASSED' if all(results.values()) else '❌ FAILED'}

## Validation Results

### File Structure
- Status: {'✅ PASSED' if results['file_structure'] else '❌ FAILED'}
- Description: Validates that all required test files exist

### Frontend Tests
- Status: {'✅ PASSED' if results['frontend_tests'] else '❌ FAILED'}
- Description: Validates frontend test configuration and dependencies

### Backend Tests
- Status: {'✅ PASSED' if results['backend_tests'] else '❌ FAILED'}
- Description: Validates backend test configuration and syntax

### Integration Tests
- Status: {'✅ PASSED' if results['integration_tests'] else '❌ FAILED'}
- Description: Validates integration test configuration

### Dependencies
- Status: {'✅ PASSED' if results['dependencies'] else '❌ FAILED'}
- Description: Validates required tools and dependencies

## Test Infrastructure Summary

### Frontend Testing
- Framework: Vitest + React Testing Library
- Configuration: scripts/frontend-tests/vitest.config.ts
- Package Management: npm
- Coverage: Built-in coverage reporting

### Backend Testing
- Framework: pytest + pytest-asyncio
- Configuration: scripts/backend-tests/conftest.py
- Database: PostgreSQL with pgvector
- Coverage: pytest-cov

### Integration Testing
- Framework: pytest + aiohttp
- Scope: Frontend-backend communication
- Real-time: WebSocket testing
- Performance: Response time validation

## Recommendations
"""
    
    if all(results.values()):
        report_content += """
- All validation checks passed successfully
- Test infrastructure is ready for execution
- Proceed with running the full test suite
- Monitor test execution for any runtime issues
"""
    else:
        report_content += """
- Address failed validation checks before running tests
- Install missing dependencies
- Fix configuration issues
- Re-run validation after fixes
"""
    
    report_content += """
## Next Steps
1. Run the full test suite: ./scripts/run-all-tests.sh
2. Review test results and coverage reports
3. Address any identified issues
4. Prepare for production deployment
"""
    
    # Write report
    with open("docs/test-reports/validation-report.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print_status("SUCCESS", "Validation report generated: docs/test-reports/validation-report.md")

def main():
    """Main validation function."""
    print("🧪 Test Infrastructure Validation")
    print("=" * 50)
    print()
    
    results = {}
    
    # Run validation checks
    results['file_structure'] = check_file_structure()
    print()
    
    results['frontend_tests'] = validate_frontend_tests()
    print()
    
    results['backend_tests'] = validate_backend_tests()
    print()
    
    results['integration_tests'] = validate_integration_tests()
    print()
    
    results['dependencies'] = check_dependencies()
    print()
    
    # Generate report
    generate_validation_report(results)
    print()
    
    # Final summary
    print("=" * 50)
    if all(results.values()):
        print_status("SUCCESS", "All validation checks passed! Test infrastructure is ready.")
        return 0
    else:
        print_status("ERROR", "Some validation checks failed. Please address the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
