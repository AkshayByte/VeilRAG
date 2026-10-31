"""Tests for src/eval/pii_eval.py."""

from __future__ import annotations

from src.eval.pii_eval import Case, _span_overlap, evaluate_pii, format_table_markdown


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


def test_evaluate_pii_baseline() -> None:
    """evaluate_pii works in baseline mode."""

    case = Case(
        text="Contact Rahul Sharma at rahul@example.com",
        entities=[
            ("PERSON", 8, 20),
            ("EMAIL_ADDRESS", 24, 41),
        ],
    )
    results = evaluate_pii(cases=[case], baseline=True)
    assert results["baseline"] is True
    assert results["num_cases"] == 1


def test_span_overlap_calculation() -> None:
    """IoU calculation handles exact, partial, and non-overlapping spans."""

    # Exact match: IoU = 1.0
    assert _span_overlap(("PERSON", 0, 10), ("PERSON", 0, 10)) == 1.0

    # No overlap: IoU = 0.0
    assert _span_overlap(("PERSON", 0, 5), ("PERSON", 6, 10)) == 0.0

    # Partial overlap
    overlap = _span_overlap(("PERSON", 0, 10), ("PERSON", 5, 15))
    assert 0.0 < overlap < 1.0


def test_format_table_markdown() -> None:
    """format_table_markdown produces valid markdown table output."""

    case = Case(text="Hello world", entities=[])
    results = evaluate_pii(cases=[case], baseline=False)
    md = format_table_markdown(results, "Test Table")
    assert "### Test Table" in md
    assert "| Entity Type | Precision | Recall |" in md
