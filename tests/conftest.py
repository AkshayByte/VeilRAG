"""Shared pytest fixtures for secure-rag-agent tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_text() -> str:
    """Return a synthetic text string with a person name and email."""

    return "Alice Smith can be reached at alice@example.com."


@pytest.fixture
def sample_text_with_pii() -> str:
    """Return a synthetic text string containing multiple PII types."""

    return (
        "John Doe's phone is 555-1234 and email is john@example.com. "
        "His Aadhaar is 1234 5678 9012."
    )
