"""
End-to-end tests for complete user workflows
"""

import pytest
import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any
from unittest.mock import patch, AsyncMock

from tests import TEST_CONFIG


class TestUserRegistrationWorkflow:
    """Test complete user registration and onboarding workflow"""
    
    @pytest.mark.e2e
    async def test_user_registration_to_first_agent(self, aiohttp_client, clean_database):
        """Test complete workflow from user registration to creating first agent"""
        
        # Step 1: User Registration
        register_url = f"{TEST_CONFIG['api_base_url']}/auth/register"
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "username": "newuser",
            "full_name": "New User"
        }
        
        async with aiohttp_client.post(register_url, json=user_data) as response:
            assert response.status == 201
            register_data = await response.json()
            assert "access_token" in register_data
            assert "user" in register_data
            
            user_id = register_data["user"]["id"]
            auth_token = register_data["access_token"]
            auth_headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Step 2: User Profile Verification
        profile_url = f"{TEST_CONFIG['api_base_url']}/users/me"
        async with aiohttp_client.get(profile_url, headers=auth_headers) as response:
            assert response.status == 200
            profile_data = await response.json()
            assert profile_data["email"] == user_data["email"]
            assert profile_data["username"] == user_data["username"]
        
        # Step 3: Create First Agent
        agent_url = f"{TEST_CONFIG['api_base_url']}/agents"
        agent_data = {
            "name": "My First Agent",
            "description": "An AI agent to help me with tasks",
            "config": {
                "model": "llama2:7b",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
        
        async with aiohttp_client.post(agent_url, json=agent_data, headers=auth_headers) as response:
            assert response.status == 201
            agent_response = await response.json()
            assert "id" in agent_response
            assert agent_response["name"] == agent_data["name"]
            
            agent_id = agent_response["id"]
        
        # Step 4: Verify Agent Creation
        agent_detail_url = f"{TEST_CONFIG['api_base_url']}/agents/{agent_id}"
        async with aiohttp_client.get(agent_detail_url, headers=auth_headers) as response:
            assert response.status == 200
            agent_detail = await response.json()
            assert agent_detail["id"] == agent_id
            assert agent_detail["user_id"] == user_id
        
        # Step 5: List User's Agents
        agents_list_url = f"{TEST_CONFIG['api_base_url']}/agents"
        async with aiohttp_client.get(agents_list_url, headers=auth_headers) as response:
            assert response.status == 200
            agents_list = await response.json()
            assert len(agents_list) == 1
            assert agents_list[0]["id"] == agent_id
        
        print("✅ User registration to first agent workflow completed successfully")
    
    @pytest.mark.e2e
    async def test_user_onboarding_flow(self, aiohttp_client, clean_database):
        """Test complete user onboarding flow including profile setup"""
        
        # Step 1: Register user
        register_url = f"{TEST_CONFIG['api_base_url']}/auth/register"
        user_data = {
            "email": "onboard@example.com",
            "password": "SecurePassword123!",
            "username": "onboarduser",
            "full_name": "Onboard User"
        }
        
        async with aiohttp_client.post(register_url, json=user_data) as response:
            assert response.status == 201
            register_data = await response.json()
            auth_headers = {"Authorization": f"Bearer {register_data['access_token']}"}
        
        # Step 2: Update user profile
        profile_update_url = f"{TEST_CONFIG['api_base_url']}/users/me"
        profile_update = {
            "full_name": "Updated Onboard User",
            "bio": "I'm a new user learning about AI agents"
        }
        
        async with aiohttp_client.put(profile_update_url, json=profile_update, headers=auth_headers) as response:
            assert response.status == 200
            updated_profile = await response.json()
            assert updated_profile["full_name"] == profile_update["full_name"]
        
        # Step 3: Add knowledge base document
        kb_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents"
        document_data = {
            "title": "Getting Started Guide",
            "content": "This is a guide to help new users get started with AI agents.",
            "source": "user_upload",
            "tags": ["guide", "getting-started"]
        }
        
        async with aiohttp_client.post(kb_url, json=document_data, headers=auth_headers) as response:
            assert response.status == 201
            doc_response = await response.json()
            assert "id" in doc_response
            doc_id = doc_response["id"]
        
        # Step 4: Search knowledge base
        search_url = f"{TEST_CONFIG['api_base_url']}/knowledge/search"
        search_data = {"query": "getting started", "limit": 5}
        
        async with aiohttp_client.post(search_url, json=search_data, headers=auth_headers) as response:
            assert response.status == 200
            search_results = await response.json()
            assert "results" in search_results
            assert len(search_results["results"]) > 0
        
        print("✅ User onboarding flow completed successfully")


class TestAgentWorkflowExecution:
    """Test complete agent workflow execution"""
    
    @pytest.mark.e2e
    async def test_agent_workflow_creation_and_execution(self, aiohttp_client, auth_headers, test_agent, clean_database):
        """Test creating and executing a complete agent workflow"""
        
        # Step 1: Create a workflow
        workflow_url = f"{TEST_CONFIG['api_base_url']}/workflows"
        workflow_data = {
            "name": "Research Workflow",
            "description": "A workflow to research a topic and generate a summary",
            "agent_id": test_agent["id"],
            "steps": [
                {
                    "step": 1,
                    "action": "search",
                    "params": {"query": "artificial intelligence trends 2024"}
                },
                {
                    "step": 2,
                    "action": "analyze",
                    "params": {"analysis_type": "summary", "max_length": 500}
                },
                {
                    "step": 3,
                    "action": "save",
                    "params": {"format": "markdown", "filename": "ai_trends_summary"}
                }
            ]
        }
        
        async with aiohttp_client.post(workflow_url, json=workflow_data, headers=auth_headers) as response:
            assert response.status == 201
            workflow_response = await response.json()
            assert "id" in workflow_response
            workflow_id = workflow_response["id"]
        
        # Step 2: Execute the workflow
        execution_url = f"{TEST_CONFIG['api_base_url']}/workflows/{workflow_id}/execute"
        execution_data = {
            "input": "Research the latest trends in artificial intelligence for 2024"
        }
        
        async with aiohttp_client.post(execution_url, json=execution_data, headers=auth_headers) as response:
            assert response.status == 202  # Accepted for async execution
            execution_response = await response.json()
            assert "execution_id" in execution_response
            execution_id = execution_response["execution_id"]
        
        # Step 3: Check execution status
        status_url = f"{TEST_CONFIG['api_base_url']}/workflows/executions/{execution_id}/status"
        
        # Poll for completion (with timeout)
        max_attempts = 10
        for attempt in range(max_attempts):
            async with aiohttp_client.get(status_url, headers=auth_headers) as response:
                assert response.status == 200
                status_data = await response.json()
                
                if status_data["status"] in ["completed", "failed"]:
                    break
                
                await asyncio.sleep(2)  # Wait 2 seconds before next check
        
        # Step 4: Get execution results
        results_url = f"{TEST_CONFIG['api_base_url']}/workflows/executions/{execution_id}/results"
        async with aiohttp_client.get(results_url, headers=auth_headers) as response:
            assert response.status == 200
            results_data = await response.json()
            assert "results" in results_data
            assert "output" in results_data
        
        print("✅ Agent workflow creation and execution completed successfully")
    
    @pytest.mark.e2e
    async def test_agent_interaction_workflow(self, aiohttp_client, auth_headers, test_agent, clean_database):
        """Test complete agent interaction workflow"""
        
        # Step 1: Start a conversation with the agent
        conversation_url = f"{TEST_CONFIG['api_base_url']}/agents/{test_agent['id']}/conversations"
        conversation_data = {
            "title": "AI Discussion",
            "initial_message": "Hello! Can you help me understand machine learning?"
        }
        
        async with aiohttp_client.post(conversation_url, json=conversation_data, headers=auth_headers) as response:
            assert response.status == 201
            conversation_response = await response.json()
            assert "id" in conversation_response
            conversation_id = conversation_response["id"]
        
        # Step 2: Send a message to the agent
        message_url = f"{TEST_CONFIG['api_base_url']}/conversations/{conversation_id}/messages"
        message_data = {
            "content": "What are the main types of machine learning algorithms?",
            "type": "user"
        }
        
        async with aiohttp_client.post(message_url, json=message_data, headers=auth_headers) as response:
            assert response.status == 201
            message_response = await response.json()
            assert "id" in message_response
        
        # Step 3: Get agent response
        # This would typically be async, so we check for the response
        messages_url = f"{TEST_CONFIG['api_base_url']}/conversations/{conversation_id}/messages"
        async with aiohttp_client.get(messages_url, headers=auth_headers) as response:
            assert response.status == 200
            messages_data = await response.json()
            assert len(messages_data) >= 2  # Initial message + user message
        
        # Step 4: Continue conversation
        follow_up_data = {
            "content": "Can you explain supervised learning in more detail?",
            "type": "user"
        }
        
        async with aiohttp_client.post(message_url, json=follow_up_data, headers=auth_headers) as response:
            assert response.status == 201
        
        print("✅ Agent interaction workflow completed successfully")


class TestFileManagementWorkflow:
    """Test complete file management workflow"""
    
    @pytest.mark.e2e
    async def test_file_upload_and_processing_workflow(self, aiohttp_client, auth_headers, temp_dir):
        """Test complete file upload and processing workflow"""
        
        # Step 1: Create a test file
        test_file_path = temp_dir / "test_document.txt"
        test_content = """
        This is a test document for AI processing.
        It contains information about artificial intelligence and machine learning.
        The document will be processed by the AI agent to extract insights.
        """
        test_file_path.write_text(test_content)
        
        # Step 2: Upload the file
        upload_url = f"{TEST_CONFIG['api_base_url']}/files/upload"
        
        data = aiohttp.FormData()
        data.add_field('file',
                      open(test_file_path, 'rb'),
                      filename='test_document.txt',
                      content_type='text/plain')
        
        async with aiohttp_client.post(upload_url, data=data, headers=auth_headers) as response:
            assert response.status == 201
            upload_response = await response.json()
            assert "file_id" in upload_response
            file_id = upload_response["file_id"]
        
        # Step 3: Process the file with AI
        process_url = f"{TEST_CONFIG['api_base_url']}/files/{file_id}/process"
        process_data = {
            "action": "analyze",
            "params": {
                "analysis_type": "summary",
                "extract_keywords": True,
                "generate_insights": True
            }
        }
        
        async with aiohttp_client.post(process_url, json=process_data, headers=auth_headers) as response:
            assert response.status == 202  # Accepted for processing
            process_response = await response.json()
            assert "task_id" in process_response
            task_id = process_response["task_id"]
        
        # Step 4: Check processing status
        status_url = f"{TEST_CONFIG['api_base_url']}/files/processing/{task_id}/status"
        
        # Poll for completion
        max_attempts = 10
        for attempt in range(max_attempts):
            async with aiohttp_client.get(status_url, headers=auth_headers) as response:
                assert response.status == 200
                status_data = await response.json()
                
                if status_data["status"] in ["completed", "failed"]:
                    break
                
                await asyncio.sleep(2)
        
        # Step 5: Get processing results
        results_url = f"{TEST_CONFIG['api_base_url']}/files/processing/{task_id}/results"
        async with aiohttp_client.get(results_url, headers=auth_headers) as response:
            assert response.status == 200
            results_data = await response.json()
            assert "results" in results_data
        
        # Step 6: List user files
        files_url = f"{TEST_CONFIG['api_base_url']}/files"
        async with aiohttp_client.get(files_url, headers=auth_headers) as response:
            assert response.status == 200
            files_data = await response.json()
            assert len(files_data) > 0
            assert any(f["file_id"] == file_id for f in files_data)
        
        print("✅ File upload and processing workflow completed successfully")


class TestKnowledgeBaseWorkflow:
    """Test complete knowledge base workflow"""
    
    @pytest.mark.e2e
    async def test_knowledge_base_management_workflow(self, aiohttp_client, auth_headers, clean_database):
        """Test complete knowledge base management workflow"""
        
        # Step 1: Add multiple documents to knowledge base
        kb_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents"
        
        documents = [
            {
                "title": "Python Programming Guide",
                "content": "Python is a high-level programming language known for its simplicity and readability.",
                "source": "manual",
                "tags": ["python", "programming", "guide"]
            },
            {
                "title": "Machine Learning Basics",
                "content": "Machine learning is a subset of artificial intelligence that enables computers to learn without being explicitly programmed.",
                "source": "manual",
                "tags": ["machine-learning", "ai", "basics"]
            },
            {
                "title": "Data Science Workflow",
                "content": "The data science workflow includes data collection, cleaning, analysis, and visualization.",
                "source": "manual",
                "tags": ["data-science", "workflow", "analysis"]
            }
        ]
        
        document_ids = []
        for doc in documents:
            async with aiohttp_client.post(kb_url, json=doc, headers=auth_headers) as response:
                assert response.status == 201
                doc_response = await response.json()
                document_ids.append(doc_response["id"])
        
        # Step 2: Search knowledge base
        search_url = f"{TEST_CONFIG['api_base_url']}/knowledge/search"
        search_data = {"query": "programming", "limit": 10}
        
        async with aiohttp_client.post(search_url, json=search_data, headers=auth_headers) as response:
            assert response.status == 200
            search_results = await response.json()
            assert "results" in search_results
            assert len(search_results["results"]) > 0
        
        # Step 3: Update a document
        update_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents/{document_ids[0]}"
        update_data = {
            "title": "Updated Python Programming Guide",
            "content": "Python is a high-level programming language known for its simplicity, readability, and extensive library ecosystem.",
            "tags": ["python", "programming", "guide", "updated"]
        }
        
        async with aiohttp_client.put(update_url, json=update_data, headers=auth_headers) as response:
            assert response.status == 200
            updated_doc = await response.json()
            assert updated_doc["title"] == update_data["title"]
        
        # Step 4: Get document by ID
        doc_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents/{document_ids[0]}"
        async with aiohttp_client.get(doc_url, headers=auth_headers) as response:
            assert response.status == 200
            doc_data = await response.json()
            assert doc_data["id"] == document_ids[0]
            assert doc_data["title"] == update_data["title"]
        
        # Step 5: List all documents
        list_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents"
        async with aiohttp_client.get(list_url, headers=auth_headers) as response:
            assert response.status == 200
            list_data = await response.json()
            assert len(list_data) >= 3
        
        # Step 6: Delete a document
        delete_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents/{document_ids[2]}"
        async with aiohttp_client.delete(delete_url, headers=auth_headers) as response:
            assert response.status == 204
        
        # Step 7: Verify deletion
        async with aiohttp_client.get(list_url, headers=auth_headers) as response:
            assert response.status == 200
            list_data = await response.json()
            assert len(list_data) == 2  # One document deleted
        
        print("✅ Knowledge base management workflow completed successfully")


class TestSearchAndAnalysisWorkflow:
    """Test complete search and analysis workflow"""
    
    @pytest.mark.e2e
    async def test_web_search_and_analysis_workflow(self, aiohttp_client, auth_headers):
        """Test complete web search and analysis workflow"""
        
        # Step 1: Perform web search
        search_url = f"{TEST_CONFIG['api_base_url']}/search/web"
        search_data = {
            "query": "latest developments in artificial intelligence 2024",
            "limit": 5
        }
        
        async with aiohttp_client.post(search_url, json=search_data, headers=auth_headers) as response:
            assert response.status == 200
            search_response = await response.json()
            assert "results" in search_response
            assert len(search_response["results"]) > 0
        
        # Step 2: Scrape a specific website
        scrape_url = f"{TEST_CONFIG['api_base_url']}/search/scrape"
        scrape_data = {
            "url": "https://example.com",
            "extract_text": True,
            "extract_links": True
        }
        
        async with aiohttp_client.post(scrape_url, json=scrape_data, headers=auth_headers) as response:
            # Should return 200 or handle appropriately
            assert response.status in [200, 202, 400]
        
        # Step 3: Analyze search results
        analysis_url = f"{TEST_CONFIG['api_base_url']}/search/analyze"
        analysis_data = {
            "query": "AI trends analysis",
            "results": search_response["results"],
            "analysis_type": "trends",
            "max_length": 1000
        }
        
        async with aiohttp_client.post(analysis_url, json=analysis_data, headers=auth_headers) as response:
            assert response.status == 200
            analysis_response = await response.json()
            assert "analysis" in analysis_response
        
        print("✅ Web search and analysis workflow completed successfully")


class TestSystemIntegrationWorkflow:
    """Test complete system integration workflows"""
    
    @pytest.mark.e2e
    async def test_complete_user_journey(self, aiohttp_client, clean_database):
        """Test a complete user journey from registration to advanced usage"""
        
        # Step 1: User Registration
        register_url = f"{TEST_CONFIG['api_base_url']}/auth/register"
        user_data = {
            "email": "journey@example.com",
            "password": "SecurePassword123!",
            "username": "journeyuser",
            "full_name": "Journey User"
        }
        
        async with aiohttp_client.post(register_url, json=user_data) as response:
            assert response.status == 201
            register_data = await response.json()
            auth_headers = {"Authorization": f"Bearer {register_data['access_token']}"}
        
        # Step 2: Create an agent
        agent_url = f"{TEST_CONFIG['api_base_url']}/agents"
        agent_data = {
            "name": "Research Assistant",
            "description": "An AI assistant for research and analysis",
            "config": {
                "model": "llama2:7b",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }
        
        async with aiohttp_client.post(agent_url, json=agent_data, headers=auth_headers) as response:
            assert response.status == 201
            agent_response = await response.json()
            agent_id = agent_response["id"]
        
        # Step 3: Add knowledge base documents
        kb_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents"
        doc_data = {
            "title": "Research Guidelines",
            "content": "Guidelines for conducting effective research using AI tools.",
            "source": "manual",
            "tags": ["research", "guidelines", "ai"]
        }
        
        async with aiohttp_client.post(kb_url, json=doc_data, headers=auth_headers) as response:
            assert response.status == 201
            doc_response = await response.json()
            doc_id = doc_response["id"]
        
        # Step 4: Create a workflow
        workflow_url = f"{TEST_CONFIG['api_base_url']}/workflows"
        workflow_data = {
            "name": "Research Workflow",
            "description": "Complete research workflow",
            "agent_id": agent_id,
            "steps": [
                {
                    "step": 1,
                    "action": "search",
                    "params": {"query": "AI research methodology"}
                },
                {
                    "step": 2,
                    "action": "analyze",
                    "params": {"analysis_type": "comprehensive"}
                }
            ]
        }
        
        async with aiohttp_client.post(workflow_url, json=workflow_data, headers=auth_headers) as response:
            assert response.status == 201
            workflow_response = await response.json()
            workflow_id = workflow_response["id"]
        
        # Step 5: Execute workflow
        execution_url = f"{TEST_CONFIG['api_base_url']}/workflows/{workflow_id}/execute"
        execution_data = {"input": "Research AI methodology"}
        
        async with aiohttp_client.post(execution_url, json=execution_data, headers=auth_headers) as response:
            assert response.status == 202
            execution_response = await response.json()
            execution_id = execution_response["execution_id"]
        
        # Step 6: Check system status
        status_url = f"{TEST_CONFIG['api_base_url']}/status"
        async with aiohttp_client.get(status_url) as response:
            assert response.status == 200
            status_data = await response.json()
            assert "services" in status_data
        
        # Step 7: Get user dashboard data
        dashboard_url = f"{TEST_CONFIG['api_base_url']}/users/dashboard"
        async with aiohttp_client.get(dashboard_url, headers=auth_headers) as response:
            assert response.status == 200
            dashboard_data = await response.json()
            assert "agents_count" in dashboard_data
            assert "workflows_count" in dashboard_data
            assert "documents_count" in dashboard_data
        
        print("✅ Complete user journey workflow completed successfully")
    
    @pytest.mark.e2e
    async def test_multi_user_collaboration_workflow(self, aiohttp_client, clean_database):
        """Test multi-user collaboration workflow"""
        
        # Create multiple users
        users = []
        auth_headers_list = []
        
        for i in range(2):
            register_url = f"{TEST_CONFIG['api_base_url']}/auth/register"
            user_data = {
                "email": f"collab{i}@example.com",
                "password": "SecurePassword123!",
                "username": f"collabuser{i}",
                "full_name": f"Collaboration User {i}"
            }
            
            async with aiohttp_client.post(register_url, json=user_data) as response:
                assert response.status == 201
                register_data = await response.json()
                users.append(register_data["user"])
                auth_headers_list.append({"Authorization": f"Bearer {register_data['access_token']}"})
        
        # User 1 creates a shared resource
        kb_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents"
        shared_doc = {
            "title": "Shared Research Document",
            "content": "This is a document that will be shared between users.",
            "source": "manual",
            "tags": ["shared", "research"],
            "is_public": True
        }
        
        async with aiohttp_client.post(kb_url, json=shared_doc, headers=auth_headers_list[0]) as response:
            assert response.status == 201
            shared_doc_response = await response.json()
            shared_doc_id = shared_doc_response["id"]
        
        # User 2 accesses the shared resource
        shared_doc_url = f"{TEST_CONFIG['api_base_url']}/knowledge/documents/{shared_doc_id}"
        async with aiohttp_client.get(shared_doc_url, headers=auth_headers_list[1]) as response:
            assert response.status == 200
            accessed_doc = await response.json()
            assert accessed_doc["id"] == shared_doc_id
        
        print("✅ Multi-user collaboration workflow completed successfully")







