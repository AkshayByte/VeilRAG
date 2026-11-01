"""Document ingestion pipeline for VeilRAG.

Steps
-----
1. Load raw documents from ``data/docs/``.
2. Sanitize whole document via :func:`src.sanitizer.sanitize`.
3. Discard reversible placeholder map immediately (ephemeral).
4. Chunk the redacted text (sentence-aligned, configurable token count and overlap).
5. Extract entity metadata (entity count, risk score, per-type counts; zero raw PII).
6. Embed chunks locally via :mod:`src.embeddings`.
7. Persist to ChromaDB (idempotent upsert, cosine distance).

This module is runnable via ``python -m src.rag.ingest``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import settings
from src.embeddings import get_embedding_model
from src.embeddings.local import Embedder
from src.rag.retriever import VectorStore
from src.sanitizer import SanitizedText, sanitize

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A single sanitized chunk ready for vector storage."""

    doc_id: str
    chunk_index: int
    text: SanitizedText
    metadata: dict[str, Any]


def load_documents(path: str = "data/docs") -> list[dict[str, str]]:
    """Load raw documents from *path*.

    Returns
    -------
    list[dict[str, str]]
        Each dict has ``id``, ``text``, and ``doc_type`` keys.
    """
    doc_dir = Path(path)
    if not doc_dir.exists():
        logger.warning("Document directory does not exist: %s", path)
        return []

    documents: list[dict[str, str]] = []
    # Collect all .txt and .md files excluding hidden/internal files starting with . or _
    files = sorted(
        [
            f
            for f in doc_dir.iterdir()
            if f.is_file()
            and f.suffix.lower() in [".txt", ".md"]
            and not f.name.startswith((".", "_"))
        ]
    )

    for f in files:
        text = f.read_text(encoding="utf-8")
        filename = f.name
        # Infer doc_type from filename prefix
        if filename.startswith("hr_policy"):
            doc_type = "hr_policy"
        elif filename.startswith("loan_agreement"):
            doc_type = "loan_agreement"
        elif filename.startswith("hospital_discharge"):
            doc_type = "hospital_discharge"
        elif filename.startswith("insurance_claim"):
            doc_type = "insurance_claim"
        elif filename.startswith("kyc_form"):
            doc_type = "kyc_form"
        else:
            doc_type = filename.split("_")[0] if "_" in filename else "general"

        documents.append({"id": filename, "text": text, "doc_type": doc_type})

    logger.info("Loaded %d documents from %s", len(documents), path)
    return documents


def _count_tokens(text: str) -> int:
    """Estimate token count based on words and punctuation tokens."""
    return len(re.findall(r"\w+|[^\w\s]", text))


def chunk_text(
    text: SanitizedText,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[SanitizedText]:
    """Split *text* into roughly sentence-aligned chunks of <= *chunk_size* tokens.

    Parameters
    ----------
    text
        The sanitized document text. Must be a SanitizedText instance.
    chunk_size
        Target chunk size in tokens (default 500).
    overlap
        Overlap between consecutive chunks in tokens (default 100).
    """
    if not isinstance(text, SanitizedText):
        raise TypeError(
            f"Expected SanitizedText, got plain {type(text).__name__}. "
            "Redact whole document via src.sanitizer.sanitize() before chunking."
        )

    if not text.strip():
        return []

    total_tokens = _count_tokens(text)
    if total_tokens <= chunk_size:
        return [text]

    # Split into sentence-like segments on sentence end boundaries or double newlines
    sentences = re.split(r"(?<=[.!?\n])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = _count_tokens(sent)

        # If a single sentence exceeds chunk_size, split it into word-level sub-chunks
        if sent_tokens > chunk_size:
            words = sent.split()
            sub_words: list[str] = []
            for w in words:
                sub_words.append(w)
                if len(sub_words) >= chunk_size:
                    chunks.append(" ".join(sub_words))
                    sub_words = sub_words[-overlap:] if overlap > 0 else []
            if sub_words:
                current_sentences = [" ".join(sub_words)]
                current_tokens = len(sub_words)
            continue

        if current_tokens + sent_tokens > chunk_size and current_sentences:
            # Emit current chunk
            chunk_str = " ".join(current_sentences)
            chunks.append(chunk_str)

            # Build overlap from trailing sentences
            overlap_sentences: list[str] = []
            overlap_count = 0
            for prev_sent in reversed(current_sentences):
                p_tokens = _count_tokens(prev_sent)
                if overlap_count + p_tokens <= overlap:
                    overlap_sentences.insert(0, prev_sent)
                    overlap_count += p_tokens
                else:
                    break
            current_sentences = overlap_sentences
            current_tokens = overlap_count

        current_sentences.append(sent)
        current_tokens += sent_tokens

    if current_sentences:
        chunk_str = " ".join(current_sentences)
        chunks.append(chunk_str)

    # Wrap each chunk into SanitizedText using sentinel
    return [
        SanitizedText(c, _sentinel=SanitizedText._SENTINEL)
        for c in chunks
    ]


def ingest_documents(
    path: str = "data/docs",
    collection_name: str = "docs",
    persist_dir: str | None = None,
    embedder: Embedder | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> int:
    """Run the full fail-closed, idempotent ingestion pipeline.

    Parameters
    ----------
    path
        Directory containing raw documents.
    collection_name
        ChromaDB collection name.
    persist_dir
        Optional directory for ChromaDB persistence.
    embedder
        Optional custom Embedder instance.

    Returns
    -------
    int
        Total number of chunks persisted.
    """
    c_size = chunk_size or settings.chunk_size_tokens
    c_overlap = chunk_overlap or settings.chunk_overlap_tokens

    raw_docs = load_documents(path)
    if not raw_docs:
        logger.info("No documents found in %s to ingest.", path)
        return 0

    all_chunks: list[SanitizedText] = []
    all_metadatas: list[dict[str, Any]] = []
    all_ids: list[str] = []

    successful_docs = 0
    failed_docs = 0

    for doc in raw_docs:
        doc_id = doc["id"]
        doc_type = doc.get("doc_type", "general")
        raw_text = doc["text"]

        try:
            # 1. Sanitize whole document with enterprise entity types
            extra_ents = ["IFSC_CODE", "UPI_ID", "MEDICAL_RECORD_NUMBER", "PATIENT_ID"]
            result = sanitize(raw_text, extra_entities=extra_ents)

            # 2. Ephemeral reversible map discarded immediately
            del result.reversible_map

            # 3. Aggregate entity counts and risk score (zero raw PII in metadata)
            entity_count = len(result.entities)
            risk_score = result.risk_score
            type_counts: dict[str, int] = {}
            for ent in result.entities:
                key = f"count_{ent.entity_type}"
                type_counts[key] = type_counts.get(key, 0) + 1

            # 4. Chunk sanitized text
            chunks = chunk_text(result.safe, chunk_size=c_size, overlap=c_overlap)

            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}#chunk_{i}"
                meta: dict[str, Any] = {
                    "source": doc_id,
                    "doc_type": doc_type,
                    "chunk_id": chunk_id,
                    "chunk_index": i,
                    "entity_count": entity_count,
                    "risk_score": risk_score,
                }
                meta.update(type_counts)

                all_chunks.append(chunk)
                all_metadatas.append(meta)
                all_ids.append(chunk_id)

            successful_docs += 1
            logger.info("Processed %s -> %d chunks (risk: %.2f)", doc_id, len(chunks), risk_score)

        except Exception as exc:  # Fail-closed per document
            failed_docs += 1
            logger.error("Failed to ingest document %s (fail-closed skip): %s", doc_id, exc)

    if not all_chunks:
        logger.warning("No chunks generated from documents.")
        return 0

    # 5. Embed and persist to ChromaDB
    active_embedder = embedder or get_embedding_model()
    vectors = active_embedder.embed(all_chunks).tolist()

    store = VectorStore(
        collection_name=collection_name,
        persist_dir=persist_dir,
        embedder=active_embedder,
    )
    store.add(
        chunks=all_chunks,
        embeddings=vectors,
        metadatas=all_metadatas,
        ids=all_ids,
    )

    logger.info(
        "Ingestion completed: %d documents ingested successfully (%d failed), %d chunks stored.",
        successful_docs,
        failed_docs,
        len(all_chunks),
    )
    return len(all_chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count: int = ingest_documents()
    logger.info("Ingested %d chunks", count)
