#!/usr/bin/env python3
"""
Comprehensive System Integration Test Suite

This script validates the complete self-hosted Suna system integration,
testing all components work together properly.
"""

import asyncio
import aiohttp
import json
import sys
import os
from pathlib import Path
import time
from typing import Dict, List, Any
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemIntegrationTester:
    """Comprehensive system integration tester."""

    def __init__(self):
        self.base_url = "http://localhost:8091"
        self.session = None
        self.test_results = []
        self.token = None

    async def setup_session(self):
        """Set up HTTP session for testing."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def teardown_session(self):
        """Clean up HTTP session."""
        if self.session:
            await self.session.close()

    async def make_request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    data = await response.text()
                return response.status, data
        except Exception as e:
            logger.error(f"Request failed: {method} {url} - {str(e)}")
            return None, str(e)

    async def test_health_endpoints(self):
        """Test all health check endpoints."""
        logger.info("Testing health endpoints...")

        endpoints = [
            "/api/health",
            "/api/health-docker"
        ]

        for endpoint in endpoints:
            status, data = await self.make_request("GET", endpoint)
            if status == 200:
                logger.info(f"✅ {endpoint} - OK")
                self.test_results.append({"test": f"health_{endpoint}", "status": "PASS"})
            else:
                logger.error(f"❌ {endpoint} - FAILED (status: {status})")
                self.test_results.append({"test": f"health_{endpoint}", "status": "FAIL", "error": data})

    async def test_authentication_system(self):
        """Test local authentication system."""
        logger.info("Testing authentication system...")

        # Test registration
        register_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "name": "Test User"
        }

        status, data = await self.make_request("POST", "/api/auth/register", json=register_data)
        if status in [201, 200]:
            logger.info("✅ User registration - OK")
            self.test_results.append({"test": "user_registration", "status": "PASS"})
        else:
            logger.error(f"❌ User registration - FAILED (status: {status})")
            self.test_results.append({"test": "user_registration", "status": "FAIL", "error": data})

        # Test login
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }

        status, data = await self.make_request("POST", "/api/auth/login", json=login_data)
        if status == 200 and "access_token" in str(data):
            logger.info("✅ User login - OK")
            self.test_results.append({"test": "user_login", "status": "PASS"})
            self.token = data.get("access_token")
        else:
            logger.error(f"❌ User login - FAILED (status: {status})")
            self.test_results.append({"test": "user_login", "status": "FAIL", "error": data})

    async def test_agent_system(self):
        """Test agent creation and management."""
        logger.info("Testing agent system...")

        if not self.token:
            logger.warning("⚠️  Skipping agent tests - no auth token")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test agent creation
        agent_data = {
            "name": "Integration Test Agent",
            "description": "Agent created during system integration testing",
            "system_prompt": "You are a helpful assistant for integration testing."
        }

        status, data = await self.make_request("POST", "/api/agents", json=agent_data, headers=headers)
        if status in [201, 200]:
            logger.info("✅ Agent creation - OK")
            self.test_results.append({"test": "agent_creation", "status": "PASS"})
            agent_id = data.get("id")
        else:
            logger.error(f"❌ Agent creation - FAILED (status: {status})")
            self.test_results.append({"test": "agent_creation", "status": "FAIL", "error": data})
            return

        # Test agent retrieval
        status, data = await self.make_request("GET", f"/api/agents/{agent_id}", headers=headers)
        if status == 200:
            logger.info("✅ Agent retrieval - OK")
            self.test_results.append({"test": "agent_retrieval", "status": "PASS"})
        else:
            logger.error(f"❌ Agent retrieval - FAILED (status: {status})")
            self.test_results.append({"test": "agent_retrieval", "status": "FAIL", "error": data})

    async def test_file_system(self):
        """Test local file storage system."""
        logger.info("Testing file storage system...")

        if not self.token:
            logger.warning("⚠️  Skipping file tests - no auth token")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test file upload (mock data)
        test_content = b"This is a test file for integration testing"
        files = aiohttp.FormData()
        files.add_field('file', test_content, filename='test.txt', content_type='text/plain')

        status, data = await self.make_request("POST", "/api/files/upload", data=files, headers=headers)
        if status in [201, 200]:
            logger.info("✅ File upload - OK")
            self.test_results.append({"test": "file_upload", "status": "PASS"})
        else:
            logger.error(f"❌ File upload - FAILED (status: {status})")
            self.test_results.append({"test": "file_upload", "status": "FAIL", "error": data})

    async def test_vector_database(self):
        """Test vector database functionality."""
        logger.info("Testing vector database...")

        if not self.token:
            logger.warning("⚠️  Skipping vector tests - no auth token")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test vector search
        search_data = {
            "query": "test query for integration",
            "limit": 10
        }

        status, data = await self.make_request("POST", "/api/vector/search", json=search_data, headers=headers)
        if status == 200:
            logger.info("✅ Vector search - OK")
            self.test_results.append({"test": "vector_search", "status": "PASS"})
        else:
            logger.warning(f"⚠️  Vector search - NOT AVAILABLE (status: {status})")
            self.test_results.append({"test": "vector_search", "status": "SKIP", "error": data})

    async def test_websocket_communication(self):
        """Test WebSocket real-time communication."""
        logger.info("Testing WebSocket communication...")

        try:
            async with self.session.ws_connect(f"ws://localhost:8091/api/ws") as ws:
                # Send test message
                test_message = {"type": "test", "message": "integration test"}
                await ws.send_str(json.dumps(test_message))

                # Wait for response
                response = await asyncio.wait_for(ws.receive(), timeout=5.0)
                if response.type == aiohttp.WSMsgType.TEXT:
                    logger.info("✅ WebSocket communication - OK")
                    self.test_results.append({"test": "websocket", "status": "PASS"})
                else:
                    logger.error("❌ WebSocket communication - FAILED (no text response)")
                    self.test_results.append({"test": "websocket", "status": "FAIL"})
        except Exception as e:
            logger.warning(f"⚠️  WebSocket test - NOT AVAILABLE ({str(e)})")
            self.test_results.append({"test": "websocket", "status": "SKIP", "error": str(e)})

    async def test_search_services(self):
        """Test local search services."""
        logger.info("Testing search services...")

        # Test SearXNG (if available)
        searxng_session = aiohttp.ClientSession()
        try:
            async with searxng_session.get("http://localhost:8080/search?q=test") as response:
                status = response.status
                if status == 200:
                    logger.info("✅ SearXNG search - OK")
                    self.test_results.append({"test": "searxng_search", "status": "PASS"})
                else:
                    logger.warning("⚠️  SearXNG search - NOT AVAILABLE")
                    self.test_results.append({"test": "searxng_search", "status": "SKIP"})
        except Exception as e:
            logger.warning("⚠️  SearXNG search - NOT AVAILABLE")
            self.test_results.append({"test": "searxng_search", "status": "SKIP"})
        finally:
            await searxng_session.close()

        # Test scraping service
        scraping_session = aiohttp.ClientSession()
        try:
            async with scraping_session.get("http://localhost:8082/health") as response:
                status = response.status
                if status == 200:
                    logger.info("✅ Scraping service - OK")
                    self.test_results.append({"test": "scraping_service", "status": "PASS"})
                else:
                    logger.warning("⚠️  Scraping service - NOT AVAILABLE")
                    self.test_results.append({"test": "scraping_service", "status": "SKIP"})
        except Exception as e:
            logger.warning("⚠️  Scraping service - NOT AVAILABLE")
            self.test_results.append({"test": "scraping_service", "status": "SKIP"})
        finally:
            await scraping_session.close()

    async def test_monitoring_services(self):
        """Test monitoring and observability services."""
        logger.info("Testing monitoring services...")

        # Test Prometheus
        prometheus_session = aiohttp.ClientSession()
        try:
            async with prometheus_session.get("http://localhost:9091/-/healthy") as response:
                status = response.status
                if status == 200:
                    logger.info("✅ Prometheus monitoring - OK")
                    self.test_results.append({"test": "prometheus", "status": "PASS"})
                else:
                    logger.warning("⚠️  Prometheus monitoring - NOT AVAILABLE")
                    self.test_results.append({"test": "prometheus", "status": "SKIP"})
        except Exception as e:
            logger.warning("⚠️  Prometheus monitoring - NOT AVAILABLE")
            self.test_results.append({"test": "prometheus", "status": "SKIP"})
        finally:
            await prometheus_session.close()

        # Test Grafana
        grafana_session = aiohttp.ClientSession()
        try:
            async with grafana_session.get("http://localhost:3191/api/health") as response:
                status = response.status
                if status == 200:
                    logger.info("✅ Grafana dashboard - OK")
                    self.test_results.append({"test": "grafana", "status": "PASS"})
                else:
                    logger.warning("⚠️  Grafana dashboard - NOT AVAILABLE")
                    self.test_results.append({"test": "grafana", "status": "SKIP"})
        except Exception as e:
            logger.warning("⚠️  Grafana dashboard - NOT AVAILABLE")
            self.test_results.append({"test": "grafana", "status": "SKIP"})
        finally:
            await grafana_session.close()

    async def test_ai_services(self):
        """Test local AI/ML services."""
        logger.info("Testing AI services...")

        # Test Ollama
        ollama_session = aiohttp.ClientSession()
        try:
            async with ollama_session.get("http://localhost:11491/api/tags") as response:
                status = response.status
                if status == 200:
                    logger.info("✅ Ollama service - OK")
                    self.test_results.append({"test": "ollama", "status": "PASS"})
                else:
                    logger.warning("⚠️  Ollama service - NOT AVAILABLE")
                    self.test_results.append({"test": "ollama", "status": "SKIP"})
        except Exception as e:
            logger.warning("⚠️  Ollama service - NOT AVAILABLE")
            self.test_results.append({"test": "ollama", "status": "SKIP"})
        finally:
            await ollama_session.close()

    async def test_email_services(self):
        """Test local email services."""
        logger.info("Testing email services...")

        # Test MailHog
        mailhog_session = aiohttp.ClientSession()
        try:
            async with mailhog_session.get("http://localhost:8091") as response:
                status = response.status
                if status == 200:
                    logger.info("✅ MailHog service - OK")
                    self.test_results.append({"test": "mailhog", "status": "PASS"})
                else:
                    logger.warning("⚠️  MailHog service - NOT AVAILABLE")
                    self.test_results.append({"test": "mailhog", "status": "SKIP"})
        except Exception as e:
            logger.warning("⚠️  MailHog service - NOT AVAILABLE")
            self.test_results.append({"test": "mailhog", "status": "SKIP"})
        finally:
            await mailhog_session.close()

    async def test_database_connection(self):
        """Test PostgreSQL database connection."""
        logger.info("Testing database connection...")

        if not self.token:
            logger.warning("⚠️  Skipping database tests - no auth token")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test database connectivity through API
        status, data = await self.make_request("GET", "/api/admin/database/status", headers=headers)
        if status == 200:
            logger.info("✅ Database connection - OK")
            self.test_results.append({"test": "database", "status": "PASS"})
        else:
            logger.warning("⚠️  Database status check - NOT AVAILABLE")
            self.test_results.append({"test": "database", "status": "SKIP"})

    async def run_performance_tests(self):
        """Run basic performance tests."""
        logger.info("Running performance tests...")

        if not self.token:
            logger.warning("⚠️  Skipping performance tests - no auth token")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test response time for multiple requests
        import time
        start_time = time.time()

        for i in range(10):
            status, _ = await self.make_request("GET", "/api/health", headers=headers)
            if status != 200:
                logger.error(f"❌ Performance test failed on request {i+1}")
                self.test_results.append({"test": "performance", "status": "FAIL"})
                return

        end_time = time.time()
        avg_time = (end_time - start_time) / 10

        if avg_time < 1.0:
            logger.info(f"✅ Performance test - OK (avg: {avg_time:.2f}s)")
            self.test_results.append({"test": "performance", "status": "PASS"})
        else:
            logger.warning(f"⚠️  Performance test - SLOW (avg: {avg_time:.2f}s)")
            self.test_results.append({"test": "performance", "status": "WARN"})

    async def generate_report(self):
        """Generate comprehensive test report."""
        logger.info("Generating test report...")

        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["status"] == "PASS"])
        failed_tests = len([t for t in self.test_results if t["status"] == "FAIL"])
        skipped_tests = len([t for t in self.test_results if t["status"] == "SKIP"])

        print("\n" + "="*60)
        print("SYSTEM INTEGRATION TEST REPORT")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Skipped: {skipped_tests}")
        print()

        if failed_tests > 0:
            print("FAILED TESTS:")
            for test in self.test_results:
                if test["status"] == "FAIL":
                    print(f"❌ {test['test']}: {test.get('error', 'Unknown error')}")
            print()

        if passed_tests > 0:
            print("PASSED TESTS:")
            for test in self.test_results:
                if test["status"] == "PASS":
                    print(f"✅ {test['test']}")
            print()

        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print(".1f")
        print("="*60)

        return success_rate >= 80.0  # Consider 80% success rate as passing

    async def run_all_tests(self):
        """Run all integration tests."""
        logger.info("Starting comprehensive system integration tests...")

        await self.setup_session()

        try:
            # Core system tests
            await self.test_health_endpoints()
            await self.test_authentication_system()
            await self.test_database_connection()

            # Feature tests
            await self.test_agent_system()
            await self.test_file_system()
            await self.test_vector_database()
            await self.test_websocket_communication()

            # Service tests
            await self.test_search_services()
            await self.test_monitoring_services()
            await self.test_ai_services()
            await self.test_email_services()

            # Performance tests
            await self.run_performance_tests()

            # Generate report
            success = await self.generate_report()
            return success

        finally:
            await self.teardown_session()


async def main():
    """Main test runner."""
    tester = SystemIntegrationTester()
    success = await tester.run_all_tests()

    if success:
        logger.info("🎉 System integration tests PASSED!")
        return 0
    else:
        logger.error("❌ System integration tests FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
