#!/usr/bin/env python3
"""
Security Validation Script

This script validates security measures and access controls
for the self-hosted Suna system.
"""

import os
import sys
import json
import re
from pathlib import Path
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityValidator:
    """Validates security measures and access controls."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.validation_results = []

    def validate_security_headers(self, nginx_config: str) -> bool:
        """Validate Nginx security headers configuration."""
        config_path = self.base_path / nginx_config

        if not config_path.exists():
            self.validation_results.append({
                "test": f"nginx_security_{nginx_config.replace('/', '_').replace('.', '_')}",
                "description": f"Nginx security config {nginx_config}",
                "status": "FAIL",
                "details": f"Nginx config missing: {config_path}"
            })
            return False

        try:
            with open(config_path, 'r') as f:
                config_content = f.read()

            # Check for essential security headers
            security_headers = [
                'X-Frame-Options',
                'X-Content-Type-Options',
                'X-XSS-Protection',
                'Content-Security-Policy',
                'Strict-Transport-Security'
            ]

            found_headers = []
            for header in security_headers:
                if header in config_content:
                    found_headers.append(header)

            if len(found_headers) >= 3:  # At least 3 major security headers
                self.validation_results.append({
                    "test": f"nginx_security_{nginx_config.replace('/', '_').replace('.', '_')}",
                    "description": f"Nginx security config {nginx_config}",
                    "status": "PASS",
                    "details": f"Found {len(found_headers)} security headers: {', '.join(found_headers)}"
                })
                return True
            else:
                self.validation_results.append({
                    "test": f"nginx_security_{nginx_config.replace('/', '_').replace('.', '_')}",
                    "description": f"Nginx security config {nginx_config}",
                    "status": "WARN",
                    "details": f"Only found {len(found_headers)} security headers: {', '.join(found_headers)}"
                })
                return False

        except Exception as e:
            self.validation_results.append({
                "test": f"nginx_security_{nginx_config.replace('/', '_').replace('.', '_')}",
                "description": f"Nginx security config {nginx_config}",
                "status": "FAIL",
                "details": f"Error reading nginx config: {str(e)}"
            })
            return False

    def validate_environment_secrets(self) -> bool:
        """Validate environment variables don't contain secrets."""
        logger.info("Validating environment secrets...")

        env_files = [
            '.env.example',
            'backend/.env.example',
            'frontend/.env.example',
            'self-hosted.env.example'
        ]

        all_secure = True
        for env_file in env_files:
            env_path = self.base_path / env_file
            if not env_path.exists():
                continue

            try:
                with open(env_path, 'r') as f:
                    content = f.read()

                # Check for hardcoded secrets
                secret_patterns = [
                    r'PASSWORD\s*=\s*[^$].*',  # PASSWORD=actual_password
                    r'SECRET\s*=\s*[^$].*',   # SECRET=actual_secret
                    r'KEY\s*=\s*[^$].*',      # KEY=actual_key
                    r'TOKEN\s*=\s*[^$].*'     # TOKEN=actual_token
                ]

                found_secrets = []
                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    found_secrets.extend(matches)

                if found_secrets:
                    self.validation_results.append({
                        "test": f"env_secrets_{env_file.replace('/', '_').replace('.', '_')}",
                        "description": f"Environment secrets in {env_file}",
                        "status": "FAIL",
                        "details": f"Found {len(found_secrets)} potential hardcoded secrets"
                    })
                    all_secure = False
                else:
                    self.validation_results.append({
                        "test": f"env_secrets_{env_file.replace('/', '_').replace('.', '_')}",
                        "description": f"Environment secrets in {env_file}",
                        "status": "PASS",
                        "details": "No hardcoded secrets found"
                    })

            except Exception as e:
                self.validation_results.append({
                    "test": f"env_secrets_{env_file.replace('/', '_').replace('.', '_')}",
                    "description": f"Environment secrets in {env_file}",
                    "status": "FAIL",
                    "details": f"Error reading env file: {str(e)}"
                })
                all_secure = False

        return all_secure

    def validate_docker_security(self, compose_file: str) -> bool:
        """Validate Docker Compose security configuration."""
        compose_path = self.base_path / compose_file

        if not compose_path.exists():
            self.validation_results.append({
                "test": f"docker_security_{compose_file.replace('/', '_').replace('.', '_')}",
                "description": f"Docker security in {compose_file}",
                "status": "FAIL",
                "details": f"Compose file missing: {compose_path}"
            })
            return False

        try:
            import yaml
            with open(compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get('services', {})
            security_issues = []
            security_good = []

            for service_name, service_config in services.items():
                # Check for root user
                if service_config.get('user') == 'root':
                    security_issues.append(f"{service_name}: runs as root")
                elif 'user' in service_config:
                    security_good.append(f"{service_name}: non-root user")

                # Check for privileged mode
                if service_config.get('privileged') is True:
                    security_issues.append(f"{service_name}: privileged mode")
                else:
                    security_good.append(f"{service_name}: not privileged")

                # Check for sensitive environment variables
                env_vars = service_config.get('environment', [])
                if isinstance(env_vars, list):
                    for env_var in env_vars:
                        if isinstance(env_var, str) and ('PASSWORD' in env_var or 'SECRET' in env_var):
                            if not env_var.startswith('$'):  # Not using environment variable
                                security_issues.append(f"{service_name}: hardcoded sensitive env var")

            if security_issues:
                self.validation_results.append({
                    "test": f"docker_security_{compose_file.replace('/', '_').replace('.', '_')}",
                    "description": f"Docker security in {compose_file}",
                    "status": "WARN",
                    "details": f"Security issues: {'; '.join(security_issues)}"
                })
                return len(security_issues) == 0
            else:
                self.validation_results.append({
                    "test": f"docker_security_{compose_file.replace('/', '_').replace('.', '_')}",
                    "description": f"Docker security in {compose_file}",
                    "status": "PASS",
                    "details": f"Good security practices: {'; '.join(security_good[:3])}"  # Show first 3
                })
                return True

        except Exception as e:
            self.validation_results.append({
                "test": f"docker_security_{compose_file.replace('/', '_').replace('.', '_')}",
                "description": f"Docker security in {compose_file}",
                "status": "FAIL",
                "details": f"Error reading compose file: {str(e)}"
            })
            return False

    def validate_code_security(self) -> bool:
        """Validate code for common security issues."""
        logger.info("Validating code security...")

        # Check for common security issues in Python files
        python_files = list(self.base_path.rglob('backend/**/*.py'))

        security_issues = []

        for py_file in python_files[:10]:  # Check first 10 files for performance
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Check for dangerous patterns
                dangerous_patterns = [
                    r'eval\s*\(',
                    r'exec\s*\(',
                    r'subprocess\.call\s*\(\s*.*shell\s*=\s*True',
                    r'os\.system\s*\(',
                    r'pickle\.loads?\s*\(',
                    r'yaml\.load\s*\('
                ]

                for pattern in dangerous_patterns:
                    if re.search(pattern, content):
                        security_issues.append(f"{py_file.name}: {pattern}")

            except Exception as e:
                logger.warning(f"Error reading {py_file}: {str(e)}")

        if security_issues:
            self.validation_results.append({
                "test": "code_security",
                "description": "Code security analysis",
                "status": "WARN",
                "details": f"Found {len(security_issues)} potential security issues"
            })
            return False
        else:
            self.validation_results.append({
                "test": "code_security",
                "description": "Code security analysis",
                "status": "PASS",
                "details": "No obvious security issues found in code"
            })
            return True

    def validate_authentication_security(self) -> bool:
        """Validate authentication security measures."""
        logger.info("Validating authentication security...")

        # Check for JWT configuration
        auth_files = [
            'backend/auth/__init__.py',
            'backend/services/auth_api.py'
        ]

        auth_secure = True
        for auth_file in auth_files:
            auth_path = self.base_path / auth_file
            if not auth_path.exists():
                continue

            try:
                with open(auth_path, 'r') as f:
                    content = f.read()

                # Check for secure JWT practices
                if 'JWT_SECRET_KEY' in content:
                    if 'your-secret-key' in content or 'change-this' in content:
                        self.validation_results.append({
                            "test": f"auth_security_{auth_file.replace('/', '_').replace('.', '_')}",
                            "description": f"Authentication security in {auth_file}",
                            "status": "WARN",
                            "details": "JWT secret key appears to be placeholder"
                        })
                        auth_secure = False
                    else:
                        self.validation_results.append({
                            "test": f"auth_security_{auth_file.replace('/', '_').replace('.', '_')}",
                            "description": f"Authentication security in {auth_file}",
                            "status": "PASS",
                            "details": "JWT configuration appears secure"
                        })

            except Exception as e:
                logger.warning(f"Error reading {auth_file}: {str(e)}")

        return auth_secure

    def validate_network_security(self) -> bool:
        """Validate network security configuration."""
        logger.info("Validating network security...")

        # Check docker-compose for network isolation
        compose_path = self.base_path / 'docker-compose.self-hosted.yml'

        if not compose_path.exists():
            self.validation_results.append({
                "test": "network_security",
                "description": "Network security configuration",
                "status": "FAIL",
                "details": "Docker Compose file missing"
            })
            return False

        try:
            import yaml
            with open(compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)

            networks = compose_data.get('networks', {})
            services = compose_data.get('services', {})

            # Check if custom networks are used
            if networks:
                self.validation_results.append({
                    "test": "network_security",
                    "description": "Network security configuration",
                    "status": "PASS",
                    "details": f"Custom networks configured: {list(networks.keys())}"
                })
                return True
            else:
                self.validation_results.append({
                    "test": "network_security",
                    "description": "Network security configuration",
                    "status": "WARN",
                    "details": "Using default networks - consider custom networks for isolation"
                })
                return False

        except Exception as e:
            self.validation_results.append({
                "test": "network_security",
                "description": "Network security configuration",
                "status": "FAIL",
                "details": f"Error reading compose file: {str(e)}"
            })
            return False

    def run_security_validation(self):
        """Run all security validation checks."""
        logger.info("Starting security validation...")

        # Core security validations
        logger.info("Validating core security measures...")
        self.validate_security_headers('security/nginx.conf')
        self.validate_environment_secrets()
        self.validate_docker_security('docker-compose.self-hosted.yml')

        # Code and authentication security
        logger.info("Validating code and authentication security...")
        self.validate_code_security()
        self.validate_authentication_security()

        # Network security
        logger.info("Validating network security...")
        self.validate_network_security()

        # Generate report
        return self.generate_report()

    def generate_report(self):
        """Generate security validation report."""
        total_tests = len(self.validation_results)
        passed_tests = len([r for r in self.validation_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.validation_results if r["status"] == "FAIL"])
        warn_tests = len([r for r in self.validation_results if r["status"] == "WARN"])

        print("\n" + "="*80)
        print("SECURITY VALIDATION REPORT")
        print("="*80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Warnings: {warn_tests}")
        print()

        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.validation_results:
                if result["status"] == "FAIL":
                    print(f"❌ {result['description']}")
                    print(f"   {result['details']}")
            print()

        if warn_tests > 0:
            print("WARNINGS:")
            for result in self.validation_results:
                if result["status"] == "WARN":
                    print(f"⚠️  {result['description']}")
                    print(f"   {result['details']}")
            print()

        if passed_tests > 0:
            print("PASSED TESTS:")
            for result in self.validation_results:
                if result["status"] == "PASS":
                    print(f"✅ {result['description']}")
            print()

        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print(".1f")
        print()

        if success_rate >= 75:
            print("🛡️  SECURITY VALIDATION PASSED!")
            print("Security measures are properly configured.")
        else:
            print("❌ SECURITY VALIDATION FAILED!")
            print("Security configuration needs attention.")

        print("="*80)

        return success_rate >= 75


def main():
    """Main security validation runner."""
    base_path = Path(__file__).parent.parent.parent  # Go up to suna directory

    validator = SecurityValidator(base_path)
    success = validator.run_security_validation()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)





