#!/bin/bash
# Build and push multi-architecture Docker images to Docker Hub
# Supports both AMD64 and ARM64 architectures

set -e

DOCKER_USERNAME="${DOCKER_USERNAME:-staugustine1}"
BACKEND_IMAGE="${DOCKER_USERNAME}/elvanto-export-backend"
FRONTEND_IMAGE="${DOCKER_USERNAME}/elvanto-export-frontend"

# Read version from VERSION file
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION | tr -d '[:space:]')
    echo "Version from VERSION file: ${VERSION}"
else
    echo "Warning: VERSION file not found. Using 'latest' only."
    VERSION=""
fi

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building and pushing multi-architecture images to Docker Hub...${NC}"
echo -e "${BLUE}Docker Hub username: ${DOCKER_USERNAME}${NC}"
if [ -n "$VERSION" ]; then
    echo -e "${BLUE}Version: ${VERSION}${NC}"
fi

# Check if logged into Docker Hub (basic check)
echo -e "${BLUE}Checking Docker Hub authentication...${NC}"
if ! docker info 2>/dev/null | grep -q "Username"; then
    echo "Warning: Make sure you're logged into Docker Hub. Run 'docker login' if needed."
fi

# Check if buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo "Error: docker buildx is not available. Please install Docker Buildx."
    exit 1
fi

# Determine build platform
# Set BUILD_PLATFORM env var to "arm64" to build only for ARM64, or "multi" for both
BUILD_PLATFORM="${BUILD_PLATFORM:-multi}"

if [ "$BUILD_PLATFORM" = "arm64" ]; then
    PLATFORM="linux/arm64"
    echo -e "${BLUE}Building for ARM64 only...${NC}"
else
    PLATFORM="linux/amd64,linux/arm64"
    echo -e "${BLUE}Building for multiple architectures (AMD64 and ARM64)...${NC}"
    
    # Set up buildx builder for multi-arch builds
    echo -e "${BLUE}Setting up buildx builder...${NC}"
    BUILDER_NAME="multiarch-builder"
    
    # Check if builder exists and is usable
    if docker buildx ls 2>/dev/null | grep -q "$BUILDER_NAME"; then
        echo "Builder exists, attempting to use: $BUILDER_NAME"
        if docker buildx use "$BUILDER_NAME" 2>/dev/null; then
            echo "Successfully switched to builder: $BUILDER_NAME"
        else
            echo "Builder exists but can't be used, removing and recreating..."
            docker buildx rm "$BUILDER_NAME" 2>/dev/null || true
            docker buildx create --name "$BUILDER_NAME" --use --driver docker-container
        fi
    else
        echo "Creating new builder: $BUILDER_NAME"
        docker buildx create --name "$BUILDER_NAME" --use --driver docker-container
    fi
    
    # Bootstrap the builder
    echo "Bootstrapping builder..."
    docker buildx inspect --bootstrap
fi

# Build and push backend image
echo -e "${GREEN}Building backend image for ${PLATFORM}...${NC}"
cd backend

# Build tags
TAGS="--tag ${BACKEND_IMAGE}:latest"
if [ -n "$VERSION" ]; then
    TAGS="${TAGS} --tag ${BACKEND_IMAGE}:${VERSION}"
    TAGS="${TAGS} --tag ${BACKEND_IMAGE}:v${VERSION}"
fi

if [ "$BUILD_PLATFORM" = "arm64" ]; then
    # Simple build for single platform
    docker build ${TAGS} -t ${BACKEND_IMAGE}:latest .
    if [ -n "$VERSION" ]; then
        docker tag ${BACKEND_IMAGE}:latest ${BACKEND_IMAGE}:${VERSION}
        docker tag ${BACKEND_IMAGE}:latest ${BACKEND_IMAGE}:v${VERSION}
    fi
    docker push ${BACKEND_IMAGE}:latest
    if [ -n "$VERSION" ]; then
        docker push ${BACKEND_IMAGE}:${VERSION}
        docker push ${BACKEND_IMAGE}:v${VERSION}
    fi
else
    # Multi-arch build with buildx
    docker buildx build \
        --platform ${PLATFORM} \
        ${TAGS} \
        --push \
        .
fi
cd ..

# Build and push frontend production image
echo -e "${GREEN}Building frontend production image for ${PLATFORM}...${NC}"
cd frontend

# Default API URL - can be overridden with REACT_APP_API_URL env var
REACT_APP_API_URL=${REACT_APP_API_URL:-http://localhost:9000}

# Build tags for frontend
FRONTEND_TAGS="--tag ${FRONTEND_IMAGE}:latest"
if [ -n "$VERSION" ]; then
    FRONTEND_TAGS="${FRONTEND_TAGS} --tag ${FRONTEND_IMAGE}:${VERSION}"
    FRONTEND_TAGS="${FRONTEND_TAGS} --tag ${FRONTEND_IMAGE}:v${VERSION}"
fi

if [ "$BUILD_PLATFORM" = "arm64" ]; then
    # Simple build for single platform
    docker build \
        --file Dockerfile.prod \
        --build-arg REACT_APP_API_URL=${REACT_APP_API_URL} \
        -t ${FRONTEND_IMAGE}:latest \
        .
    if [ -n "$VERSION" ]; then
        docker tag ${FRONTEND_IMAGE}:latest ${FRONTEND_IMAGE}:${VERSION}
        docker tag ${FRONTEND_IMAGE}:latest ${FRONTEND_IMAGE}:v${VERSION}
    fi
    docker push ${FRONTEND_IMAGE}:latest
    if [ -n "$VERSION" ]; then
        docker push ${FRONTEND_IMAGE}:${VERSION}
        docker push ${FRONTEND_IMAGE}:v${VERSION}
    fi
else
    # Multi-arch build with buildx
    docker buildx build \
        --platform ${PLATFORM} \
        --file Dockerfile.prod \
        --build-arg REACT_APP_API_URL=${REACT_APP_API_URL} \
        ${FRONTEND_TAGS} \
        --push \
        .
fi
cd ..

echo -e "${GREEN}✓ Images built and pushed successfully!${NC}"
echo -e "${BLUE}Backend: ${BACKEND_IMAGE}:latest${NC}"
if [ -n "$VERSION" ]; then
    echo -e "${BLUE}         ${BACKEND_IMAGE}:${VERSION}${NC}"
    echo -e "${BLUE}         ${BACKEND_IMAGE}:v${VERSION}${NC}"
fi
echo -e "${BLUE}Frontend: ${FRONTEND_IMAGE}:latest${NC}"
if [ -n "$VERSION" ]; then
    echo -e "${BLUE}         ${FRONTEND_IMAGE}:${VERSION}${NC}"
    echo -e "${BLUE}         ${FRONTEND_IMAGE}:v${VERSION}${NC}"
fi

