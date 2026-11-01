"""Generate heldout3 evaluation dataset for coverage recognizers in VeilRAG.

Evaluates coverage of privacy gap recognizers under frozen tag recognizers-frozen-v3.
Built with a completely separate random seed and disjoint sentence templates.
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
HELDOUT3_PATH = DATA_DIR / "pii_heldout3.jsonl"

RANDOM_SEED = 88419
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


def gen_dob_heldout() -> list[dict[str, object]]:
    """Generate held-out positive DATE_OF_BIRTH cases."""
    cases: list[dict[str, object]] = []

    dobs = [
        "16-11-1982",
        "29/04/1991",
        "05-12-1976",
        "18-09-1995",
        "23-01-1989",
        "30-06-1973",
        "12-10-1997",
        "07-03-1968",
        "21-08-1993",
        "14-05-1986",
        "02-12-1980",
        "27-07-1964",
        "11-02-1994",
        "19-04-1978",
        "06-11-1996",
        "28 October 1991",
        "17 February 1983",
        "09 September 1995",
        "25 December 1987",
        "13 July 1981",
        "22-Oct-1990",
        "15-Jan-1985",
        "04.08.1992",
        "19.06.1977",
    ]

    templates = [
        "Primary insured member official date of birth {val} recorded at branch.",
        "Beneficiary identity documentation lists DOB: {val} as validated.",
        "According to immigration records the claimant was born on {val}.",
        "Executive identity dossier contains guarantor birth date {val} on file.",
        "Employee records maintain verified date of birth {val} in HR archive.",
        "Medical intake form confirms D.O.B: {val} for pediatric registry.",
        "The nominee was born on {val} per school leaving certificate.",
        "Customer profile indicates date of birth {val} authenticated via passport.",
    ]

    for i, dob_val in enumerate(dobs):
        tmpl = templates[i % len(templates)]
        text = tmpl.format(val=dob_val)
        start = text.index(dob_val)
        end = start + len(dob_val)
        cases.append(_make_case(text, [("DATE_OF_BIRTH", start, end)]))

    return cases


def gen_bank_account_heldout() -> list[dict[str, object]]:
    """Generate held-out positive BANK_ACCOUNT cases."""
    cases: list[dict[str, object]] = []

    accounts = [
        "60100889922114",
        "30491122334",
        "005601988234",
        "60100778833445",
        "000806023459",
        "915010045678902",
        "60100112233440",
        "40981245082",
        "23400016009834",
        "60100667788990",
        "20050167909234",
        "20460600239956",
        "60100556677889",
        "40099135612",
        "004901699235",
        "87654321098765",
        "223344556677",
        "887766554433221",
        "23456789012",
        "556677889900112",
    ]

    templates = [
        "Vendor electronic remittance processed to current account {val}.",
        "Maturity proceeds credited to customer savings account {val}.",
        "Rebate reimbursement approved to designated account {val}.",
        "Direct debit authorization executed against account {val} via mandate.",
        "Dividends remitted via NACH to account {val} without rejection.",
        "Security caution deposit refunded to designated account {val}.",
        "Loan principal credited into borrower savings account {val}.",
        "Corporate dividend distribution credited to current account {val}.",
    ]

    for i, acc in enumerate(accounts):
        tmpl = templates[i % len(templates)]
        text = tmpl.format(val=acc)
        start = text.index(acc)
        end = start + len(acc)
        cases.append(_make_case(text, [("BANK_ACCOUNT", start, end)]))

    return cases


def gen_address_heldout() -> list[dict[str, object]]:
    """Generate held-out positive ADDRESS cases."""
    cases: list[dict[str, object]] = []

    addresses = [
        "Flat 502 Silver Oak, SG Highway, Bodakdev, Ahmedabad, Gujarat 380054",
        "House No 44, Malviya Nagar, JLN Marg, Jaipur, Rajasthan 302017",
        "Tower C Apt 804, Sector 17 Commercial Complex, Chandigarh 160017",
        "House 29, Gomti Nagar Phase 2, Vibhuti Khand, Lucknow, Uttar Pradesh 226010",
        "Plot 112, Peelamedu Industrial Estate, Avinashi Road, Coimbatore, Tamil Nadu 641004",
        "Flat 601 Royal Residency, Ring Road, Surat, Gujarat 395002",
        "Flat 204 Maple Heights, Vijay Nagar AB Road, Indore, Madhya Pradesh 452010",
        "B-402 Chandrasekharpur Housing Colony, Bhubaneswar, Odisha 751024",
        "C-18 Jayalakshmipuram, Temple Road, Mysore, Karnataka 570012",
        "House 92, Arera Colony Sector E-7, Bhopal, Madhya Pradesh 462016",
        "Door No 56, VIP Road, CBM Compound, Visakhapatnam, Andhra Pradesh 530003",
        "Plot 45, MIDC Industrial Area, Hingna Road, Nagpur, Maharashtra 440016",
        "Flat 108 Green View Apartments, Rajpur Road, Dehradun, Uttarakhand 248001",
        "Bait-ul-Salam, Beach Road, Kozhikode, Kerala 673032",
        "Flat 303 Golden Palms, GS Road, Christian Basti, Guwahati, Assam 781005",
        "Apartment 7A, Ocean Spray Towers, Marine Drive, Kochi, Kerala 682011",
        "Suite 400, DLF Cyber City Tower C, DLF Phase 3, Gurugram, Haryana 122002",
        "Building 12, Commerzone IT Park, Yerwada, Pune, Maharashtra 411006",
        "House 314, Urban Estate Phase 1, Jalandhar, Punjab 144022",
        "Plot 90, GIDC Industrial Estate, Makarpura, Vadodara, Gujarat 390010",
    ]

    templates = [
        "Verified communication residence is documented as {val}.",
        "The corporate registered branch address is recorded as {val}.",
        "Physical site audit conducted at premise location: {val}.",
        "Applicant home residence verified as {val}.",
        "Contractual legal notice delivered to {val}.",
    ]

    for i, addr in enumerate(addresses):
        tmpl = templates[i % len(templates)]
        text = tmpl.format(val=addr)
        start = text.index(addr)
        end = start + len(addr)
        cases.append(_make_case(text, [("ADDRESS", start, end)]))

    return cases


def gen_uhid_heldout() -> list[dict[str, object]]:
    """Generate held-out positive UHID / Hospital ID cases."""
    cases: list[dict[str, object]] = []

    hosp_ids = [
        "UH-991204",
        "UH-334190",
        "UH-667812",
        "UH-884102",
        "IP-2026-MED-99410",
        "IP-2026-CARD-22045",
        "IP-2026-SURG-77123",
        "IP-2026-PED-55901",
        "AIIMS-MED-2026-DEL-801",
        "KIMS-ORTHO-2026-HYD-442",
        "NAR-CARD-2026-BLR-610",
        "MED-SURG-2026-GUR-205",
        "MRN-991204",
        "MRN-330412",
        "MRN-884190",
        "PID-667821",
        "PID-889034",
        "PID-221094",
    ]

    templates = [
        "Electronic medical record cataloged under UHID: {val}.",
        "Clinical observation file tagged with hospital identifier {val}.",
        "Discharge clearance recorded under admission tracking code {val}.",
        "Laboratory pathology dossier references patient record {val}.",
    ]

    for i, hid in enumerate(hosp_ids):
        tmpl = templates[i % len(templates)]
        text = tmpl.format(val=hid)
        start = text.index(hid)
        end = start + len(hid)
        cases.append(_make_case(text, [("UHID", start, end)]))

    return cases


def gen_hard_negatives_heldout() -> list[dict[str, object]]:
    """Generate held-out hard negatives."""
    cases: list[dict[str, object]] = []

    # 1. Non-DOB dates
    dates = [
        "Commercial purchase order INV-2026-904 dated 18/04/2026 is due on 02/05/2026.",
        "The bilateral non-disclosure agreement remains in effect until 31-10-2026.",
        "Statutory filing deadline for annual return is finalized as 30-09-2026.",
        "Board of directors meeting convened on 14th November 2026 in Mumbai.",
        "Equipment warranty valid through 28-02-2027 under original manufacturer terms.",
        "Software release version 2.4 deployment scheduled for 22/07/2026.",
        "Audit committee concluded inspections on 19 December 2026.",
        "Lease tenancy period terminates on 31-08-2026 without renewal option.",
        "The project commissioning milestone target is set for 15.10.2026.",
        "Notice period for executive resignation is 90 days from 01-11-2026.",
    ]

    # 2. OTPs
    otps = [
        "Your authentication one-time password for mobile login is 774102.",
        "Enter six-digit validation code 449012 to authorize access.",
        "Secure verification OTP 881234 expires in two minutes.",
        "Banking portal two-factor passcode 223401 generated on token.",
        "Customer portal authorization code 993410 delivered to handset.",
        "Security validation code 550192 required to confirm password change.",
    ]

    # 3. Order / consignment tracking
    orders = [
        "Warehouse shipment requisition #9988776655 has cleared export customs.",
        "Cargo tracking identifier 223344556677 indicates delivery to airport hub.",
        "Procurement dispatch note PO-8877665544 signed by receiving officer.",
        "Air waybill tracking number 334455667788 shows transit through Doha.",
        "Enterprise service ticket ID 8899001122 closed with resolution.",
        "Container freight manifest 112233445566 inspected at dry port.",
    ]

    # 4. Phone numbers without banking context
    phones = [
        "For technical questions, please dial customer helpdesk 8844220011.",
        "Dispatch coordinator emergency contact line is 7733119900.",
        "Direct office telephone line for facilities is 9988112233.",
        "Enterprise vendor support desk answers calls at 8822446600.",
        "Central reception switchboard telephone number is 6644220088.",
    ]

    # 5. Quantities / metric counts
    quantities = [
        "The semiconductor foundry produced 250000000 silicon chips this quarter.",
        "City water utility supplies 800000000 gallons during summer distribution.",
        "Cryptographic proof verification computed in 200000000 CPU cycles.",
        "Optical sensor detected particle scattering at 650000000 picometers.",
        "Buffer memory cleared after streaming 500000000 data frames.",
        "Telecommunications trunk link capacity measured at 2000000000 bits per second.",
    ]

    # 6. Addresses without PIN code
    addresses_no_pin = [
        "Regional sales office located at Flat 502 Silver Oak, SG Highway, Ahmedabad.",
        "The client resides at House No 44, Malviya Nagar, JLN Marg, Jaipur.",
        "Branch operations situated in Tower C Apt 804, Sector 17, Chandigarh.",
        "Corporate legal team based at House 29, Gomti Nagar Phase 2, Lucknow.",
        "Manufacturing plant situated at Plot 112, Peelamedu Industrial Estate, Coimbatore.",
        "Residential flat located at Flat 601 Royal Residency, Ring Road, Surat.",
    ]

    # 7. Postal PIN without address premises markers
    pins = [
        "Consignment will be sorted at Jaipur GPO PIN 302001.",
        "Postal dispatch routed to Ahmedabad Navrangpura PIN 380009.",
        "Central mail distribution hub in Lucknow Chowk PIN 226003.",
        "Express parcel delivery destined for Chandigarh Sector 22 PIN 160022.",
        "Surat textile market postal agency PIN 395003 received shipment.",
        "Indore postal sorting facility PIN 452001 processed incoming mail.",
        "Kochi Marine Drive delivery station PIN 682011 dispatched letters.",
        "Coimbatore RS Puram postal hub PIN 641002 scanned package.",
    ]

    # 8. Clean prose
    clean = [
        "Distributed consensus protocols guarantee transactional integrity in replicated databases.",
        "Statutory corporate governance regulations mandate independent board oversight.",
        "Automated deployment orchestrators manage rolling canary updates across nodes.",
        "Network packet inspection validated low round-trip latency across WAN gateways.",
        "Microservice containers implement health probes and graceful termination handlers.",
        "Agile retrospectives identify continuous process enhancements for engineering teams.",
        "Immutable audit logs prevent unauthorized tampering with security telemetry.",
        "Financial controllers confirmed reconciliation of inter-company ledger balances.",
        "Kubernetes ingress controllers enforce TLS termination and path-based routing.",
        "Zero-trust network architecture requires continuous identity and device verification.",
    ]

    all_negatives = (
        dates
        + otps
        + orders
        + phones
        + quantities
        + addresses_no_pin
        + pins
        + clean
    )

    for text in all_negatives:
        cases.append(_make_case(text, []))

    return cases


def generate_all_heldout3_cases() -> list[dict[str, object]]:
    """Assemble the complete heldout3 evaluation dataset."""
    cases: list[dict[str, object]] = []
    cases.extend(gen_dob_heldout())  # 24 positives
    cases.extend(gen_bank_account_heldout())  # 20 positives
    cases.extend(gen_address_heldout())  # 20 positives
    cases.extend(gen_uhid_heldout())  # 18 positives
    cases.extend(gen_hard_negatives_heldout())  # 65 hard negatives
    return cases


def main() -> int:
    """Generate and serialize the heldout3 evaluation dataset."""
    logging.basicConfig(level=logging.INFO)
    HELDOUT3_PATH.parent.mkdir(parents=True, exist_ok=True)

    cases = generate_all_heldout3_cases()
    clean_count = sum(1 for c in cases if not c.get("entities"))
    pii_count = len(cases) - clean_count

    with open(HELDOUT3_PATH, "w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    logger.info("Generated %d heldout3 cases to %s", len(cases), HELDOUT3_PATH)
    logger.info("  PII positive cases: %d", pii_count)
    logger.info("  PII-free hard negatives: %d", clean_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

