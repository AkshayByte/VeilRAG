"""Tests for src/config.py."""

from __future__ import annotations

from src.config import Settings, settings


def test_settings_singleton() -> None:
    """Settings singleton is instantiated with defaults."""

    assert isinstance(settings, Settings)
    assert settings.llm_provider in ("fake", "hosted", "ollama", "anthropic")
