"""Local embedding package — SentenceTransformer models run entirely on-device.

No text or embeddings are sent to any external service. Models are cached
locally under ``~/.cache/huggingface`` by default.
"""

from src.embeddings.local import (
    Embedder,
    EmbeddingModel,
    FakeEmbeddingModel,
    get_embedding_model,
    set_embedding_model,
)

__all__ = [
    "Embedder",
    "EmbeddingModel",
    "FakeEmbeddingModel",
    "get_embedding_model",
    "set_embedding_model",
]
