#!/usr/bin/env python3
"""
Test runner for Suna comprehensive testing suite
"""

import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from tests import TEST_CONFIG, TEST_CATEGORIES


class TestRunner:
    """Test runner for Suna testing suite"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_tests(self, categories: List[str] = None, markers: List[str] = None, 
                  parallel: bool = False, coverage: bool = False, 
                  output_format: str = "text") -> Dict[str, Any]:
        """Run tests with specified configuration"""
        
        self.start_time = time.time()
        
        # Default to all categories if none specified
        if not categories:
            categories = list(TEST_CATEGORIES.keys())
        
        print(f"🚀 Starting Suna Test Suite")
        print(f"📋 Test Categories: {', '.join(categories)}")
        print(f"🏷️  Markers: {', '.join(markers) if markers else 'All'}")
        print(f"⚡ Parallel: {parallel}")
        print(f"📊 Coverage: {coverage}")
        print(f"📄 Output Format: {output_format}")
        print("-" * 60)
        
        # Build pytest command
        cmd = self._build_pytest_command(categories, markers, parallel, coverage, output_format)
        
        # Run tests
        result = self._execute_tests(cmd)
        
        self.end_time = time.time()
        
        # Generate report
        report = self._generate_report(result, categories, markers)
        
        return report
    
    def _build_pytest_command(self, categories: List[str], markers: List[str], 
                             parallel: bool, coverage: bool, output_format: str) -> List[str]:
        """Build pytest command with specified options"""
        
        cmd = ["python", "-m", "pytest"]
        
        # Add test paths based on categories
        for category in categories:
            if category in TEST_CATEGORIES:
                cmd.append(f"tests/{category}")
        
        # Add markers
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Add parallel execution
        if parallel:
            cmd.extend(["-n", "auto"])
        
        # Add coverage
        if coverage:
            cmd.extend([
                "--cov=.",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json"
            ])
        
        # Add output format
        if output_format == "json":
            cmd.extend(["--json-report", "--json-report-file=test-results.json"])
        elif output_format == "junit":
            cmd.extend(["--junitxml=test-results.xml"])
        
        # Add common options
        cmd.extend([
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "--strict-markers",  # Strict marker validation
            "--disable-warnings",  # Disable warnings
            "--color=yes"  # Colored output
        ])
        
        return cmd
    
    def _execute_tests(self, cmd: List[str]) -> Dict[str, Any]:
        """Execute pytest command and capture results"""
        
        print(f"🔧 Executing: {' '.join(cmd)}")
        print()
        
        try:
            # Run pytest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=backend_dir,
                timeout=3600  # 1 hour timeout
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": "Test execution timed out after 1 hour",
                "success": False
            }
        except Exception as e:
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": str(e),
                "success": False
            }
    
    def _generate_report(self, result: Dict[str, Any], categories: List[str], 
                        markers: List[str]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        duration = self.end_time - self.start_time
        
        # Parse test results from stdout
        test_stats = self._parse_test_output(result["stdout"])
        
        report = {
            "summary": {
                "total_duration": duration,
                "success": result["success"],
                "return_code": result["returncode"],
                "categories_tested": categories,
                "markers_used": markers
            },
            "test_results": test_stats,
            "output": {
                "stdout": result["stdout"],
                "stderr": result["stderr"]
            }
        }
        
        # Print summary
        self._print_summary(report)
        
        return report
    
    def _parse_test_output(self, stdout: str) -> Dict[str, Any]:
        """Parse pytest output to extract test statistics"""
        
        stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "warnings": 0
        }
        
        lines = stdout.split('\n')
        
        for line in lines:
            if "passed" in line and "failed" in line:
                # Parse summary line like "10 passed, 2 failed in 45.67s"
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        if "passed" in line and part in line:
                            stats["passed"] = int(part)
                        elif "failed" in line and part in line:
                            stats["failed"] = int(part)
                        elif "skipped" in line and part in line:
                            stats["skipped"] = int(part)
                        elif "error" in line and part in line:
                            stats["errors"] = int(part)
                        elif "warning" in line and part in line:
                            stats["warnings"] = int(part)
                
                stats["total"] = stats["passed"] + stats["failed"] + stats["skipped"] + stats["errors"]
                break
        
        return stats
    
    def _print_summary(self, report: Dict[str, Any]):
        """Print test execution summary"""
        
        summary = report["summary"]
        results = report["test_results"]
        
        print("\n" + "=" * 60)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 60)
        
        # Overall status
        status_emoji = "✅" if summary["success"] else "❌"
        print(f"{status_emoji} Overall Status: {'PASSED' if summary['success'] else 'FAILED'}")
        
        # Duration
        print(f"⏱️  Duration: {summary['total_duration']:.2f} seconds")
        
        # Test statistics
        print(f"📈 Test Statistics:")
        print(f"   Total Tests: {results['total']}")
        print(f"   Passed: {results['passed']} ✅")
        print(f"   Failed: {results['failed']} ❌")
        print(f"   Skipped: {results['skipped']} ⏭️")
        print(f"   Errors: {results['errors']} 💥")
        print(f"   Warnings: {results['warnings']} ⚠️")
        
        # Categories tested
        print(f"📂 Categories Tested: {', '.join(summary['categories_tested'])}")
        
        # Success rate
        if results['total'] > 0:
            success_rate = (results['passed'] / results['total']) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")
        
        print("=" * 60)
    
    def save_report(self, report: Dict[str, Any], filename: str = "test-report.json"):
        """Save test report to file"""
        
        report_path = backend_dir / filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Test report saved to: {report_path}")


def main():
    """Main entry point for test runner"""
    
    parser = argparse.ArgumentParser(description="Suna Test Suite Runner")
    
    # Test categories
    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        choices=list(TEST_CATEGORIES.keys()),
        help="Test categories to run"
    )
    
    # Test markers
    parser.add_argument(
        "--markers", "-m",
        nargs="+",
        help="Test markers to include"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--coverage", "--cov",
        action="store_true",
        help="Generate coverage report"
    )
    
    # Output options
    parser.add_argument(
        "--output-format", "-o",
        choices=["text", "json", "junit"],
        default="text",
        help="Output format for test results"
    )
    
    parser.add_argument(
        "--save-report", "-s",
        action="store_true",
        help="Save detailed test report to file"
    )
    
    parser.add_argument(
        "--report-file",
        default="test-report.json",
        help="Filename for test report"
    )
    
    # Environment options
    parser.add_argument(
        "--env",
        choices=["local", "staging", "production"],
        default="local",
        help="Environment to run tests against"
    )
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ["TEST_ENV"] = args.env
    
    # Initialize test runner
    runner = TestRunner(TEST_CONFIG)
    
    # Run tests
    report = runner.run_tests(
        categories=args.categories,
        markers=args.markers,
        parallel=args.parallel,
        coverage=args.coverage,
        output_format=args.output_format
    )
    
    # Save report if requested
    if args.save_report:
        runner.save_report(report, args.report_file)
    
    # Exit with appropriate code
    sys.exit(0 if report["summary"]["success"] else 1)


if __name__ == "__main__":
    main()







