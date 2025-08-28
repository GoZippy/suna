# Suna Agent Sandbox Container

This directory contains the Docker configuration for creating agent sandbox containers that replace the Daytona functionality with local container orchestration.

## Features

- **Base OS**: Ubuntu 22.04 LTS
- **Python**: 3.11+ with common development packages
- **Node.js**: 20+ with npm, yarn, pnpm
- **VNC Server**: TigerVNC with XFCE4 desktop environment
- **Web VNC**: noVNC for browser-based desktop access
- **Browser Automation**: Playwright and Selenium with browser drivers
- **Process Management**: Supervisor for managing services
- **Security**: Non-root user configuration and container hardening

## Quick Start

### Building the Container

```bash
# Check available ports first (optional)
python find_ports.py

# On Linux/macOS
./build.sh

# On Windows
.\build.ps1
```

### Running the Container

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Using Docker directly
docker run -d \
  -p 5901:5901 \
  -p 8080:8080 \
  -p 3000:3000 \
  -p 8000:8000 \
  --name suna-sandbox \
  suna/agent-sandbox:latest
```

### Accessing the Container

#### VNC Access
- **Desktop VNC Client**: `localhost:5901`
- **Web VNC Interface**: `http://localhost:6080/vnc.html`
- **Password**: `suna123`
- **Resolution**: 1920x1080

#### Shell Access
```bash
docker exec -it suna-sandbox /bin/bash
```

## Container Configuration

### Installed Software

#### Development Tools
- Git, Vim, Nano, Htop, Tree
- Build essentials (gcc, g++, make, cmake)
- Python 3.11 with pip, virtualenv, poetry
- Node.js 20 with npm, yarn, pnpm

#### Python Packages
- Web frameworks: FastAPI, Flask, Django
- Testing: pytest, black, flake8, mypy
- Data science: pandas, numpy, matplotlib
- Automation: selenium, playwright, requests

#### Node.js Packages
- TypeScript, ts-node, nodemon
- Framework CLIs: create-react-app, @vue/cli, @angular/cli
- Build tools: webpack, vite
- Code quality: eslint, prettier

#### Browser Automation
- Playwright with Chromium, Firefox, WebKit
- Selenium WebDriver
- All necessary browser dependencies

### Security Features

- **Non-root user**: All processes run as `suna` user
- **Limited privileges**: Container runs with minimal required capabilities
- **Isolated filesystem**: Workspace mounted as volume
- **Network isolation**: Custom Docker network for sandbox containers

### Process Management

Supervisor manages the following services:
- **VNC Server**: TigerVNC on display :1
- **noVNC**: Web-based VNC client on port 6080
- **D-Bus**: System message bus for desktop environment

## Usage Examples

### Web Development
```bash
# Access the container
docker exec -it suna-sandbox /bin/bash

# Create a React app
cd /workspace
npx create-react-app my-app
cd my-app
npm start  # Accessible at localhost:3000
```

### Python Development
```bash
# Access the container
docker exec -it suna-sandbox /bin/bash

# Create a FastAPI app
cd /workspace
pip install fastapi uvicorn
# Create your app and run with: uvicorn main:app --host 0.0.0.0 --port 8000
```

### Browser Automation
```bash
# Access the container
docker exec -it suna-sandbox /bin/bash

# Run Playwright script
cd /workspace
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com')
    print(page.title())
    browser.close()
"
```

## Environment Variables

- `DISPLAY=:1` - VNC display
- `HOME=/home/suna` - User home directory
- `USER=suna` - Username
- `SHELL=/bin/bash` - Default shell

## Ports

Default host ports (using "17" pattern to avoid conflicts):
- `5917` - VNC server (maps to container port 5901)
- `6017` - noVNC web interface (maps to container port 6080)
- `8117` - General development server (maps to container port 8080)
- `3017` - React/Next.js default port (maps to container port 3000)
- `8017` - FastAPI/Django default port (maps to container port 8000)

**Note**: Use `python find_ports.py` to check available ports and get recommended mappings for your system.

## Volumes

- `/workspace` - Main working directory (mounted as volume)
- `/home/suna` - User home directory

## Troubleshooting

### VNC Connection Issues
1. Ensure port 5901 is not blocked by firewall
2. Check if VNC server is running: `docker exec suna-sandbox ps aux | grep vnc`
3. Restart VNC service: `docker exec suna-sandbox supervisorctl restart vnc`

### Browser Automation Issues
1. Ensure container has sufficient shared memory: `--shm-size=2gb`
2. Check if browsers are installed: `docker exec suna-sandbox playwright --version`
3. For headless mode issues, use VNC to debug visually

### Permission Issues
1. All files in `/workspace` should be owned by `suna:suna`
2. Use `docker exec -u suna suna-sandbox` to ensure correct user context

## Integration with Suna

This container is designed to be managed by the Suna backend's container orchestration system. The backend will:

1. Create containers dynamically for each agent session
2. Mount project-specific volumes to `/workspace`
3. Manage container lifecycle (start, stop, cleanup)
4. Provide VNC access through the web interface
5. Handle file operations and code execution

## Security Considerations

- Container runs with non-root user by default
- Limited system capabilities
- Network isolation from host system
- Regular security updates for base image
- Sandboxed browser execution
- Resource limits to prevent abuse

## Customization

To customize the container for specific use cases:

1. Modify `Dockerfile` to add/remove packages
2. Update `supervisord.conf` to manage additional services
3. Adjust `docker-compose.yml` for different port mappings
4. Create specialized images for different development stacks