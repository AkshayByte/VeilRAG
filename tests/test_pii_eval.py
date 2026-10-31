"""Tests for src/eval/pii_eval.py."""

from __future__ import annotations

from src.eval.pii_eval import (
    Case,
    _span_overlap,
    compute_clean_case_fpr,
    evaluate_pii,
    format_table_markdown,
)


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


def test_clean_case_fpr_hand_computed_example() -> None:
    """clean-case FPR = (PII-free flagged cases) / (number of PII-free cases)."""

    # 4 clean cases with 0 gold entities:
    # 3 unflagged clean cases, 1 flagged clean case with a false positive -> FPR = 1/4 = 0.25
    cases = [
        Case(text="Clean sentence one.", entities=[]),
        Case(text="Clean sentence two.", entities=[]),
        Case(text="Clean sentence three.", entities=[]),
        Case(text="Clean sentence four.", entities=[]),
    ]
    case_findings = [
        [],
        [],
        [],
        [{"type": "PERSON", "start": 0, "end": 5, "result": "false_positive"}],
    ]
    fpr, total_clean, flagged_clean, per_type_fpr = compute_clean_case_fpr(cases, case_findings)
    assert total_clean == 4
    assert flagged_clean == 1
    assert fpr == 0.25
    assert per_type_fpr["PERSON"] == 0.25


def test_no_shared_templates_between_dev_and_heldout() -> None:
    """No template text from the dev set generator may be shared with the heldout set generator."""
    import ast
    from pathlib import Path

    dev_path = Path("src/eval/gen_pii_cases.py")
    heldout_path = Path("scripts/gen_pii_heldout.py")

    assert dev_path.exists(), "src/eval/gen_pii_cases.py not found"
    assert heldout_path.exists(), "scripts/gen_pii_heldout.py not found"

    def extract_templates(file_path: Path) -> set[str]:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        templates: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.strip()
                # A template has placeholders like {name}, {num}, {pan}, {email}, etc.
                if "{" in val and "}" in val and len(val) > 10:
                    templates.add(val)
        return templates

    dev_templates = extract_templates(dev_path)
    heldout_templates = extract_templates(heldout_path)

    shared = dev_templates & heldout_templates
    assert len(shared) == 0, f"Found shared templates between dev and heldout: {shared}"
    assert len(dev_templates) > 0
    assert len(heldout_templates) > 0
