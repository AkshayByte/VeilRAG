"""Tests for src/embeddings/."""

from __future__ import annotations

from src.embeddings import EmbeddingModel, get_embedding_model


def test_embedding_model_construct() -> None:
    """EmbeddingModel can be instantiated."""

    model = EmbeddingModel(model_name="test-model")
    assert model._model_name == "test-model"


def test_get_embedding_model_singleton() -> None:
    """get_embedding_model returns the same instance on repeated calls."""

    # Use a short-lived test by resetting the module-level cache
    import src.embeddings.local as local_mod

    local_mod._embedding_model = None  # reset singleton
    m1 = get_embedding_model()
    m2 = get_embedding_model()
    assert m1 is m2
