from __future__ import annotations

from src.reranker import CrossEncoderReranker


class DummyCrossEncoderModel:
    def __init__(self, scores):
        self._scores = scores

    def predict(self, _pairs):
        return self._scores


def test_cross_encoder_reranker_sorts_by_score_desc(monkeypatch):
    reranker = CrossEncoderReranker()
    model = DummyCrossEncoderModel([0.1, 0.9, 0.4])
    monkeypatch.setattr(CrossEncoderReranker, "_load_model", classmethod(lambda cls: model))

    chunks = [
        {"text": "low", "source": "a.txt", "chunk_index": 1, "score": 0.1},
        {"text": "high", "source": "b.txt", "chunk_index": 2, "score": 0.1},
        {"text": "mid", "source": "c.txt", "chunk_index": 3, "score": 0.1},
    ]

    ranked = reranker.rerank("query", chunks, top_k=2)

    assert len(ranked) == 2
    assert ranked[0]["text"] == "high"
    assert ranked[1]["text"] == "mid"
    assert ranked[0]["reranker_score"] == 0.9


def test_cross_encoder_reranker_handles_single_chunk(monkeypatch):
    reranker = CrossEncoderReranker()
    model = DummyCrossEncoderModel([0.7])
    monkeypatch.setattr(CrossEncoderReranker, "_load_model", classmethod(lambda cls: model))

    chunks = [{"text": "only", "source": "only.txt", "chunk_index": 1, "score": 0.2}]
    ranked = reranker.rerank("query", chunks, top_k=3)

    assert len(ranked) == 1
    assert ranked[0]["text"] == "only"
    assert ranked[0]["reranker_score"] == 0.7


def test_cross_encoder_reranker_handles_empty_input():
    reranker = CrossEncoderReranker()

    assert reranker.rerank("query", [], top_k=3) == []
    assert reranker.rerank("   ", [{"text": "x"}], top_k=3) == []
