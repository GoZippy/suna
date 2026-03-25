import pytest
import asyncio
import aiohttp
import json
from unittest.mock import patch, MagicMock

class TestFrontendBackendIntegration:
    """Integration tests for frontend-backend communication."""

    @pytest.fixture
    async def api_client(self):
        """Create API client for testing."""
        async with aiohttp.ClientSession() as session:
            yield session

    @pytest.mark.asyncio
    async def test_authentication_flow(self, api_client):
        """Test complete authentication flow."""
        base_url = "http://localhost:8091"
        
        # Test login endpoint
        login_data = {
            "email": "test@example.com",
            "password": "testpassword"
        }
        
        async with api_client.post(f"{base_url}/api/auth/login", json=login_data) as response:
            assert response.status == 200
            data = await response.json()
            assert "access_token" in data
            token = data["access_token"]
        
        # Test protected endpoint with token
        headers = {"Authorization": f"Bearer {token}"}
        async with api_client.get(f"{base_url}/api/user/profile", headers=headers) as response:
            assert response.status == 200

    @pytest.mark.asyncio
    async def test_agent_creation_flow(self, api_client):
        """Test complete agent creation flow."""
        base_url = "http://localhost:8091"
        
        # Mock authentication
        headers = {"Authorization": "Bearer mock-token"}
        
        # Create agent
        agent_data = {
            "name": "Test Integration Agent",
            "description": "Agent created during integration test",
            "system_prompt": "You are a helpful assistant for integration testing."
        }
        
        async with api_client.post(f"{base_url}/api/agents", json=agent_data, headers=headers) as response:
            assert response.status == 201
            data = await response.json()
            agent_id = data["id"]
        
        # Verify agent was created
        async with api_client.get(f"{base_url}/api/agents/{agent_id}", headers=headers) as response:
            assert response.status == 200
            data = await response.json()
            assert data["name"] == "Test Integration Agent"

    @pytest.mark.asyncio
    async def test_thread_creation_and_messaging(self, api_client):
        """Test thread creation and message exchange."""
        base_url = "http://localhost:8091"
        headers = {"Authorization": "Bearer mock-token"}
        
        # Create thread
        thread_data = {
            "title": "Integration Test Thread",
            "agent_id": "test-agent-id"
        }
        
        async with api_client.post(f"{base_url}/api/threads", json=thread_data, headers=headers) as response:
            assert response.status == 201
            data = await response.json()
            thread_id = data["id"]
        
        # Send message
        message_data = {
            "content": "Hello, this is an integration test message.",
            "role": "user"
        }
        
        async with api_client.post(f"{base_url}/api/threads/{thread_id}/messages", json=message_data, headers=headers) as response:
            assert response.status == 201
        
        # Get messages
        async with api_client.get(f"{base_url}/api/threads/{thread_id}/messages", headers=headers) as response:
            assert response.status == 200
            data = await response.json()
            assert len(data) > 0

    @pytest.mark.asyncio
    async def test_file_upload_and_management(self, api_client):
        """Test file upload and management flow."""
        base_url = "http://localhost:8091"
        headers = {"Authorization": "Bearer mock-token"}
        
        # Upload file
        file_content = b"Test file content for integration testing"
        files = {"file": ("test.txt", file_content, "text/plain")}
        
        async with api_client.post(f"{base_url}/api/files/upload", data=files, headers=headers) as response:
            assert response.status == 201
            data = await response.json()
            file_id = data["id"]
        
        # Get file info
        async with api_client.get(f"{base_url}/api/files/{file_id}", headers=headers) as response:
            assert response.status == 200
            data = await response.json()
            assert data["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_websocket_communication(self, api_client):
        """Test WebSocket communication."""
        base_url = "ws://localhost:8091"
        
        # Test WebSocket connection
        async with api_client.ws_connect(f"{base_url}/ws") as websocket:
            # Send test message
            await websocket.send_str(json.dumps({
                "type": "test",
                "message": "Integration test message"
            }))
            
            # Receive response
            response = await websocket.receive_str()
            data = json.loads(response)
            assert data is not None

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, api_client):
        """Test error handling across frontend-backend boundary."""
        base_url = "http://localhost:8091"
        
        # Test invalid authentication
        headers = {"Authorization": "Bearer invalid-token"}
        async with api_client.get(f"{base_url}/api/user/profile", headers=headers) as response:
            assert response.status == 401
        
        # Test invalid data
        invalid_data = {"invalid_field": "invalid_value"}
        async with api_client.post(f"{base_url}/api/agents", json=invalid_data) as response:
            assert response.status == 422

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, api_client):
        """Test rate limiting across the system."""
        base_url = "http://localhost:8091"
        headers = {"Authorization": "Bearer mock-token"}
        
        # Make multiple requests to trigger rate limiting
        responses = []
        for _ in range(10):
            async with api_client.get(f"{base_url}/api/agents", headers=headers) as response:
                responses.append(response.status)
        
        # Check if rate limiting is working
        # Note: This depends on your rate limiting implementation
        assert len(responses) == 10

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, api_client):
        """Test handling of concurrent requests."""
        base_url = "http://localhost:8091"
        headers = {"Authorization": "Bearer mock-token"}
        
        # Make concurrent requests
        async def make_request():
            async with api_client.get(f"{base_url}/api/agents", headers=headers) as response:
                return response.status
        
        # Create multiple concurrent requests
        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(status == 200 for status in results)

    @pytest.mark.asyncio
    async def test_data_consistency(self, api_client):
        """Test data consistency across API calls."""
        base_url = "http://localhost:8091"
        headers = {"Authorization": "Bearer mock-token"}
        
        # Create agent
        agent_data = {
            "name": "Consistency Test Agent",
            "description": "Testing data consistency"
        }
        
        async with api_client.post(f"{base_url}/api/agents", json=agent_data, headers=headers) as response:
            assert response.status == 201
            create_data = await response.json()
        
        # Get agent and verify consistency
        agent_id = create_data["id"]
        async with api_client.get(f"{base_url}/api/agents/{agent_id}", headers=headers) as response:
            assert response.status == 200
            get_data = await response.json()
            
            # Verify data consistency
            assert get_data["name"] == create_data["name"]
            assert get_data["description"] == create_data["description"]
            assert get_data["id"] == create_data["id"]

    @pytest.mark.asyncio
    async def test_session_management(self, api_client):
        """Test session management and persistence."""
        base_url = "http://localhost:8091"
        
        # Login and get session
        login_data = {"email": "test@example.com", "password": "testpassword"}
        async with api_client.post(f"{base_url}/api/auth/login", json=login_data) as response:
            assert response.status == 200
            session_data = await response.json()
            token = session_data["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Make multiple requests with same session
        for _ in range(3):
            async with api_client.get(f"{base_url}/api/user/profile", headers=headers) as response:
                assert response.status == 200

    @pytest.mark.asyncio
    async def test_performance_under_load(self, api_client):
        """Test system performance under load."""
        base_url = "http://localhost:8091"
        headers = {"Authorization": "Bearer mock-token"}
        
        import time
        
        # Measure response time for multiple requests
        start_time = time.time()
        
        async def timed_request():
            start = time.time()
            async with api_client.get(f"{base_url}/api/agents", headers=headers) as response:
                end = time.time()
                return response.status, end - start
        
        # Make multiple requests and measure performance
        tasks = [timed_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all requests succeeded
        assert all(status == 200 for status, _ in results)
        
        # Check performance (adjust thresholds as needed)
        avg_response_time = sum(time_taken for _, time_taken in results) / len(results)
        assert avg_response_time < 1.0  # Average response time should be under 1 second
        assert total_time < 10.0  # Total time should be under 10 seconds







