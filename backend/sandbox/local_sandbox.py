"""
Local Sandbox Implementation

This module provides a compatibility layer that replaces Daytona functionality
with local Docker-based container management while maintaining the same interface.
"""

import asyncio
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from services.local_container_manager import get_container_manager, ContainerResources
from services.container_filesystem import ContainerFileSystem
from utils.logger import logger
from utils.config import config


@dataclass
class LocalSandboxInfo:
    """Local sandbox information compatible with Daytona interface"""
    id: str
    state: str
    project_id: Optional[str] = None


class LocalSandboxFileSystem:
    """
    File system interface compatible with Daytona SDK.
    Wraps ContainerFileSystem to provide the same API.
    """
    
    def __init__(self, container_fs: ContainerFileSystem):
        self.container_fs = container_fs
    
    async def upload_file(self, content: bytes, path: str) -> bool:
        """Upload file content to the sandbox"""
        return await self.container_fs.upload_file(content, path)
    
    async def download_file(self, path: str) -> bytes:
        """Download file content from the sandbox"""
        return await self.container_fs.download_file(path)
    
    async def list_files(self, path: str = "/workspace"):
        """List files in directory"""
        files = await self.container_fs.list_files(path)
        
        # Convert to Daytona-compatible format
        daytona_files = []
        for file_info in files:
            # Create a simple object with the expected attributes
            file_obj = type('FileInfo', (), {
                'name': file_info.name,
                'is_dir': file_info.is_dir,
                'size': file_info.size,
                'mod_time': file_info.mod_time
            })()
            daytona_files.append(file_obj)
        
        return daytona_files
    
    async def delete_file(self, path: str) -> bool:
        """Delete a file or directory"""
        return await self.container_fs.delete_file(path)


class LocalSandbox:
    """
    Local sandbox implementation that provides Daytona-compatible interface
    using Docker containers managed by LocalContainerManager.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.id = project_id  # Use project_id as sandbox_id for compatibility
        self.state = "unknown"
        self._fs = None
        self._manager = None
    
    @property
    def fs(self) -> LocalSandboxFileSystem:
        """Get file system interface"""
        if self._fs is None:
            raise RuntimeError("Sandbox not initialized. Call get_or_start_sandbox first.")
        return self._fs
    
    async def _initialize(self):
        """Initialize the sandbox with container manager"""
        self._manager = get_container_manager()
        
        # Get container info
        container_info = await self._manager.get_container_info(self.project_id)
        
        if container_info:
            self.state = container_info.state.value
            
            # Initialize file system if container is running
            if container_info.state.value == "running":
                docker_container = self._manager.docker_client.containers.get(container_info.container_id)
                container_fs = ContainerFileSystem(docker_container)
                self._fs = LocalSandboxFileSystem(container_fs)
        else:
            self.state = "not_found"


async def get_or_start_sandbox(sandbox_id: str) -> LocalSandbox:
    """
    Retrieve a sandbox by ID, check its state, and start it if needed.
    
    This function provides compatibility with the existing Daytona interface
    while using local Docker containers.
    
    Args:
        sandbox_id: The sandbox/project ID
        
    Returns:
        LocalSandbox: The sandbox instance
    """
    logger.debug(f"Getting or starting local sandbox with ID: {sandbox_id}")
    
    try:
        # Create sandbox instance
        sandbox = LocalSandbox(sandbox_id)
        
        # Get container manager
        manager = get_container_manager()
        
        # Check if container exists
        container_info = await manager.get_container_info(sandbox_id)
        
        if container_info:
            # Container exists, check if it needs to be started
            if container_info.state.value in ["stopped", "error"]:
                logger.debug(f"Container is in {container_info.state.value} state. Starting...")
                try:
                    container_info = await manager.start_container(sandbox_id)
                    logger.debug(f"Container started successfully")
                except Exception as e:
                    logger.error(f"Error starting container: {e}")
                    raise e
            
            # Initialize sandbox
            await sandbox._initialize()
            
        else:
            # Container doesn't exist, create it
            logger.debug(f"Container not found, creating new one for project {sandbox_id}")
            
            try:
                container_info = await manager.create_container(
                    project_id=sandbox_id,
                    vnc_password="vncpassword"  # Default password
                )
                
                # Initialize sandbox
                await sandbox._initialize()
                
                logger.debug(f"New container created and initialized for project {sandbox_id}")
                
            except Exception as e:
                logger.error(f"Error creating container: {e}")
                raise e
        
        logger.debug(f"Local sandbox {sandbox_id} is ready")
        return sandbox
        
    except Exception as e:
        logger.error(f"Error retrieving or starting local sandbox: {str(e)}")
        raise e


async def create_sandbox(password: str, project_id: str = None) -> LocalSandbox:
    """
    Create a new sandbox with all required services configured and running.
    
    This function provides compatibility with the existing Daytona interface
    while using local Docker containers.
    
    Args:
        password: VNC password for the sandbox
        project_id: Project ID for the sandbox
        
    Returns:
        LocalSandbox: The created sandbox instance
    """
    logger.debug("Creating new local sandbox environment")
    
    if not project_id:
        raise ValueError("project_id is required for local sandbox creation")
    
    try:
        # Get container manager
        manager = get_container_manager()
        
        # Create container with specified password
        container_info = await manager.create_container(
            project_id=project_id,
            vnc_password=password
        )
        
        # Create sandbox instance
        sandbox = LocalSandbox(project_id)
        await sandbox._initialize()
        
        logger.debug(f"Local sandbox environment successfully initialized for project {project_id}")
        return sandbox
        
    except Exception as e:
        logger.error(f"Error creating local sandbox: {str(e)}")
        raise e


async def delete_sandbox(sandbox_id: str) -> bool:
    """
    Delete a sandbox by its ID.
    
    Args:
        sandbox_id: The sandbox/project ID to delete
        
    Returns:
        bool: True if deletion was successful
    """
    logger.debug(f"Deleting local sandbox with ID: {sandbox_id}")
    
    try:
        # Get container manager
        manager = get_container_manager()
        
        # Delete the container
        success = await manager.delete_container(sandbox_id)
        
        if success:
            logger.debug(f"Successfully deleted local sandbox {sandbox_id}")
        else:
            logger.error(f"Failed to delete local sandbox {sandbox_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error deleting local sandbox {sandbox_id}: {str(e)}")
        raise e


# Compatibility functions for existing code
async def start_supervisord_session(sandbox: LocalSandbox):
    """
    Start supervisord in a session (compatibility function).
    
    For local containers, supervisord is already started via the Dockerfile,
    so this is a no-op for compatibility.
    """
    logger.debug(f"Supervisord session start requested for sandbox {sandbox.id} (no-op for local containers)")
    pass


# Export the same interface as the original sandbox module
__all__ = [
    'get_or_start_sandbox',
    'create_sandbox', 
    'delete_sandbox',
    'start_supervisord_session',
    'LocalSandbox',
    'LocalSandboxFileSystem'
]