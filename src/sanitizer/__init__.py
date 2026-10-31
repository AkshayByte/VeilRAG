"""PII sanitization package — Presidio + custom regex + spaCy NER.

Public API
----------
- :func:`sanitize`           — redact PII from text, returning a :class:`SanitizeResult`
- :class:`SanitizeResult`     — dataclass holding the redacted text and entity spans
- :class:`SanitizationError`  — raised when sanitization fails

Redaction style is fixed: typed numbered placeholders, e.g. ``[PERSON_1]``,
``[EMAIL_ADDRESS_1]`` — numbering is consistent within a single document.
"""

from src.sanitizer.sanitize import SanitizationError, SanitizeResult, sanitize

__all__ = ["SanitizationError", "SanitizeResult", "sanitize"]
