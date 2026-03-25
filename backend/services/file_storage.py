"""
File Storage Service

This module provides comprehensive file storage functionality including:
- File upload and download
- File versioning and backup
- File sharing and permissions
- File search and indexing
- Quota management
"""

import asyncio
import hashlib
import mimetypes
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, BinaryIO, Tuple
from uuid import UUID, uuid4
import aiofiles
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database.models import FileStorage, FileVersion, FileShare, FileBackup, User, Project
from utils.logger import logger
from utils.config import config


class FileStorageService:
    """
    Comprehensive file storage service for managing files in the Suna system.
    
    Features:
    - Secure file upload and download
    - File versioning and backup
    - File sharing and permission management
    - File search and indexing
    - Quota management and cleanup
    """
    
    def __init__(self, db: Session):
        """Initialize file storage service"""
        self.db = db
        self.base_path = config.FILE_STORAGE_PATH or "/data/files"
        self.max_file_size = config.MAX_FILE_SIZE or 100 * 1024 * 1024  # 100MB
        self.allowed_extensions = config.ALLOWED_FILE_EXTENSIONS or [
            '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json', '.xml',
            '.csv', '.xlsx', '.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg',
            '.gif', '.svg', '.zip', '.tar', '.gz', '.rar'
        ]
        
        # Ensure base directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        directories = [
            self.base_path,
            os.path.join(self.base_path, "users"),
            os.path.join(self.base_path, "projects"),
            os.path.join(self.base_path, "backups"),
            os.path.join(self.base_path, "temp"),
            os.path.join(self.base_path, "shared")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    async def upload_file(
        self,
        file: UploadFile,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        description: Optional[str] = None,
        is_public: bool = False
    ) -> FileStorage:
        """
        Upload a file to the storage system.
        
        Args:
            file: FastAPI UploadFile object
            user_id: ID of the user uploading the file
            project_id: Optional project ID to associate with the file
            description: Optional file description
            is_public: Whether the file should be publicly accessible
            
        Returns:
            FileStorage: Created file storage record
            
        Raises:
            HTTPException: If upload fails or validation fails
        """
        try:
            # Validate file
            await self._validate_file(file)
            
            # Check user quota
            await self._check_user_quota(user_id, file.size)
            
            # Generate file ID and paths
            file_id = str(uuid4())
            file_hash = await self._calculate_file_hash(file)
            
            # Check if file already exists (deduplication)
            existing_file = self.db.query(FileStorage).filter(
                FileStorage.file_hash == file_hash,
                FileStorage.user_id == user_id
            ).first()
            
            if existing_file:
                logger.info(f"File already exists for user {user_id}: {existing_file.file_id}")
                return existing_file
            
            # Determine storage path
            if project_id:
                storage_path = os.path.join(self.base_path, "projects", str(project_id), file_id)
            else:
                storage_path = os.path.join(self.base_path, "users", str(user_id), file_id)
            
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            
            # Save file to disk
            stored_filename = f"{file_id}_{file.filename}"
            file_path = os.path.join(storage_path, stored_filename)
            
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Create database record
            file_record = FileStorage(
                file_id=file_id,
                user_id=user_id,
                project_id=project_id,
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_path=file_path,
                file_size=file.size,
                content_type=file.content_type or self._guess_content_type(file.filename),
                file_hash=file_hash,
                is_public=is_public,
                metadata={
                    'description': description,
                    'upload_method': 'web_upload',
                    'original_content_type': file.content_type
                }
            )
            
            self.db.add(file_record)
            self.db.commit()
            self.db.refresh(file_record)
            
            logger.info(f"File uploaded successfully: {file_id} ({file.filename})")
            return file_record
            
        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    async def download_file(self, file_id: str, user_id: Optional[UUID] = None) -> Tuple[bytes, FileStorage]:
        """
        Download a file from storage.
        
        Args:
            file_id: ID of the file to download
            user_id: Optional user ID for permission checking
            
        Returns:
            Tuple[bytes, FileStorage]: File content and file record
            
        Raises:
            HTTPException: If file not found or access denied
        """
        try:
            # Get file record
            file_record = self.db.query(FileStorage).filter(
                FileStorage.file_id == file_id,
                FileStorage.status == 'active'
            ).first()
            
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Check permissions
            if not await self._can_access_file(file_record, user_id):
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Check if file exists on disk
            if not os.path.exists(file_record.file_path):
                raise HTTPException(status_code=404, detail="File not found on disk")
            
            # Read file content
            async with aiofiles.open(file_record.file_path, 'rb') as f:
                content = await f.read()
            
            # Update download statistics
            file_record.download_count += 1
            file_record.last_downloaded_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"File downloaded: {file_id} by user {user_id}")
            return content, file_record
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")
    
    async def list_files(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        status: str = 'active',
        limit: int = 100,
        offset: int = 0
    ) -> List[FileStorage]:
        """
        List files for a user or project.
        
        Args:
            user_id: User ID to list files for
            project_id: Optional project ID to filter by
            status: File status filter
            limit: Maximum number of files to return
            offset: Number of files to skip
            
        Returns:
            List[FileStorage]: List of file records
        """
        try:
            query = self.db.query(FileStorage).filter(
                FileStorage.user_id == user_id,
                FileStorage.status == status
            )
            
            if project_id:
                query = query.filter(FileStorage.project_id == project_id)
            
            files = query.order_by(FileStorage.created_at.desc()).offset(offset).limit(limit).all()
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files for user {user_id}: {e}")
            return []
    
    async def delete_file(self, file_id: str, user_id: UUID) -> bool:
        """
        Delete a file (soft delete).
        
        Args:
            file_id: ID of the file to delete
            user_id: ID of the user requesting deletion
            
        Returns:
            bool: True if deletion successful
            
        Raises:
            HTTPException: If file not found or access denied
        """
        try:
            file_record = self.db.query(FileStorage).filter(
                FileStorage.file_id == file_id,
                FileStorage.user_id == user_id,
                FileStorage.status == 'active'
            ).first()
            
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Soft delete
            file_record.status = 'deleted'
            self.db.commit()
            
            logger.info(f"File deleted: {file_id} by user {user_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
    
    async def create_file_version(
        self,
        file_id: str,
        user_id: UUID,
        new_file: UploadFile,
        change_description: Optional[str] = None
    ) -> FileVersion:
        """
        Create a new version of an existing file.
        
        Args:
            file_id: ID of the original file
            user_id: ID of the user creating the version
            new_file: New file content
            change_description: Description of changes
            
        Returns:
            FileVersion: Created version record
            
        Raises:
            HTTPException: If versioning fails
        """
        try:
            # Get original file
            original_file = self.db.query(FileStorage).filter(
                FileStorage.file_id == file_id,
                FileStorage.user_id == user_id,
                FileStorage.status == 'active'
            ).first()
            
            if not original_file:
                raise HTTPException(status_code=404, detail="Original file not found")
            
            # Get next version number
            latest_version = self.db.query(FileVersion).filter(
                FileVersion.file_id == original_file.id
            ).order_by(FileVersion.version_number.desc()).first()
            
            version_number = (latest_version.version_number + 1) if latest_version else 1
            
            # Create backup of current version
            await self._backup_current_version(original_file, version_number - 1)
            
            # Update original file with new content
            new_hash = await self._calculate_file_hash(new_file)
            new_content = await new_file.read()
            
            # Save new content
            async with aiofiles.open(original_file.file_path, 'wb') as f:
                await f.write(new_content)
            
            # Update file record
            original_file.file_size = len(new_content)
            original_file.file_hash = new_hash
            original_file.updated_at = datetime.utcnow()
            
            # Create version record
            version_record = FileVersion(
                file_id=original_file.id,
                version_number=version_number,
                stored_filename=original_file.stored_filename,
                file_path=original_file.file_path,
                file_size=original_file.file_size,
                file_hash=original_file.file_hash,
                change_description=change_description,
                created_by=user_id
            )
            
            self.db.add(version_record)
            self.db.commit()
            self.db.refresh(version_record)
            
            logger.info(f"File version created: {file_id} v{version_number}")
            return version_record
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating file version for {file_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create file version: {str(e)}")
    
    async def share_file(
        self,
        file_id: str,
        shared_by: UUID,
        shared_with: Optional[UUID] = None,
        share_token: Optional[str] = None,
        permissions: str = 'read',
        expires_at: Optional[datetime] = None
    ) -> FileShare:
        """
        Share a file with another user or create a public share.
        
        Args:
            file_id: ID of the file to share
            shared_by: ID of the user sharing the file
            shared_with: ID of the user to share with (optional for public shares)
            share_token: Optional custom share token
            permissions: Share permissions (read, write, admin)
            expires_at: Optional expiration date
            
        Returns:
            FileShare: Created share record
            
        Raises:
            HTTPException: If sharing fails
        """
        try:
            # Verify file exists and user owns it
            file_record = self.db.query(FileStorage).filter(
                FileStorage.file_id == file_id,
                FileStorage.user_id == shared_by,
                FileStorage.status == 'active'
            ).first()
            
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Generate share token if not provided
            if not share_token:
                share_token = str(uuid4())
            
            # Create share record
            share_record = FileShare(
                file_id=file_record.id,
                shared_by=shared_by,
                shared_with=shared_with,
                share_token=share_token,
                permissions=permissions,
                expires_at=expires_at
            )
            
            self.db.add(share_record)
            self.db.commit()
            self.db.refresh(share_record)
            
            logger.info(f"File shared: {file_id} by {shared_by} with {shared_with or 'public'}")
            return share_record
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sharing file {file_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to share file: {str(e)}")
    
    async def search_files(
        self,
        user_id: UUID,
        query: str,
        content_types: Optional[List[str]] = None,
        project_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[FileStorage]:
        """
        Search files by filename and metadata.
        
        Args:
            user_id: User ID to search files for
            query: Search query string
            content_types: Optional list of content types to filter by
            project_id: Optional project ID to filter by
            limit: Maximum number of results
            
        Returns:
            List[FileStorage]: List of matching files
        """
        try:
            search_query = self.db.query(FileStorage).filter(
                FileStorage.user_id == user_id,
                FileStorage.status == 'active',
                or_(
                    FileStorage.original_filename.ilike(f"%{query}%"),
                    FileStorage.metadata['description'].astext.ilike(f"%{query}%")
                )
            )
            
            if content_types:
                search_query = search_query.filter(FileStorage.content_type.in_(content_types))
            
            if project_id:
                search_query = search_query.filter(FileStorage.project_id == project_id)
            
            files = search_query.order_by(FileStorage.updated_at.desc()).limit(limit).all()
            
            return files
            
        except Exception as e:
            logger.error(f"Error searching files for user {user_id}: {e}")
            return []
    
    async def get_user_storage_usage(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get storage usage statistics for a user.
        
        Args:
            user_id: User ID to get usage for
            
        Returns:
            Dict[str, Any]: Storage usage statistics
        """
        try:
            # Get total file count and size
            stats = self.db.query(
                func.count(FileStorage.id).label('file_count'),
                func.sum(FileStorage.file_size).label('total_size')
            ).filter(
                FileStorage.user_id == user_id,
                FileStorage.status == 'active'
            ).first()
            
            total_size = stats.total_size or 0
            file_count = stats.file_count or 0
            
            # Get user tier for quota info
            user = self.db.query(User).filter(User.id == user_id).first()
            max_storage = user.tier.max_storage_gb * 1024 * 1024 * 1024 if user and user.tier else 5 * 1024 * 1024 * 1024
            
            return {
                'user_id': user_id,
                'file_count': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'total_size_gb': total_size / (1024 * 1024 * 1024),
                'max_storage_bytes': max_storage,
                'max_storage_gb': max_storage / (1024 * 1024 * 1024),
                'usage_percentage': (total_size / max_storage * 100) if max_storage > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting storage usage for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'file_count': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'total_size_gb': 0,
                'max_storage_bytes': 0,
                'max_storage_gb': 0,
                'usage_percentage': 0
            }
    
    async def cleanup_expired_files(self) -> int:
        """
        Clean up expired files and shares.
        
        Returns:
            int: Number of files cleaned up
        """
        try:
            # Clean up expired shares
            expired_shares = self.db.query(FileShare).filter(
                and_(
                    FileShare.expires_at < datetime.utcnow(),
                    FileShare.is_active == True
                )
            ).all()
            
            for share in expired_shares:
                share.is_active = False
            
            # Clean up old backups
            retention_days = 30
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            old_backups = self.db.query(FileBackup).filter(
                FileBackup.created_at < cutoff_date
            ).all()
            
            for backup in old_backups:
                # Remove backup file from disk
                if os.path.exists(backup.backup_path):
                    os.remove(backup.backup_path)
                self.db.delete(backup)
            
            self.db.commit()
            
            cleaned_count = len(expired_shares) + len(old_backups)
            logger.info(f"Cleaned up {cleaned_count} expired files/shares")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired files: {e}")
            return 0
    
    async def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if file.size > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {self.max_file_size / (1024 * 1024)}MB"
            )
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}"
            )
    
    async def _check_user_quota(self, user_id: UUID, file_size: int) -> None:
        """Check if user has enough storage quota"""
        usage = await self.get_user_storage_usage(user_id)
        
        if usage['total_size_bytes'] + file_size > usage['max_storage_bytes']:
            raise HTTPException(
                status_code=413,
                detail=f"Insufficient storage quota. Available: {usage['max_storage_gb'] - usage['total_size_gb']:.2f}GB"
            )
    
    async def _calculate_file_hash(self, file: UploadFile) -> str:
        """Calculate SHA256 hash of file content"""
        content = await file.read()
        file.seek(0)  # Reset file pointer
        return hashlib.sha256(content).hexdigest()
    
    async def _can_access_file(self, file_record: FileStorage, user_id: Optional[UUID]) -> bool:
        """Check if user can access a file"""
        # Public files are accessible to everyone
        if file_record.is_public:
            return True
        
        # File owner can always access
        if user_id and file_record.user_id == user_id:
            return True
        
        # Check shared access
        if user_id:
            share = self.db.query(FileShare).filter(
                FileShare.file_id == file_record.id,
                FileShare.shared_with == user_id,
                FileShare.is_active == True,
                or_(
                    FileShare.expires_at == None,
                    FileShare.expires_at > datetime.utcnow()
                )
            ).first()
            
            if share:
                return True
        
        return False
    
    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename"""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'
    
    async def _backup_current_version(self, file_record: FileStorage, version_number: int) -> None:
        """Create backup of current file version"""
        try:
            backup_dir = os.path.join(self.base_path, "backups", str(file_record.user_id))
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_filename = f"{file_record.file_id}_v{version_number}_{file_record.original_filename}"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Copy file to backup location
            shutil.copy2(file_record.file_path, backup_path)
            
            # Get backup file info
            backup_size = os.path.getsize(backup_path)
            with open(backup_path, 'rb') as f:
                backup_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Create backup record
            backup_record = FileBackup(
                file_id=file_record.id,
                backup_filename=backup_filename,
                backup_path=backup_path,
                backup_size=backup_size,
                backup_hash=backup_hash,
                backup_type='version',
                created_by=file_record.user_id
            )
            
            self.db.add(backup_record)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error creating backup for file {file_record.file_id}: {e}")

    # Admin methods
    async def get_system_storage_stats(self) -> Dict[str, Any]:
        """Get system-wide storage statistics (admin only)"""
        try:
            # Get basic stats
            total_files = self.db.query(FileStorage).count()
            active_files = self.db.query(FileStorage).filter(FileStorage.status == 'active').count()
            deleted_files = self.db.query(FileStorage).filter(FileStorage.status == 'deleted').count()
            
            # Get total size
            total_size_result = self.db.query(func.sum(FileStorage.file_size)).filter(
                FileStorage.status == 'active'
            ).scalar()
            total_size_bytes = total_size_result or 0
            
            # Get average file size
            avg_size_result = self.db.query(func.avg(FileStorage.file_size)).filter(
                FileStorage.status == 'active'
            ).scalar()
            avg_file_size = int(avg_size_result) if avg_size_result else 0
            
            # Get user stats
            users_with_files = self.db.query(func.count(func.distinct(FileStorage.user_id))).filter(
                FileStorage.status == 'active'
            ).scalar() or 0
            
            # Get top storage user
            top_user_result = self.db.query(
                FileStorage.user_id,
                func.sum(FileStorage.file_size).label('total_size')
            ).filter(
                FileStorage.status == 'active'
            ).group_by(FileStorage.user_id).order_by(
                func.sum(FileStorage.file_size).desc()
            ).first()
            
            top_storage_user = top_user_result.user_id if top_user_result else None
            
            # Get shared and public files
            shared_files = self.db.query(FileShare).count()
            public_files = self.db.query(FileStorage).filter(
                FileStorage.is_public == True,
                FileStorage.status == 'active'
            ).count()
            
            # Get recent uploads (last 24 hours)
            recent_uploads = self.db.query(FileStorage).filter(
                FileStorage.created_at >= datetime.now() - timedelta(days=1),
                FileStorage.status == 'active'
            ).count()
            
            # Get active users (users with files in last 7 days)
            active_users = self.db.query(func.count(func.distinct(FileStorage.user_id))).filter(
                FileStorage.created_at >= datetime.now() - timedelta(days=7),
                FileStorage.status == 'active'
            ).scalar() or 0
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size_bytes,
                "active_files": active_files,
                "deleted_files": deleted_files,
                "avg_file_size": avg_file_size,
                "users_with_files": users_with_files,
                "top_storage_user": top_storage_user,
                "shared_files": shared_files,
                "public_files": public_files,
                "recent_uploads": recent_uploads,
                "active_users": active_users
            }
            
        except Exception as e:
            logger.error(f"Error getting system storage stats: {e}")
            raise

    async def get_admin_file_list(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get list of all files for admin (admin only)"""
        try:
            query = self.db.query(FileStorage).join(User, FileStorage.user_id == User.id)
            
            if status:
                query = query.filter(FileStorage.status == status)
            if user_id:
                query = query.filter(FileStorage.user_id == user_id)
            
            files = query.order_by(FileStorage.created_at.desc()).offset(offset).limit(limit).all()
            
            return [
                {
                    "file_id": file.file_id,
                    "original_filename": file.original_filename,
                    "file_size": file.file_size,
                    "content_type": file.content_type,
                    "status": file.status,
                    "is_public": file.is_public,
                    "created_at": file.created_at.isoformat(),
                    "user_email": file.user.email if file.user else None,
                    "user_id": str(file.user_id) if file.user_id else None
                }
                for file in files
            ]
            
        except Exception as e:
            logger.error(f"Error getting admin file list: {e}")
            raise

    async def get_all_user_storage(self) -> List[Dict[str, Any]]:
        """Get storage usage for all users (admin only)"""
        try:
            # Get storage usage per user
            user_storage = self.db.query(
                User.id,
                User.email,
                func.count(FileStorage.id).label('file_count'),
                func.sum(FileStorage.file_size).label('total_size_bytes')
            ).outerjoin(FileStorage, and_(
                User.id == FileStorage.user_id,
                FileStorage.status == 'active'
            )).group_by(User.id, User.email).all()
            
            result = []
            for user_id, email, file_count, total_size in user_storage:
                total_size_bytes = total_size or 0
                max_storage_bytes = 5 * 1024 * 1024 * 1024  # 5GB default quota
                usage_percentage = (total_size_bytes / max_storage_bytes) * 100 if max_storage_bytes > 0 else 0
                
                result.append({
                    "user_id": str(user_id),
                    "email": email,
                    "file_count": file_count or 0,
                    "total_size_bytes": total_size_bytes,
                    "max_storage_bytes": max_storage_bytes,
                    "usage_percentage": usage_percentage
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all user storage: {e}")
            raise

    async def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent file activity (admin only)"""
        try:
            # This is a placeholder - in a real implementation, you'd have an activity log table
            # For now, we'll return recent file operations based on file timestamps
            
            recent_files = self.db.query(FileStorage).order_by(
                FileStorage.created_at.desc()
            ).limit(limit).all()
            
            activity = []
            for file in recent_files:
                activity.append({
                    "type": "file_upload",
                    "description": f"File '{file.original_filename}' uploaded by user",
                    "timestamp": file.created_at.isoformat(),
                    "file_id": file.file_id,
                    "user_id": str(file.user_id) if file.user_id else None
                })
            
            return activity
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            raise

    async def cleanup_expired_files(self) -> Dict[str, int]:
        """Cleanup expired files (admin only)"""
        try:
            # Find expired files (files with expiration date in the past)
            expired_files = self.db.query(FileStorage).filter(
                and_(
                    FileStorage.expires_at.isnot(None),
                    FileStorage.expires_at < datetime.now(),
                    FileStorage.status == 'active'
                )
            ).all()
            
            cleaned_count = 0
            for file in expired_files:
                try:
                    # Delete the physical file
                    file_path = os.path.join(self.storage_path, file.file_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # Update database record
                    file.status = 'deleted'
                    file.deleted_at = datetime.now()
                    self.db.commit()
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Error cleaning up expired file {file.file_id}: {e}")
                    continue
            
            return {"cleaned_count": cleaned_count}
            
        except Exception as e:
            logger.error(f"Error cleaning up expired files: {e}")
            raise

    async def cleanup_deleted_files(self) -> Dict[str, int]:
        """Cleanup soft-deleted files (admin only)"""
        try:
            # Find soft-deleted files older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            deleted_files = self.db.query(FileStorage).filter(
                and_(
                    FileStorage.status == 'deleted',
                    FileStorage.deleted_at < cutoff_date
                )
            ).all()
            
            cleaned_count = 0
            for file in deleted_files:
                try:
                    # Delete the physical file
                    file_path = os.path.join(self.storage_path, file.file_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # Delete database record
                    self.db.delete(file)
                    self.db.commit()
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Error cleaning up deleted file {file.file_id}: {e}")
                    continue
            
            return {"cleaned_count": cleaned_count}
            
        except Exception as e:
            logger.error(f"Error cleaning up deleted files: {e}")
            raise

    async def cleanup_old_backups(self) -> Dict[str, int]:
        """Cleanup old backups (admin only)"""
        try:
            # Find old backups (older than 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            old_backups = self.db.query(FileBackup).filter(
                FileBackup.created_at < cutoff_date
            ).all()
            
            cleaned_count = 0
            for backup in old_backups:
                try:
                    # Delete the physical backup file
                    backup_path = os.path.join(self.storage_path, backup.backup_path)
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    
                    # Delete database record
                    self.db.delete(backup)
                    self.db.commit()
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Error cleaning up backup {backup.id}: {e}")
                    continue
            
            return {"cleaned_count": cleaned_count}
            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
            raise

    async def update_storage_settings(self, settings: Dict[str, Any]) -> bool:
        """Update storage settings (admin only)"""
        try:
            # This would typically update configuration in a settings table or config file
            # For now, we'll just log the settings update
            logger.info(f"Storage settings updated: {settings}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating storage settings: {e}")
            raise

    async def update_feature_flags(self, flags: Dict[str, bool]) -> bool:
        """Update file storage feature flags (admin only)"""
        try:
            # This would typically update feature flags in a settings table or config file
            # For now, we'll just log the flags update
            logger.info(f"File storage feature flags updated: {flags}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating feature flags: {e}")
            raise
