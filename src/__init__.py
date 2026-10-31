"""Secure RAG Agent — a portfolio project for privacy-preserving document Q&A.

This package contains the core modules:
- :mod:`src.config`         — environment-based configuration
- :mod:`src.llm`            — single LLM adapter (hosted API / local Ollama)
- :mod:`src.api`            — FastAPI HTTP entrypoint
- :mod:`src.sanitizer`      — PII detection and redaction (Presidio + custom regex)
- :mod:`src.embeddings`     — local SentenceTransformer embeddings
- :mod:`src.rag`            — ingestion, retrieval, and LangGraph agent
- :mod:`src.eval`           — evaluation scripts
- :mod:`src.audit`          — hash-chained audit logging and verification
"""
