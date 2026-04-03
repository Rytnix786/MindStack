#!/usr/bin/env python3
"""Quick test of single query to check grounding flags."""
from src.models import QueryRequest
from src.retrieval import run_rag_query, retrieve_chunks

req = QueryRequest(query="What is the refund policy?")

# First check what chunks are retrieved
chunks = retrieve_chunks(req.query, top_k=3)
print(f"Retrieved {len(chunks)} chunks:")
for i, chunk in enumerate(chunks):
    score = chunk.get("score", 0)
    rerank = chunk.get("reranker_score", None)
    print(f"  Chunk {i+1}: score={score}, reranker_score={rerank}, source={chunk.get('source')}")

print("\nRunning full query...")
res = run_rag_query(req)
print(f"Question: {res.query}")
print(f"Answer: {res.answer[:150]}")
print(f"Grounded: {res.answer_grounded}")
print(f"Citation count: {len(res.citations) if res.citations else 0}")
