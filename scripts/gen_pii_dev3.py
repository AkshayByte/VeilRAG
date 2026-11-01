"""Generate dev3 evaluation dataset for coverage recognizers in VeilRAG.

Evaluates coverage of newly added privacy gap recognizers:
- DATE_OF_BIRTH
- BANK_ACCOUNT
- ADDRESS (and STREET_ADDRESS)
- UHID (Hospital IDs)

Includes rigorous hard negatives:
- Invoice/due dates and generic agreement dates
- 6-digit OTPs
- Order numbers and tracking identifiers
- Phone-like 10-digit numbers without banking context
- 9-digit quantities and metric units
- Addresses without 6-digit PIN codes
- Standalone postal PIN codes without address premises prefixes
- Clean corporate and technical prose
"""

from __future__ import annotations

import json
import logging
import random
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

DATA_DIR = REPO_ROOT / "data" / "eval"
DEV3_PATH = DATA_DIR / "pii_dev3.jsonl"

RANDOM_SEED = 77123
random.seed(RANDOM_SEED)


def _make_case(text: str, entities: list[tuple[str, int, int]]) -> dict[str, object]:
    """Build a labeled case dictionary with verified span boundaries."""
    spans: list[dict[str, object]] = []
    for entity_type, start, end in entities:
        if start < 0 or end <= start or end > len(text):
            raise ValueError(f"Invalid span [{start}:{end}] for text length {len(text)}")
        spans.append(
            {
                "type": entity_type,
                "start": start,
                "end": end,
                "value": text[start:end],
            }
        )
    return {"text": text, "entities": spans}


def gen_dob_cases() -> list[dict[str, object]]:
    """Generate positive DATE_OF_BIRTH cases."""
    cases: list[dict[str, object]] = []

    dobs = [
        ("14-08-1988", "dd-mm-yyyy"),
        ("19/03/1990", "dd/mm/yyyy"),
        ("22-11-1985", "dd-mm-yyyy"),
        ("03-05-1992", "dd-mm-yyyy"),
        ("20-07-1984", "dd-mm-yyyy"),
        ("11-12-1971", "dd-mm-yyyy"),
        ("28-09-1994", "dd-mm-yyyy"),
        ("04-10-1969", "dd-mm-yyyy"),
        ("15-06-1996", "dd-mm-yyyy"),
        ("18-01-1987", "dd-mm-yyyy"),
        ("09-12-1981", "dd-mm-yyyy"),
        ("25-04-1965", "dd-mm-yyyy"),
        ("12-07-1993", "dd-mm-yyyy"),
        ("22-03-1979", "dd-mm-yyyy"),
        ("08-11-1995", "dd-mm-yyyy"),
        ("19 March 1990", "textual"),
        ("24 January 1980", "textual"),
        ("15 June 1996", "textual"),
        ("14 August 1988", "textual"),
        ("20 July 1984", "textual"),
        ("14-Aug-1988", "hyphen_month"),
        ("05-May-1991", "hyphen_month"),
        ("28.09.1994", "dotted"),
        ("12.07.1993", "dotted"),
    ]

    templates = [
        "Patient identity verified with date of birth {val}.",
        "Applicant record confirms DOB: {val} in national database.",
        "The employee was born on {val} according to service register.",
        "Guarantor date of birth {val} authenticated via birth certificate.",
        "Customer registered birth date {val} on the onboarding portal.",
        "D.O.B: {val} verified against matriculation certificate.",
        "Policyholder born on {val} is eligible for senior citizen rider.",
        "KYC dossier documents date of birth {val} for pension entitlement.",
    ]

    for i, (dob_val, _) in enumerate(dobs):
        tmpl = templates[i % len(templates)]
        text = tmpl.format(val=dob_val)
        start = text.index(dob_val)
        end = start + len(dob_val)
        cases.append(_make_case(text, [("DATE_OF_BIRTH", start, end)]))

    return cases


def gen_bank_account_cases() -> list[dict[str, object]]:
    """Generate positive BANK_ACCOUNT cases."""
    cases: list[dict[str, object]] = []

    accounts = [
        "50100234918231",
        "20489912034",
        "004501589123",
        "50100458921345",
        "000705012398",
        "914010034567891",
        "50100984512390",
        "30981245091",
        "12300015009823",
        "50100778899123",
        "10040156908123",
        "10450500129845",
        "50100445566778",
        "30089124501",
        "003901589124",
        "98765432101234",
        "112233445566",
        "998877665544332",
        "12345678901",
        "445566778899001",
    ]

    templates = [
        "Monthly salary credited to corporate salary account {val}.",
        "Disbursement proceeds transferred to savings account {val}.",
        "Refund issued to account {val} via electronic clearing.",
        "Standing instruction registered against current account {val}.",
        "Clearance credited via NEFT to account {val} successfully.",
        "Claim reimbursement remitted to savings account {val}.",
        "Designated account {val} verified for direct tax debit.",
        "Escrow deposit held in designated account {val} until completion.",
    ]

    for i, acc in enumerate(accounts):
        tmpl = templates[i % len(templates)]
        text = tmpl.format(val=acc)
        start = text.index(acc)
        end = start + len(acc)
        cases.append(_make_case(text, [("BANK_ACCOUNT", start, end)]))

    return cases


def gen_address_cases() -> list[dict[str, object]]:
    """Generate positive ADDRESS cases."""
    cases: list[dict[str, object]] = []

    addresses = [
        "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066",
        "House No 12, Sector 18, Vashi, Navi Mumbai, Maharashtra 400703",
        "Tower B Apt 901, Cyber City Residency, DLF Phase 2, Gurugram, Haryana 122002",
        "House 45, Koramangala 4th Block, 80 Feet Road, Bengaluru, Karnataka 560034",
        "Plot 88, Okhla Industrial Area Phase 3, New Delhi 110020",
        "Flat 201 Sri Sai Residency, Madhapur, Hyderabad, Telangana 500081",
        "Flat 102 Crystal Arcade, Indiranagar 100 Feet Road, Bengaluru, Karnataka 560038",
        "B-203 Sunrise Towers, Chembur East, Mumbai, Maharashtra 400071",
        "C-44 Greater Kailash 1, New Delhi 110048",
        "House 78, 5th Cross, Malleshwaram, Bengaluru, Karnataka 560003",
        "Door No 14, 2nd Main Road, Gandhi Nagar, Adyar, Chennai, Tamil Nadu 600020",
        "Plot 18, Block EP & GP, Sector V, Salt Lake, Kolkata, West Bengal 700091",
        "Flat 301 Shanti Nivas, 14th Main, JP Nagar 2nd Phase, Bengaluru, Karnataka 560078",
        "Bait-ul-Salam, Marine Drive, Ernakulam, Kochi, Kerala 682031",
        "Flat 404 Green Acres, Baner Road, Pune, Maharashtra 411045",
        "Apartment 5B, Skyline Residency, MG Road, Bengaluru, Karnataka 560001",
        "Suite 300, Prestige Tech Park, Marathahalli, Bengaluru, Karnataka 560103",
        "Building 4, Mindspace IT Park, Hitec City, Hyderabad, Telangana 500081",
        "House 108, Model Town, Jalandhar, Punjab 144003",
        "Plot 22, MIDC Industrial Zone, Andheri East, Mumbai, Maharashtra 400093",
    ]

    templates = [
        "Primary residential domicile is logged as {val}.",
        "Communication address recorded in profile is {val}.",
        "Physical inspection conducted at registered premises: {val}.",
        "Guarantor verified home address: {val}.",
        "Official dispatch packet delivered to {val}.",
    ]

    for i, addr in enumerate(addresses):
        tmpl = templates[i % len(templates)]
        text = tmpl.format(val=addr)
        start = text.index(addr)
        end = start + len(addr)
        cases.append(_make_case(text, [("ADDRESS", start, end)]))

    return cases


def gen_uhid_cases() -> list[dict[str, object]]:
    """Generate positive Hospital ID / UHID cases."""
    cases: list[dict[str, object]] = []

    hosp_ids = [
        "UH-889021",
        "UH-120934",
        "UH-554109",
        "UH-908123",
        "IP-2026-MED-77412",
        "IP-2026-SURG-11045",
        "IP-2026-ORTHO-88912",
        "IP-2026-PED-33410",
        "FH-CARD-2026-MUM-901",
        "MAN-ORTHO-2026-DEL-331",
        "APO-MED-2026-BLR-502",
        "MAX-SURG-2026-DEL-104",
        "MRN-882109",
        "MRN-441203",
        "MRN-773401",
        "PID-559012",
        "PID-992143",
        "PID-104822",
    ]

    templates = [
        "Inpatient registration completed under UHID: {val}.",
        "Patient medical folder references clinical identifier {val}.",
        "Emergency admission dossier created with record code {val}.",
        "Laboratory pathology test linked to identifier {val}.",
    ]

    for i, hid in enumerate(hosp_ids):
        tmpl = templates[i % len(templates)]
        text = tmpl.format(val=hid)
        start = text.index(hid)
        end = start + len(hid)
        cases.append(_make_case(text, [("UHID", start, end)]))

    return cases


def gen_hard_negatives() -> list[dict[str, object]]:
    """Generate comprehensive hard negatives for coverage recognizers."""
    cases: list[dict[str, object]] = []

    # 1. Generic dates without DOB context (invoices, effective dates, notice periods, terms)
    date_negatives = [
        "Invoice INV-2026-088 dated 15/03/2026 is due for settlement on 30/03/2026.",
        "The contractual master services agreement takes effect from 01-04-2026.",
        "Employee resignation notice period requires 60 calendar days starting 15-05-2026.",
        "Audited quarterly financial statements published on 24th January 2026.",
        "Software subscription license expires on 31-12-2026 unless renewed.",
        "Delivery scheduled between 10/02/2026 and 14/02/2026 via road express.",
        "The warranty coverage period concludes on 15 March 2027.",
        "Statutory GST compliance filing window opens on 20-04-2026.",
        "Scheduled maintenance interval runs from 01.06.2026 through 05.06.2026.",
        "Tender submission deadline is strictly enforced for 18-08-2026.",
    ]

    # 2. 6-digit OTPs and verification codes (NOT PIN codes, NOT bank accounts)
    otp_negatives = [
        "Your secret one-time password for transaction authorization is 582104.",
        "Enter verification code 918234 to authenticate your session.",
        "Mobile banking login OTP 645109 expires in three minutes.",
        "Two-factor authentication code 309812 delivered via SMS.",
        "Security passkey token 771230 confirmed on device.",
        "Confirmation passcode 440192 required to proceed with transfer.",
    ]

    # 3. Order numbers and tracking identifiers (NOT bank accounts)
    order_negatives = [
        "Purchase order PO-9876543210 has been approved by the procurement desk.",
        "Logistics tracking number 123456789012 indicates package arrived at hub.",
        "E-commerce order #8899001122 is packaged and ready for dispatch.",
        "Waybill consignment 445566778899 is currently in transit.",
        "Support helpdesk ticket 9012345678 assigned to tier-two engineering.",
        "Shipping manifest barcode 1029384756 scanned at container freight station.",
    ]

    # 4. Phone-like 10-digit numbers without banking context
    phone_negatives = [
        "For customer inquiries, reach out to corporate helpline 9822011223.",
        "Direct emergency triage switchboard reachable at 8877665544.",
        "Toll-free technical assistance line open 24/7 at 7766554433.",
        "Facilities dispatch coordinator phone extension is 9123456780.",
        "Vendor support desk representative contact is 6677889900.",
    ]

    # 5. 9-digit quantities and metric units (NOT bank accounts)
    quantity_negatives = [
        "Total production output exceeded 125000000 units during annual operations.",
        "The municipal reservoir holds 500000000 liters of potable water reserves.",
        "High-performance quantum benchmark completed in 100000000 cycles.",
        "The sensor measured radiation intensity at 450000000 picometers.",
        "Microcontroller buffer processed exactly 250000000 bytes without error.",
        "Data transmission link capacity rated at 1000000000 bits per second.",
    ]

    # 6. Addresses without PIN code (NOT valid ADDRESS span per protocol)
    address_without_pin_negatives = [
        "Our branch is located at Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru.",
        "Corporate headquarters situated at Plot 88, Okhla Industrial Area Phase 3, New Delhi.",
        "Employee resides at House No 12, Sector 18, Vashi, Navi Mumbai.",
        "Consultant office based in Tower B Apt 901, Cyber City Residency, Gurugram.",
        "Regional sales depot at Plot 18, Block EP & GP, Sector V, Salt Lake, Kolkata.",
        "Inspection visited Door No 14, 2nd Main Road, Gandhi Nagar, Adyar, Chennai.",
    ]

    # 7. Postal PIN codes in general context without Flat/House/Plot prefixes
    pin_negatives = [
        "Delivery vehicle routed to Chennai T Nagar PIN 600017.",
        "Registered parcel will be delivered to New Delhi GPO PIN 110001.",
        "Consignment addressed to Bengaluru Whitefield PIN 560066.",
        "Sub-post office located near Mumbai Bandra Kurla Complex PIN 400051.",
        "Mail sorting facility in Kolkata Salt Lake PIN 700091.",
        "Express courier dispatched to Hyderabad Madhapur PIN 500081.",
        "Pune Kothrud postal branch PIN 411038 processed the letter.",
        "Ahmedabad Navrangpura postal center PIN 380009 received parcel dispatch.",
    ]

    # 8. Clean corporate, engineering, and administrative prose
    clean_prose = [
        "Modern cloud architectures rely on microservices, service meshes, and distributed tracing.",
        "The audit committee reviewed internal financial controls and risk management frameworks.",
        "Continuous integration pipelines enforce automated linting, type-checking, and unit tests.",
        "Database administrators executed routine vacuuming and query index maintenance tasks.",
        "Enterprise network topology isolates development environments from production workloads.",
        "Agile delivery squads conduct bi-weekly sprint reviews and retrospective meetings.",
        "Cryptographic hash algorithms ensure message integrity and tamper-evident logging.",
        "The executive summary highlights strategic expansion in international commerce.",
        "Load balancers dynamically route inbound HTTP requests to healthy compute instances.",
        "Security awareness training covers phishing defense, credential hygiene, and access control.",
    ]

    all_negatives = (
        date_negatives
        + otp_negatives
        + order_negatives
        + phone_negatives
        + quantity_negatives
        + address_without_pin_negatives
        + pin_negatives
        + clean_prose
    )

    for text in all_negatives:
        cases.append(_make_case(text, []))

    return cases


def generate_all_dev3_cases() -> list[dict[str, object]]:
    """Assemble the complete dev3 evaluation dataset."""
    cases: list[dict[str, object]] = []
    cases.extend(gen_dob_cases())  # 24 positives
    cases.extend(gen_bank_account_cases())  # 20 positives
    cases.extend(gen_address_cases())  # 20 positives
    cases.extend(gen_uhid_cases())  # 18 positives
    cases.extend(gen_hard_negatives())  # 65 hard negatives
    return cases


def main() -> int:
    """Generate and serialize the dev3 evaluation dataset."""
    logging.basicConfig(level=logging.INFO)
    DEV3_PATH.parent.mkdir(parents=True, exist_ok=True)

    cases = generate_all_dev3_cases()
    clean_count = sum(1 for c in cases if not c.get("entities"))
    pii_count = len(cases) - clean_count

    with open(DEV3_PATH, "w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    logger.info("Generated %d dev3 cases to %s", len(cases), DEV3_PATH)
    logger.info("  PII positive cases: %d", pii_count)
    logger.info("  PII-free hard negatives: %d", clean_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

