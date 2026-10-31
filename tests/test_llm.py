"""Tests for src/llm.py."""

from __future__ import annotations

from src.llm import LLMResponse, get_adapter


def test_llm_response_dataclass() -> None:
    """LLMResponse can be constructed with required fields."""

    resp = LLMResponse(text="hello", model="test", provider="test")
    assert resp.text == "hello"
    assert resp.model == "test"
    assert resp.provider == "test"


def test_get_adapter_returns_instance() -> None:
    """get_adapter returns an object implementing the LLMAdapter protocol."""

    adapter = get_adapter()
    assert adapter is not None
    assert hasattr(adapter, "complete")
