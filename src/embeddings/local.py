"""Local SentenceTransformer embedding model.

All computation happens on-device; no text leaves the machine.  The model
is loaded once and cached in a module-level singleton.
"""

from __future__ import annotations

import logging

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from src.config import settings

logger = logging.getLogger(__name__)

_embedding_model: EmbeddingModel | None = None


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
            self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def dimension(self) -> int:
        """Vector dimensionality of the embedding space."""

        dim = self.model.get_sentence_embedding_dimension()
        return int(dim) if dim is not None else 0

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Embed a batch of *texts* into a 2-D float32 array."""

        raise NotImplementedError


def get_embedding_model() -> EmbeddingModel:
    """Return a module-level cached EmbeddingModel singleton."""

    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model
