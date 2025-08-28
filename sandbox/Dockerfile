# Agent Sandbox Container Image
# Base Ubuntu 22.04 with development tools, VNC server, and browser automation

FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Create non-root user for security
RUN groupadd -r suna && useradd -r -g suna -m -d /home/suna -s /bin/bash suna \
    && echo "suna:suna123" | chpasswd

# Install system packages and development tools
RUN apt-get update && apt-get install -y \
    # Basic system tools
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    tree \
    unzip \
    zip \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    # Build tools
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    pkg-config \
    # Python development
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    # VNC and desktop environment
    tigervnc-standalone-server \
    tigervnc-common \
    xfce4 \
    xfce4-goodies \
    dbus-x11 \
    # Web-based VNC access
    websockify \
    # Browser dependencies
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    # Process management
    supervisor \
    # Network tools
    net-tools \
    iputils-ping \
    # Additional development tools
    jq \
    sqlite3 \
    postgresql-client \
    redis-tools \
    # Security tools
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Configure sudo for suna user (limited permissions)
RUN echo "suna ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/pip3, /usr/bin/npm" >> /etc/sudoers.d/suna \
    && chmod 0440 /etc/sudoers.d/suna

# Install Node.js 20+
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Set up Python 3.11 as default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Install Python packages
RUN pip3 install --no-cache-dir \
    pip \
    setuptools \
    wheel \
    virtualenv \
    pipenv \
    poetry \
    # Development tools
    ipython \
    jupyter \
    pytest \
    black \
    flake8 \
    mypy \
    # Web development
    requests \
    beautifulsoup4 \
    selenium \
    playwright \
    # Data science basics
    pandas \
    numpy \
    matplotlib \
    # FastAPI and web frameworks
    fastapi \
    uvicorn \
    flask \
    django \
    # Additional development tools
    httpx \
    aiohttp \
    pydantic \
    sqlalchemy \
    alembic \
    redis \
    celery \
    # Testing frameworks
    pytest-asyncio \
    pytest-mock \
    coverage

# Install Playwright browsers
RUN playwright install chromium firefox webkit \
    && playwright install-deps

# Install global npm packages
RUN npm install -g \
    yarn \
    pnpm \
    typescript \
    ts-node \
    nodemon \
    pm2 \
    create-react-app \
    @vue/cli \
    @angular/cli \
    vite \
    webpack \
    eslint \
    prettier

# Install noVNC for web-based VNC access
RUN cd /opt && \
    git clone https://github.com/novnc/noVNC.git && \
    cd noVNC && \
    ln -s vnc.html index.html

# Create workspace directory
RUN mkdir -p /workspace && chown suna:suna /workspace

# Set up VNC configuration
RUN mkdir -p /home/suna/.vnc \
    && echo "suna123" | vncpasswd -f > /home/suna/.vnc/passwd \
    && chmod 600 /home/suna/.vnc/passwd \
    && chown -R suna:suna /home/suna/.vnc

# Create VNC startup script
RUN echo '#!/bin/bash\n\
export USER=suna\n\
export HOME=/home/suna\n\
export DISPLAY=:1\n\
cd /home/suna\n\
# Kill any existing VNC servers\n\
vncserver -kill :1 2>/dev/null || true\n\
# Start VNC server\n\
vncserver :1 -geometry 1920x1080 -depth 24 -dpi 96 -localhost no\n\
# Keep the script running\n\
while true; do\n\
  if ! pgrep -f "Xvnc.*:1" > /dev/null; then\n\
    echo "VNC server stopped, restarting..."\n\
    vncserver :1 -geometry 1920x1080 -depth 24 -dpi 96 -localhost no\n\
  fi\n\
  sleep 5\n\
done' > /usr/local/bin/start-vnc.sh \
    && chmod +x /usr/local/bin/start-vnc.sh

# Create xstartup script for VNC
RUN echo '#!/bin/bash\n\
# Clean up any existing sessions\n\
unset SESSION_MANAGER\n\
unset DBUS_SESSION_BUS_ADDRESS\n\
# Set up environment\n\
export XKL_XMODMAP_DISABLE=1\n\
export XDG_CURRENT_DESKTOP="XFCE"\n\
export XDG_SESSION_DESKTOP="xfce"\n\
# Start XFCE4\n\
exec startxfce4' > /home/suna/.vnc/xstartup \
    && chmod +x /home/suna/.vnc/xstartup \
    && chown suna:suna /home/suna/.vnc/xstartup

# Configure Supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy healthcheck script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Set up environment for suna user
USER suna
WORKDIR /workspace

# Set environment variables
ENV HOME=/home/suna
ENV USER=suna
ENV SHELL=/bin/bash
ENV DISPLAY=:1

# Expose VNC and noVNC ports
EXPOSE 5901 6080

# Start supervisor
USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]