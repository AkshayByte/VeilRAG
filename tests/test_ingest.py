"""Tests for src/rag/ingest.py."""

from __future__ import annotations

import pytest

from src.rag.ingest import DocumentChunk, chunk_text, ingest_documents, load_documents


def test_document_chunk_dataclass() -> None:
    """DocumentChunk can be constructed."""

    chunk = DocumentChunk(doc_id="doc1", chunk_index=0, text="sample", metadata={})
    assert chunk.doc_id == "doc1"
    assert chunk.chunk_index == 0


def test_chunk_text_not_implemented() -> None:
    """chunk_text is a stub."""

    with pytest.raises(NotImplementedError):
        chunk_text("some text")


def test_load_documents_not_implemented() -> None:
    """load_documents is a stub."""

    with pytest.raises(NotImplementedError):
        load_documents()


def test_ingest_documents_not_implemented() -> None:
    """ingest_documents is a stub."""

    with pytest.raises(NotImplementedError):
        ingest_documents()
