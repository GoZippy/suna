"""
Local file storage service to replace Supabase Storage.
Provides file upload, download, and management functionality using local filesystem.
"""

import os
import shutil
import hashlib
import mimetypes
from typing import Optional, Dict, Any, List, BinaryIO
from pathlib import Path
from datetime import datetime, timezone
import uuid
import aiofiles
import aiofiles.os
from fastapi import UploadFile, HTTPException
from utils.logger import logger
from utils.config import config

class LocalStorageService:
    """Local file storage service"""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or config.LOCAL_STORAGE_PATH or "./data/storage")
        self.max_file_size = config.MAX_FILE_SIZE or 100 * 1024 * 1024  # 100MB default
        self.allowed_extensions = config.ALLOWED_FILE_EXTENSIONS or [
            '.txt', '.md', '.py', '.js', '.ts', '.json', '.yaml', '.yml',
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.tar', '.gz', '.csv'
        ]
        
        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create bucket directories
        self.buckets = {
            'projects': self.base_path / 'projects',
            'uploads': self.base_path / 'uploads',
            'avatars': self.base_path / 'avatars',
            'screenshots': self.base_path / 'screenshots',
            'documents': self.base_path / 'documents',
            'temp': self.base_path / 'temp'
        }
        
        for bucket_path in self.buckets.values():
            bucket_path.mkdir(parents=True, exist_ok=True)
    
    def _get_bucket_path(self, bucket: str) -> Path:
        """Get the path for a specific bucket"""
        if bucket not in self.buckets:
            raise ValueError(f"Unknown bucket: {bucket}")
        return self.buckets[bucket]
    
    def _validate_file(self, filename: str, file_size: int) -> None:
        """Validate file before upload"""
        # Check file size
        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {self.max_file_size / (1024*1024):.1f}MB"
            )
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed extensions: {', '.join(self.allowed_extensions)}"
            )
    
    def _generate_file_path(self, bucket: str, filename: str, user_id: Optional[str] = None) -> Path:
        """Generate a unique file path"""
        bucket_path = self._get_bucket_path(bucket)
        
        # Create user subdirectory if user_id provided
        if user_id:
            user_path = bucket_path / user_id
            user_path.mkdir(parents=True, exist_ok=True)
            bucket_path = user_path
        
        # Generate unique filename to avoid conflicts
        file_ext = Path(filename).suffix
        base_name = Path(filename).stem
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        unique_filename = f"{base_name}_{timestamp}_{unique_id}{file_ext}"
        return bucket_path / unique_filename
    
    async def upload_file(
        self,
        file: UploadFile,
        bucket: str,
        user_id: Optional[str] = None,
        custom_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a file to local storage"""
        try:
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Validate file
            self._validate_file(file.filename, file_size)
            
            # Generate file path
            if custom_path:
                file_path = self._get_bucket_path(bucket) / custom_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                file_path = self._generate_file_path(bucket, file.filename, user_id)
            
            # Calculate file hash
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Write file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # Get file info
            file_info = {
                'id': str(uuid.uuid4()),
                'name': file.filename,
                'path': str(file_path.relative_to(self.base_path)),
                'full_path': str(file_path),
                'bucket': bucket,
                'size': file_size,
                'mime_type': file.content_type or mimetypes.guess_type(file.filename)[0],
                'hash': file_hash,
                'user_id': user_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'url': f"/api/storage/{bucket}/{file_path.relative_to(self._get_bucket_path(bucket))}"
            }
            
            logger.info(f"File uploaded successfully: {file_path}")
            return file_info
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    async def upload_from_bytes(
        self,
        content: bytes,
        filename: str,
        bucket: str,
        user_id: Optional[str] = None,
        custom_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file from bytes content"""
        try:
            file_size = len(content)
            
            # Validate file
            self._validate_file(filename, file_size)
            
            # Generate file path
            if custom_path:
                file_path = self._get_bucket_path(bucket) / custom_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                file_path = self._generate_file_path(bucket, filename, user_id)
            
            # Calculate file hash
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Write file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # Get file info
            file_info = {
                'id': str(uuid.uuid4()),
                'name': filename,
                'path': str(file_path.relative_to(self.base_path)),
                'full_path': str(file_path),
                'bucket': bucket,
                'size': file_size,
                'mime_type': mimetypes.guess_type(filename)[0],
                'hash': file_hash,
                'user_id': user_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'url': f"/api/storage/{bucket}/{file_path.relative_to(self._get_bucket_path(bucket))}"
            }
            
            logger.info(f"File uploaded from bytes: {file_path}")
            return file_info
            
        except Exception as e:
            logger.error(f"Error uploading file from bytes: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    async def download_file(self, bucket: str, file_path: str) -> bytes:
        """Download a file from local storage"""
        try:
            full_path = self._get_bucket_path(bucket) / file_path
            
            if not full_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            async with aiofiles.open(full_path, 'rb') as f:
                content = await f.read()
            
            return content
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
    
    async def delete_file(self, bucket: str, file_path: str) -> bool:
        """Delete a file from local storage"""
        try:
            full_path = self._get_bucket_path(bucket) / file_path
            
            if not full_path.exists():
                return False
            
            await aiofiles.os.remove(full_path)
            logger.info(f"File deleted: {full_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    async def list_files(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files in a bucket"""
        try:
            bucket_path = self._get_bucket_path(bucket)
            
            if user_id:
                bucket_path = bucket_path / user_id
            
            if not bucket_path.exists():
                return []
            
            files = []
            pattern = f"{prefix}*" if prefix else "*"
            
            for file_path in bucket_path.rglob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    
                    file_info = {
                        'name': file_path.name,
                        'path': str(file_path.relative_to(self._get_bucket_path(bucket))),
                        'size': stat.st_size,
                        'mime_type': mimetypes.guess_type(file_path.name)[0],
                        'created_at': datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                        'modified_at': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        'url': f"/api/storage/{bucket}/{file_path.relative_to(self._get_bucket_path(bucket))}"
                    }
                    files.append(file_info)
            
            # Sort by creation time (newest first)
            files.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Apply pagination
            return files[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    async def get_file_info(self, bucket: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific file"""
        try:
            full_path = self._get_bucket_path(bucket) / file_path
            
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            
            # Calculate file hash
            async with aiofiles.open(full_path, 'rb') as f:
                content = await f.read()
                file_hash = hashlib.sha256(content).hexdigest()
            
            file_info = {
                'name': full_path.name,
                'path': str(full_path.relative_to(self.base_path)),
                'full_path': str(full_path),
                'bucket': bucket,
                'size': stat.st_size,
                'mime_type': mimetypes.guess_type(full_path.name)[0],
                'hash': file_hash,
                'created_at': datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                'url': f"/api/storage/{bucket}/{file_path}"
            }
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    async def copy_file(self, source_bucket: str, source_path: str, dest_bucket: str, dest_path: str) -> bool:
        """Copy a file from one location to another"""
        try:
            source_full_path = self._get_bucket_path(source_bucket) / source_path
            dest_full_path = self._get_bucket_path(dest_bucket) / dest_path
            
            if not source_full_path.exists():
                return False
            
            # Create destination directory if needed
            dest_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_full_path, dest_full_path)
            logger.info(f"File copied: {source_full_path} -> {dest_full_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    async def move_file(self, source_bucket: str, source_path: str, dest_bucket: str, dest_path: str) -> bool:
        """Move a file from one location to another"""
        try:
            source_full_path = self._get_bucket_path(source_bucket) / source_path
            dest_full_path = self._get_bucket_path(dest_bucket) / dest_path
            
            if not source_full_path.exists():
                return False
            
            # Create destination directory if needed
            dest_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(source_full_path, dest_full_path)
            logger.info(f"File moved: {source_full_path} -> {dest_full_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics"""
        try:
            stats = {
                'total_size': 0,
                'file_count': 0,
                'buckets': {}
            }
            
            for bucket_name, bucket_path in self.buckets.items():
                bucket_size = 0
                bucket_files = 0
                
                if bucket_path.exists():
                    for file_path in bucket_path.rglob('*'):
                        if file_path.is_file():
                            file_size = file_path.stat().st_size
                            bucket_size += file_size
                            bucket_files += 1
                
                stats['buckets'][bucket_name] = {
                    'size': bucket_size,
                    'file_count': bucket_files
                }
                
                stats['total_size'] += bucket_size
                stats['file_count'] += bucket_files
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {'total_size': 0, 'file_count': 0, 'buckets': {}}
    
    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary files older than specified hours"""
        try:
            temp_path = self.buckets['temp']
            if not temp_path.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            deleted_count = 0
            
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        await aiofiles.os.remove(file_path)
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} temporary files")
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

# Global storage service instance
storage_service = LocalStorageService()

# Convenience functions
async def upload_file(file: UploadFile, bucket: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Upload a file to local storage"""
    return await storage_service.upload_file(file, bucket, user_id)

async def download_file(bucket: str, file_path: str) -> bytes:
    """Download a file from local storage"""
    return await storage_service.download_file(bucket, file_path)

async def delete_file(bucket: str, file_path: str) -> bool:
    """Delete a file from local storage"""
    return await storage_service.delete_file(bucket, file_path)