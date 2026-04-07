from __future__ import annotations

from dataclasses import dataclass

from src import retrieval


@dataclass
class DummyDoc:
    page_content: str
    metadata: dict


class DummyVectorStore:
    def similarity_search_with_score(self, query: str, k: int):
        assert query == "refund policy"
        docs = [
            (DummyDoc("refund chunk", {"source": "refund_policy.txt", "chunk_index": 1}), 0.11),
            (DummyDoc("onboarding chunk", {"source": "onboarding_guide.txt", "chunk_index": 2}), 0.22),
            (DummyDoc("pricing chunk", {"source": "product_docs.txt", "chunk_index": 3}), 0.33),
        ]
        return docs[:k]


class DummyBm25:
    def get_scores(self, _tokens):
        return [0.1, 0.9, 0.4]


def test_retrieve_chunks_returns_top_k_results(monkeypatch):
    monkeypatch.setattr(retrieval, "_VECTORSTORE", DummyVectorStore())

    chunks = retrieval.retrieve_chunks("refund policy", top_k=2)

    assert len(chunks) == 2
    assert chunks[0]["source"] == "refund_policy.txt"
    assert chunks[1]["source"] == "onboarding_guide.txt"
    assert all(chunk["retrieval_method"] == "vector" for chunk in chunks)


def test_retrieve_chunks_handles_empty_index_gracefully(monkeypatch):
    monkeypatch.setattr(retrieval, "_VECTORSTORE", None)

    chunks = retrieval.retrieve_chunks("anything", top_k=5)

    assert chunks == []


def test_bm25_search_returns_top_k_results(monkeypatch):
    payload = {
        "bm25": DummyBm25(),
        "documents": [
            {"page_content": "a", "metadata": {"source": "a.txt", "chunk_index": 1}},
            {"page_content": "b", "metadata": {"source": "b.txt", "chunk_index": 2}},
            {"page_content": "c", "metadata": {"source": "c.txt", "chunk_index": 3}},
        ],
    }
    monkeypatch.setattr(retrieval, "_BM25_PAYLOAD", payload)

    chunks = retrieval.bm25_search("query tokens", top_k=2)

    assert len(chunks) == 2
    assert chunks[0]["source"] == "b.txt"
    assert chunks[1]["source"] == "c.txt"
    assert all(chunk["retrieval_method"] == "bm25" for chunk in chunks)


def test_bm25_search_handles_empty_index_gracefully(monkeypatch):
    monkeypatch.setattr(retrieval, "_BM25_PAYLOAD", {})

    chunks = retrieval.bm25_search("query", top_k=3)

    assert chunks == []


def test_generate_answer_refuses_on_low_evidence_confidence(monkeypatch):
    monkeypatch.setattr(
        retrieval,
        "load_prompt_config",
        lambda: {"system_prompt": "test", "refusal_token": "INSUFFICIENT_CONTEXT", "version": "test"},
    )
    monkeypatch.setattr(retrieval, "_REFUSAL_CONFIDENCE_ENABLED", True)
    monkeypatch.setattr(retrieval, "_REFUSAL_CONFIDENCE_THRESHOLD", 0.22)

    # Tiny overlap + weak score passes relevance gate but remains low confidence.
    chunks = [
        {
            "text": "refund generic info",
            "source": "refund_policy.txt",
            "chunk_index": 1,
            "reranker_score": 0.1,
            "retrieval_method": "hybrid",
        }
    ]

    result = retrieval.generate_answer(
        "refund policy cancellation enterprise annual discount invoice support login",
        chunks,
    )

    assert result["answer"] == "INSUFFICIENT_CONTEXT"
    assert result["answer_grounded"] is False
    assert result["model_used"] == "confidence-gate"
    assert result["llm_called"] is False


def test_generate_answer_does_not_force_fallback_when_disabled(monkeypatch):
    class _FakeOllamaClient:
        def __init__(self, host=None):
            self.host = host

        def chat(self, **_kwargs):
            return {"message": {"content": "INSUFFICIENT_CONTEXT"}}

    class _FakeOllamaModule:
        Client = _FakeOllamaClient

    monkeypatch.setattr(
        retrieval,
        "load_prompt_config",
        lambda: {"system_prompt": "test", "refusal_token": "INSUFFICIENT_CONTEXT", "version": "test"},
    )
    monkeypatch.setattr(retrieval, "_ENABLE_EXTRACTIVE_FAST_PATH", False)
    monkeypatch.setattr(retrieval, "_REFUSAL_CONFIDENCE_ENABLED", True)
    monkeypatch.setattr(retrieval, "_REFUSAL_CONFIDENCE_THRESHOLD", 0.1)
    monkeypatch.setattr(retrieval, "_FORCE_FALLBACK_ON_MODEL_REFUSAL", False)
    monkeypatch.setattr(retrieval.importlib, "import_module", lambda _name: _FakeOllamaModule)

    chunks = [
        {
            "text": "Customers may return products within 30 days of purchase.",
            "source": "refund_policy.txt",
            "chunk_index": 1,
            "reranker_score": 4.2,
            "retrieval_method": "hybrid",
        }
    ]

    result = retrieval.generate_answer("What is the refund policy?", chunks)

    assert result["answer"] == "INSUFFICIENT_CONTEXT"
    assert result["answer_grounded"] is False


def test_generate_answer_forces_fallback_only_when_enabled(monkeypatch):
    class _FakeOllamaClient:
        def __init__(self, host=None):
            self.host = host

        def chat(self, **_kwargs):
            return {"message": {"content": "INSUFFICIENT_CONTEXT"}}

    class _FakeOllamaModule:
        Client = _FakeOllamaClient

    monkeypatch.setattr(
        retrieval,
        "load_prompt_config",
        lambda: {"system_prompt": "test", "refusal_token": "INSUFFICIENT_CONTEXT", "version": "test"},
    )
    monkeypatch.setattr(retrieval, "_ENABLE_EXTRACTIVE_FAST_PATH", False)
    monkeypatch.setattr(retrieval, "_REFUSAL_CONFIDENCE_ENABLED", True)
    monkeypatch.setattr(retrieval, "_REFUSAL_CONFIDENCE_THRESHOLD", 0.1)
    monkeypatch.setattr(retrieval, "_FORCE_FALLBACK_ON_MODEL_REFUSAL", True)
    monkeypatch.setattr(retrieval, "_FORCE_FALLBACK_CONFIDENCE_THRESHOLD", 0.5)
    monkeypatch.setattr(retrieval.importlib, "import_module", lambda _name: _FakeOllamaModule)

    chunks = [
        {
            "text": "Company Refund Policy: Customers may return products within 30 days.",
            "source": "refund_policy.txt",
            "chunk_index": 1,
            "reranker_score": 4.6,
            "retrieval_method": "hybrid",
        }
    ]

    result = retrieval.generate_answer("What is the refund policy?", chunks)

    assert result["answer_grounded"] is True
    assert "30 days" in result["answer"]
