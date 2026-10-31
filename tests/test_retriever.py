"""Tests for src/rag/retriever.py."""

from __future__ import annotations

import pytest

from src.rag.retriever import RetrievedDocument, VectorStore


def test_retrieved_document_dataclass() -> None:
    """RetrievedDocument can be constructed."""

    doc = RetrievedDocument(text="sample", metadata={"id": "1"}, score=0.95)
    assert doc.text == "sample"
    assert doc.score == 0.95


def test_vector_store_search_not_implemented() -> None:
    """VectorStore.search is a stub."""

    store = VectorStore.__new__(VectorStore)  # bypass __init__
    with pytest.raises(NotImplementedError):
        store.search("query")
