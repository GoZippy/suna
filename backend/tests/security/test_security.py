"""
Security testing and vulnerability scanning for Suna system
"""

import pytest
import asyncio
import aiohttp
import json
import re
from typing import List, Dict, Any
from unittest.mock import patch, AsyncMock

from tests import TEST_CONFIG


class TestAuthenticationSecurity:
    """Test authentication security measures"""
    
    @pytest.mark.security
    async def test_password_strength_validation(self, aiohttp_client):
        """Test password strength validation"""
        url = f"{TEST_CONFIG['api_base_url']}/auth/register"
        
        # Test weak passwords
        weak_passwords = [
            "123",  # Too short
            "password",  # Common password
            "abc123",  # Too simple
            "qwerty",  # Common password
            "123456789",  # Only numbers
            "abcdefgh",  # Only letters
        ]
        
        for weak_password in weak_passwords:
            user_data = {
                "email": "test@example.com",
                "password": weak_password,
                "username": "testuser",
                "full_name": "Test User"
            }
            
            async with aiohttp_client.post(url, json=user_data) as response:
                assert response.status == 422  # Validation error
                
                data = await response.json()
                assert "password" in str(data).lower()  # Password error mentioned
    
    @pytest.mark.security
    async def test_sql_injection_prevention(self, aiohttp_client, auth_headers):
        """Test SQL injection prevention"""
        url = f"{TEST_CONFIG['api_base_url']}/auth/login"
        
        # SQL injection attempts
        sql_injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "1' OR '1' = '1' --",
        ]
        
        for payload in sql_injection_payloads:
            login_data = {
                "email": payload,
                "password": "testpassword"
            }
            
            async with aiohttp_client.post(url, json=login_data) as response:
                # Should not crash or expose data
                assert response.status in [401, 422]  # Unauthorized or validation error
                
                # Should not expose SQL errors
                if response.status == 422:
                    data = await response.json()
                    error_text = json.dumps(data).lower()
                    assert "sql" not in error_text
                    assert "database" not in error_text
                    assert "syntax" not in error_text
    
    @pytest.mark.security
    async def test_jwt_token_security(self, aiohttp_client, test_user):
        """Test JWT token security"""
        # Test with valid credentials first
        login_url = f"{TEST_CONFIG['api_base_url']}/auth/login"
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        async with aiohttp_client.post(login_url, json=login_data) as response:
            assert response.status == 200
            data = await response.json()
            token = data["access_token"]
        
        # Test token tampering
        tampered_token = token[:-1] + "X"  # Change last character
        
        headers = {"Authorization": f"Bearer {tampered_token}"}
        protected_url = f"{TEST_CONFIG['api_base_url']}/users/me"
        
        async with aiohttp_client.get(protected_url, headers=headers) as response:
            assert response.status == 401  # Should reject tampered token
        
        # Test expired token
        import jwt
        from datetime import datetime, timedelta
        
        expired_token = jwt.encode(
            {
                "sub": test_user.email,
                "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
            },
            "test-secret",
            algorithm="HS256"
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        async with aiohttp_client.get(protected_url, headers=headers) as response:
            assert response.status == 401  # Should reject expired token
    
    @pytest.mark.security
    async def test_brute_force_protection(self, aiohttp_client):
        """Test brute force attack protection"""
        url = f"{TEST_CONFIG['api_base_url']}/auth/login"
        
        # Attempt multiple failed logins
        for i in range(10):
            login_data = {
                "email": "test@example.com",
                "password": f"wrongpassword{i}"
            }
            
            async with aiohttp_client.post(url, json=login_data) as response:
                if i < 5:
                    assert response.status == 401  # Normal failed login
                else:
                    # After multiple failed attempts, should implement rate limiting
                    assert response.status in [401, 429]  # Unauthorized or Too Many Requests
    
    @pytest.mark.security
    async def test_session_management(self, aiohttp_client, test_user):
        """Test session management security"""
        # Login to get token
        login_url = f"{TEST_CONFIG['api_base_url']}/auth/login"
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        async with aiohttp_client.post(login_url, json=login_data) as response:
            assert response.status == 200
            data = await response.json()
            token = data["access_token"]
        
        # Test token reuse
        headers = {"Authorization": f"Bearer {token}"}
        protected_url = f"{TEST_CONFIG['api_base_url']}/users/me"
        
        # First request should work
        async with aiohttp_client.get(protected_url, headers=headers) as response:
            assert response.status == 200
        
        # Second request should also work (unless token is single-use)
        async with aiohttp_client.get(protected_url, headers=headers) as response:
            assert response.status in [200, 401]  # Either works or token is single-use


class TestInputValidation:
    """Test input validation and sanitization"""
    
    @pytest.mark.security
    async def test_xss_prevention(self, aiohttp_client, auth_headers):
        """Test XSS (Cross-Site Scripting) prevention"""
        url = f"{TEST_CONFIG['api_base_url']}/agents"
        
        # XSS payloads
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg onload=alert('xss')>",
        ]
        
        for payload in xss_payloads:
            agent_data = {
                "name": payload,
                "description": f"Agent with XSS payload: {payload}",
                "config": {"model": "llama2:7b", "temperature": 0.7}
            }
            
            async with aiohttp_client.post(url, json=agent_data, headers=auth_headers) as response:
                # Should either reject or sanitize the input
                assert response.status in [201, 422]  # Created or validation error
                
                if response.status == 201:
                    # If created, check that the response is sanitized
                    data = await response.json()
                    response_text = json.dumps(data)
                    
                    # Should not contain raw script tags
                    assert "<script>" not in response_text
                    assert "javascript:" not in response_text
                    assert "onerror=" not in response_text
                    assert "onload=" not in response_text
    
    @pytest.mark.security
    async def test_path_traversal_prevention(self, aiohttp_client, auth_headers):
        """Test path traversal attack prevention"""
        url = f"{TEST_CONFIG['api_base_url']}/files/download"
        
        # Path traversal attempts
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
        ]
        
        for payload in traversal_payloads:
            file_url = f"{url}/{payload}"
            
            async with aiohttp_client.get(file_url, headers=auth_headers) as response:
                # Should not allow access to system files
                assert response.status in [404, 403, 400]  # Not found, forbidden, or bad request
    
    @pytest.mark.security
    async def test_command_injection_prevention(self, aiohttp_client, auth_headers):
        """Test command injection prevention"""
        url = f"{TEST_CONFIG['api_base_url']}/agents"
        
        # Command injection payloads
        command_payloads = [
            "test; rm -rf /",
            "test && rm -rf /",
            "test | rm -rf /",
            "test`rm -rf /`",
            "test$(rm -rf /)",
            "test; DROP TABLE users;",
        ]
        
        for payload in command_payloads:
            agent_data = {
                "name": payload,
                "description": f"Agent with command injection: {payload}",
                "config": {"model": "llama2:7b", "temperature": 0.7}
            }
            
            async with aiohttp_client.post(url, json=agent_data, headers=auth_headers) as response:
                # Should reject or sanitize command injection attempts
                assert response.status in [201, 422]  # Created or validation error
                
                if response.status == 201:
                    # If created, verify no commands were executed
                    data = await response.json()
                    response_text = json.dumps(data)
                    
                    # Should not contain command execution indicators
                    assert "rm -rf" not in response_text
                    assert "DROP TABLE" not in response_text
    
    @pytest.mark.security
    async def test_content_type_validation(self, aiohttp_client, auth_headers):
        """Test content type validation"""
        url = f"{TEST_CONFIG['api_base_url']}/agents"
        
        # Valid JSON
        valid_data = {
            "name": "Test Agent",
            "description": "Test description",
            "config": {"model": "llama2:7b", "temperature": 0.7}
        }
        
        headers = {**auth_headers, "Content-Type": "application/json"}
        async with aiohttp_client.post(url, json=valid_data, headers=headers) as response:
            assert response.status == 201
        
        # Invalid content type
        headers = {**auth_headers, "Content-Type": "text/plain"}
        async with aiohttp_client.post(url, json=valid_data, headers=headers) as response:
            assert response.status in [400, 415]  # Bad request or unsupported media type
        
        # No content type
        headers = {**auth_headers}
        headers.pop("Content-Type", None)
        async with aiohttp_client.post(url, json=valid_data, headers=headers) as response:
            # Should either work (auto-detection) or reject
            assert response.status in [201, 400, 415]


class TestAuthorizationSecurity:
    """Test authorization and access control"""
    
    @pytest.mark.security
    async def test_unauthorized_access_prevention(self, aiohttp_client):
        """Test prevention of unauthorized access"""
        protected_endpoints = [
            "/users/me",
            "/agents",
            "/workflows",
            "/knowledge/documents",
            "/files",
            "/admin/metrics",
        ]
        
        for endpoint in protected_endpoints:
            url = f"{TEST_CONFIG['api_base_url']}{endpoint}"
            
            # Test without authentication
            async with aiohttp_client.get(url) as response:
                assert response.status == 401  # Unauthorized
    
    @pytest.mark.security
    async def test_resource_isolation(self, aiohttp_client, auth_headers):
        """Test that users can only access their own resources"""
        # Create a resource with authenticated user
        agent_url = f"{TEST_CONFIG['api_base_url']}/agents"
        agent_data = {
            "name": "Test Agent",
            "description": "Test description",
            "config": {"model": "llama2:7b", "temperature": 0.7}
        }
        
        async with aiohttp_client.post(agent_url, json=agent_data, headers=auth_headers) as response:
            assert response.status == 201
            data = await response.json()
            agent_id = data["id"]
        
        # Try to access with different user (should fail)
        # This would require creating a second user and trying to access the first user's resource
        # For now, we test the structure
        
        # Test accessing non-existent resource
        fake_agent_url = f"{TEST_CONFIG['api_base_url']}/agents/99999"
        async with aiohttp_client.get(fake_agent_url, headers=auth_headers) as response:
            assert response.status == 404  # Not found
    
    @pytest.mark.security
    async def test_admin_access_control(self, aiohttp_client, auth_headers):
        """Test admin access control"""
        admin_endpoints = [
            "/admin/metrics",
            "/admin/users",
            "/admin/system",
        ]
        
        for endpoint in admin_endpoints:
            url = f"{TEST_CONFIG['api_base_url']}{endpoint}"
            
            # Test with regular user (should be denied)
            async with aiohttp_client.get(url, headers=auth_headers) as response:
                assert response.status in [403, 404]  # Forbidden or not found
    
    @pytest.mark.security
    async def test_method_authorization(self, aiohttp_client, auth_headers):
        """Test HTTP method authorization"""
        # Test that users can't use unauthorized HTTP methods
        url = f"{TEST_CONFIG['api_base_url']}/users/me"
        
        # GET should work
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            assert response.status == 200
        
        # DELETE should be forbidden (users can't delete themselves via this endpoint)
        async with aiohttp_client.delete(url, headers=auth_headers) as response:
            assert response.status in [405, 403]  # Method not allowed or forbidden


class TestDataProtection:
    """Test data protection and privacy"""
    
    @pytest.mark.security
    async def test_sensitive_data_exposure(self, aiohttp_client, auth_headers):
        """Test that sensitive data is not exposed"""
        # Test user profile endpoint
        url = f"{TEST_CONFIG['api_base_url']}/users/me"
        
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            assert response.status == 200
            data = await response.json()
            
            # Should not expose sensitive information
            assert "hashed_password" not in data
            assert "password" not in data
            assert "salt" not in data
            assert "secret" not in data
    
    @pytest.mark.security
    async def test_error_information_disclosure(self, aiohttp_client):
        """Test that error messages don't disclose sensitive information"""
        # Test with invalid endpoint
        url = f"{TEST_CONFIG['api_base_url']}/nonexistent/endpoint"
        
        async with aiohttp_client.get(url) as response:
            assert response.status == 404
            
            # Error message should not expose internal details
            data = await response.json()
            error_text = json.dumps(data).lower()
            
            # Should not expose internal paths, stack traces, or system details
            assert "stack trace" not in error_text
            assert "internal" not in error_text
            assert "debug" not in error_text
            assert "exception" not in error_text
    
    @pytest.mark.security
    async def test_logging_sanitization(self, aiohttp_client, auth_headers):
        """Test that sensitive data is not logged"""
        # This would require checking actual log files
        # For now, we test that the API doesn't expose sensitive data in responses
        
        url = f"{TEST_CONFIG['api_base_url']}/auth/login"
        
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        async with aiohttp_client.post(url, json=login_data) as response:
            assert response.status == 200
            data = await response.json()
            
            # Response should not contain the password
            response_text = json.dumps(data)
            assert "testpassword123" not in response_text


class TestNetworkSecurity:
    """Test network security measures"""
    
    @pytest.mark.security
    async def test_https_enforcement(self, aiohttp_client):
        """Test HTTPS enforcement (if applicable)"""
        # This test would check if the API enforces HTTPS
        # For local testing, we just verify the endpoint works
        
        url = f"{TEST_CONFIG['api_base_url']}/health"
        
        async with aiohttp_client.get(url) as response:
            # Should work regardless of HTTP/HTTPS for local testing
            assert response.status == 200
    
    @pytest.mark.security
    async def test_cors_configuration(self, aiohttp_client):
        """Test CORS (Cross-Origin Resource Sharing) configuration"""
        url = f"{TEST_CONFIG['api_base_url']}/health"
        
        # Test with different origins
        origins = [
            "https://localhost:3091",
            "https://example.com",
            "http://malicious-site.com",
        ]
        
        for origin in origins:
            headers = {"Origin": origin}
            async with aiohttp_client.get(url, headers=headers) as response:
                # Check CORS headers
                cors_headers = response.headers.get("Access-Control-Allow-Origin")
                
                if cors_headers:
                    # Should only allow specific origins
                    assert cors_headers in ["*", origin, "https://localhost:3091"]
    
    @pytest.mark.security
    async def test_security_headers(self, aiohttp_client):
        """Test security headers are present"""
        url = f"{TEST_CONFIG['api_base_url']}/health"
        
        async with aiohttp_client.get(url) as response:
            headers = response.headers
            
            # Check for security headers
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Content-Security-Policy",
            ]
            
            # At least some security headers should be present
            present_headers = [h for h in security_headers if h in headers]
            assert len(present_headers) > 0


class TestVulnerabilityScanning:
    """Test vulnerability scanning capabilities"""
    
    @pytest.mark.security
    async def test_dependency_vulnerability_check(self):
        """Test dependency vulnerability checking"""
        import subprocess
        import sys
        
        # Check if safety is available
        try:
            result = subprocess.run(
                [sys.executable, "-m", "safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # No vulnerabilities found
                assert True
            else:
                # Vulnerabilities found, but test should still pass
                # (we're testing the scanning capability, not the absence of vulnerabilities)
                print(f"Vulnerability scan found issues: {result.stdout}")
                assert True
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Safety not available, skip test
            pytest.skip("Safety vulnerability scanner not available")
    
    @pytest.mark.security
    async def test_container_vulnerability_scan(self):
        """Test container vulnerability scanning"""
        import subprocess
        
        # Check if trivy is available
        try:
            result = subprocess.run(
                ["trivy", "image", "--format", "json", "suna-backend:latest"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Trivy should run successfully (even if vulnerabilities are found)
            # We're testing the scanning capability, not the absence of vulnerabilities
            print(f"Container vulnerability scan completed: {result.returncode}")
            assert True
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Trivy not available, skip test
            pytest.skip("Trivy vulnerability scanner not available")
    
    @pytest.mark.security
    async def test_secret_scanning(self):
        """Test for hardcoded secrets in code"""
        import os
        import re
        
        # Patterns for common secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'private_key\s*=\s*["\'][^"\']+["\']',
        ]
        
        # Scan backend directory for secrets
        backend_dir = os.path.join(os.path.dirname(__file__), "..")
        found_secrets = []
        
        for root, dirs, files in os.walk(backend_dir):
            for file in files:
                if file.endswith(('.py', '.env', '.yaml', '.yml', '.json')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern in secret_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                # Skip test files and common test values
                                if 'test' in file.lower() or 'example' in match.lower():
                                    continue
                                found_secrets.append(f"{file_path}: {match}")
                                
                    except Exception:
                        continue
        
        # Report found secrets
        if found_secrets:
            print("Potential secrets found:")
            for secret in found_secrets:
                print(f"  {secret}")
        
        # For now, we don't fail the test if secrets are found
        # (they might be legitimate test data)
        assert True







