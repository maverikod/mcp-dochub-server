#!/bin/bash

# Build script for MCP DocHub Server Docker image
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="mcp-dochub-server"
TAG="latest"
BUILD_CONTEXT="../"
DOCKERFILE="Dockerfile"
NO_CACHE=false
PUSH=false
REGISTRY=""

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
    echo "  -n, --name NAME       Image name (default: mcp-dochub-server)"
    echo "  -t, --tag TAG         Image tag (default: latest)"
    echo "  -r, --registry REG    Registry prefix (e.g., docker.io/username)"
    echo "  --no-cache           Build without cache"
    echo "  --push               Push image after build"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                           # Build with defaults"
    echo "  $0 -n myserver -t v1.0.0                   # Custom name and tag"
    echo "  $0 -r docker.io/username --push            # Build and push to registry"
    echo "  $0 --no-cache                              # Build without cache"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --push)
            PUSH=true
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

# Construct full image name
if [[ -n "$REGISTRY" ]]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${TAG}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
fi

# Check if we're in the correct directory
if [[ ! -f "$DOCKERFILE" ]]; then
    print_error "Dockerfile not found in current directory!"
    print_info "Make sure you're running this script from the docker/ directory"
    exit 1
fi

# Check if build context exists
if [[ ! -d "$BUILD_CONTEXT" ]]; then
    print_error "Build context directory not found: $BUILD_CONTEXT"
    exit 1
fi

# Create necessary directories
print_info "Creating required directories..."
mkdir -p ../logs ../cache

print_info "🐳 Building Docker image..."
print_info "Image: $FULL_IMAGE_NAME"
print_info "Context: $BUILD_CONTEXT"
print_info "Dockerfile: $DOCKERFILE"

# Build docker command
DOCKER_CMD="docker build"

if [[ "$NO_CACHE" == "true" ]]; then
    DOCKER_CMD="$DOCKER_CMD --no-cache"
    print_info "Cache disabled"
fi

DOCKER_CMD="$DOCKER_CMD -t $FULL_IMAGE_NAME -f $DOCKERFILE $BUILD_CONTEXT"

# Execute build
print_info "Executing: $DOCKER_CMD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if eval $DOCKER_CMD; then
    print_success "Docker image built successfully!"
    
    # Show image info
    print_info "Image details:"
    docker images "$FULL_IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    # Push if requested
    if [[ "$PUSH" == "true" ]]; then
        if [[ -z "$REGISTRY" ]]; then
            print_warning "Cannot push: no registry specified"
            print_info "Use -r/--registry option to specify registry"
        else
            print_info "🚀 Pushing image to registry..."
            if docker push "$FULL_IMAGE_NAME"; then
                print_success "Image pushed successfully!"
            else
                print_error "Failed to push image"
                exit 1
            fi
        fi
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "🎉 Build completed successfully!"
    print_info "To run the container:"
    echo "   docker run -d -p 8060:8060 \\
     --restart unless-stopped \\
     -v \$(pwd)/../config:/app/config:ro \\
     -v \$(pwd)/../logs:/app/logs \\
     -v \$(pwd)/../cache:/app/cache \\
     -v /var/run/docker.sock:/var/run/docker.sock \\
     --user \$(id -u):\$(id -g) \\
     $FULL_IMAGE_NAME"
    print_info "Or use docker-compose:"
    echo "   cd docker && docker-compose up -d"
    
else
    print_error "Docker build failed!"
    exit 1
fi 