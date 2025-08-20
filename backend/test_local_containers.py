#!/usr/bin/env python3
"""
Test script for local container orchestration system.

This script tests the basic functionality of the local Docker-based
container management system that replaces Daytona.
"""

import asyncio
import sys
import os
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.local_container_manager import LocalContainerManager, ContainerResources
from services.container_filesystem import ContainerFileSystem
from utils.logger import logger


async def test_container_lifecycle():
    """Test basic container lifecycle operations"""
    print("🧪 Testing container lifecycle...")
    
    manager = LocalContainerManager()
    project_id = "test-project-123"
    
    try:
        # Test container creation
        print("  ✅ Creating container...")
        container_info = await manager.create_container(
            project_id=project_id,
            vnc_password="testpass123"
        )
        print(f"  ✅ Container created: {container_info.container_id}")
        
        # Test container info retrieval
        print("  ✅ Getting container info...")
        retrieved_info = await manager.get_container_info(project_id)
        assert retrieved_info is not None
        assert retrieved_info.project_id == project_id
        print(f"  ✅ Container info retrieved: {retrieved_info.state}")
        
        # Test container listing
        print("  ✅ Listing containers...")
        containers = await manager.list_containers()
        assert len(containers) >= 1
        print(f"  ✅ Found {len(containers)} containers")
        
        # Test VNC and HTTP URLs
        vnc_url = manager.get_vnc_url(project_id)
        http_url = manager.get_http_url(project_id)
        print(f"  ✅ VNC URL: {vnc_url}")
        print(f"  ✅ HTTP URL: {http_url}")
        
        return container_info
        
    except Exception as e:
        print(f"  ❌ Container lifecycle test failed: {e}")
        raise


async def test_file_operations(container_info):
    """Test file system operations within container"""
    print("🧪 Testing file operations...")
    
    manager = LocalContainerManager()
    
    try:
        # Get Docker container
        docker_container = manager.docker_client.containers.get(container_info.container_id)
        fs = ContainerFileSystem(docker_container)
        
        # Test file upload
        print("  ✅ Testing file upload...")
        test_content = b"Hello, World! This is a test file."
        test_path = "/workspace/test_file.txt"
        
        success = await fs.upload_file(test_content, test_path)
        assert success, "File upload failed"
        print(f"  ✅ File uploaded to {test_path}")
        
        # Test file listing
        print("  ✅ Testing file listing...")
        files = await fs.list_files("/workspace")
        assert len(files) > 0, "No files found"
        
        # Find our test file
        test_file = None
        for file_info in files:
            if file_info.name == "test_file.txt":
                test_file = file_info
                break
        
        assert test_file is not None, "Test file not found in listing"
        print(f"  ✅ Found test file: {test_file.name} ({test_file.size} bytes)")
        
        # Test file download
        print("  ✅ Testing file download...")
        downloaded_content = await fs.download_file(test_path)
        assert downloaded_content == test_content, "Downloaded content doesn't match"
        print(f"  ✅ File downloaded successfully ({len(downloaded_content)} bytes)")
        
        # Test directory creation
        print("  ✅ Testing directory creation...")
        test_dir = "/workspace/test_directory"
        success = await fs.create_directory(test_dir)
        assert success, "Directory creation failed"
        print(f"  ✅ Directory created: {test_dir}")
        
        # Test file copy
        print("  ✅ Testing file copy...")
        copy_path = "/workspace/test_directory/copied_file.txt"
        success = await fs.copy_file(test_path, copy_path)
        assert success, "File copy failed"
        print(f"  ✅ File copied to {copy_path}")
        
        # Test file info
        print("  ✅ Testing file info...")
        file_info = await fs.get_file_info(test_path)
        assert file_info is not None, "File info retrieval failed"
        print(f"  ✅ File info: {file_info.name}, {file_info.size} bytes, {file_info.permissions}")
        
        # Test file deletion
        print("  ✅ Testing file deletion...")
        success = await fs.delete_file(copy_path)
        assert success, "File deletion failed"
        print(f"  ✅ File deleted: {copy_path}")
        
        # Cleanup test file
        await fs.delete_file(test_path)
        await fs.delete_file(test_dir)
        
    except Exception as e:
        print(f"  ❌ File operations test failed: {e}")
        raise


async def test_container_management():
    """Test container start/stop/restart operations"""
    print("🧪 Testing container management...")
    
    manager = LocalContainerManager()
    project_id = "test-project-123"
    
    try:
        # Test container stop
        print("  ✅ Stopping container...")
        success = await manager.stop_container(project_id)
        assert success, "Container stop failed"
        print("  ✅ Container stopped")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Test container start
        print("  ✅ Starting container...")
        container_info = await manager.start_container(project_id)
        assert container_info.state.value == "running", "Container not running after start"
        print("  ✅ Container started")
        
        # Test container restart
        print("  ✅ Restarting container...")
        container_info = await manager.restart_container(project_id)
        assert container_info.state.value == "running", "Container not running after restart"
        print("  ✅ Container restarted")
        
    except Exception as e:
        print(f"  ❌ Container management test failed: {e}")
        raise


async def cleanup_test_containers():
    """Clean up test containers"""
    print("🧹 Cleaning up test containers...")
    
    manager = LocalContainerManager()
    project_id = "test-project-123"
    
    try:
        success = await manager.delete_container(project_id)
        if success:
            print("  ✅ Test container deleted")
        else:
            print("  ⚠️  Test container deletion failed (may not exist)")
            
    except Exception as e:
        print(f"  ⚠️  Cleanup failed: {e}")


async def main():
    """Run all tests"""
    print("🚀 Starting local container orchestration tests...\n")
    
    try:
        # Test container lifecycle
        container_info = await test_container_lifecycle()
        print()
        
        # Wait for container to be fully ready
        print("⏳ Waiting for container to be ready...")
        await asyncio.sleep(10)
        print()
        
        # Test file operations
        await test_file_operations(container_info)
        print()
        
        # Test container management
        await test_container_management()
        print()
        
        print("✅ All tests passed! Local container orchestration is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        return 1
        
    finally:
        # Always cleanup
        await cleanup_test_containers()
        print()
    
    return 0


if __name__ == "__main__":
    # Check if Docker is available
    try:
        import docker
        client = docker.from_env()
        client.ping()
        print("✅ Docker is available and running")
    except Exception as e:
        print(f"❌ Docker is not available: {e}")
        print("Please ensure Docker is installed and running.")
        sys.exit(1)
    
    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)