"""Tests for src/eval/rag_eval.py."""

from __future__ import annotations

import pytest

from src.eval.rag_eval import evaluate_rag


def test_evaluate_rag_not_implemented() -> None:
    """evaluate_rag is a stub."""

    with pytest.raises(NotImplementedError):
        evaluate_rag()
