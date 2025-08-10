FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        docker.io \
        curl \
        git && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create directories for mounted volumes
RUN mkdir -p /app/config /app/logs /app/cache

# Expose port
EXPOSE 8060

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8060/health || exit 1

# Default command
CMD ["python", "-m", "ai_admin.server", "--host", "0.0.0.0", "--port", "8060"] 