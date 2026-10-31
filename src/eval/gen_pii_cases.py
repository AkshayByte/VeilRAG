"""Generate a labeled PII evaluation set for the VeilRAG sanitizer.

Emits ``data/eval/pii_cases.jsonl`` with 150+ synthetic cases built from
Faker (locales en_IN and en_US). Each case carries gold spans
{type, start, end} for overlap-based evaluation.

Includes hard cases:
- names embedded mid-sentence and at start/end
- spaced, dashed, and contiguous Verhoeff-valid Aadhaar numbers
- uppercase, lowercase, and mixed-case PAN numbers
- emails with plus-tags and subdomains
- non-PII lookalikes: 12-digit non-Verhoeff order IDs, pin codes, hardware serials
- clean sentences with zero PII
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from faker import Faker

from src.sanitizer.detectors import validate_verhoeff

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "eval"
CASES_PATH = DATA_DIR / "pii_cases.jsonl"

random.seed(42)
faker_in = Faker("en_IN")
faker_us = Faker("en_US")
Faker.seed(42)


def _make_case(text: str, entities: list[tuple[str, int, int]]) -> dict[str, object]:
    """Build a labeled case dictionary with verified span boundaries."""
    spans: list[dict[str, object]] = []
    for entity_type, start, end in entities:
        if start < 0 or end <= start or end > len(text):
            raise ValueError(f"Invalid span [{start}:{end}] for text length {len(text)}")
        spans.append({"type": entity_type, "start": start, "end": end})
    return {"text": text, "entities": spans}


def gen_names() -> list[dict[str, object]]:
    """Generate cases with names inside sentences (en_IN and en_US)."""
    templates = [
        "Please forward the Q3 audit documentation to {name} by Friday.",
        "According to {name}, the database migration completed with zero downtime.",
        "The project architecture was originally designed by {name} last year.",
        "Yesterday {name} delivered the technical presentation to stakeholders.",
        "Reach out directly to {name} if you experience any permission issues.",
        "All changes require sign-off from {name} prior to staging deployment.",
        "The incident response team was led by {name} during the outage.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(35):
        fk = faker_in if i % 2 == 0 else faker_us
        name = f"{fk.first_name()} {fk.last_name()}"
        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{name}", name)
        start = text.find(name)
        cases.append(_make_case(text, [("PERSON", start, start + len(name))]))
    return cases


def _generate_valid_aadhaar() -> str:
    """Generate a 12-digit number that passes the Verhoeff checksum."""
    while True:
        prefix = "".join(str(random.randint(0, 9)) for _ in range(11))
        # Ensure first digit is not 0 or 1 for realistic UIDAI format
        if prefix[0] in "01":
            prefix = str(random.randint(2, 9)) + prefix[1:]
        for check in range(10):
            candidate = prefix + str(check)
            if validate_verhoeff(candidate):
                return candidate


def gen_aadhaar() -> list[dict[str, object]]:
    """Generate Verhoeff-valid Aadhaar cases in spaced, dashed, and contiguous formats."""
    templates = [
        "The applicant provided Aadhaar number {num} for KYC verification.",
        "Kindly verify identity using Aadhaar {num} on the government portal.",
        "Aadhaar card with number {num} was approved by the registrar.",
        "Link your primary savings account with your Aadhaar {num} today.",
        "Official identity records indicate Aadhaar {num} has been verified.",
    ]
    cases: list[dict[str, object]] = []
    formats = ["spaced", "dashed", "contiguous"]
    for i in range(30):
        raw_digits = _generate_valid_aadhaar()
        fmt = formats[i % len(formats)]
        if fmt == "spaced":
            formatted = f"{raw_digits[:4]} {raw_digits[4:8]} {raw_digits[8:]}"
        elif fmt == "dashed":
            formatted = f"{raw_digits[:4]}-{raw_digits[4:8]}-{raw_digits[8:]}"
        else:
            formatted = raw_digits

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{num}", formatted)
        start = text.find(formatted)
        cases.append(_make_case(text, [("IDENTITY_DOCUMENT", start, start + len(formatted))]))
    return cases


def gen_pan() -> list[dict[str, object]]:
    """Generate PAN cases including uppercase, lowercase, and mixed-case variants."""
    templates = [
        "Please enter your PAN number {pan} on the tax declaration form.",
        "The financial entity registered under PAN {pan} cleared the compliance check.",
        "Ensure your PAN {pan} matches the details on your bank statement.",
        "Income tax return filed against PAN {pan} is under assessment.",
        "Submit a scanned copy of PAN {pan} for account reactivation.",
    ]
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    cases: list[dict[str, object]] = []
    for i in range(25):
        alpha5 = "".join(random.choice(letters) for _ in range(5))
        num4 = f"{random.randint(1000, 9999)}"
        alpha1 = random.choice(letters)
        pan = f"{alpha5}{num4}{alpha1}"

        if i % 3 == 1:
            pan = pan.lower()
        elif i % 3 == 2:
            pan = pan[:3].lower() + pan[3:5].upper() + num4 + pan[-1].lower()

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{pan}", pan)
        start = text.find(pan)
        cases.append(_make_case(text, [("PAN_NUMBER", start, start + len(pan))]))
    return cases


def gen_emails() -> list[dict[str, object]]:
    """Generate email cases including plus-tags and corporate subdomains."""
    templates = [
        "For security escalations, email {email} immediately.",
        "We dispatched an encrypted confirmation email to {email}.",
        "The administrative notification was routed to {email}.",
        "Primary contact address on file is {email}.",
        "Send your signed agreement directly to {email}.",
    ]
    domains = ["example.com", "company.co.in", "secure-mail.org", "corp.internal.net"]
    plus_tags = ["+alerts", "+billing", "+support", "+security", "+dev"]
    cases: list[dict[str, object]] = []
    for i in range(25):
        fk = faker_us if i % 2 == 0 else faker_in
        user = fk.user_name()
        domain = domains[i % len(domains)]
        if i % 2 == 0:
            tag = plus_tags[i % len(plus_tags)]
            email = f"{user}{tag}@{domain}"
        else:
            email = f"{user}.{random.randint(10, 99)}@{domain}"

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{email}", email)
        start = text.find(email)
        cases.append(_make_case(text, [("EMAIL_ADDRESS", start, start + len(email))]))
    return cases


def gen_indian_mobile() -> list[dict[str, object]]:
    """Generate Indian mobile numbers with varying prefixes."""
    templates = [
        "Call customer support at {mobile} during business hours.",
        "The verification OTP was delivered to {mobile}.",
        "Primary phone contact registered is {mobile}.",
        "Dial {mobile} to connect with the local representative.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(20):
        lead_digit = random.choice("6789")
        rest = "".join(str(random.randint(0, 9)) for _ in range(9))
        digits = lead_digit + rest
        fmt = i % 4
        if fmt == 0:
            mobile = f"+91 {digits}"
        elif fmt == 1:
            mobile = f"+91-{digits}"
        elif fmt == 2:
            mobile = f"91{digits}"
        else:
            mobile = digits

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{mobile}", mobile)
        start = text.find(mobile)
        cases.append(_make_case(text, [("INDIAN_MOBILE", start, start + len(mobile))]))
    return cases


def gen_phone_number() -> list[dict[str, object]]:
    """Generate standard US / international phone numbers."""
    templates = [
        "Inquiries can be made via telephone at {phone}.",
        "Reach our regional headquarters at {phone}.",
        "Customer service hotline: {phone}.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(15):
        area = random.randint(200, 999)
        prefix = random.randint(200, 999)
        line = random.randint(1000, 9999)
        phone = f"({area}) {prefix}-{line}" if i % 2 == 0 else f"{area}-{prefix}-{line}"
        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{phone}", phone)
        start = text.find(phone)
        cases.append(_make_case(text, [("PHONE_NUMBER", start, start + len(phone))]))
    return cases


def gen_other_pii() -> list[dict[str, object]]:
    """Generate financial identifiers, US SSN, secrets, URLs, and IPs."""
    items: list[tuple[str, str, str]] = [
        ("US_SSN", "Employee record lists SSN {val} for tax processing.", "123-45-6789"),
        ("US_SSN", "Applicant social security number is {val}.", "987-65-4321"),
        (
            "CREDIT_CARD",
            "Corporate card {val} was charged for hosting fees.",
            "4111-2222-3333-4444",
        ),
        ("CREDIT_CARD", "Payment processed on credit card {val}.", "5500 0000 0000 0004"),
        ("IBAN_CODE", "Vendor wire transferred funds to IBAN {val}.", "GB29NWBK60161331926819"),
        (
            "IBAN_CODE",
            "International clearing code IBAN {val} confirmed.",
            "DE89370400440532013000",
        ),
        ("IFSC_CODE", "Remit the RTGS payment using IFSC {val}.", "SBIN0001234"),
        ("IFSC_CODE", "Branch routing verified with IFSC {val}.", "HDFC0000123"),
        ("UPI_ID", "Make instant merchant payment to {val}.", "vendor.support@upi"),
        ("UPI_ID", "User transferred funds via UPI address {val}.", "rahul@okhdfcbank"),
        (
            "AWS_ACCESS_KEY",
            "AWS access key {val} detected in CI log.",
            "AKIAIOSFODNN7EXAMPLE",
        ),
        ("AWS_ACCESS_KEY", "Deployment worker initialized with key {val}.", "AKIA2EXAMPLEKEY01234"),
        (
            "AWS_SECRET_KEY",
            "Secret access credential {val} was rotated.",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        ),
        (
            "SECRET_KEY",
            "API bearer authorization token is {val}.",
            "sk-proj-abc123def456ghi789jkl012mno345pq",
        ),
        (
            "SECRET_KEY",
            "Private service webhook secret {val} renewed.",
            "pk-live-9982401823901238012938012938",
        ),
        ("IP_ADDRESS", "Database connection pool established from IP {val}.", "192.168.1.105"),
        ("IP_ADDRESS", "Reverse proxy listening on internal host {val}.", "10.0.4.12"),
        (
            "URL",
            "Production API endpoint documentation at {val}.",
            "https://api.internal-vault.com/v2/keys",
        ),
        ("URL", "Staging environment accessible at {val}.", "http://dev-cluster.local.net/status"),
        ("MEDICAL_RECORD_NUMBER", "Patient health file indexed under {val}.", "MRN-44921"),
    ]
    cases: list[dict[str, object]] = []
    for entity_type, tmpl, val in items:
        text = tmpl.replace("{val}", val)
        start = text.find(val)
        cases.append(_make_case(text, [(entity_type, start, start + len(val))]))
    return cases


def gen_hard_negatives() -> list[dict[str, object]]:
    """Hard negative cases (lookalikes that fail checksum or non-PII IDs) -> entities: []."""
    lookalikes = [
        # 12-digit numbers that fail Verhoeff checksum (order IDs, tracking numbers)
        "Order reference 123456789012 has been packaged for dispatch.",
        "Shipment tracking number 234567890123 is currently in transit.",
        "Logistics manifest code 987654321012 cleared export inspection.",
        "Invoice sequence 555566667771 generated by the billing engine.",
        "Warehouse inventory barcode 112233445566 verified on shelf 4.",
        # 6-digit Indian PIN codes (not Aadhaar, phone, or SSN)
        "Delivery available for postal PIN code 560001 and nearby sectors.",
        "Branch operations center located in PIN 110001.",
        "Consignment routed to hub PIN code 400001 today.",
        "Postal sorting station 700001 handled the registered parcel.",
        # Hardware serial numbers and device IDs
        "Server chassis serial number SN: ABC-1234-XYZ passed benchmark tests.",
        "Telemetry gateway DEV-9876543210 connected to MQTT broker.",
        "Diagnostic unit serial SN-88371-B reported normal operating voltage.",
        # Ticket, invoice, and port identifiers
        "Customer support ticket #88371 marked as resolved by engineer.",
        "Accounting invoice INV-2024-9982 scheduled for payment.",
        "Service listening on port 8080 with 16 active worker threads.",
        # Currencies, percentages, room numbers, and dates
        "Annual cloud infrastructure expenses totaled 150000 dollars.",
        "Conference room 305 reserved from 2:00 PM until 4:30 PM.",
        "System throughput increased by 28 percent after the optimization.",
        "Flight AI-4921 scheduled to depart at 09:15 from terminal 3.",
        "Quarterly budget allocation set at 750000 rupees for research.",
    ]
    cases: list[dict[str, object]] = []
    for text in lookalikes:
        cases.append(_make_case(text, []))
    return cases


def gen_clean_sentences() -> list[dict[str, object]]:
    """Sentences that contain zero PII -> entities: []."""
    clean_texts = [
        "The quarterly project milestone is scheduled for next Friday.",
        "Cloud hosting infrastructure was migrated to the new availability zone.",
        "Technical documentation has been committed to the repository.",
        "All integration tests executed cleanly on the automated pipeline.",
        "The performance evaluation showed substantial latency reduction.",
        "Please review the architectural proposal before the design sync.",
        "Customer satisfaction ratings improved across all service tiers.",
        "The distributed cache cluster maintained high availability during peak load.",
        "Database replication lag remained below twenty milliseconds throughout the test.",
        "Static code analysis passed without warnings or style violations.",
        "Microservices communicate asynchronously through reliable message queues.",
        "Continuous delivery pipelines ensure rapid and safe deployments.",
        "The security audit verified that end-to-end encryption is enforced.",
        "Automated backups are scheduled to execute daily at midnight.",
        "System documentation has been updated to reflect the latest API version.",
        "The container orchestration platform dynamically scales worker nodes.",
        "Code review guidelines require thorough unit test coverage for new modules.",
        "The incident postmortem documented lessons learned and follow-up actions.",
        "Network latency between regional data centers remained stable.",
        "Engineering teams hold daily standup meetings to coordinate sprint goals.",
    ]
    cases: list[dict[str, object]] = []
    for text in clean_texts:
        cases.append(_make_case(text, []))
    return cases


def main() -> int:
    """Generate the full labeled evaluation set and persist to pii_cases.jsonl."""
    cases: list[dict[str, object]] = []
    cases.extend(gen_names())
    cases.extend(gen_aadhaar())
    cases.extend(gen_pan())
    cases.extend(gen_emails())
    cases.extend(gen_indian_mobile())
    cases.extend(gen_phone_number())
    cases.extend(gen_other_pii())
    cases.extend(gen_hard_negatives())
    cases.extend(gen_clean_sentences())

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CASES_PATH.open("w", encoding="utf-8") as fh:
        for case in cases:
            fh.write(json.dumps(case, ensure_ascii=False) + "\n")

    by_type: dict[str, int] = {}
    for case in cases:
        entities = case.get("entities")
        if isinstance(entities, list):
            for e in entities:
                if isinstance(e, dict):
                    t = str(e.get("type", "unknown"))
                    by_type[t] = by_type.get(t, 0) + 1

    clean_count = sum(1 for c in cases if not c.get("entities"))
    print(f"Generated {len(cases)} cases -> {CASES_PATH}")
    print(f"Clean/negative cases: {clean_count}")
    print("Gold entities by type:", json.dumps(by_type, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
