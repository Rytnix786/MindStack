docker exec rag-backend sh -c "cd /app && PYTHONPATH=/app OLLAMA_BASE_URL=http://rag-ollama:11434 python evals/evaluate.py"
