"""Tests for src/eval/pii_eval.py."""

from __future__ import annotations

import pytest

from src.eval.pii_eval import Case, evaluate_pii


def test_evaluate_pii_returns_metrics() -> None:
    """evaluate_pii returns precision, recall, f1, and overall metrics."""

    case = Case(
        text="Contact Rahul Sharma at rahul@example.com",
        entities=[
            ("PERSON", 8, 20),
            ("EMAIL_ADDRESS", 24, 41),
        ],
    )
    results = evaluate_pii(cases=[case], baseline=False)
    assert "overall" in results
    assert "precision" in results["overall"]
    assert "recall" in results["overall"]
    assert "f1" in results["overall"]
    assert results["num_cases"] == 1
