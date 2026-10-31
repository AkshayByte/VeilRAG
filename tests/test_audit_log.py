"""Tests for src/audit/log.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.audit.log import AuditLogger, AuditRecord


def test_audit_record_defaults() -> None:
    """AuditRecord has sensible defaults."""

    record = AuditRecord(timestamp="2026-01-01T00:00:00Z", event_type="sanitize")
    assert record.event_type == "sanitize"
    assert record.entity_counts == {}
    assert record.prev_hash == ""
    assert record.record_hash == ""


def test_audit_logger_construct(tmp_path: Path) -> None:
    """AuditLogger can be instantiated with a path."""

    logger = AuditLogger(path=str(tmp_path / "audit.log.jsonl"))
    assert logger._path.endswith("audit.log.jsonl")


def test_log_sanitize_not_implemented(tmp_path: Path) -> None:
    """log_sanitize is a stub."""

    logger = AuditLogger(path=str(tmp_path / "audit.log.jsonl"))
    with pytest.raises(NotImplementedError):
        logger.log_sanitize({"PERSON": 1})
