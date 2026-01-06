#!/bin/bash

# Deploy Script for Ominifix AI Enhanced Self-Healing RPA Framework
# This script builds and starts all Docker containers

echo "=========================================="
echo "Ominifix AI Self-Healing RPA Deployment"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose not found. Please install docker-compose."
    exit 1
fi

echo "✅ docker-compose is available"
echo ""

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down
echo ""

# Build images
echo "🔨 Building Docker images..."
docker-compose build --no-cache
if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "❌ Failed to start services!"
    exit 1
fi
echo ""

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Deployment completed!"
echo ""
echo "🌐 Access Points:"
echo "   - Orchestrator Dashboard: http://localhost:8000"
echo "   - RabbitMQ Management:    http://localhost:15672 (guest/guest)"
echo "   - Model Server:           http://localhost:8002"
echo "   - AI Healing Engine:      http://localhost:5001"
echo "   - AI Element Locator:     http://localhost:8001"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
