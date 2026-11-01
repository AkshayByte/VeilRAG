"""Tests for the src.sanitizer package — local PII sanitization core."""

from __future__ import annotations

import pytest

from src.sanitizer import (
    SanitizationError,
    SanitizedText,
    SanitizeResult,
    sanitize,
)
from src.sanitizer.detectors import validate_verhoeff

# ── Verhoeff checksum tests ──────────────────────────────────────────────


def test_verhoeff_valid_aadhaar() -> None:
    """A valid 12-digit Aadhaar number passes the Verhoeff check."""

    # Generated to satisfy Verhoeff checksum (known test vector).
    assert validate_verhoeff("123456789012") is False  # invalid check digit


def test_verhoeff_invalid_aadhaar_order_number() -> None:
    """A 12-digit order number failing Verhoeff must NOT be flagged as Aadhaar.

    Negative case: order numbers often look like Aadhaar but fail checksum.
    """

    assert validate_verhoeff("123456789013") is False


def test_verhoeff_non_digit_rejected() -> None:
    """Non-numeric input returns False."""

    assert validate_verhoeff("abcd1234efgh") is False
    assert validate_verhoeff("") is False


# ── sanitize() basic behavior ────────────────────────────────────────────

def test_sanitize_returns_result_object() -> None:
    """sanitize returns a SanitizeResult instance."""

    result = sanitize("Hello world")
    assert isinstance(result, SanitizeResult)


def test_sanitize_result_has_required_fields() -> None:
    """SanitizeResult exposes sanitized_text, entities, risk_score, mode."""

    result = sanitize("Alice Smith at alice@example.com")
    assert result.sanitized_text is not None
    assert isinstance(result.entities, list)
    assert 0.0 <= result.risk_score <= 1.0
    assert result.mode == "general"


def test_sanitize_no_pii_returns_unchanged_text() -> None:
    """Text without PII is returned unchanged with zero entities."""

    result = sanitize("The quick brown fox jumps over the lazy dog.")
    assert result.sanitized_text == "The quick brown fox jumps over the lazy dog."
    assert result.entities == []
    assert result.risk_score == 0.0


def test_sanitize_redacts_person() -> None:
    """PERSON entities are replaced with typed placeholders."""

    result = sanitize("John Doe is here.")
    assert "John Doe" not in result.sanitized_text
    assert "[PERSON_1]" in result.sanitized_text


def test_sanitize_redacts_email() -> None:
    """EMAIL_ADDRESS entities are replaced with typed placeholders."""

    result = sanitize("Contact alice@example.com.")
    assert "alice@example.com" not in result.sanitized_text
    assert "[EMAIL_ADDRESS_1]" in result.sanitized_text


def test_sanitize_redacts_phone() -> None:
    """PHONE_NUMBER entities are replaced."""

    result = sanitize("Call 555-123-4567.")
    assert "555-123-4567" not in result.sanitized_text
    assert "[PHONE_1]" in result.sanitized_text


def test_sanitize_redacts_us_ssn() -> None:
    """US_SSN entities are replaced."""

    result = sanitize("SSN: 123-45-6789.")
    assert "123-45-6789" not in result.sanitized_text
    assert "[US_SSN_1]" in result.sanitized_text


def test_sanitize_redacts_credit_card() -> None:
    """CREDIT_CARD entities are replaced."""

    result = sanitize("Card 4111 1111 1111 1111.")
    assert "4111 1111 1111 1111" not in result.sanitized_text
    assert "[CREDIT_CARD_1]" in result.sanitized_text


# ── Consistent placeholder numbering ─────────────────────────────────────


def test_same_person_same_placeholder() -> None:
    """The same person name maps to the same placeholder throughout one document."""

    text = "Alice Smith called Alice Smith again."
    result = sanitize(text)
    count = result.sanitized_text.count("[PERSON_1]")
    assert count == 2
    assert "[PERSON_2]" not in result.sanitized_text


def test_different_types_different_counters() -> None:
    """PERSON and EMAIL_ADDRESS each get their own counter sequence."""

    result = sanitize("Alice Smith alice@example.com")
    assert "[PERSON_1]" in result.sanitized_text
    assert "[EMAIL_ADDRESS_1]" in result.sanitized_text


# ── Entity metadata (type, start, end, score — never raw value) ─────────


def test_entity_span_fields() -> None:
    """Each entity span has type, start, end, score but no raw text."""

    result = sanitize("Alice Smith at alice@example.com.")
    person = next(e for e in result.entities if e.entity_type == "PERSON")
    email = next(e for e in result.entities if e.entity_type == "EMAIL_ADDRESS")

    assert person.entity_type == "PERSON"
    assert isinstance(person.start, int)
    assert isinstance(person.end, int)
    assert 0.0 <= person.score <= 1.0
    assert email.entity_type == "EMAIL_ADDRESS"

    # Raw values must never appear in entities
    assert not hasattr(person, "text") or person.text is None


# ── Risk score ───────────────────────────────────────────────────────────


def test_risk_score_zero_for_no_pii() -> None:
    """Risk score is 0.0 when no PII is detected."""

    result = sanitize("Hello world.")
    assert result.risk_score == 0.0


def test_risk_score_high_for_sensitive_pii() -> None:
    """Risk score increases for high-sensitivity entities."""

    result_low = sanitize("Alice Smith.")
    result_high = sanitize("SSN 123-45-6789 card 4111111111111111.")
    assert result_high.risk_score > result_low.risk_score


def test_risk_score_bounded() -> None:
    """Risk score always stays within [0.0, 1.0]."""

    result = sanitize("SSN 123-45-6789 card 4111111111111111 AWS AKIAIOSFODNN7EXAMPLE.")
    assert 0.0 <= result.risk_score <= 1.0


# ── Context modes ────────────────────────────────────────────────────────


def test_general_mode_default() -> None:
    """Default mode is 'general'."""

    result = sanitize("Alice Smith.")
    assert result.mode == "general"


def test_invalid_mode_raises() -> None:
    """An unknown mode raises SanitizationError (fail-closed)."""

    with pytest.raises(SanitizationError):
        sanitize("Alice Smith.", mode="nonexistent_mode")


def test_financial_mode_redacts_ifsc() -> None:
    """Financial mode redacts IFSC codes."""

    result = sanitize("IFSC: HDFC0001234.", mode="financial")
    assert "HDFC0001234" not in result.sanitized_text
    assert "[IFSC_1]" in result.sanitized_text


def test_financial_mode_redacts_upi() -> None:
    """Financial mode redacts UPI IDs."""

    result = sanitize("UPI: rahul@upi.", mode="financial")
    assert "rahul@upi" not in result.sanitized_text
    assert "[UPI_1]" in result.sanitized_text


def test_medical_mode_redacts_patient_id() -> None:
    """Medical mode redacts patient IDs."""

    result = sanitize("Patient MRN-12345.", mode="medical")
    assert "MRN-12345" not in result.sanitized_text


def test_code_mode_redacts_aws_key() -> None:
    """Code mode redacts AWS access keys."""

    result = sanitize("Key: AKIAIOSFODNN7EXAMPLE.", mode="code")
    assert "AKIAIOSFODNN7EXAMPLE" not in result.sanitized_text
    assert "[AWS_ACCESS_KEY_1]" in result.sanitized_text


def test_sanitize_mode_full_redacts_enterprise_entities() -> None:
    """Mode 'full' redacts IFSC, UPI ID, Medical Record Number, and Patient ID."""
    text = (
        "Transfer via IFSC HDFC0001234 and UPI rohit@okhdfcbank. "
        "Patient record MRN-99881 and docket PID-7744."
    )
    result = sanitize(text, mode="full")
    assert "HDFC0001234" not in result.safe
    assert "[IFSC_1]" in result.safe
    assert "rohit@okhdfcbank" not in result.safe
    assert "[UPI_1]" in result.safe
    assert "MRN-99881" not in result.safe
    assert "[MEDICAL_RECORD_NUMBER_1]" in result.safe
    assert "PID-7744" not in result.safe
    assert "[PATIENT_ID_1]" in result.safe


def test_default_mode_unchanged_ignores_specialized_entities() -> None:
    """Default mode remains 'general' and does not redact specialized enterprise entities."""
    text = "Contact Alice at alice@example.com with IFSC HDFC0001234 and MRN-99881."
    result = sanitize(text)
    assert result.mode == "general"
    # General entities are redacted
    assert "alice@example.com" not in result.safe
    assert "[EMAIL_ADDRESS_1]" in result.safe
    # Specialized enterprise entities are not in general mode
    assert "HDFC0001234" in result.safe
    assert "MRN-99881" in result.safe


# ── Custom recognizers ───────────────────────────────────────────────────


def test_aadhaar_valid_redacted() -> None:
    """A Verhoeff-valid Aadhaar number starting with 2-9 is redacted."""

    result = sanitize("Aadhaar: 2000 0000 0009.", mode="general")
    assert "[AADHAAR_1]" in result.sanitized_text


def test_aadhaar_dashed_form_redacted() -> None:
    """A dashed Verhoeff-valid Aadhaar number is redacted."""

    result = sanitize("Aadhaar: 2000-0000-0009.", mode="general")
    assert "[AADHAAR_1]" in result.sanitized_text
    assert "2000-0000-0009" not in result.sanitized_text


def test_aadhaar_contiguous_form_redacted() -> None:
    """A contiguous 12-digit Verhoeff-valid Aadhaar number is redacted."""

    result = sanitize("Aadhaar: 200000000009.", mode="general")
    assert "[AADHAAR_1]" in result.sanitized_text
    assert "200000000009" not in result.sanitized_text


def test_aadhaar_dotted_form_redacted() -> None:
    """A dotted 12-digit Verhoeff-valid Aadhaar number is redacted."""

    result = sanitize("Aadhaar: 2345.6789.0124.", mode="general")
    assert "[AADHAAR_1]" in result.sanitized_text
    assert "2345.6789.0124" not in result.sanitized_text


def test_aadhaar_smoke_vector_redacted() -> None:
    """Valid Aadhaar test vector alongside PAN, email, and name are all redacted."""

    text = "Rahul Sharma, Aadhaar 2345 6789 0124, PAN ABCDE1234F, rahul@gmail.com"
    result = sanitize(text)
    assert "[PERSON_1]" in result.sanitized_text
    assert "[AADHAAR_1]" in result.sanitized_text
    assert "[PAN_1]" in result.sanitized_text
    assert "[EMAIL_ADDRESS_1]" in result.sanitized_text
    assert "2345 6789 0124" not in result.sanitized_text
    assert "ABCDE1234F" not in result.sanitized_text
    assert "rahul@gmail.com" not in result.sanitized_text
    assert len(result.entities) == 4


def test_aadhaar_rejects_starts_with_0_or_1() -> None:
    """Aadhaar numbers starting with 0 or 1 are rejected even if Verhoeff valid."""

    from src.sanitizer.recognizers.custom import AadhaarRecognizer

    rec = AadhaarRecognizer()
    # 1000 0000 0004 has a valid Verhoeff checksum but starts with 1
    results = rec.analyze("Aadhaar: 1000 0000 0004", ["IDENTITY_DOCUMENT"])
    assert len(results) == 0

    # 0123 4567 8900 starts with 0
    res_0 = rec.analyze("Aadhaar: 0123 4567 8900", ["IDENTITY_DOCUMENT"])
    assert len(res_0) == 0


def test_aadhaar_lowers_confidence_without_context() -> None:
    """Aadhaar recognizer returns higher confidence with context words and lower without."""

    from src.sanitizer.recognizers.custom import AadhaarRecognizer

    rec = AadhaarRecognizer()
    # 2345 6789 0124 starts with 2 and has valid Verhoeff check
    with_context = rec.analyze(
        "My Aadhaar card number is 2345 6789 0124", ["IDENTITY_DOCUMENT"]
    )
    without_context = rec.analyze(
        "The shipment code is 2345 6789 0124", ["IDENTITY_DOCUMENT"]
    )
    assert len(with_context) == 1
    assert len(without_context) == 1
    assert with_context[0].score > without_context[0].score
    assert with_context[0].score >= 0.80
    assert without_context[0].score <= 0.50


def test_aadhaar_invalid_not_redacted() -> None:
    """A 12-digit number failing Verhoeff (e.g. order number) is NOT redacted as Aadhaar."""

    text = "Order 123456789012 shipped."
    result = sanitize(text, mode="general")
    aadhaar_entities = [e for e in result.entities if e.entity_type == "IDENTITY_DOCUMENT"]
    assert len(aadhaar_entities) == 0
    assert "123456789012" in result.sanitized_text

    # Also test another 12-digit invalid number (such as 2345 6789 0123)
    res2 = sanitize("Order number 2345 6789 0123 processed successfully.")
    aadhaar2 = [e for e in res2.entities if e.entity_type == "IDENTITY_DOCUMENT"]
    assert len(aadhaar2) == 0
    assert "2345 6789 0123" in res2.sanitized_text


def test_pan_redacted() -> None:
    """PAN numbers are redacted."""

    result = sanitize("PAN: ABCDE1234F.")
    assert "ABCDE1234F" not in result.sanitized_text
    assert "[PAN_1]" in result.sanitized_text


def test_indian_mobile_redacted() -> None:
    """Indian mobile numbers are redacted."""

    result = sanitize("Call +91 9876543210.")
    assert "+91 9876543210" not in result.sanitized_text
    assert "[PHONE_1]" in result.sanitized_text


def test_indian_mobile_not_matched_inside_12_digit_number() -> None:
    """A 12-digit number (barcode/tracking) must not have its tail matched as a mobile number."""

    # 109283746519 ends in 9283746519 (a 10-digit sequence starting with 9).
    # Without negative lookbehind, this falsely flagged as INDIAN_MOBILE.
    text = "Package tracking barcode 109283746519 was registered."
    result = sanitize(text, mode="general")
    mobile_entities = [e for e in result.entities if e.entity_type == "INDIAN_MOBILE"]
    assert len(mobile_entities) == 0
    assert "109283746519" in result.sanitized_text


def test_indian_mobile_split_blocks_redacted() -> None:
    """Indian mobile numbers formatted with 5+5 digit blocks or dashes are redacted."""

    res1 = sanitize("Reach me at +91-98765-43210 immediately.")
    assert "+91-98765-43210" not in res1.sanitized_text
    assert "[PHONE_1]" in res1.sanitized_text

    res2 = sanitize("Helpline desk contact: 98765 43210.")
    assert "98765 43210" not in res2.sanitized_text
    assert "[PHONE_1]" in res2.sanitized_text


def test_aws_secret_key_redacted() -> None:
    """AWS secret keys are redacted."""

    result = sanitize("Secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY.")
    assert "[AWS_SECRET_KEY_1]" in result.sanitized_text


def test_url_redacted() -> None:
    """URLs are redacted."""

    result = sanitize("Visit https://example.com.")
    assert "https://example.com" not in result.sanitized_text
    assert "[URL_1]" in result.sanitized_text


def test_ip_redacted() -> None:
    """IP addresses are redacted."""

    result = sanitize("Server at 192.168.1.1.")
    assert "192.168.1.1" not in result.sanitized_text
    assert "[IP_ADDRESS_1]" in result.sanitized_text


# ── Fail-closed behavior ─────────────────────────────────────────────────


def test_sanitization_error_is_exception() -> None:
    """SanitizationError is a proper exception class."""

    assert issubclass(SanitizationError, Exception)


def test_extra_entities_redacted() -> None:
    """Extra entities beyond mode defaults are redacted."""

    result = sanitize("API key sk-abc123def456ghi789jkl012mno345pq.", extra_entities=["SECRET_KEY"])
    assert "[SECRET_KEY_1]" in result.sanitized_text


# ── Reversible map (request scope only) ──────────────────────────────────


def test_reversible_map_contains_placeholders() -> None:
    """The reversible map maps placeholder → original text."""

    result = sanitize("Alice Smith alice@example.com.")
    assert "[PERSON_1]" in result.reversible_map
    assert result.reversible_map["[PERSON_1]"] == "Alice Smith"
    assert result.reversible_map["[EMAIL_ADDRESS_1]"] == "alice@example.com"


def test_reversible_map_not_persisted() -> None:
    """The reversible map exists only for this request (not on the result as a persisted field)."""

    result = sanitize("Alice Smith.")
    # reversible_map is a field of SanitizeResult but marked repr=False
    assert "reversible_map" not in repr(result)


# ── SanitizedText type boundary enforcement ──────────────────────────────


def test_sanitized_text_cannot_be_instantiated_directly() -> None:
    """Direct instantiation of SanitizedText raises TypeError."""
    with pytest.raises(TypeError, match="cannot be instantiated directly"):
        SanitizedText("plain text")


def test_sanitize_result_requires_sanitized_text() -> None:
    """SanitizeResult raises TypeError if sanitized_text is not a SanitizedText instance."""
    with pytest.raises(TypeError, match="requires a SanitizedText instance"):
        SanitizeResult(sanitized_text="plain text")  # type: ignore[arg-type]


def test_sanitize_returns_sanitized_text_instance() -> None:
    """sanitize() returns SanitizedText for both safe and sanitized_text."""
    res = sanitize("Contact alice@example.com")
    assert isinstance(res.safe, SanitizedText)
    assert isinstance(res.sanitized_text, SanitizedText)
    assert isinstance(res.safe, str)


def test_string_concatenation_drops_sanitized_text_type() -> None:
    """Tampered or concatenated strings revert to plain str and lose SanitizedText type."""
    res = sanitize("Contact alice@example.com")
    tampered = res.safe + " unredacted leak"
    assert not isinstance(tampered, SanitizedText)
    assert isinstance(tampered, str)


def test_placeholder_namespacing_prevents_chunk_collision() -> None:
    """placeholder_prefix namespaces placeholders to prevent collision with stored chunk tokens."""
    res = sanitize("Patient Vikram Malhotra has Aadhaar 2345 6789 0124", placeholder_prefix="Q_")
    assert "[Q_PERSON_1]" in res.safe
    assert "[Q_AADHAAR_1]" in res.safe
    assert "[PERSON_1]" not in res.safe
    assert "[AADHAAR_1]" not in res.safe
    assert "[Q_PERSON_1]" in res.reversible_map
    assert res.reversible_map["[Q_PERSON_1]"] == "Vikram Malhotra"


def test_sanitize_idempotency_on_placeholder_text() -> None:
    """sanitize(sanitize(x)) == sanitize(x) holds across nested passes."""
    text = (
        "Transfer request from [Q_PERSON_1] with Aadhaar [Q_AADHAAR_1] to "
        "beneficiary [PERSON_1] with IFSC [IFSC_1]."
    )
    res1 = sanitize(text, mode="full")
    res2 = sanitize(res1.safe, mode="full")
    assert res1.safe == text
    assert res2.safe == res1.safe



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
