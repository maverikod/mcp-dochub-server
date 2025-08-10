#!/bin/bash

# AI Admin Server Docker Run Script
# This script runs the AI Admin server container with proper configuration

set -e

# Configuration
CONTAINER_NAME="ai-admin"
IMAGE_NAME="docker_ai-admin-server:latest"
HOST_PORT="8060"
CONTAINER_PORT="8060"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AI Admin Server...${NC}"

# Stop and remove existing container if it exists
if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}Stopping existing container ${CONTAINER_NAME}...${NC}"
    docker stop ${CONTAINER_NAME} || true
    docker rm ${CONTAINER_NAME} || true
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p ../config ../logs ../cache ../models

# Run the container
echo -e "${YELLOW}Starting container...${NC}"
docker run -d \
    --name ${CONTAINER_NAME} \
    --restart unless-stopped \
    -p ${HOST_PORT}:${CONTAINER_PORT} \
    -v $(pwd)/../config:/app/config:ro \
    -v $(pwd)/../logs:/app/logs \
    -v $(pwd)/../cache:/app/cache \
    -v $(pwd)/../models:/app/models \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e PYTHONPATH=/app \
    -e LOG_LEVEL=INFO \
    -e OLLAMA_MODELS=/app/models \
    -e OLLAMA_HOST=localhost \
    -e OLLAMA_PORT=11434 \
    -e HOME=/home/aiadmin \
    ${IMAGE_NAME}

# Wait for container to start
echo -e "${YELLOW}Waiting for container to start...${NC}"
sleep 5

# Check if container is running
if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${GREEN}✅ Container ${CONTAINER_NAME} is running successfully!${NC}"
    echo -e "${GREEN}🌐 Server available at: http://localhost:${HOST_PORT}${NC}"
    echo -e "${GREEN}📊 Health check: http://localhost:${HOST_PORT}/health${NC}"
    
    # Show container info
    echo -e "\n${YELLOW}Container Information:${NC}"
    docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    # Show logs
    echo -e "\n${YELLOW}Recent logs:${NC}"
    docker logs --tail 10 ${CONTAINER_NAME}
    
else
    echo -e "${RED}❌ Failed to start container ${CONTAINER_NAME}${NC}"
    echo -e "${YELLOW}Container logs:${NC}"
    docker logs ${CONTAINER_NAME}
    exit 1
fi

echo -e "\n${GREEN}🎉 AI Admin Server is ready!${NC}"
echo -e "${YELLOW}To view logs: docker logs -f ${CONTAINER_NAME}${NC}"
echo -e "${YELLOW}To stop: docker stop ${CONTAINER_NAME}${NC}"
echo -e "${YELLOW}To restart: docker restart ${CONTAINER_NAME}${NC}" 