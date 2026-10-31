"""Local embedding package — SentenceTransformer models run entirely on-device.

No text or embeddings are sent to any external service.  Models are cached
locally under ``~/.cache/huggingface`` by default.
"""

from src.embeddings.local import EmbeddingModel, get_embedding_model

__all__ = ["EmbeddingModel", "get_embedding_model"]
