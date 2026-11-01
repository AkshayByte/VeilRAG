"""Tests for src/eval/ingest_eval.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.eval.ingest_eval import (
    IngestEvalResult,
    _scan_disk_for_bytes,
    generate_markdown_report,
    run_ingest_eval,
)


def test_scan_disk_for_bytes(tmp_path: Path) -> None:
    """_scan_disk_for_bytes finds binary matches in directory."""
    f1 = tmp_path / "test.bin"
    f1.write_bytes(b"some prefix SECRET123 suffix")
    f2 = tmp_path / "clean.bin"
    f2.write_bytes(b"completely clean file")

    matches = _scan_disk_for_bytes(b"SECRET123", tmp_path)
    assert len(matches) == 1
    assert str(f1) in matches[0]

    no_matches = _scan_disk_for_bytes(b"NOT_FOUND", tmp_path)
    assert len(no_matches) == 0


def test_generate_markdown_report(tmp_path: Path) -> None:
    """generate_markdown_report outputs valid markdown table."""
    res = IngestEvalResult(
        total_docs=2,
        total_chunks=3,
        corpus="v1",
        in_scope_pattern_leaks=0,
        person_planted=5,
        person_leaks=0,
        out_of_scope_planted=4,
        out_of_scope_leaks=2,
        char_metrics={
            "gold_chars": 100,
            "leaked_chars": 0,
            "leak_rate": 0.0,
            "non_pii_chars": 1000,
            "over_redacted_chars": 10,
            "over_redaction_rate": 0.01,
        },
        total_facts=4,
        survived_facts=4,
        fact_details=[
            {"doc": "d1.txt", "fact_name": "notice", "fact_value": "30 days", "survived": True}
        ],
    )
    report_file = tmp_path / "test_report.md"
    report = generate_markdown_report(res, out_path=report_file)
    assert "# VeilRAG Secure Ingestion & Local Retrieval Audit Report" in report
    assert "PASS (0 Leaks)" in report
    assert report_file.exists()


def test_run_ingest_eval_real_data() -> None:
    """run_ingest_eval verifies committed documents for corpus v1."""
    res = run_ingest_eval(corpus="v1")
    assert res.total_docs == 15
    assert res.total_chunks >= 15
    assert res.in_scope_pattern_leaks == 0
    assert res.survived_facts == res.total_facts
    assert res.total_facts == 60


def test_run_ingest_eval_empty_store_raises(tmp_path: Path) -> None:
    """run_ingest_eval raises ValueError if vector store has 0 chunks."""
    empty_chroma = tmp_path / "empty_chroma"
    with pytest.raises(ValueError, match="Vector store is empty"):
        run_ingest_eval(corpus="v1", persist_dir=str(empty_chroma))


def test_run_ingest_eval_fewer_chunks_than_docs_raises(tmp_path: Path) -> None:
    """run_ingest_eval raises ValueError if vector store has fewer chunks than documents."""
    fewer_chroma = tmp_path / "fewer_chroma"
    from src.embeddings import FakeEmbeddingModel
    from src.rag.retriever import VectorStore
    from src.sanitizer import SanitizedText

    store = VectorStore(
        collection_name="docs",
        persist_dir=str(fewer_chroma),
        embedder=FakeEmbeddingModel(dimension=32),
    )
    chunk = SanitizedText("Only one chunk", _sentinel=SanitizedText._SENTINEL)
    store.add(
        chunks=[chunk],
        embeddings=[[0.0] * 32],
        metadatas=[{"source": "hr_policy_01.txt"}],
        ids=["hr_policy_01.txt#chunk_0"],
    )

    with pytest.raises(ValueError, match="fewer chunks"):
        run_ingest_eval(corpus="v1", persist_dir=str(fewer_chroma))


def test_run_ingest_eval_planted_leak_triggers_security_violation(tmp_path: Path) -> None:
    """A tmp store with a planted known value triggers the SECURITY VIOLATION assertion."""
    from src.embeddings import FakeEmbeddingModel
    from src.rag.retriever import VectorStore
    from src.sanitizer import SanitizedText

    leak_chroma = tmp_path / "leak_chroma"
    fake_gt = tmp_path / "_ground_truth.json"

    leak_val = "SECRET_LEAKED_PAN_123"
    fake_data: dict[str, Any] = {
        "documents": [
            {
                "filename": "planted_doc.txt",
                "key_facts": {},
                "pii_entities": [
                    {
                        "type": "PAN",
                        "value": leak_val,
                        "start": 0,
                        "end": len(leak_val),
                        "in_scope": True,
                    }
                ],
            }
        ]
    }
    fake_gt.write_text(json.dumps(fake_data), encoding="utf-8")

    store = VectorStore(
        collection_name="docs",
        persist_dir=str(leak_chroma),
        embedder=FakeEmbeddingModel(dimension=32),
    )
    chunk = SanitizedText(
        f"Notice: the customer PAN is {leak_val}.",
        _sentinel=SanitizedText._SENTINEL,
    )
    store.add(
        chunks=[chunk],
        embeddings=[[0.0] * 32],
        metadatas=[{"source": "planted_doc.txt"}],
        ids=["planted_doc.txt#chunk_0"],
    )

    with pytest.raises(AssertionError, match="SECURITY VIOLATION"):
        run_ingest_eval(ground_truth_path=fake_gt, persist_dir=str(leak_chroma), strict=True)



