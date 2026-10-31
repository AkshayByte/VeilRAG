"""Structured audit log writer.

Writes JSONL records where each record contains a hash of the previous
record, forming an immutable hash chain.  Only entity *types* and *counts*
are logged — never raw PII values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """A single audit record."""

    timestamp: str
    event_type: str
    entity_counts: dict[str, int] = field(default_factory=dict)
    prev_hash: str = ""
    record_hash: str = ""


class AuditLogger:
    """Append-only, hash-chained audit logger."""

    def __init__(self, path: str = "data/audit/audit.log.jsonl") -> None:
        self._path: str = path
        self._prev_hash: str = ""

    def log_sanitize(self, entity_counts: dict[str, int]) -> AuditRecord:
        """Log a sanitization event with entity type counts."""

        raise NotImplementedError

    def log_llm_request(self, event_type: str = "llm_request") -> AuditRecord:
        """Log that a request was sent to the LLM adapter."""

        raise NotImplementedError

    def close(self) -> None:
        """Flush any buffered records."""

        raise NotImplementedError
