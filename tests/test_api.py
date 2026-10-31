"""Tests for src/api.py."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import app


def test_health_endpoint() -> None:
    """GET /health returns 200 with status ok."""

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
