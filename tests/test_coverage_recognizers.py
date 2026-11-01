"""Unit tests for the Prompt 4A coverage recognizers in src.sanitizer.

Validates detection of:
- DATE_OF_BIRTH (context-bounded dates of birth vs invoice/due dates)
- BANK_ACCOUNT (context-bounded 9-18 digit accounts vs order numbers/quantities)
- ADDRESS (Indian address prefix through 6-digit PIN code vs addresses without PIN or OTPs)
- Hospital IDs (UHID and IP admission numbers vs policy/reference IDs)
"""

from src.config import PIPELINE_MODE
from src.sanitizer import sanitize

# ── DATE_OF_BIRTH Tests ───────────────────────────────────────────────────────


def test_dob_positive_dashed() -> None:
    """Verifies that a date of birth formatted with dashes is redacted under full mode."""
    text = "Candidate profile: John Doe, DOB: 14-08-1988, citizenship Indian."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[DOB_1]" in res.safe
    assert "14-08-1988" not in res.safe


def test_dob_positive_slashed() -> None:
    """Verifies that a date of birth formatted with slashes is redacted."""
    text = "Patient details: Date of Birth: 22/11/1982 recorded on admission."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[DOB_1]" in res.safe
    assert "22/11/1982" not in res.safe


def test_dob_positive_textual_month() -> None:
    """Verifies that a date of birth formatted with textual month is redacted."""
    text = "Employee was born on 19 March 1990 in Bengaluru."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[DOB_1]" in res.safe
    assert "19 March 1990" not in res.safe


def test_dob_positive_dotted() -> None:
    """Verifies that a date of birth formatted with dots is redacted."""
    text = "KYC Form: D.O.B: 05.12.1995 verified with passport."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[DOB_1]" in res.safe
    assert "05.12.1995" not in res.safe


def test_dob_hard_negative_invoice_date() -> None:
    """Hard negative: Invoice dates must NOT be redacted as DATE_OF_BIRTH."""
    text = "Tax Invoice INV-2026-9901 dated Invoice Date: 14-08-2023 for software licensing."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "14-08-2023" in res.safe
    assert "[DOB" not in res.safe


def test_dob_hard_negative_due_date() -> None:
    """Hard negative: Due dates must NOT be redacted as DATE_OF_BIRTH."""
    text = "Payment reminder: Loan installment Due Date: 22/11/2024 to avoid penalty."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "22/11/2024" in res.safe
    assert "[DOB" not in res.safe


def test_dob_hard_negative_effective_date() -> None:
    """Hard negative: Employment policy effective dates must NOT be redacted as DOB."""
    text = "The revised attendance policy takes effect from 15 April 2025 across all units."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "15 April 2025" in res.safe
    assert "[DOB" not in res.safe


# ── BANK_ACCOUNT Tests ────────────────────────────────────────────────────────


def test_bank_account_positive_standard() -> None:
    """Verifies that an account number with explicit bank account context is redacted."""
    text = "Disbursement instructions: Credit Bank Account: 50100234918231 via RTGS."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ACCOUNT_1]" in res.safe
    assert "50100234918231" not in res.safe


def test_bank_account_positive_ac_no() -> None:
    """Verifies that an account number with 'A/C No' label is redacted."""
    text = "Settlement remittance sent to A/C No: 20489912034 with immediate effect."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ACCOUNT_1]" in res.safe
    assert "20489912034" not in res.safe


def test_bank_account_positive_acct_prefix() -> None:
    """Verifies that an account number with 'Acct' label is redacted."""
    text = "Vendor details: Acct 004501589123 branch clearing."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ACCOUNT_1]" in res.safe
    assert "004501589123" not in res.safe


def test_bank_account_hard_negative_order_number() -> None:
    """Hard negative: Numeric order IDs must NOT be redacted as BANK_ACCOUNT."""
    text = "Your e-commerce shipment Order #914010034 has been dispatched via courier."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ACCOUNT" not in res.safe
    assert not any(e.entity_type == "BANK_ACCOUNT" for e in res.entities)


def test_bank_account_hard_negative_quantity() -> None:
    """Hard negative: 9-digit inventory quantities must NOT be redacted as BANK_ACCOUNT."""
    text = "Warehouse logistics summary: Processed 123456789 units during Q3 audit."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ACCOUNT" not in res.safe
    assert not any(e.entity_type == "BANK_ACCOUNT" for e in res.entities)


# ── ADDRESS Tests ─────────────────────────────────────────────────────────────


def test_address_positive_flat_with_pin() -> None:
    """Verifies that a residential address starting with Flat and ending with PIN is redacted."""
    text = (
        "Resident Address: Flat 402 Palm Meadows, "
        "Whitefield Main Road, Bengaluru, Karnataka 560066."
    )
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ADDRESS_1]" in res.safe
    assert "560066" not in res.safe


def test_address_positive_house_with_pin() -> None:
    """Verifies that a residential address starting with House No is redacted."""
    text = "Current Residence: House No 12, Sector 18, Vashi, Navi Mumbai, Maharashtra 400703."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ADDRESS_1]" in res.safe
    assert "400703" not in res.safe


def test_address_positive_plot_with_pin() -> None:
    """Verifies that a commercial plot address ending with PIN is redacted."""
    text = "Facility Location: Plot 88, Okhla Industrial Area Phase 3, New Delhi 110020."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ADDRESS_1]" in res.safe
    assert "110020" not in res.safe


def test_address_hard_negative_no_pin() -> None:
    """Hard negative: Address without a valid 6-digit PIN code must NOT be matched by ADDRESS."""
    text = "Regional office located at House 45, Koramangala 4th Block, Bengaluru, Karnataka."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[ADDRESS" not in res.safe


def test_address_hard_negative_otp() -> None:
    """Hard negative: 6-digit OTP codes must NOT be redacted as an ADDRESS."""
    text = "Security Notification: Your verification OTP is 560066, valid for 10 minutes."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "560066" in res.safe
    assert "[ADDRESS" not in res.safe


# ── Hospital ID Tests (UHID / IP Admission) ───────────────────────────────────


def test_hospital_uhid_positive() -> None:
    """Verifies that a patient UHID identifier is redacted."""
    text = "Patient triage chart: UHID: UH-889021 admitted to acute surgical ward."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[UHID_1]" in res.safe
    assert "UH-889021" not in res.safe


def test_hospital_ip_admission_positive() -> None:
    """Verifies that an in-patient admission identifier is redacted."""
    text = "Hospital intake record: IP Admission No: IP-2026-MED-77412 confirmed by nurse."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "[UHID_1]" in res.safe
    assert "IP-2026-MED-77412" not in res.safe


def test_hospital_hard_negative_policy_ref() -> None:
    """Hard negative: Policy reference numbers must NOT be redacted as hospital UHID."""
    text = "Corporate coverage under Policy Reference: REF-2026-MED-77412 with full indemnity."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "REF-2026-MED-77412" in res.safe
    assert "[UHID" not in res.safe


def test_hospital_hard_negative_claim_no() -> None:
    """Hard negative: Insurance claim numbers must NOT be redacted as hospital UHID."""
    text = "Settlement approved for Claim No: CLM-1092834 filed under motor vehicular cover."
    res = sanitize(text, mode=PIPELINE_MODE)
    assert "CLM-1092834" in res.safe
    assert "[UHID" not in res.safe
