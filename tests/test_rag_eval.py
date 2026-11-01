"""Tests for RAG evaluation harness, ablations, metrics, caching, and datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.eval.rag_eval import (
    DEV_QA_FILE,
    TEST_QA_FILE,
    check_answer_correctness,
    check_citation_correctness,
    check_pii_leak,
    check_refusal,
    check_retrieval_hit,
    format_ci,
    load_qa_records,
    run_single_ablation,
    wilson_interval,
)
from src.llm import CachedLLMAdapter, FakeLLMAdapter, LLMResponse
from src.rag.agent import run_query
from src.rag.retriever import RetrievedDocument
from src.sanitizer import SanitizedText, sanitize

# ─────────────────────────────────────────────────────────────────────────────
# 1. Wilson 95% Confidence Interval Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_wilson_interval_known_cases() -> None:
    """Validate Wilson score confidence intervals on known analytical benchmarks."""
    # Zero successes: k=0, n=40
    p, low, high = wilson_interval(0, 40)
    assert p == 0.0
    assert low == 0.0
    assert 0.08 < high < 0.09  # ~8.76% rule-of-three upper bound

    # Perfect successes: k=40, n=40
    p, low, high = wilson_interval(40, 40)
    assert p == 1.0
    assert 0.91 < low < 0.92
    assert high == 1.0

    # 50% split: k=50, n=100
    p, low, high = wilson_interval(50, 100)
    assert p == 0.5
    assert 0.40 < low < 0.41  # ~0.4038
    assert 0.59 < high < 0.60  # ~0.5962

    # Zero sample size guard
    assert wilson_interval(0, 0) == (0.0, 0.0, 0.0)

    # Format helper
    ci_str = format_ci(31, 40)
    assert "31/40" in ci_str
    assert "95% CI" in ci_str


# ─────────────────────────────────────────────────────────────────────────────
# 2. Hand-Computed Metric Function Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_metric_retrieval_hit_rate() -> None:
    """Test retrieval hit rate detection against hand-crafted document sets."""
    sample_docs = [
        RetrievedDocument(
            text="chunk 0",
            metadata={"chunk_id": "hr_policy_01.txt#chunk_0", "source": "hr_policy_01.txt"},
            score=0.9,
        ),
        RetrievedDocument(
            text="chunk 1",
            metadata={"chunk_id": "hr_policy_01.txt#chunk_1", "source": "hr_policy_01.txt"},
            score=0.85,
        ),
        RetrievedDocument(
            text="loan 0",
            metadata={
                "chunk_id": "loan_agreement_02.txt#chunk_0",
                "source": "loan_agreement_02.txt",
            },
            score=0.75,
        ),
    ]

    # Hit by chunk id prefix
    assert check_retrieval_hit("hr_policy_01.txt", sample_docs) is True
    assert check_retrieval_hit("loan_agreement_02.txt", sample_docs) is True

    # Miss when document not present
    assert check_retrieval_hit("hospital_discharge_03.txt", sample_docs) is False

    # None gold doc returns False
    assert check_retrieval_hit(None, sample_docs) is False


def test_metric_answer_correctness() -> None:
    """Test programmatic exact/normalized answer correctness matching."""
    # Exact substring
    assert check_answer_correctness("30 calendar days", "Notice is 30 calendar days.") is True

    # Case-insensitive
    assert check_answer_correctness("30 Calendar Days", "Notice is 30 calendar days.") is True

    # Currency normalization
    assert check_answer_correctness("INR 25,00,000", "The loan amount is 25,00,000.") is True
    assert check_answer_correctness("INR 25,00,000", "Sanctioned INR 25,00,000 credit.") is True

    # Percentage normalization
    assert check_answer_correctness(
        "8.75% per annum floating", "The interest rate is 8.75% applied daily."
    ) is True

    # Mismatch returns False
    assert check_answer_correctness("60 calendar days", "Notice is 30 calendar days.") is False
    assert check_answer_correctness(None, "Any answer.") is False


def test_metric_refusal_detection() -> None:
    """Test refusal check on unanswerable questions."""
    assert check_refusal("I don't know.") is True
    assert check_refusal("I do not know the answer.") is True
    assert check_refusal("This cannot be determined from the context.") is True
    assert check_refusal("The context does not contain enough information.") is True
    assert check_refusal("According to [doc#chunk_0], the interest rate is 9.5%.") is False


def test_metric_citation_correctness() -> None:
    """Test citation validation against target gold document."""
    ans_correct = "According to [hr_policy_01.txt#chunk_0], notice is 30 days."
    ans_wrong = "According to [loan_agreement_02.txt#chunk_0], notice is 30 days."
    ans_no_cite = "Notice is 30 days."

    assert check_citation_correctness("hr_policy_01.txt", ans_correct) is True
    assert check_citation_correctness("hr_policy_01.txt", ans_wrong) is False
    assert check_citation_correctness("hr_policy_01.txt", ans_no_cite) is False
    assert check_citation_correctness(None, ans_correct) is False


def test_metric_pii_leak_detection() -> None:
    """Test comprehensive PII leak detection (planted substrings and sanitizer)."""
    planted = ["6484 3732 8119", "abcks1234m", "ananya.sharma@starlighttech.example"]

    # Clean answer with placeholder
    clean_ans = "The employee's Aadhaar is [AADHAAR_1] and PAN is [PAN_1]."
    is_leak, leaks = check_pii_leak(clean_ans, planted)
    assert is_leak is False
    assert len(leaks) == 0

    # Leak of planted value
    leaked_ans_planted = "The employee's Aadhaar is 6484 3732 8119."
    is_leak, leaks = check_pii_leak(leaked_ans_planted, planted)
    assert is_leak is True
    assert any("6484 3732 8119" in leak for leak in leaks)

    # Leak detected by sanitizer
    leaked_ans_unplanted = "The borrower's email is confidential.contact@company.com"
    is_leak, leaks = check_pii_leak(leaked_ans_unplanted, planted)
    assert is_leak is True
    assert any("EMAIL_ADDRESS" in leak for leak in leaks)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Response Cache Safety Rail Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_response_cache_works(tmp_path: Path) -> None:
    """CachedLLMAdapter caches responses on disk and enforces SanitizedText boundary."""
    inner = FakeLLMAdapter(responses=["First call response", "Second call response"])
    cached = CachedLLMAdapter(inner, cache_dir=tmp_path)

    p1 = sanitize("What is the interest rate?").safe
    p2 = sanitize("What is the notice period?").safe

    # Call 1: Miss
    r1 = cached.complete(p1)
    assert r1.text == "First call response"
    assert cached.misses == 1
    assert cached.hits == 0

    # Call 1 repeat: Hit from disk cache
    r1_repeat = cached.complete(p1)
    assert r1_repeat.text == "First call response"
    assert cached.misses == 1
    assert cached.hits == 1

    # Call 2: Miss on new prompt
    r2 = cached.complete(p2)
    assert r2.text == "Second call response"
    assert cached.misses == 2
    assert cached.hits == 1

    # Type boundary enforced: plain str raises TypeError
    with pytest.raises(TypeError, match="Expected SanitizedText"):
        cached.complete("Unsanitized plain string")  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Cost Cap Safety Rail Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_cost_cap_aborts() -> None:
    """Evaluation strictly aborts when cumulative cost exceeds MAX_EVAL_COST_USD."""

    class CostlyAdapter:
        model = "costly-model"
        provider = "costly"

        def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
            return LLMResponse(
                text="expensive response",
                model=self.model,
                provider=self.provider,
                cost=0.05,  # $0.05 per call
            )

        async def acomplete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
            return self.complete(prompt, **kwargs)

        def astream(self, prompt: SanitizedText, **kwargs: object) -> Any:
            raise NotImplementedError

    sample_questions = [
        {
            "id": f"q_{i}",
            "question": f"Question {i}?",
            "category": "key_fact",
            "gold_doc": "hr_policy_01.txt",
            "gold_value": "30 days",
            "planted_values": [],
        }
        for i in range(5)
    ]

    adapter = CostlyAdapter()  # type: ignore[assignment]

    # Budget cap set to $0.08: q1 costs $0.05, q2 costs $0.05 ($0.10 > $0.08) -> abort
    with pytest.raises(RuntimeError, match="MAX_EVAL_COST_USD exceeded"):
        run_single_ablation(
            ablation_key="A",
            questions=sample_questions,
            adapter=adapter,  # type: ignore[arg-type]
            judge_adapter=adapter,  # type: ignore[arg-type]
            max_cost_usd=0.08,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Dataset Invariant & Structure Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_qa_test_dataset_structure() -> None:
    """Validate structure of data/eval/qa_test.jsonl: 26/8/6 questions with unique gold docs."""
    questions = load_qa_records(TEST_QA_FILE)

    # Total questions = 40
    assert len(questions) == 40

    key_fact = [q for q in questions if q["category"] == "key_fact"]
    unanswerable = [q for q in questions if q["category"] == "unanswerable"]
    pii_extraction = [q for q in questions if q["category"] == "pii_extraction"]

    # Exactly 26 answerable, 8 unanswerable, 6 PII
    assert len(key_fact) == 26
    assert len(unanswerable) == 8
    assert len(pii_extraction) == 6

    # Unique gold docs for answerable key-fact questions
    gold_docs_ans = [q["gold_doc"] for q in key_fact]
    assert len(gold_docs_ans) == 26
    assert len(set(gold_docs_ans)) == 26
    assert all(d.endswith(".txt") for d in gold_docs_ans)

    # Unique gold docs for PII extraction questions
    gold_docs_pii = [q["gold_doc"] for q in pii_extraction]
    assert len(gold_docs_pii) == 6
    assert len(set(gold_docs_pii)) == 6
    assert all(d.endswith(".txt") for d in gold_docs_pii)

    # Zero overlap between answerable and PII gold docs
    assert len(set(gold_docs_ans).intersection(set(gold_docs_pii))) == 0

    # Unanswerable invariants: gold_doc is None, gold_value is None
    for q in unanswerable:
        assert q["gold_doc"] is None
        assert q["gold_value"] is None

    # PII invariants: gold_value is None, planted_values is non-empty
    for q in pii_extraction:
        assert q["gold_value"] is None
        assert len(q["planted_values"]) > 0


def test_qa_dev_dataset_structure() -> None:
    """Validate structure of data/eval/qa_dev.jsonl: exactly 10 questions."""
    questions = load_qa_records(DEV_QA_FILE)
    assert len(questions) == 10

    key_fact = [q for q in questions if q["category"] == "key_fact"]
    unanswerable = [q for q in questions if q["category"] == "unanswerable"]
    pii_extraction = [q for q in questions if q["category"] == "pii_extraction"]

    assert len(key_fact) == 6
    assert len(pii_extraction) == 2
    assert len(unanswerable) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 6. Ablation Stage Wiring Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_ablation_stage_configurations() -> None:
    """Test that all 4 ablation graphs compile and execute with expected stage bypasses."""
    fake_adapter = FakeLLMAdapter(
        responses=["yes", "yes", "Generated answer [hr_policy_01.txt#chunk_0]", "yes"]
    )

    # Ablation A (Naive RAG: grading, rewrite, verification, output_guard all disabled)
    state_a = run_query(
        "What is the notice period?",
        adapter=fake_adapter,
        enable_grading=False,
        enable_rewrite=False,
        enable_verification=False,
        enable_output_guard=False,
    )
    assert state_a["step_count"] <= 15
    # Verification and output guard trace entries indicate skipped
    skipped_nodes = [t["node"] for t in state_a["audit_trace"] if t.get("skipped")]
    assert "grade_documents" in skipped_nodes
    assert "verify_answer" in skipped_nodes
    assert "output_guard" in skipped_nodes

    # Ablation D (Full System: all enabled)
    fake_adapter_d = FakeLLMAdapter(
        responses=[
            "yes",  # grade 1
            "yes",  # grade 2
            "yes",  # grade 3
            "yes",  # grade 4
            "Generated answer [hr_policy_01.txt#chunk_0]",
            "yes",  # verification
        ]
    )
    state_d = run_query(
        "What is the notice period?",
        adapter=fake_adapter_d,
        enable_grading=True,
        enable_rewrite=True,
        enable_verification=True,
        enable_output_guard=True,
    )
    skipped_d = [t["node"] for t in state_d["audit_trace"] if t.get("skipped")]
    assert len(skipped_d) == 0
    assert len(state_d["relevant_docs"]) >= 2
