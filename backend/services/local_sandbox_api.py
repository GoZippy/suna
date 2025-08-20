"""
Local Sandbox API

This module provides FastAPI endpoints for the local container orchestration system,
replacing Daytona functionality with Docker-based sandbox management.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel

from services.local_container_manager import (
    get_container_manager, 
    ContainerInfo, 
    ContainerResources,
    ContainerState
)
from services.container_filesystem import ContainerFileSystem, FileInfo
from utils.logger import logger
from utils.auth_utils import get_optional_user_id
from services.supabase import DBConnection


# Initialize router
router = APIRouter(tags=["local_sandbox"])
db = None


def initialize(_db: DBConnection):
    """Initialize the local sandbox API with resources from the main API."""
    global db
    db = _db
    logger.debug("Initialized local sandbox API with database connection")


# Pydantic models for API requests/responses
class CreateSandboxRequest(BaseModel):
    """Request model for creating a sandbox"""
    project_id: str
    vnc_password: Optional[str] = "vncpassword"
    cpu_limit: Optional[float] = 2.0
    memory_limit: Optional[str] = "4g"
    disk_limit: Optional[str] = "10g"


class SandboxResponse(BaseModel):
    """Response model for sandbox information"""
    container_id: str
    project_id: str
    state: str
    created_at: str
    vnc_port: int
    http_port: int
    vnc_url: str
    http_url: str
    health_status: str
    last_health_check: Optional[str] = None


class FileListResponse(BaseModel):
    """Response model for file listing"""
    files: List[Dict[str, Any]]


class FileOperationResponse(BaseModel):
    """Response model for file operations"""
    status: str
    message: str
    path: Optional[str] = None


async def verify_sandbox_access(client, project_id: str, user_id: Optional[str] = None):
    """
    Verify that a user has access to a specific project/sandbox.
    
    Args:
        client: The Supabase client
        project_id: The project ID to check access for
        user_id: The user ID to check permissions for
        
    Returns:
        dict: Project data
        
    Raises:
        HTTPException: If the user doesn't have access or project doesn't exist
    """
    # Find the project
    project_result = await client.table('projects').select('*').eq('project_id', project_id).execute()
    
    if not project_result.data or len(project_result.data) == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = project_result.data[0]

    # Check if project is public
    if project_data.get('is_public'):
        return project_data
    
    # For private projects, we must have a user_id
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required for this resource")
    
    account_id = project_data.get('account_id')
    
    # Verify account membership
    if account_id:
        account_user_result = await client.schema('basejump').from_('account_user').select('account_role').eq('user_id', user_id).eq('account_id', account_id).execute()
        if account_user_result.data and len(account_user_result.data) > 0:
            return project_data
    
    raise HTTPException(status_code=403, detail="Not authorized to access this project")


def _container_info_to_response(container_info: ContainerInfo, manager) -> SandboxResponse:
    """Convert ContainerInfo to SandboxResponse"""
    return SandboxResponse(
        container_id=container_info.container_id,
        project_id=container_info.project_id or "",
        state=container_info.state.value,
        created_at=container_info.created_at.isoformat(),
        vnc_port=container_info.vnc_port,
        http_port=container_info.http_port,
        vnc_url=manager.get_vnc_url(container_info.project_id) or "",
        http_url=manager.get_http_url(container_info.project_id) or "",
        health_status=container_info.health_status,
        last_health_check=container_info.last_health_check.isoformat() if container_info.last_health_check else None
    )


@router.post("/sandboxes", response_model=SandboxResponse)
async def create_sandbox(
    request: CreateSandboxRequest,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Create a new sandbox container for a project"""
    logger.info(f"Creating sandbox for project {request.project_id}")
    
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, request.project_id, user_id)
    
    try:
        manager = get_container_manager()
        
        # Create resource limits
        resources = ContainerResources(
            cpu_limit=request.cpu_limit,
            memory_limit=request.memory_limit,
            disk_limit=request.disk_limit
        )
        
        # Create container
        container_info = await manager.create_container(
            project_id=request.project_id,
            vnc_password=request.vnc_password,
            resources=resources
        )
        
        logger.info(f"Sandbox created successfully for project {request.project_id}")
        return _container_info_to_response(container_info, manager)
        
    except Exception as e:
        logger.error(f"Failed to create sandbox for project {request.project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {str(e)}")


@router.get("/sandboxes/{project_id}", response_model=SandboxResponse)
async def get_sandbox(
    project_id: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Get sandbox information for a project"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        container_info = await manager.get_container_info(project_id)
        
        if not container_info:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        return _container_info_to_response(container_info, manager)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sandbox for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sandbox: {str(e)}")


@router.post("/sandboxes/{project_id}/start", response_model=SandboxResponse)
async def start_sandbox(
    project_id: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Start a stopped sandbox"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        container_info = await manager.start_container(project_id)
        
        logger.info(f"Sandbox started for project {project_id}")
        return _container_info_to_response(container_info, manager)
        
    except Exception as e:
        logger.error(f"Failed to start sandbox for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start sandbox: {str(e)}")


@router.post("/sandboxes/{project_id}/stop")
async def stop_sandbox(
    project_id: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Stop a running sandbox"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        success = await manager.stop_container(project_id)
        
        if success:
            logger.info(f"Sandbox stopped for project {project_id}")
            return {"status": "success", "message": "Sandbox stopped"}
        else:
            raise HTTPException(status_code=500, detail="Failed to stop sandbox")
        
    except Exception as e:
        logger.error(f"Failed to stop sandbox for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop sandbox: {str(e)}")


@router.post("/sandboxes/{project_id}/restart", response_model=SandboxResponse)
async def restart_sandbox(
    project_id: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Restart a sandbox"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        container_info = await manager.restart_container(project_id)
        
        logger.info(f"Sandbox restarted for project {project_id}")
        return _container_info_to_response(container_info, manager)
        
    except Exception as e:
        logger.error(f"Failed to restart sandbox for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restart sandbox: {str(e)}")


@router.delete("/sandboxes/{project_id}")
async def delete_sandbox(
    project_id: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Delete a sandbox and cleanup resources"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        success = await manager.delete_container(project_id)
        
        if success:
            logger.info(f"Sandbox deleted for project {project_id}")
            return {"status": "success", "message": "Sandbox deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete sandbox")
        
    except Exception as e:
        logger.error(f"Failed to delete sandbox for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete sandbox: {str(e)}")


@router.get("/sandboxes", response_model=List[SandboxResponse])
async def list_sandboxes(
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """List all sandboxes (admin endpoint or filtered by user access)"""
    try:
        manager = get_container_manager()
        containers = await manager.list_containers()
        
        # Convert to response format
        responses = []
        for container in containers:
            if container.project_id:
                try:
                    # For now, return all containers. In production, you might want to filter by user access
                    responses.append(_container_info_to_response(container, manager))
                except Exception as e:
                    logger.warning(f"Error processing container {container.project_id}: {e}")
                    continue
        
        return responses
        
    except Exception as e:
        logger.error(f"Failed to list sandboxes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sandboxes: {str(e)}")


# File system operations
@router.post("/sandboxes/{project_id}/files", response_model=FileOperationResponse)
async def upload_file(
    project_id: str,
    path: str = Form(...),
    file: UploadFile = File(...),
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Upload a file to the sandbox"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        container_info = await manager.get_container_info(project_id)
        
        if not container_info or container_info.state != ContainerState.RUNNING:
            raise HTTPException(status_code=400, detail="Sandbox is not running")
        
        # Get Docker container
        docker_container = manager.docker_client.containers.get(container_info.container_id)
        fs = ContainerFileSystem(docker_container)
        
        # Read file content
        content = await file.read()
        
        # Upload file
        success = await fs.upload_file(content, path)
        
        if success:
            return FileOperationResponse(
                status="success",
                message="File uploaded successfully",
                path=path
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to upload file")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file to sandbox {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/sandboxes/{project_id}/files", response_model=FileListResponse)
async def list_files(
    project_id: str,
    path: str = "/workspace",
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """List files in a sandbox directory"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        container_info = await manager.get_container_info(project_id)
        
        if not container_info or container_info.state != ContainerState.RUNNING:
            raise HTTPException(status_code=400, detail="Sandbox is not running")
        
        # Get Docker container
        docker_container = manager.docker_client.containers.get(container_info.container_id)
        fs = ContainerFileSystem(docker_container)
        
        # List files
        files = await fs.list_files(path)
        
        # Convert to dict format
        file_dicts = []
        for file_info in files:
            file_dicts.append({
                "name": file_info.name,
                "path": file_info.path,
                "is_dir": file_info.is_dir,
                "size": file_info.size,
                "mod_time": file_info.mod_time,
                "permissions": file_info.permissions,
                "owner": file_info.owner
            })
        
        return FileListResponse(files=file_dicts)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list files in sandbox {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/sandboxes/{project_id}/files/content")
async def download_file(
    project_id: str,
    path: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Download a file from the sandbox"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        container_info = await manager.get_container_info(project_id)
        
        if not container_info or container_info.state != ContainerState.RUNNING:
            raise HTTPException(status_code=400, detail="Sandbox is not running")
        
        # Get Docker container
        docker_container = manager.docker_client.containers.get(container_info.container_id)
        fs = ContainerFileSystem(docker_container)
        
        # Download file
        content = await fs.download_file(path)
        
        # Return file content
        filename = path.split('/')[-1]
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file from sandbox {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.delete("/sandboxes/{project_id}/files", response_model=FileOperationResponse)
async def delete_file(
    project_id: str,
    path: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Delete a file from the sandbox"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        container_info = await manager.get_container_info(project_id)
        
        if not container_info or container_info.state != ContainerState.RUNNING:
            raise HTTPException(status_code=400, detail="Sandbox is not running")
        
        # Get Docker container
        docker_container = manager.docker_client.containers.get(container_info.container_id)
        fs = ContainerFileSystem(docker_container)
        
        # Delete file
        success = await fs.delete_file(path)
        
        if success:
            return FileOperationResponse(
                status="success",
                message="File deleted successfully",
                path=path
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file from sandbox {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.post("/project/{project_id}/sandbox/ensure-active", response_model=SandboxResponse)
async def ensure_project_sandbox_active(
    project_id: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Ensure that a project's sandbox is active and running.
    Creates the sandbox if it doesn't exist, starts it if it's stopped.
    """
    logger.info(f"Ensuring sandbox is active for project {project_id}")
    
    client = await db.client
    
    # Verify access to the project
    project_data = await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        
        # Check if container already exists
        container_info = await manager.get_container_info(project_id)
        
        if container_info:
            # Container exists, ensure it's running
            if container_info.state == ContainerState.RUNNING:
                logger.info(f"Sandbox already running for project {project_id}")
                return _container_info_to_response(container_info, manager)
            elif container_info.state == ContainerState.STOPPED:
                # Start the stopped container
                container_info = await manager.start_container(project_id)
                logger.info(f"Started existing sandbox for project {project_id}")
                return _container_info_to_response(container_info, manager)
            else:
                # Container in error state, recreate it
                await manager.delete_container(project_id)
                logger.info(f"Deleted errored container for project {project_id}")
        
        # Create new container
        container_info = await manager.create_container(
            project_id=project_id,
            vnc_password="vncpassword"  # Default password
        )
        
        logger.info(f"Created new sandbox for project {project_id}")
        return _container_info_to_response(container_info, manager)
        
    except Exception as e:
        logger.error(f"Failed to ensure sandbox is active for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ensure sandbox is active: {str(e)}")


# Health and monitoring endpoints
@router.get("/sandboxes/{project_id}/health")
async def get_sandbox_health(
    project_id: str,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Get detailed health information for a sandbox"""
    client = await db.client
    
    # Verify access to the project
    await verify_sandbox_access(client, project_id, user_id)
    
    try:
        manager = get_container_manager()
        container_info = await manager.get_container_info(project_id)
        
        if not container_info:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        # Get detailed container stats
        try:
            docker_container = manager.docker_client.containers.get(container_info.container_id)
            stats = docker_container.stats(stream=False)
            
            return {
                "project_id": project_id,
                "state": container_info.state.value,
                "health_status": container_info.health_status,
                "last_health_check": container_info.last_health_check.isoformat() if container_info.last_health_check else None,
                "vnc_url": manager.get_vnc_url(project_id),
                "http_url": manager.get_http_url(project_id),
                "resource_usage": {
                    "cpu_usage": stats.get("cpu_stats", {}),
                    "memory_usage": stats.get("memory_stats", {}),
                    "network_usage": stats.get("networks", {})
                }
            }
        except Exception as stats_error:
            logger.warning(f"Could not get container stats: {stats_error}")
            return {
                "project_id": project_id,
                "state": container_info.state.value,
                "health_status": container_info.health_status,
                "last_health_check": container_info.last_health_check.isoformat() if container_info.last_health_check else None,
                "vnc_url": manager.get_vnc_url(project_id),
                "http_url": manager.get_http_url(project_id)
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sandbox health for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sandbox health: {str(e)}")


@router.get("/system/health")
async def get_system_health():
    """Get overall system health information"""
    try:
        manager = get_container_manager()
        containers = await manager.list_containers()
        
        # Count containers by state
        state_counts = {}
        for container in containers:
            state = container.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # Get Docker system info
        docker_info = manager.docker_client.info()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "containers": {
                "total": len(containers),
                "by_state": state_counts
            },
            "docker_info": {
                "containers_running": docker_info.get("ContainersRunning", 0),
                "containers_stopped": docker_info.get("ContainersStopped", 0),
                "images": docker_info.get("Images", 0),
                "server_version": docker_info.get("ServerVersion", "unknown")
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }