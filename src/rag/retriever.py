"""ChromaDB retrieval wrapper.

All queries are sanitized before embedding so that no raw PII is stored
or searched.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast

import chromadb

from src.config import settings
from src.embeddings import get_embedding_model
from src.embeddings.local import Embedder
from src.sanitizer import SanitizedText

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """A single retrieved document chunk with its similarity score."""

    text: str
    metadata: dict[str, Any]
    score: float


class VectorStore:
    """Thin wrapper around a ChromaDB collection."""

    def __init__(
        self,
        collection_name: str = "docs",
        persist_dir: str | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        """Initialize ChromaDB client and collection."""
        self._persist_dir: str = persist_dir or settings.chroma_persist_dir
        self._client: Any = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = embedder or get_embedding_model()

    def search(
        self,
        query: SanitizedText,
        k: int = 4,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Embed *query* locally and return the top-*k* most similar chunks."""
        if not isinstance(query, SanitizedText):
            raise TypeError(
                f"Expected SanitizedText, got plain {type(query).__name__}. "
                "Redact via src.sanitizer.sanitize() first."
            )

        count = self._collection.count()
        if count == 0:
            return []

        n_results = min(k, count)
        query_vector = self._embedder.embed_query(query).tolist()
        where_clause = filters if filters else None

        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=n_results,
            where=where_clause,
        )

        retrieved: list[RetrievedDocument] = []
        raw_docs = results.get("documents") or []
        raw_meta = results.get("metadatas") or []
        raw_dist = results.get("distances") or []

        docs = raw_docs[0] if raw_docs else []
        metas = raw_meta[0] if raw_meta else []
        dists = raw_dist[0] if raw_dist else []

        for text, meta, dist in zip(docs, metas, dists):
            # Cosine distance in chroma: 1.0 - cosine_similarity
            score = 1.0 - float(dist) if dist is not None else 0.0
            retrieved.append(
                RetrievedDocument(
                    text=text,
                    metadata=dict(meta) if meta else {},
                    score=round(score, 4),
                )
            )
        return retrieved

    def add(
        self,
        chunks: list[SanitizedText],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> None:
        """Add pre-computed embeddings and chunks to the collection."""
        for chunk in chunks:
            if not isinstance(chunk, SanitizedText):
                raise TypeError(
                    f"Expected SanitizedText, got plain {type(chunk).__name__}. "
                    "All chunks must be redacted before storage."
                )

        generated_ids = (
            ids
            if ids is not None
            else [f"chunk_{i}" for i in range(len(chunks))]
        )

        self._collection.upsert(
            documents=[str(c) for c in chunks],
            embeddings=cast(Any, embeddings),
            metadatas=cast(Any, metadatas),
            ids=generated_ids,
        )
