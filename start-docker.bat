@echo off
REM RAG System Docker startup script for Windows

echo.
echo 🚀 Starting RAG System with Docker...
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please ensure Docker Desktop includes Compose.
    exit /b 1
)

REM Build and start services
echo 📦 Building Docker images...
docker-compose build

if errorlevel 1 (
    echo ❌ Build failed!
    exit /b 1
)

echo 🐳 Starting services...
docker-compose up -d

if errorlevel 1 (
    echo ❌ Failed to start services!
    exit /b 1
)

REM Wait for services to be healthy
echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak

REM Pull mistral model
echo 📥 Pulling Ollama mistral model (this may take several minutes)...
docker exec rag-ollama ollama pull mistral

echo.
echo ✅ RAG System is running!
echo.
echo 📍 API available at: http://localhost:8000
echo 📚 API docs at: http://localhost:8000/docs
echo 🔌 Ollama available at: http://localhost:11434
echo.
echo Next steps:
echo 1. Place documents in .\data folder
echo 2. Run: docker exec rag-backend python -m src.ingestion
echo 3. Query: curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d "{\"question\": \"Your question here\"}"
echo.
echo View logs: docker-compose logs -f
echo.
pause
