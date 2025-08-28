#!/usr/bin/env python3
"""
Generate docker-compose.yml with available ports
"""

import yaml
from find_ports import find_sandbox_ports

def generate_compose_config():
    """Generate docker-compose configuration with available ports"""
    
    # Find available ports
    ports = find_sandbox_ports()
    
    if not all(ports.values()):
        print("Error: Could not find available ports for all services")
        return None
    
    # Base docker-compose configuration
    config = {
        'services': {
            'agent-sandbox': {
                'build': {
                    'context': '.',
                    'dockerfile': 'Dockerfile'
                },
                'image': 'suna/agent-sandbox:latest',
                'container_name': 'suna-agent-sandbox',
                'ports': [
                    f"{ports['VNC']}:5901",  # VNC server
                    f"{ports['noVNC']}:6080",  # noVNC web interface
                    f"{ports['Dev-General']}:8080",  # Development server port
                    f"{ports['Dev-React']}:3000",  # React/Next.js default port
                    f"{ports['Dev-FastAPI']}:8000",  # FastAPI/Django default port
                ],
                'volumes': [
                    'sandbox_workspace:/workspace',
                    '/var/run/docker.sock:/var/run/docker.sock'
                ],
                'environment': [
                    'DISPLAY=:1',
                    'VNC_PASSWORD=suna123'
                ],
                'security_opt': [
                    'seccomp:unconfined'
                ],
                'cap_add': [
                    'SYS_ADMIN'
                ],
                'shm_size': '2gb',
                'restart': 'unless-stopped',
                'networks': [
                    'sandbox-network'
                ]
            }
        },
        'networks': {
            'sandbox-network': {
                'driver': 'bridge'
            }
        },
        'volumes': {
            'sandbox_workspace': {
                'driver': 'local'
            }
        }
    }
    
    return config, ports

def main():
    print("Generating docker-compose.yml with available ports...")
    
    config, ports = generate_compose_config()
    if not config:
        return 1
    
    # Write the configuration
    with open('docker-compose.generated.yml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("Generated docker-compose.generated.yml")
    print("\nPort mappings:")
    for service, port in ports.items():
        print(f"  {service}: {port}")
    
    print("\nTo use the generated file:")
    print("  docker-compose -f docker-compose.generated.yml up -d")
    
    print("\nAccess URLs:")
    print(f"  VNC Desktop: localhost:{ports['VNC']} (password: suna123)")
    print(f"  Web VNC:     http://localhost:{ports['noVNC']}/vnc.html")
    print(f"  React App:   http://localhost:{ports['Dev-React']}")
    print(f"  FastAPI:     http://localhost:{ports['Dev-FastAPI']}")
    print(f"  General:     http://localhost:{ports['Dev-General']}")
    
    return 0

if __name__ == "__main__":
    exit(main())