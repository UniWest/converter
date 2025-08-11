#!/bin/bash

# Docker Setup Verification Script
# This script verifies that the Docker environment is properly configured

echo "🔍 Docker Setup Verification Starting..."
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed or not in PATH"
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t media-converter-test . || {
    echo "❌ Failed to build Docker image"
    exit 1
}

echo "✅ Docker image built successfully"

# Test FFmpeg installation inside the container
echo "🎬 Testing FFmpeg installation..."
docker run --rm media-converter-test ffmpeg -version | head -3 || {
    echo "❌ FFmpeg is not properly installed in the container"
    exit 1
}

echo "✅ FFmpeg is properly installed"

# Test Python and Django setup
echo "🐍 Testing Python and Django setup..."
docker run --rm media-converter-test python --version || {
    echo "❌ Python is not properly installed"
    exit 1
}

docker run --rm media-converter-test python -c "import django; print(f'Django {django.get_version()}')" || {
    echo "❌ Django is not properly installed"
    exit 1
}

echo "✅ Python and Django are properly installed"

# Test that requirements are installed
echo "📦 Testing package installations..."
docker run --rm media-converter-test python -c "import celery, redis, PIL" || {
    echo "❌ Required packages are not installed"
    exit 1
}

echo "✅ Required packages are installed"

# Clean up test image
echo "🧹 Cleaning up test image..."
docker rmi media-converter-test || {
    echo "⚠️ Warning: Could not remove test image"
}

echo ""
echo "🎉 All checks passed! Docker setup is ready for deployment."
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your settings"
echo "2. Run 'docker-compose up --build' to start the application"
echo "3. Access the application at http://localhost:8000"
echo "4. Monitor tasks at http://localhost:5555 (Flower)"
echo ""
