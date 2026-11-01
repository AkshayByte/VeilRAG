"""Tests for src/rag/agent.py — Corrective-RAG LangGraph agent."""

from __future__ import annotations

from typing import Any

import pytest

from src.llm import FakeLLMAdapter
from src.rag.agent import AgentState, build_graph, run_query
from src.sanitizer import SanitizationError, SanitizedText


def test_agent_state_typeddict() -> None:
    """AgentState is a usable TypedDict with required keys."""
    state: AgentState = {
        "raw_query": "test",
        "sanitized_query": "",
        "query_reversible_map": {},
        "query_entity_counts": {},
        "retrieved_docs": [],
        "relevant_docs": [],
        "rewrite_count": 0,
        "regeneration_count": 0,
        "step_count": 0,
        "hard_limit_exceeded": False,
        "prompt": "",
        "prompts": [],
        "response": None,
        "raw_response": "",
        "final_response": "",
        "revealed_response": "",
        "entity_counts": {},
        "output_entity_counts": {},
        "tokens": 0,
        "cost": 0.0,
        "duration_ms": 0.0,
        "audit_trace": [],
    }
    assert state["raw_query"] == "test"


def test_build_graph_compiles() -> None:
    """build_graph constructs and compiles the state graph."""
    app = build_graph()
    assert app is not None
    assert hasattr(app, "invoke")


def test_relevant_chunks_generate_with_citations() -> None:
    """When chunks are graded relevant, agent generates answer citing chunk IDs."""
    fake_adapter = FakeLLMAdapter(
        responses=[
            "yes",  # grade chunk 1
            "yes",  # grade chunk 2
            "yes",  # grade chunk 3
            "yes",  # grade chunk 4
            "According to [loan_agreement_01.txt#chunk_0], the interest rate is 8.65%.",
            "yes",  # verification
        ]
    )

    state = run_query(
        "What is the interest rate in loan agreement 01?",
        adapter=fake_adapter,
    )

    assert "[loan_agreement_01.txt#chunk_0]" in state["final_response"]
    assert "8.65%" in state["final_response"]
    assert state["rewrite_count"] == 0
    assert len(state["relevant_docs"]) >= 2


def test_insufficient_chunks_rewrites_and_falls_back_to_idk() -> None:
    """When chunks are irrelevant, agent rewrites up to 2 times then answers 'I don't know'."""
    # Always grade "no" so zero chunks are considered relevant
    def custom_handler(prompt: SanitizedText) -> str:
        p_str = str(prompt).lower()
        if "grade" in p_str or "relevant to answering" in p_str:
            return "no"
        if "rewrite" in p_str:
            return "rewritten query attempt"
        return "I don't know."

    fake_adapter = FakeLLMAdapter(custom_handler=custom_handler)

    state = run_query(
        "What is the secret recipe for Martian space pie?",
        adapter=fake_adapter,
    )

    # Max 2 rewrites were triggered
    assert state["rewrite_count"] == 2
    assert "I don't know" in state["final_response"]
    assert state["step_count"] <= 15


def test_no_unredacted_text_to_llm() -> None:
    """Security invariant: the text passed to the LLM adapter must NEVER contain unredacted PII."""
    fake_adapter = FakeLLMAdapter()
    query = (
        "My name is Vikram Malhotra, Aadhaar 2345 6789 0124, UPI vikram@okaxis. "
        "What is my loan tenure?"
    )

    state = run_query(query, adapter=fake_adapter)

    # Verify query was sanitized with Q_ namespacing
    assert "[Q_PERSON_1]" in state["sanitized_query"]
    assert "[Q_AADHAAR_1]" in state["sanitized_query"]
    assert "[Q_UPI_1]" in state["sanitized_query"]

    # Verify every single prompt captured by the LLM adapter contains ZERO unredacted values
    assert len(fake_adapter.prompts_received) > 0
    for p in fake_adapter.prompts_received:
        p_str = str(p)
        assert "Vikram Malhotra" not in p_str
        assert "2345 6789 0124" not in p_str
        assert "vikram@okaxis" not in p_str

    # Test reveal restores ONLY user query values
    assert "[Q_PERSON_1]" in state["query_reversible_map"]
    assert state["query_reversible_map"]["[Q_PERSON_1]"] == "Vikram Malhotra"


def test_sanitizer_raises_llm_never_called(monkeypatch: pytest.MonkeyPatch) -> None:
    """If sanitization fails, fail-closed ensures the LLM adapter is never called."""
    import src.rag.agent as agent_mod

    fake_adapter = FakeLLMAdapter()

    def failing_sanitize(*args: Any, **kwargs: Any) -> Any:
        raise SanitizationError("Simulated scanner crash")

    monkeypatch.setattr(agent_mod, "sanitize", failing_sanitize)

    with pytest.raises(SanitizationError, match="Simulated scanner crash"):
        run_query("Some query", adapter=fake_adapter)

    # Zero prompts reached the LLM
    assert len(fake_adapter.prompts_received) == 0


def test_output_guard_redacts_pii_emitted_by_llm() -> None:
    """Output guard redacts any PII pattern the LLM attempts to emit."""
    # LLM emits unredacted PAN and Indian mobile number in its answer
    def custom_handler(prompt: SanitizedText) -> str:
        p_str = str(prompt).lower()
        if "cite the source chunk ids" in p_str:
            return "Contact officer with PAN ABCDE1234F and mobile +91 98220 55443."
        if "supported by the context" in p_str:
            return "yes"
        return "yes"

    fake_adapter = FakeLLMAdapter(custom_handler=custom_handler)

    state = run_query("Who is the contact officer?", adapter=fake_adapter)

    # Output guard must redact them
    assert "ABCDE1234F" not in state["final_response"]
    assert "+91 98220 55443" not in state["final_response"]
    assert "[PAN_1]" in state["final_response"]
    assert "[PHONE_1]" in state["final_response"]
    assert state["output_entity_counts"].get("count_PAN_NUMBER", 0) >= 1
    assert state["output_entity_counts"].get("count_INDIAN_MOBILE", 0) >= 1
