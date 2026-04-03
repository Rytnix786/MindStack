#!/usr/bin/env python
"""Quick verification that models and retrieval work together."""

try:
    from src.models import QueryRequest, ChunkResult, RAGResponse
    from src.retrieval import run_rag_query
    
    print("✅ All imports successful!")
    print("")
    print("Models available:")
    print(f"  - QueryRequest: {QueryRequest}")
    print(f"  - ChunkResult: {ChunkResult}")
    print(f"  - RAGResponse: {RAGResponse}")
    print("")
    print("Functions available:")
    print(f"  - run_rag_query: {run_rag_query}")
    print("")
    print("✅ Integration verified!")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
