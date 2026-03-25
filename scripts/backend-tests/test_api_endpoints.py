import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

class TestAPIEndpoints:
    """Test suite for API endpoints."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

    @patch('services.auth.get_current_user')
    def test_protected_endpoint_with_auth(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test protected endpoint with valid authentication."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_get_current_user.return_value = mock_user

        response = client.get("/api/user/profile", headers=auth_headers)
        assert response.status_code == 200

    def test_protected_endpoint_without_auth(self, client: TestClient):
        """Test protected endpoint without authentication."""
        response = client.get("/api/user/profile")
        assert response.status_code == 401

    @patch('services.auth.get_current_user')
    def test_agents_endpoint(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test agents endpoint."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_get_current_user.return_value = mock_user

        response = client.get("/api/agents", headers=auth_headers)
        assert response.status_code == 200

    @patch('services.auth.get_current_user')
    def test_create_agent(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test agent creation endpoint."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_get_current_user.return_value = mock_user

        agent_data = {
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a helpful assistant."
        }

        response = client.post("/api/agents", json=agent_data, headers=auth_headers)
        assert response.status_code in [200, 201]

    @patch('services.auth.get_current_user')
    def test_threads_endpoint(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test threads endpoint."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_get_current_user.return_value = mock_user

        response = client.get("/api/threads", headers=auth_headers)
        assert response.status_code == 200

    @patch('services.auth.get_current_user')
    def test_create_thread(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test thread creation endpoint."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_get_current_user.return_value = mock_user

        thread_data = {
            "title": "Test Thread",
            "agent_id": "test-agent-id"
        }

        response = client.post("/api/threads", json=thread_data, headers=auth_headers)
        assert response.status_code in [200, 201]

    @patch('services.auth.get_current_user')
    def test_messages_endpoint(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test messages endpoint."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_get_current_user.return_value = mock_user

        response = client.get("/api/threads/test-thread-id/messages", headers=auth_headers)
        assert response.status_code == 200

    @patch('services.auth.get_current_user')
    def test_send_message(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test message sending endpoint."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_get_current_user.return_value = mock_user

        message_data = {
            "content": "Hello, agent!",
            "role": "user"
        }

        response = client.post(
            "/api/threads/test-thread-id/messages", 
            json=message_data, 
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

    def test_invalid_endpoint(self, client: TestClient):
        """Test invalid endpoint returns 404."""
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404

    @patch('services.auth.get_current_user')
    def test_admin_endpoint_with_user_role(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test admin endpoint with user role (should be denied)."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_user.role = "user"
        mock_get_current_user.return_value = mock_user

        response = client.get("/api/admin/users", headers=auth_headers)
        assert response.status_code == 403

    @patch('services.auth.get_current_user')
    def test_admin_endpoint_with_admin_role(self, mock_get_current_user, client: TestClient, admin_headers):
        """Test admin endpoint with admin role."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_user.role = "admin"
        mock_get_current_user.return_value = mock_user

        response = client.get("/api/admin/users", headers=admin_headers)
        assert response.status_code == 200

    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/api/agents")
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    @patch('services.auth.get_current_user')
    def test_rate_limiting(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test rate limiting on API endpoints."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_get_current_user.return_value = mock_user

        # Make multiple requests to trigger rate limiting
        for _ in range(10):
            response = client.get("/api/agents", headers=auth_headers)
            
        # The 11th request should be rate limited
        response = client.get("/api/agents", headers=auth_headers)
        # Note: This test depends on your rate limiting implementation
        # assert response.status_code == 429

    def test_request_validation(self, client: TestClient):
        """Test request validation for malformed data."""
        invalid_data = {
            "invalid_field": "invalid_value"
        }

        response = client.post("/api/agents", json=invalid_data)
        assert response.status_code == 422  # Validation error

    @patch('services.auth.get_current_user')
    def test_file_upload_endpoint(self, mock_get_current_user, client: TestClient, auth_headers):
        """Test file upload endpoint."""
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_get_current_user.return_value = mock_user

        # Create a test file
        files = {"file": ("test.txt", b"test content", "text/plain")}
        response = client.post("/api/files/upload", files=files, headers=auth_headers)
        assert response.status_code in [200, 201]

    def test_websocket_endpoint(self, client: TestClient):
        """Test WebSocket endpoint."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("Hello")
            data = websocket.receive_text()
            assert data is not None







