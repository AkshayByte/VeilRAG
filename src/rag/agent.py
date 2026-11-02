"""LangGraph corrective-RAG state graph for VeilRAG.

Architecture
------------
1. **sanitize_query** — Redact PII from user query with ``mode=PIPELINE_MODE`` and
   ``placeholder_prefix="Q_"`` to prevent collision with document-level chunk placeholders.
2. **retrieve** — Embed sanitized query and search vector store.
3. **grade_documents** — LLM evaluates whether each retrieved chunk is relevant (yes/no).
4. **rewrite_query** (conditional) — If fewer than 1 relevant chunk, rewrite query (max 2 rewrites)
   and loop back to **retrieve**.
5. **generate** — Answer question strictly from context citing source chunk IDs.
6. **verify_answer** — Check that every claim is supported by retrieved context.
   Regenerate once if unsupported; otherwise fall back to "I don't know."
7. **output_guard** — Sanitize final LLM response with ``mode=PIPELINE_MODE``,
   recording output entity types and counts.

Security Invariants
-------------------
- Zero unredacted query text reaches the LLM adapter (enforced via SanitizedText).
- Node telemetry records duration, tokens, cost, and entity TYPES/counts only, never raw PII values.
- Ephemeral query reversible map exists exclusively in request scope.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Literal, NotRequired, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.config import PIPELINE_MODE
from src.llm import LLMAdapter, LLMResponse, get_adapter
from src.rag.retriever import RetrievedDocument, VectorStore
from src.sanitizer import SanitizedText, sanitize

logger = logging.getLogger(__name__)

MAX_STEPS = 15
MAX_REWRITES = 2


class AgentState(TypedDict):
    """State schema for the corrective-RAG agent graph."""

    raw_query: str
    sanitized_query: str
    query_reversible_map: dict[str, str]
    query_entity_counts: dict[str, int]
    retrieved_docs: list[RetrievedDocument]
    relevant_docs: list[RetrievedDocument]
    first_pass_retrieved_docs: NotRequired[list[RetrievedDocument]]
    all_retrieved_docs: NotRequired[list[RetrievedDocument]]
    rewrite_count: int
    regeneration_count: int
    step_count: int
    hard_limit_exceeded: bool
    prompt: str
    prompts: list[str]
    response: LLMResponse | None
    raw_response: str
    final_response: str
    revealed_response: str
    entity_counts: dict[str, int]
    output_entity_counts: dict[str, int]
    tokens: int
    cost: float
    duration_ms: float
    audit_trace: list[dict[str, Any]]
    unparseable_verifier_count: NotRequired[int]


def build_graph(
    adapter: LLMAdapter | None = None,
    enable_grading: bool = True,
    enable_rewrite: bool = True,
    enable_verification: bool = True,
    enable_output_guard: bool = True,
) -> CompiledStateGraph:
    """Construct and return the compiled LangGraph agent.

    Parameters
    ----------
    adapter:
        LLM adapter instance (defaults to configured system adapter).
    enable_grading:
        Whether to grade candidate retrieved documents for relevance.
    enable_rewrite:
        Whether to rewrite queries when insufficient relevant chunks are found.
    enable_verification:
        Whether to verify factual claims in generated answers against context.
    enable_output_guard:
        Whether to sanitize the final answer with PIPELINE_MODE.
    """
    active_adapter = adapter or get_adapter()
    vector_store = VectorStore()

    def sanitize_query_node(state: AgentState) -> dict[str, Any]:
        """Node 1: Sanitize user query with namespaced placeholders."""
        t0 = time.perf_counter()
        raw = state["raw_query"]
        res = sanitize(raw, mode=PIPELINE_MODE, placeholder_prefix="Q_")
        dur = (time.perf_counter() - t0) * 1000

        counts: dict[str, int] = {}
        for ent in res.entities:
            key = f"count_{ent.entity_type}"
            counts[key] = counts.get(key, 0) + 1

        logger.info(
            "Node [sanitize_query] completed: duration=%.1fms entity_counts=%s",
            dur,
            counts,
        )

        trace_entry = {
            "node": "sanitize_query",
            "duration_ms": dur,
            "entity_types": list(counts.keys()),
            "entity_counts": counts,
        }

        return {
            "sanitized_query": res.safe,
            "query_reversible_map": res.reversible_map,
            "query_entity_counts": counts,
            "entity_counts": counts,
            "step_count": state.get("step_count", 0) + 1,
            "duration_ms": state.get("duration_ms", 0.0) + dur,
            "audit_trace": state.get("audit_trace", []) + [trace_entry],
        }

    def retrieve_node(state: AgentState) -> dict[str, Any]:
        """Node 2: Retrieve candidate chunks from vector store."""
        t0 = time.perf_counter()
        steps = state.get("step_count", 0) + 1
        if steps >= MAX_STEPS:
            logger.warning("Hard step limit exceeded (%d steps)", steps)
            return {
                "step_count": steps,
                "hard_limit_exceeded": True,
            }

        sanitized_q = state["sanitized_query"]
        safe_q = SanitizedText(str(sanitized_q), _sentinel=SanitizedText._SENTINEL)
        docs = vector_store.search(query=safe_q, k=4)
        dur = (time.perf_counter() - t0) * 1000

        logger.info(
            "Node [retrieve] completed: duration=%.1fms retrieved=%d",
            dur,
            len(docs),
        )

        first_pass = state.get("first_pass_retrieved_docs")
        if first_pass is None:
            first_pass = docs

        prev_all = state.get("all_retrieved_docs", [])
        combined_all = list(prev_all)
        existing_ids = {d.id for d in combined_all}
        for d in docs:
            if d.id not in existing_ids:
                combined_all.append(d)
                existing_ids.add(d.id)

        trace_entry = {
            "node": "retrieve",
            "duration_ms": dur,
            "retrieved_count": len(docs),
            "retrieved_doc_ids": [d.id for d in docs],
        }

        return {
            "retrieved_docs": docs,
            "first_pass_retrieved_docs": first_pass,
            "all_retrieved_docs": combined_all,
            "step_count": steps,
            "duration_ms": state.get("duration_ms", 0.0) + dur,
            "audit_trace": state.get("audit_trace", []) + [trace_entry],
        }

    def grade_documents_node(state: AgentState) -> dict[str, Any]:
        """Node 3: Grade candidate documents for relevance."""
        t0 = time.perf_counter()
        steps = state.get("step_count", 0) + 1
        if steps >= MAX_STEPS:
            return {"step_count": steps, "hard_limit_exceeded": True}

        docs = state.get("retrieved_docs", [])

        if not enable_grading:
            # Grading disabled: consider all retrieved chunks relevant without calling LLM
            dur = (time.perf_counter() - t0) * 1000
            trace_entry = {
                "node": "grade_documents",
                "duration_ms": dur,
                "tokens": 0,
                "cost": 0.0,
                "relevant_count": len(docs),
                "skipped": True,
            }
            return {
                "relevant_docs": docs,
                "step_count": steps,
                "duration_ms": state.get("duration_ms", 0.0) + dur,
                "audit_trace": state.get("audit_trace", []) + [trace_entry],
            }

        q = state["sanitized_query"]
        relevant: list[RetrievedDocument] = []
        new_prompts: list[str] = []
        grader_decisions: list[dict[str, Any]] = []
        tokens_added = 0
        cost_added = 0.0

        for d in docs:
            p_text = (
                f"You are a document grader evaluating relevance to a user question.\n\n"
                f"Question: {q}\n\n"
                f"Document [{d.id}]:\n{d.text}\n\n"
                f"A document chunk is relevant ONLY IF it contains the answer to the "
                f"question AND matches any document ID or organization named in the question.\n"
                f"If the document is for a different organization or document ID, or does not "
                f"contain the answer, it is not relevant.\n"
                f"Output must be exactly Yes or No."
            )
            safe_p = SanitizedText(p_text, _sentinel=SanitizedText._SENTINEL)
            new_prompts.append(p_text)
            resp = active_adapter.complete(safe_p)
            tokens_added += resp.input_tokens + resp.output_tokens
            cost_added += resp.cost
            raw_t = resp.text.strip()
            words = raw_t.split()
            first_w = words[0].lower().rstrip(".,:;!?") if words else ""
            is_rel = (first_w == "yes")
            is_clean = (first_w in ("yes", "no")) and (len(words) == 1)
            grader_decisions.append({
                "chunk_id": d.id,
                "response_text": raw_t,
                "relevant": is_rel,
                "is_clean": is_clean,
            })
            if is_rel:
                relevant.append(d)

        dur = (time.perf_counter() - t0) * 1000
        logger.info(
            "Node [grade_documents] completed: duration=%.1fms relevant=%d/%d tokens=%d cost=$%.6f",
            dur,
            len(relevant),
            len(docs),
            tokens_added,
            cost_added,
        )

        trace_entry = {
            "node": "grade_documents",
            "stage": "grade_documents",
            "duration_ms": dur,
            "tokens": tokens_added,
            "cost": cost_added,
            "relevant_count": len(relevant),
            "decisions": grader_decisions,
        }

        return {
            "relevant_docs": relevant,
            "prompts": state.get("prompts", []) + new_prompts,
            "tokens": state.get("tokens", 0) + tokens_added,
            "cost": state.get("cost", 0.0) + cost_added,
            "step_count": steps,
            "duration_ms": state.get("duration_ms", 0.0) + dur,
            "audit_trace": state.get("audit_trace", []) + [trace_entry],
        }

    def decide_to_generate(
        state: AgentState,
    ) -> Literal["generate", "rewrite_query", "output_guard"]:
        """Conditional routing from grade_documents."""
        if not enable_grading:
            return "generate"
        if state.get("hard_limit_exceeded"):
            return "output_guard"
        rel_count = len(state.get("relevant_docs", []))
        rewrites = state.get("rewrite_count", 0)

        if not enable_rewrite:
            return "generate"
        if rel_count >= 1 or rewrites >= MAX_REWRITES:
            return "generate"
        return "rewrite_query"

    def rewrite_query_node(state: AgentState) -> dict[str, Any]:
        """Node 4: Rewrite query when retrieval yields insufficient chunks."""
        t0 = time.perf_counter()
        steps = state.get("step_count", 0) + 1
        rewrites = state.get("rewrite_count", 0) + 1

        prompt_str = (
            f"You are a query rewriter. The following query retrieved insufficient "
            f"relevant documents:\n"
            f"Query: {state['sanitized_query']}\n\n"
            f"Rewrite the query to be clearer, more specific, and optimize for document retrieval. "
            f"Output ONLY the rewritten query text."
        )
        safe_p = SanitizedText(prompt_str, _sentinel=SanitizedText._SENTINEL)
        resp = active_adapter.complete(safe_p)
        tokens_added = resp.input_tokens + resp.output_tokens
        cost_added = resp.cost

        # Re-sanitize the rewritten query with PIPELINE_MODE and Q_ prefix
        res = sanitize(resp.text, mode=PIPELINE_MODE, placeholder_prefix="Q_")
        dur = (time.perf_counter() - t0) * 1000

        logger.info(
            "Node [rewrite_query] (attempt %d/%d): duration=%.1fms tokens=%d cost=$%.6f",
            rewrites,
            MAX_REWRITES,
            dur,
            tokens_added,
            cost_added,
        )

        trace_entry = {
            "node": "rewrite_query",
            "rewrite_attempt": rewrites,
            "duration_ms": dur,
            "tokens": tokens_added,
            "cost": cost_added,
        }

        # Merge newly discovered placeholders into query_reversible_map
        merged_map = dict(state.get("query_reversible_map", {}))
        merged_map.update(res.reversible_map)

        return {
            "sanitized_query": res.safe,
            "query_reversible_map": merged_map,
            "rewrite_count": rewrites,
            "prompts": state.get("prompts", []) + [prompt_str],
            "tokens": state.get("tokens", 0) + tokens_added,
            "cost": state.get("cost", 0.0) + cost_added,
            "step_count": steps,
            "duration_ms": state.get("duration_ms", 0.0) + dur,
            "audit_trace": state.get("audit_trace", []) + [trace_entry],
        }

    def generate_node(state: AgentState) -> dict[str, Any]:
        """Node 5: Generate answer citing chunk IDs."""
        t0 = time.perf_counter()
        steps = state.get("step_count", 0) + 1
        if state.get("hard_limit_exceeded"):
            return {
                "raw_response": "I don't know.",
                "step_count": steps,
            }

        if not enable_grading:
            docs = state.get("retrieved_docs", [])
            if len(docs) == 0:
                dur = (time.perf_counter() - t0) * 1000
                return {
                    "raw_response": "I don't know.",
                    "prompt": "",
                    "step_count": steps,
                    "duration_ms": state.get("duration_ms", 0.0) + dur,
                }
        else:
            docs = state.get("relevant_docs", [])
            if len(docs) < 1:
                dur = (time.perf_counter() - t0) * 1000
                return {
                    "raw_response": "I don't know.",
                    "prompt": "",
                    "step_count": steps,
                    "duration_ms": state.get("duration_ms", 0.0) + dur,
                }

        context_str = "\n\n".join([f"[{d.id}]\n{d.text}" for d in docs])
        prompt_str = (
            f"You are an assistant answering a question based strictly on the provided context.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {state['sanitized_query']}\n\n"
            f"Answer the question based strictly on the context. "
            f"You MUST cite the source chunk IDs (e.g. [doc_id#chunk_n]) for every fact mentioned. "
            f"If the context does not contain enough information to answer, state 'I don't know.'"
        )
        safe_p = SanitizedText(prompt_str, _sentinel=SanitizedText._SENTINEL)
        resp = active_adapter.complete(safe_p)
        tokens_added = resp.input_tokens + resp.output_tokens
        cost_added = resp.cost
        dur = (time.perf_counter() - t0) * 1000

        logger.info(
            "Node [generate] completed: duration=%.1fms tokens=%d cost=$%.6f",
            dur,
            tokens_added,
            cost_added,
        )

        trace_entry = {
            "node": "generate",
            "duration_ms": dur,
            "tokens": tokens_added,
            "cost": cost_added,
        }

        return {
            "raw_response": resp.text,
            "response": resp,
            "prompt": prompt_str,
            "prompts": state.get("prompts", []) + [prompt_str],
            "tokens": state.get("tokens", 0) + tokens_added,
            "cost": state.get("cost", 0.0) + cost_added,
            "step_count": steps,
            "duration_ms": state.get("duration_ms", 0.0) + dur,
            "audit_trace": state.get("audit_trace", []) + [trace_entry],
        }

    def verify_answer_node(state: AgentState) -> dict[str, Any]:
        """Node 6: Verify factual claims against context; regenerate once if needed."""
        t0 = time.perf_counter()
        steps = state.get("step_count", 0) + 1
        raw_ans = state.get("raw_response", "").strip()

        if not enable_verification:
            # Verification disabled: keep raw_response unchanged without LLM verification
            dur = (time.perf_counter() - t0) * 1000
            trace_entry = {
                "node": "verify_answer",
                "duration_ms": dur,
                "tokens": 0,
                "cost": 0.0,
                "skipped": True,
            }
            return {
                "raw_response": raw_ans,
                "step_count": steps,
                "duration_ms": state.get("duration_ms", 0.0) + dur,
                "audit_trace": state.get("audit_trace", []) + [trace_entry],
            }

        if not raw_ans or raw_ans.lower().startswith("i don't know"):
            dur = (time.perf_counter() - t0) * 1000
            return {
                "raw_response": "I don't know.",
                "step_count": steps,
                "duration_ms": state.get("duration_ms", 0.0) + dur,
            }

        docs = state.get("relevant_docs", []) or state.get("retrieved_docs", [])
        context_str = "\n\n".join([f"[{d.id}]\n{d.text}" for d in docs])
        valid_chunk_ids = {d.id for d in docs}

        # Citation check: if answer cites chunk IDs not in context, treat as failed verification
        initial_cites = re.findall(r"\[([a-zA-Z0-9_\-\.]+#chunk_\d+)\]", raw_ans)
        initial_invalid_cites = [c for c in initial_cites if c not in valid_chunk_ids]

        verify_p = (
            f"You are a factual verification assistant checking for hallucinations.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Answer:\n{raw_ans}\n\n"
            f"Is every factual claim in the answer supported by the context?\n"
            f"Output must be exactly Yes or No."
        )
        safe_v = SanitizedText(verify_p, _sentinel=SanitizedText._SENTINEL)
        v_resp = active_adapter.complete(safe_v)
        tokens_added = v_resp.input_tokens + v_resp.output_tokens
        cost_added = v_resp.cost
        new_prompts = [verify_p]
        final_raw = raw_ans

        initial_resp_text = v_resp.text.strip()
        v1_words = initial_resp_text.split()
        v1_first = v1_words[0].lower().rstrip(".,:;!?") if v1_words else ""
        v1_unparseable = v1_first not in ("yes", "no")
        unparseable_count = 1 if v1_unparseable else 0

        # Initial verification succeeds only if first word is 'yes' AND citations are in context
        initial_verified = (v1_first == "yes") and (len(initial_invalid_cites) == 0)

        rejected_answer: str | None = None
        regen_answer: str | None = None
        secondary_verified: bool | None = None
        secondary_resp_text: str | None = None

        if initial_verified:
            logger.info("Verification passed: factual claims confirmed supported")
        else:
            logger.warning(
                "Verification failed: unsupported claims or invalid citations (invalid: %s)",
                initial_invalid_cites,
            )
            rejected_answer = raw_ans
            if state.get("regeneration_count", 0) < 1:
                # Regenerate once
                regen_p = (
                    f"The previous answer contained unsupported claims or invalid citations.\n\n"
                    f"Context:\n{context_str}\n\n"
                    f"Question: {state['sanitized_query']}\n\n"
                    f"Generate an answer strictly supported by the context, citing ONLY chunk IDs "
                    f"present in the context above (e.g. [doc_id.txt#chunk_n]). "
                    f"If the context does not contain the answer, reply 'I don't know.'"
                )
                safe_r = SanitizedText(regen_p, _sentinel=SanitizedText._SENTINEL)
                new_prompts.append(regen_p)
                r_resp = active_adapter.complete(safe_r)
                tokens_added += r_resp.input_tokens + r_resp.output_tokens
                cost_added += r_resp.cost
                regen_answer = r_resp.text

                # Second verification check
                regen_cites = re.findall(r"\[([a-zA-Z0-9_\-\.]+#chunk_\d+)\]", r_resp.text)
                regen_invalid_cites = [c for c in regen_cites if c not in valid_chunk_ids]

                v2_p = (
                    f"Context:\n{context_str}\n\n"
                    f"Answer:\n{r_resp.text}\n\n"
                    f"Is every claim supported by the context?\n"
                    f"Output must be exactly Yes or No."
                )
                safe_v2 = SanitizedText(v2_p, _sentinel=SanitizedText._SENTINEL)
                new_prompts.append(v2_p)
                v2_resp = active_adapter.complete(safe_v2)
                tokens_added += v2_resp.input_tokens + v2_resp.output_tokens
                cost_added += v2_resp.cost
                secondary_resp_text = v2_resp.text.strip()
                v2_words = secondary_resp_text.split()
                v2_first = v2_words[0].lower().rstrip(".,:;!?") if v2_words else ""
                if v2_first not in ("yes", "no"):
                    unparseable_count += 1
                secondary_verified = (v2_first == "yes") and (len(regen_invalid_cites) == 0)

                if secondary_verified:
                    final_raw = r_resp.text
                else:
                    final_raw = "I don't know."
            else:
                final_raw = "I don't know."

        dur = (time.perf_counter() - t0) * 1000
        logger.info(
            "Node [verify_answer] completed: duration=%.1fms tokens=%d cost=$%.6f",
            dur,
            tokens_added,
            cost_added,
        )

        trace_entry = {
            "node": "verify_answer",
            "stage": "verify_answer",
            "duration_ms": dur,
            "tokens": tokens_added,
            "cost": cost_added,
            "verified": initial_verified,
            "verifier_response": initial_resp_text,
            "invalid_citations": initial_invalid_cites,
            "unparseable": v1_unparseable,
            "rejected_answer": rejected_answer,
            "regenerated_answer": regen_answer,
            "secondary_verified": secondary_verified,
            "secondary_verifier_response": secondary_resp_text,
            "unparseable_verifier_count": unparseable_count,
        }

        return {
            "raw_response": final_raw,
            "regeneration_count": state.get("regeneration_count", 0) + 1,
            "unparseable_verifier_count": (
                state.get("unparseable_verifier_count", 0) + unparseable_count
            ),
            "prompts": state.get("prompts", []) + new_prompts,
            "tokens": state.get("tokens", 0) + tokens_added,
            "cost": state.get("cost", 0.0) + cost_added,
            "step_count": steps,
            "duration_ms": state.get("duration_ms", 0.0) + dur,
            "audit_trace": state.get("audit_trace", []) + [trace_entry],
        }

    def output_guard_node(state: AgentState) -> dict[str, Any]:
        """Node 7: Output guard sanitizing final response."""
        t0 = time.perf_counter()
        steps = state.get("step_count", 0) + 1
        raw_ans = state.get("raw_response", "I don't know.")

        if not enable_output_guard:
            # Output guard disabled: pass through unredacted LLM output
            dur = (time.perf_counter() - t0) * 1000
            revealed = raw_ans
            for placeholder, original in state.get("query_reversible_map", {}).items():
                revealed = revealed.replace(placeholder, original)
            trace_entry = {
                "node": "output_guard",
                "duration_ms": dur,
                "entity_types": [],
                "entity_counts": {},
                "skipped": True,
            }
            return {
                "final_response": raw_ans,
                "revealed_response": revealed,
                "output_entity_counts": {},
                "step_count": steps,
                "duration_ms": state.get("duration_ms", 0.0) + dur,
                "audit_trace": state.get("audit_trace", []) + [trace_entry],
            }

        # Sanitize LLM answer with PIPELINE_MODE
        res = sanitize(raw_ans, mode=PIPELINE_MODE)
        dur = (time.perf_counter() - t0) * 1000

        counts: dict[str, int] = {}
        for ent in res.entities:
            key = f"count_{ent.entity_type}"
            counts[key] = counts.get(key, 0) + 1

        logger.info(
            "Node [output_guard] completed: duration=%.1fms entity_counts=%s",
            dur,
            counts,
        )

        # Build revealed response (reversing ONLY user query placeholders)
        revealed = str(res.safe)
        for placeholder, original in state.get("query_reversible_map", {}).items():
            revealed = revealed.replace(placeholder, original)

        trace_entry = {
            "node": "output_guard",
            "duration_ms": dur,
            "entity_types": list(counts.keys()),
            "entity_counts": counts,
        }

        return {
            "final_response": res.safe,
            "revealed_response": revealed,
            "output_entity_counts": counts,
            "step_count": steps,
            "duration_ms": state.get("duration_ms", 0.0) + dur,
            "audit_trace": state.get("audit_trace", []) + [trace_entry],
        }

    workflow = StateGraph(AgentState)

    workflow.add_node("sanitize_query", sanitize_query_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("verify_answer", verify_answer_node)
    workflow.add_node("output_guard", output_guard_node)

    workflow.set_entry_point("sanitize_query")
    workflow.add_edge("sanitize_query", "retrieve")
    workflow.add_edge("retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "generate": "generate",
            "rewrite_query": "rewrite_query",
            "output_guard": "output_guard",
        },
    )

    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("generate", "verify_answer")
    workflow.add_edge("verify_answer", "output_guard")
    workflow.add_edge("output_guard", END)

    return workflow.compile()


def run_query(
    query: str,
    adapter: LLMAdapter | None = None,
    reveal: bool = False,
    enable_grading: bool = True,
    enable_rewrite: bool = True,
    enable_verification: bool = True,
    enable_output_guard: bool = True,
) -> AgentState:
    """Run the corrective-RAG state graph on *query* and return final state."""
    app = build_graph(
        adapter=adapter,
        enable_grading=enable_grading,
        enable_rewrite=enable_rewrite,
        enable_verification=enable_verification,
        enable_output_guard=enable_output_guard,
    )

    initial_state: AgentState = {
        "raw_query": query,
        "sanitized_query": "",
        "query_reversible_map": {},
        "query_entity_counts": {},
        "retrieved_docs": [],
        "relevant_docs": [],
        "first_pass_retrieved_docs": [],
        "all_retrieved_docs": [],
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
        "unparseable_verifier_count": 0,
    }

    raw_final: dict[str, Any] = app.invoke(initial_state)
    return AgentState(
        raw_query=raw_final["raw_query"],
        sanitized_query=raw_final["sanitized_query"],
        query_reversible_map=raw_final["query_reversible_map"],
        query_entity_counts=raw_final["query_entity_counts"],
        retrieved_docs=raw_final["retrieved_docs"],
        relevant_docs=raw_final["relevant_docs"],
        first_pass_retrieved_docs=raw_final.get(
            "first_pass_retrieved_docs", raw_final["retrieved_docs"]
        ),
        all_retrieved_docs=raw_final.get(
            "all_retrieved_docs", raw_final["retrieved_docs"]
        ),
        rewrite_count=raw_final["rewrite_count"],
        regeneration_count=raw_final["regeneration_count"],
        step_count=raw_final["step_count"],
        hard_limit_exceeded=raw_final["hard_limit_exceeded"],
        prompt=raw_final["prompt"],
        prompts=raw_final["prompts"],
        response=raw_final["response"],
        raw_response=raw_final["raw_response"],
        final_response=raw_final["final_response"],
        revealed_response=raw_final["revealed_response"],
        entity_counts=raw_final["entity_counts"],
        output_entity_counts=raw_final["output_entity_counts"],
        tokens=raw_final["tokens"],
        cost=raw_final["cost"],
        duration_ms=raw_final["duration_ms"],
        audit_trace=raw_final["audit_trace"],
        unparseable_verifier_count=raw_final.get("unparseable_verifier_count", 0),
    )
