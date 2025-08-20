"""
Local storage API endpoints to replace Supabase Storage functionality.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List
from services.local_storage import storage_service
from services.auth_middleware import get_current_active_user, get_current_user
from services.auth import User
from utils.logger import logger
import io
import mimetypes

router = APIRouter(prefix="/storage", tags=["storage"])

@router.post("/upload/{bucket}")
async def upload_file_endpoint(
    bucket: str,
    file: UploadFile = File(...),
    custom_path: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Upload a file to the specified bucket.
    
    Parameters:
    - bucket: Storage bucket name (projects, uploads, avatars, etc.)
    - file: File to upload
    - custom_path: Optional custom path within the bucket
    - Authentication: Optional (some buckets may allow anonymous uploads)
    """
    try:
        user_id = current_user.id if current_user else None
        
        # Check if bucket allows anonymous uploads
        anonymous_buckets = ['temp', 'screenshots']
        if not current_user and bucket not in anonymous_buckets:
            raise HTTPException(status_code=401, detail="Authentication required for this bucket")
        
        file_info = await storage_service.upload_file(
            file=file,
            bucket=bucket,
            user_id=user_id,
            custom_path=custom_path
        )
        
        return {
            "success": True,
            "file": file_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@router.post("/upload-bytes/{bucket}")
async def upload_bytes_endpoint(
    bucket: str,
    filename: str,
    content: bytes,
    custom_path: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Upload file content from bytes.
    This is typically used for programmatic uploads.
    """
    try:
        user_id = current_user.id if current_user else None
        
        # Check if bucket allows anonymous uploads
        anonymous_buckets = ['temp', 'screenshots']
        if not current_user and bucket not in anonymous_buckets:
            raise HTTPException(status_code=401, detail="Authentication required for this bucket")
        
        file_info = await storage_service.upload_from_bytes(
            content=content,
            filename=filename,
            bucket=bucket,
            user_id=user_id,
            custom_path=custom_path
        )
        
        return {
            "success": True,
            "file": file_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload bytes error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@router.get("/download/{bucket}/{file_path:path}")
async def download_file_endpoint(
    bucket: str,
    file_path: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Download a file from the specified bucket.
    
    Parameters:
    - bucket: Storage bucket name
    - file_path: Path to the file within the bucket
    """
    try:
        # Check access permissions
        public_buckets = ['screenshots', 'temp']
        if bucket not in public_buckets and not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get file content
        content = await storage_service.download_file(bucket, file_path)
        
        # Get file info for proper headers
        file_info = await storage_service.get_file_info(bucket, file_path)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine content type
        content_type = file_info.get('mime_type') or 'application/octet-stream'
        
        # Create streaming response
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_info['name']}",
                "Content-Length": str(len(content))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="Download failed")

@router.get("/view/{bucket}/{file_path:path}")
async def view_file_endpoint(
    bucket: str,
    file_path: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    View a file inline (for images, PDFs, etc.)
    """
    try:
        # Check access permissions
        public_buckets = ['screenshots', 'temp']
        if bucket not in public_buckets and not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get file content
        content = await storage_service.download_file(bucket, file_path)
        
        # Get file info for proper headers
        file_info = await storage_service.get_file_info(bucket, file_path)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine content type
        content_type = file_info.get('mime_type') or 'application/octet-stream'
        
        # Create streaming response for inline viewing
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Length": str(len(content))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"View error: {e}")
        raise HTTPException(status_code=500, detail="View failed")

@router.delete("/delete/{bucket}/{file_path:path}")
async def delete_file_endpoint(
    bucket: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a file from the specified bucket.
    Requires authentication.
    """
    try:
        success = await storage_service.delete_file(bucket, file_path)
        
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"success": True, "message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail="Delete failed")

@router.get("/list/{bucket}")
async def list_files_endpoint(
    bucket: str,
    prefix: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    List files in the specified bucket.
    
    Parameters:
    - bucket: Storage bucket name
    - prefix: Optional prefix to filter files
    - limit: Maximum number of files to return
    - offset: Number of files to skip
    """
    try:
        # Check access permissions
        public_buckets = ['screenshots', 'temp']
        if bucket not in public_buckets and not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        user_id = current_user.id if current_user else None
        
        files = await storage_service.list_files(
            bucket=bucket,
            prefix=prefix,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "files": files,
            "count": len(files),
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List files error: {e}")
        raise HTTPException(status_code=500, detail="List failed")

@router.get("/info/{bucket}/{file_path:path}")
async def get_file_info_endpoint(
    bucket: str,
    file_path: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get information about a specific file.
    """
    try:
        # Check access permissions
        public_buckets = ['screenshots', 'temp']
        if bucket not in public_buckets and not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        file_info = await storage_service.get_file_info(bucket, file_path)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "success": True,
            "file": file_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get file info error: {e}")
        raise HTTPException(status_code=500, detail="Get info failed")

@router.post("/copy")
async def copy_file_endpoint(
    source_bucket: str,
    source_path: str,
    dest_bucket: str,
    dest_path: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Copy a file from one location to another.
    Requires authentication.
    """
    try:
        success = await storage_service.copy_file(
            source_bucket, source_path, dest_bucket, dest_path
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Source file not found")
        
        return {"success": True, "message": "File copied successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copy error: {e}")
        raise HTTPException(status_code=500, detail="Copy failed")

@router.post("/move")
async def move_file_endpoint(
    source_bucket: str,
    source_path: str,
    dest_bucket: str,
    dest_path: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Move a file from one location to another.
    Requires authentication.
    """
    try:
        success = await storage_service.move_file(
            source_bucket, source_path, dest_bucket, dest_path
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Source file not found")
        
        return {"success": True, "message": "File moved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Move error: {e}")
        raise HTTPException(status_code=500, detail="Move failed")

@router.get("/stats")
async def get_storage_stats_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get storage usage statistics.
    Requires authentication.
    """
    try:
        # Only allow admins to view system-wide stats
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        stats = storage_service.get_storage_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail="Get stats failed")

@router.post("/cleanup-temp")
async def cleanup_temp_files_endpoint(
    max_age_hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    current_user: User = Depends(get_current_active_user)
):
    """
    Clean up temporary files older than specified hours.
    Requires authentication.
    """
    try:
        # Only allow admins to cleanup files
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        await storage_service.cleanup_temp_files(max_age_hours)
        
        return {
            "success": True,
            "message": f"Cleaned up temporary files older than {max_age_hours} hours"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")