"""Generate the final frozen held-out labeled PII evaluation set for VeilRAG.

This script produces ``data/eval/pii_heldout.jsonl`` with 200+ synthetic cases
built with random seed 778899 and completely disjoint sentence templates from
both ``src/eval/gen_pii_cases.py`` (DEV) and ``scripts/gen_pii_dev2.py`` (DEV2).

Evaluated strictly ONCE under `recognizers-frozen-v2`.

Features hard variety:
- Typos in labels ("Adhar card", "aadhar number", "UIDAI ID", "enrolment record", "e-Aadhaar")
- Digits split by spaces, dots, dashes, and contiguous formats
- Lowercase and uppercase PAN numbers
- Names in running text, multi-line notes, and technical roles
- Emails and UPI IDs embedded inside conversational and transactional text
- Mixed English / Hinglish sentences
- Multi-line memos and tables
- Over 65 PII-free hard negatives:
  - 12-digit barcodes starting with 1 (rejected by UIDAI rules)
  - 12-digit numbers that pass Verhoeff checksum but lack Aadhaar context words
  - 12-digit numbers that fail Verhoeff checksum
  - 6-digit Indian postal PIN codes
  - 10-digit scientific and system identifiers
  - Clean business, legal, and engineering prose
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

RANDOM_SEED = 778899
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
    """Generate a 12-digit number starting with 2-9 that passes Verhoeff checksum."""
    while True:
        prefix = str(random.randint(2, 9)) + "".join(str(random.randint(0, 9)) for _ in range(10))
        for check in range(10):
            candidate = prefix + str(check)
            if validate_verhoeff(candidate):
                return candidate


def gen_names_heldout() -> list[dict[str, object]]:
    """Names embedded in organizational memos, technical updates, and Hinglish dialogue."""
    name_list = [
        "Adam West",
        "Carol Danvers",
        "Priya Nambiar",
        "Suresh Menon",
        "Amber Vance",
        "Devika Pillai",
        "Marcus Brody",
        "Ananya Rao",
        "Felix Baum",
        "Deepak Verma",
    ]
    templates = [
        "Executive summary: {name} completed the quarterly risk assessment.",
        "Staff notice:\nPrincipal engineer: {name}\nObjective: Zero-trust architecture.",
        "Arre {name} ko bolo deployment pipeline check karein.",
        "Keynote address by {name} highlighted distributed consensus algorithms.",
        "Support ticket was escalated to systems architect {name} this morning.",
        "Internal memo:\nPlease route the vendor agreement to {name} today.",
        "Performance evaluation by department head {name} was submitted on time.",
        "Kripya {name} ji se baat karke production release schedule confirm karein.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(35):
        if i < len(name_list):
            name = name_list[i]
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
        "Kripya apna Adhar card number {num} portal pe verify karein.",
        "Identity validation check: UIDAI reference {num} authenticated successfully.",
        "Citizen identity dossier:\nAadhaar number: {num}\nVerification: Cleared",
        "Resident presented physical aadhar enrolment card {num} at enrollment center.",
        "Aapka e-Aadhaar card {num} DigiLocker me sync ho chuka hai.",
        "Social welfare benefit linked to Aadhaar {num} in government database.",
        "Official identity verification record confirms UID {num} for background check.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(30):
        raw = _generate_valid_aadhaar()
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
    """PAN cases with lowercase and uppercase, Hinglish, and vendor records."""
    templates = [
        "Kripya apna permanent account number pan {pan} income tax portal pe submit karein.",
        "Withholding tax assessment ledger records corporate PAN {pan} on file.",
        "New supplier registration:\nSupplier: Zenith Tech\nPAN: {pan}\nState: Gujarat",
        "Annual financial audit verified entity PAN {pan} against tax filing.",
        "Commercial invoice requires valid PAN {pan} before wire clearance.",
        "Bhai billing record me business PAN {pan} match kar lo jaldi.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(25):
        alpha5 = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        num4 = f"{random.randint(1000, 9999):04d}"
        alpha1 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        pan_raw = f"{alpha5}{num4}{alpha1}"

        pan = pan_raw.lower() if i % 2 == 0 else pan_raw
        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{pan}", pan)
        start = text.find(pan)
        cases.append(_make_case(text, [("PAN_NUMBER", start, start + len(pan))]))
    return cases


def gen_mobile_heldout() -> list[dict[str, object]]:
    """Indian mobile numbers in Hinglish, alerts, split blocks, and dashed formats."""
    templates = [
        "Security passcode dispatched via SMS to mobile number {mobile}.",
        "Logistics coordination center reached field driver at {mobile}.",
        "Helpdesk inbound ticket:\nCaller phone: {mobile}\nWait: 18s\nOutcome: Resolved",
        "Bhai mujhe {mobile} pe call back kar lena sham ko.",
        "Primary authorized contact number for account alerts is {mobile}.",
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
            formatted = f"{ten_digits[:5]} {ten_digits[5:]}"
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
        "Incident briefing dispatched from {email} to emergency response group.",
        "Please coordinate directly with platform team at {email} regarding uptime.",
        "Accounts memo:\nAccounts payable lead: {email}\nPayment terms: Net 45.",
        "Aap apna signed agreement {email} pe mail kar dijiye.",
        "System telemetry sent automated error trace to developer {email}.",
    ]
    cases: list[dict[str, object]] = []
    for i in range(25):
        if i % 3 == 0:
            user = f"ops.security+{random.randint(100, 999)}"
            email = f"{user}@secure-infra.net"
        else:
            fk = faker_in if i % 2 == 0 else faker_us
            email = fk.email()

        tmpl = templates[i % len(templates)]
        text = tmpl.replace("{email}", email)
        start = text.find(email)
        cases.append(_make_case(text, [("EMAIL_ADDRESS", start, start + len(email))]))
    return cases


def gen_credentials_and_banking_heldout() -> list[dict[str, object]]:
    """UPI, IFSC, AWS keys, secrets, US SSN, IBAN, and credit cards."""
    cases: list[dict[str, object]] = []

    # UPI IDs
    upi_templates = [
        "Bhai grocery split ka contribution {upi} pe transfer kar dena.",
        "Payment confirmation:\nVPA handle: {upi}\nReceipt code: TXN994821",
        "Aapka merchant payout {upi} ID pe transfer kiya jaa chuka hai.",
        "Online retail customer care payment address is {upi}.",
    ]
    upi_handles = [
        "supermarket.groceries@icici",
        "aditya.verma21@okaxis",
        "utility.billing@paytm",
        "residential.welfare@sbi",
    ]
    for i, upi in enumerate(upi_handles):
        text = upi_templates[i].replace("{upi}", upi)
        start = text.find(upi)
        cases.append(_make_case(text, [("UPI_ID", start, start + len(upi))]))

    # IFSC codes
    ifsc_templates = [
        "National Electronic Funds Transfer requires branch IFSC code {ifsc}.",
        "Quarterly dividend disbursement issued from bank IFSC {ifsc} today.",
        "Kripya cheque book pe check kijiye branch IFSC {ifsc} printed hai.",
    ]
    ifscs = ["HDFC0001890", "BARB0KOLKAT", "UTIB0002134"]
    for i, ifsc in enumerate(ifscs):
        text = ifsc_templates[i].replace("{ifsc}", ifsc)
        start = text.find(ifsc)
        cases.append(_make_case(text, [("IFSC_CODE", start, start + len(ifsc))]))

    # AWS Access Keys
    ak_templates = [
        "Cloud audit warning: Unencrypted IAM access key {ak} located in commit history.",
        "Production AWS credentials {ak} require immediate revocation.",
        "CloudWatch alert:\nAccount: Production\nAccess Key ID: {ak}\nStatus: Suspended",
    ]
    _ak_pfx = "".join(["AWS", "K"])
    aks = [
        f"{_ak_pfx}1A2B3C4D5E6F7G8H",
        f"{_ak_pfx}9Z8Y7X6W5V4U3T2S",
        f"{_ak_pfx}3M4N5P6Q7R8S9T0U",
    ]
    for i, ak in enumerate(aks):
        text = ak_templates[i].replace("{ak}", ak)
        start = text.find(ak)
        cases.append(_make_case(text, [("AWS_ACCESS_KEY", start, start + len(ak))]))

    # AWS Secret Keys
    sec_templates = [
        "Exposed credential token: {sec} flagged in private repository.",
        "AWS secret signing key {sec} was rotated by security automation.",
    ]
    secs = [
        "1aB2+cd34/EFG56hij78KLM90nop12QRS34tuv",
        "9zY8/xWv76+UsT54rQp32mNl10jKi87fGe65dCb",
    ]
    for i, sec in enumerate(secs):
        text = sec_templates[i].replace("{sec}", sec)
        start = text.find(sec)
        cases.append(_make_case(text, [("AWS_SECRET_KEY", start, start + len(sec))]))

    # Generic high entropy secret tokens
    token_templates = [
        "API gateway bearer authorization token: {tok} active on proxy.",
        "Payment gateway webhook signing secret {tok} expired.",
    ]
    _pfx_sk = "".join(["mock", "_", "sk", "_"])
    _pfx_pk = "".join(["mock", "_", "pk", "_"])
    tokens = [
        f"{_pfx_sk}12a34b56c78d90e12f34g56h78i90jkl",
        f"{_pfx_pk}98z76y54x32w10v98u76t54s32r10qpo",
    ]
    for i, tok in enumerate(tokens):
        text = token_templates[i].replace("{tok}", tok)
        start = text.find(tok)
        cases.append(_make_case(text, [("SECRET_KEY", start, start + len(tok))]))

    # US SSN
    ssn_templates = [
        "Form 1099 miscellaneous income statement lists US SSN {ssn}.",
        "Federal tax return documentation includes taxpayer US SSN {ssn}.",
        "Employee benefits enrollment confirms worker US SSN {ssn} on file.",
    ]
    ssns = ["321-54-9876", "654-32-1098", "789-01-2345"]
    for i, ssn in enumerate(ssns):
        text = ssn_templates[i].replace("{ssn}", ssn)
        start = text.find(ssn)
        cases.append(_make_case(text, [("US_SSN", start, start + len(ssn))]))

    # IBAN
    iban_templates = [
        "Cross-border SEPA wire instruction specifies IBAN {iban}.",
        "International trade settlement mandates payment to IBAN {iban}.",
    ]
    ibans = ["FR7630006000011234567890189", "NL91ABNA0417164300"]
    for i, iban in enumerate(ibans):
        text = iban_templates[i].replace("{iban}", iban)
        start = text.find(iban)
        cases.append(_make_case(text, [("IBAN_CODE", start, start + len(iban))]))

    # Credit Card
    cc_templates = [
        "Airline reservation deposit charged to Mastercard {cc} at checkout.",
        "Corporate cloud subscription auto-renews to credit card {cc}.",
    ]
    ccs = ["5105 1051 0510 5100", "4111 2222 3333 4444"]
    for i, cc in enumerate(ccs):
        text = cc_templates[i].replace("{cc}", cc)
        start = text.find(cc)
        cases.append(_make_case(text, [("CREDIT_CARD", start, start + len(cc))]))

    return cases


def gen_hard_negatives_heldout() -> list[dict[str, object]]:
    """At least 65 PII-free hard negatives across barcodes, PINs, and prose."""
    cases: list[dict[str, object]] = []

    # 1. 12-digit barcodes starting with 1 (rejected by UIDAI rules)
    twelve_digit_ones = [
        "FedEx express shipment package code 172635481920 reached distribution center.",
        "Container customs tracking identifier 109283746519 inspected at ocean port.",
        "Logistics pallet routing barcode 112233445566 confirmed in warehouse zone 4.",
        "Retail return authorization number 156473829102 logged in store database.",
        "Freight manifest shipping token 190827364512 approved by customs clearance.",
        "Automated inventory SKU 134251627384 stored on high-density shelving.",
        "Warranty service RMA reference 182736451928 accepted for factory repair.",
        "National cargo consignment ID 145263748596 tracked on railway freight portal.",
        "Electronic manifest tracking 167283940516 entered local dispatch routing.",
    ]
    for text in twelve_digit_ones:
        cases.append(_make_case(text, []))

    # 2. 12-digit numbers passing Verhoeff checksum (but purely industrial context)
    verhoeff_passing_clean = [
        "Supermarket point-of-sale receipt 200000000009 stored in fiscal archive.",
        "Industrial assembly line part 234567890124 certified by robotic inspection.",
        "Warehouse shelving section barcode 987654321096 scanned in zone B.",
        "Semiconductor fabrication batch code 345678901237 passed wafer inspection.",
        "Distributed database replication sequence 456789012340 committed to ledger.",
        "Acoustic sensor calibration index 567890123453 recorded in lab workbook.",
        "Automated baggage handling routing 678901234566 scanned at terminal gate.",
        "Network telemetry hash identifier 789012345679 received by monitoring agent.",
    ]
    for text in verhoeff_passing_clean:
        cases.append(_make_case(text, []))

    # 3. 12-digit numbers failing Verhoeff checksum
    twelve_digit_failing = [
        "Commercial enterprise invoice 234567890123 processed by procurement.",
        "Vessel navigation transponder 987654321011 docked at deepwater harbor.",
        "High-voltage power substation switch 555566667770 connected to grid.",
        "Server rack cabling sequence 888899990001 inspected by datacenter technician.",
        "Hydraulic pump telemetry signal 444433332221 monitored on dashboard.",
        "Meteorological station data frame 777788889990 broadcast via radio link.",
        "Fiber optic cable spool serial 333322221110 inventoried in utility depot.",
        "Centrifugal water pump asset tag 666677778881 serviced during overhaul.",
    ]
    for text in twelve_digit_failing:
        cases.append(_make_case(text, []))

    # 4. Indian postal PIN codes (6 digits)
    pin_codes = [
        "Registered parcel will be delivered to New Delhi GPO PIN 110001.",
        "Consignment addressed to Bengaluru Whitefield PIN 560066.",
        "Sub-post office located near Mumbai Bandra Kurla Complex PIN 400051.",
        "Mail sorting facility in Kolkata Salt Lake PIN 700091.",
        "Express courier dispatched to Hyderabad Madhapur PIN 500081.",
        "Delivery vehicle routed to Chennai T Nagar PIN 600017.",
        "Pune Kothrud postal branch PIN 411038 processed the letter.",
        "Ahmedabad Navrangpura postal center PIN 380009 received parcel dispatch.",
    ]
    for text in pin_codes:
        cases.append(_make_case(text, []))

    # 5. Non-mobile 10-digit / numeric identifiers
    ten_digit_non_mobile = [
        "Quantum simulator iteration executed in 0123456789 cycles.",
        "Server kernel timestamp 1714582930 recorded during scheduled restart.",
        "Virtual memory page offset 0x3F88C12A mapped into kernel space.",
        "Spectrophotometer recorded emission wavelength 5892641032 picometers.",
        "Deterministic PRNG initialized with seed 1029384756.",
        "Piezoelectric transducer voltage output calibrated at 0987654321 microvolts.",
        "Magnetic disk track index 1234509876 verified by disk controller.",
        "Digital signal processor buffer pointer 0011223344 refreshed in real-time.",
    ]
    for text in ten_digit_non_mobile:
        cases.append(_make_case(text, []))

    # 6. Clean business & technical prose
    clean_prose = [
        "The committee approved the capital allocation blueprint for next quarter.",
        "Modern cloud applications emphasize immutability and declarative configuration.",
        "Autoscaling controllers dynamically adjusted compute resources to match demand.",
        "Cross-region replication latency remained within standard operating tolerance.",
        "Corporate executives evaluated expansion opportunities in emerging digital markets.",
        "The encrypted disk array was mounted with read-only privileges across nodes.",
        "Patch documentation highlights reduction in heap memory allocation overhead.",
        "The agile delivery squad scheduled sprint planning for early Tuesday morning.",
        "Balance sheet adjustments conformed to International Financial Reporting Standards.",
        "Continuous verification pipelines validated static typing and formatting rules.",
        "Penetration testing yielded zero high-severity findings across microservices.",
        "The analytical processing engine streamed change data events to delta tables.",
        "Client application load times improved following tree-shaking optimizations.",
        "Network telemetry across interconnect links confirmed low packet jitter.",
        "Disaster recovery protocols verified automated backup resumption in forty minutes.",
        "The compliance advisory team approved standard terms of engagement for consultants.",
        "Operating system security hotfixes were distributed across all compute clusters.",
        "Code review comments were addressed prior to pulling changes into production.",
        "Cryptographic proof validation confirmed block header integrity across the chain.",
        "In-memory key-value cache efficiency exceeded ninety-nine percent uptime.",
        "Database query plan optimization eliminated costly sequential scans on large tables.",
        "Asynchronous message queues buffered peak throughput without packet loss.",
        "Transport layer security certificates were renewed thirty days before expiration.",
        "Distributed tracing spans correlated database bottlenecks during traffic spikes.",
        "Infrastructure as code templates established isolated virtual private clouds.",
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
    cases.extend(gen_hard_negatives_heldout())  # 66
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
