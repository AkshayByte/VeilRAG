"""LangGraph state machine for the VeilRAG pipeline.

Graph nodes (in order)
----------------------
1. **sanitize_input** — redact PII from the user's query.
2. **retrieve**       — embed the *sanitized* query locally and search ChromaDB.
3. **compose_prompt** — build the augmented prompt from retrieved chunks.
4. **llm_call**       — send the *sanitized* prompt to the LLM adapter.

Security invariant enforced here: the user's raw query is sanitized at
node 1; only the redacted version ever reaches the LLM (node 4).  This is
verified in ``tests/test_agent.py``.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import StateGraph

from src.llm import LLMResponse
from src.rag.retriever import RetrievedDocument

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Mutable state passed between LangGraph nodes."""

    raw_query: str
    sanitized_query: str
    retrieved_docs: list[RetrievedDocument]
    prompt: str
    response: LLMResponse | None
    entity_counts: dict[str, int]


def build_graph() -> StateGraph:
    """Construct and return the compiled LangGraph agent."""

    raise NotImplementedError


def run_query(query: str) -> AgentState:
    """Convenience function: run the full agent on *query* and return final state."""

    raise NotImplementedError
