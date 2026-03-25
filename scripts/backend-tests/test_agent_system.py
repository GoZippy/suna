import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

class TestAgentSystem:
    """Test suite for agent system functionality."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization."""
        from agent.run import AgentConfig, ToolManager
        
        config = AgentConfig(
            thread_id="test-thread",
            project_id="test-project",
            stream=True
        )
        
        assert config.thread_id == "test-thread"
        assert config.project_id == "test-project"
        assert config.stream is True

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test tool registration in agent system."""
        from agent.run import ToolManager
        from agentpress.thread_manager import ThreadManager
        
        # Mock thread manager
        mock_thread_manager = MagicMock()
        mock_thread_manager.add_tool = AsyncMock()
        
        tool_manager = ToolManager(mock_thread_manager, "test-project", "test-thread")
        
        # Test tool registration
        tool_manager.register_all_tools()
        
        # Verify tools were registered
        assert mock_thread_manager.add_tool.called

    @pytest.mark.asyncio
    async def test_agent_execution(self):
        """Test agent execution flow."""
        from agent.run import run_agent
        
        # Mock dependencies
        with patch('agent.run.ThreadManager') as mock_thread_manager_class:
            mock_thread_manager = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager
            
            # Mock agent execution
            mock_thread_manager.run_agent = AsyncMock(return_value="Test response")
            
            config = MagicMock()
            config.thread_id = "test-thread"
            config.project_id = "test-project"
            config.stream = False
            
            # Test agent execution
            result = await run_agent(config)
            
            assert result is not None
            assert mock_thread_manager.run_agent.called

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Test individual tool execution."""
        from agent.tools.sb_files_tool import SandboxFilesTool
        
        # Mock tool dependencies
        with patch('agent.tools.sb_files_tool.SandboxToolsBase') as mock_base:
            mock_base.return_value = None
            
            # Create tool instance
            tool = SandboxFilesTool("test-project", "test-thread", MagicMock())
            
            # Test tool methods exist
            assert hasattr(tool, 'list_files')
            assert hasattr(tool, 'read_file')
            assert hasattr(tool, 'write_file')

    @pytest.mark.asyncio
    async def test_browser_tool(self):
        """Test browser automation tool."""
        from agent.tools.sb_browser_tool import SandboxBrowserTool
        
        # Mock dependencies
        with patch('agent.tools.sb_browser_tool.SandboxToolsBase') as mock_base:
            mock_base.return_value = None
            
            tool = SandboxBrowserTool("test-project", "test-thread", MagicMock())
            
            # Test browser tool methods
            assert hasattr(tool, 'navigate_to')
            assert hasattr(tool, 'click_element')
            assert hasattr(tool, 'type_text')
            assert hasattr(tool, 'screenshot')

    @pytest.mark.asyncio
    async def test_file_operations(self):
        """Test file system operations."""
        from agent.tools.sb_files_tool import SandboxFilesTool
        
        # Mock file operations
        with patch('agent.tools.sb_files_tool.SandboxToolsBase') as mock_base:
            mock_base.return_value = None
            
            tool = SandboxFilesTool("test-project", "test-thread", MagicMock())
            
            # Test file operation methods
            assert hasattr(tool, 'list_files')
            assert hasattr(tool, 'read_file')
            assert hasattr(tool, 'write_file')
            assert hasattr(tool, 'delete_file')
            assert hasattr(tool, 'create_directory')

    @pytest.mark.asyncio
    async def test_web_search_tool(self):
        """Test web search functionality."""
        from agent.tools.web_search_tool import SandboxWebSearchTool
        
        # Mock search dependencies
        with patch('agent.tools.web_search_tool.SandboxToolsBase') as mock_base:
            mock_base.return_value = None
            
            tool = SandboxWebSearchTool("test-project", "test-thread", MagicMock())
            
            # Test search methods
            assert hasattr(tool, 'search_web')
            assert hasattr(tool, 'search_news')
            assert hasattr(tool, 'search_images')

    @pytest.mark.asyncio
    async def test_agent_configuration(self):
        """Test agent configuration management."""
        from agent.run import AgentConfig
        
        # Test default configuration
        config = AgentConfig(
            thread_id="test-thread",
            project_id="test-project",
            stream=True
        )
        
        assert config.native_max_auto_continues == 25
        assert config.max_iterations == 100
        assert config.model_name == "openrouter/moonshotai/kimi-k2"
        assert config.enable_thinking is False
        assert config.reasoning_effort == 'low'
        assert config.enable_context_manager is True

    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        """Test agent error handling."""
        from agent.run import run_agent
        
        # Mock dependencies with error
        with patch('agent.run.ThreadManager') as mock_thread_manager_class:
            mock_thread_manager = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager
            
            # Mock agent execution with error
            mock_thread_manager.run_agent = AsyncMock(side_effect=Exception("Test error"))
            
            config = MagicMock()
            config.thread_id = "test-thread"
            config.project_id = "test-project"
            config.stream = False
            
            # Test error handling
            with pytest.raises(Exception):
                await run_agent(config)

    @pytest.mark.asyncio
    async def test_tool_validation(self):
        """Test tool input validation."""
        from agent.tools.sb_browser_tool import SandboxBrowserTool
        
        # Mock dependencies
        with patch('agent.tools.sb_browser_tool.SandboxToolsBase') as mock_base:
            mock_base.return_value = None
            
            tool = SandboxBrowserTool("test-project", "test-thread", MagicMock())
            
            # Test image validation
            is_valid, message = tool._validate_base64_image("invalid_base64")
            assert is_valid is False
            assert "Invalid base64" in message

    @pytest.mark.asyncio
    async def test_agent_streaming(self):
        """Test agent streaming functionality."""
        from agent.run import run_agent
        
        # Mock streaming dependencies
        with patch('agent.run.ThreadManager') as mock_thread_manager_class:
            mock_thread_manager = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager
            
            # Mock streaming response
            async def mock_stream():
                yield "Test"
                yield " response"
                yield " stream"
            
            mock_thread_manager.run_agent = mock_stream
            
            config = MagicMock()
            config.thread_id = "test-thread"
            config.project_id = "test-project"
            config.stream = True
            
            # Test streaming
            result = await run_agent(config)
            assert result is not None

    @pytest.mark.asyncio
    async def test_agent_timeout(self):
        """Test agent timeout handling."""
        from agent.run import run_agent
        
        # Mock dependencies with timeout
        with patch('agent.run.ThreadManager') as mock_thread_manager_class:
            mock_thread_manager = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager
            
            # Mock slow execution
            async def slow_execution():
                await asyncio.sleep(2)  # Simulate slow execution
                return "Slow response"
            
            mock_thread_manager.run_agent = slow_execution
            
            config = MagicMock()
            config.thread_id = "test-thread"
            config.project_id = "test-project"
            config.stream = False
            
            # Test timeout handling
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(run_agent(config), timeout=1.0)

    @pytest.mark.asyncio
    async def test_agent_memory_management(self):
        """Test agent memory management."""
        from agent.run import run_agent
        
        # Mock dependencies
        with patch('agent.run.ThreadManager') as mock_thread_manager_class:
            mock_thread_manager = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager
            
            # Mock memory cleanup
            mock_thread_manager.cleanup = AsyncMock()
            mock_thread_manager.run_agent = AsyncMock(return_value="Test response")
            
            config = MagicMock()
            config.thread_id = "test-thread"
            config.project_id = "test-project"
            config.stream = False
            
            # Test memory cleanup
            result = await run_agent(config)
            
            assert mock_thread_manager.cleanup.called
            assert result is not None







