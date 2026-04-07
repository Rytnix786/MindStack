# RAG System Deployment Guide

## Local Docker Deployment

### Prerequisites

- Docker installed
- Docker Compose installed

### Setup & Run Locally

1. **Build and start services:**

```bash
cd rag-system
docker-compose up --build
```

This will:

- Pull and run Ollama container (downloads mistral model on first run ~4GB)
- Build and run the RAG backend (FastAPI on port 8000)
- Setup ChromaDB persistence

1. **Initialize Ollama model (first time only):**

```bash
docker exec rag-ollama ollama pull mistral
```

1. **Ingest documents:**

```bash
# Place .txt, .pdf, or .md files in ./data folder
docker exec rag-backend python -m src.ingestion
```

1. **Test the API:**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?"}'
```

1. **View API docs:**

Open [http://localhost:8000/docs](http://localhost:8000/docs) in browser

---

## InsForge Deployment

### Setup InsForge CLI

1. **Install InsForge CLI:**

```bash
npm install -g @insforge/cli
```

1. **Authenticate with your credentials:**

```bash
npx @insforge/install --client copilot \
  --env API_KEY=ik_your_insforge_key_here \
  --env API_BASE_URL=https://your-org.us-east.insforge.app
```

1. **Link your project:**

```bash
npx @insforge/cli link --project-id your-project-id-here
```

### Deploy to InsForge

1. **Push Docker image:**

```bash
docker build -t rag-backend:latest .
docker tag rag-backend:latest your-registry/rag-backend:latest
docker push your-registry/rag-backend:latest
```

1. **Deploy via InsForge CLI:**

```bash
npx @insforge/cli deploy \
  --image your-registry/rag-backend:latest \
  --port 8000 \
  --env CHROMA_PERSIST_DIR=/data/chroma_db \
  --env TOP_K_RETRIEVAL=10
```

1. **Set up Ollama sidecar:**

InsForge should detect the docker-compose services. Configure:

- Ollama container as sidecar service
- Network: same as RAG backend
- Port: 11434

### Environment Variables (InsForge)

```
OPENAI_API_KEY=dummy_key_ollama
CHROMA_PERSIST_DIR=/data/chroma_db
TOP_K_RETRIEVAL=10
TOP_K_RERANK=3
FAITHFULNESS_THRESHOLD=0.75
```

### Data Persistence

For InsForge deployment, configure volumes:

- `/app/data` → document storage
- `/app/chroma_db` → vector database
- `/app/bm25_index.pkl` → BM25 index

---

## Troubleshooting

### Ollama not found error

```bash
# Ensure Ollama container is running
docker ps | grep ollama

# Manual pull
docker exec rag-ollama ollama pull mistral
```

### ChromaDB permission errors

```bash
# Set permissions
docker exec rag-backend chmod 766 /app/chroma_db
```

### API not responding

```bash
# Check logs
docker logs rag-backend
docker logs rag-ollama
```

### Model download stuck

Ollama models are large (~4GB for mistral). First pull may take 10-15 minutes.

---

## Performance Notes

- **First query:** ~30-60s (Ollama model loading + inference)
- **Subsequent queries:** ~5-15s (cached model)
- **Reranking:** +2-5s (cross-encoder scoring)
- **Full pipeline:** hybrid retrieval → rerank → LLM generation

---

## Scaling Considerations

For production InsForge:

- Use GPU nodes for Ollama (faster inference)
- Deploy multiple RAG backend replicas
- Use managed database for ChromaDB (PostgreSQL backend)
- Set up horizontal scaling via load balancer

