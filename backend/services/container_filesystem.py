"""
Container File System Operations

This module provides secure file system operations within sandbox containers,
including file upload, download, listing, and manipulation capabilities.
"""

import asyncio
import io
import os
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, BinaryIO
from dataclasses import dataclass
from datetime import datetime

import docker
from docker.models.containers import Container

from utils.logger import logger


@dataclass
class FileInfo:
    """File information data class"""
    name: str
    path: str
    is_dir: bool
    size: int
    mod_time: str
    permissions: Optional[str] = None
    owner: Optional[str] = None


class ContainerFileSystem:
    """
    Provides secure file system operations within Docker containers.
    
    This class handles file operations like upload, download, listing,
    and manipulation within sandbox containers while maintaining security.
    """
    
    def __init__(self, container: Container):
        """
        Initialize container file system handler.
        
        Args:
            container: Docker container instance
        """
        self.container = container
        self.workspace_path = "/workspace"
    
    async def upload_file(self, content: bytes, file_path: str) -> bool:
        """
        Upload file content to the container.
        
        Args:
            content: File content as bytes
            file_path: Destination path in container
            
        Returns:
            bool: True if upload successful
        """
        try:
            # Normalize path
            normalized_path = self._normalize_path(file_path)
            
            # Create directory structure if needed
            dir_path = os.path.dirname(normalized_path)
            if dir_path and dir_path != "/":
                await self._ensure_directory(dir_path)
            
            # Create tar archive with the file
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tarinfo = tarfile.TarInfo(name=os.path.basename(normalized_path))
                tarinfo.size = len(content)
                tarinfo.mtime = int(datetime.now().timestamp())
                tar.addfile(tarinfo, io.BytesIO(content))
            
            tar_stream.seek(0)
            
            # Upload to container
            success = self.container.put_archive(
                path=dir_path if dir_path else "/",
                data=tar_stream.getvalue()
            )
            
            if success:
                logger.debug(f"File uploaded successfully: {normalized_path}")
                return True
            else:
                logger.error(f"Failed to upload file: {normalized_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            return False
    
    async def download_file(self, file_path: str) -> bytes:
        """
        Download file content from the container.
        
        Args:
            file_path: Path to file in container
            
        Returns:
            bytes: File content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If download fails
        """
        try:
            normalized_path = self._normalize_path(file_path)
            
            # Check if file exists
            if not await self._file_exists(normalized_path):
                raise FileNotFoundError(f"File not found: {normalized_path}")
            
            # Get file from container as tar archive
            tar_stream, _ = self.container.get_archive(normalized_path)
            
            # Extract file content from tar
            tar_data = b''.join(tar_stream)
            tar_file = tarfile.open(fileobj=io.BytesIO(tar_data))
            
            # Get the first (and should be only) file from the archive
            members = tar_file.getmembers()
            if not members:
                raise RuntimeError(f"No content found in archive for: {normalized_path}")
            
            file_member = members[0]
            if file_member.isdir():
                raise RuntimeError(f"Path is a directory, not a file: {normalized_path}")
            
            # Extract file content
            file_obj = tar_file.extractfile(file_member)
            if file_obj is None:
                raise RuntimeError(f"Could not extract file content: {normalized_path}")
            
            content = file_obj.read()
            tar_file.close()
            
            logger.debug(f"File downloaded successfully: {normalized_path}")
            return content
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error downloading file {file_path}: {e}")
            raise RuntimeError(f"Download failed: {e}")
    
    async def list_files(self, directory_path: str = "/workspace") -> List[FileInfo]:
        """
        List files and directories in the specified path.
        
        Args:
            directory_path: Directory path to list
            
        Returns:
            List[FileInfo]: List of file information objects
        """
        try:
            normalized_path = self._normalize_path(directory_path)
            
            # Check if directory exists
            if not await self._directory_exists(normalized_path):
                raise FileNotFoundError(f"Directory not found: {normalized_path}")
            
            # Execute ls command to get file information
            exec_result = self.container.exec_run(
                f"ls -la --time-style=iso {normalized_path}",
                demux=True
            )
            
            if exec_result.exit_code != 0:
                error_msg = exec_result.output[1].decode() if exec_result.output[1] else "Unknown error"
                raise RuntimeError(f"Failed to list directory: {error_msg}")
            
            # Parse ls output
            output = exec_result.output[0].decode() if exec_result.output[0] else ""
            files = self._parse_ls_output(output, normalized_path)
            
            logger.debug(f"Listed {len(files)} items in directory: {normalized_path}")
            return files
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error listing directory {directory_path}: {e}")
            raise RuntimeError(f"Directory listing failed: {e}")
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file or directory from the container.
        
        Args:
            file_path: Path to file or directory to delete
            
        Returns:
            bool: True if deletion successful
        """
        try:
            normalized_path = self._normalize_path(file_path)
            
            # Check if file/directory exists
            if not await self._path_exists(normalized_path):
                logger.warning(f"Path does not exist: {normalized_path}")
                return True  # Consider non-existent as successfully deleted
            
            # Execute rm command
            exec_result = self.container.exec_run(f"rm -rf {normalized_path}")
            
            if exec_result.exit_code == 0:
                logger.debug(f"Path deleted successfully: {normalized_path}")
                return True
            else:
                error_msg = exec_result.output.decode() if exec_result.output else "Unknown error"
                logger.error(f"Failed to delete path {normalized_path}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting path {file_path}: {e}")
            return False
    
    async def create_directory(self, directory_path: str) -> bool:
        """
        Create a directory in the container.
        
        Args:
            directory_path: Directory path to create
            
        Returns:
            bool: True if creation successful
        """
        try:
            normalized_path = self._normalize_path(directory_path)
            return await self._ensure_directory(normalized_path)
        except Exception as e:
            logger.error(f"Error creating directory {directory_path}: {e}")
            return False
    
    async def copy_file(self, source_path: str, destination_path: str) -> bool:
        """
        Copy a file within the container.
        
        Args:
            source_path: Source file path
            destination_path: Destination file path
            
        Returns:
            bool: True if copy successful
        """
        try:
            source_normalized = self._normalize_path(source_path)
            dest_normalized = self._normalize_path(destination_path)
            
            # Check if source exists
            if not await self._path_exists(source_normalized):
                raise FileNotFoundError(f"Source path not found: {source_normalized}")
            
            # Ensure destination directory exists
            dest_dir = os.path.dirname(dest_normalized)
            if dest_dir and dest_dir != "/":
                await self._ensure_directory(dest_dir)
            
            # Execute cp command
            exec_result = self.container.exec_run(f"cp -r {source_normalized} {dest_normalized}")
            
            if exec_result.exit_code == 0:
                logger.debug(f"File copied successfully: {source_normalized} -> {dest_normalized}")
                return True
            else:
                error_msg = exec_result.output.decode() if exec_result.output else "Unknown error"
                logger.error(f"Failed to copy file: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error copying file {source_path} to {destination_path}: {e}")
            return False
    
    async def move_file(self, source_path: str, destination_path: str) -> bool:
        """
        Move a file within the container.
        
        Args:
            source_path: Source file path
            destination_path: Destination file path
            
        Returns:
            bool: True if move successful
        """
        try:
            source_normalized = self._normalize_path(source_path)
            dest_normalized = self._normalize_path(destination_path)
            
            # Check if source exists
            if not await self._path_exists(source_normalized):
                raise FileNotFoundError(f"Source path not found: {source_normalized}")
            
            # Ensure destination directory exists
            dest_dir = os.path.dirname(dest_normalized)
            if dest_dir and dest_dir != "/":
                await self._ensure_directory(dest_dir)
            
            # Execute mv command
            exec_result = self.container.exec_run(f"mv {source_normalized} {dest_normalized}")
            
            if exec_result.exit_code == 0:
                logger.debug(f"File moved successfully: {source_normalized} -> {dest_normalized}")
                return True
            else:
                error_msg = exec_result.output.decode() if exec_result.output else "Unknown error"
                logger.error(f"Failed to move file: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error moving file {source_path} to {destination_path}: {e}")
            return False
    
    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """
        Get detailed information about a file or directory.
        
        Args:
            file_path: Path to file or directory
            
        Returns:
            FileInfo or None if not found
        """
        try:
            normalized_path = self._normalize_path(file_path)
            
            # Execute stat command to get file information
            exec_result = self.container.exec_run(
                f"stat -c '%n|%s|%Y|%A|%U' {normalized_path}",
                demux=True
            )
            
            if exec_result.exit_code != 0:
                return None
            
            output = exec_result.output[0].decode().strip() if exec_result.output[0] else ""
            if not output:
                return None
            
            # Parse stat output
            parts = output.split('|')
            if len(parts) != 5:
                return None
            
            name = os.path.basename(parts[0])
            size = int(parts[1])
            mod_time = datetime.fromtimestamp(int(parts[2])).isoformat()
            permissions = parts[3]
            owner = parts[4]
            is_dir = permissions.startswith('d')
            
            return FileInfo(
                name=name,
                path=normalized_path,
                is_dir=is_dir,
                size=size,
                mod_time=mod_time,
                permissions=permissions,
                owner=owner
            )
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize and validate file path.
        
        Args:
            path: Input path
            
        Returns:
            str: Normalized path
        """
        # Remove any dangerous path components
        normalized = os.path.normpath(path)
        
        # Ensure path is within workspace or is absolute
        if not normalized.startswith('/'):
            normalized = os.path.join(self.workspace_path, normalized)
        
        # Prevent directory traversal attacks
        if '..' in normalized:
            raise ValueError(f"Invalid path (contains '..'): {path}")
        
        return normalized
    
    async def _file_exists(self, file_path: str) -> bool:
        """Check if a file exists in the container"""
        exec_result = self.container.exec_run(f"test -f {file_path}")
        return exec_result.exit_code == 0
    
    async def _directory_exists(self, directory_path: str) -> bool:
        """Check if a directory exists in the container"""
        exec_result = self.container.exec_run(f"test -d {directory_path}")
        return exec_result.exit_code == 0
    
    async def _path_exists(self, path: str) -> bool:
        """Check if a path (file or directory) exists in the container"""
        exec_result = self.container.exec_run(f"test -e {path}")
        return exec_result.exit_code == 0
    
    async def _ensure_directory(self, directory_path: str) -> bool:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory_path: Directory path to ensure
            
        Returns:
            bool: True if directory exists or was created successfully
        """
        try:
            # Check if directory already exists
            if await self._directory_exists(directory_path):
                return True
            
            # Create directory
            exec_result = self.container.exec_run(f"mkdir -p {directory_path}")
            
            if exec_result.exit_code == 0:
                logger.debug(f"Directory created: {directory_path}")
                return True
            else:
                error_msg = exec_result.output.decode() if exec_result.output else "Unknown error"
                logger.error(f"Failed to create directory {directory_path}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring directory {directory_path}: {e}")
            return False
    
    def _parse_ls_output(self, output: str, base_path: str) -> List[FileInfo]:
        """
        Parse ls -la output into FileInfo objects.
        
        Args:
            output: ls command output
            base_path: Base directory path
            
        Returns:
            List[FileInfo]: Parsed file information
        """
        files = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line or line.startswith('total'):
                continue
            
            # Skip current and parent directory entries
            if line.endswith(' .') or line.endswith(' ..'):
                continue
            
            try:
                # Parse ls -la output format
                parts = line.split(None, 8)
                if len(parts) < 9:
                    continue
                
                permissions = parts[0]
                size = int(parts[4]) if parts[4].isdigit() else 0
                
                # Date and time parsing (ISO format from --time-style=iso)
                date_part = parts[5]
                time_part = parts[6]
                mod_time = f"{date_part}T{time_part}"
                
                name = parts[8]
                is_dir = permissions.startswith('d')
                
                # Construct full path
                if base_path.endswith('/'):
                    full_path = f"{base_path}{name}"
                else:
                    full_path = f"{base_path}/{name}"
                
                file_info = FileInfo(
                    name=name,
                    path=full_path,
                    is_dir=is_dir,
                    size=size,
                    mod_time=mod_time,
                    permissions=permissions,
                    owner=f"{parts[2]}:{parts[3]}"
                )
                
                files.append(file_info)
                
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse ls line: {line} - {e}")
                continue
        
        return files