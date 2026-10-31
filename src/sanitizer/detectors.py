"""Custom regex-based PII detectors.

These detectors complement Microsoft Presidio's built-in recognizers with
India-specific and credential-specific patterns.  Each detector exposes a
``scan(text) -> list[RegexMatch]`` method.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Verhoeff algorithm tables for Aadhaar checksum validation
_VERHOEFF_MUL = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_PERM = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def validate_verhoeff(number: str) -> bool:
    """Validate a numeric string using the Verhoeff checksum algorithm.

    Parameters
    ----------
    number
        A string of decimal digits (e.g. a 12-digit Aadhaar number).

    Returns
    -------
    bool
        ``True`` if the Verhoeff check digit validates.
    """

    if not number.isdigit():
        return False

    digits = [int(d) for d in number]
    c = 0
    for i, digit in enumerate(reversed(digits)):
        c = _VERHOEFF_MUL[c][_VERHOEFF_PERM[i % 8][digit]]
    return c == 0


@dataclass(frozen=True)
class RegexMatch:
    """A single regex-detected PII occurrence."""

    entity_type: str
    start: int
    end: int
    score: float
    match_text: str


@dataclass(frozen=True)
class Detector:
    """A named regex detector with associated entity type."""

    name: str
    entity_type: str
    pattern: str

    def scan(self, text: str) -> list[RegexMatch]:
        """Return all matches of this detector's pattern in *text*."""

        results: list[RegexMatch] = []
        for m in re.finditer(self.pattern, text):
            results.append(
                RegexMatch(
                    entity_type=self.entity_type,
                    start=m.start(),
                    end=m.end(),
                    score=0.9,
                    match_text=m.group(),
                )
            )
        return results


# Indian mobile: +91 followed by 10 digits starting 6-9, or bare 10 digits
_INDIAN_MOBILE_PATTERN = r"(?:\+91\s*)?[6-9]\d{9}"

# PAN: AAAAA9999A (5 alpha, 4 digit, 1 alpha)
_PAN_PATTERN = r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"

# IFSC: 4 alpha, 0, 6 alphanumeric
_IFSC_PATTERN = r"\b[A-Z]{4}0[A-Z0-9]{6}\b"

# UPI: name@bank or name.surname@bank etc.
_UPI_PATTERN = r"\b[a-zA-Z0-9.\-]{2,}@[a-zA-Z]{2,}\b"

# AWS Access Key ID
_AWS_ACCESS_KEY_PATTERN = r"\bAKIA[A-Z0-9]{16}\b"

# AWS Secret Access Key (32+ chars, base64-like including / and +)
_AWS_SECRET_KEY_PATTERN = r"\b[A-Za-z0-9/+=]{32,}\b"

# Generic high-entropy secret token (sk-, pk-, etc., includes / and +)
_GENERIC_SECRET_PATTERN = r"\b(?:sk|pk|[a-z]+_)?[A-Za-z0-9/+=_-]{32,}\b"

# US SSN
_SSN_PATTERN = r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b"

# Medical Record Number (MRN-xxx or MRN xxx)
_MRN_PATTERN = r"\bMRN[- ]?\d{4,}\b"

# Patient ID (PID-xxx or PID xxx)
_PATIENT_ID_PATTERN = r"\bPID[- ]?\d{4,}\b"

# Credit card (basic Luhn-agnostic pattern; Presidio also has one)
_CREDIT_CARD_PATTERN = r"\b(?:\d[ -]?){13,16}\b"

# URL
_URL_PATTERN = r"https?://[^\s<>\"]+"

# IP address (IPv4)
_IP_PATTERN = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"

DEFAULT_DETECTORS: list[Detector] = [
    Detector(
        name="indian_mobile",
        entity_type="INDIAN_MOBILE",
        pattern=_INDIAN_MOBILE_PATTERN,
    ),
    Detector(
        name="pan_number",
        entity_type="PAN_NUMBER",
        pattern=_PAN_PATTERN,
    ),
    Detector(
        name="ifsc_code",
        entity_type="IFSC_CODE",
        pattern=_IFSC_PATTERN,
    ),
    Detector(
        name="upi_id",
        entity_type="UPI_ID",
        pattern=_UPI_PATTERN,
    ),
    Detector(
        name="aws_access_key",
        entity_type="AWS_ACCESS_KEY",
        pattern=_AWS_ACCESS_KEY_PATTERN,
    ),
    Detector(
        name="aws_secret_key",
        entity_type="AWS_SECRET_KEY",
        pattern=_AWS_SECRET_KEY_PATTERN,
    ),
    Detector(
        name="generic_secret",
        entity_type="SECRET_KEY",
        pattern=_GENERIC_SECRET_PATTERN,
    ),
    Detector(
        name="us_ssn",
        entity_type="US_SSN",
        pattern=_SSN_PATTERN,
    ),
    Detector(
        name="credit_card",
        entity_type="CREDIT_CARD",
        pattern=_CREDIT_CARD_PATTERN,
    ),
    Detector(
        name="url",
        entity_type="URL",
        pattern=_URL_PATTERN,
    ),
    Detector(
        name="ip_address",
        entity_type="IP_ADDRESS",
        pattern=_IP_PATTERN,
    ),
    Detector(
        name="medical_record_number",
        entity_type="MEDICAL_RECORD_NUMBER",
        pattern=_MRN_PATTERN,
    ),
    Detector(
        name="patient_id",
        entity_type="PATIENT_ID",
        pattern=_PATIENT_ID_PATTERN,
    ),
]

__all__ = [
    "validate_verhoeff",
    "RegexMatch",
    "Detector",
    "DEFAULT_DETECTORS",
]
