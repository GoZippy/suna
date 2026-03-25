"""
Container Manager for Suna Agent Sandbox Containers
Provides programmatic interface for managing sandbox containers
"""

import docker
import logging
import time
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from find_ports import find_available_port_with_pattern

@dataclass
class SandboxConfig:
    """Configuration for a sandbox container"""
    project_id: str
    user_id: str
    memory_limit: str = "2g"
    cpu_count: int = 2
    vnc_port: Optional[int] = None
    dev_ports: List[int] = None
    environment: Dict[str, str] = None
    volumes: Dict[str, str] = None

class SandboxManager:
    """Manages agent sandbox containers"""
    
    def __init__(self, base_image: str = "suna/agent-sandbox:latest"):
        self.docker_client = docker.from_env()
        self.base_image = base_image
        self.logger = logging.getLogger(__name__)
        self.active_containers: Dict[str, docker.models.containers.Container] = {}
        
    def create_sandbox(self, config: SandboxConfig) -> Tuple[str, Dict[str, int]]:
        """
        Create a new sandbox container
        
        Args:
            config: Sandbox configuration
            
        Returns:
            Tuple of (container_id, port_mappings)
        """
        container_name = f"suna-sandbox-{config.project_id}-{uuid.uuid4().hex[:8]}"
        
        # Prepare port mappings
        port_mappings = {}
        
        # VNC port - try preferred pattern first
        vnc_port = config.vnc_port or find_available_port_with_pattern(5991)
        port_mappings["5901/tcp"] = vnc_port
        
        # noVNC web interface port
        novnc_port = find_available_port_with_pattern(6091)
        port_mappings["6080/tcp"] = novnc_port
        
        # Development ports
        dev_ports = config.dev_ports or [3091, 8091, 8080]
        for i, port in enumerate(dev_ports):
            # Use pattern like 3091, 8091, 8191 for host ports
            preferred_host_port = int(f"{port // 1000}{(port % 1000) // 100}91")
            if preferred_host_port == port:  # Avoid same port
                preferred_host_port += 1000
            host_port = find_available_port_with_pattern(preferred_host_port)
            port_mappings[f"{port}/tcp"] = host_port
        
        # Prepare volumes
        volumes = {
            f"sandbox_{config.project_id}": {"bind": "/workspace", "mode": "rw"}
        }
        if config.volumes:
            volumes.update(config.volumes)
        
        # Prepare environment variables
        environment = {
            "DISPLAY": ":1",
            "PROJECT_ID": config.project_id,
            "USER_ID": config.user_id,
            "VNC_PASSWORD": "suna123"
        }
        if config.environment:
            environment.update(config.environment)
        
        try:
            # Create and start container
            container = self.docker_client.containers.run(
                image=self.base_image,
                name=container_name,
                detach=True,
                mem_limit=config.memory_limit,
                cpu_count=config.cpu_count,
                ports=port_mappings,
                volumes=volumes,
                environment=environment,
                security_opt=["seccomp:unconfined"],
                cap_add=["SYS_ADMIN"],
                shm_size="2gb",
                network_mode="bridge",
                restart_policy={"Name": "unless-stopped"}
            )
            
            # Wait for container to be ready
            self._wait_for_container_ready(container)
            
            # Store container reference
            self.active_containers[container.id] = container
            
            self.logger.info(f"Created sandbox container {container.id} for project {config.project_id}")
            
            return container.id, {str(k): v for k, v in port_mappings.items()}
            
        except Exception as e:
            self.logger.error(f"Failed to create sandbox container: {e}")
            raise
    
    def stop_sandbox(self, container_id: str) -> bool:
        """
        Stop a sandbox container
        
        Args:
            container_id: Container ID to stop
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if container_id in self.active_containers:
                container = self.active_containers[container_id]
            else:
                container = self.docker_client.containers.get(container_id)
            
            container.stop(timeout=30)
            
            if container_id in self.active_containers:
                del self.active_containers[container_id]
            
            self.logger.info(f"Stopped sandbox container {container_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop container {container_id}: {e}")
            return False
    
    def remove_sandbox(self, container_id: str, remove_volumes: bool = False) -> bool:
        """
        Remove a sandbox container
        
        Args:
            container_id: Container ID to remove
            remove_volumes: Whether to remove associated volumes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Stop container first if running
            self.stop_sandbox(container_id)
            
            # Get container
            try:
                container = self.docker_client.containers.get(container_id)
                container.remove(v=remove_volumes)
            except docker.errors.NotFound:
                pass  # Container already removed
            
            self.logger.info(f"Removed sandbox container {container_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove container {container_id}: {e}")
            return False
    
    def get_container_status(self, container_id: str) -> Optional[Dict]:
        """
        Get status information for a container
        
        Args:
            container_id: Container ID
            
        Returns:
            Dictionary with status information or None if not found
        """
        try:
            container = self.docker_client.containers.get(container_id)
            
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "created": container.attrs["Created"],
                "ports": container.ports,
                "image": container.image.tags[0] if container.image.tags else "unknown"
            }
            
        except docker.errors.NotFound:
            return None
        except Exception as e:
            self.logger.error(f"Failed to get container status {container_id}: {e}")
            return None
    
    def list_sandboxes(self, project_id: Optional[str] = None) -> List[Dict]:
        """
        List all sandbox containers
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            List of container information dictionaries
        """
        try:
            filters = {"ancestor": self.base_image}
            if project_id:
                filters["label"] = f"project_id={project_id}"
            
            containers = self.docker_client.containers.list(all=True, filters=filters)
            
            result = []
            for container in containers:
                info = {
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "created": container.attrs["Created"],
                    "ports": container.ports,
                    "project_id": container.attrs.get("Config", {}).get("Env", {}).get("PROJECT_ID"),
                    "user_id": container.attrs.get("Config", {}).get("Env", {}).get("USER_ID")
                }
                result.append(info)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to list containers: {e}")
            return []
    
    def execute_command(self, container_id: str, command: str, user: str = "suna") -> Tuple[int, str]:
        """
        Execute a command in a container
        
        Args:
            container_id: Container ID
            command: Command to execute
            user: User to run command as
            
        Returns:
            Tuple of (exit_code, output)
        """
        try:
            container = self.docker_client.containers.get(container_id)
            
            result = container.exec_run(
                command,
                user=user,
                workdir="/workspace"
            )
            
            return result.exit_code, result.output.decode("utf-8")
            
        except Exception as e:
            self.logger.error(f"Failed to execute command in container {container_id}: {e}")
            return 1, str(e)
    
    def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """
        Get logs from a container
        
        Args:
            container_id: Container ID
            tail: Number of lines to return
            
        Returns:
            Container logs as string
        """
        try:
            container = self.docker_client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode("utf-8")
            
        except Exception as e:
            self.logger.error(f"Failed to get logs for container {container_id}: {e}")
            return f"Error getting logs: {e}"
    
    def _find_available_port(self, preferred_port: int) -> int:
        """Find an available port starting from preferred_port"""
        import socket
        
        port = preferred_port
        while port < preferred_port + 1000:  # Try up to 1000 ports
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                port += 1
        
        raise RuntimeError(f"No available ports found starting from {preferred_port}")
    
    def _find_available_port_with_pattern(self, preferred_port: int) -> int:
        """Find an available port, preferring the 17 pattern"""
        import socket
        
        # Try the preferred port first
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', preferred_port))
                return preferred_port
        except OSError:
            pass
        
        # If preferred port is not available, try other ports ending in 17
        base = preferred_port // 100 * 100
        for offset in range(1, 100):  # Try x91, x+191, x+291, etc.
            port = base + (offset * 100) + 91
            if port > 65535:  # Max port number
                break
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        
        # Fallback to any available port
        return self._find_available_port(preferred_port)
    
    def _wait_for_container_ready(self, container, timeout: int = 60):
        """Wait for container to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container.reload()
                if container.status == "running":
                    # Check if VNC server is running
                    result = container.exec_run("pgrep Xtigervnc", user="suna")
                    if result.exit_code == 0:
                        return True
                
                time.sleep(2)
                
            except Exception as e:
                self.logger.warning(f"Error checking container readiness: {e}")
                time.sleep(2)
        
        raise TimeoutError(f"Container did not become ready within {timeout} seconds")
    
    def cleanup_stopped_containers(self):
        """Remove all stopped sandbox containers"""
        try:
            containers = self.docker_client.containers.list(
                all=True,
                filters={"ancestor": self.base_image, "status": "exited"}
            )
            
            for container in containers:
                try:
                    container.remove()
                    self.logger.info(f"Cleaned up stopped container {container.id}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove container {container.id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup containers: {e}")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = SandboxManager()
    
    # Create a test sandbox
    config = SandboxConfig(
        project_id="test-project-123",
        user_id="user-456",
        dev_ports=[3091, 8091]
    )
    
    try:
        container_id, ports = manager.create_sandbox(config)
        print(f"Created container {container_id}")
        print(f"Port mappings: {ports}")
        
        # Get status
        status = manager.get_container_status(container_id)
        print(f"Status: {status}")
        
        # Execute a test command
        exit_code, output = manager.execute_command(container_id, "python3 --version")
        print(f"Python version: {output}")
        
        # Clean up
        input("Press Enter to stop and remove the container...")
        manager.remove_sandbox(container_id)
        
    except Exception as e:
        print(f"Error: {e}")