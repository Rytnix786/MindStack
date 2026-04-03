"""Data models for the RAG system using Pydantic v2."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for RAG queries."""

    query: str = Field(..., min_length=3, max_length=500, description="The user's question")
    top_k_retrieval: int = Field(default=10, ge=1, le=20, description="Top K chunks to retrieve")
    top_k_rerank: int = Field(default=3, ge=1, le=10, description="Top K chunks to rerank to")


class ChunkResult(BaseModel):
    """A single retrieved and reranked chunk."""

    text: str = Field(..., description="Chunk text content")
    source: str = Field(..., description="Source document filename")
    chunk_index: int = Field(..., description="Chunk index within the source document")
    reranker_score: float = Field(default=0.0, description="Cross-encoder reranker score")
    retrieval_method: str = Field(default="hybrid", description="Retrieval method used")


class RAGResponse(BaseModel):
    """Response model for RAG queries."""

    query: str = Field(..., description="Original user query")
    answer: str = Field(..., description="Generated answer from LLM")
    answer_grounded: bool = Field(..., description="Whether answer is grounded in context")
    citations: list[ChunkResult] = Field(default_factory=list, description="Cited chunks")
    chunks_retrieved: int = Field(..., description="Total chunks retrieved")
    latency_ms: float = Field(..., description="End-to-end latency in milliseconds")
    model_used: str = Field(..., description="LLM model used for generation")
    prompt_version: str = Field(..., description="Prompt template version")
    reranker_applied: bool = Field(default=False, description="Whether reranking was applied")
    llm_called: bool = Field(default=False, description="Whether LLM was called")
    cached: bool = Field(default=False, description="Whether response was retrieved from cache")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class EvalResult(BaseModel):
    """Evaluation result for a single RAG query."""

    question: str = Field(..., description="Input question")
    expected_answer: str = Field(..., description="Ground truth answer")
    generated_answer: str = Field(..., description="Generated answer from RAG")
    faithfulness: float = Field(..., ge=0.0, le=1.0, description="Faithfulness score")
    answer_relevancy: float = Field(..., ge=0.0, le=1.0, description="Answer relevancy score")
    context_precision: float = Field(..., ge=0.0, le=1.0, description="Context precision score")
    passed: bool = Field(..., description="Whether evaluation passed")
