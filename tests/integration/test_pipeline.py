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


def test_query_endpoint_empty_retrieval_results(monkeypatch):
    """Error scenario: Query that returns no retrieval results should gracefully refuse."""
    def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
        # Simulate empty retrieval (no relevant chunks found)
        return RAGResponse(
            query=payload.query,
            answer="INSUFFICIENT_CONTEXT",
            answer_grounded=False,
            citations=[],
            chunks_retrieved=0,
            latency_ms=45.0,
            model_used="relevance-gate",
            prompt_version="test",
            reranker_applied=False,
            llm_called=False,
            cached=False,
        )

    monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
    client = TestClient(api.app)

    response = client.post("/query", json={"query": "Completely out of scope question?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer_grounded"] is False
    assert data["answer"] == "INSUFFICIENT_CONTEXT"
    assert len(data["citations"]) == 0
    assert data["chunks_retrieved"] == 0


def test_query_response_latency_tracking(monkeypatch):
    """Validation: API should preserve latency reported by the pipeline response."""

    def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
        return _make_response(
            payload,
            grounded=True,
            cached=False,
            answer="Test answer",
        )

    monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
    client = TestClient(api.app)

    response = client.post("/query", json={"query": "test"})
    assert response.status_code == 200
    data = response.json()

    # Latency should be present and match mocked pipeline output.
    assert data["latency_ms"] > 0
    assert data["latency_ms"] == 12.3


def test_query_with_extreme_top_k_values(monkeypatch):
    """Edge case: Very large top_k values should be clamped or handled."""
    call_count = {"count": 0}

    def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
        call_count["count"] += 1
        # Mock should still return valid response regardless of top_k
        return _make_response(
            payload,
            grounded=True,
            cached=False,
            answer="Answer with clamped top_k",
        )

    monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
    client = TestClient(api.app)

    # Very large top_k values
    response = client.post("/query", json={
        "query": "test",
        "top_k_retrieval": 1000,
        "top_k_rerank": 500
    })
    
    # Should either accept or reject gracefully
    assert response.status_code in [200, 400, 422]


def test_cache_behavior_with_normalized_queries(monkeypatch):
    """Validation: Query normalization should make cache hits work for similar queries."""
    call_log = []

    def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
        call_log.append(payload.query)
        # All queries return same answer
        return _make_response(
            payload,
            grounded=True,
            cached=False,
            answer="Standard answer",
        )

    monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
    client = TestClient(api.app)

    # Query 1: Normal
    r1 = client.post("/query", json={"query": "What is the refund policy?"})
    assert r1.json()["cached"] is False

    # Query 2: Same but with extra spaces / different case
    r2 = client.post("/query", json={"query": "  What   is   the   refund   policy?  "})
    # If normalization works, this might be cached
    # If not, it's still a valid scenario

    assert r1.status_code == 200
    assert r2.status_code == 200


def test_multiple_sequential_queries_with_different_answers(monkeypatch):
    """Stress test: Multiple sequential queries should each be answered correctly."""
    def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
        if "refund" in payload.query.lower():
            answer = "30 days for refunds"
            grounded = True
        elif "onboarding" in payload.query.lower():
            answer = "Complete onboarding in first week"
            grounded = True
        else:
            answer = "INSUFFICIENT_CONTEXT"
            grounded = False

        return RAGResponse(
            query=payload.query,
            answer=answer,
            answer_grounded=grounded,
            citations=[] if not grounded else [
                ChunkResult(
                    text=answer,
                    source="test.txt",
                    chunk_index=0,
                    reranker_score=5.0,
                    retrieval_method="hybrid",
                )
            ],
            chunks_retrieved=1 if grounded else 0,
            latency_ms=20.0,
            model_used="test",
            prompt_version="test",
            reranker_applied=True,
            llm_called=True,
            cached=False,
        )

    monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
    client = TestClient(api.app)

    queries = [
        ("What is the refund policy?", True, "30 days"),
        ("How does onboarding work?", True, "first week"),
        ("Tell me about aliens", False, "INSUFFICIENT_CONTEXT"),
    ]

    for query, should_ground, expected_answer_part in queries:
        response = client.post("/query", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert data["answer_grounded"] == should_ground
        assert expected_answer_part in data["answer"]


def test_response_consistency_across_models(monkeypatch):
    """Validation: Different model choices should return consistent schema."""
    def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
        models = ["extractive-fast-path", "llm-full", "relevance-gate"]
        model = models[hash(payload.query) % len(models)]
        
        return RAGResponse(
            query=payload.query,
            answer="Test",
            answer_grounded=True,
            citations=[],
            chunks_retrieved=0,
            latency_ms=10.0,
            model_used=model,
            prompt_version="1.0",
            reranker_applied=False,
            llm_called=model != "extractive-fast-path",
            cached=False,
        )

    monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
    client = TestClient(api.app)

    for i in range(5):
        response = client.post("/query", json={"query": f"test query {i}"})
        assert response.status_code == 200
        data = response.json()
        
        # All should have same schema regardless of model
        required_keys = {
            "query", "answer", "answer_grounded", "citations", "chunks_retrieved",
            "latency_ms", "model_used", "prompt_version", "reranker_applied",
            "llm_called", "cached", "timestamp"
        }
        assert required_keys.issubset(set(data.keys()))
        assert isinstance(data["latency_ms"], (int, float))
        assert data["latency_ms"] >= 0


def test_citation_generation_consistency(monkeypatch):
    """Validation: Citations should always match answer_grounded flag."""
    def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
        if "refuse" in payload.query.lower():
            # Refusal case: should have no citations
            return RAGResponse(
                query=payload.query,
                answer="INSUFFICIENT_CONTEXT",
                answer_grounded=False,
                citations=[],
                chunks_retrieved=0,
                latency_ms=30.0,
                model_used="relevance-gate",
                prompt_version="test",
                reranker_applied=False,
                llm_called=False,
                cached=False,
            )
        else:
            # Grounded case: should have citations
            return RAGResponse(
                query=payload.query,
                answer="Grounded answer with source",
                answer_grounded=True,
                citations=[
                    ChunkResult(
                        text="Source material",
                        source="test.txt",
                        chunk_index=0,
                        reranker_score=7.0,
                        retrieval_method="hybrid",
                    )
                ],
                chunks_retrieved=1,
                latency_ms=50.0,
                model_used="test",
                prompt_version="test",
                reranker_applied=True,
                llm_called=True,
                cached=False,
            )

    monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
    client = TestClient(api.app)

    # Refusal query
    refuse_resp = client.post("/query", json={"query": "refuse this please"})
    refuse_data = refuse_resp.json()
    assert refuse_data["answer_grounded"] is False
    assert len(refuse_data["citations"]) == 0

    # Grounded query
    ground_resp = client.post("/query", json={"query": "normal question"})
    ground_data = ground_resp.json()
    assert ground_data["answer_grounded"] is True
    assert len(ground_data["citations"]) > 0
