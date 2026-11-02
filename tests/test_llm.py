"""Tests for src/llm.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.llm import CachedLLMAdapter, FakeLLMAdapter, LLMResponse, OllamaAdapter, get_adapter
from src.sanitizer import SanitizedText, sanitize


def _make_sanitized(text: str = "What is the interest rate?") -> SanitizedText:
    """Return a SanitizedText instance for use in tests."""
    return sanitize(text, mode="full").safe


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


# ─────────────────────────────────────────────────────────────────────────────
# Ollama adapter tests (all HTTP calls mocked — no Ollama server required)
# ─────────────────────────────────────────────────────────────────────────────


def _mock_ollama_response(
    response_text: str = "answer",
    prompt_eval_count: int = 10,
    eval_count: int = 5,
    num_ctx: int = 8192,
) -> Any:
    """Build a mock httpx response simulating Ollama /api/generate."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "response": response_text,
        "prompt_eval_count": prompt_eval_count,
        "eval_count": eval_count,
    }
    # Store num_ctx for overflow tests
    mock_resp._num_ctx = num_ctx
    return mock_resp


def test_ollama_context_overflow_raises() -> None:
    """OllamaAdapter raises RuntimeError when prompt_eval_count >= num_ctx."""
    adapter = OllamaAdapter(num_ctx=100)
    prompt = _make_sanitized()

    overflow_data = {
        "response": "truncated answer",
        "prompt_eval_count": 100,  # >= num_ctx=100
        "eval_count": 5,
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = overflow_data
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp

    with patch("src.llm.httpx.Client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="context overflow"):
            adapter.complete(prompt)


def test_ollama_strips_think_blocks() -> None:
    """OllamaAdapter strips <think>…</think> blocks from the response text."""
    adapter = OllamaAdapter()
    prompt = _make_sanitized()

    think_data = {
        "response": "<think>internal reasoning here</think>The actual answer.",
        "prompt_eval_count": 10,
        "eval_count": 8,
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = think_data
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp

    with patch("src.llm.httpx.Client", return_value=mock_client):
        resp = adapter.complete(prompt)

    assert "<think>" not in resp.text
    assert "internal reasoning here" not in resp.text
    assert "The actual answer." in resp.text


def test_ollama_strips_think_static() -> None:
    """OllamaAdapter._strip_think removes all think blocks regardless of nesting."""
    stripped = OllamaAdapter._strip_think("<think>foo</think>bar<think>baz</think>")
    assert stripped == "bar"
    # No think block: text returned as-is (stripped)
    assert OllamaAdapter._strip_think("  plain text  ") == "plain text"


def test_ollama_cache_key_includes_seed_num_ctx_num_predict(tmp_path: Path) -> None:
    """CachedLLMAdapter cache key changes when seed, num_ctx, or num_predict changes."""
    inner = FakeLLMAdapter()
    inner.seed = 42  # type: ignore[attr-defined]
    inner.num_ctx = 8192  # type: ignore[attr-defined]
    inner.num_predict_answer = 400  # type: ignore[attr-defined]
    cached = CachedLLMAdapter(inner, cache_dir=tmp_path)
    p = _make_sanitized()

    base_key = cached._cache_key(p, temperature=0.0, seed=42, num_ctx=8192, num_predict=400)
    key_diff_seed = cached._cache_key(p, temperature=0.0, seed=99, num_ctx=8192, num_predict=400)
    key_diff_ctx = cached._cache_key(p, temperature=0.0, seed=42, num_ctx=4096, num_predict=400)
    key_diff_pred = cached._cache_key(p, temperature=0.0, seed=42, num_ctx=8192, num_predict=64)

    assert base_key != key_diff_seed, "seed change must change cache key"
    assert base_key != key_diff_ctx, "num_ctx change must change cache key"
    assert base_key != key_diff_pred, "num_predict change must change cache key"


def test_ollama_never_caches_empty_reply(tmp_path: Path) -> None:
    """CachedLLMAdapter must not write a cache file when the response is empty."""
    inner = FakeLLMAdapter(responses=[""])  # empty string response
    cached = CachedLLMAdapter(inner, cache_dir=tmp_path)
    p = _make_sanitized()

    resp = cached.complete(p)
    assert resp.text == ""
    # No cache files should exist
    assert list(tmp_path.glob("*.json")) == [], "empty response must not be cached"


def test_ollama_never_caches_error(tmp_path: Path) -> None:
    """CachedLLMAdapter must not write a cache file when the adapter raises."""

    class ErrorAdapter:
        model = "error-model"
        provider = "error"

        def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
            """Always raises to simulate a transient failure."""
            raise RuntimeError("Simulated adapter error")

        async def acomplete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
            """Async version always raises."""
            raise RuntimeError("Simulated adapter error")

        def astream(self, prompt: SanitizedText, **kwargs: object) -> Any:
            """Streaming version always raises."""
            raise NotImplementedError

    cached = CachedLLMAdapter(ErrorAdapter(), cache_dir=tmp_path)  # type: ignore[arg-type]
    p = _make_sanitized()

    with pytest.raises(RuntimeError, match="Simulated adapter error"):
        cached.complete(p)

    assert list(tmp_path.glob("*.json")) == [], "error response must not be cached"


def test_ollama_rerun_makes_zero_calls(tmp_path: Path) -> None:
    """Second run with same prompt/params makes zero HTTP calls (cache hit)."""
    inner = FakeLLMAdapter(responses=["First real call"])
    cached = CachedLLMAdapter(inner, cache_dir=tmp_path)
    p = _make_sanitized()

    # First call: miss — writes cache
    r1 = cached.complete(p)
    assert r1.text == "First real call"
    assert cached.misses == 1
    assert cached.hits == 0

    # Second call: hit — inner adapter must NOT be called again
    r2 = cached.complete(p)
    assert r2.text == "First real call"
    assert cached.misses == 1
    assert cached.hits == 1
    # inner.responses is exhausted; if inner were called it would return "I don't know."
    assert len(inner.responses) == 0, "inner adapter was called again (should not happen)"


def test_ollama_options_sent_in_payload() -> None:
    """OllamaAdapter sends temperature=0, seed, num_ctx, and num_predict in options."""
    adapter = OllamaAdapter(num_ctx=512, seed=7, num_predict_answer=200)
    prompt = _make_sanitized()

    ok_data = {"response": "ok", "prompt_eval_count": 5, "eval_count": 3}
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = ok_data
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp

    captured_payload: list[dict[str, Any]] = []

    def fake_post(url: str, json: dict[str, Any], **kw: object) -> Any:
        captured_payload.append(json)
        return mock_resp

    mock_client.post = fake_post

    with patch("src.llm.httpx.Client", return_value=mock_client):
        adapter.complete(prompt)

    assert len(captured_payload) == 1
    opts = captured_payload[0].get("options", {})
    assert opts["temperature"] == 0
    assert opts["seed"] == 7
    assert opts["num_ctx"] == 512
    assert opts["num_predict"] == 200


def test_ollama_adapter_rejects_plain_str() -> None:
    """OllamaAdapter.complete raises TypeError for a plain str (no HTTP call)."""
    adapter = OllamaAdapter()
    with pytest.raises(TypeError, match="Expected SanitizedText"):
        adapter.complete("raw string")  # type: ignore[arg-type]


def test_get_adapter_ollama_returns_ollama_adapter() -> None:
    """get_adapter('ollama') returns an OllamaAdapter instance."""
    adapter = get_adapter(provider="ollama")
    assert isinstance(adapter, OllamaAdapter)


def test_get_adapter_ollama_with_model_override() -> None:
    """get_adapter('ollama', model='gemma3:4b') passes the model through."""
    adapter = get_adapter(provider="ollama", model="gemma3:4b")
    assert isinstance(adapter, OllamaAdapter)
    assert adapter.model == "gemma3:4b"

