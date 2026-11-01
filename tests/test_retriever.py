"""Tests for src/rag/retriever.py."""

from __future__ import annotations

import pytest

from src.embeddings import FakeEmbeddingModel
from src.rag.retriever import RetrievedDocument, VectorStore
from src.sanitizer import sanitize


def test_retrieved_document_dataclass() -> None:
    """RetrievedDocument can be constructed."""
    doc = RetrievedDocument(text="sample", metadata={"id": "1"}, score=0.95)
    assert doc.text == "sample"
    assert doc.score == 0.95


def test_vector_store_rejects_plain_str(tmp_path: pytest.TempPathFactory) -> None:
    """VectorStore raises TypeError when given plain str in search or add."""
    fake = FakeEmbeddingModel(dimension=32)
    store = VectorStore(
        collection_name="test_col_err",
        persist_dir=str(tmp_path),
        embedder=fake,
    )

    with pytest.raises(TypeError, match="Expected SanitizedText"):
        store.search("unredacted query")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="Expected SanitizedText"):
        store.add(
            chunks=["unredacted chunk"],  # type: ignore[list-item]
            embeddings=[[0.1] * 32],
            metadatas=[{"source": "test"}],
        )


def test_vector_store_add_and_search(tmp_path: pytest.TempPathFactory) -> None:
    """VectorStore correctly stores and retrieves sanitized documents."""
    fake = FakeEmbeddingModel(dimension=32)
    store = VectorStore(
        collection_name="test_col_ok",
        persist_dir=str(tmp_path),
        embedder=fake,
    )

    r1 = sanitize("Employee policy states 30 days notice.")
    r2 = sanitize("Hospital discharge summary for patient treatment.")

    v1 = fake.embed([r1.safe]).tolist()
    v2 = fake.embed([r2.safe]).tolist()

    store.add(
        chunks=[r1.safe, r2.safe],
        embeddings=[v1[0], v2[0]],
        metadatas=[{"doc_id": "hr1"}, {"doc_id": "med1"}],
        ids=["hr1#0", "med1#0"],
    )

    q = sanitize("What is the employee notice period?")
    results = store.search(q.safe, k=2)

    assert len(results) == 2
    assert all(isinstance(r, RetrievedDocument) for r in results)
    assert results[0].metadata["doc_id"] in ["hr1", "med1"]
    assert 0.0 <= results[0].score <= 1.0
