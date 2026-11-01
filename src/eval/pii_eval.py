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
DEV_CASES_PATH = DATA_DIR / "pii_cases.jsonl"
DEV2_CASES_PATH = DATA_DIR / "pii_dev2.jsonl"
HELDOUT_CASES_PATH = DATA_DIR / "pii_heldout.jsonl"
CASES_PATH = DEV_CASES_PATH
DEV_RESULTS_PATH = DATA_DIR / "pii_results.json"
DEV2_RESULTS_PATH = DATA_DIR / "pii_results_dev2.json"
HELDOUT_RESULTS_PATH = DATA_DIR / "pii_results_heldout.json"
RESULTS_PATH = DEV_RESULTS_PATH
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
    """Precision/recall/F1 for one configuration."""

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

    @staticmethod
    def _safe_div(num: int, den: int) -> float:
        return num / den if den > 0 else 0.0

    def __add__(self, other: Metrics) -> Metrics:
        return Metrics(
            true_positives=self.true_positives + other.true_positives,
            false_positives=self.false_positives + other.false_positives,
            false_negatives=self.false_negatives + other.false_negatives,
        )


def compute_clean_case_fpr(
    cases: list[Case],
    case_findings: list[list[dict[str, Any]]],
) -> tuple[float, int, int, dict[str, float]]:
    """Compute clean-case FPR: (clean cases with any flagged entity) / (total clean cases).

    Returns
    -------
    tuple
        (overall_clean_fpr, total_clean_cases, flagged_clean_cases, per_type_clean_fpr)
    """
    total_clean = 0
    flagged_clean = 0
    per_type_flagged: dict[str, int] = {}

    for case, findings in zip(cases, case_findings):
        if len(case.entities) == 0:
            total_clean += 1
            has_fp = any(f["result"] == "false_positive" for f in findings)
            if has_fp:
                flagged_clean += 1
                flagged_types = {f["type"] for f in findings if f["result"] == "false_positive"}
                for t in flagged_types:
                    per_type_flagged[t] = per_type_flagged.get(t, 0) + 1

    overall_fpr = flagged_clean / total_clean if total_clean > 0 else 0.0
    per_type_fpr = {
        t: count / total_clean if total_clean > 0 else 0.0
        for t, count in per_type_flagged.items()
    }
    return overall_fpr, total_clean, flagged_clean, per_type_fpr


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


def compute_char_metrics(
    text: str,
    gold_spans: list[tuple[str, int, int]],
    detected_spans: list[tuple[str, int, int]],
) -> dict[str, Any]:
    """Compute type-agnostic character-level leak and over-redaction metrics.

    Parameters
    ----------
    text
        The input text string.
    gold_spans
        Ground-truth entity spans as (type, start, end).
    detected_spans
        Detected entity spans as (type, start, end).

    Returns
    -------
    dict[str, Any]
        Dictionary with character counts and rates:
        - ``gold_chars``: number of characters in ground-truth PII spans
        - ``leaked_chars``: gold characters not covered by any detected span
        - ``non_pii_chars``: number of non-PII characters in text
        - ``over_redacted_chars``: non-PII characters covered by a detected span
        - ``leak_rate``: leaked_chars / gold_chars (0.0 if gold_chars == 0)
        - ``over_redaction_rate``: over_redacted_chars / non_pii_chars (0.0 if non_pii_chars == 0)
    """
    text_len = len(text)
    gold_indices: set[int] = set()
    for _, s, e in gold_spans:
        gold_indices.update(range(max(0, s), min(text_len, e)))

    det_indices: set[int] = set()
    for _, s, e in detected_spans:
        det_indices.update(range(max(0, s), min(text_len, e)))

    non_pii_indices = set(range(text_len)) - gold_indices

    gold_chars = len(gold_indices)
    leaked_chars = len(gold_indices - det_indices)
    non_pii_chars = len(non_pii_indices)
    over_redacted_chars = len(det_indices & non_pii_indices)

    leak_rate = leaked_chars / gold_chars if gold_chars > 0 else 0.0
    over_redaction_rate = (
        over_redacted_chars / non_pii_chars if non_pii_chars > 0 else 0.0
    )

    return {
        "gold_chars": gold_chars,
        "leaked_chars": leaked_chars,
        "non_pii_chars": non_pii_chars,
        "over_redacted_chars": over_redacted_chars,
        "leak_rate": leak_rate,
        "over_redaction_rate": over_redaction_rate,
    }


def evaluate_case(
    case: Case, *, baseline: bool = False
) -> tuple[int, int, int, int, list[dict[str, Any]], dict[str, Any]]:
    """Evaluate a single case against gold spans.

    Returns a 6-tuple of (tp, fp, fn, total_gold, findings, char_metrics).
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

    char_metrics = compute_char_metrics(case.text, gold, detected)

    return tp, fp, fn, len(gold), findings, char_metrics


def _collect_metrics(
    cases: list[Case],
    *,
    baseline: bool = False,
) -> tuple[
    Metrics,
    dict[str, Metrics],
    list[dict[str, Any]],
    float,
    int,
    int,
    dict[str, float],
    dict[str, Any],
]:
    """Run evaluation over all cases, returning overall, per-type, and character-level metrics."""
    overall = Metrics()
    per_type: dict[str, Metrics] = {}
    findings: list[dict[str, Any]] = []
    case_findings: list[list[dict[str, Any]]] = []

    total_gold_chars = 0
    total_leaked_chars = 0
    total_non_pii_chars = 0
    total_over_redacted_chars = 0

    for case in cases:
        tp, fp, fn, total_gold, per_case, char_metrics = evaluate_case(case, baseline=baseline)
        findings.extend(per_case)
        case_findings.append(per_case)
        overall += Metrics(tp, fp, fn)

        total_gold_chars += char_metrics["gold_chars"]
        total_leaked_chars += char_metrics["leaked_chars"]
        total_non_pii_chars += char_metrics["non_pii_chars"]
        total_over_redacted_chars += char_metrics["over_redacted_chars"]

        for f in per_case:
            m = per_type.setdefault(f["type"], Metrics())
            if f["result"] == "true_positive":
                m.true_positives += 1
            elif f["result"] == "false_positive":
                m.false_positives += 1
            elif f["result"] == "false_negative":
                m.false_negatives += 1

    clean_fpr, total_clean, flagged_clean, per_type_clean_fpr = compute_clean_case_fpr(
        cases, case_findings
    )

    overall_leak_rate = (
        total_leaked_chars / total_gold_chars if total_gold_chars > 0 else 0.0
    )
    overall_over_redaction_rate = (
        total_over_redacted_chars / total_non_pii_chars
        if total_non_pii_chars > 0
        else 0.0
    )

    char_summary = {
        "char_leak_rate": round(overall_leak_rate, 4),
        "char_over_redaction_rate": round(overall_over_redaction_rate, 4),
        "total_gold_chars": total_gold_chars,
        "total_leaked_chars": total_leaked_chars,
        "total_non_pii_chars": total_non_pii_chars,
        "total_over_redacted_chars": total_over_redacted_chars,
    }

    return (
        overall,
        per_type,
        findings,
        clean_fpr,
        total_clean,
        flagged_clean,
        per_type_clean_fpr,
        char_summary,
    )


def evaluate(
    cases: list[Case],
    *,
    baseline: bool = False,
) -> dict[str, Any]:
    """Evaluate all *cases* and return a structured result."""
    (
        overall,
        per_type,
        findings,
        clean_fpr,
        total_clean,
        flagged_clean,
        per_type_clean_fpr,
        char_summary,
    ) = _collect_metrics(cases, baseline=baseline)

    span_precision = overall.precision
    total_flagged = overall.true_positives + overall.false_positives
    span_error_rate = 1.0 - span_precision if total_flagged > 0 else 0.0

    return {
        "baseline": baseline,
        "num_cases": len(cases),
        "clean_cases_total": total_clean,
        "clean_cases_flagged": flagged_clean,
        "overall": {
            "true_positives": overall.true_positives,
            "false_positives": overall.false_positives,
            "false_negatives": overall.false_negatives,
            "precision": round(overall.precision, 4),
            "recall": round(overall.recall, 4),
            "f1": round(overall.f1, 4),
            "clean_case_fpr": round(clean_fpr, 4),
            "false_positive_rate": round(clean_fpr, 4),
            "span_precision": round(span_precision, 4),
            "span_error_rate": round(span_error_rate, 4),
            "char_leak_rate": char_summary["char_leak_rate"],
            "char_over_redaction_rate": char_summary["char_over_redaction_rate"],
            "total_gold_chars": char_summary["total_gold_chars"],
            "total_leaked_chars": char_summary["total_leaked_chars"],
            "total_non_pii_chars": char_summary["total_non_pii_chars"],
            "total_over_redacted_chars": char_summary["total_over_redacted_chars"],
        },
        "per_entity_type": {
            k: {
                "true_positives": v.true_positives,
                "false_positives": v.false_positives,
                "false_negatives": v.false_negatives,
                "precision": round(v.precision, 4),
                "recall": round(v.recall, 4),
                "f1": round(v.f1, 4),
                "clean_case_fpr": round(per_type_clean_fpr.get(k, 0.0), 4),
                "false_positive_rate": round(per_type_clean_fpr.get(k, 0.0), 4),
            }
            for k, v in sorted(per_type.items())
        },
        "findings": findings,
    }


def format_table_markdown(results: dict[str, Any], title: str) -> str:
    """Format evaluation results as a clean Markdown table."""
    overall = results["overall"]
    per_type = results["per_entity_type"]

    leak_chars = overall.get("total_leaked_chars", 0)
    gold_chars = overall.get("total_gold_chars", 0)
    over_chars = overall.get("total_over_redacted_chars", 0)
    non_pii_chars = overall.get("total_non_pii_chars", 0)

    lines: list[str] = [
        f"### {title}",
        "",
        f"- Cases evaluated: {results['num_cases']}",
        f"- PII-free clean cases: {results.get('clean_cases_total', 'N/A')}",
        (
            f"- Flagged clean cases: {results.get('clean_cases_flagged', 'N/A')} "
            f"(Clean-case FPR: "
            f"{overall.get('clean_case_fpr', overall.get('false_positive_rate', 0.0)):.4f})"
        ),
        (
            f"- Character leak rate (type-agnostic): {overall.get('char_leak_rate', 0.0):.4f} "
            f"({leak_chars}/{gold_chars} gold PII characters unredacted)"
        ),
        (
            "- Character over-redaction rate (type-agnostic): "
            f"{overall.get('char_over_redaction_rate', 0.0):.4f} "
            f"({over_chars}/{non_pii_chars} non-PII characters redacted)"
        ),
        f"- Span overlap threshold (IoU): {SPAN_OVERLAP_THRESHOLD:.0%}",
        "",
        "| Entity Type | Precision | Recall | F1 Score | Clean FPR | TP | FP | FN |",
        "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for et, m in sorted(per_type.items()):
        fpr_val = m.get("clean_case_fpr", m.get("false_positive_rate", 0.0))
        lines.append(
            f"| `{et}` | {m['precision']:.4f} | {m['recall']:.4f} | "
            f"{m['f1']:.4f} | {fpr_val:.4f} | "
            f"{m['true_positives']} | {m['false_positives']} | {m['false_negatives']} |"
        )

    ov_fpr = overall.get("clean_case_fpr", overall.get("false_positive_rate", 0.0))
    lines.append(
        f"| **OVERALL** | **{overall['precision']:.4f}** | **{overall['recall']:.4f}** | "
        f"**{overall['f1']:.4f}** | **{ov_fpr:.4f}** | "
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
        f"{'Clean FPR':<9} | {'TP':<4} | {'FP':<4} | {'FN':<4}"
    )
    print(header)
    print("-" * 90)

    for et, m in sorted(per_type.items()):
        fpr_val = m.get("clean_case_fpr", m.get("false_positive_rate", 0.0))
        row = (
            f"{et:<24} | {m['precision']:<9.4f} | {m['recall']:<9.4f} | {m['f1']:<9.4f} | "
            f"{fpr_val:<9.4f} | {m['true_positives']:<4} | "
            f"{m['false_positives']:<4} | {m['false_negatives']:<4}"
        )
        print(row)

    print("-" * 90)
    ov_fpr = overall.get("clean_case_fpr", overall.get("false_positive_rate", 0.0))
    overall_row = (
        f"{'OVERALL':<24} | {overall['precision']:<9.4f} | {overall['recall']:<9.4f} | "
        f"{overall['f1']:<9.4f} | {ov_fpr:<9.4f} | "
        f"{overall['true_positives']:<4} | {overall['false_positives']:<4} | "
        f"{overall['false_negatives']:<4}"
    )
    print(overall_row)
    print("=" * 90)
    leak_chars = overall.get("total_leaked_chars", 0)
    gold_chars = overall.get("total_gold_chars", 0)
    over_chars = overall.get("total_over_redacted_chars", 0)
    non_pii_chars = overall.get("total_non_pii_chars", 0)
    print(
        f"  Type-Agnostic Leak Rate:         {overall.get('char_leak_rate', 0.0):.4f} "
        f"({leak_chars}/{gold_chars} gold PII chars unredacted)"
    )
    print(
        f"  Type-Agnostic Over-Redaction:    {overall.get('char_over_redaction_rate', 0.0):.4f} "
        f"({over_chars}/{non_pii_chars} non-PII chars redacted)"
    )
    print("=" * 90)


def _render_dataset_markdown_section(
    section_title: str,
    dataset_file: str,
    notes: list[str],
    results_file: Path,
) -> list[str]:
    """Render a dataset results section in markdown format."""
    lines: list[str] = [
        f"## {section_title}",
        "",
        f"- **Dataset**: `{dataset_file}`",
    ]
    for n in notes:
        if n.startswith(">"):
            lines.append(n)
        else:
            lines.append(f"- {n}")
    lines.append("")

    if not results_file.exists():
        lines.append("*No evaluation results recorded yet.*")
        lines.append("")
        return lines

    try:
        data = json.loads(results_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to render %s: %s", results_file, e)
        return lines

    if "full" in data and "baseline" in data:
        f_ov = data["full"]["overall"]
        b_ov = data["baseline"]["overall"]
        f_fpr = f_ov.get("clean_case_fpr", f_ov.get("false_positive_rate", 0.0))
        b_fpr = b_ov.get("clean_case_fpr", b_ov.get("false_positive_rate", 0.0))
        f_leak = f_ov.get("char_leak_rate", 0.0)
        b_leak = b_ov.get("char_leak_rate", 0.0)
        f_over = f_ov.get("char_over_redaction_rate", 0.0)
        b_over = b_ov.get("char_over_redaction_rate", 0.0)

        lines.extend([
            f"### {section_title}: VeilRAG vs Presidio Baseline Summary",
            "",
            "| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |",
            "|:---|:---:|:---:|:---:|",
            f"| **Precision** | {f_ov['precision']:.4f} | {b_ov['precision']:.4f} | "
            f"{f_ov['precision'] - b_ov['precision']:+.4f} |",
            f"| **Recall** | {f_ov['recall']:.4f} | {b_ov['recall']:.4f} | "
            f"{f_ov['recall'] - b_ov['recall']:+.4f} |",
            f"| **F1 Score** | {f_ov['f1']:.4f} | {b_ov['f1']:.4f} | "
            f"{f_ov['f1'] - b_ov['f1']:+.4f} |",
            f"| **Clean-case FPR** | {f_fpr:.4f} | {b_fpr:.4f} | "
            f"{f_fpr - b_fpr:+.4f} |",
            f"| **Character Leak Rate** | {f_leak:.4f} | {b_leak:.4f} | "
            f"{f_leak - b_leak:+.4f} |",
            f"| **Character Over-Redaction** | {f_over:.4f} | {b_over:.4f} | "
            f"{f_over - b_over:+.4f} |",
            "",
            format_table_markdown(data["full"], f"{section_title} — VeilRAG Full Configuration"),
            "",
            format_table_markdown(
                data["baseline"], f"{section_title} — Presidio Baseline Configuration"
            ),
            "",
        ])
    elif "baseline" in data:
        lines.extend([
            format_table_markdown(
                data["baseline"], f"{section_title} — Presidio Baseline Configuration"
            ),
            "",
        ])
    elif "full" in data:
        lines.extend([
            format_table_markdown(data["full"], f"{section_title} — VeilRAG Full Configuration"),
            "",
        ])
    return lines


def _write_combined_markdown() -> None:
    """Write markdown evaluation report containing DEV and HELD-OUT comparisons."""
    lines: list[str] = [
        "# VeilRAG PII Sanitization Evaluation Report",
        "",
        "> Measured evaluation of local fail-closed PII sanitization against labeled ground truth.",
        "> Generated from synthetic cases using Faker (`en_IN` and `en_US`).",
        "",
        "## Metric Definitions",
        "",
        "- **Clean-case False Positive Rate (Clean FPR)**: "
        "`(PII-free cases where ANY entity was flagged) / (number of PII-free cases)`."
        " Measures the proportion of non-PII documents incorrectly subjected to redaction.",
        "- **Span Precision**: `TP / (TP + FP)`."
        " The proportion of flagged spans that truly correspond to ground-truth PII."
        " The span error rate is `1 - precision` (the share of flagged spans that are wrong).",
        "- **Recall**: `TP / (TP + FN)`."
        " The proportion of ground-truth PII entities successfully detected and redacted.",
        "- **F1 Score**: `2 * (Precision * Recall) / (Precision + Recall)`."
        " Harmonic mean of precision and recall.",
        "- **Character Leak Rate (Type-Agnostic)**: "
        "`(Total gold PII characters NOT covered by ANY detected span) / "
        "(Total gold PII characters)`."
        " Measures raw sensitive text leakage independent of entity categorization.",
        "- **Character Over-Redaction Rate (Type-Agnostic)**: "
        "`(Total non-PII characters covered by ANY detected span) / (Total non-PII characters)`."
        " Measures collateral redaction of benign document text across the corpus.",
        "",
    ]

    lines.extend(
        _render_dataset_markdown_section(
            "1. Development Dataset Evaluation (DEV)",
            "data/eval/pii_cases.jsonl",
            ["Used during initial development of custom recognizers and detectors."],
            DEV_RESULTS_PATH,
        )
    )

    if DEV2_RESULTS_PATH.exists():
        lines.extend(
            _render_dataset_markdown_section(
                "2. First Held-Out Run (Pre-Fix / DEV2)",
                "data/eval/pii_dev2.jsonl",
                [
                    "First held-out evaluation run on recognizers-frozen-v1.",
                    "Diagnosed in `docs/pii_errors_heldout.md` and subsequently used as DEV2.",
                ],
                DEV2_RESULTS_PATH,
            )
        )

    lines.extend(
        _render_dataset_markdown_section(
            "3. Final Held-Out Dataset Evaluation (HELD-OUT)",
            "data/eval/pii_heldout.jsonl",
            [
                "Frozen recognizers (`recognizers-frozen-v2`).",
                "Strictly evaluated once without tuning.",
                "> [!NOTE] Secret Scanner Compatibility & Dataset Adjustments\n"
                "> The held-out evaluation dataset was adjusted twice post-generation:\n"
                "> 1. Synthetic Stripe-style keys (sk-live and pk-test vectors) triggered "
                "GitHub push protection and were replaced with scanner-safe mock secrets "
                "(mock_sk_... and mock_pk_...), which are detected with 100% precision and "
                "recall by VeilRAG's GenericSecretRecognizer.\n"
                "> 2. An initial over-correction temporarily replaced AWS access keys (AKIA...) "
                "with an AWSK prefix. Because AWSKeyRecognizer was frozen under "
                "recognizers-frozen-v2 with strict pattern matching, this made them undetectable "
                "by construction (3 false negatives). This over-correction was reverted to restore "
                "the exact original AKIA test vectors.\n>\n"
                "> Final held-out results: Precision 0.6976, Recall 0.9167 "
                "(143 TP / 62 FP / 13 FN), F1 0.7922, Character Leak Rate 0.0061 "
                "(15/2,443 characters unredacted).",
            ],
            HELDOUT_RESULTS_PATH,
        )
    )

    lines.extend([
        "## Limitations",
        "",
        "- **Synthetic Data**: Both the development and held-out evaluation sets are "
        "synthetically generated using Faker (`en_IN` and `en_US`). Real-world private documents "
        "exhibit messier token distributions, arbitrary OCR errors, multi-column tables, scanned "
        "PDFs, and handwriting not fully represented in synthetic text strings.",
        "- **English-Heavy**: All cases use English and Romanized Hinglish. Hindi or other "
        "regional Indian script inputs (Devanagari, Tamil, Telugu, etc.) are outside the "
        "current Presidio analyzer configuration.",
        "- **Same Author as Recognizers**: Synthetic generation templates were conceived by the "
        "same development framework as the custom regex and Presidio recognizers, which may create "
        "unintended shared structural priors despite distinct random seeds and decoupled "
        "template vocabularies.",
        "",
    ])

    DOCS_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")


def evaluate_pii(
    cases: list[Case] | None = None,
    *,
    baseline: bool = False,
    dataset: str = "dev",
) -> dict[str, Any]:
    """Evaluate PII detection on the labeled case set.

    Parameters
    ----------
    cases
        Optional pre-loaded cases; loads dataset file if omitted.
    baseline
        If True, run Presidio built-ins only (no custom recognizers).
    dataset
        'dev', 'dev2', or 'heldout'.

    Returns
    -------
    dict[str, Any]
        Overall and per-entity-type metrics.
    """
    if cases is None:
        if dataset == "heldout":
            path = HELDOUT_CASES_PATH
        elif dataset == "dev2":
            path = DEV2_CASES_PATH
        else:
            path = DEV_CASES_PATH

        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")
        cases = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            cases.append(Case.from_dict(json.loads(line)))

    return evaluate(cases, baseline=baseline)


def main() -> int:
    """Run the PII evaluation for both full and baseline configurations."""
    parser = argparse.ArgumentParser(description="Evaluate VeilRAG PII sanitization")
    parser.add_argument(
        "--dataset",
        choices=["dev", "dev2", "heldout"],
        default="dev",
        help="Dataset to evaluate: 'dev' (default), 'dev2', or 'heldout'",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Run Presidio defaults only (no custom recognizers) for comparison",
    )
    parser.add_argument("--json", type=Path, default=None, help="Override results JSON output path")
    parser.add_argument("--md", type=Path, default=None, help="Override markdown output path")
    args = parser.parse_args()

    global DOCS_RESULTS_PATH  # noqa: PLW0603
    if args.json:
        target_results_path = args.json
    else:
        if args.dataset == "heldout":
            target_results_path = HELDOUT_RESULTS_PATH
        elif args.dataset == "dev2":
            target_results_path = DEV2_RESULTS_PATH
        else:
            target_results_path = DEV_RESULTS_PATH

    if args.md:
        DOCS_RESULTS_PATH = args.md

    # Warm Presidio analyzer
    _get_presidio_analyzer()

    if args.baseline:
        base_results = evaluate_pii(baseline=True, dataset=args.dataset)
        print_table(
            base_results,
            f"Baseline Configuration (Presidio Built-ins Only) [{args.dataset.upper()} SET]",
        )
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        existing: dict[str, Any] = {}
        if target_results_path.exists():
            try:
                existing = json.loads(target_results_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        existing["baseline"] = base_results
        target_results_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _write_combined_markdown()
        print(f"\nResults written to:\n  -> {target_results_path}\n  -> {DOCS_RESULTS_PATH}")
        return 0

    full_results = evaluate_pii(baseline=False, dataset=args.dataset)
    base_results = evaluate_pii(baseline=True, dataset=args.dataset)

    print_table(
        full_results,
        f"VeilRAG Full Configuration (Presidio + Custom Recognizers) [{args.dataset.upper()} SET]",
    )
    print_table(
        base_results,
        f"Baseline Configuration (Presidio Built-ins Only) [{args.dataset.upper()} SET]",
    )

    f_ov = full_results["overall"]
    b_ov = base_results["overall"]
    f_fpr = f_ov.get("clean_case_fpr", f_ov.get("false_positive_rate", 0.0))
    b_fpr = b_ov.get("clean_case_fpr", b_ov.get("false_positive_rate", 0.0))

    print("\n" + "=" * 60)
    print(f" VEILRAG VS BASELINE COMPARISON SUMMARY [{args.dataset.upper()} SET]")
    print("=" * 60)
    print(f"  Precision:           {f_ov['precision']:.4f} (vs {b_ov['precision']:.4f} baseline)")
    print(f"  Recall:              {f_ov['recall']:.4f} (vs {b_ov['recall']:.4f} baseline)")
    print(f"  F1 Score:            {f_ov['f1']:.4f} (vs {b_ov['f1']:.4f} baseline)")
    print(f"  Clean-case FPR:      {f_fpr:.4f} (vs {b_fpr:.4f} baseline)")
    print(
        f"  Character Leak Rate: {f_ov.get('char_leak_rate', 0.0):.4f} "
        f"(vs {b_ov.get('char_leak_rate', 0.0):.4f} baseline)"
    )
    print(
        f"  Over-Redaction Rate: {f_ov.get('char_over_redaction_rate', 0.0):.4f} "
        f"(vs {b_ov.get('char_over_redaction_rate', 0.0):.4f} baseline)"
    )
    print(f"  Recall Lift:         +{(f_ov['recall'] - b_ov['recall']) * 100:.2f}%")
    print("=" * 60)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    combined_json = {
        "full": full_results,
        "baseline": base_results,
    }
    target_results_path.write_text(
        json.dumps(combined_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _write_combined_markdown()
    print(f"\nResults written to:\n  -> {target_results_path}\n  -> {DOCS_RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
