"""Command-line interface for the Secure RAG Agent.

Usage
-----
::

    python -m src.rag.cli ingest   # ingest documents into ChromaDB
    python -m src.rag.cli query "What is the customer's name?"
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


def _cmd_query(args: argparse.Namespace) -> None:
    """Run the agent on a single query."""

    from src.rag.agent import run_query

    state = run_query(args.query)
    # Access response text via the agent state
    _ = state.get("response")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Secure RAG Agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Ingest documents into ChromaDB")

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
    elif args.command == "query":
        _cmd_query(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
