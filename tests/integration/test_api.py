from __future__ import annotations

import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient

from src import api
from src.db import init_db


@pytest.mark.asyncio
async def test_health_returns_200():
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_returns_expected_schema(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "metrics_test.db"
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    init_db()

    with closing(sqlite3.connect(sqlite_path)) as conn:
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
            ("2026-04-03T10:00:00", "h1", 100.0, 1, 0, 2, 1, 1),
        )
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
            ("2026-04-03T10:01:00", "h2", 300.0, 0, 0, 0, 1, 1),
        )
        conn.commit()

    client = TestClient(api.app)

    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "total_queries",
        "grounded_rate",
        "avg_latency_ms",
        "p95_latency_ms",
        "p50_latency_ms",
        "queries_last_24h",
        "grounded_rate_7d",
    }
    assert data["total_queries"] == 2
    assert data["grounded_rate"] == 0.5
    assert data["avg_latency_ms"] == 200.0
    assert data["p95_latency_ms"] == 300.0
    assert data["p50_latency_ms"] == 300.0
    assert isinstance(data["queries_last_24h"], int)
    assert isinstance(data["grounded_rate_7d"], float)


def test_ingest_triggers_reindex(monkeypatch):
    called = {"value": False}

    def fake_run(*args, **kwargs):
        called["value"] = True
        assert args[0] == ["python", "-m", "src.ingestion"]
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    client = TestClient(api.app)

    response = client.post("/ingest")

    assert called["value"] is True
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["stdout"] == "ok"


@pytest.mark.asyncio
async def test_metrics_trend_returns_daily_aggregates(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "metrics_trend.db"
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    init_db()

    with closing(sqlite3.connect(sqlite_path)) as conn:
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
            ("2026-04-01T10:00:00", "t1", 120.0, 1, 0, 2, 1, 1),
        )
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
            ("2026-04-01T11:00:00", "t2", 180.0, 0, 0, 1, 1, 1),
        )
        conn.commit()

    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics/trend")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert set(first.keys()) == {"date", "total_queries", "grounded_rate", "avg_latency_ms"}
