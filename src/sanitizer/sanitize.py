"""Core sanitization logic — Presidio Analyzer + custom regex + Verhoeff Aadhaar.

The :func:`sanitize` function is the public entry point.  It:

1. Loads the appropriate context mode from ``modes.yaml``.
2. Runs Presidio Analyzer with built-in + custom recognizers.
3. Runs custom regex detectors from :mod:`src.sanitizer.detectors`.
4. Deduplicates overlapping spans and keeps the highest-confidence match.
5. Replaces each PII span with a typed numbered placeholder such as
   ``[PERSON_1]`` or ``[AADHAAR_1]`` — the same original text always maps to
   the same placeholder within a single document.
6. Returns a :class:`SanitizeResult` containing the redacted text, entity
   spans (type / start / end / score — never raw values), a 0–1 risk score,
   and the mode used.

**No redacted or unredacted text leaves this module.**  A reversible
placeholder→original map is kept only for the duration of the call and is
never persisted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from src.config import settings
from src.sanitizer.detectors import DEFAULT_DETECTORS, RegexMatch
from src.sanitizer.recognizers.custom import get_custom_recognizers

logger = logging.getLogger(__name__)
# Suppress noisy Presidio mapping and language warnings
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)

_MODES_PATH = Path(__file__).parent / "modes.yaml"
_ANALYZER_CACHE: AnalyzerEngine | None = None


def _get_analyzer() -> AnalyzerEngine:
    """Return the cached Presidio AnalyzerEngine configured with the spaCy model from config."""
    global _ANALYZER_CACHE
    if _ANALYZER_CACHE is None:
        nlp_config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": settings.spacy_model}],
        }
        provider = NlpEngineProvider(nlp_configuration=nlp_config)
        nlp_engine = provider.create_engine()
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        for recognizer in get_custom_recognizers():
            analyzer.registry.add_recognizer(recognizer)
        _ANALYZER_CACHE = analyzer
    return _ANALYZER_CACHE

_PLACEHOLDER_PREFIXES: dict[str, str] = {
    "IDENTITY_DOCUMENT": "AADHAAR",
    "AADHAAR": "AADHAAR",
    "PAN_NUMBER": "PAN",
    "PAN": "PAN",
    "UPI_ID": "UPI",
    "UPI": "UPI",
    "IFSC_CODE": "IFSC",
    "IFSC": "IFSC",
    "PHONE_NUMBER": "PHONE",
    "INDIAN_MOBILE": "PHONE",
}

_SENSITIVITY_WEIGHTS: dict[str, float] = {
    "US_SSN": 0.30,
    "CREDIT_CARD": 0.30,
    "IDENTITY_DOCUMENT": 0.30,
    "AWS_ACCESS_KEY": 0.30,
    "AWS_SECRET_KEY": 0.30,
    "SECRET_KEY": 0.25,
    "API_KEY": 0.25,
    "PAN_NUMBER": 0.20,
    "IFSC_CODE": 0.20,
    "IBAN_CODE": 0.20,
    "UPI_ID": 0.20,
    "EMAIL_ADDRESS": 0.15,
    "PHONE_NUMBER": 0.15,
    "INDIAN_MOBILE": 0.15,
    "PERSON": 0.10,
    "LOCATION": 0.10,
    "DATE_TIME": 0.05,
    "URL": 0.05,
    "IP_ADDRESS": 0.05,
    "MEDICAL_RECORD_NUMBER": 0.25,
    "PATIENT_ID": 0.25,
    "PRIVATE_KEY": 0.30,
    "PEM_BLOCK": 0.30,
    "CONNECTION_STRING": 0.25,
    "PASSWORD": 0.25,
}


class SanitizationError(Exception):
    """Raised when sanitization cannot complete (fail-closed)."""


class SanitizedText(str):
    """A string guaranteed to have passed through VeilRAG fail-closed sanitization.

    Can only be instantiated via `sanitize()`. Direct instantiation by callers raises `TypeError`.
    """

    _SENTINEL = object()

    def __new__(cls, value: str, *, _sentinel: object | None = None) -> SanitizedText:
        if _sentinel is not cls._SENTINEL:
            raise TypeError(
                "SanitizedText cannot be instantiated directly. "
                "Obtain an instance via `src.sanitizer.sanitize(text).safe`."
            )
        return super().__new__(cls, value)


@dataclass(frozen=True)
class EntitySpan:
    """A single detected PII entity span — raw value is never stored."""

    entity_type: str
    start: int
    end: int
    score: float


@dataclass
class SanitizeResult:
    """Result of sanitizing a single document.

    Attributes
    ----------
    sanitized_text
        Input text with all PII replaced by typed numbered placeholders (SanitizedText).
    entities
        Sorted list of detected entity spans (type, start, end, score).
        Raw PII values are intentionally *not* included.
    risk_score
        Float in [0.0, 1.0] estimating overall sensitivity.
    mode
        The context mode used for sanitization.
    reversible_map
        Placeholder → original text mapping, valid only for this request.
        Never persisted to disk or logs.
    safe
        Type-enforced SanitizedText wrapper around sanitized_text.
    """

    sanitized_text: SanitizedText
    entities: list[EntitySpan] = field(default_factory=list)
    risk_score: float = 0.0
    mode: str = "general"
    reversible_map: dict[str, str] = field(default_factory=dict, repr=False)
    safe: SanitizedText = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.sanitized_text, SanitizedText):
            raise TypeError(
                "SanitizeResult requires a SanitizedText instance. "
                "Obtain sanitized text via src.sanitizer.sanitize()."
            )
        object.__setattr__(self, "safe", self.sanitized_text)


def _load_modes() -> dict[str, Any]:
    """Load mode configuration from ``modes.yaml``."""

    with open(_MODES_PATH, encoding="utf-8") as fh:
        return cast(dict[str, Any], yaml.safe_load(fh))


def _get_mode_entities(mode: str) -> list[str]:
    """Return the list of entity types to redact for *mode*."""

    modes = _load_modes()
    if mode not in modes:
        raise SanitizationError(f"Unknown sanitization mode: {mode!r}")
    return list(modes[mode].get("entities", []))


def _deduplicate_spans(
    spans: list[tuple[str, int, int, float]],
) -> list[tuple[str, int, int, float]]:
    """Remove overlapping spans, keeping the higher-confidence match."""

    spans_sorted = sorted(spans, key=lambda s: (s[1], -s[3], s[2] - s[1]))
    kept: list[tuple[str, int, int, float]] = []
    for span in spans_sorted:
        _, start, end, _ = span
        if not any(s_start < end and start < s_end for _, s_start, s_end, _ in kept):
            kept.append(span)
    kept.sort(key=lambda s: s[1])
    return kept


def _calculate_risk_score(entities: list[EntitySpan]) -> float:
    """Estimate a 0–1 risk score from detected entities."""

    if not entities:
        return 0.0

    score = 0.0
    for entity in entities:
        score += _SENSITIVITY_WEIGHTS.get(entity.entity_type, 0.1)

    return min(score, 1.0)


def sanitize(
    text: str,
    mode: str = "general",
    *,
    extra_entities: list[str] | None = None,
) -> SanitizeResult:
    """Redact PII from *text* using the specified *mode*.

    Parameters
    ----------
    text
        The input text, which may contain PII.
    mode
        One of the keys defined in ``modes.yaml`` (``general``,
        ``financial``, ``medical``, ``code``).
    extra_entities
        Additional entity types to redact beyond the mode defaults.

    Returns
    -------
    SanitizeResult
        Redacted text plus metadata (entity spans, risk score, mode,
        reversible placeholder map).

    Raises
    ------
    SanitizationError
        If *mode* is unknown or any detector raises an exception
        (fail-closed — no partial output is ever returned).
    """

    try:
        mode_entities = _get_mode_entities(mode)
        # Credential types are ALWAYS detected (leakage risk), never mode-gated.
        mode_entities += [
            "AWS_ACCESS_KEY",
            "AWS_SECRET_KEY",
            "SECRET_KEY",
            "PRIVATE_KEY",
            "PEM_BLOCK",
            "CONNECTION_STRING",
            "PASSWORD",
        ]
        if extra_entities:
            mode_entities = sorted(set(mode_entities) | set(extra_entities))

        # --- Presidio Analyzer with built-in + custom recognizers ---
        analyzer = _get_analyzer()

        presidio_results: list[RecognizerResult] = analyzer.analyze(
            text=text,
            entities=mode_entities,
            language="en",
        )

        # --- Custom regex detectors ---
        custom_matches: list[RegexMatch] = []
        for detector in DEFAULT_DETECTORS:
            if detector.entity_type not in mode_entities:
                continue
            custom_matches.extend(detector.scan(text))

        # --- Combine all spans into (entity_type, start, end, score) ---
        all_spans: list[tuple[str, int, int, float]] = []
        for r in presidio_results:
            all_spans.append((r.entity_type, r.start, r.end, r.score))
        for m in custom_matches:
            all_spans.append((m.entity_type, m.start, m.end, m.score))

        # --- Deduplicate overlapping spans ---
        deduped = _deduplicate_spans(all_spans)

        # --- Build placeholders with consistent numbering within document ---
        placeholder_counters: dict[str, int] = {}
        text_to_placeholder: dict[tuple[str, str], str] = {}
        reversible_map: dict[str, str] = {}

        result_parts: list[str] = []
        last_end = 0

        for entity_type, start, end, score in deduped:
            original = text[start:end]
            prefix = _PLACEHOLDER_PREFIXES.get(entity_type, entity_type)
            key = (prefix, original)

            if key in text_to_placeholder:
                placeholder = text_to_placeholder[key]
            else:
                counter = placeholder_counters.get(prefix, 0) + 1
                placeholder_counters[prefix] = counter
                placeholder = f"[{prefix}_{counter}]"
                text_to_placeholder[key] = placeholder
                reversible_map[placeholder] = original

            result_parts.append(text[last_end:start])
            result_parts.append(placeholder)
            last_end = end

        result_parts.append(text[last_end:])
        sanitized_text = "".join(result_parts)

        entity_spans = [
            EntitySpan(entity_type=et, start=s, end=e, score=sc)
            for et, s, e, sc in deduped
        ]

        risk_score = _calculate_risk_score(entity_spans)

        safe_text = SanitizedText(sanitized_text, _sentinel=SanitizedText._SENTINEL)

        return SanitizeResult(
            sanitized_text=safe_text,
            entities=entity_spans,
            risk_score=risk_score,
            mode=mode,
            reversible_map=reversible_map,
        )

    except SanitizationError:
        raise
    except Exception as exc:  # fail-closed — never return partial output
        logger.error("Sanitization failed: %s", exc, exc_info=True)
        raise SanitizationError(f"Sanitization failed: {exc}") from exc
