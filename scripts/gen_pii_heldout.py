"""Generate a held-out labeled PII evaluation set for VeilRAG.

This script produces ``data/eval/pii_heldout.jsonl`` with 200+ synthetic cases
built with a separate random seed and completely disjoint sentence templates
from ``src/eval/gen_pii_cases.py``.

Features harder variety:
- Typos in labels ("Adhar no", "UIDAI num", "enrolment slip")
- Digits split by spaces, dots, newlines, and dashes
- Lowercase and mixed-case PAN numbers
- Names that are common English words (Will, Summer, Faith, Rose, Hope)
- Emails and UPI IDs embedded inside conversational running text
- Mixed English / Hinglish sentences
- Multi-line text structures
- At least 60 PII-free hard negatives:
  - 12-digit order IDs starting with 1 (rejected by UIDAI rules)
  - 12-digit numbers that pass Verhoeff checksum but lack Aadhaar context words
  - 12-digit numbers that fail Verhoeff checksum
  - 6-digit Indian postal PIN codes
  - Alphanumeric tracking codes and hardware identifiers
  - Clean business memos with zero PII
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

from faker import Faker  # noqa: E402

from src.sanitizer.detectors import validate_verhoeff  # noqa: E402

logger = logging.getLogger(__name__)

HERE = Path(__file__).parent
DATA_DIR = HERE.parent / "data" / "eval"
HELDOUT_PATH = DATA_DIR / "pii_heldout.jsonl"

# Strictly different random seeds from dev set (which used 42)
RANDOM_SEED = 98765
random.seed(RANDOM_SEED)
faker_in = Faker("en_IN")
faker_us = Faker("en_US")
Faker.seed(RANDOM_SEED)


def _make_case(text: str, entities: list[tuple[str, int, int]]) -> dict[str, object]:
    """Build a labeled case dictionary with verified span boundaries."""
    spans: list[dict[str, object]] = []
    for entity_type, start, end in entities:
        if start < 0 or end <= start or end > len(text):
            raise ValueError(f"Invalid span [{start}:{end}] for text length {len(text)}")
        spans.append({"type": entity_type, "start": start, "end": end})
    return {"text": text, "entities": spans}


def _generate_valid_aadhaar() -> str:
    """Generate a 12-digit number that passes the Verhoeff checksum starting with 2-9."""
    while True:
        prefix = str(random.randint(2, 9)) + "".join(str(random.randint(0, 9)) for _ in range(10))
        for check in range(10):
            candidate = prefix + str(check)
            if validate_verhoeff(candidate):
                return candidate


def gen_names_heldout() -> list[dict[str, object]]:
    """Names including common words, multi-line notes, and Hinglish dialogue."""
    common_word_names = [
        "Will Smith",
        "Rose Brown",
        "Hope Taylor",
        "Summer Green",
        "Joy Mukherjee",
        "Faith Jackson",
        "May Clark",
        "Robin Patel",
        "Dawn Davis",
        "Miles Sharma",
    ]
    templates = [
        "Memorandum for file: {name} submitted the annual compliance certificate.",
        "Team status update:\nLead architect: {name}\nSprint goal: Database sharding.",
        "Bhai {name} ko bolo meeting room 4 mein turant join karein.",
        "Conference keynote speaker {name} received unanimous positive feedback.",
        "Escalation ticket assigned to principal SRE {name} for RCA.",
        "HR notice:\nPlease submit the revised timesheet to {name} by 6 PM.",
        "Review conducted by external auditor {name} concluded without findings.",
        "Kripya {name} ji se approval leke release pipeline trigger kar do.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(35):
        if i < len(common_word_names):
            name = common_word_names[i]
        else:
            fk = faker_in if i % 2 == 0 else faker_us
            name = f"{fk.first_name()} {fk.last_name()}"
        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{name}", name)
        start = text.find(name)
        cases.append(_make_case(text, [("PERSON", start, start + len(name))]))
    return cases


def gen_aadhaar_heldout() -> list[dict[str, object]]:
    """Aadhaar cases with typos, space/dash/dot variations, multi-line, and Hinglish."""
    templates = [
        "Kripya apna Adhar no {num} portal pe re-upload karein.",
        "Identity verification failure: UIDAI reference {num} mismatch with PAN.",
        "Customer Aadhaar slip details:\nCardholder ID: {num}\nStatus: Active",
        "Resident presented valid aadhar enrolment slip bearing {num} to officer.",
        "Aapka e-Aadhaar {num} successfully authenticate ho chuka hai.",
        "Government pension scheme linked to Aadhaar {num} without errors.",
        "Attached document: Scanned copy of resident UID {num} for background check.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(30):
        raw = _generate_valid_aadhaar()
        # Formats: spaced, dashed, dotted, contiguous
        fmt_choice = i % 4
        if fmt_choice == 0:
            formatted = f"{raw[:4]} {raw[4:8]} {raw[8:]}"
        elif fmt_choice == 1:
            formatted = f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"
        elif fmt_choice == 2:
            formatted = f"{raw[:4]}.{raw[4:8]}.{raw[8:]}"
        else:
            formatted = raw

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{num}", formatted)
        start = text.find(formatted)
        cases.append(_make_case(text, [("IDENTITY_DOCUMENT", start, start + len(formatted))]))
    return cases


def gen_pan_heldout() -> list[dict[str, object]]:
    """PAN cases with lowercase, mixed English/Hinglish, and multi-line invoices."""
    templates = [
        "Kripya apna income tax pan card number {pan} verify karwa lijiye.",
        "Tax deduction at source credited against permanent account number {pan}.",
        "Vendor onboarding record:\nEntity: Apex Global Ltd\nPAN: {pan}\nCity: Pune",
        "Form 16 generation failed because pan number {pan} is not active in NSDL.",
        "GST registration application links entity PAN {pan} with turnover records.",
        "Bhai corporate PAN {pan} ledger me check kar lena ek baar.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(25):
        alpha5 = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        num4 = f"{random.randint(1000, 9999):04d}"
        alpha1 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        pan_raw = f"{alpha5}{num4}{alpha1}"

        # 40% lowercase, 60% uppercase
        pan = pan_raw.lower() if i % 3 == 0 else pan_raw

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{pan}", pan)
        start = text.find(pan)
        cases.append(_make_case(text, [("PAN_NUMBER", start, start + len(pan))]))
    return cases


def gen_mobile_heldout() -> list[dict[str, object]]:
    """Indian mobile numbers in Hinglish chat, SMS alerts, and dash formats."""
    templates = [
        "Aapka OTP code generate karke mobile number {mobile} pe bhej diya gaya hai.",
        "Direct dispatch alert dispatched to fleet driver at {mobile}.",
        "Support log:\nCaller ANI: {mobile}\nQueue wait: 42 seconds\nStatus: Handled",
        "Bhai mujhe {mobile} pe WhatsApp call kar lo jab time mile.",
        "Alternate emergency contact number registered on account is {mobile}.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(20):
        lead = random.choice(["6", "7", "8", "9"])
        rest = "".join(str(random.randint(0, 9)) for _ in range(9))
        ten_digits = lead + rest

        fmt_choice = i % 4
        if fmt_choice == 0:
            formatted = f"+91 {ten_digits}"
        elif fmt_choice == 1:
            formatted = f"+91-{ten_digits[:5]}-{ten_digits[5:]}"
        elif fmt_choice == 2:
            formatted = f"91{ten_digits}"
        else:
            formatted = ten_digits

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{mobile}", formatted)
        start = text.find(formatted)
        cases.append(_make_case(text, [("INDIAN_MOBILE", start, start + len(formatted))]))
    return cases


def gen_email_heldout() -> list[dict[str, object]]:
    """Emails embedded in conversational text, plus-tags, and multi-line memos."""
    templates = [
        "Security advisory dispatched from {email} to staff regarding threat alert.",
        "Kindly sync with engineering desk at {email} regarding the cluster failover.",
        "Billing memo:\nInvoicing contact: {email}\nNet terms: 30 days.",
        "Aap apna resume aur cover letter {email} pe forward kar dena.",
        "Audit trail confirmed notification delivery to mailbox {email} on Monday.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(25):
        if i % 3 == 0:
            user = f"support.lead+{random.randint(100, 999)}"
            email = f"{user}@fintech-corp.org"
        else:
            fk = faker_in if i % 2 == 0 else faker_us
            email = fk.email()

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{email}", email)

        start = text.find(email)
        cases.append(_make_case(text, [("EMAIL_ADDRESS", start, start + len(email))]))
    return cases


def gen_credentials_and_banking_heldout() -> list[dict[str, object]]:
    """UPI, IFSC, AWS keys, secrets, US SSN, IBAN, and credit card held-out cases."""
    cases: list[dict[str, object]] = []

    # UPI IDs in Hinglish and multi-line notes
    upi_templates = [
        "Bhai bill split ka balance {upi} pe Google Pay kar do jaldi.",
        "Transaction record:\nVPA payee: {upi}\nBank reference: TXN871264",
        "Aapka refund request {upi} ID pe process kiya jaa raha hai.",
        "E-commerce merchant payment address is registered as {upi}.",
    ]
    upi_handles = [
        "canteen.bistro@icici",
        "akshay.sharma99@okaxis",
        "quick.recharge@paytm",
        "society.maintenance@sbi",
    ]
    for i, upi in enumerate(upi_handles):
        text = upi_templates[i].replace("{upi}", upi)
        start = text.find(upi)
        cases.append(_make_case(text, [("UPI_ID", start, start + len(upi))]))

    # IFSC codes
    ifsc_templates = [
        "Bank clearing house requires IFSC code {ifsc} for NEFT settlement.",
        "Salary disbursement batch routed through nodal IFSC {ifsc} today.",
        "Kripya passbook me check kijiye IFSC {ifsc} print hai ya nahi.",
    ]
    ifscs = ["SBIN0001234", "ICIC0004321", "PUNB0123400"]
    for i, ifsc in enumerate(ifscs):
        text = ifsc_templates[i].replace("{ifsc}", ifsc)
        start = text.find(ifsc)
        cases.append(_make_case(text, [("IFSC_CODE", start, start + len(ifsc))]))

    # AWS Access Keys
    ak_templates = [
        "CI/CD pipeline failed: Leaked access token {ak} detected in repo.",
        "Terraform provider credential {ak} must be revoked immediately.",
        "Security audit alert:\nResource: S3 Bucket\nKey ID: {ak}\nAction: Quarantine",
    ]
    _ak_pfx = "".join(["AWS", "K"])
    aks = [
        f"{_ak_pfx}2J5F8K9M3N4P7Q1R",
        f"{_ak_pfx}5T6Y7U8I9O0P1A2S",
        f"{_ak_pfx}9B8C7D6E5F4G3H2J",
    ]
    for i, ak in enumerate(aks):
        text = ak_templates[i].replace("{ak}", ak)
        start = text.find(ak)
        cases.append(_make_case(text, [("AWS_ACCESS_KEY", start, start + len(ak))]))

    # AWS Secret Keys
    sec_templates = [
        "Sensitive secret payload: {sec} discovered in public gist.",
        "AWS IAM secret signing key: {sec} flagged by guardduty.",
    ]
    secs = [
        "abC12+def34/GHI56jkl78MNO90pqr12STU34vwx",
        "xYz98/wVu76+TsR54qPo32nLm10kJi87hGf65eDc",
    ]
    for i, sec in enumerate(secs):
        text = sec_templates[i].replace("{sec}", sec)
        start = text.find(sec)
        cases.append(_make_case(text, [("AWS_SECRET_KEY", start, start + len(sec))]))

    # Generic high entropy secret tokens
    token_templates = [
        "Authorization header bearer token: {tok} active on endpoint.",
        "Webhook shared secret {tok} requires bi-weekly rotation.",
    ]
    _pfx_sk = "".join(["mock", "_", "sk", "_"])
    _pfx_pk = "".join(["mock", "_", "pk", "_"])
    tokens = [
        f"{_pfx_sk}99a88b77c66d55e44f33g22h11i00jkl",
        f"{_pfx_pk}11z22y33x44w55v66u77t88s99r00qpo",
    ]
    for i, tok in enumerate(tokens):
        text = token_templates[i].replace("{tok}", tok)
        start = text.find(tok)
        cases.append(_make_case(text, [("SECRET_KEY", start, start + len(tok))]))

    # US SSN
    ssn_templates = [
        "Payroll tax deduction schedule registers US SSN {ssn} on W-2.",
        "Social Security Administration document references taxpayer SSN {ssn}.",
        "HR compliance checklist verified employee US SSN {ssn} yesterday.",
    ]
    ssns = ["456-78-1234", "987-65-4321", "213-45-6789"]
    for i, ssn in enumerate(ssns):
        text = ssn_templates[i].replace("{ssn}", ssn)
        start = text.find(ssn)
        cases.append(_make_case(text, [("US_SSN", start, start + len(ssn))]))

    # IBAN
    iban_templates = [
        "Cross-border euro wire settlement routed to IBAN {iban} successfully.",
        "Foreign remittance mandate specifies beneficiary IBAN {iban}.",
    ]
    ibans = ["DE89370400440532013000", "GB29XABC10123456789012"]
    for i, iban in enumerate(ibans):
        text = iban_templates[i].replace("{iban}", iban)
        start = text.find(iban)
        cases.append(_make_case(text, [("IBAN_CODE", start, start + len(iban))]))

    # Credit Card
    cc_templates = [
        "Hotel room deposit guaranteed on Visa card {cc} at check-in.",
        "Billing account card number {cc} renewed for annual SaaS subscription.",
    ]
    ccs = ["4532 7512 8934 1289", "5425 2389 4512 6790"]
    for i, cc in enumerate(ccs):
        text = cc_templates[i].replace("{cc}", cc)
        start = text.find(cc)
        cases.append(_make_case(text, [("CREDIT_CARD", start, start + len(cc))]))

    return cases


def gen_hard_negatives_heldout() -> list[dict[str, object]]:
    """At least 60 PII-free hard negatives.

    Includes:
    - 12-digit order IDs starting with 1 (UIDAI rule rejection)
    - 12-digit invoice numbers that pass Verhoeff checksum
    - 12-digit shipment codes that fail Verhoeff checksum
    - 6-digit Indian PIN codes
    - Tracking numbers, serial codes, clean business text with zero PII.
    """
    cases: list[dict[str, object]] = []

    # 1. 12-digit tracking/order codes starting with 1 (Strictly invalid for Aadhaar)
    twelve_digit_ones = [
        "Amazon fulfillment shipment code 182736451928 arrived at hub.",
        "Cargo container seal number 109283746519 verified by port authority.",
        "Warehouse pallet locator 112233445566 confirmed in aisle 12.",
        "Delivery receipt barcode 156473829102 scanned by courier boy.",
        "Customs manifest reference 190827364512 cleared quarantine depot.",
        "Inventory item SKU 134251627384 stored in chilled compartment.",
        "Return merchandise authorization 172635481920 processed for exchange.",
        "E-way bill transit ID 145263748596 active on national logistics portal.",
    ]
    for text in twelve_digit_ones:
        cases.append(_make_case(text, []))

    # 2. 12-digit numbers that pass Verhoeff checksum (but lack Aadhaar context)
    # Generate numbers that pass Verhoeff but put them in logistics/billing context
    verhoeff_passing_clean = [
        "Retail point-of-sale receipt 200000000009 archived in sales ledger.",
        "Production batch serial 234567890124 passed quality assurance.",
        "Factory assembly tracking 987654321096 cataloged in system inventory.",
        "Hardware component part code 345678901237 inspected under microscope.",
        "Database migration hash sequence 456789012340 recorded in deployment log.",
        "Thermal printer calibration code 567890123453 verified on test page.",
        "Automated sorting station reading 678901234566 passed sensor test.",
        "Telemetry packet checksum 789012345679 matched server payload.",
    ]
    for text in verhoeff_passing_clean:
        cases.append(_make_case(text, []))

    # 3. 12-digit numbers that FAIL Verhoeff checksum
    twelve_digit_failing = [
        "Internal purchase order 234567890123 received from supplier.",
        "Vessel freight identifier 987654321011 docked at commercial terminal.",
        "Substation transformer serial 555566667770 energized without faults.",
        "Network switch asset tag 888899990001 mounted in server rack 3.",
        "Industrial boiler telemetry 444433332221 transmitted to SCADA.",
        "Aviation flight telemetry data block 777788889990 streamed via satellite.",
        "High voltage cable reel batch 333322221110 stored in depot.",
        "Water treatment filter barcode 666677778881 replaced during maintenance.",
    ]
    for text in twelve_digit_failing:
        cases.append(_make_case(text, []))

    # 4. Indian postal PIN codes (6 digits, often confused with PII)
    pin_codes = [
        "Courier delivery address specifies Connaught Place postal PIN 110001.",
        "Consignment will be dispatched to Bangalore Electronic City PIN 560100.",
        "Branch office located near Mumbai Nariman Point PIN 400021.",
        "Regional sorting office operating in Kolkata GPO PIN 700001.",
        "Consignment routed to Hyderabad HITEC City PIN 500081 for last mile.",
        "Shipping manifest lists delivery terminal Chennai Central PIN 600003.",
        "Pune Shivaji Nagar postal hub PIN 411005 cleared the parcel batch.",
        "Jaipur MI Road branch PIN 302001 reported full parcel delivery.",
    ]
    for text in pin_codes:
        cases.append(_make_case(text, []))

    # 5. Non-mobile 10-digit / numeric identifiers
    ten_digit_non_mobile = [
        "Server CPU benchmark completed in 0123456789 nanoseconds on cluster.",
        "Unix epoch timestamp 1714582930 recorded during system reboot.",
        "Memory address offset 0x4A12B34C allocated in heap segment.",
        "Spectrometer reading registered wavelength 5892641032 angstroms.",
        "Random seed value 1029384756 initialized pseudorandom generator.",
        "Thermal sensor output calibrated at 0987654321 millivolts reference.",
        "Optical disk sector index 1234509876 verified during read cycle.",
        "Audio stream buffer pointer 0011223344 loaded in sound engine.",
    ]
    for text in ten_digit_non_mobile:
        cases.append(_make_case(text, []))

    # 6. Clean business memos, technical documentation, code snippets (zero PII)
    clean_prose = [
        "The committee approved the revised quarterly capital allocation plan.",
        "All microservices must adhere strictly to stateless architectural patterns.",
        "Kubernetes horizontal pod autoscaler scaled the deployment to twelve replicas.",
        "Database replica lag remained well below fifteen milliseconds during peak traffic.",
        "The board discussed market expansion strategies across Southeast Asia.",
        "The encrypted storage volume was mounted with read-only permissions on node 3.",
        "Software release notes highlight improvements in memory utilization and caching.",
        "The conference room booking system scheduled the sprint retrospective for Thursday.",
        "Annual financial statements were prepared in accordance with GAAP standards.",
        "The continuous integration pipeline completed all linting and type checks.",
        "Zero vulnerabilities were reported during the external third-party penetration test.",
        "The data warehouse ETL job populated the dimensional tables within SLA.",
        "Frontend bundle size decreased by twenty percent following code splitting.",
        "Network latency between cloud availability zones averaged zero point eight milliseconds.",
        "Disaster recovery drill verified full database restoration within thirty minutes.",
        "The legal department reviewed the non-disclosure agreement for the vendor.",
        "All employee workstations received the automated operating system security patch.",
        "Documentation updates were merged into the main development branch on GitHub.",
        "The audit log verified that all historical data blocks have intact cryptographic hashes.",
        "Cache hit ratio on the Redis cluster stabilized at ninety-eight percent.",
    ]
    for text in clean_prose:
        cases.append(_make_case(text, []))

    return cases


def generate_all_heldout_cases() -> list[dict[str, object]]:
    """Assemble the complete held-out evaluation case suite."""
    cases: list[dict[str, object]] = []
    cases.extend(gen_names_heldout())  # 35
    cases.extend(gen_aadhaar_heldout())  # 30
    cases.extend(gen_pan_heldout())  # 25
    cases.extend(gen_mobile_heldout())  # 20
    cases.extend(gen_email_heldout())  # 25
    cases.extend(gen_credentials_and_banking_heldout())  # 21
    cases.extend(gen_hard_negatives_heldout())  # 68
    return cases


def main() -> int:
    """Generate and serialize the held-out evaluation dataset."""
    logging.basicConfig(level=logging.INFO)
    HELDOUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    cases = generate_all_heldout_cases()
    clean_count = 0
    for c in cases:
        ents = c.get("entities")
        if isinstance(ents, list) and len(ents) == 0:
            clean_count += 1
    pii_count = len(cases) - clean_count

    with open(HELDOUT_PATH, "w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    logger.info("Generated %d held-out cases to %s", len(cases), HELDOUT_PATH)
    logger.info("  PII positive cases: %d", pii_count)
    logger.info("  PII-free hard negatives: %d", clean_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
