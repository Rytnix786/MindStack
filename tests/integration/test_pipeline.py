from __future__ import annotations

from fastapi.testclient import TestClient

from src import api
from src.models import ChunkResult, QueryRequest, RAGResponse


def _make_response(payload: QueryRequest, *, grounded: bool, cached: bool, answer: str) -> RAGResponse:
    citations = []
    if grounded:
        citations = [
            ChunkResult(
                text="Customers may return products within 30 days.",
                source="refund_policy.txt",
                chunk_index=1,
                reranker_score=5.0,
                retrieval_method="hybrid",
            )
        ]

    return RAGResponse(
        query=payload.query,
        answer=answer,
        answer_grounded=grounded,
        citations=citations,
        chunks_retrieved=len(citations),
        latency_ms=12.3,
        model_used="extractive-fast-path",
        prompt_version="test",
        reranker_applied=True,
        llm_called=not cached,
        cached=cached,
    )


def test_query_endpoint_grounded_unanswerable_and_cached(monkeypatch):
    cache: dict[str, RAGResponse] = {}

    def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
        if payload.query in cache:
            cached_response = cache[payload.query].model_copy()
            cached_response.cached = True
            cached_response.llm_called = False
            return cached_response

        if "unanswerable" in payload.query.lower():
            response = _make_response(
                payload,
                grounded=False,
                cached=False,
                answer="INSUFFICIENT_CONTEXT",
            )
        else:
            response = _make_response(
                payload,
                grounded=True,
                cached=False,
                answer="Customers may return products within 30 days.",
            )

        cache[payload.query] = response
        return response

    monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
    client = TestClient(api.app)

    grounded = client.post("/query", json={"query": "What is the refund policy?"})
    assert grounded.status_code == 200
    grounded_json = grounded.json()
    assert grounded_json["answer_grounded"] is True
    assert len(grounded_json["citations"]) > 0
    assert grounded_json["cached"] is False

    unanswerable = client.post("/query", json={"query": "This is unanswerable from docs"})
    assert unanswerable.status_code == 200
    unanswerable_json = unanswerable.json()
    assert unanswerable_json["answer_grounded"] is False
    assert unanswerable_json["answer"] == "INSUFFICIENT_CONTEXT"

    cached = client.post("/query", json={"query": "What is the refund policy?"})
    assert cached.status_code == 200
    cached_json = cached.json()
    assert cached_json["cached"] is True
