"""PII sanitization evaluation.

Loads ``data/eval/pii_cases.jsonl`` and computes per-entity-type and overall
precision, recall, F1, and false-positive rate for the VeilRAG sanitizer
against known gold spans. A ``--baseline`` flag runs Microsoft Presidio
defaults (built-in recognizers only, no custom recognizers) for comparison.

Results are written to ``data/eval/pii_results.json`` and ``docs/pii_results.md``.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from presidio_analyzer import AnalyzerEngine

from src.sanitizer import sanitize

logger = logging.getLogger(__name__)

# Singleton Presidio AnalyzerEngine — construction is expensive; reuse it.
_ANALYZER_CACHE: AnalyzerEngine | None = None


def _get_presidio_analyzer() -> AnalyzerEngine:
    """Return the cached Presidio AnalyzerEngine instance."""
    global _ANALYZER_CACHE
    if _ANALYZER_CACHE is None:
        _ANALYZER_CACHE = AnalyzerEngine()
    return _ANALYZER_CACHE


HERE = Path(__file__).parent
DATA_DIR = HERE.parent.parent / "data" / "eval"
CASES_PATH = DATA_DIR / "pii_cases.jsonl"
RESULTS_PATH = DATA_DIR / "pii_results.json"
DOCS_RESULTS_PATH = HERE.parent.parent / "docs" / "pii_results.md"

SPAN_OVERLAP_THRESHOLD = 0.80

ALL_EVAL_ENTITIES: list[str] = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "URL",
    "IDENTITY_DOCUMENT",
    "PAN_NUMBER",
    "IFSC_CODE",
    "UPI_ID",
    "INDIAN_MOBILE",
    "MEDICAL_RECORD_NUMBER",
    "PATIENT_ID",
    "AWS_ACCESS_KEY",
    "AWS_SECRET_KEY",
    "SECRET_KEY",
]


@dataclass
class Case:
    """A single labeled evaluation case."""

    text: str
    entities: list[tuple[str, int, int]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Case:
        """Build a :class:`Case` from a JSONL record."""
        return cls(
            text=data["text"],
            entities=[(e["type"], e["start"], e["end"]) for e in data.get("entities", [])],
        )


@dataclass
class Metrics:
    """Precision/recall/F1/false-positive-rate for one configuration."""

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        return self._safe_div(self.true_positives, self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        return self._safe_div(self.true_positives, self.true_positives + self.false_negatives)

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 0.0 if (p + r) == 0 else 2 * p * r / (p + r)

    @property
    def false_positive_rate(self) -> float:
        return self._safe_div(self.false_positives, self.false_positives + self.false_negatives)

    @staticmethod
    def _safe_div(num: int, den: int) -> float:
        return num / den if den > 0 else 0.0

    def __add__(self, other: Metrics) -> Metrics:
        return Metrics(
            true_positives=self.true_positives + other.true_positives,
            false_positives=self.false_positives + other.false_positives,
            false_negatives=self.false_negatives + other.false_negatives,
        )


def _span_overlap(gold: tuple[str, int, int], det: tuple[str, int, int]) -> float:
    """Return IoU between two spans."""
    gold_start, gold_end = gold[1], gold[2]
    det_start, det_end = det[1], det[2]
    inter = max(0, min(gold_end, det_end) - max(gold_start, det_start))
    union = max(gold_end, det_end) - min(gold_start, det_start)
    return inter / union if union > 0 else 0.0


def _matches_gold(detected: tuple[str, int, int], gold: list[tuple[str, int, int]]) -> bool:
    """True if the detected span overlaps a gold span of the same type enough."""
    for g in gold:
        if g[0] != detected[0]:
            continue
        if _span_overlap(g, detected) >= SPAN_OVERLAP_THRESHOLD:
            return True
    return False


def evaluate_case(
    case: Case, *, baseline: bool = False
) -> tuple[int, int, int, int, list[dict[str, Any]]]:
    """Evaluate a single case against gold spans.

    Returns a 4-tuple of (tp, fp, fn, total_gold) plus a list of per-entity
    findings for the report.
    """
    if baseline:
        results = _get_presidio_analyzer().analyze(text=case.text, language="en")
        detected: list[tuple[str, int, int]] = [(r.entity_type, r.start, r.end) for r in results]
    else:
        result = sanitize(case.text, extra_entities=ALL_EVAL_ENTITIES)
        detected = [(e.entity_type, e.start, e.end) for e in result.entities]

    gold = case.entities
    tp = fp = fn = 0
    findings: list[dict[str, Any]] = []

    for det in detected:
        if _matches_gold(det, gold):
            tp += 1
            findings.append(
                {"type": det[0], "start": det[1], "end": det[2], "result": "true_positive"}
            )
        else:
            fp += 1
            findings.append(
                {"type": det[0], "start": det[1], "end": det[2], "result": "false_positive"}
            )

    for g in gold:
        if not any(
            _span_overlap(g, det) >= SPAN_OVERLAP_THRESHOLD
            for det in detected
            if det[0] == g[0]
        ):
            fn += 1
            findings.append(
                {"type": g[0], "start": g[1], "end": g[2], "result": "false_negative"}
            )

    return tp, fp, fn, len(gold), findings


def _collect_metrics(
    cases: list[Case],
    *,
    baseline: bool = False,
) -> tuple[Metrics, dict[str, Metrics], list[dict[str, Any]]]:
    """Run evaluation over all cases, returning overall and per-type metrics."""
    overall = Metrics()
    per_type: dict[str, Metrics] = {}
    findings: list[dict[str, Any]] = []

    for case in cases:
        tp, fp, fn, total_gold, per_case = evaluate_case(case, baseline=baseline)
        findings.extend(per_case)
        overall += Metrics(tp, fp, fn)
        for f in per_case:
            m = per_type.setdefault(f["type"], Metrics())
            if f["result"] == "true_positive":
                m.true_positives += 1
            elif f["result"] == "false_positive":
                m.false_positives += 1
            elif f["result"] == "false_negative":
                m.false_negatives += 1

    return overall, per_type, findings


def evaluate(
    cases: list[Case],
    *,
    baseline: bool = False,
) -> dict[str, Any]:
    """Evaluate all *cases* and return a structured result."""
    overall, per_type, findings = _collect_metrics(cases, baseline=baseline)
    return {
        "baseline": baseline,
        "num_cases": len(cases),
        "overall": {
            "true_positives": overall.true_positives,
            "false_positives": overall.false_positives,
            "false_negatives": overall.false_negatives,
            "precision": round(overall.precision, 4),
            "recall": round(overall.recall, 4),
            "f1": round(overall.f1, 4),
            "false_positive_rate": round(overall.false_positive_rate, 4),
        },
        "per_entity_type": {
            k: {
                "true_positives": v.true_positives,
                "false_positives": v.false_positives,
                "false_negatives": v.false_negatives,
                "precision": round(v.precision, 4),
                "recall": round(v.recall, 4),
                "f1": round(v.f1, 4),
                "false_positive_rate": round(v.false_positive_rate, 4),
            }
            for k, v in sorted(per_type.items())
        },
        "findings": findings,
    }


def format_table_markdown(results: dict[str, Any], title: str) -> str:
    """Format evaluation results as a clean Markdown table."""
    overall = results["overall"]
    per_type = results["per_entity_type"]

    lines: list[str] = [
        f"### {title}",
        "",
        f"- Cases evaluated: {results['num_cases']}",
        f"- Span overlap threshold (IoU): {SPAN_OVERLAP_THRESHOLD:.0%}",
        "",
        "| Entity Type | Precision | Recall | F1 Score | FPR | TP | FP | FN |",
        "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for et, m in sorted(per_type.items()):
        lines.append(
            f"| `{et}` | {m['precision']:.4f} | {m['recall']:.4f} | "
            f"{m['f1']:.4f} | {m['false_positive_rate']:.4f} | "
            f"{m['true_positives']} | {m['false_positives']} | {m['false_negatives']} |"
        )

    lines.append(
        f"| **OVERALL** | **{overall['precision']:.4f}** | **{overall['recall']:.4f}** | "
        f"**{overall['f1']:.4f}** | **{overall['false_positive_rate']:.4f}** | "
        f"**{overall['true_positives']}** | **{overall['false_positives']}** | "
        f"**{overall['false_negatives']}** |"
    )
    return "\n".join(lines)


def print_table(results: dict[str, Any], title: str) -> None:
    """Print formatted evaluation metrics to the console."""
    overall = results["overall"]
    per_type = results["per_entity_type"]

    print("\n" + "=" * 90)
    print(f" {title.upper()} (Cases: {results['num_cases']}, IoU: {SPAN_OVERLAP_THRESHOLD:.0%})")
    print("=" * 90)
    header = (
        f"{'Entity Type':<24} | {'Precision':<9} | {'Recall':<9} | {'F1':<9} | "
        f"{'FPR':<9} | {'TP':<4} | {'FP':<4} | {'FN':<4}"
    )
    print(header)
    print("-" * 90)

    for et, m in sorted(per_type.items()):
        row = (
            f"{et:<24} | {m['precision']:<9.4f} | {m['recall']:<9.4f} | {m['f1']:<9.4f} | "
            f"{m['false_positive_rate']:<9.4f} | {m['true_positives']:<4} | "
            f"{m['false_positives']:<4} | {m['false_negatives']:<4}"
        )
        print(row)

    print("-" * 90)
    overall_row = (
        f"{'OVERALL':<24} | {overall['precision']:<9.4f} | {overall['recall']:<9.4f} | "
        f"{overall['f1']:<9.4f} | {overall['false_positive_rate']:<9.4f} | "
        f"{overall['true_positives']:<4} | {overall['false_positives']:<4} | "
        f"{overall['false_negatives']:<4}"
    )
    print(overall_row)
    print("=" * 90)


def _write_combined_markdown(
    full_results: dict[str, Any],
    base_results: dict[str, Any] | None,
) -> None:
    """Write markdown evaluation report containing full and baseline comparisons."""
    lines: list[str] = [
        "# VeilRAG PII Sanitization Evaluation Report",
        "",
        "> Measured evaluation of local fail-closed PII sanitization against labeled ground truth.",
        "> Generated from synthetic cases using Faker (`en_IN` and `en_US`).",
        "",
        "## Executive Summary",
        "",
    ]

    if base_results:
        f_ov = full_results["overall"]
        b_ov = base_results["overall"]
        lines.extend([
            "| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |",
            "|:---|:---:|:---:|:---:|",
            f"| **Precision** | {f_ov['precision']:.4f} | {b_ov['precision']:.4f} | "
            f"{f_ov['precision'] - b_ov['precision']:+.4f} |",
            f"| **Recall** | {f_ov['recall']:.4f} | {b_ov['recall']:.4f} | "
            f"{f_ov['recall'] - b_ov['recall']:+.4f} |",
            f"| **F1 Score** | {f_ov['f1']:.4f} | {b_ov['f1']:.4f} | "
            f"{f_ov['f1'] - b_ov['f1']:+.4f} |",
            f"| **False Positive Rate** | {f_ov['false_positive_rate']:.4f} | "
            f"{b_ov['false_positive_rate']:.4f} | "
            f"{f_ov['false_positive_rate'] - b_ov['false_positive_rate']:+.4f} |",
            "",
        ])

    lines.append(format_table_markdown(
        full_results, "VeilRAG Full Configuration (Presidio + Custom Recognizers)"
    ))
    lines.append("")

    if base_results:
        lines.append(format_table_markdown(
            base_results, "Baseline Configuration (Presidio Built-ins Only)"
        ))
        lines.append("")

    lines.extend([
        "## Evaluation Methodology",
        "",
        f"- **Dataset**: {full_results['num_cases']} synthetic test cases generated with Faker.",
        "- **Locales**: `en_IN` (Indian identifiers) and `en_US` (US/Global formats).",
        f"- **Metric Matching**: IoU span overlap threshold >= {SPAN_OVERLAP_THRESHOLD:.0%}.",
        "- **Negative Cases**: Non-PII lookalikes (order numbers failing Verhoeff checksum, "
        "PIN codes, device serials) and clean sentences with zero PII.",
        "- **Strict Zero-Hallucination Metrics**: All numbers come directly from execution.",
        "",
    ])

    DOCS_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")


def evaluate_pii(
    cases: list[Case] | None = None,
    *,
    baseline: bool = False,
) -> dict[str, Any]:
    """Evaluate PII detection on the labeled case set.

    Parameters
    ----------
    cases
        Optional pre-loaded cases; loads ``pii_cases.jsonl`` if omitted.
    baseline
        If True, run Presidio built-ins only (no custom recognizers).

    Returns
    -------
    dict[str, Any]
        Overall and per-entity-type metrics.
    """
    if cases is None:
        cases = []
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            cases.append(Case.from_dict(json.loads(line)))

    return evaluate(cases, baseline=baseline)


def main() -> int:
    """Run the PII evaluation for both full and baseline configurations."""
    parser = argparse.ArgumentParser(description="Evaluate VeilRAG PII sanitization")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Run Presidio defaults only (no custom recognizers) for comparison",
    )
    parser.add_argument("--json", type=Path, default=None, help="Override results JSON output path")
    parser.add_argument("--md", type=Path, default=None, help="Override markdown output path")
    args = parser.parse_args()

    global RESULTS_PATH, DOCS_RESULTS_PATH  # noqa: PLW0603
    if args.json:
        RESULTS_PATH = args.json
    if args.md:
        DOCS_RESULTS_PATH = args.md

    # Warm Presidio analyzer
    _get_presidio_analyzer()

    if args.baseline:
        base_results = evaluate_pii(baseline=True)
        print_table(base_results, "Baseline Configuration (Presidio Built-ins Only)")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(
            json.dumps({"baseline": base_results}, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _write_combined_markdown(base_results, None)
        print(f"\nResults written to:\n  -> {RESULTS_PATH}\n  -> {DOCS_RESULTS_PATH}")
        return 0

    full_results = evaluate_pii(baseline=False)
    base_results = evaluate_pii(baseline=True)

    print_table(full_results, "VeilRAG Full Configuration (Presidio + Custom Recognizers)")
    print_table(base_results, "Baseline Configuration (Presidio Built-ins Only)")

    # Print summary lift
    f_ov = full_results["overall"]
    b_ov = base_results["overall"]
    print("\n" + "=" * 60)
    print(" VEILRAG VS BASELINE COMPARISON SUMMARY")
    print("=" * 60)
    print(f"  Precision: {f_ov['precision']:.4f} (vs {b_ov['precision']:.4f} baseline)")
    print(f"  Recall:    {f_ov['recall']:.4f} (vs {b_ov['recall']:.4f} baseline)")
    print(f"  F1 Score:  {f_ov['f1']:.4f} (vs {b_ov['f1']:.4f} baseline)")
    print(f"  Recall Lift: +{(f_ov['recall'] - b_ov['recall']) * 100:.2f}%")
    print("=" * 60)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    combined_json = {
        "full": full_results,
        "baseline": base_results,
    }
    RESULTS_PATH.write_text(
        json.dumps(combined_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _write_combined_markdown(full_results, base_results)
    print(f"\nResults written to:\n  -> {RESULTS_PATH}\n  -> {DOCS_RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
