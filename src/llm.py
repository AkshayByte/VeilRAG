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
    """Adapter for a local Ollama server.

    Sends every request with deterministic options (temperature=0, fixed seed,
    num_ctx, num_predict).  Raises ``RuntimeError`` if the server truncates the
    prompt (``prompt_eval_count >= num_ctx``).  Strips ``<think>…</think>``
    blocks from the response before returning.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        num_ctx: int | None = None,
        seed: int | None = None,
        timeout_s: int | None = None,
        num_predict_short: int | None = None,
        num_predict_answer: int | None = None,
    ) -> None:
        """Initialise the adapter, reading defaults from :data:`src.config.settings`."""
        # Prefer OLLAMA_HOST over OLLAMA_BASE_URL when both are set
        cfg_url = settings.ollama_host or settings.ollama_base_url
        self.base_url = (base_url or cfg_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.provider = "ollama"
        self.num_ctx = num_ctx if num_ctx is not None else settings.ollama_num_ctx
        self.seed = seed if seed is not None else settings.ollama_seed
        self.timeout_s = timeout_s if timeout_s is not None else settings.ollama_timeout_s
        self.num_predict_short = (
            num_predict_short
            if num_predict_short is not None
            else settings.ollama_num_predict_short
        )
        self.num_predict_answer = (
            num_predict_answer
            if num_predict_answer is not None
            else settings.ollama_num_predict_answer
        )
        self._model_digest: str | None = None

    @staticmethod
    def _strip_think(text: str) -> str:
        """Remove ``<think>…</think>`` blocks emitted by reasoning models."""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    def get_model_digest(self) -> str:
        """Fetch and cache the model digest from the Ollama /api/show endpoint."""
        if self._model_digest is not None:
            return self._model_digest
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    f"{self.base_url}/api/show",
                    json={"model": self.model},
                )
                res.raise_for_status()
                data = res.json()
            self._model_digest = data.get("digest", "unknown")
        except Exception:
            self._model_digest = "unknown"
        return self._model_digest  # type: ignore[return-value]

    def get_server_version(self) -> str:
        """Fetch the Ollama server version string from /api/version."""
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{self.base_url}/api/version")
                res.raise_for_status()
                return str(res.json().get("version", "unknown"))
        except Exception:
            return "unknown"

    def _build_payload(self, prompt: SanitizedText, num_predict: int) -> dict[str, object]:
        """Assemble the Ollama /api/generate request body."""
        return {
            "model": self.model,
            "prompt": str(prompt),
            "stream": False,
            "options": {
                "temperature": 0,
                "seed": self.seed,
                "num_ctx": self.num_ctx,
                "num_predict": num_predict,
            },
        }

    def _parse_response(
        self, data: dict[str, object], prompt: SanitizedText
    ) -> tuple[str, int, int]:
        """Extract (text, in_tokens, out_tokens) from an Ollama response dict.

        Raises
        ------
        RuntimeError
            If ``prompt_eval_count >= num_ctx`` (silent truncation guard).
        """
        raw_eval_in = data.get("prompt_eval_count", 0)
        try:
            inp_tokens = int(str(raw_eval_in))
        except (ValueError, TypeError):
            inp_tokens = _estimate_tokens(prompt)
        if inp_tokens <= 0:
            inp_tokens = _estimate_tokens(prompt)

        raw_eval_out = data.get("eval_count", 0)
        raw_text = str(data.get("response", ""))
        try:
            out_tokens = int(str(raw_eval_out))
        except (ValueError, TypeError):
            out_tokens = _estimate_tokens(raw_text)
        if out_tokens <= 0:
            out_tokens = _estimate_tokens(raw_text)

        if inp_tokens >= self.num_ctx:
            raise RuntimeError(
                f"Ollama context overflow: prompt_eval_count={inp_tokens} >= "
                f"num_ctx={self.num_ctx}. Reduce prompt length or increase OLLAMA_NUM_CTX."
            )
        text = self._strip_think(raw_text)
        return text, inp_tokens, out_tokens

    def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Send a synchronous completion request to the Ollama server.

        Parameters
        ----------
        prompt:
            Already-redacted text.  Raises :class:`TypeError` for plain ``str``.
        kwargs:
            Optional overrides such as ``num_predict``; defaults to ``num_predict_answer``.
        """
        _check_sanitized(prompt)
        raw_n_pred = kwargs.get("num_predict")
        try:
            n_pred = int(str(raw_n_pred)) if raw_n_pred is not None else self.num_predict_answer
        except (ValueError, TypeError):
            n_pred = self.num_predict_answer

        t0 = time.perf_counter()
        payload = self._build_payload(prompt, n_pred)

        try:
            with httpx.Client(timeout=float(self.timeout_s)) as client:
                res = client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data: dict[str, object] = res.json()
        except Exception as exc:
            logger.error("Ollama API request failed: %s", exc)
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        text, inp_tokens, out_tokens = self._parse_response(data, prompt)
        duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "LLM call completed: provider=ollama model=%s in_tokens=%d out_tokens=%d "
            "cost=$0 duration=%.1fms",
            self.model,
            inp_tokens,
            out_tokens,
            duration_ms,
        )

        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.provider,
            input_tokens=inp_tokens,
            output_tokens=out_tokens,
            cost=0.0,
            usage={
                "prompt_tokens": inp_tokens,
                "completion_tokens": out_tokens,
                "total_tokens": inp_tokens + out_tokens,
            },
        )

    async def acomplete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Asynchronous completion for Ollama.

        Parameters
        ----------
        prompt:
            Already-redacted text.  Raises :class:`TypeError` for plain ``str``.
        kwargs:
            Optional overrides such as ``num_predict``; defaults to ``num_predict_answer``.
        """
        _check_sanitized(prompt)
        raw_n_pred = kwargs.get("num_predict")
        try:
            n_pred = int(str(raw_n_pred)) if raw_n_pred is not None else self.num_predict_answer
        except (ValueError, TypeError):
            n_pred = self.num_predict_answer

        t0 = time.perf_counter()
        payload = self._build_payload(prompt, n_pred)

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_s)) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data_a: dict[str, object] = res.json()
        except Exception as exc:
            logger.error("Ollama async request failed: %s", exc)
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        text, inp_tokens, out_tokens = self._parse_response(data_a, prompt)
        duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "LLM call completed: provider=ollama model=%s in_tokens=%d out_tokens=%d "
            "cost=$0 duration=%.1fms",
            self.model,
            inp_tokens,
            out_tokens,
            duration_ms,
        )

        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.provider,
            input_tokens=inp_tokens,
            output_tokens=out_tokens,
            cost=0.0,
            usage={
                "prompt_tokens": inp_tokens,
                "completion_tokens": out_tokens,
                "total_tokens": inp_tokens + out_tokens,
            },
        )

    async def astream(self, prompt: SanitizedText, **kwargs: object) -> AsyncIterator[str]:
        """Stream chunks from Ollama (delegates to acomplete for simplicity)."""
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
    """Wrapper that caches completions on disk keyed by SHA-256 of
    (provider + model + temperature + seed + num_ctx + num_predict + prompt).

    Responses are never cached when the inner adapter raises an exception or
    returns an empty string.
    """

    def __init__(self, inner: LLMAdapter, cache_dir: Path | str = "data/cache") -> None:
        """Initialise the cache wrapper around *inner* adapter."""
        self.inner = inner
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = getattr(inner, "model", "cached-model")
        self.provider = getattr(inner, "provider", "cached")
        self.hits = 0
        self.misses = 0
        self.bypass_cache = False

    def _cache_key(
        self,
        prompt: SanitizedText,
        temperature: float = 0.0,
        seed: int | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
    ) -> str:
        """SHA-256 of (provider:model:temperature:seed:num_ctx:num_predict:prompt).

        For non-Ollama adapters the extra fields default to sentinel strings so
        the key still differs from Ollama keys even with an identical prompt.
        """
        _seed = seed if seed is not None else getattr(self.inner, "seed", "none")
        _num_ctx = num_ctx if num_ctx is not None else getattr(self.inner, "num_ctx", "none")
        _num_predict = (
            num_predict
            if num_predict is not None
            else getattr(self.inner, "num_predict_answer", "none")
        )
        content = (
            f"{self.provider}:{self.model}:{temperature}:"
            f"{_seed}:{_num_ctx}:{_num_predict}:{str(prompt)}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def complete(self, prompt: SanitizedText, **kwargs: object) -> LLMResponse:
        """Return cached response or delegate to inner adapter and store result.

        Empty responses and adapter errors are never persisted to disk.
        """
        _check_sanitized(prompt)
        raw_temp = kwargs.get("temperature", getattr(self.inner, "temperature", 0.0))
        try:
            temp_val = float(raw_temp)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            temp_val = 0.0

        raw_seed = kwargs.get("seed", getattr(self.inner, "seed", None))
        raw_num_ctx = kwargs.get("num_ctx", getattr(self.inner, "num_ctx", None))
        raw_num_predict = kwargs.get(
            "num_predict", getattr(self.inner, "num_predict_answer", None)
        )

        try:
            seed_val: int | None = int(str(raw_seed)) if raw_seed is not None else None
        except (ValueError, TypeError):
            seed_val = None
        try:
            num_ctx_val: int | None = (
                int(str(raw_num_ctx)) if raw_num_ctx is not None else None
            )
        except (ValueError, TypeError):
            num_ctx_val = None
        try:
            num_pred_val: int | None = (
                int(str(raw_num_predict)) if raw_num_predict is not None else None
            )
        except (ValueError, TypeError):
            num_pred_val = None

        key = self._cache_key(
            prompt,
            temperature=temp_val,
            seed=seed_val,
            num_ctx=num_ctx_val,
            num_predict=num_pred_val,
        )
        cache_file = self.cache_dir / f"{key}.json"

        if not self.bypass_cache and cache_file.exists():
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

        # Only cache successful, non-empty responses
        if resp.text.strip():
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "text": resp.text,
                            "model": resp.model,
                            "provider": resp.provider,
                            "temperature": temp_val,
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


def get_adapter(provider: str | None = None, model: str | None = None) -> LLMAdapter:
    """Return the configured LLM adapter based on ``LLM_PROVIDER`` or parameter.

    Parameters
    ----------
    provider:
        Override the provider; if ``None`` reads ``settings.llm_provider``.
    model:
        Optional model name override passed to the constructed adapter.
    """
    prov = (provider or settings.llm_provider).lower()

    if prov == "fake":
        return _DEFAULT_FAKE_ADAPTER
    elif prov == "ollama":
        return OllamaAdapter(model=model)
    elif prov in ("anthropic", "hosted"):
        return AnthropicAdapter(model=model)
    else:
        raise ValueError(f"Unknown LLM provider: {prov!r}. Supported: fake, ollama, anthropic")
