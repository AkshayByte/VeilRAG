"""Tests for src/eval/pii_eval.py."""

from __future__ import annotations

import pytest

from src.eval.pii_eval import evaluate_pii


def test_evaluate_pii_not_implemented() -> None:
    """evaluate_pii is a stub."""

    with pytest.raises(NotImplementedError):
        evaluate_pii()
