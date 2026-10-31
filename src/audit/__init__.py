"""Audit logging package — immutable, hash-chained audit trail.

Each audit record stores:
- ``timestamp``       — ISO-8601 UTC
- ``event_type``      — e.g. ``"sanitize"``, ``"llm_request"``
- ``entity_counts``   — dict mapping entity type → count (never raw PII)
- ``prev_hash``       — SHA-256 of the previous record (hash chain)
- ``record_hash``     — SHA-256 of this record's content

The chain makes any editing, deletion, or reordering detectable via
:func:`src.audit.verify.verify_chain`.
"""
