"""FastAPI HTTP entrypoint for the VeilRAG.

Exposes a single ``POST /query`` endpoint that accepts a user question,
sanitizes it, retrieves relevant documents, and returns the LLM answer.

Security note: raw user text is sanitized *before* it reaches the LLM
adapter, and only redacted entity types and counts are written to the
audit log.
"""

from __future__ import annotations

from fastapi import FastAPI

app: FastAPI = FastAPI(title="VeilRAG", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""

    return {"status": "ok"}


@app.post("/query")
async def query(question: str) -> dict[str, str]:
    """Answer a question using the VeilRAG pipeline.

    Parameters
    ----------
    question
        The user's raw (possibly PII-containing) question.  It will be
        sanitized before being sent to any external service.
    """

    raise NotImplementedError
