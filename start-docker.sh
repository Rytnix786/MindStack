#!/bin/bash

echo "🚀 Starting RAG System with Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Build and start services
echo "📦 Building Docker images..."
docker-compose build

echo "🐳 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Pull mistral model
echo "📥 Pulling Ollama mistral model (this may take a few minutes)..."
docker exec rag-ollama ollama pull mistral

echo ""
echo "✅ RAG System is running!"
echo ""
echo "📍 API available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo "🔌 Ollama available at: http://localhost:11434"
echo ""
echo "Next steps:"
echo "1. Place documents in ./data folder"
echo "2. Run: docker exec rag-backend python -m src.ingestion"
echo "3. Query: curl -X POST http://localhost:8000/query -H 'Content-Type: application/json' -d '{\"question\": \"Your question here\"}'"
echo ""
echo "View logs: docker-compose logs -f"
