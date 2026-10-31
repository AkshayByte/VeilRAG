"""Tests for src/audit/verify.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.audit.verify import VerificationError, verify_chain


def test_verification_error_is_exception() -> None:
    """VerificationError is a subclass of Exception."""

    assert issubclass(VerificationError, Exception)


def test_verify_chain_not_implemented(tmp_path: Path) -> None:
    """verify_chain is a stub."""

    log_path = str(tmp_path / "audit.log.jsonl")
    with pytest.raises(NotImplementedError):
        verify_chain(log_path)
