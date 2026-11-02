"""Local SentenceTransformer embedding model.

All computation happens on-device; no text leaves the machine. The model
is loaded once and cached in a module-level singleton.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Protocol

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.sanitizer import SanitizedText

logger = logging.getLogger(__name__)

_embedding_model: EmbeddingModel | FakeEmbeddingModel | None = None


def _check_sanitized(text: object) -> None:
    if not isinstance(text, SanitizedText):
        raise TypeError(
            f"Expected SanitizedText, got plain {type(text).__name__}. "
            "Redact via src.sanitizer.sanitize() first."
        )


class Embedder(Protocol):
    """Protocol for embedding models."""

    @property
    def dimension(self) -> int: ...

    @property
    def model_name(self) -> str: ...

    def embed(self, texts: list[SanitizedText]) -> NDArray[np.float32]: ...

    def embed_query(self, text: SanitizedText) -> NDArray[np.float32]: ...


class FakeEmbeddingModel:
    """Deterministic fake embedder for tests and CI without loading neural models."""

    def __init__(self, dimension: int = 384) -> None:
        self._dimension: int = dimension

    @property
    def dimension(self) -> int:
        """Vector dimensionality of the fake embedding space."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Model identifier string for fake embedder."""
        return "fake"

    def embed(self, texts: list[SanitizedText]) -> NDArray[np.float32]:
        """Embed a batch of *texts* into deterministic pseudo-vectors."""
        for t in texts:
            _check_sanitized(t)
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        vectors: list[NDArray[np.float32]] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            repeats = (self._dimension // len(h)) + 1
            raw_buf = (h * repeats)[: self._dimension]
            u8 = np.frombuffer(raw_buf, dtype=np.uint8)
            arr = (u8.astype(np.float32) - 128.0) / 128.0
            norm = float(np.linalg.norm(arr))
            if norm > 0:
                arr = arr / norm
            vectors.append(arr)
        return np.array(vectors, dtype=np.float32)  # type: ignore[no-any-return]

    def embed_query(self, text: SanitizedText) -> NDArray[np.float32]:
        """Embed a single *text* query."""
        _check_sanitized(text)
        return self.embed([text])[0]  # type: ignore[no-any-return]


class EmbeddingModel:
    """Thin wrapper around a local SentenceTransformer model."""

    def __init__(self, model_name: str | None = None) -> None:
        """Load the model from *model_name* or the configured default."""
        self._model_name: str = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load and cache the underlying SentenceTransformer."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self._model_name)
            try:
                self._model = SentenceTransformer(self._model_name, local_files_only=True)
            except Exception:
                self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def model_name(self) -> str:
        """Name of the configured embedding model."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Vector dimensionality of the embedding space."""
        if hasattr(self.model, "get_embedding_dimension"):
            dim = self.model.get_embedding_dimension()
        else:
            dim = self.model.get_sentence_embedding_dimension()
        return int(dim) if dim is not None else 0

    def embed(self, texts: list[SanitizedText]) -> NDArray[np.float32]:
        """Embed a batch of *texts* into a 2-D float32 array.

        All input texts must be SanitizedText instances.
        """
        for t in texts:
            _check_sanitized(t)
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        embeddings = self.model.encode(
            [str(t) for t in texts],
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype=np.float32)  # type: ignore[no-any-return]

    def embed_query(self, text: SanitizedText) -> NDArray[np.float32]:
        """Embed a single *text* query into a 1-D float32 array."""
        _check_sanitized(text)
        return self.embed([text])[0]  # type: ignore[no-any-return]


def get_embedding_model() -> EmbeddingModel | FakeEmbeddingModel:
    """Return a module-level cached EmbeddingModel singleton."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


def set_embedding_model(model: EmbeddingModel | FakeEmbeddingModel | None) -> None:
    """Override or reset the module-level embedding model singleton (used in tests)."""
    global _embedding_model
    _embedding_model = model
