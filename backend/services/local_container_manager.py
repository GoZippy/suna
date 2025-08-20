"""
Local Container Orchestration System

This module provides Docker-based sandbox management to replace Daytona functionality.
It implements container lifecycle management, secure isolation, VNC server integration,
file system operations, and health monitoring.
"""

import asyncio
import docker
import json
import logging
import os
import shutil
import tempfile
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from utils.logger import logger
from utils.config import config


class ContainerState(Enum):
    """Container state enumeration"""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DELETED = "deleted"


@dataclass
class ContainerInfo:
    """Container information data class"""
    container_id: str
    name: str
    state: ContainerState
    created_at: datetime
    vnc_port: int
    http_port: int
    project_id: Optional[str] = None
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"
    resource_limits: Optional[Dict[str, Any]] = None


@dataclass
class ContainerResources:
    """Container resource limits"""
    cpu_limit: float = 2.0  # CPU cores
    memory_limit: str = "4g"  # Memory limit
    disk_limit: str = "10g"  # Disk limit
    shm_size: str = "2g"  # Shared memory


class LocalContainerManager:
    """
    Local Docker-based container orchestration system.
    
    Provides secure container isolation, lifecycle management, VNC access,
    file operations, and health monitoring for agent sandboxes.
    """
    
    def __init__(self):
        """Initialize the container manager"""
        self.docker_client = None
        self.containers: Dict[str, ContainerInfo] = {}
        self.port_manager = PortManager()
        self.network_name = "suna_sandbox_network"
        self.base_image = "suna/agent-sandbox:latest"
        self.container_prefix = "suna_sandbox_"
        self.health_check_interval = 30  # seconds
        self.auto_cleanup_interval = 3600  # 1 hour
        self._health_check_task = None
        self._cleanup_task = None
        
        # Initialize Docker client
        self._init_docker_client()
        
        # Create isolated network
        self._ensure_network()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _init_docker_client(self):
        """Initialize Docker client with error handling"""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise RuntimeError(f"Docker is not available: {e}")
    
    def _ensure_network(self):
        """Ensure the sandbox network exists"""
        try:
            # Check if network exists
            networks = self.docker_client.networks.list(names=[self.network_name])
            if not networks:
                # Create isolated network for sandboxes
                network = self.docker_client.networks.create(
                    name=self.network_name,
                    driver="bridge",
                    options={
                        "com.docker.network.bridge.enable_icc": "false",  # Disable inter-container communication
                        "com.docker.network.bridge.enable_ip_masquerade": "true"
                    },
                    labels={"managed_by": "suna_container_manager"}
                )
                logger.info(f"Created sandbox network: {self.network_name}")
            else:
                logger.debug(f"Sandbox network already exists: {self.network_name}")
        except Exception as e:
            logger.error(f"Failed to create sandbox network: {e}")
            raise
    
    def _start_background_tasks(self):
        """Start background monitoring and cleanup tasks"""
        try:
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("Background tasks started successfully")
        except Exception as e:
            logger.error(f"Failed to start background tasks: {e}")
    
    async def create_container(
        self, 
        project_id: str, 
        vnc_password: str = "vncpassword",
        resources: Optional[ContainerResources] = None
    ) -> ContainerInfo:
        """
        Create a new sandbox container with secure isolation.
        
        Args:
            project_id: Unique project identifier
            vnc_password: VNC access password
            resources: Resource limits for the container
            
        Returns:
            ContainerInfo: Information about the created container
        """
        if resources is None:
            resources = ContainerResources()
        
        container_name = f"{self.container_prefix}{project_id}"
        
        # Check if container already exists
        if project_id in self.containers:
            existing_container = self.containers[project_id]
            if existing_container.state == ContainerState.RUNNING:
                logger.info(f"Container for project {project_id} already running")
                return existing_container
        
        try:
            # Allocate ports
            vnc_port = self.port_manager.allocate_port()
            http_port = self.port_manager.allocate_port()
            
            # Create workspace volume
            workspace_volume = f"suna_workspace_{project_id}"
            
            # Container configuration
            container_config = {
                "image": self.base_image,
                "name": container_name,
                "detach": True,
                "network": self.network_name,
                "ports": {
                    "5901/tcp": vnc_port,  # VNC port
                    "6080/tcp": vnc_port + 1,  # noVNC web interface
                    "8080/tcp": http_port,  # HTTP server
                },
                "environment": {
                    "VNC_PASSWORD": vnc_password,
                    "RESOLUTION": "1024x768x24",
                    "RESOLUTION_WIDTH": "1024",
                    "RESOLUTION_HEIGHT": "768",
                    "DISPLAY": ":99",
                    "CHROME_PERSISTENT_SESSION": "true",
                    "ANONYMIZED_TELEMETRY": "false",
                    "PROJECT_ID": project_id,
                },
                "volumes": {
                    workspace_volume: {"bind": "/workspace", "mode": "rw"},
                    "/tmp/.X11-unix": {"bind": "/tmp/.X11-unix", "mode": "rw"}
                },
                "mem_limit": resources.memory_limit,
                "cpu_count": int(resources.cpu_limit),
                "shm_size": resources.shm_size,
                "cap_add": ["SYS_ADMIN"],  # Required for Chrome
                "security_opt": ["seccomp=unconfined"],
                "tmpfs": {"/tmp": ""},
                "restart_policy": {"Name": "unless-stopped"},
                "labels": {
                    "managed_by": "suna_container_manager",
                    "project_id": project_id,
                    "created_at": datetime.now().isoformat()
                }
            }
            
            # Create and start container
            logger.info(f"Creating container for project {project_id}")
            container = self.docker_client.containers.run(**container_config)
            
            # Wait for container to be ready
            await self._wait_for_container_ready(container.id)
            
            # Create container info
            container_info = ContainerInfo(
                container_id=container.id,
                name=container_name,
                state=ContainerState.RUNNING,
                created_at=datetime.now(),
                vnc_port=vnc_port,
                http_port=http_port,
                project_id=project_id,
                resource_limits=resources.__dict__
            )
            
            # Store container info
            self.containers[project_id] = container_info
            
            logger.info(f"Container created successfully for project {project_id}")
            return container_info
            
        except Exception as e:
            logger.error(f"Failed to create container for project {project_id}: {e}")
            # Cleanup on failure
            self.port_manager.release_port(vnc_port)
            self.port_manager.release_port(http_port)
            raise RuntimeError(f"Container creation failed: {e}")
    
    async def start_container(self, project_id: str) -> ContainerInfo:
        """
        Start a stopped container.
        
        Args:
            project_id: Project identifier
            
        Returns:
            ContainerInfo: Updated container information
        """
        if project_id not in self.containers:
            raise ValueError(f"Container for project {project_id} not found")
        
        container_info = self.containers[project_id]
        
        try:
            container = self.docker_client.containers.get(container_info.container_id)
            
            if container.status != "running":
                logger.info(f"Starting container for project {project_id}")
                container.start()
                
                # Wait for container to be ready
                await self._wait_for_container_ready(container.id)
                
                # Update state
                container_info.state = ContainerState.RUNNING
                
            logger.info(f"Container for project {project_id} is running")
            return container_info
            
        except docker.errors.NotFound:
            logger.error(f"Container {container_info.container_id} not found")
            container_info.state = ContainerState.ERROR
            raise RuntimeError(f"Container not found")
        except Exception as e:
            logger.error(f"Failed to start container for project {project_id}: {e}")
            container_info.state = ContainerState.ERROR
            raise RuntimeError(f"Container start failed: {e}")
    
    async def stop_container(self, project_id: str) -> bool:
        """
        Stop a running container.
        
        Args:
            project_id: Project identifier
            
        Returns:
            bool: True if stopped successfully
        """
        if project_id not in self.containers:
            raise ValueError(f"Container for project {project_id} not found")
        
        container_info = self.containers[project_id]
        
        try:
            container = self.docker_client.containers.get(container_info.container_id)
            
            if container.status == "running":
                logger.info(f"Stopping container for project {project_id}")
                container.stop(timeout=30)
            
            # Update state
            container_info.state = ContainerState.STOPPED
            
            logger.info(f"Container for project {project_id} stopped")
            return True
            
        except docker.errors.NotFound:
            logger.error(f"Container {container_info.container_id} not found")
            container_info.state = ContainerState.ERROR
            return False
        except Exception as e:
            logger.error(f"Failed to stop container for project {project_id}: {e}")
            container_info.state = ContainerState.ERROR
            return False
    
    async def delete_container(self, project_id: str) -> bool:
        """
        Delete a container and cleanup resources.
        
        Args:
            project_id: Project identifier
            
        Returns:
            bool: True if deleted successfully
        """
        if project_id not in self.containers:
            logger.warning(f"Container for project {project_id} not found in registry")
            return True
        
        container_info = self.containers[project_id]
        
        try:
            container = self.docker_client.containers.get(container_info.container_id)
            
            # Stop container if running
            if container.status == "running":
                logger.info(f"Stopping container before deletion for project {project_id}")
                container.stop(timeout=30)
            
            # Remove container
            logger.info(f"Deleting container for project {project_id}")
            container.remove(force=True)
            
            # Cleanup resources
            self.port_manager.release_port(container_info.vnc_port)
            self.port_manager.release_port(container_info.http_port)
            
            # Remove workspace volume
            try:
                volume_name = f"suna_workspace_{project_id}"
                volume = self.docker_client.volumes.get(volume_name)
                volume.remove(force=True)
                logger.debug(f"Removed workspace volume: {volume_name}")
            except docker.errors.NotFound:
                logger.debug(f"Workspace volume not found: {volume_name}")
            
            # Remove from registry
            del self.containers[project_id]
            
            logger.info(f"Container for project {project_id} deleted successfully")
            return True
            
        except docker.errors.NotFound:
            logger.warning(f"Container {container_info.container_id} not found, removing from registry")
            del self.containers[project_id]
            return True
        except Exception as e:
            logger.error(f"Failed to delete container for project {project_id}: {e}")
            return False
    
    async def get_container_info(self, project_id: str) -> Optional[ContainerInfo]:
        """
        Get container information.
        
        Args:
            project_id: Project identifier
            
        Returns:
            ContainerInfo or None if not found
        """
        return self.containers.get(project_id)
    
    async def list_containers(self) -> List[ContainerInfo]:
        """
        List all managed containers.
        
        Returns:
            List of ContainerInfo objects
        """
        return list(self.containers.values())
    
    async def _wait_for_container_ready(self, container_id: str, timeout: int = 60):
        """
        Wait for container to be ready by checking health endpoints.
        
        Args:
            container_id: Container ID
            timeout: Timeout in seconds
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container = self.docker_client.containers.get(container_id)
                
                if container.status != "running":
                    await asyncio.sleep(2)
                    continue
                
                # Check if VNC server is ready
                exec_result = container.exec_run("nc -z localhost 5901", detach=False)
                if exec_result.exit_code == 0:
                    logger.debug(f"Container {container_id} is ready")
                    return
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"Waiting for container {container_id} to be ready: {e}")
                await asyncio.sleep(2)
        
        raise TimeoutError(f"Container {container_id} did not become ready within {timeout} seconds")
    
    async def _health_check_loop(self):
        """Background task for container health monitoring"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _perform_health_checks(self):
        """Perform health checks on all containers"""
        for project_id, container_info in list(self.containers.items()):
            try:
                await self._check_container_health(project_id, container_info)
            except Exception as e:
                logger.error(f"Health check failed for container {project_id}: {e}")
    
    async def _check_container_health(self, project_id: str, container_info: ContainerInfo):
        """
        Check health of a specific container.
        
        Args:
            project_id: Project identifier
            container_info: Container information
        """
        try:
            container = self.docker_client.containers.get(container_info.container_id)
            
            # Update container state based on Docker status
            if container.status == "running":
                # Check if VNC server is responsive
                exec_result = container.exec_run("nc -z localhost 5901", detach=False)
                if exec_result.exit_code == 0:
                    container_info.health_status = "healthy"
                    container_info.state = ContainerState.RUNNING
                else:
                    container_info.health_status = "unhealthy"
                    logger.warning(f"Container {project_id} VNC server not responding")
            else:
                container_info.state = ContainerState.STOPPED
                container_info.health_status = "stopped"
            
            container_info.last_health_check = datetime.now()
            
        except docker.errors.NotFound:
            logger.warning(f"Container {container_info.container_id} not found during health check")
            container_info.state = ContainerState.ERROR
            container_info.health_status = "not_found"
        except Exception as e:
            logger.error(f"Health check error for container {project_id}: {e}")
            container_info.health_status = "error"
    
    async def _cleanup_loop(self):
        """Background task for automatic cleanup of old containers"""
        while True:
            try:
                await asyncio.sleep(self.auto_cleanup_interval)
                await self._perform_cleanup()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _perform_cleanup(self):
        """Perform cleanup of old or orphaned containers"""
        cutoff_time = datetime.now() - timedelta(hours=24)  # Cleanup containers older than 24 hours
        
        for project_id, container_info in list(self.containers.items()):
            try:
                # Skip recently created containers
                if container_info.created_at > cutoff_time:
                    continue
                
                # Check if container is still needed (this could be enhanced with database checks)
                if container_info.state in [ContainerState.ERROR, ContainerState.STOPPED]:
                    logger.info(f"Cleaning up old container for project {project_id}")
                    await self.delete_container(project_id)
                    
            except Exception as e:
                logger.error(f"Cleanup error for container {project_id}: {e}")
    
    async def restart_container(self, project_id: str) -> ContainerInfo:
        """
        Restart a container (stop and start).
        
        Args:
            project_id: Project identifier
            
        Returns:
            ContainerInfo: Updated container information
        """
        await self.stop_container(project_id)
        await asyncio.sleep(2)  # Brief pause
        return await self.start_container(project_id)
    
    def get_vnc_url(self, project_id: str) -> Optional[str]:
        """
        Get VNC web interface URL for a container.
        
        Args:
            project_id: Project identifier
            
        Returns:
            VNC URL or None if container not found
        """
        if project_id not in self.containers:
            return None
        
        container_info = self.containers[project_id]
        return f"http://localhost:{container_info.vnc_port + 1}"
    
    def get_http_url(self, project_id: str) -> Optional[str]:
        """
        Get HTTP server URL for a container.
        
        Args:
            project_id: Project identifier
            
        Returns:
            HTTP URL or None if container not found
        """
        if project_id not in self.containers:
            return None
        
        container_info = self.containers[project_id]
        return f"http://localhost:{container_info.http_port}"
    
    async def cleanup(self):
        """Cleanup resources and stop background tasks"""
        logger.info("Cleaning up container manager")
        
        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Stop all containers
        for project_id in list(self.containers.keys()):
            try:
                await self.delete_container(project_id)
            except Exception as e:
                logger.error(f"Error cleaning up container {project_id}: {e}")


class PortManager:
    """
    Manages port allocation for containers to avoid conflicts.
    """
    
    def __init__(self, start_port: int = 15900, end_port: int = 16900):
        """
        Initialize port manager.
        
        Args:
            start_port: Starting port number
            end_port: Ending port number
        """
        self.start_port = start_port
        self.end_port = end_port
        self.allocated_ports = set()
        self.current_port = start_port
    
    def allocate_port(self) -> int:
        """
        Allocate an available port.
        
        Returns:
            int: Allocated port number
            
        Raises:
            RuntimeError: If no ports available
        """
        # Find next available port
        for _ in range(self.end_port - self.start_port):
            if self.current_port not in self.allocated_ports:
                port = self.current_port
                self.allocated_ports.add(port)
                self.current_port = (self.current_port + 1 - self.start_port) % (self.end_port - self.start_port) + self.start_port
                return port
            
            self.current_port = (self.current_port + 1 - self.start_port) % (self.end_port - self.start_port) + self.start_port
        
        raise RuntimeError("No available ports")
    
    def release_port(self, port: int):
        """
        Release an allocated port.
        
        Args:
            port: Port number to release
        """
        self.allocated_ports.discard(port)


# Global container manager instance
container_manager: Optional[LocalContainerManager] = None


def get_container_manager() -> LocalContainerManager:
    """
    Get the global container manager instance.
    
    Returns:
        LocalContainerManager: The container manager instance
    """
    global container_manager
    if container_manager is None:
        container_manager = LocalContainerManager()
    return container_manager


async def initialize_container_manager():
    """Initialize the global container manager"""
    global container_manager
    if container_manager is None:
        container_manager = LocalContainerManager()
        logger.info("Container manager initialized")


async def cleanup_container_manager():
    """Cleanup the global container manager"""
    global container_manager
    if container_manager is not None:
        await container_manager.cleanup()
        container_manager = None
        logger.info("Container manager cleaned up")