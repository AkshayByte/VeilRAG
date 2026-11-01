"""Shared pytest fixtures for veilrag tests."""

from __future__ import annotations

import pytest


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
def setup_test_vector_store() -> None:
    """Ensure Chroma vector store has documents for test session if empty."""
    from src.config import settings
    from src.rag.ingest import ingest_documents
    from src.rag.retriever import VectorStore

    store = VectorStore(collection_name="docs", persist_dir=str(settings.chroma_persist_dir))
    if store._collection.count() == 0:
        ingest_documents(path="data/docs", corpus="v1")

