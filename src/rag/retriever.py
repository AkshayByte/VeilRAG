"""ChromaDB retrieval wrapper.

All queries are sanitized before embedding so that no raw PII is stored
or searched.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import chromadb

from src.config import settings
from src.embeddings import get_embedding_model

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """A single retrieved document chunk with its similarity score."""

    text: str
    metadata: dict[str, str]
    score: float


class VectorStore:
    """Thin wrapper around a ChromaDB collection."""

    def __init__(self, collection_name: str = "docs", persist_dir: str | None = None) -> None:
        self._persist_dir: str = persist_dir or settings.chroma_persist_dir
        self._client: Any = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(name=collection_name)
        self._embedder = get_embedding_model()

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        """Embed *query* locally and return the top-*k* most similar chunks."""

        raise NotImplementedError

    def add(self, chunks: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
        """Add pre-computed embeddings to the collection."""

        raise NotImplementedError
