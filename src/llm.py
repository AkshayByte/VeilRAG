"""LLM adapter — the single exit point for all LLM calls.

The provider is selected via the ``LLM_PROVIDER`` environment variable:

- ``hosted`` — OpenAI-compatible REST API (requires ``OPENAI_API_KEY``).
- ``ollama`` — local Ollama server (default).

**Security invariant:** callers *must* pass already-redacted text.
The adapter does not perform any redaction itself; it relies on the
caller having called :func:`src.sanitizer.sanitize` first.  Violations can be
detected in tests via :func:`tests.test_agent.test_no_unredacted_text_to_llm`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Container for a single LLM response."""

    text: str
    model: str
    provider: str
    usage: dict[str, int] | None = None


class LLMAdapter(Protocol):
    """Protocol every concrete adapter must satisfy."""

    async def acomplete(self, prompt: str, **kwargs: object) -> LLMResponse: ...

    async def astream(self, prompt: str, **kwargs: object) -> AsyncIterator[str]: ...

    def complete(self, prompt: str, **kwargs: object) -> LLMResponse: ...


def get_adapter() -> LLMAdapter:
    """Return the configured LLM adapter based on ``LLM_PROVIDER``."""

    if settings.llm_provider == "hosted":
        from src.llm import _HostAdapter  # imported lazily to avoid hard dep

        return _HostAdapter()
    else:
        from src.llm import _OllamaAdapter  # imported lazily

        return _OllamaAdapter()


class _HostAdapter:
    """Adapter for OpenAI-compatible hosted APIs."""

    async def acomplete(self, prompt: str, **kwargs: object) -> LLMResponse:
        raise NotImplementedError

    async def astream(self, prompt: str, **kwargs: object) -> AsyncIterator[str]:
        raise NotImplementedError

    def complete(self, prompt: str, **kwargs: object) -> LLMResponse:
        raise NotImplementedError


class _OllamaAdapter:
    """Adapter for local Ollama server."""

    async def acomplete(self, prompt: str, **kwargs: object) -> LLMResponse:
        raise NotImplementedError

    async def astream(self, prompt: str, **kwargs: object) -> AsyncIterator[str]:
        raise NotImplementedError

    def complete(self, prompt: str, **kwargs: object) -> LLMResponse:
        raise NotImplementedError
