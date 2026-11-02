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

    llm_provider: str = "fake"
    """Which LLM backend to use: ``fake``, ``ollama``, or ``anthropic``."""

    openai_api_base: str | None = None
    """Base URL for an OpenAI-compatible API (used when ``llm_provider=hosted``)."""

    openai_api_key: str | None = None
    """API key for a hosted LLM provider (used when ``llm_provider=hosted``)."""

    anthropic_api_key: str | None = None
    """API key for Anthropic provider (used when ``llm_provider=anthropic``)."""

    llm_model: str = "gpt-4o-mini"
    """Model name / identifier."""

    ollama_base_url: str = "http://localhost:11434"
    """URL of the local Ollama server (also readable as OLLAMA_HOST)."""

    ollama_host: str = "http://localhost:11434"
    """Alias for ollama_base_url; takes precedence if set explicitly."""

    ollama_model: str = "gemma3:4b"
    """Default Ollama model name."""

    ollama_judge_model: str | None = None
    """Ollama model used for faithfulness judging; defaults to ollama_model when None."""

    ollama_num_ctx: int = 8192
    """Ollama context window size in tokens."""

    ollama_seed: int = 42
    """Fixed random seed for deterministic Ollama outputs (temperature is always 0)."""

    ollama_timeout_s: int = 300
    """HTTP timeout for Ollama requests in seconds."""

    ollama_num_predict_short: int = 64
    """max_tokens for short Ollama responses (grading, verification)."""

    ollama_num_predict_answer: int = 400
    """max_tokens for answer-generation Ollama responses."""

    chroma_persist_dir: str = "data/chroma"
    """Directory where ChromaDB persists its index."""

    api_host: str = "0.0.0.0"
    """Host interface for the FastAPI server."""

    api_port: int = 8000
    """Port for the FastAPI server."""

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    """SentenceTransformer model used for local embeddings."""

    chunk_size_tokens: int = 300
    """Target chunk size in tokens for document ingestion."""

    chunk_overlap_tokens: int = 60
    """Overlap between adjacent chunks in tokens."""

    spacy_model: str = "en_core_web_lg"
    """spaCy model used for Presidio NLP engine and entity recognition."""

    pipeline_mode: str = "full"
    """Central sanitization mode used across ingestion, query, and guards."""


CHUNK_SIZE_TOKENS: int = 300
"""Target chunk size in tokens; 300 tokens preserves clause coherence within budgets."""

CHUNK_OVERLAP_TOKENS: int = 60
"""Overlap in tokens (20%) ensuring cross-boundary facts and entities are not truncated."""

PIPELINE_MODE: str = "full"
"""Central sanitization mode constant for ingestion, query path, rewriting, and guards."""

settings: Settings = Settings()
"""Module-level singleton — import as ``from src.config import settings``."""
