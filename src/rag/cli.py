"""Command-line interface for VeilRAG.

Usage
-----
::

    python -m src.rag.cli ingest          # ingest documents into ChromaDB
    python -m src.rag.cli peek --n 3      # peek at stored sanitized chunks
    python -m src.rag.cli query "Question" # run a RAG query
"""

from __future__ import annotations

import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def _cmd_ingest() -> None:
    """Run the ingestion pipeline."""
    from src.rag.ingest import ingest_documents

    count: int = ingest_documents()
    logger.info("Ingested %d chunks", count)


def _cmd_peek(args: argparse.Namespace) -> None:
    """Inspect sanitized chunks stored in ChromaDB."""
    from src.rag.retriever import VectorStore

    store = VectorStore()
    records = store.peek(n=args.n)
    if not records:
        print("No documents found in ChromaDB collection.")
        return

    print(f"\n=== Peek: Displaying {len(records)} Chunk(s) from ChromaDB ===")
    for i, r in enumerate(records, start=1):
        cid = r["id"]
        meta = r["metadata"]
        text = r["document"]
        preview = text.replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:120] + "..."
        print(f"[{i}] Chunk ID: {cid}")
        print(f"    Source:      {meta.get('source')} | Doc Type: {meta.get('doc_type')}")
        print(f"    Index:       {meta.get('chunk_index')} | Risk: {meta.get('risk_score')}")
        print(f"    PII Count:   {meta.get('entity_count')}")
        if getattr(args, "full", False):
            print(f"    Full Text:\n{text}")
        else:
            preview = text.replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:120] + "..."
            print(f"    Preview:     {preview}")
    print("\n============================================================\n")


def _cmd_query(args: argparse.Namespace) -> None:
    """Run the agent on a single query."""
    from src.rag.agent import run_query

    state = run_query(args.query)
    ans = state.get("final_response", "")
    print(f"Answer: {ans}")


def _cmd_ask(args: argparse.Namespace) -> None:
    """Run the corrective-RAG agent on a question."""
    from src.llm import get_adapter
    from src.rag.agent import run_query

    adapter = None
    provider = getattr(args, "provider", None)
    model = getattr(args, "model", None)
    if provider or model:
        adapter = get_adapter(provider=provider, model=model)

    state = run_query(args.question, adapter=adapter)

    if getattr(args, "show_prompts", False):
        prompts = state.get("prompts", [])
        print("\n=== Prompts Sent to LLM ===")
        for i, p in enumerate(prompts, start=1):
            print(f"\n--- Prompt {i} ---")
            print(p)
        print("\n===========================\n")

    if getattr(args, "reveal", False):
        ans = state.get("revealed_response", "")
    else:
        ans = state.get("final_response", "")

    print(f"Answer: {ans}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="VeilRAG CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Ingest documents into ChromaDB")

    p = sub.add_parser("peek", help="Inspect chunks stored in ChromaDB")
    p.add_argument("--n", "-n", type=int, default=3, help="Number of chunks to display")
    p.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="Print entire chunk text instead of preview",
    )

    q = sub.add_parser("query", help="Run a single RAG query")
    q.add_argument("query", type=str, help="The question to ask")

    ask_p = sub.add_parser("ask", help="Ask a question using the corrective-RAG agent")
    ask_p.add_argument("question", type=str, help="The question to ask")
    ask_p.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=["fake", "ollama", "anthropic"],
        help="LLM provider adapter (default: settings.llm_provider)",
    )
    ask_p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name override",
    )
    ask_p.add_argument(
        "--reveal",
        action="store_true",
        default=False,
        help=(
            "Restore values typed by the user in the query using the request-scoped query map. "
            "Chunk originals are never stored and can never be revealed."
        ),
    )
    ask_p.add_argument(
        "--show-prompts",
        action="store_true",
        default=False,
        help="Print all prompts sent to the LLM adapter across all graph nodes",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        _cmd_ingest()
    elif args.command == "peek":
        _cmd_peek(args)
    elif args.command == "query":
        _cmd_query(args)
    elif args.command == "ask":
        _cmd_ask(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
