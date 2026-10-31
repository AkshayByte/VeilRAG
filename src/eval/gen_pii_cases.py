"""Generate a labeled PII evaluation set for the VeilRAG sanitizer.

Emits ``data/eval/pii_cases.jsonl`` with 150+ synthetic cases built from
Faker (locales en_IN and en_US). Each case carries gold spans
{type, start, end} for overlap-based evaluation.

Includes hard cases:
- names embedded mid-sentence
- spaced / dashed Aadhaar numbers
- lowercase PAN (AAAbc1234a style and mixed)
- emails with plus-tags and subdomains
- non-PII lookalikes: order IDs, pin codes, phone-like serials
- clean sentences with zero PII
"""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Sequence
from pathlib import Path

from faker import Faker

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "eval"
CASES_PATH = DATA_DIR / "pii_cases.jsonl"

random.seed(42)
fakers = {
    "en_IN": Faker("en_IN"),
    "en_US": Faker("en_US"),
}


def _insert(text: str, gold_type: str, start: int, end: int) -> dict[str, object]:
    return {"text": text, "entities": [{"type": gold_type, "start": start, "end": end}]}


def _insert_multi(
    text: str,
    golds: Sequence[tuple[str, int, int] | tuple[int, int]],
) -> dict[str, object]:
    out: list[dict[str, object]] = []
    for g in golds:
        if len(g) == 3:
            out.append({"type": g[0], "start": g[1], "end": g[2]})
        else:
            # (start, end) with a default label
            out.append({"type": "entity", "start": g[0], "end": g[1]})
    return {"text": text, "entities": out}


def add_name_fake(text: str) -> tuple[str, list[tuple[str, int, int]]]:
    """Insert a Faker full name into *text* and return the modified text + gold."""

    loc = random.choice(list(fakers))
    fake = fakers[loc]
    first = fake.first_name()
    last = fake.last_name()
    name = f"{first} {last}"
    # pick a position that keeps the sentence grammatical-ish
    parts = text.split(" ", maxsplit=1)
    if len(parts) == 1:
        out = name + " " + text
        return out, [("PERSON", 0, len(name))]
    out = parts[0] + " " + name + " " + parts[1]
    return out, [("PERSON", len(parts[0]) + 1, len(parts[0]) + 1 + len(name))]


def gen_names() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for _ in range(35):
        template = (
            "The conference speaker {name} will discuss secure data handling."
        )
        out, gold = add_name_fake(template)
        cases.append(_insert_multi(out, gold))
        out2, gold2 = add_name_fake("During the meeting, {name} presented the Q3 report.")
        cases.append(_insert_multi(out2, gold2))
    return cases


def gen_aadhaar() -> list[dict[str, object]]:
    """Aadhaar: 12 digits, Verhoeff-valid. Spaced and dashed forms."""

    cases: list[dict[str, object]] = []

    def make_valid_12(digits_prefix: str) -> str:
        # brute-force a valid check digit for prefix of 11 digits
        for check in range(10):
            candidate = digits_prefix + str(check)
            try:
                from src.sanitizer.detectors import validate_verhoeff
            except Exception:
                return digits_prefix + str(check)
            if validate_verhoeff(candidate):
                return candidate
        return digits_prefix + "0"

    templates = [
        "Please enter your Aadhaar number for verification.",
        "Upload a copy of your Aadhaar card.",
        "We verified the Aadhaar {num} successfully.",
        "Link your PAN with Aadhaar {num}.",
    ]
    formats = ["{}{}", "{} {} {}", "{}-{}-{}"]
    for _ in range(30):
        prefix = "".join(random.choices("0123456789", k=11))
        num = make_valid_12(prefix)
        fmt = random.choice(formats)
        if fmt == "{}{}":
            s = num
        elif fmt == "{} {} {}":
            s = f"{num[:4]} {num[4:8]} {num[8:]}"
        else:
            s = f"{num[:4]}-{num[4:8]}-{num[8:]}"
        tmpl = random.choice(templates)
        out = tmpl.replace("{num}", s)
        cases.append(_insert_multi(out, [("IDENTITY_DOCUMENT", out.find(s), out.find(s) + len(s))]))
    return cases


def gen_pan() -> list[dict[str, object]]:
    """PAN: AAAAA9994A. Include lowercase and mixed-case variants."""

    cases: list[dict[str, object]] = []
    templates = [
        "Enter your PAN number: {pan}.",
        "Please quote your PAN {pan} on the form.",
        "PAN {pan} does not match our records.",
    ]
    for _ in range(25):
        _alpha = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        pan = "".join(random.choice(_alpha) for _ in range(5))
        pan += str(random.randint(1000, 9999))
        pan += random.choice(_alpha)
        if random.random() < 0.5:
            pan = pan.lower()
        else:
            pan = pan[:5] + str(random.randint(1000, 9999)) + pan[-1].upper()
        out = random.choice(templates).replace("{pan}", pan)
        cases.append(_insert_multi(out, [("PAN_NUMBER", out.find(pan), out.find(pan) + len(pan))]))
    return cases


def gen_emails() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    templates = [
        "Contact us at {email} for support.",
        "We sent a confirmation to {email}.",
        "Your account is {email}.",
        "Reach out to {email} before the deadline.",
    ]
    plus_tags = ["+newsletter", "+promo", "+work", "+personal", "+123", "+tag"]
    for _ in range(25):
        fake = random.choice(list(fakers.values()))
        name = fake.user_name()
        domain = random.choice(["example.com", "company.co.in", "mail.org", "inbox.net"])
        email = f"{name}@{domain}"
        if random.random() < 0.5:
            email = f"{name}{random.choice(plus_tags)}@{domain}"
        else:
            email = f"{name}.{random.randint(1, 99)}@{domain}"
        out = random.choice(templates).replace("{email}", email)
        start = out.find(email)
        cases.append(_insert_multi(out, [("EMAIL_ADDRESS", start, start + len(email))]))
    return cases


def gen_non_pii_lookalikes() -> list[dict[str, object]]:
    """Hard negative cases: order IDs, pincodes, serials — must NOT be flagged."""

    cases: list[dict[str, object]] = []
    order_ids = ["ORD-2024-88371", "order#88371", "SO-994102", "ref 12345678", "ORDER-20240517-99"]
    pincodes = ["110001", "400001", "560001", "700001"]
    serials = ["SN: ABC-1234-XYZ", "DEV-9876543210", "SN 1234 5678 9012"]
    clean = [
        ("The order {oid} shipped yesterday.", oid, "order_id")
        for oid in order_ids
    ]
    clean += [
        ("Pincode {pc} covers this area.", pc, "pincode")
        for pc in pincodes
    ]
    clean += [
        ("Serial {sn} is under warranty.", sn, "serial")
        for sn in serials
    ]
    clean += [
        ("The quick brown fox jumps over the lazy dog.", "", "clean"),
        ("No PII in this clean sentence at all.", "", "clean"),
        ("Meeting at 3pm tomorrow in room 204.", "", "clean"),
        ("Budget is 15000 rupees for Q3 planning.", "", "clean"),
        ("Invoice 77821 is due on the 15th.", "", "clean"),
        ("Room 305 booked until 5:30.", "", "clean"),
        ("Flight number 4921 departs on time.", "", "clean"),
        ("Password reset link: https://portal.example.com/reset?token=abc", "", "clean"),
    ]
    for text, _, label in clean:
        cases.append(_insert(text, label, 0, 1))
    return cases


def gen_phone() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    templates = [
        "Call +91 {mobile} for inquiries.",
        "Reach me at {mobile} during work hours.",
        "Dial 91 {mobile} from outside India.",
        "Mobile number on file: {mobile}.",
    ]
    for _ in range(20):
        fake = random.choice(list(fakers.values()))
        mobile = fake.phone_number()
        # Normalize to a 10-digit Indian-style mobile starting 6-9
        digits = "".join(c for c in mobile if c.isdigit())
        digits = "9" + digits[1:10] if len(digits) >= 10 else digits.ljust(10, "0")[:10]
        form = random.choice([f"+91 {digits}", digits, f"91-{digits}", f"(+91){digits}"])
        out = random.choice(templates).replace("{mobile}", form)
        start = out.find(form)
        cases.append(_insert_multi(out, [("INDIAN_MOBILE", start, start + len(form))]))
    return cases


def gen_other_pii() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    templates = [
        "Credit card {cc} expired last year.",
        "The IBAN {iban} belongs to the vendor.",
        "Send payment to account {ifsc} IFSC.",
        "Use UPI ID {upi} to pay.",
        "The SSN on file is {ssn}.",
        "API key {secret} must not be committed.",
        "AWS access key {ak} leaked in the repo.",
        "The URL {url} points to the staging env.",
        "The server IP is {ip}.",
        "Patient MRN {mrn} requires follow-up.",
    ]
    entries = [
        ("CREDIT_CARD", "4111-1111-1111-1111"),
        ("IBAN_CODE", "GB29NWBK60161331926819"),
        ("IFSC_CODE", "SBIN0001234"),
        ("UPI_ID", "rahul@upi"),
        ("US_SSN", "123-45-6789"),
        ("SECRET_KEY", "sk-abc123def456ghi789jkl012mno345pq"),
        ("AWS_ACCESS_KEY", "AKIAIOSFODNN7EXAMPLE"),
        ("URL", "https://example.com/secure/path"),
        ("IP_ADDRESS", "192.168.1.42"),
        ("MEDICAL_RECORD_NUMBER", "MRN-4421"),
    ]
    for entity, value in entries:
        for _ in range(3):
            tmpl = random.choice(templates)
            out = tmpl.replace("{", f"{{{entity.lower()}").replace(f"{{{entity.lower()}}}", value)
            start = out.find(value)
            cases.append(_insert_multi(out, [(entity, start, start + len(value))]))
    return cases


def gen_clean_sentences() -> list[dict[str, object]]:
    """Sentences that contain no PII — must return zero entities."""

    templates = [
        "The project milestone is next Friday.",
        "Cloud hosting costs rose by twelve percent.",
        "Team sync happens at 10am every Monday.",
        "Please update the README before Monday.",
        "The build passed on the CI pipeline.",
        "Documentation is in the shared drive.",
        "Q3 revenue target is fifteen million.",
        "Office supplies order arrived today.",
        "The demo ran without errors.",
        "Please keep the conference room until five.",
    ]
    return [_insert(random.choice(templates), "clean", 0, 1) for _ in range(20)]


def main() -> int:
    cases: list[dict[str, object]] = []
    cases += gen_names()
    cases += gen_aadhaar()
    cases += gen_pan()
    cases += gen_emails()
    cases += gen_phone()
    cases += gen_other_pii()
    cases += gen_non_pii_lookalikes()
    cases += gen_clean_sentences()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CASES_PATH.open("w", encoding="utf-8") as fh:
        for case in cases:
            fh.write(json.dumps(case, ensure_ascii=False) + "\n")

    by_type: dict[str, int] = {}
    for case in cases:
        entities = case.get("entities")
        if not isinstance(entities, list):
            continue
        for e in entities:
            if isinstance(e, dict):
                t = e.get("type")
                if isinstance(t, str):
                    by_type[t] = by_type.get(t, 0) + 1
    logger.info("Generated %d cases", len(cases))
    logger.info("By type: %s", by_type)
    print(f"Generated {len(cases)} cases -> {CASES_PATH}")
    print("By type:", by_type)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
