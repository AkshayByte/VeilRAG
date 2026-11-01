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
    """run_ingest_eval verifies committed documents against the active Chroma store."""
    from src.config import settings
    from src.rag.retriever import VectorStore

    store = VectorStore(collection_name="docs", persist_dir=str(settings.chroma_persist_dir))
    records = store.peek(n=5000)
    corpus = "v2" if len(records) > 20 else "v1"

    res = run_ingest_eval(corpus=corpus)
    if corpus == "v2":
        assert res.total_docs == 70
        assert res.total_chunks == 140
        assert res.survived_facts >= 280
    else:
        assert res.total_docs == 15
        assert res.in_scope_pattern_leaks == 0
        assert res.survived_facts == res.total_facts
        assert res.total_facts == 60


def test_run_ingest_eval_assertion_error_on_leak(tmp_path: Path) -> None:
    """run_ingest_eval raises AssertionError when in-scope pattern leak is detected."""
    from src.config import settings
    from src.rag.retriever import VectorStore

    store = VectorStore(collection_name="docs", persist_dir=str(settings.chroma_persist_dir))
    records = store.peek(n=5)
    doc_name = (
        records[0]["metadata"].get("source", "hr_policy_01.txt")
        if records
        else "hr_policy_01.txt"
    )
    # Find a word present in the chunk text to simulate a leaked pattern entity
    leak_val = "Starlight" if "Starlight" in records[0]["document"] else records[0]["document"][:8]

    fake_gt = tmp_path / "_ground_truth.json"
    fake_data: dict[str, Any] = {
        "documents": [
            {
                "filename": doc_name,
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

    with pytest.raises(AssertionError, match="SECURITY VIOLATION"):
        run_ingest_eval(ground_truth_path=fake_gt, strict=True)


