#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e
set -o pipefail

if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Exiting..."
    exit 1
fi

# Define the image name
IMAGE_NAME=${1:-"langgraph-server:latest"}
VERSION="1.0.0"
FULL_IMAGE_NAME="$IMAGE_NAME:$VERSION"

# Uncomment if needed
# docker rmi $IMAGE_NAME
# docker builder prune --all --force

# Remove all containers based on the specified image, both stopped and exited
echo "Removing containers based on $FULL_IMAGE_NAME..."
docker ps -a -q --filter "ancestor=$FULL_IMAGE_NAME" | xargs -r docker rm -f

# Build the new image with the specified tag
# Example for error handling after docker build
echo "Building new image $FULL_IMAGE_NAME..."
docker build --no-cache -t $FULL_IMAGE_NAME . || { echo "Docker build failed"; exit 1; }


