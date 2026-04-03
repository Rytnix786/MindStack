"""Reranking utilities for retrieved chunks."""

import importlib
from typing import Any, Dict, List, Optional


class Reranker:
    """Token-overlap reranker used as a deterministic baseline."""

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in text.lower().split() if token}

    def rerank(self, query: str, candidates: List[Dict[str, object]], top_k: int) -> List[Dict[str, object]]:
        """Rerank retrieved chunks by overlap with query terms."""
        q_tokens = self._tokenize(query)

        rescored: List[Dict[str, object]] = []
        for item in candidates:
            chunk_tokens = self._tokenize(str(item.get("content", "")))
            overlap = len(q_tokens.intersection(chunk_tokens))
            updated = dict(item)
            updated["reranker_score"] = float(overlap)
            rescored.append(updated)

        rescored.sort(key=lambda x: x["reranker_score"], reverse=True)  # type: ignore
        return rescored[: max(top_k, 0)]


class CrossEncoderReranker:
    """Uses a cross-encoder model to rerank retrieved chunks."""

    _model: Optional[Any] = None

    def __init__(self) -> None:
        """Initialize reranker; loads model lazily on first use."""
        pass

    @classmethod
    def _load_model(cls) -> Any:
        """Load cross-encoder model (lazy, cached at class level)."""
        if cls._model is None:
            print("Loading cross-encoder model 'cross-encoder/ms-marco-MiniLM-L-6-v2'...")
            from sentence_transformers import CrossEncoder

            cls._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            print("Cross-encoder model loaded.")
        return cls._model

    def rerank(
        self, query: str, chunks: List[Dict[str, Any]], top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Rerank chunks using cross-encoder and return top_k by score."""
        if not chunks or not query.strip():
            return []

        try:
            model = self._load_model()

            print(f"Reranking {len(chunks)} chunks with cross-encoder...")
            pairs = [[query, chunk.get("text", "")] for chunk in chunks]
            scores = model.predict(pairs)

            scored_chunks: List[Dict[str, Any]] = []
            for chunk, score in zip(chunks, scores):
                updated = dict(chunk)
                updated["reranker_score"] = float(score)
                scored_chunks.append(updated)

            scored_chunks.sort(key=lambda x: x["reranker_score"], reverse=True)
            result = scored_chunks[: max(top_k, 0)]

            print(f"Reranking complete: {len(chunks)} chunks → {len(result)} top chunks")
            return result

        except Exception as exc:  # pylint: disable=broad-except
            print(f"Reranking failed: {exc}. Falling back to top {top_k} by original score.")
            chunks_sorted = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
            return chunks_sorted[: max(top_k, 0)]
