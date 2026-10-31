"""Tests for src/eval/injection_eval.py."""

from __future__ import annotations

import pytest

from src.eval.injection_eval import evaluate_injections


def test_evaluate_injections_not_implemented() -> None:
    """evaluate_injections is a stub."""

    with pytest.raises(NotImplementedError):
        evaluate_injections()
