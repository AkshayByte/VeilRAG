"""Shared pytest fixtures for veilrag tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from src.config import settings
from src.rag.ingest import ingest_documents


@pytest.fixture
def sample_text() -> str:
    """Return a synthetic text string with a person name and email."""

    return "Alice Smith can be reached at alice@example.com."


@pytest.fixture
def sample_text_with_pii() -> str:
    """Return a synthetic text string containing multiple PII types."""

    return (
        "John Doe's phone is 555-1234 and email is john@example.com. "
        "His Aadhaar is 1234 5678 9012."
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_vector_store(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[Path]:
    """Ensure tests run against an isolated temporary Chroma vector store containing corpus v1."""
    test_chroma_dir = tmp_path_factory.mktemp("chroma")
    original_persist_dir = settings.chroma_persist_dir
    settings.chroma_persist_dir = str(test_chroma_dir)

    try:
        ingest_documents(
            path="data/docs",
            corpus="v1",
            persist_dir=str(test_chroma_dir),
            reset=True,
        )
        yield test_chroma_dir
    finally:
        settings.chroma_persist_dir = original_persist_dir


