docker exec rag-backend sh -c "cd /app/evals && PYTHONPATH=/app OLLAMA_BASE_URL=http://rag-ollama:11434 python evaluate.py"
