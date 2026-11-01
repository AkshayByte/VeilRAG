"""Application configuration loaded from environment variables.

Uses Pydantic ``BaseSettings`` so every setting has a type, a default, and
clear documentation.  Settings are read from the environment or a ``.env``
file at runtime.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_provider: str = "ollama"
    """Which LLM backend to use: ``hosted`` or ``ollama``."""

    openai_api_base: str | None = None
    """Base URL for an OpenAI-compatible API (used when ``llm_provider=hosted``)."""

    openai_api_key: str | None = None
    """API key for a hosted LLM provider (used when ``llm_provider=hosted``)."""

    llm_model: str = "gpt-4o-mini"
    """Model name / identifier."""

    ollama_base_url: str = "http://localhost:11434"
    """URL of the local Ollama server."""

    ollama_model: str = "llama3"
    """Default Ollama model name."""

    chroma_persist_dir: str = "data/chroma"
    """Directory where ChromaDB persists its index."""

    api_host: str = "0.0.0.0"
    """Host interface for the FastAPI server."""

    api_port: int = 8000
    """Port for the FastAPI server."""

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    """SentenceTransformer model used for local embeddings."""

    chunk_size_tokens: int = 500
    """Target chunk size in tokens for document ingestion."""

    chunk_overlap_tokens: int = 100
    """Overlap between adjacent chunks in tokens."""

    spacy_model: str = "en_core_web_lg"
    """spaCy model used for Presidio NLP engine and entity recognition."""


settings: Settings = Settings()
"""Module-level singleton — import as ``from src.config import settings``."""
