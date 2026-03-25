"""
File Storage API

FastAPI endpoints for file storage functionality including:
- File upload and download
- File management and listing
- File versioning
- File sharing and permissions
- File search and indexing
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, 
    Query, BackgroundTasks, Response
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.connection import get_db
from database.models import FileStorage, FileVersion, FileShare, User
from services.file_storage import FileStorageService
from auth.jwt_auth import get_current_user_id_from_jwt
from utils.logger import logger


router = APIRouter(prefix="/api/files", tags=["File Storage"])


# Pydantic models for API requests/responses
class FileUploadResponse(BaseModel):
    file_id: str
    original_filename: str
    file_size: int
    content_type: str
    file_hash: str
    is_public: bool
    created_at: datetime
    metadata: Dict[str, Any]

class FileListResponse(BaseModel):
    files: List[FileUploadResponse]
    total_count: int
    page: int
    page_size: int

class FileVersionResponse(BaseModel):
    version_number: int
    file_size: int
    file_hash: str
    change_description: Optional[str]
    created_at: datetime
    created_by: UUID

class FileShareRequest(BaseModel):
    shared_with: Optional[UUID] = None
    share_token: Optional[str] = None
    permissions: str = "read"
    expires_at: Optional[datetime] = None

class FileShareResponse(BaseModel):
    share_id: UUID
    file_id: str
    share_token: str
    permissions: str
    expires_at: Optional[datetime]
    created_at: datetime

class FileSearchRequest(BaseModel):
    query: str
    content_types: Optional[List[str]] = None
    project_id: Optional[UUID] = None
    limit: int = 50

class StorageUsageResponse(BaseModel):
    user_id: UUID
    file_count: int
    total_size_bytes: int
    total_size_mb: float
    total_size_gb: float
    max_storage_bytes: int
    max_storage_gb: float
    usage_percentage: float


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project_id: Optional[UUID] = Form(None),
    description: Optional[str] = Form(None),
    is_public: bool = Form(False),
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """Upload a file to the storage system"""
    try:
        file_service = FileStorageService(db)
        file_record = await file_service.upload_file(
            file=file,
            user_id=user_id,
            project_id=project_id,
            description=description,
            is_public=is_public
        )
        
        return FileUploadResponse(
            file_id=file_record.file_id,
            original_filename=file_record.original_filename,
            file_size=file_record.file_size,
            content_type=file_record.content_type,
            file_hash=file_record.file_hash,
            is_public=file_record.is_public,
            created_at=file_record.created_at,
            metadata=file_record.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_file endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    user_id: Optional[UUID] = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """Download a file from storage"""
    try:
        file_service = FileStorageService(db)
        content, file_record = await file_service.download_file(file_id, user_id)
        
        return StreamingResponse(
            iter([content]),
            media_type=file_record.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_record.original_filename}",
                "Content-Length": str(file_record.file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_file endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list", response_model=FileListResponse)
async def list_files(
    project_id: Optional[UUID] = Query(None),
    status: str = Query("active"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """List files for the current user"""
    try:
        file_service = FileStorageService(db)
        offset = (page - 1) * page_size
        
        files = await file_service.list_files(
            user_id=user_id,
            project_id=project_id,
            status=status,
            limit=page_size,
            offset=offset
        )
        
        # Get total count for pagination
        total_query = db.query(FileStorage).filter(
            FileStorage.user_id == user_id,
            FileStorage.status == status
        )
        if project_id:
            total_query = total_query.filter(FileStorage.project_id == project_id)
        total_count = total_query.count()
        
        file_responses = [
            FileUploadResponse(
                file_id=file.file_id,
                original_filename=file.original_filename,
                file_size=file.file_size,
                content_type=file.content_type,
                file_hash=file.file_hash,
                is_public=file.is_public,
                created_at=file.created_at,
                metadata=file.metadata
            )
            for file in files
        ]
        
        return FileListResponse(
            files=file_responses,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error in list_files endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """Delete a file (soft delete)"""
    try:
        file_service = FileStorageService(db)
        success = await file_service.delete_file(file_id, user_id)
        
        if success:
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_file endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{file_id}/versions", response_model=FileVersionResponse)
async def create_file_version(
    file_id: str,
    file: UploadFile = File(...),
    change_description: Optional[str] = Form(None),
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """Create a new version of an existing file"""
    try:
        file_service = FileStorageService(db)
        version_record = await file_service.create_file_version(
            file_id=file_id,
            user_id=user_id,
            new_file=file,
            change_description=change_description
        )
        
        return FileVersionResponse(
            version_number=version_record.version_number,
            file_size=version_record.file_size,
            file_hash=version_record.file_hash,
            change_description=version_record.change_description,
            created_at=version_record.created_at,
            created_by=version_record.created_by
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_file_version endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{file_id}/versions", response_model=List[FileVersionResponse])
async def list_file_versions(
    file_id: str,
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """List all versions of a file"""
    try:
        # Get file record to verify ownership
        file_record = db.query(FileStorage).filter(
            FileStorage.file_id == file_id,
            FileStorage.user_id == user_id,
            FileStorage.status == 'active'
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get versions
        versions = db.query(FileVersion).filter(
            FileVersion.file_id == file_record.id
        ).order_by(FileVersion.version_number.desc()).all()
        
        return [
            FileVersionResponse(
                version_number=version.version_number,
                file_size=version.file_size,
                file_hash=version.file_hash,
                change_description=version.change_description,
                created_at=version.created_at,
                created_by=version.created_by
            )
            for version in versions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_file_versions endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{file_id}/share", response_model=FileShareResponse)
async def share_file(
    file_id: str,
    share_request: FileShareRequest,
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """Share a file with another user or create a public share"""
    try:
        file_service = FileStorageService(db)
        share_record = await file_service.share_file(
            file_id=file_id,
            shared_by=user_id,
            shared_with=share_request.shared_with,
            share_token=share_request.share_token,
            permissions=share_request.permissions,
            expires_at=share_request.expires_at
        )
        
        return FileShareResponse(
            share_id=share_record.id,
            file_id=file_id,
            share_token=share_record.share_token,
            permissions=share_record.permissions,
            expires_at=share_record.expires_at,
            created_at=share_record.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in share_file endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/shared", response_model=List[FileUploadResponse])
async def list_shared_files(
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """List files shared with the current user"""
    try:
        # Get files shared with this user
        shared_files = db.query(FileStorage).join(FileShare).filter(
            FileShare.shared_with == user_id,
            FileShare.is_active == True,
            FileStorage.status == 'active',
            or_(
                FileShare.expires_at == None,
                FileShare.expires_at > datetime.utcnow()
            )
        ).all()
        
        return [
            FileUploadResponse(
                file_id=file.file_id,
                original_filename=file.original_filename,
                file_size=file.file_size,
                content_type=file.content_type,
                file_hash=file.file_hash,
                is_public=file.is_public,
                created_at=file.created_at,
                metadata=file.metadata
            )
            for file in shared_files
        ]
        
    except Exception as e:
        logger.error(f"Error in list_shared_files endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/download/shared/{share_token}")
async def download_shared_file(
    share_token: str,
    db: Session = Depends(get_db)
):
    """Download a file using a share token"""
    try:
        # Get share record
        share_record = db.query(FileShare).filter(
            FileShare.share_token == share_token,
            FileShare.is_active == True,
            or_(
                FileShare.expires_at == None,
                FileShare.expires_at > datetime.utcnow()
            )
        ).first()
        
        if not share_record:
            raise HTTPException(status_code=404, detail="Share not found or expired")
        
        # Get file record
        file_record = db.query(FileStorage).filter(
            FileStorage.id == share_record.file_id,
            FileStorage.status == 'active'
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Download file
        file_service = FileStorageService(db)
        content, _ = await file_service.download_file(file_record.file_id, None)
        
        return StreamingResponse(
            iter([content]),
            media_type=file_record.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_record.original_filename}",
                "Content-Length": str(file_record.file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_shared_file endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=List[FileUploadResponse])
async def search_files(
    search_request: FileSearchRequest,
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """Search files by filename and metadata"""
    try:
        file_service = FileStorageService(db)
        files = await file_service.search_files(
            user_id=user_id,
            query=search_request.query,
            content_types=search_request.content_types,
            project_id=search_request.project_id,
            limit=search_request.limit
        )
        
        return [
            FileUploadResponse(
                file_id=file.file_id,
                original_filename=file.original_filename,
                file_size=file.file_size,
                content_type=file.content_type,
                file_hash=file.file_hash,
                is_public=file.is_public,
                created_at=file.created_at,
                metadata=file.metadata
            )
            for file in files
        ]
        
    except Exception as e:
        logger.error(f"Error in search_files endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/usage", response_model=StorageUsageResponse)
async def get_storage_usage(
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """Get storage usage statistics for the current user"""
    try:
        file_service = FileStorageService(db)
        usage = await file_service.get_user_storage_usage(user_id)
        
        return StorageUsageResponse(**usage)
        
    except Exception as e:
        logger.error(f"Error in get_storage_usage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/cleanup")
async def cleanup_expired_files(
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db)
):
    """Clean up expired files and shares (admin only)"""
    try:
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        
        # Run cleanup in background
        background_tasks.add_task(file_service.cleanup_expired_files)
        
        return {"message": "File cleanup started in background"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cleanup_expired_files endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/public/{file_id}")
async def download_public_file(
    file_id: str,
    db: Session = Depends(get_db)
):
    """Download a public file"""
    try:
        # Get public file
        file_record = db.query(FileStorage).filter(
            FileStorage.file_id == file_id,
            FileStorage.is_public == True,
            FileStorage.status == 'active'
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="Public file not found")
        
        # Download file
        file_service = FileStorageService(db)
        content, _ = await file_service.download_file(file_id, None)
        
        return StreamingResponse(
            iter([content]),
            media_type=file_record.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_record.original_filename}",
                "Content-Length": str(file_record.file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_public_file endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Admin endpoints
@router.get("/admin/stats")
async def get_admin_storage_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get system-wide storage statistics (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        stats = await file_service.get_system_storage_stats()
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin storage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin storage stats")

@router.get("/admin/list")
async def get_admin_file_list(
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db)
):
    """Get list of all files (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        files = await file_service.get_admin_file_list(
            limit=limit,
            offset=offset,
            status=status,
            user_id=user_id
        )
        return files
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin file list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin file list")

@router.get("/admin/user-storage")
async def get_admin_user_storage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get storage usage for all users (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        user_storage = await file_service.get_all_user_storage()
        return user_storage
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin user storage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin user storage")

@router.get("/admin/activity")
async def get_admin_activity(
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Get recent file activity (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        activity = await file_service.get_recent_activity(limit=limit)
        return activity
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin activity")

@router.post("/admin/cleanup-expired")
async def cleanup_expired_files_admin(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cleanup expired files (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        result = await file_service.cleanup_expired_files()
        return {
            "success": True,
            "message": f"Cleaned up {result['cleaned_count']} expired files",
            "cleaned_count": result['cleaned_count']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up expired files: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup expired files")

@router.post("/admin/cleanup-deleted")
async def cleanup_deleted_files_admin(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cleanup soft-deleted files (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        result = await file_service.cleanup_deleted_files()
        return {
            "success": True,
            "message": f"Cleaned up {result['cleaned_count']} deleted files",
            "cleaned_count": result['cleaned_count']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up deleted files: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup deleted files")

@router.post("/admin/cleanup-backups")
async def cleanup_old_backups_admin(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cleanup old backups (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        result = await file_service.cleanup_old_backups()
        return {
            "success": True,
            "message": f"Cleaned up {result['cleaned_count']} old backups",
            "cleaned_count": result['cleaned_count']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup old backups")

@router.post("/admin/settings")
async def update_storage_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update storage settings (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        result = await file_service.update_storage_settings(settings)
        return {
            "success": True,
            "message": "Storage settings updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating storage settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update storage settings")

@router.post("/admin/feature-flags")
async def update_feature_flags(
    flags: Dict[str, bool],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update file storage feature flags (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        file_service = FileStorageService(db)
        result = await file_service.update_feature_flags(flags)
        return {
            "success": True,
            "message": "Feature flags updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feature flags: {e}")
        raise HTTPException(status_code=500, detail="Failed to update feature flags")
