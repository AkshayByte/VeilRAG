"""Document ingestion pipeline.

Steps
-----
1. Load raw documents from ``data/docs/``.
2. Sanitize each document via :func:`src.sanitizer.sanitize`.
3. Chunk the redacted text (sentence-based).
4. Embed chunks locally via :mod:`src.embeddings`.
5. Persist to ChromaDB.

This module is runnable via ``python -m src.rag.ingest``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A single sanitized chunk ready for vector storage."""

    doc_id: str
    chunk_index: int
    text: str
    metadata: dict[str, str]


def load_documents(path: str = "data/docs") -> list[dict[str, str]]:
    """Load raw documents from *path*.

    Returns
    -------
    list[dict[str, str]]
        Each dict has ``id`` and ``text`` keys.
    """

    raise NotImplementedError


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    """Split *text* into roughly sentence-aligned chunks of ≤ *chunk_size* chars."""

    raise NotImplementedError


def ingest_documents(path: str = "data/docs", collection_name: str = "docs") -> int:
    """Run the full ingestion pipeline and return the number of chunks persisted.

    Parameters
    ----------
    path
        Directory containing raw ``.txt`` or ``.md`` documents.
    collection_name
        ChromaDB collection name.
    """

    raise NotImplementedError


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count: int = ingest_documents()
    logger.info("Ingested %d chunks", count)
