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
