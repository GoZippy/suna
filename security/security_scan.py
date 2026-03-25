#!/usr/bin/env python3
"""
Security scanning script for Suna self-hosted deployment
Performs vulnerability assessment and security checks
"""

import os
import sys
import subprocess
import json
import time
import requests
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SecurityCheck:
    """Security check result"""
    name: str
    status: str  # "PASS", "FAIL", "WARNING", "INFO"
    description: str
    details: Dict[str, Any] = None
    recommendations: List[str] = None


class SecurityScanner:
    """Security scanner for Suna deployment"""
    
    def __init__(self, base_url: str = "http://localhost:8091"):
        self.base_url = base_url
        self.checks: List[SecurityCheck] = []
        
    def run_all_checks(self) -> List[SecurityCheck]:
        """Run all security checks"""
        logger.info("Starting security scan")
        
        # Network security checks
        self._check_ssl_configuration()
        self._check_security_headers()
        self._check_rate_limiting()
        self._check_cors_configuration()
        
        # Application security checks
        self._check_authentication_endpoints()
        self._check_admin_endpoints()
        self._check_input_validation()
        self._check_error_handling()
        
        # Infrastructure security checks
        self._check_docker_security()
        self._check_database_security()
        self._check_file_permissions()
        self._check_environment_variables()
        
        # Monitoring and logging checks
        self._check_audit_logging()
        self._check_monitoring_endpoints()
        
        logger.info(f"Security scan completed. {len(self.checks)} checks performed")
        return self.checks
    
    def _check_ssl_configuration(self):
        """Check SSL/TLS configuration"""
        try:
            # Try HTTPS first
            https_url = self.base_url.replace("http://", "https://")
            response = requests.get(f"{https_url}/health", timeout=5, verify=False)
            
            if response.status_code == 200:
                self.checks.append(SecurityCheck(
                    name="SSL/TLS Configuration",
                    status="PASS",
                    description="HTTPS is enabled and accessible",
                    details={
                        "ssl_enabled": True,
                        "status_code": response.status_code
                    }
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="SSL/TLS Configuration",
                    status="WARNING",
                    description="HTTPS endpoint accessible but returned non-200 status",
                    details={
                        "ssl_enabled": True,
                        "status_code": response.status_code
                    },
                    recommendations=[
                        "Check SSL certificate configuration",
                        "Verify nginx SSL settings"
                    ]
                ))
                
        except requests.exceptions.RequestException:
            # Try HTTP
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    self.checks.append(SecurityCheck(
                        name="SSL/TLS Configuration",
                        status="FAIL",
                        description="HTTPS not enabled - using HTTP",
                        details={
                            "ssl_enabled": False,
                            "status_code": response.status_code
                        },
                        recommendations=[
                            "Enable HTTPS with valid SSL certificate",
                            "Configure nginx for SSL termination",
                            "Redirect HTTP to HTTPS"
                        ]
                    ))
                else:
                    self.checks.append(SecurityCheck(
                        name="SSL/TLS Configuration",
                        status="FAIL",
                        description="Service not accessible",
                        details={
                            "ssl_enabled": False,
                            "status_code": response.status_code
                        },
                        recommendations=[
                            "Check if service is running",
                            "Verify network connectivity"
                        ]
                    ))
            except requests.exceptions.RequestException:
                self.checks.append(SecurityCheck(
                    name="SSL/TLS Configuration",
                    status="FAIL",
                    description="Service not accessible",
                    details={"error": "Connection failed"},
                    recommendations=[
                        "Check if service is running",
                        "Verify network connectivity",
                        "Check firewall settings"
                    ]
                ))
    
    def _check_security_headers(self):
        """Check security headers"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            headers = response.headers
            
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": None  # Any value is acceptable
            }
            
            missing_headers = []
            for header, expected_value in security_headers.items():
                if header not in headers:
                    missing_headers.append(header)
                elif expected_value and headers[header] != expected_value:
                    missing_headers.append(f"{header} (incorrect value)")
            
            if not missing_headers:
                self.checks.append(SecurityCheck(
                    name="Security Headers",
                    status="PASS",
                    description="All required security headers are present",
                    details={"headers_found": list(security_headers.keys())}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Security Headers",
                    status="FAIL",
                    description=f"Missing or incorrect security headers: {', '.join(missing_headers)}",
                    details={
                        "missing_headers": missing_headers,
                        "found_headers": {k: v for k, v in headers.items() if k in security_headers}
                    },
                    recommendations=[
                        "Configure nginx to add missing security headers",
                        "Update FastAPI middleware to include security headers"
                    ]
                ))
                
        except requests.exceptions.RequestException as e:
            self.checks.append(SecurityCheck(
                name="Security Headers",
                status="FAIL",
                description="Could not check security headers",
                details={"error": str(e)},
                recommendations=["Check service availability"]
            ))
    
    def _check_rate_limiting(self):
        """Check rate limiting implementation"""
        try:
            # Test rate limiting by making multiple requests quickly
            responses = []
            for i in range(15):  # Make 15 requests
                response = requests.get(f"{self.base_url}/api/health", timeout=5)
                responses.append(response.status_code)
                time.sleep(0.1)  # Small delay
            
            # Check if any requests were rate limited (429 status)
            rate_limited = any(status == 429 for status in responses)
            
            if rate_limited:
                self.checks.append(SecurityCheck(
                    name="Rate Limiting",
                    status="PASS",
                    description="Rate limiting is working",
                    details={
                        "total_requests": len(responses),
                        "rate_limited_requests": responses.count(429),
                        "response_codes": responses
                    }
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Rate Limiting",
                    status="WARNING",
                    description="Rate limiting may not be properly configured",
                    details={
                        "total_requests": len(responses),
                        "response_codes": responses
                    },
                    recommendations=[
                        "Verify rate limiting configuration",
                        "Check if rate limiting is enabled for all endpoints"
                    ]
                ))
                
        except requests.exceptions.RequestException as e:
            self.checks.append(SecurityCheck(
                name="Rate Limiting",
                status="FAIL",
                description="Could not test rate limiting",
                details={"error": str(e)},
                recommendations=["Check service availability"]
            ))
    
    def _check_cors_configuration(self):
        """Check CORS configuration"""
        try:
            # Test CORS with a preflight request
            headers = {
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
            
            response = requests.options(f"{self.base_url}/api/health", headers=headers, timeout=5)
            cors_headers = response.headers
            
            # Check if CORS is properly configured
            if "Access-Control-Allow-Origin" in cors_headers:
                allowed_origin = cors_headers["Access-Control-Allow-Origin"]
                if allowed_origin == "*":
                    self.checks.append(SecurityCheck(
                        name="CORS Configuration",
                        status="WARNING",
                        description="CORS allows all origins (*)",
                        details={"allowed_origin": allowed_origin},
                        recommendations=[
                            "Restrict CORS to specific domains",
                            "Configure allowed origins in production"
                        ]
                    ))
                else:
                    self.checks.append(SecurityCheck(
                        name="CORS Configuration",
                        status="PASS",
                        description="CORS is properly configured",
                        details={"allowed_origin": allowed_origin}
                    ))
            else:
                self.checks.append(SecurityCheck(
                    name="CORS Configuration",
                    status="INFO",
                    description="CORS headers not found (may be handled by nginx)",
                    details={"cors_headers": dict(cors_headers)}
                ))
                
        except requests.exceptions.RequestException as e:
            self.checks.append(SecurityCheck(
                name="CORS Configuration",
                status="FAIL",
                description="Could not check CORS configuration",
                details={"error": str(e)},
                recommendations=["Check service availability"]
            ))
    
    def _check_authentication_endpoints(self):
        """Check authentication endpoint security"""
        try:
            # Test login endpoint with invalid credentials
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={"email": "test@example.com", "password": "wrongpassword"},
                timeout=5
            )
            
            # Check if endpoint exists and handles invalid credentials properly
            if response.status_code in [401, 422, 400]:
                self.checks.append(SecurityCheck(
                    name="Authentication Endpoints",
                    status="PASS",
                    description="Login endpoint properly handles invalid credentials",
                    details={"status_code": response.status_code}
                ))
            elif response.status_code == 404:
                self.checks.append(SecurityCheck(
                    name="Authentication Endpoints",
                    status="INFO",
                    description="Authentication endpoint not found (may be disabled)",
                    details={"status_code": response.status_code}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Authentication Endpoints",
                    status="WARNING",
                    description="Unexpected response from login endpoint",
                    details={"status_code": response.status_code},
                    recommendations=[
                        "Verify authentication endpoint configuration",
                        "Check error handling for invalid credentials"
                    ]
                ))
                
        except requests.exceptions.RequestException as e:
            self.checks.append(SecurityCheck(
                name="Authentication Endpoints",
                status="FAIL",
                description="Could not test authentication endpoints",
                details={"error": str(e)},
                recommendations=["Check service availability"]
            ))
    
    def _check_admin_endpoints(self):
        """Check admin endpoint security"""
        try:
            # Test admin endpoint without authentication
            response = requests.get(f"{self.base_url}/admin", timeout=5)
            
            if response.status_code in [401, 403, 404]:
                self.checks.append(SecurityCheck(
                    name="Admin Endpoints",
                    status="PASS",
                    description="Admin endpoint properly protected",
                    details={"status_code": response.status_code}
                ))
            elif response.status_code == 200:
                self.checks.append(SecurityCheck(
                    name="Admin Endpoints",
                    status="FAIL",
                    description="Admin endpoint accessible without authentication",
                    details={"status_code": response.status_code},
                    recommendations=[
                        "Implement authentication for admin endpoints",
                        "Add authorization checks"
                    ]
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Admin Endpoints",
                    status="WARNING",
                    description="Unexpected response from admin endpoint",
                    details={"status_code": response.status_code},
                    recommendations=["Verify admin endpoint configuration"]
                ))
                
        except requests.exceptions.RequestException as e:
            self.checks.append(SecurityCheck(
                name="Admin Endpoints",
                status="FAIL",
                description="Could not test admin endpoints",
                details={"error": str(e)},
                recommendations=["Check service availability"]
            ))
    
    def _check_input_validation(self):
        """Check input validation"""
        try:
            # Test SQL injection attempt
            payload = "'; DROP TABLE users; --"
            response = requests.get(
                f"{self.base_url}/api/health",
                params={"test": payload},
                timeout=5
            )
            
            # Check if the request was handled properly
            if response.status_code in [200, 400, 422]:
                self.checks.append(SecurityCheck(
                    name="Input Validation",
                    status="PASS",
                    description="Input validation appears to be working",
                    details={"status_code": response.status_code}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Input Validation",
                    status="WARNING",
                    description="Unexpected response to suspicious input",
                    details={"status_code": response.status_code},
                    recommendations=[
                        "Verify input validation is enabled",
                        "Test with additional malicious inputs"
                    ]
                ))
                
        except requests.exceptions.RequestException as e:
            self.checks.append(SecurityCheck(
                name="Input Validation",
                status="FAIL",
                description="Could not test input validation",
                details={"error": str(e)},
                recommendations=["Check service availability"]
            ))
    
    def _check_error_handling(self):
        """Check error handling"""
        try:
            # Test with invalid endpoint
            response = requests.get(f"{self.base_url}/api/nonexistent", timeout=5)
            
            if response.status_code == 404:
                # Check if error response doesn't leak sensitive information
                response_text = response.text.lower()
                sensitive_terms = ["password", "secret", "key", "token", "database", "sql"]
                leaked_info = [term for term in sensitive_terms if term in response_text]
                
                if not leaked_info:
                    self.checks.append(SecurityCheck(
                        name="Error Handling",
                        status="PASS",
                        description="Error handling doesn't leak sensitive information",
                        details={"status_code": response.status_code}
                    ))
                else:
                    self.checks.append(SecurityCheck(
                        name="Error Handling",
                        status="FAIL",
                        description="Error response may leak sensitive information",
                        details={
                            "status_code": response.status_code,
                            "suspicious_terms": leaked_info
                        },
                        recommendations=[
                            "Review error messages for sensitive information",
                            "Implement generic error responses"
                        ]
                    ))
            else:
                self.checks.append(SecurityCheck(
                    name="Error Handling",
                    status="INFO",
                    description="Unexpected response for invalid endpoint",
                    details={"status_code": response.status_code}
                ))
                
        except requests.exceptions.RequestException as e:
            self.checks.append(SecurityCheck(
                name="Error Handling",
                status="FAIL",
                description="Could not test error handling",
                details={"error": str(e)},
                recommendations=["Check service availability"]
            ))
    
    def _check_docker_security(self):
        """Check Docker security configuration"""
        try:
            # Check if running in Docker
            if os.path.exists("/.dockerenv"):
                self.checks.append(SecurityCheck(
                    name="Docker Security",
                    status="INFO",
                    description="Running in Docker container",
                    details={"containerized": True}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Docker Security",
                    status="INFO",
                    description="Not running in Docker container",
                    details={"containerized": False}
                ))
                
            # Check for security-related environment variables
            security_vars = [
                "JWT_SECRET_KEY", "DATABASE_URL", "REDIS_PASSWORD",
                "ADMIN_PASSWORD", "API_KEY_SECRET"
            ]
            
            found_vars = [var for var in security_vars if os.getenv(var)]
            if found_vars:
                self.checks.append(SecurityCheck(
                    name="Environment Variables",
                    status="PASS",
                    description="Security environment variables are set",
                    details={"security_variables": found_vars}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Environment Variables",
                    status="WARNING",
                    description="No security environment variables found",
                    details={"security_variables": found_vars},
                    recommendations=[
                        "Set required security environment variables",
                        "Use secure secrets management"
                    ]
                ))
                
        except Exception as e:
            self.checks.append(SecurityCheck(
                name="Docker Security",
                status="FAIL",
                description="Could not check Docker security",
                details={"error": str(e)}
            ))
    
    def _check_database_security(self):
        """Check database security configuration"""
        try:
            # Check if database connection is secure
            db_url = os.getenv("DATABASE_URL", "")
            if db_url:
                if "ssl=true" in db_url.lower() or "sslmode=require" in db_url.lower():
                    self.checks.append(SecurityCheck(
                        name="Database Security",
                        status="PASS",
                        description="Database connection uses SSL",
                        details={"ssl_enabled": True}
                    ))
                else:
                    self.checks.append(SecurityCheck(
                        name="Database Security",
                        status="WARNING",
                        description="Database connection may not be encrypted",
                        details={"ssl_enabled": False},
                        recommendations=[
                            "Enable SSL for database connections",
                            "Use encrypted database connections in production"
                        ]
                    ))
            else:
                self.checks.append(SecurityCheck(
                    name="Database Security",
                    status="INFO",
                    description="Database URL not found in environment",
                    details={"database_url_set": False}
                ))
                
        except Exception as e:
            self.checks.append(SecurityCheck(
                name="Database Security",
                status="FAIL",
                description="Could not check database security",
                details={"error": str(e)}
            ))
    
    def _check_file_permissions(self):
        """Check file permissions"""
        try:
            # Check common file permissions
            files_to_check = [
                "/app/.env",
                "/app/data",
                "/app/logs",
                "/app/ssl"
            ]
            
            permission_issues = []
            for file_path in files_to_check:
                if os.path.exists(file_path):
                    stat_info = os.stat(file_path)
                    mode = oct(stat_info.st_mode)[-3:]
                    
                    # Check if permissions are too open
                    if mode in ["777", "666", "755"]:
                        permission_issues.append(f"{file_path}: {mode}")
            
            if not permission_issues:
                self.checks.append(SecurityCheck(
                    name="File Permissions",
                    status="PASS",
                    description="File permissions appear secure",
                    details={"checked_files": files_to_check}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="File Permissions",
                    status="WARNING",
                    description="Some files have overly permissive permissions",
                    details={"permission_issues": permission_issues},
                    recommendations=[
                        "Review and restrict file permissions",
                        "Use appropriate ownership and permissions"
                    ]
                ))
                
        except Exception as e:
            self.checks.append(SecurityCheck(
                name="File Permissions",
                status="FAIL",
                description="Could not check file permissions",
                details={"error": str(e)}
            ))
    
    def _check_environment_variables(self):
        """Check environment variable security"""
        try:
            # Check for sensitive environment variables
            sensitive_vars = [
                "JWT_SECRET_KEY", "DATABASE_URL", "REDIS_PASSWORD",
                "ADMIN_PASSWORD", "API_KEY_SECRET", "STRIPE_SECRET_KEY"
            ]
            
            found_sensitive = []
            for var in sensitive_vars:
                if os.getenv(var):
                    found_sensitive.append(var)
            
            if found_sensitive:
                self.checks.append(SecurityCheck(
                    name="Environment Variables",
                    status="PASS",
                    description="Sensitive environment variables are set",
                    details={"sensitive_variables": found_sensitive}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Environment Variables",
                    status="WARNING",
                    description="No sensitive environment variables found",
                    details={"sensitive_variables": found_sensitive},
                    recommendations=[
                        "Set required sensitive environment variables",
                        "Use secure secrets management"
                    ]
                ))
                
        except Exception as e:
            self.checks.append(SecurityCheck(
                name="Environment Variables",
                status="FAIL",
                description="Could not check environment variables",
                details={"error": str(e)}
            ))
    
    def _check_audit_logging(self):
        """Check audit logging configuration"""
        try:
            # Check if log files exist and are writable
            log_paths = [
                "/app/logs",
                "/var/log/nginx",
                "/var/log/app"
            ]
            
            accessible_logs = []
            for log_path in log_paths:
                if os.path.exists(log_path) and os.access(log_path, os.W_OK):
                    accessible_logs.append(log_path)
            
            if accessible_logs:
                self.checks.append(SecurityCheck(
                    name="Audit Logging",
                    status="PASS",
                    description="Log directories are accessible",
                    details={"accessible_logs": accessible_logs}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Audit Logging",
                    status="WARNING",
                    description="No accessible log directories found",
                    details={"accessible_logs": accessible_logs},
                    recommendations=[
                        "Configure logging directories",
                        "Ensure proper log file permissions"
                    ]
                ))
                
        except Exception as e:
            self.checks.append(SecurityCheck(
                name="Audit Logging",
                status="FAIL",
                description="Could not check audit logging",
                details={"error": str(e)}
            ))
    
    def _check_monitoring_endpoints(self):
        """Check monitoring endpoint security"""
        try:
            # Test monitoring endpoints
            monitoring_endpoints = [
                "/metrics",
                "/health",
                "/api/monitoring/health"
            ]
            
            accessible_endpoints = []
            for endpoint in monitoring_endpoints:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        accessible_endpoints.append(endpoint)
                except:
                    pass
            
            if accessible_endpoints:
                self.checks.append(SecurityCheck(
                    name="Monitoring Endpoints",
                    status="PASS",
                    description="Monitoring endpoints are accessible",
                    details={"accessible_endpoints": accessible_endpoints}
                ))
            else:
                self.checks.append(SecurityCheck(
                    name="Monitoring Endpoints",
                    status="WARNING",
                    description="No monitoring endpoints accessible",
                    details={"accessible_endpoints": accessible_endpoints},
                    recommendations=[
                        "Configure monitoring endpoints",
                        "Ensure health checks are working"
                    ]
                ))
                
        except Exception as e:
            self.checks.append(SecurityCheck(
                name="Monitoring Endpoints",
                status="FAIL",
                description="Could not check monitoring endpoints",
                details={"error": str(e)}
            ))
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate security scan report"""
        status_counts = {
            "PASS": len([c for c in self.checks if c.status == "PASS"]),
            "FAIL": len([c for c in self.checks if c.status == "FAIL"]),
            "WARNING": len([c for c in self.checks if c.status == "WARNING"]),
            "INFO": len([c for c in self.checks if c.status == "INFO"])
        }
        
        return {
            "timestamp": time.time(),
            "base_url": self.base_url,
            "summary": {
                "total_checks": len(self.checks),
                "status_counts": status_counts,
                "overall_status": "PASS" if status_counts["FAIL"] == 0 else "FAIL"
            },
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "description": check.description,
                    "details": check.details,
                    "recommendations": check.recommendations
                }
                for check in self.checks
            ]
        }


def main():
    """Main function to run security scan"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security scanner for Suna deployment")
    parser.add_argument("--url", default="http://localhost:8091", help="Base URL to scan")
    parser.add_argument("--output", help="Output file for JSON report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Run security scan
    scanner = SecurityScanner(args.url)
    checks = scanner.run_all_checks()
    report = scanner.generate_report()
    
    # Print summary
    print("\n" + "="*60)
    print("SECURITY SCAN REPORT")
    print("="*60)
    print(f"Base URL: {args.url}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report['timestamp']))}")
    print(f"Total Checks: {report['summary']['total_checks']}")
    print(f"Overall Status: {report['summary']['overall_status']}")
    print()
    
    print("Status Summary:")
    for status, count in report['summary']['status_counts'].items():
        print(f"  {status}: {count}")
    print()
    
    # Print detailed results
    for check in checks:
        status_icon = {
            "PASS": "✅",
            "FAIL": "❌",
            "WARNING": "⚠️",
            "INFO": "ℹ️"
        }.get(check.status, "❓")
        
        print(f"{status_icon} {check.name}")
        print(f"   Status: {check.status}")
        print(f"   Description: {check.description}")
        if check.recommendations:
            print("   Recommendations:")
            for rec in check.recommendations:
                print(f"     - {rec}")
        print()
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {args.output}")
    
    # Exit with appropriate code
    if report['summary']['overall_status'] == "FAIL":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()







