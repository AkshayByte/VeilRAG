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
        print(f"\n[{i}] Chunk ID: {cid}")
        print(f"    Source:      {meta.get('source')} | Doc Type: {meta.get('doc_type')}")
        print(f"    Index:       {meta.get('chunk_index')} | Risk: {meta.get('risk_score')}")
        print(f"    PII Count:   {meta.get('entity_count')}")
        print(f"    Preview:     {preview}")
    print("\n============================================================\n")


def _cmd_query(args: argparse.Namespace) -> None:
    """Run the agent on a single query."""
    from src.rag.agent import run_query

    state = run_query(args.query)
    _ = state.get("response")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="VeilRAG CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Ingest documents into ChromaDB")

    p = sub.add_parser("peek", help="Inspect chunks stored in ChromaDB")
    p.add_argument("--n", "-n", type=int, default=3, help="Number of chunks to display")

    q = sub.add_parser("query", help="Run a single RAG query")
    q.add_argument("query", type=str, help="The question to ask")

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

    return 0


if __name__ == "__main__":
    sys.exit(main())
