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


def test_fake_adapter_tracks_prompts_and_tokens() -> None:
    """FakeLLMAdapter records prompts received, token usage, and cost."""
    from src.llm import FakeLLMAdapter
    from src.sanitizer import sanitize

    adapter = FakeLLMAdapter()
    res = sanitize("What is the interest rate?", mode="full")
    resp = adapter.complete(res.safe)

    assert len(adapter.prompts_received) == 1
    assert adapter.prompts_received[0] == res.safe
    assert resp.input_tokens > 0
    assert resp.output_tokens > 0
    assert resp.cost == 0.0
    assert resp.provider == "fake"


def test_anthropic_adapter_missing_key_raises() -> None:
    """AnthropicAdapter raises ValueError when ANTHROPIC_API_KEY is missing."""
    from src.llm import AnthropicAdapter

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicAdapter(api_key="")


def test_get_adapter_unknown_provider_raises() -> None:
    """get_adapter raises ValueError for unrecognized provider strings."""
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_adapter(provider="unsupported_provider")
