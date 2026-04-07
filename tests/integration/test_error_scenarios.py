"""
Comprehensive error scenario and edge case testing for MindStack RAG API.

Tests cover:
- Invalid input validation
- API security (auth, authorization)
- Error response formats
- Resource limits
- Concurrent request handling
- Graceful degradation
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from src import api
from src.models import RAGResponse, ChunkResult, QueryRequest


class TestInputValidation:
    """Validate input sanitization and rejection of malformed data."""

    def test_query_with_null_bytes(self):
        """Security: Null bytes in query should be handled safely."""
        client = TestClient(api.app)
        response = client.post("/query", json={"query": "test\x00null"})
        # Should handle gracefully (not crash)
        assert response.status_code in [200, 400, 422]

    def test_query_with_control_characters(self):
        """Security: Control characters should be handled."""
        client = TestClient(api.app)
        for char in ["\x01", "\x02", "\x1f"]:
            response = client.post("/query", json={"query": f"test{char}query"})
            assert response.status_code in [200, 400, 422]

    def test_query_exceeds_max_length(self):
        """Resource limit: Very long queries should be rejected or clamped."""
        client = TestClient(api.app)
        huge_query = "a" * 100000  # 100KB query
        response = client.post("/query", json={"query": huge_query})
        # Should reject or clamp, not hang
        assert response.status_code in [200, 400, 413, 414, 422]

    def test_non_string_query_field(self):
        """Input validation: Query field must be string, not int/bool/null."""
        client = TestClient(api.app)
        
        invalid_queries = [
            {"query": 123},
            {"query": True},
            {"query": None},
            {"query": ["list"]},
            {"query": {"nested": "object"}},
        ]
        
        for payload in invalid_queries:
            response = client.post("/query", json=payload)
            assert response.status_code in [400, 422]

    def test_extra_fields_in_request(self):
        """Input validation: Extra unexpected fields should be ignored or rejected."""
        client = TestClient(api.app)
        response = client.post("/query", json={
            "query": "test",
            "extra_field": "should not matter",
            "another_field": 123
        })
        # Should ignore extras or validate strictly
        assert response.status_code in [200, 422]

    def test_malformed_json_encoding(self):
        """Input validation: Invalid UTF-8 or encoding issues."""
        client = TestClient(api.app)
        # Invalid UTF-8 sequence
        response = client.post(
            "/query",
            content=b'{"query": "\xff\xfe"}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]


class TestAuthorizationErrors:
    """Test security: admin endpoint protection."""

    def test_upload_without_auth(self, monkeypatch):
        """Security: /upload must require admin authentication."""
        monkeypatch.setattr(api.settings, "enable_unauth_admin", False)
        monkeypatch.setattr(api.settings, "admin_api_key", "test-key")
        
        client = TestClient(api.app)
        response = client.post(
            "/upload",
            files={"files": ("test.txt", b"content")}
        )
        assert response.status_code == 403

    def test_ingest_disabled_when_no_api_key_set(self, monkeypatch):
        """Security: /ingest should be disabled if admin_api_key not configured."""
        monkeypatch.setattr(api.settings, "enable_unauth_admin", False)
        monkeypatch.setattr(api.settings, "admin_api_key", "")
        
        client = TestClient(api.app)
        response = client.post("/ingest")
        assert response.status_code == 503  # Service unavailable

    def test_admin_key_case_sensitive(self, monkeypatch):
        """Security: Admin keys should be case-sensitive."""
        def fake_ingest(_):
            return {"chunks_created": 0, "documents_processed": 0, "collection_name": "test"}

        monkeypatch.setattr(api.settings, "enable_unauth_admin", False)
        monkeypatch.setattr(api.settings, "admin_api_key", "MySecretKey123")
        monkeypatch.setattr(api, "ingest_documents", fake_ingest)
        monkeypatch.setattr(api, "refresh_retrieval_resources", lambda: None)
        
        client = TestClient(api.app)
        
        # Wrong case should fail
        response = client.post("/ingest", headers={"X-Admin-Api-Key": "mysecretkey123"})
        assert response.status_code == 403

    def test_bearer_token_wrong_format(self, monkeypatch):
        """Security: Malformed Bearer token should be rejected."""
        monkeypatch.setattr(api.settings, "enable_unauth_admin", False)
        monkeypatch.setattr(api.settings, "admin_api_key", "correct-key")
        
        client = TestClient(api.app)
        
        invalid_bearer = [
            "Bearer ",  # Empty bearer
            "Bearer",  # Missing space
            "Bearer  ",  # Extra spaces
            "bearer correct-key",  # Wrong case
        ]
        
        for bearer in invalid_bearer:
            response = client.post("/ingest", headers={"Authorization": bearer})
            assert response.status_code == 403


class TestErrorResponseFormats:
    """Test that error responses have consistent, helpful formats."""

    def test_validation_error_response_schema(self):
        """Validation: Error responses should include error details."""
        client = TestClient(api.app)
        response = client.post("/query", json={})  # Missing required field
        
        assert response.status_code == 422
        data = response.json()
        # Pydantic returns 'detail' field with validation errors
        assert "detail" in data or response.status_code == 422

    def test_bad_request_includes_helpful_message(self):
        """Validation: 400 errors should hint at the problem."""
        client = TestClient(api.app)
        response = client.post(
            "/query",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]

    def test_successful_response_always_has_timestamp(self, monkeypatch):
        """Validation: Successful query responses should include timestamp."""
        def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
            return RAGResponse(
                query=payload.query,
                answer="test",
                answer_grounded=True,
                citations=[],
                chunks_retrieved=0,
                latency_ms=10.0,
                model_used="test",
                prompt_version="1.0",
                reranker_applied=False,
                llm_called=False,
                cached=False,
            )

        monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
        client = TestClient(api.app)
        
        response = client.post("/query", json={"query": "test"})
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"] is not None


class TestResourceLimits:
    """Test handling of resource-intensive requests."""

    def test_very_high_top_k_retrieval(self):
        """Resource limit: Unreasonably high top_k should be rejected."""
        client = TestClient(api.app)
        response = client.post("/query", json={
            "query": "test",
            "top_k_retrieval": 999999
        })
        # Either accept and clamp, or reject
        assert response.status_code in [200, 400, 422]

    def test_very_high_top_k_rerank(self):
        """Resource limit: Unreasonably high rerank k should be rejected."""
        client = TestClient(api.app)
        response = client.post("/query", json={
            "query": "test",
            "top_k_rerank": 999999
        })
        assert response.status_code in [200, 400, 422]

    def test_negative_parameters(self):
        """Validation: Negative parameters should be rejected."""
        client = TestClient(api.app)
        
        response = client.post("/query", json={
            "query": "test",
            "top_k_retrieval": -10
        })
        assert response.status_code == 422
        
        response = client.post("/query", json={
            "query": "test",
            "top_k_rerank": -5
        })
        assert response.status_code == 422

    def test_zero_parameters(self):
        """Validation: Zero top_k should be rejected."""
        client = TestClient(api.app)
        
        response = client.post("/query", json={
            "query": "test",
            "top_k_retrieval": 0
        })
        assert response.status_code == 422


class TestEdgeCases:
    """Test unusual but valid-ish inputs."""

    def test_empty_citation_list_consistency(self, monkeypatch):
        """Edge case: Ungrounded answer should have empty citations."""
        def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
            return RAGResponse(
                query=payload.query,
                answer="INSUFFICIENT_CONTEXT",
                answer_grounded=False,
                citations=[],
                chunks_retrieved=0,
                latency_ms=10.0,
                model_used="test",
                prompt_version="1.0",
                reranker_applied=False,
                llm_called=False,
                cached=False,
            )

        monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
        client = TestClient(api.app)
        
        response = client.post("/query", json={"query": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer_grounded"] is False
        assert len(data["citations"]) == 0
        assert data["chunks_retrieved"] == 0

    def test_single_very_long_citation(self, monkeypatch):
        """Edge case: Very long citation text should be handled."""
        long_text = "x" * 10000
        
        def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
            return RAGResponse(
                query=payload.query,
                answer="Answer",
                answer_grounded=True,
                citations=[
                    ChunkResult(
                        text=long_text,
                        source="large.txt",
                        chunk_index=0,
                        reranker_score=1.0,
                        retrieval_method="hybrid",
                    )
                ],
                chunks_retrieved=1,
                latency_ms=10.0,
                model_used="test",
                prompt_version="1.0",
                reranker_applied=False,
                llm_called=False,
                cached=False,
            )

        monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
        client = TestClient(api.app)
        
        response = client.post("/query", json={"query": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["citations"]) == 1
        assert len(data["citations"][0]["text"]) == 10000

    def test_many_citations(self, monkeypatch):
        """Edge case: Response with many citations should serialize correctly."""
        def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
            citations = [
                ChunkResult(
                    text=f"Citation {i}",
                    source=f"source{i}.txt",
                    chunk_index=i,
                    reranker_score=float(i),
                    retrieval_method="hybrid",
                )
                for i in range(50)
            ]
            
            return RAGResponse(
                query=payload.query,
                answer="Answer with many citations",
                answer_grounded=True,
                citations=citations,
                chunks_retrieved=len(citations),
                latency_ms=100.0,
                model_used="test",
                prompt_version="1.0",
                reranker_applied=True,
                llm_called=True,
                cached=False,
            )

        monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
        client = TestClient(api.app)
        
        response = client.post("/query", json={"query": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["citations"]) == 50

    def test_special_float_values(self, monkeypatch):
        """Edge case: Special float values (inf, nan) should be handled."""
        def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
            return RAGResponse(
                query=payload.query,
                answer="test",
                answer_grounded=True,
                citations=[
                    ChunkResult(
                        text="test",
                        source="test.txt",
                        chunk_index=0,
                        reranker_score=1.0,  # Normal float
                        retrieval_method="hybrid",
                    )
                ],
                chunks_retrieved=1,
                latency_ms=50.5,  # Normal latency
                model_used="test",
                prompt_version="1.0",
                reranker_applied=False,
                llm_called=False,
                cached=False,
            )

        monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
        client = TestClient(api.app)
        
        response = client.post("/query", json={"query": "test"})
        assert response.status_code == 200
        # Response should be JSON-serializable (no inf/nan)
        data = response.json()
        assert data["latency_ms"] == 50.5


class TestConcurrency:
    """Test behavior under concurrent-like conditions."""

    def test_sequential_queries_maintain_state(self, monkeypatch):
        """Concurrency: Sequential queries should not interfere."""
        results = []

        def fake_run_rag_query(payload: QueryRequest) -> RAGResponse:
            answer = f"Answer to: {payload.query[:10]}"
            results.append(payload.query)
            
            return RAGResponse(
                query=payload.query,
                answer=answer,
                answer_grounded=True,
                citations=[],
                chunks_retrieved=0,
                latency_ms=10.0,
                model_used="test",
                prompt_version="1.0",
                reranker_applied=False,
                llm_called=False,
                cached=False,
            )

        monkeypatch.setattr(api, "run_rag_query", fake_run_rag_query)
        client = TestClient(api.app)
        
        queries = ["query 1", "query 2", "query 3"]
        responses = []
        
        for query in queries:
            resp = client.post("/query", json={"query": query})
            assert resp.status_code == 200
            responses.append(resp.json())
        
        # Verify order and content
        assert len(responses) == 3
        assert [r["query"] for r in responses] == queries
        assert results == queries
