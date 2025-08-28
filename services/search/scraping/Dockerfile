# Web Scraping Service Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    # Browser dependencies for Playwright
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (skip deps installation for now)
RUN playwright install chromium --with-deps || playwright install chromium

# Copy application code
COPY . .

# Create data directory for storage
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]