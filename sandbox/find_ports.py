#!/usr/bin/env python3
"""
Port finder utility for Suna sandbox containers
Finds available ports using the preferred "17" pattern
"""

import socket
from typing import List, Dict

def is_port_available(port: int) -> bool:
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False

def find_available_port_with_pattern(preferred_port: int) -> int:
    """Find an available port, preferring the 17 pattern"""
    # Try the preferred port first
    if is_port_available(preferred_port):
        return preferred_port
    
    # If preferred port is not available, try other ports ending in 91
    base = preferred_port // 100 * 100
    for offset in range(1, 100):  # Try x91, x+191, x+291, etc.
        port = base + (offset * 100) + 91
        if port > 65535:  # Max port number
            break
        if is_port_available(port):
            return port
    
    # Fallback to sequential search from preferred port
    port = preferred_port
    while port < preferred_port + 1000:
        if is_port_available(port):
            return port
        port += 1
    
    raise RuntimeError(f"No available ports found starting from {preferred_port}")

def find_sandbox_ports() -> Dict[str, int]:
    """Find available ports for sandbox services"""
    services = {
        "VNC": 5991,
        "noVNC": 6091,
        "Dev-React": 3091,
        "Dev-FastAPI": 8091,
        "Dev-General": 8191
    }
    
    available_ports = {}
    for service, preferred_port in services.items():
        try:
            port = find_available_port_with_pattern(preferred_port)
            available_ports[service] = port
        except RuntimeError as e:
            print(f"Warning: {e}")
            available_ports[service] = None
    
    return available_ports

def check_common_ports() -> List[int]:
    """Check which common development ports are in use"""
    common_ports = [3091, 3191, 5901, 6080, 8091, 8080, 8081, 5991, 6091, 8191]
    used_ports = []
    
    for port in common_ports:
        if not is_port_available(port):
            used_ports.append(port)
    
    return used_ports

def main():
    print("Suna Sandbox Port Finder")
    print("=" * 40)
    
    # Check which common ports are in use
    used_ports = check_common_ports()
    if used_ports:
        print(f"Ports currently in use: {', '.join(map(str, used_ports))}")
    else:
        print("All common development ports are available")
    
    print()
    
    # Find available ports for sandbox services
    print("Recommended ports for sandbox services:")
    available_ports = find_sandbox_ports()
    
    for service, port in available_ports.items():
        if port:
            status = "✓ Available"
            if not is_port_available(port):
                status = "✗ In use (race condition)"
        else:
            status = "✗ No available port found"
        
        print(f"  {service:12} : {port or 'N/A':>5} {status}")
    
    print()
    
    # Generate docker-compose port mappings
    if all(available_ports.values()):
        print("Docker Compose port mappings:")
        print(f'      - "{available_ports["VNC"]}:5901"  # VNC server')
        print(f'      - "{available_ports["noVNC"]}:6080"  # noVNC web interface')
        print(f'      - "{available_ports["Dev-General"]}:8080"  # Development server port')
        print(f'      - "{available_ports["Dev-React"]}:3000"  # React/Next.js default port')
        print(f'      - "{available_ports["Dev-FastAPI"]}:8000"  # FastAPI/Django default port')
        
        print()
        print("Access URLs:")
        print(f"  VNC Desktop: localhost:{available_ports['VNC']} (password: suna123)")
        print(f"  Web VNC:     http://localhost:{available_ports['noVNC']}/vnc.html")
        print(f"  React App:   http://localhost:{available_ports['Dev-React']}")
        print(f"  FastAPI:     http://localhost:{available_ports['Dev-FastAPI']}")
        print(f"  General:     http://localhost:{available_ports['Dev-General']}")

if __name__ == "__main__":
    main()