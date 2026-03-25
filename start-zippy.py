#!/usr/bin/env python3
"""
Zippy Suna Smart Startup Script
Detects existing local services and intelligently starts only needed containers.
"""

import os
import sys
import subprocess
import socket
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import docker
from docker.errors import DockerException

class ServiceDetector:
    """Detects running services on the local machine"""
    
    def __init__(self):
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except DockerException:
            print("⚠️  Docker not available - will only check local services")
    
    def check_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result != 0
        except:
            return True
    
    def check_local_postgres(self) -> Tuple[bool, str]:
        """Check if PostgreSQL is running locally"""
        ports = [5432, 5433, 5434, 5435]
        for port in ports:
            if not self.check_port_available(port):
                try:
                    # Try to connect to PostgreSQL
                    import psycopg2
                    conn = psycopg2.connect(
                        host='localhost',
                        port=port,
                        database='postgres',
                        user='postgres',
                        password='',
                        connect_timeout=3
                    )
                    conn.close()
                    return True, f"localhost:{port}"
                except:
                    continue
        return False, ""
    
    def check_local_redis(self) -> Tuple[bool, str]:
        """Check if Redis is running locally"""
        ports = [6379, 6380, 6381, 6382]
        for port in ports:
            if not self.check_port_available(port):
                try:
                    import redis
                    r = redis.Redis(host='localhost', port=port, socket_connect_timeout=3)
                    r.ping()
                    return True, f"localhost:{port}"
                except:
                    continue
        return False, ""
    
    def check_local_ollama(self) -> Tuple[bool, str]:
        """Check if Ollama is running locally"""
        if not self.check_port_available(11434):
            try:
                import requests
                response = requests.get('http://localhost:11434/api/tags', timeout=3)
                if response.status_code == 200:
                    return True, "localhost:11434"
            except:
                pass
        return False, ""
    
    def check_project_containers(self) -> Dict[str, bool]:
        """Check if project-specific containers are already running"""
        if not self.docker_client:
            return {}
        
        project_containers = {
            'postgres': False,
            'redis': False,
            'ollama': False,
            'backend': False,
            'frontend': False
        }
        
        try:
            containers = self.docker_client.containers.list()
            for container in containers:
                name = container.name.lower()
                if 'suna' in name or 'zippy' in name:
                    if 'postgres' in name:
                        project_containers['postgres'] = True
                    elif 'redis' in name:
                        project_containers['redis'] = True
                    elif 'ollama' in name:
                        project_containers['ollama'] = True
                    elif 'backend' in name:
                        project_containers['backend'] = True
                    elif 'frontend' in name:
                        project_containers['frontend'] = True
        except:
            pass
        
        return project_containers

class SmartStartup:
    """Manages intelligent startup of Zippy Suna services"""
    
    def __init__(self):
        self.detector = ServiceDetector()
        self.project_dir = Path(__file__).parent
        self.compose_file = self.project_dir / "docker-compose.self-hosted.yml"
        self.env_file = self.project_dir / ".env"
        
    def detect_services(self) -> Dict[str, Dict]:
        """Detect all available services"""
        print("🔍 Detecting available services...")
        
        # Check local services
        local_postgres, postgres_url = self.detector.check_local_postgres()
        local_redis, redis_url = self.detector.check_local_redis()
        local_ollama, ollama_url = self.detector.check_local_ollama()
        
        # Check project containers
        project_containers = self.detector.check_project_containers()
        
        services = {
            'postgres': {
                'local': local_postgres,
                'local_url': postgres_url,
                'project_container': project_containers.get('postgres', False),
                'recommended': 'local' if local_postgres else 'container'
            },
            'redis': {
                'local': local_redis,
                'local_url': redis_url,
                'project_container': project_containers.get('redis', False),
                'recommended': 'local' if local_redis else 'container'
            },
            'ollama': {
                'local': local_ollama,
                'local_url': ollama_url,
                'project_container': project_containers.get('ollama', False),
                'recommended': 'local' if local_ollama else 'container'
            },
            'backend': {
                'project_container': project_containers.get('backend', False),
                'recommended': 'container'
            },
            'frontend': {
                'project_container': project_containers.get('frontend', False),
                'recommended': 'container'
            }
        }
        
        return services
    
    def display_service_status(self, services: Dict[str, Dict]):
        """Display current service status"""
        print("\n📊 Service Status:")
        print("=" * 60)
        
        for service, status in services.items():
            if service in ['postgres', 'redis', 'ollama']:
                local_status = "✅ Running" if status['local'] else "❌ Not Found"
                container_status = "✅ Running" if status['project_container'] else "❌ Not Running"
                recommended = status['recommended'].upper()
                
                print(f"{service.upper():<12} | Local: {local_status:<12} | Container: {container_status:<15} | Recommended: {recommended}")
                
                if status['local'] and status['local_url']:
                    print(f"{'':<12} | URL: {status['local_url']}")
            else:
                container_status = "✅ Running" if status['project_container'] else "❌ Not Running"
                print(f"{service.upper():<12} | Container: {container_status:<15} | Required: YES")
        
        print("=" * 60)
    
    def get_user_preferences(self, services: Dict[str, Dict]) -> Dict[str, str]:
        """Get user preferences for service usage"""
        preferences = {}
        
        print("\n🎯 Service Configuration:")
        print("Choose which services to use for each component:")
        
        for service in ['postgres', 'redis', 'ollama']:
            if services[service]['local']:
                print(f"\n{service.upper()}:")
                print(f"  Local service found at: {services[service]['local_url']}")
                print(f"  Project container: {'Running' if services[service]['project_container'] else 'Not running'}")
                
                while True:
                    choice = input(f"  Use local service? (y/n) [default: y]: ").strip().lower()
                    if choice in ['', 'y', 'yes']:
                        preferences[service] = 'local'
                        break
                    elif choice in ['n', 'no']:
                        preferences[service] = 'container'
                        break
                    else:
                        print("  Please enter 'y' or 'n'")
            else:
                print(f"\n{service.upper()}: No local service found - will use container")
                preferences[service] = 'container'
        
        return preferences
    
    def create_smart_compose_file(self, services: Dict[str, Dict], preferences: Dict[str, str]) -> str:
        """Create a smart docker-compose file based on user preferences"""
        print("\n🔧 Creating smart docker-compose configuration...")
        
        # Read the base compose file
        with open(self.compose_file, 'r') as f:
            compose_content = f.read()
        
        # Create a new compose file with only needed services
        smart_compose = "version: '3.8'\n\nservices:\n"
        
        # Always include core services
        core_services = ['postgres', 'redis', 'backend', 'frontend', 'worker']
        
        for service in core_services:
            if service in preferences:
                if preferences[service] == 'local':
                    print(f"  ⏭️  Skipping {service} container (using local service)")
                    continue
            
            # Extract service definition from base file
            service_start = compose_content.find(f"  {service}:")
            if service_start == -1:
                continue
                
            # Find the end of this service
            service_end = compose_content.find("\n  ", service_start + 1)
            if service_end == -1:
                service_end = len(compose_content)
            
            service_def = compose_content[service_start:service_end]
            smart_compose += service_def + "\n"
        
        # Add networks and volumes
        networks_start = compose_content.find("\nnetworks:")
        if networks_start != -1:
            smart_compose += compose_content[networks_start:]
        
        # Write the smart compose file
        smart_compose_file = self.project_dir / "docker-compose.smart.yml"
        with open(smart_compose_file, 'w') as f:
            f.write(smart_compose)
        
        print(f"  ✅ Created smart compose file: {smart_compose_file}")
        return str(smart_compose_file)
    
    def update_environment_config(self, services: Dict[str, Dict], preferences: Dict[str, str]):
        """Update environment configuration based on service choices"""
        print("\n⚙️  Updating environment configuration...")
        
        # Create/update main .env file
        if not self.env_file.exists():
            env_example = self.project_dir / "self-hosted.env.example"
            if env_example.exists():
                with open(env_example, 'r') as f:
                    env_content = f.read()
                
                # Update with local service URLs
                if preferences.get('postgres') == 'local':
                    postgres_url = services['postgres']['local_url']
                    env_content = env_content.replace(
                        'DATABASE_URL=postgresql://suna:your_super_secure_postgres_password_here@postgres:5432/suna',
                        f'DATABASE_URL=postgresql://postgres@localhost:{postgres_url.split(":")[1]}/suna'
                    )
                
                if preferences.get('redis') == 'local':
                    redis_url = services['redis']['local_url']
                    env_content = env_content.replace(
                        'REDIS_HOST=redis',
                        f'REDIS_HOST=localhost'
                    )
                    env_content = env_content.replace(
                        'REDIS_PORT=6379',
                        f'REDIS_PORT={redis_url.split(":")[1]}'
                    )
                
                if preferences.get('ollama') == 'local':
                    ollama_url = services['ollama']['local_url']
                    env_content = env_content.replace(
                        'OLLAMA_BASE_URL=http://ollama:11434',
                        f'OLLAMA_BASE_URL=http://{ollama_url}'
                    )
                
                # Update CORS origins
                env_content = env_content.replace(
                    'CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000", "http://suna.local:3000"]',
                    'CORS_ORIGINS=["http://localhost:18884", "http://127.0.0.1:18884"]'
                )
                
                with open(self.env_file, 'w') as f:
                    f.write(env_content)
                
                print("  ✅ Created .env file with local service configuration")
        
        # Update backend .env
        backend_env = self.project_dir / "backend" / ".env"
        if not backend_env.exists():
            backend_env_config = self.project_dir / "backend_env_config.txt"
            if backend_env_config.exists():
                with open(backend_env_config, 'r') as f:
                    backend_content = f.read()
                
                # Update backend configuration
                if preferences.get('ollama') == 'local':
                    ollama_url = services['ollama']['local_url']
                    backend_content = backend_content.replace(
                        'OLLAMA_BASE_URL=http://localhost:11434',
                        f'OLLAMA_BASE_URL=http://{ollama_url}'
                    )
                
                backend_content = backend_content.replace(
                    'CORS_ORIGINS=http://localhost:18884',
                    'CORS_ORIGINS=http://localhost:18884'
                )
                
                with open(backend_env, 'w') as f:
                    f.write(backend_content)
                
                print("  ✅ Created backend .env file")
    
    def start_services(self, smart_compose_file: str):
        """Start the configured services"""
        print("\n🚀 Starting Zippy Suna services...")
        
        try:
            # Stop any existing project containers
            subprocess.run([
                "docker-compose", "-f", smart_compose_file, "down"
            ], check=True, capture_output=True)
            
            # Start services
            subprocess.run([
                "docker-compose", "-f", smart_compose_file, "up", "-d", "--build"
            ], check=True)
            
            print("  ✅ Services started successfully!")
            
            # Show status
            subprocess.run([
                "docker-compose", "-f", smart_compose_file, "ps"
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Error starting services: {e}")
            print(f"  📋 Command output: {e.stderr.decode() if e.stderr else 'No output'}")
            return False
        
        return True
    
    def show_access_info(self, services: Dict[str, Dict], preferences: Dict[str, Dict]):
        """Show how to access the running services"""
        print("\n🌐 Access Information:")
        print("=" * 40)
        
        if preferences.get('frontend') != 'local':
            print("Frontend: http://localhost:18884")
        
        if preferences.get('backend') != 'local':
            print("Backend API: http://localhost:18883")
        
        if preferences.get('postgres') == 'container':
            print("PostgreSQL: localhost:18881")
        
        if preferences.get('redis') == 'container':
            print("Redis: localhost:18882")
        
        if preferences.get('ollama') == 'container':
            print("Ollama: localhost:18885")
        
        print("Monitoring: http://localhost:18888 (Prometheus)")
        print("Grafana: http://localhost:18889")
        print("MailHog: http://localhost:18887")
        
        print("\n📚 Next Steps:")
        print("1. Wait for all services to be healthy")
        print("2. Access the frontend at http://localhost:18884")
        print("3. Check logs: docker-compose -f docker-compose.smart.yml logs -f")
        print("4. Stop services: docker-compose -f docker-compose.smart.yml down")
    
    def run(self):
        """Main startup process"""
        print("🚀 Zippy Suna Smart Startup")
        print("=" * 40)
        
        # Check prerequisites
        if not self.compose_file.exists():
            print(f"❌ Docker compose file not found: {self.compose_file}")
            return False
        
        # Detect services
        services = self.detect_services()
        self.display_service_status(services)
        
        # Get user preferences
        preferences = self.get_user_preferences(services)
        
        # Create smart configuration
        smart_compose_file = self.create_smart_compose_file(services, preferences)
        
        # Update environment
        self.update_environment_config(services, preferences)
        
        # Start services
        if self.start_services(smart_compose_file):
            self.show_access_info(services, preferences)
            return True
        
        return False

def main():
    """Main entry point"""
    try:
        startup = SmartStartup()
        success = startup.run()
        
        if success:
            print("\n🎉 Zippy Suna startup completed successfully!")
        else:
            print("\n❌ Startup failed. Check the logs above for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Startup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
