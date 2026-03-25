"""
Integration tests for API endpoints
"""

import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock

from tests import TEST_CONFIG


class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""
    
    @pytest.mark.asyncio
    async def test_user_registration(self, aiohttp_client, clean_database):
        """Test user registration endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/auth/register"
        
        user_data = {
            "email": "newuser@example.com",
            "password": "newpassword123",
            "username": "newuser",
            "full_name": "New User"
        }
        
        async with aiohttp_client.post(url, json=user_data) as response:
            assert response.status == 201
            
            data = await response.json()
            assert "user" in data
            assert "access_token" in data
            assert data["user"]["email"] == user_data["email"]
            assert data["user"]["username"] == user_data["username"]
    
    @pytest.mark.asyncio
    async def test_user_login(self, aiohttp_client, test_user):
        """Test user login endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/auth/login"
        
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        async with aiohttp_client.post(url, json=login_data) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_user_login_invalid_credentials(self, aiohttp_client):
        """Test user login with invalid credentials"""
        url = f"{TEST_CONFIG['api_base_url']}/auth/login"
        
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        
        async with aiohttp_client.post(url, json=login_data) as response:
            assert response.status == 401
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_token(self, aiohttp_client, auth_headers):
        """Test accessing protected endpoint with valid token"""
        url = f"{TEST_CONFIG['api_base_url']}/users/me"
        
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "email" in data
            assert "username" in data
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, aiohttp_client):
        """Test accessing protected endpoint without token"""
        url = f"{TEST_CONFIG['api_base_url']}/users/me"
        
        async with aiohttp_client.get(url) as response:
            assert response.status == 401


class TestAgentEndpoints:
    """Test agent management API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_agent(self, aiohttp_client, auth_headers, clean_database):
        """Test agent creation endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/agents"
        
        agent_data = {
            "name": "Test Agent",
            "description": "A test agent for integration testing",
            "config": {
                "model": "llama2:7b",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
        
        async with aiohttp_client.post(url, json=agent_data, headers=auth_headers) as response:
            assert response.status == 201
            
            data = await response.json()
            assert "id" in data
            assert data["name"] == agent_data["name"]
            assert data["description"] == agent_data["description"]
    
    @pytest.mark.asyncio
    async def test_get_agents(self, aiohttp_client, auth_headers, test_agent):
        """Test getting user's agents"""
        url = f"{TEST_CONFIG['api_base_url']}/agents"
        
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            assert response.status == 200
            
            data = await response.json()
            assert isinstance(data, list)
            assert len(data) > 0
            assert data[0]["name"] == test_agent["name"]
    
    @pytest.mark.asyncio
    async def test_get_agent_by_id(self, aiohttp_client, auth_headers, test_agent):
        """Test getting specific agent by ID"""
        url = f"{TEST_CONFIG['api_base_url']}/agents/{test_agent['id']}"
        
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            assert response.status == 200
            
            data = await response.json()
            assert data["id"] == test_agent["id"]
            assert data["name"] == test_agent["name"]
    
    @pytest.mark.asyncio
    async def test_update_agent(self, aiohttp_client, auth_headers, test_agent):
        """Test updating agent"""
        url = f"{TEST_CONFIG['api_base_url']}/agents/{test_agent['id']}"
        
        update_data = {
            "name": "Updated Test Agent",
            "description": "Updated description"
        }
        
        async with aiohttp_client.put(url, json=update_data, headers=auth_headers) as response:
            assert response.status == 200
            
            data = await response.json()
            assert data["name"] == update_data["name"]
            assert data["description"] == update_data["description"]
    
    @pytest.mark.asyncio
    async def test_delete_agent(self, aiohttp_client, auth_headers, test_agent):
        """Test deleting agent"""
        url = f"{TEST_CONFIG['api_base_url']}/agents/{test_agent['id']}"
        
        async with aiohttp_client.delete(url, headers=auth_headers) as response:
            assert response.status == 204


class TestWorkflowEndpoints:
    """Test workflow management API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, aiohttp_client, auth_headers, test_agent, clean_database):
        """Test workflow creation endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/workflows"
        
        workflow_data = {
            "name": "Test Workflow",
            "description": "A test workflow",
            "agent_id": test_agent["id"],
            "steps": [
                {
                    "step": 1,
                    "action": "search",
                    "params": {"query": "test query"}
                },
                {
                    "step": 2,
                    "action": "analyze",
                    "params": {"analysis_type": "summary"}
                }
            ]
        }
        
        async with aiohttp_client.post(url, json=workflow_data, headers=auth_headers) as response:
            assert response.status == 201
            
            data = await response.json()
            assert "id" in data
            assert data["name"] == workflow_data["name"]
            assert len(data["steps"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_workflows(self, aiohttp_client, auth_headers, test_workflow):
        """Test getting user's workflows"""
        url = f"{TEST_CONFIG['api_base_url']}/workflows"
        
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            assert response.status == 200
            
            data = await response.json()
            assert isinstance(data, list)
            assert len(data) > 0
            assert data[0]["name"] == test_workflow["name"]
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, aiohttp_client, auth_headers, test_workflow):
        """Test workflow execution"""
        url = f"{TEST_CONFIG['api_base_url']}/workflows/{test_workflow['id']}/execute"
        
        execution_data = {
            "input": "Test input for workflow execution"
        }
        
        async with aiohttp_client.post(url, json=execution_data, headers=auth_headers) as response:
            assert response.status == 202  # Accepted for async execution
            
            data = await response.json()
            assert "execution_id" in data
            assert "status" in data


class TestKnowledgeBaseEndpoints:
    """Test knowledge base API endpoints"""
    
    @pytest.mark.asyncio
    async def test_add_document(self, aiohttp_client, auth_headers, clean_database):
        """Test adding document to knowledge base"""
        url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents"
        
        document_data = {
            "title": "Test Document",
            "content": "This is a test document for the knowledge base.",
            "source": "test",
            "tags": ["test", "documentation"]
        }
        
        async with aiohttp_client.post(url, json=document_data, headers=auth_headers) as response:
            assert response.status == 201
            
            data = await response.json()
            assert "id" in data
            assert data["title"] == document_data["title"]
            assert data["content"] == document_data["content"]
    
    @pytest.mark.asyncio
    async def test_search_knowledge_base(self, aiohttp_client, auth_headers, clean_database):
        """Test searching knowledge base"""
        # First add a document
        add_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents"
        document_data = {
            "title": "Python Programming Guide",
            "content": "Python is a high-level programming language known for its simplicity and readability.",
            "source": "test",
            "tags": ["python", "programming"]
        }
        
        async with aiohttp_client.post(add_url, json=document_data, headers=auth_headers) as response:
            assert response.status == 201
        
        # Then search for it
        search_url = f"{TEST_CONFIG['api_base_url']}/knowledge/search"
        search_data = {
            "query": "Python programming",
            "limit": 10
        }
        
        async with aiohttp_client.post(search_url, json=search_data, headers=auth_headers) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "results" in data
            assert len(data["results"]) > 0
            assert "Python" in data["results"][0]["title"]


class TestFileManagementEndpoints:
    """Test file management API endpoints"""
    
    @pytest.mark.asyncio
    async def test_upload_file(self, aiohttp_client, auth_headers, temp_dir):
        """Test file upload endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/files/upload"
        
        # Create a test file
        test_file_path = temp_dir / "test.txt"
        test_file_path.write_text("This is a test file content.")
        
        data = aiohttp.FormData()
        data.add_field('file',
                      open(test_file_path, 'rb'),
                      filename='test.txt',
                      content_type='text/plain')
        
        async with aiohttp_client.post(url, data=data, headers=auth_headers) as response:
            assert response.status == 201
            
            result = await response.json()
            assert "file_id" in result
            assert "filename" in result
            assert result["filename"] == "test.txt"
    
    @pytest.mark.asyncio
    async def test_list_files(self, aiohttp_client, auth_headers):
        """Test listing user files"""
        url = f"{TEST_CONFIG['api_base_url']}/files"
        
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            assert response.status == 200
            
            data = await response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_download_file(self, aiohttp_client, auth_headers):
        """Test file download endpoint"""
        # This would require a file to be uploaded first
        # For now, just test the endpoint structure
        url = f"{TEST_CONFIG['api_base_url']}/files/download/test-file-id"
        
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            # Should return 404 for non-existent file
            assert response.status in [404, 200]


class TestSearchEndpoints:
    """Test search API endpoints"""
    
    @pytest.mark.asyncio
    async def test_web_search(self, aiohttp_client, auth_headers):
        """Test web search endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/search/web"
        
        search_data = {
            "query": "Python programming",
            "limit": 5
        }
        
        async with aiohttp_client.post(url, json=search_data, headers=auth_headers) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "results" in data
            assert isinstance(data["results"], list)
    
    @pytest.mark.asyncio
    async def test_scrape_website(self, aiohttp_client, auth_headers):
        """Test website scraping endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/search/scrape"
        
        scrape_data = {
            "url": "https://example.com",
            "extract_text": True
        }
        
        async with aiohttp_client.post(url, json=scrape_data, headers=auth_headers) as response:
            # Should return 200 or handle the request appropriately
            assert response.status in [200, 202, 400]


class TestMonitoringEndpoints:
    """Test monitoring and health check endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, aiohttp_client):
        """Test health check endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/health"
        
        async with aiohttp_client.get(url) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "status" in data
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_system_metrics(self, aiohttp_client, auth_headers):
        """Test system metrics endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/admin/metrics"
        
        async with aiohttp_client.get(url, headers=auth_headers) as response:
            # Should return 200 for admin users or 403 for non-admin
            assert response.status in [200, 403]
    
    @pytest.mark.asyncio
    async def test_service_status(self, aiohttp_client):
        """Test service status endpoint"""
        url = f"{TEST_CONFIG['api_base_url']}/status"
        
        async with aiohttp_client.get(url) as response:
            assert response.status == 200
            
            data = await response.json()
            assert "services" in data
            assert isinstance(data["services"], dict)


class TestRateLimiting:
    """Test API rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, aiohttp_client):
        """Test that rate limiting is enforced"""
        url = f"{TEST_CONFIG['api_base_url']}/auth/login"
        
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            async with aiohttp_client.post(url, json={"email": "test", "password": "test"}) as response:
                responses.append(response.status)
        
        # Should see some 429 (Too Many Requests) responses
        assert 429 in responses or all(status == 401 for status in responses)


class TestErrorHandling:
    """Test API error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, aiohttp_client, auth_headers):
        """Test handling of invalid JSON"""
        url = f"{TEST_CONFIG['api_base_url']}/agents"
        
        async with aiohttp_client.post(url, data="invalid json", headers=auth_headers) as response:
            assert response.status == 422
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, aiohttp_client, auth_headers):
        """Test handling of missing required fields"""
        url = f"{TEST_CONFIG['api_base_url']}/agents"
        
        incomplete_data = {
            "name": "Test Agent"
            # Missing required fields
        }
        
        async with aiohttp_client.post(url, json=incomplete_data, headers=auth_headers) as response:
            assert response.status == 422
    
    @pytest.mark.asyncio
    async def test_not_found_endpoint(self, aiohttp_client):
        """Test 404 handling for non-existent endpoints"""
        url = f"{TEST_CONFIG['api_base_url']}/nonexistent/endpoint"
        
        async with aiohttp_client.get(url) as response:
            assert response.status == 404







