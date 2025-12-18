#!/bin/bash
# Build and push multi-architecture Docker images to Docker Hub
# Supports both AMD64 and ARM64 architectures

set -e

DOCKER_USERNAME="${DOCKER_USERNAME:-staugustine1}"
BACKEND_IMAGE="${DOCKER_USERNAME}/elvanto-export-backend"
FRONTEND_IMAGE="${DOCKER_USERNAME}/elvanto-export-frontend"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building and pushing multi-architecture images to Docker Hub...${NC}"
echo -e "${BLUE}Docker Hub username: ${DOCKER_USERNAME}${NC}"

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

# Create and use a buildx builder instance
echo -e "${BLUE}Setting up buildx builder...${NC}"
docker buildx create --name multiarch-builder --use 2>/dev/null || docker buildx use multiarch-builder
docker buildx inspect --bootstrap

# Build and push backend image
echo -e "${GREEN}Building backend image (linux/amd64,linux/arm64)...${NC}"
cd backend
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag ${BACKEND_IMAGE}:latest \
    --tag ${BACKEND_IMAGE}:$(git rev-parse --short HEAD) \
    --push \
    .
cd ..

# Build and push frontend production image
echo -e "${GREEN}Building frontend production image (linux/amd64,linux/arm64)...${NC}"
cd frontend

# Default API URL - can be overridden with REACT_APP_API_URL env var
REACT_APP_API_URL=${REACT_APP_API_URL:-http://localhost:9000}

docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --file Dockerfile.prod \
    --build-arg REACT_APP_API_URL=${REACT_APP_API_URL} \
    --tag ${FRONTEND_IMAGE}:latest \
    --tag ${FRONTEND_IMAGE}:$(git rev-parse --short HEAD) \
    --push \
    .
cd ..

echo -e "${GREEN}✓ Images built and pushed successfully!${NC}"
echo -e "${BLUE}Backend: ${BACKEND_IMAGE}:latest${NC}"
echo -e "${BLUE}Frontend: ${FRONTEND_IMAGE}:latest${NC}"

