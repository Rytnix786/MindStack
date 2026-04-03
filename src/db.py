"""SQLite persistence and analytics for query metrics."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List

try:
    from .models import RAGResponse
except ImportError:  # pragma: no cover
    from models import RAGResponse


_DEFAULT_SQLITE_PATH = "data/metrics.db"


def _resolve_sqlite_path() -> Path:
    """Return resolved SQLite path from env var or default location."""
    raw_path = os.getenv("SQLITE_PATH", _DEFAULT_SQLITE_PATH).strip() or _DEFAULT_SQLITE_PATH
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parent.parent / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_sqlite_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create query_log table if it does not already exist."""
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                grounded INTEGER NOT NULL,
                cached INTEGER NOT NULL,
                chunks_retrieved INTEGER NOT NULL,
                reranker_applied INTEGER NOT NULL,
                llm_called INTEGER NOT NULL
            )
            """
        )
        conn.commit()


def insert_query_result(response: RAGResponse) -> None:
    """Insert one query response row into query_log."""
    normalized_query = response.query.strip().lower()
    query_hash = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()

    with closing(_get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO query_log (
                timestamp,
                query_hash,
                latency_ms,
                grounded,
                cached,
                chunks_retrieved,
                reranker_applied,
                llm_called
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                response.timestamp.isoformat(),
                query_hash,
                float(response.latency_ms),
                1 if response.answer_grounded else 0,
                1 if response.cached else 0,
                int(response.chunks_retrieved),
                1 if response.reranker_applied else 0,
                1 if response.llm_called else 0,
            ),
        )
        conn.commit()


def _percentile(sorted_values: List[float], ratio: float) -> float:
    if not sorted_values:
        return 0.0
    index = int(ratio * len(sorted_values))
    if index >= len(sorted_values):
        index = len(sorted_values) - 1
    return float(sorted_values[index])


def get_metrics_summary() -> Dict[str, Any]:
    """Return aggregate metrics from SQLite query_log."""
    with closing(_get_connection()) as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_queries,
                COALESCE(AVG(grounded), 0.0) AS grounded_rate,
                COALESCE(AVG(latency_ms), 0.0) AS avg_latency_ms
            FROM query_log
            """
        ).fetchone()

        latencies_rows = conn.execute("SELECT latency_ms FROM query_log ORDER BY latency_ms ASC").fetchall()
        latencies = [float(row["latency_ms"]) for row in latencies_rows]

        queries_last_24h_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM query_log
            WHERE datetime(timestamp) >= datetime('now', '-24 hours')
            """
        ).fetchone()

        grounded_rate_7d_row = conn.execute(
            """
            SELECT COALESCE(AVG(grounded), 0.0) AS grounded_rate_7d
            FROM query_log
            WHERE datetime(timestamp) >= datetime('now', '-7 days')
            """
        ).fetchone()

    total_queries = int(totals["total_queries"]) if totals else 0
    grounded_rate = float(totals["grounded_rate"]) if totals else 0.0
    avg_latency_ms = float(totals["avg_latency_ms"]) if totals else 0.0

    return {
        "total_queries": total_queries,
        "grounded_rate": grounded_rate,
        "avg_latency_ms": avg_latency_ms,
        "p95_latency_ms": _percentile(latencies, 0.95),
        "p50_latency_ms": _percentile(latencies, 0.50),
        "queries_last_24h": int(queries_last_24h_row["total"]) if queries_last_24h_row else 0,
        "grounded_rate_7d": float(grounded_rate_7d_row["grounded_rate_7d"]) if grounded_rate_7d_row else 0.0,
    }


def get_metrics_trend(days: int = 30) -> List[Dict[str, Any]]:
    """Return daily metrics aggregates for the last N days."""
    window = max(days - 1, 0)

    with closing(_get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT
                date(timestamp) AS date,
                COUNT(*) AS total_queries,
                COALESCE(AVG(grounded), 0.0) AS grounded_rate,
                COALESCE(AVG(latency_ms), 0.0) AS avg_latency_ms
            FROM query_log
            WHERE datetime(timestamp) >= datetime('now', ?)
            GROUP BY date(timestamp)
            ORDER BY date(timestamp) ASC
            """,
            (f"-{window} days",),
        ).fetchall()

    return [
        {
            "date": row["date"],
            "total_queries": int(row["total_queries"]),
            "grounded_rate": float(row["grounded_rate"]),
            "avg_latency_ms": float(row["avg_latency_ms"]),
        }
        for row in rows
    ]
