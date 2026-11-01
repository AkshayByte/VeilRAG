"""Coverage entity recognizers for VeilRAG.

Detects additional privacy-sensitive entity types to close the measured
ingestion privacy gaps:

- DATE_OF_BIRTH: contextual date of birth only (DOB, date of birth, born on, D.O.B)
- BANK_ACCOUNT: 9-18 digit account numbers with explicit banking context
- ADDRESS: Indian address spans from Flat/House/Plot/# through 6-digit PIN code
- Hospital IDs: UHID (UH-\\d+), IP admission numbers, MRN/patient-id variants
"""

from __future__ import annotations

import re
from typing import Any

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts


class DateOfBirthRecognizer(EntityRecognizer):
    """Recognizer for dates of birth with strict contextual anchoring.

    Only flags dates when preceded or followed within ~35 characters by explicit
    birth-related context tokens (DOB, date of birth, born on, birth date).
    Generic business dates (invoices, effective dates, notice periods) are ignored.
    """

    CONTEXT_WORDS = ("dob", "date of birth", "born on", "born in", "d.o.b", "birth date")

    _CONTEXT_PATTERN = re.compile(
        r"\b(?:d\.?o\.?b\.?|date\s+of\s+birth|born\s+(?:on|in)|birth\s*date)\b",
        re.IGNORECASE,
    )

    _DATE_NUMERIC = re.compile(
        r"\b(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|1[012])[-/.](19\d\d|20[0-2]\d)\b"
    )

    _DATE_WORDS = re.compile(
        r"\b(0?[1-9]|[12]\d|3[01])\s+"
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+"
        r"(19\d\d|20[0-2]\d)\b",
        re.IGNORECASE,
    )

    _DATE_HYPHEN_WORDS = re.compile(
        r"\b(0?[1-9]|[12]\d|3[01])-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(19\d\d|20[0-2]\d)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["DATE_OF_BIRTH"],
            supported_language="en",
            name="DateOfBirthRecognizer",
            version="0.1.0",
        )

    def analyze(
        self,
        text: str,
        entities: list[str] | None = None,
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        """Detect contextual date of birth spans in *text*."""
        if entities and "DATE_OF_BIRTH" not in entities:
            return []

        results: list[RecognizerResult] = []
        seen_spans: set[tuple[int, int]] = set()

        patterns = [self._DATE_NUMERIC, self._DATE_WORDS, self._DATE_HYPHEN_WORDS]
        for pattern in patterns:
            for m in pattern.finditer(text):
                start, end = m.start(), m.end()
                if (start, end) in seen_spans:
                    continue

                window_before = text[max(0, start - 35) : start]
                window_after = text[end : min(len(text), end + 35)]

                if self._CONTEXT_PATTERN.search(window_before) or self._CONTEXT_PATTERN.search(
                    window_after
                ):
                    seen_spans.add((start, end))
                    results.append(
                        RecognizerResult(
                            entity_type="DATE_OF_BIRTH",
                            start=start,
                            end=end,
                            score=0.85,
                        )
                    )
        return results

    def load(self) -> None:
        """No-op load."""


class BankAccountRecognizer(EntityRecognizer):
    """Recognizer for 9-18 digit bank account numbers requiring explicit banking context.

    Rejects 6-digit OTPs, phone-like numbers, asset tags, quantities, and order numbers.
    """

    CONTEXT_WORDS = ("account", "a/c", "acct", "account no", "acc no", "account number")

    _ACCOUNT_PATTERN = re.compile(r"\b\d{9,18}\b")

    _CONTEXT_PATTERN = re.compile(
        r"\b(?:account|acct|a/c|account\s*no\.?|acc\s*no\.?|account\s*number|"
        r"savings\s*account|current\s*account|salary\s*account|designated\s*account|"
        r"escrow|beneficiary)\b",
        re.IGNORECASE,
    )

    _NEGATIVE_PATTERN = re.compile(
        r"\b(?:mobile|phone|contact|call|tel|cell|order|tracking|serial|asset|"
        r"invoice|receipt|pin|otp|spool|quantity|qty|units?|cycles?|picometers?|microvolts?)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["BANK_ACCOUNT"],
            supported_language="en",
            name="BankAccountRecognizer",
            version="0.1.0",
        )

    def analyze(
        self,
        text: str,
        entities: list[str] | None = None,
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        """Detect bank account numbers in *text*."""
        if entities and "BANK_ACCOUNT" not in entities:
            return []

        results: list[RecognizerResult] = []

        for m in self._ACCOUNT_PATTERN.finditer(text):
            start, end = m.start(), m.end()
            val = m.group()

            window_before = text[max(0, start - 35) : start]
            window_after = text[end : min(len(text), end + 35)]
            combined_window = window_before + " " + window_after

            # Skip if negative context is present
            if self._NEGATIVE_PATTERN.search(combined_window):
                continue

            # Must have positive banking account context
            if not self._CONTEXT_PATTERN.search(combined_window):
                continue

            # If 10 digits starting with 6-9, ensure it's not a mobile number
            if len(val) == 10 and val[0] in "6789":
                alert_pattern = r"\baccount\s+(?:alert|manager|holder|setting)"
                if re.search(alert_pattern, combined_window, re.I):
                    continue

            results.append(
                RecognizerResult(
                    entity_type="BANK_ACCOUNT",
                    start=start,
                    end=end,
                    score=1.0,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


class AddressRecognizer(EntityRecognizer):
    """Recognizer for Indian postal addresses starting from premises markers through a 6-digit PIN.

    Matches spans starting with Flat/House/Plot/No./# through a 6-digit PIN code (first digit 1-9).
    Addresses without PIN codes or standalone PINs are not matched.
    """

    _PATTERN = re.compile(
        r"\b(?:Flat|House|Plot|Door\s+No\.?|Tower|Apartment|Apt|Building|Suite|Bait-ul-Salam|"
        r"[A-Z]-\d+|(?:No\.?|#)\s*\d+)\b"
        r"[^\n\r]{10,120}?"
        r"(?<![-\w])\b[1-9]\d{5}\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["ADDRESS", "STREET_ADDRESS"],
            supported_language="en",
            name="AddressRecognizer",
            version="0.1.0",
        )

    def analyze(
        self,
        text: str,
        entities: list[str] | None = None,
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        """Detect Indian address spans in *text*."""
        allowed = {"ADDRESS", "STREET_ADDRESS"}
        if entities and not (set(entities) & allowed):
            return []

        # Determine preferred entity type tag
        target_type = "ADDRESS"
        if entities and "STREET_ADDRESS" in entities and "ADDRESS" not in entities:
            target_type = "STREET_ADDRESS"

        results: list[RecognizerResult] = []
        for m in self._PATTERN.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type=target_type,
                    start=m.start(),
                    end=m.end(),
                    score=0.85,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


class HospitalIDRecognizer(EntityRecognizer):
    """Recognizer for hospital IDs (UHID, IP admission numbers, clinical dossiers, MRN/PID)."""

    _PATTERN = re.compile(
        r"\b(?:"
        r"UH-\d{4,}|"
        r"IP-\d{4}-[A-Z]+-\d+|"
        r"[A-Z]{2,5}-(?:CARD|ORTHO|MED|SURG|PED)-\d{4}-[A-Z]{3}-\d+|"
        r"MRN[-: ]*\d{4,}|"
        r"PID[-: ]*\d{4,}"
        r")\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["UHID"],
            supported_language="en",
            name="HospitalIDRecognizer",
            version="0.1.0",
        )

    def analyze(
        self,
        text: str,
        entities: list[str] | None = None,
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        """Detect hospital IDs in *text*."""
        if entities and "UHID" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._PATTERN.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type="UHID",
                    start=m.start(),
                    end=m.end(),
                    score=0.90,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


def get_coverage_recognizers() -> list[Any]:
    """Return all coverage recognizers to register with Presidio Analyzer."""
    return [
        DateOfBirthRecognizer(),
        BankAccountRecognizer(),
        AddressRecognizer(),
        HospitalIDRecognizer(),
    ]

