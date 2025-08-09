#!/bin/bash

# Run script for MCP DocHub Server Docker container
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="mcp-dochub-server:latest"
CONTAINER_NAME="mcp-dochub-server"
HOST_PORT="8060"
CONTAINER_PORT="8060"
DETACHED=true
REMOVE_EXISTING=false

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -i, --image IMAGE     Docker image name (default: mcp-dochub-server:latest)"
    echo "  -n, --name NAME       Container name (default: mcp-dochub-server)"
    echo "  -p, --port PORT       Host port (default: 8060)"
    echo "  --interactive         Run in interactive mode (not detached)"
    echo "  --remove-existing     Remove existing container if found"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run with defaults"
    echo "  $0 -p 8080                          # Use port 8080"
    echo "  $0 --interactive                    # Run in foreground"
    echo "  $0 --remove-existing                # Remove existing container first"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -n|--name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -p|--port)
            HOST_PORT="$2"
            shift 2
            ;;
        --interactive)
            DETACHED=false
            shift
            ;;
        --remove-existing)
            REMOVE_EXISTING=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running or not accessible"
    exit 1
fi

# Check if image exists
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    print_error "Docker image '$IMAGE_NAME' not found"
    print_info "Build the image first using: ./build.sh"
    exit 1
fi

# Get current user UID and GID
USER_ID=$(id -u)
GROUP_ID=$(id -g)
print_info "Using user mapping: ${USER_ID}:${GROUP_ID}"

# Create necessary directories
print_info "Creating required directories..."
mkdir -p ../logs ../cache

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    if [[ "$REMOVE_EXISTING" == "true" ]]; then
        print_warning "Removing existing container: $CONTAINER_NAME"
        docker rm -f "$CONTAINER_NAME"
    else
        print_error "Container '$CONTAINER_NAME' already exists"
        print_info "Use --remove-existing to remove it, or choose a different name with -n"
        exit 1
    fi
fi

# Build docker run command
DOCKER_CMD="docker run"

if [[ "$DETACHED" == "true" ]]; then
    DOCKER_CMD="$DOCKER_CMD -d"
else
    DOCKER_CMD="$DOCKER_CMD -it --rm"
fi

DOCKER_CMD="$DOCKER_CMD --name $CONTAINER_NAME"
DOCKER_CMD="$DOCKER_CMD --restart unless-stopped"
DOCKER_CMD="$DOCKER_CMD -p ${HOST_PORT}:${CONTAINER_PORT}"
DOCKER_CMD="$DOCKER_CMD -v \$(pwd)/../config:/app/config:ro"
DOCKER_CMD="$DOCKER_CMD -v \$(pwd)/../logs:/app/logs"
DOCKER_CMD="$DOCKER_CMD -v \$(pwd)/../cache:/app/cache"
DOCKER_CMD="$DOCKER_CMD -v /var/run/docker.sock:/var/run/docker.sock"
DOCKER_CMD="$DOCKER_CMD --user ${USER_ID}:${GROUP_ID}"
DOCKER_CMD="$DOCKER_CMD $IMAGE_NAME"

print_info "🐳 Starting Docker container..."
print_info "Image: $IMAGE_NAME"
print_info "Container: $CONTAINER_NAME"
print_info "Port: $HOST_PORT:$CONTAINER_PORT"
print_info "Mode: $([ "$DETACHED" == "true" ] && echo "detached" || echo "interactive")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Execute run command
print_info "Executing: $DOCKER_CMD"

if eval $DOCKER_CMD; then
    if [[ "$DETACHED" == "true" ]]; then
        print_success "Container started successfully!"
        print_info "Container is running in the background"
        print_info "Server URL: http://localhost:$HOST_PORT"
        print_info "API Documentation: http://localhost:$HOST_PORT/docs"
        print_info ""
        print_info "Useful commands:"
        echo "   docker logs $CONTAINER_NAME          # View logs"
        echo "   docker logs -f $CONTAINER_NAME       # Follow logs"
        echo "   docker exec -it $CONTAINER_NAME bash # Enter container"
        echo "   docker stop $CONTAINER_NAME          # Stop container"
        echo "   docker rm $CONTAINER_NAME            # Remove container"
    else
        print_info "Container finished execution"
    fi
else
    print_error "Failed to start container!"
    exit 1
fi 