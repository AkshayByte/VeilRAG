"""Tests for src/rag/ingest.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.embeddings import FakeEmbeddingModel
from src.rag.ingest import DocumentChunk, chunk_text, ingest_documents, load_documents
from src.rag.retriever import VectorStore
from src.sanitizer import SanitizedText, sanitize


def test_document_chunk_dataclass() -> None:
    """DocumentChunk can be constructed."""
    res = sanitize("Sample text")
    chunk = DocumentChunk(doc_id="doc1", chunk_index=0, text=res.safe, metadata={})
    assert chunk.doc_id == "doc1"
    assert chunk.chunk_index == 0
    assert isinstance(chunk.text, SanitizedText)


def test_chunk_text_rejects_plain_str() -> None:
    """chunk_text raises TypeError when given a plain str instead of SanitizedText."""
    with pytest.raises(TypeError, match="Expected SanitizedText"):
        chunk_text("unredacted text")  # type: ignore[arg-type]


def test_chunk_text_produces_sanitized_chunks() -> None:
    """chunk_text creates SanitizedText chunks respecting token bounds."""
    text = (
        "Section 1: General provisions. "
        "The company provides 30 days of annual leave to confirmed personnel. "
        "Working hours are from 9:30 AM to 6:30 PM Monday through Friday. "
        "Employees must adhere strictly to information security practices. "
        "Section 2: Health benefits and casual sick leave guidelines."
    )
    res = sanitize(text)
    chunks = chunk_text(res.safe, chunk_size=20, overlap=5)

    assert len(chunks) >= 2
    for c in chunks:
        assert isinstance(c, SanitizedText)
        assert len(c.strip()) > 0


def test_load_documents_from_directory(tmp_path: Path) -> None:
    """load_documents loads all valid .txt and .md files and ignores hidden ones."""
    (tmp_path / "hr_policy_test.txt").write_text("Policy content", encoding="utf-8")
    (tmp_path / "loan_agreement_test.md").write_text("Agreement content", encoding="utf-8")
    (tmp_path / "_internal.txt").write_text("Ignored", encoding="utf-8")
    (tmp_path / ".gitkeep").write_text("Ignored", encoding="utf-8")

    docs = load_documents(str(tmp_path))
    assert len(docs) == 2
    ids = [d["id"] for d in docs]
    assert "hr_policy_test.txt" in ids
    assert "loan_agreement_test.md" in ids
    assert "_internal.txt" not in ids


def test_ingest_documents_idempotent_and_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ingestion is idempotent, fail-closed per doc, and persists no raw PII to metadata."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    d1 = docs_dir / "hr_policy_01.txt"
    d1.write_text(
        "Notice period is 60 calendar days. Contact HR Ananya Sharma at ananya@acmesoftware.in.",
        encoding="utf-8",
    )

    d2 = docs_dir / "loan_agreement_01.txt"
    d2.write_text(
        "Loan amount is INR 45,00,000 for borrower Siddharth Roy.",
        encoding="utf-8",
    )

    chroma_dir = tmp_path / "chroma"
    fake_embedder = FakeEmbeddingModel(dimension=32)

    # First ingestion run
    count1 = ingest_documents(
        path=str(docs_dir),
        collection_name="test_ingest",
        persist_dir=str(chroma_dir),
        embedder=fake_embedder,
        chunk_size=100,
        chunk_overlap=20,
    )
    assert count1 >= 2

    # Second ingestion run (idempotency check)
    count2 = ingest_documents(
        path=str(docs_dir),
        collection_name="test_ingest",
        persist_dir=str(chroma_dir),
        embedder=fake_embedder,
        chunk_size=100,
        chunk_overlap=20,
    )
    assert count2 == count1

    # Verify VectorStore content and metadata
    store = VectorStore(
        collection_name="test_ingest",
        persist_dir=str(chroma_dir),
        embedder=fake_embedder,
    )
    records = store.peek(n=10)
    assert len(records) == count1

    for r in records:
        meta: dict[str, Any] = r["metadata"]
        assert "source" in meta
        assert "doc_type" in meta
        assert "chunk_id" in meta
        assert "entity_count" in meta
        assert "risk_score" in meta
        # Verify no raw PII names leaked into metadata
        for k, v in meta.items():
            assert "Ananya Sharma" not in str(v)
            assert "ananya@acmesoftware.in" not in str(v)
            assert "Siddharth Roy" not in str(v)


def test_ingest_uses_pipeline_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ingest_documents passes PIPELINE_MODE to sanitize."""
    import src.rag.ingest as ingest_mod
    from src.config import PIPELINE_MODE

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "test_doc.txt").write_text("Some text to ingest.", encoding="utf-8")

    modes_passed: list[str] = []
    orig_sanitize = ingest_mod.sanitize

    def spy_sanitize(text: str, mode: str = "general", **kwargs: Any) -> Any:
        modes_passed.append(mode)
        return orig_sanitize(text, mode=mode, **kwargs)

    monkeypatch.setattr(ingest_mod, "sanitize", spy_sanitize)
    fake_embedder = FakeEmbeddingModel(dimension=16)

    ingest_documents(
        path=str(docs_dir),
        collection_name="test_pipeline_mode",
        persist_dir=str(tmp_path / "chroma"),
        embedder=fake_embedder,
    )

    assert len(modes_passed) == 1
    assert modes_passed[0] == PIPELINE_MODE
