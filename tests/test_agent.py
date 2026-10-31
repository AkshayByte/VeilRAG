"""Tests for src/rag/agent.py — including the no-unredacted-text-to-LLM guarantee."""

from __future__ import annotations

import pytest

from src.rag.agent import AgentState, build_graph, run_query


def test_agent_state_typeddict() -> None:
    """AgentState is a usable TypedDict."""

    state: AgentState = {
        "raw_query": "test",
        "sanitized_query": "",
        "retrieved_docs": [],
        "prompt": "",
        "response": None,
        "entity_counts": {},
    }
    assert state["raw_query"] == "test"


def test_build_graph_not_implemented() -> None:
    """build_graph is a stub."""

    with pytest.raises(NotImplementedError):
        build_graph()


def test_run_query_not_implemented() -> None:
    """run_query is a stub."""

    with pytest.raises(NotImplementedError):
        run_query("query")


def test_no_unredacted_text_to_llm() -> None:
    """
    Security invariant: the text passed to the LLM adapter must never contain
    unredacted PII.

    This test will be expanded once the agent is implemented, mocking
    ``LLMAdapter.complete`` and asserting that any PII present in the raw
    query is replaced with a placeholder before the LLM call.
    """

    # Placeholder — real logic added when agent.py is implemented.
    assert True
