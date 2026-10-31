"""Custom entity recognizers for Microsoft Presidio.

Detects India-specific and credential-specific PII patterns not covered by
Presidio's built-in recognizers:

- Aadhaar (12 digits, Verhoeff checksum validated)
- PAN (AAAAA9999A)
- IFSC (AAAA0NNNNNN)
- UPI IDs (name@bank)
- Indian mobile (+91 / 10 digits starting 6-9)
- AWS access / secret keys
- Generic high-entropy secrets
"""

from __future__ import annotations

import re
from typing import Any

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts

from src.sanitizer.detectors import validate_verhoeff


class AadhaarRecognizer(EntityRecognizer):
    """Recognizer for Indian Aadhaar 12-digit numbers with Verhoeff checksum.

    Rejects numbers starting with 0 or 1 (per UIDAI specification).
    Lowers confidence score to 0.40 when no Aadhaar context words are nearby.
    """

    CONTEXT_WORDS = ("aadhaar", "uid", "aadhar", "enrolment", "enrollment")

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["IDENTITY_DOCUMENT"],
            supported_language="en",
            name="AadhaarRecognizer",
            version="0.1.0",
        )
        self._pattern = re.compile(r"\b[2-9]\d{3}[-\s.]?\d{4}[-\s.]?\d{4}\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None = None,
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        """Detect Verhoeff-valid Aadhaar numbers in *text*."""

        if entities and "IDENTITY_DOCUMENT" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._pattern.finditer(text):
            digits = re.sub(r"[-\s.]", "", m.group())
            if len(digits) != 12:
                continue

            # Per UIDAI specification, Aadhaar numbers never start with 0 or 1
            if digits[0] in ("0", "1"):
                continue

            if not validate_verhoeff(digits):
                continue

            # Check for nearby context words in a 50-character window
            window_start = max(0, m.start() - 50)
            window_end = min(len(text), m.end() + 50)
            surrounding = text[window_start:window_end].lower()
            has_context = any(kw in surrounding for kw in self.CONTEXT_WORDS)

            # High confidence if context is present, lower confidence otherwise
            score = 0.85 if has_context else 0.40

            results.append(
                RecognizerResult(
                    entity_type="IDENTITY_DOCUMENT",
                    start=m.start(),
                    end=m.end(),
                    score=score,
                )
            )
        return results

    def load(self) -> None:
        """No-op load (stateless recognizer)."""


class PANRecognizer(EntityRecognizer):
    """Recognizer for Indian PAN cards (AAAAA9999A)."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PAN_NUMBER"],
            supported_language="en",
            name="PANRecognizer",
            version="0.1.0",
        )
        self._pattern = re.compile(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None,
        nlp_artifacts: NlpArtifacts,
    ) -> list[RecognizerResult]:
        """Detect PAN numbers in *text*."""

        if entities and "PAN_NUMBER" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._pattern.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type="PAN_NUMBER",
                    start=m.start(),
                    end=m.end(),
                    score=0.9,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


class IFSCRecognizer(EntityRecognizer):
    """Recognizer for Indian IFSC codes (AAAA0NNNNNN)."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["IFSC_CODE"],
            supported_language="en",
            name="IFSCRecognizer",
            version="0.1.0",
        )
        self._pattern = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None,
        nlp_artifacts: NlpArtifacts,
    ) -> list[RecognizerResult]:
        """Detect IFSC codes in *text*."""

        if entities and "IFSC_CODE" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._pattern.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type="IFSC_CODE",
                    start=m.start(),
                    end=m.end(),
                    score=0.9,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


class UPIRecognizer(EntityRecognizer):
    """Recognizer for UPI IDs (name@bank)."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["UPI_ID"],
            supported_language="en",
            name="UPIRecognizer",
            version="0.1.0",
        )
        self._pattern = re.compile(r"\b[a-zA-Z0-9.\-]{2,}@[a-zA-Z]{2,}\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None,
        nlp_artifacts: NlpArtifacts,
    ) -> list[RecognizerResult]:
        """Detect UPI IDs in *text*."""

        if entities and "UPI_ID" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._pattern.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type="UPI_ID",
                    start=m.start(),
                    end=m.end(),
                    score=0.85,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


class IndianMobileRecognizer(EntityRecognizer):
    """Recognizer for Indian mobile numbers (+91 or 10 digits starting 6-9)."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["INDIAN_MOBILE"],
            supported_language="en",
            name="IndianMobileRecognizer",
            version="0.1.0",
        )
        self._pattern = re.compile(r"(?<!\d)(?:\+?91[\s\-]*)?[6-9]\d{4}[-\s]?\d{5}\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None,
        nlp_artifacts: NlpArtifacts,
    ) -> list[RecognizerResult]:
        """Detect Indian mobile numbers in *text*."""

        if entities and "INDIAN_MOBILE" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._pattern.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type="INDIAN_MOBILE",
                    start=m.start(),
                    end=m.end(),
                    score=0.9,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


class AWSKeyRecognizer(EntityRecognizer):
    """Recognizer for AWS access keys (AKIA...) and secret keys (40-char base64)."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["AWS_ACCESS_KEY", "AWS_SECRET_KEY"],
            supported_language="en",
            name="AWSKeyRecognizer",
            version="0.1.0",
        )
        self._access_pattern = re.compile(r"\bAKIA[A-Z0-9]{16}\b")
        self._secret_pattern = re.compile(r"\b[A-Za-z0-9/+=]{32,}\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None,
        nlp_artifacts: NlpArtifacts,
    ) -> list[RecognizerResult]:
        """Detect AWS keys in *text*."""

        wanted = {"AWS_ACCESS_KEY", "AWS_SECRET_KEY"}
        if entities and not wanted.intersection(set(entities)):
            return []

        results: list[RecognizerResult] = []

        if not entities or "AWS_ACCESS_KEY" in entities:
            for m in self._access_pattern.finditer(text):
                results.append(
                    RecognizerResult(
                        entity_type="AWS_ACCESS_KEY",
                        start=m.start(),
                        end=m.end(),
                        score=0.95,
                    )
                )

        if not entities or "AWS_SECRET_KEY" in entities:
            for m in self._secret_pattern.finditer(text):
                results.append(
                    RecognizerResult(
                        entity_type="AWS_SECRET_KEY",
                        start=m.start(),
                        end=m.end(),
                        score=0.85,
                    )
                )

        return results

    def load(self) -> None:
        """No-op load."""


class GenericSecretRecognizer(EntityRecognizer):
    """Recognizer for generic high-entropy secret tokens."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["SECRET_KEY"],
            supported_language="en",
            name="GenericSecretRecognizer",
            version="0.1.0",
        )
        self._pattern = re.compile(r"\b(?:sk|pk|[a-z]+_)?[A-Za-z0-9/+=_-]{32,}\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None,
        nlp_artifacts: NlpArtifacts,
    ) -> list[RecognizerResult]:
        """Detect high-entropy secrets in *text*."""

        if entities and "SECRET_KEY" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._pattern.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type="SECRET_KEY",
                    start=m.start(),
                    end=m.end(),
                    score=0.8,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


class MedicalRecordRecognizer(EntityRecognizer):
    """Recognizer for Medical Record Numbers (MRN-xxx)."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["MEDICAL_RECORD_NUMBER"],
            supported_language="en",
            name="MedicalRecordRecognizer",
            version="0.1.0",
        )
        self._pattern = re.compile(r"\bMRN[- ]?\d{4,}\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None,
        nlp_artifacts: NlpArtifacts,
    ) -> list[RecognizerResult]:
        """Detect MRN numbers in *text*."""

        if entities and "MEDICAL_RECORD_NUMBER" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._pattern.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type="MEDICAL_RECORD_NUMBER",
                    start=m.start(),
                    end=m.end(),
                    score=0.9,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


class PatientIDRecognizer(EntityRecognizer):
    """Recognizer for Patient IDs (PID-xxx)."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PATIENT_ID"],
            supported_language="en",
            name="PatientIDRecognizer",
            version="0.1.0",
        )
        self._pattern = re.compile(r"\bPID[- ]?\d{4,}\b")

    def analyze(
        self,
        text: str,
        entities: list[str] | None,
        nlp_artifacts: NlpArtifacts,
    ) -> list[RecognizerResult]:
        """Detect patient IDs in *text*."""

        if entities and "PATIENT_ID" not in entities:
            return []

        results: list[RecognizerResult] = []
        for m in self._pattern.finditer(text):
            results.append(
                RecognizerResult(
                    entity_type="PATIENT_ID",
                    start=m.start(),
                    end=m.end(),
                    score=0.9,
                )
            )
        return results

    def load(self) -> None:
        """No-op load."""


def get_custom_recognizers() -> list[Any]:
    """Return all custom recognizers to register with Presidio Analyzer."""

    return [
        AadhaarRecognizer(),
        PANRecognizer(),
        IFSCRecognizer(),
        UPIRecognizer(),
        IndianMobileRecognizer(),
        AWSKeyRecognizer(),
        GenericSecretRecognizer(),
        MedicalRecordRecognizer(),
        PatientIDRecognizer(),
    ]
