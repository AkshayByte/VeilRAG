"""LLM adapter — the single exit point for all LLM calls.

The provider is selected via the ``LLM_PROVIDER`` environment variable:

- ``fake`` — deterministic, offline test adapter (default, no network/keys needed).
- ``ollama`` — local Ollama server (default localhost:11434).
- ``anthropic`` — Anthropic Claude API (requires ``ANTHROPIC_API_KEY`` from environment).

**Security invariants:**
1. Callers *must* pass already-redacted text (:class:`src.sanitizer.SanitizedText`).
   Any plain ``str`` passed to ``complete``, ``acomplete``, or ``astream`` raises
   :class:`TypeError`.
2. Full prompts and answers are **never logged** at any logging level. Only tokens, cost,
   model, provider, and duration are recorded in telemetry.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from src.config import settings
from src.sanitizer import SanitizedText

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Container for a single LLM response."""

    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    usage: dict[str, int] | None = None


class LLMAdapter(Protocol):
    """Protocol every concrete adapter must satisfy."""

    def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse: ...

    async def acomplete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse: ...

    def astream(self, prompt: SanitizedText, **kwargs: object) -> AsyncIterator[str]: ...


def _check_sanitized(prompt: object) -> None:
    """Assert that *prompt* has passed through the sanitizer type boundary."""
    if not isinstance(prompt, SanitizedText):
        raise TypeError(
            f"Expected SanitizedText, got plain {type(prompt).__name__}. "
            "Redact via src.sanitizer.sanitize() first."
        )


def _estimate_tokens(text: str) -> int:
    """Rough token estimation based on whitespace and punctuation tokens."""
    return max(1, len(re.findall(r"\w+|[^\w\s]", text)))


class FakeLLMAdapter:
    """Deterministic, offline test adapter for CI and local verification."""

    def __init__(
        self,
        model: str = "fake-model",
        responses: list[str] | None = None,
        custom_handler: Callable[[SanitizedText], str] | None = None,
    ) -> None:
        self.model = model
        self.provider = "fake"
        self.prompts_received: list[SanitizedText] = []
        self.responses: list[str] = list(responses or [])
        self.custom_handler = custom_handler

    def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Synchronous completion with telemetry and safety boundary check."""
        _check_sanitized(prompt)
        t0 = time.perf_counter()
        self.prompts_received.append(prompt)

        # 1. Custom or queued response
        if self.responses:
            response_text = self.responses.pop(0)
        elif self.custom_handler is not None:
            response_text = self.custom_handler(prompt)
        else:
            # 2. Heuristic responses for RAG state machine
            p_str = str(prompt).lower()
            if "you are a document grader" in p_str or "relevant to answering" in p_str:
                if any(w in p_str for w in ("martian", "space pie", "recipe", "secret recipe")):
                    response_text = "no"
                else:
                    response_text = "yes"
            elif "you are a query rewriter" in p_str or "query rewriter" in p_str:
                if any(w in p_str for w in ("martian", "space pie", "recipe", "secret recipe")):
                    response_text = "ingredients and baking recipe for Martian space pie"
                else:
                    response_text = "What is the policy details and terms?"
            elif "you are a factual verification assistant" in p_str or "factual claims" in p_str:
                response_text = "yes"
            elif (
                "you are an assistant answering a question" in p_str
                or "cite the source chunk ids" in p_str
            ):
                if any(w in p_str for w in ("martian", "space pie", "recipe", "secret recipe")):
                    response_text = "I don't know."
                else:
                    chunk_match = re.search(r"\[([a-zA-Z0-9_\-\.]+#chunk_\d+)\]", str(prompt))
                    cid = chunk_match.group(1) if chunk_match else "doc_01#chunk_0"
                    response_text = f"According to [{cid}], the verified details are documented."
            else:
                response_text = "I don't know."

        inp_tokens = _estimate_tokens(prompt)
        out_tokens = _estimate_tokens(response_text)
        cost = 0.0
        duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "LLM call completed: provider=fake model=%s in_tokens=%d out_tokens=%d cost=$%.6f "
            "duration=%.1fms",
            self.model,
            inp_tokens,
            out_tokens,
            cost,
            duration_ms,
        )

        return LLMResponse(
            text=response_text,
            model=self.model,
            provider=self.provider,
            input_tokens=inp_tokens,
            output_tokens=out_tokens,
            cost=cost,
            usage={
                "prompt_tokens": inp_tokens,
                "completion_tokens": out_tokens,
                "total_tokens": inp_tokens + out_tokens,
            },
        )

    async def acomplete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Asynchronous completion."""
        return self.complete(prompt, **kwargs)

    async def astream(self, prompt: SanitizedText, **kwargs: object) -> AsyncIterator[str]:
        """Asynchronous stream."""
        resp = self.complete(prompt, **kwargs)
        yield resp.text


class OllamaAdapter:
    """Adapter for local Ollama server."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.provider = "ollama"

    def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Send completion request to Ollama."""
        _check_sanitized(prompt)
        t0 = time.perf_counter()
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": str(prompt),
            "stream": False,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(endpoint, json=payload)
                res.raise_for_status()
                data = res.json()
        except Exception as exc:
            logger.error("Ollama API request failed: %s", exc)
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        response_text = data.get("response", "")
        inp_tokens = data.get("prompt_eval_count", _estimate_tokens(prompt))
        out_tokens = data.get("eval_count", _estimate_tokens(response_text))
        cost = 0.0
        duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "LLM call completed: provider=ollama model=%s in_tokens=%d out_tokens=%d cost=$%.6f "
            "duration=%.1fms",
            self.model,
            inp_tokens,
            out_tokens,
            cost,
            duration_ms,
        )

        return LLMResponse(
            text=response_text,
            model=self.model,
            provider=self.provider,
            input_tokens=inp_tokens,
            output_tokens=out_tokens,
            cost=cost,
            usage={
                "prompt_tokens": inp_tokens,
                "completion_tokens": out_tokens,
                "total_tokens": inp_tokens + out_tokens,
            },
        )

    async def acomplete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Asynchronous completion for Ollama."""
        _check_sanitized(prompt)
        t0 = time.perf_counter()
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": str(prompt),
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(endpoint, json=payload)
                res.raise_for_status()
                data = res.json()
        except Exception as exc:
            logger.error("Ollama async request failed: %s", exc)
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        response_text = data.get("response", "")
        inp_tokens = data.get("prompt_eval_count", _estimate_tokens(prompt))
        out_tokens = data.get("eval_count", _estimate_tokens(response_text))
        cost = 0.0
        duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "LLM call completed: provider=ollama model=%s in_tokens=%d out_tokens=%d cost=$%.6f "
            "duration=%.1fms",
            self.model,
            inp_tokens,
            out_tokens,
            cost,
            duration_ms,
        )

        return LLMResponse(
            text=response_text,
            model=self.model,
            provider=self.provider,
            input_tokens=inp_tokens,
            output_tokens=out_tokens,
            cost=cost,
            usage={
                "prompt_tokens": inp_tokens,
                "completion_tokens": out_tokens,
                "total_tokens": inp_tokens + out_tokens,
            },
        )

    async def astream(self, prompt: SanitizedText, **kwargs: object) -> AsyncIterator[str]:
        """Stream chunks from Ollama."""
        resp = await self.acomplete(prompt, **kwargs)
        yield resp.text


class AnthropicAdapter:
    """Adapter for Anthropic Claude API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for Anthropic adapter."
            )
        self.api_key: str = key
        self.model = model or settings.llm_model or "claude-3-5-sonnet-20241022"
        self.provider = "anthropic"

    def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Send completion request to Anthropic Messages API."""
        _check_sanitized(prompt)
        t0 = time.perf_counter()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": str(prompt)}],
            "max_tokens": 1024,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                res.raise_for_status()
                data = res.json()
        except Exception as exc:
            logger.error("Anthropic API request failed: %s", exc)
            raise RuntimeError(f"Anthropic request failed: {exc}") from exc

        content_blocks = data.get("content", [])
        response_text = "".join(
            b.get("text", "") for b in content_blocks if b.get("type") == "text"
        )
        usage = data.get("usage", {})
        inp_tokens = usage.get("input_tokens", _estimate_tokens(prompt))
        out_tokens = usage.get("output_tokens", _estimate_tokens(response_text))

        # Standard Anthropic Sonnet 3.5 estimate: $3/M in, $15/M out
        cost = (inp_tokens * 3.0 + out_tokens * 15.0) / 1_000_000.0
        duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "LLM call completed: provider=anthropic model=%s in_tokens=%d out_tokens=%d cost=$%.6f "
            "duration=%.1fms",
            self.model,
            inp_tokens,
            out_tokens,
            cost,
            duration_ms,
        )

        return LLMResponse(
            text=response_text,
            model=self.model,
            provider=self.provider,
            input_tokens=inp_tokens,
            output_tokens=out_tokens,
            cost=cost,
            usage={
                "prompt_tokens": inp_tokens,
                "completion_tokens": out_tokens,
                "total_tokens": inp_tokens + out_tokens,
            },
        )

    async def acomplete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Asynchronous completion for Anthropic."""
        _check_sanitized(prompt)
        t0 = time.perf_counter()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": str(prompt)}],
            "max_tokens": 1024,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                res.raise_for_status()
                data = res.json()
        except Exception as exc:
            logger.error("Anthropic async request failed: %s", exc)
            raise RuntimeError(f"Anthropic request failed: {exc}") from exc

        content_blocks = data.get("content", [])
        response_text = "".join(
            b.get("text", "") for b in content_blocks if b.get("type") == "text"
        )
        usage = data.get("usage", {})
        inp_tokens = usage.get("input_tokens", _estimate_tokens(prompt))
        out_tokens = usage.get("output_tokens", _estimate_tokens(response_text))
        cost = (inp_tokens * 3.0 + out_tokens * 15.0) / 1_000_000.0
        duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "LLM call completed: provider=anthropic model=%s in_tokens=%d out_tokens=%d cost=$%.6f "
            "duration=%.1fms",
            self.model,
            inp_tokens,
            out_tokens,
            cost,
            duration_ms,
        )

        return LLMResponse(
            text=response_text,
            model=self.model,
            provider=self.provider,
            input_tokens=inp_tokens,
            output_tokens=out_tokens,
            cost=cost,
            usage={
                "prompt_tokens": inp_tokens,
                "completion_tokens": out_tokens,
                "total_tokens": inp_tokens + out_tokens,
            },
        )

    async def astream(self, prompt: SanitizedText, **kwargs: object) -> AsyncIterator[str]:
        """Stream chunks from Anthropic."""
        resp = await self.acomplete(prompt, **kwargs)
        yield resp.text


class CachedLLMAdapter:
    """Wrapper that caches completions on disk keyed by SHA-256 of (model + sanitized prompt)."""

    def __init__(self, inner: LLMAdapter, cache_dir: Path | str = "data/cache") -> None:
        self.inner = inner
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = getattr(inner, "model", "cached-model")
        self.provider = getattr(inner, "provider", "cached")
        self.hits = 0
        self.misses = 0

    def _cache_key(self, prompt: SanitizedText) -> str:
        content = f"{self.provider}:{self.model}:{str(prompt)}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Return cached response or delegate to inner adapter and store result."""
        _check_sanitized(prompt)
        key = self._cache_key(prompt)
        cache_file = self.cache_dir / f"{key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                self.hits += 1
                return LLMResponse(
                    text=data["text"],
                    model=data.get("model", self.model),
                    provider=data.get("provider", self.provider),
                    input_tokens=data.get("input_tokens", 0),
                    output_tokens=data.get("output_tokens", 0),
                    cost=data.get("cost", 0.0),
                    usage=data.get("usage"),
                )
            except Exception as e:
                logger.warning("Failed to read cache file %s: %s", cache_file, e)

        # Cache miss
        self.misses += 1
        resp = self.inner.complete(prompt, **kwargs)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "text": resp.text,
                        "model": resp.model,
                        "provider": resp.provider,
                        "input_tokens": resp.input_tokens,
                        "output_tokens": resp.output_tokens,
                        "cost": resp.cost,
                        "usage": resp.usage,
                    },
                    f,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.warning("Failed to write cache file %s: %s", cache_file, e)

        return resp

    async def acomplete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Async completion delegates to sync complete."""
        return self.complete(prompt, **kwargs)

    async def astream(self, prompt: SanitizedText, **kwargs: object) -> AsyncIterator[str]:
        """Stream chunks from cached response."""
        resp = self.complete(prompt, **kwargs)
        yield resp.text


# Module-level default singleton cache for fake adapter in testing
_DEFAULT_FAKE_ADAPTER = FakeLLMAdapter()


def get_adapter(provider: str | None = None) -> LLMAdapter:
    """Return the configured LLM adapter based on ``LLM_PROVIDER`` or parameter."""
    prov = (provider or settings.llm_provider).lower()

    if prov == "fake":
        return _DEFAULT_FAKE_ADAPTER
    elif prov == "ollama":
        return OllamaAdapter()
    elif prov in ("anthropic", "hosted"):
        return AnthropicAdapter()
    else:
        raise ValueError(f"Unknown LLM provider: {prov!r}. Supported: fake, ollama, anthropic")
