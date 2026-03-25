#!/usr/bin/env python3
"""
System Component Validation Script

This script validates that all self-hosted system components are properly
configured and integrated, without requiring the full system to be running.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemValidator:
    """Validates system component integration and configuration."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.validation_results = []

    def validate_file_exists(self, file_path: str, description: str) -> bool:
        """Check if a file exists."""
        full_path = self.base_path / file_path
        exists = full_path.exists()
        status = "PASS" if exists else "FAIL"
        self.validation_results.append({
            "test": f"file_exists_{file_path.replace('/', '_').replace('.', '_')}",
            "description": description,
            "status": status,
            "details": f"File {'exists' if exists else 'missing'}: {full_path}"
        })
        return exists

    def validate_directory_exists(self, dir_path: str, description: str) -> bool:
        """Check if a directory exists."""
        full_path = self.base_path / dir_path
        exists = full_path.is_dir()
        status = "PASS" if exists else "FAIL"
        self.validation_results.append({
            "test": f"dir_exists_{dir_path.replace('/', '_')}",
            "description": description,
            "status": status,
            "details": f"Directory {'exists' if exists else 'missing'}: {full_path}"
        })
        return exists

    def validate_compose_service(self, compose_file: str, service_name: str) -> bool:
        """Validate that a service is defined in docker-compose file."""
        compose_path = self.base_path / compose_file
        if not compose_path.exists():
            self.validation_results.append({
                "test": f"compose_service_{service_name}",
                "description": f"Service {service_name} in {compose_file}",
                "status": "FAIL",
                "details": f"Compose file missing: {compose_path}"
            })
            return False

        try:
            import yaml
            with open(compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get('services', {})
            exists = service_name in services

            status = "PASS" if exists else "FAIL"
            self.validation_results.append({
                "test": f"compose_service_{service_name}",
                "description": f"Service {service_name} in {compose_file}",
                "status": status,
                "details": f"Service {'defined' if exists else 'missing'} in {compose_file}"
            })
            return exists
        except Exception as e:
            self.validation_results.append({
                "test": f"compose_service_{service_name}",
                "description": f"Service {service_name} in {compose_file}",
                "status": "FAIL",
                "details": f"Error reading compose file: {str(e)}"
            })
            return False

    def validate_python_module(self, module_path: str, description: str) -> bool:
        """Validate that a Python module can be imported."""
        try:
            # Convert file path to module path
            if module_path.endswith('.py'):
                module_path = module_path[:-3].replace('/', '.')

            __import__(module_path)
            self.validation_results.append({
                "test": f"python_module_{module_path.replace('.', '_')}",
                "description": description,
                "status": "PASS",
                "details": f"Module {module_path} imports successfully"
            })
            return True
        except ImportError as e:
            self.validation_results.append({
                "test": f"python_module_{module_path.replace('.', '_')}",
                "description": description,
                "status": "FAIL",
                "details": f"Module import failed: {str(e)}"
            })
            return False
        except Exception as e:
            self.validation_results.append({
                "test": f"python_module_{module_path.replace('.', '_')}",
                "description": description,
                "status": "WARN",
                "details": f"Module import warning: {str(e)}"
            })
            return True

    def validate_json_config(self, config_file: str, required_keys: list = None) -> bool:
        """Validate JSON configuration file."""
        config_path = self.base_path / config_file
        if not config_path.exists():
            self.validation_results.append({
                "test": f"json_config_{config_file.replace('/', '_').replace('.', '_')}",
                "description": f"JSON config file {config_file}",
                "status": "FAIL",
                "details": f"Config file missing: {config_path}"
            })
            return False

        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            if required_keys:
                missing_keys = [key for key in required_keys if key not in config_data]
                if missing_keys:
                    self.validation_results.append({
                        "test": f"json_config_{config_file.replace('/', '_').replace('.', '_')}",
                        "description": f"JSON config file {config_file}",
                        "status": "FAIL",
                        "details": f"Missing required keys: {missing_keys}"
                    })
                    return False

            self.validation_results.append({
                "test": f"json_config_{config_file.replace('/', '_').replace('.', '_')}",
                "description": f"JSON config file {config_file}",
                "status": "PASS",
                "details": f"Config file valid: {config_path}"
            })
            return True
        except Exception as e:
            self.validation_results.append({
                "test": f"json_config_{config_file.replace('/', '_').replace('.', '_')}",
                "description": f"JSON config file {config_file}",
                "status": "FAIL",
                "details": f"Config validation failed: {str(e)}"
            })
            return False

    def run_validation(self):
        """Run all validation checks."""
        logger.info("Starting system component validation...")

        # Core Infrastructure
        logger.info("Validating core infrastructure...")
        self.validate_file_exists("docker-compose.self-hosted.yml", "Main Docker Compose configuration")
        self.validate_file_exists("backend/docker-compose.yml", "Backend Docker Compose configuration")
        self.validate_file_exists("frontend/Dockerfile", "Frontend Docker configuration")
        self.validate_file_exists("backend/Dockerfile", "Backend Docker configuration")

        # Database Layer
        logger.info("Validating database layer...")
        self.validate_compose_service("docker-compose.self-hosted.yml", "postgres")
        self.validate_compose_service("docker-compose.self-hosted.yml", "redis")
        self.validate_directory_exists("database/init", "Database initialization scripts")
        self.validate_directory_exists("backend/database", "Database migration scripts")

        # Application Layer
        logger.info("Validating application layer...")
        self.validate_compose_service("docker-compose.self-hosted.yml", "backend")
        self.validate_compose_service("docker-compose.self-hosted.yml", "worker")
        self.validate_compose_service("docker-compose.self-hosted.yml", "frontend")
        self.validate_file_exists("backend/api.py", "Main FastAPI application")
        self.validate_file_exists("backend/pyproject.toml", "Python dependencies configuration")

        # AI/ML Services
        logger.info("Validating AI/ML services...")
        self.validate_compose_service("docker-compose.self-hosted.yml", "ollama")

        # Supporting Services
        logger.info("Validating supporting services...")
        self.validate_compose_service("docker-compose.self-hosted.yml", "mailhog")

        # Monitoring
        logger.info("Validating monitoring services...")
        self.validate_compose_service("docker-compose.self-hosted.yml", "prometheus")
        self.validate_compose_service("docker-compose.self-hosted.yml", "grafana")
        self.validate_directory_exists("monitoring", "Monitoring configuration")

        # Sandbox
        logger.info("Validating sandbox services...")
        self.validate_compose_service("docker-compose.self-hosted.yml", "sandbox-manager")
        self.validate_file_exists("sandbox/docker-compose.yml", "Sandbox Docker configuration")

        # Search Services
        logger.info("Validating search services...")
        self.validate_directory_exists("services/search", "Search services configuration")
        self.validate_file_exists("services/search/docker-compose.yml", "Search Docker configuration")

        # Configuration Files
        logger.info("Validating configuration files...")
        self.validate_file_exists("self-hosted.env.example", "Environment configuration example")
        self.validate_file_exists("backend/.env.example", "Backend environment example")
        self.validate_file_exists("frontend/.env.example", "Frontend environment example")

        # Python Modules
        logger.info("Validating Python modules...")
        self.validate_python_module("backend.api", "Main API module")
        self.validate_python_module("backend.services.redis", "Redis service module")
        self.validate_python_module("backend.services.local_llm", "Local LLM service module")

        # Generate Report
        return self.generate_report()

    def generate_report(self):
        """Generate validation report."""
        total_tests = len(self.validation_results)
        passed_tests = len([r for r in self.validation_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.validation_results if r["status"] == "FAIL"])
        warn_tests = len([r for r in self.validation_results if r["status"] == "WARN"])

        print("\n" + "="*80)
        print("SYSTEM COMPONENT VALIDATION REPORT")
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
        print("="*80)

        return success_rate >= 90.0  # Consider 90% success rate as passing


def main():
    """Main validation runner."""
    base_path = Path(__file__).parent.parent.parent  # Go up to suna directory

    validator = SystemValidator(base_path)
    success = validator.run_validation()

    if success:
        logger.info("🎉 System component validation PASSED!")
        return 0
    else:
        logger.error("❌ System component validation FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)





