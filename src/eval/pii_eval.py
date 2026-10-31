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
        # FPR = FP / (FP + TN); TN is approximated as non-gold spans.
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
        detected: list[tuple[str, int, int]] = [
            (r.entity_type, r.start, r.end) for r in results
        ]
    else:
        result = sanitize(case.text)
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
            for k, v in per_type.items()
        },
        "findings": findings,
    }


def _metrics_to_row(m: dict[str, Any]) -> str:
    return (
        f"{m['precision']:.4f}|"
        f"{m['recall']:.4f}|"
        f"{m['f1']:.4f}|"
        f"{m['false_positive_rate']:.4f}|"
        f"{m['true_positives']}|"
        f"{m['false_positives']}|"
        f"{m['false_negatives']}"
    )


def _write_markdown(results: dict[str, Any], baseline: bool = False) -> None:
    overall = results["overall"]
    per_type = results["per_entity_type"]

    cfg = "baseline" if baseline else "full"
    cfg_detail = "Presidio defaults only" if baseline else "Presidio + custom recognizers"
    lines: list[str] = []
    lines.append(f"# VeilRAG PII Evaluation Results ({cfg} configuration)")
    lines.append("")
    lines.append(f"- Cases evaluated: {results['num_cases']}")
    lines.append(f"- Span overlap threshold: {SPAN_OVERLAP_THRESHOLD:.0%}")
    lines.append(f"- Configuration: {cfg_detail}")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append("| Metric | Value | TP | FP | FN |")
    lines.append("| --- | --- | --- | --- | --- |")
    tp = overall["true_positives"]
    fp = overall["false_positives"]
    fn = overall["false_negatives"]
    lines.append(f"| precision | {overall['precision']:.4f} | {tp} | {fp} | {fn} |")
    lines.append(f"| recall | {overall['recall']:.4f} | {tp} | {fp} | {fn} |")
    lines.append(f"| f1 | {overall['f1']:.4f} | {tp} | {fp} | {fn} |")
    lines.append(
        f"| false_positive_rate | {overall['false_positive_rate']:.4f}"
        f" | {tp} | {fp} | {fn} |"
    )
    lines.append("")
    lines.append("## Per entity type")
    lines.append("")
    lines.append(
        "| Entity type | precision | recall | f1 | false_positive_rate | TP | FP | FN |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for et, m in sorted(per_type.items()):
        lines.append(
            f"| {et} | {_metrics_to_row(m)} |"
        )
    lines.append("")
    lines.append("## Sample findings")
    lines.append("")
    shown = results.get("findings", [])[:10]
    if not shown:
        lines.append("No findings.")
    else:
        for f in shown:
            lines.append(f"- `{f['result']}` {f['type']} at {f['start']}-{f['end']}")
    lines.append("")
    (DOCS_RESULTS_PATH.parent).mkdir(parents=True, exist_ok=True)
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
        Overall and per-entity-type metrics (precision, recall, F1,
        false_positive_rate), plus per-case findings.
    """

    if cases is None:
        cases = []
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            cases.append(Case.from_dict(json.loads(line)))

    results = evaluate(cases, baseline=baseline)
    (DATA_DIR).mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_markdown(results, baseline=baseline)
    return results


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

    # Warm the Presidio analyzer singleton before timing.
    _get_presidio_analyzer()

    logger.info("Full configuration:")
    full = evaluate_pii(baseline=False)
    ov = full["overall"]
    print(
        f"Full: precision={ov['precision']:.4f} recall={ov['recall']:.4f}"
        f" f1={ov['f1']:.4f} fpr={ov['false_positive_rate']:.4f}"
    )
    print(f"  -> {RESULTS_PATH}")
    print(f"  -> {DOCS_RESULTS_PATH}")

    if not args.baseline:
        logger.info("Baseline (Presidio defaults only):")
        base = evaluate_pii(baseline=True)
        bov = base["overall"]
        print(
            f"Baseline: precision={bov['precision']:.4f} recall={bov['recall']:.4f}"
            f" f1={bov['f1']:.4f} fpr={bov['false_positive_rate']:.4f}"
        )
        print(f"  -> {RESULTS_PATH}")
        print(f"  -> {DOCS_RESULTS_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
