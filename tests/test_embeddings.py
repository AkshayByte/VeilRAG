"""Tests for src/embeddings/."""

from __future__ import annotations

import pytest

from src.embeddings import (
    EmbeddingModel,
    FakeEmbeddingModel,
    get_embedding_model,
    set_embedding_model,
)
from src.sanitizer import sanitize


def test_embedding_model_construct() -> None:
    """EmbeddingModel can be instantiated."""
    model = EmbeddingModel(model_name="test-model")
    assert model._model_name == "test-model"


def test_get_embedding_model_singleton() -> None:
    """get_embedding_model returns the same instance on repeated calls."""
    set_embedding_model(None)
    m1 = get_embedding_model()
    m2 = get_embedding_model()
    assert m1 is m2
    set_embedding_model(None)


def test_fake_embedding_model_deterministic() -> None:
    """FakeEmbeddingModel produces deterministic unit-norm vectors."""
    fake = FakeEmbeddingModel(dimension=64)
    res = sanitize("Sample safe text")
    v1 = fake.embed([res.safe])
    v2 = fake.embed([res.safe])
    assert v1.shape == (1, 64)
    assert (v1 == v2).all()
    q = fake.embed_query(res.safe)
    assert q.shape == (64,)
    assert (q == v1[0]).all()


def test_embedding_models_reject_plain_str() -> None:
    """Embedding models raise TypeError when passed a plain str."""
    fake = FakeEmbeddingModel(dimension=64)
    with pytest.raises(TypeError, match="Expected SanitizedText"):
        fake.embed(["plain string"])  # type: ignore[list-item]

    with pytest.raises(TypeError, match="Expected SanitizedText"):
        fake.embed_query("plain string")  # type: ignore[arg-type]

    real = EmbeddingModel(model_name="sentence-transformers/all-MiniLM-L6-v2")
    with pytest.raises(TypeError, match="Expected SanitizedText"):
        real.embed(["plain string"])  # type: ignore[list-item]

    with pytest.raises(TypeError, match="Expected SanitizedText"):
        real.embed_query("plain string")  # type: ignore[arg-type]


@pytest.mark.slow
def test_real_embedding_model() -> None:
    """Real SentenceTransformer model loads and computes valid embeddings."""
    res = sanitize("Sanitized text for local vector encoding")
    model = EmbeddingModel()
    vecs = model.embed([res.safe])
    assert vecs.shape[0] == 1
    assert vecs.shape[1] == model.dimension
    assert model.dimension == 384
