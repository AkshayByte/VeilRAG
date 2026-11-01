"""Tests for src/llm.py."""

from __future__ import annotations

import pytest

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


def test_adapter_rejects_plain_str() -> None:
    """LLMAdapter methods raise TypeError if given a plain str instead of SanitizedText."""
    adapter = get_adapter()

    with pytest.raises(TypeError, match="Expected SanitizedText"):
        adapter.complete("plain prompt")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_adapter_async_rejects_plain_str() -> None:
    """Async LLMAdapter methods raise TypeError if given a plain str."""
    adapter = get_adapter()

    with pytest.raises(TypeError, match="Expected SanitizedText"):
        await adapter.acomplete("plain prompt")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="Expected SanitizedText"):
        async for _ in adapter.astream("plain prompt"):  # type: ignore[arg-type]
            pass
