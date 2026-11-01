"""Synthetic enterprise document generator for VeilRAG Corpus V2.

Generates 70 realistic Indian business documents (300-1500 words each) across 7 categories:
1. HR policies (notice period, leave policy, working hours)
2. Loan agreements (loan amount, interest rate, tenure, processing fee)
3. Hospital discharge summaries (diagnosis, status, follow-up, medications)
4. Insurance claims (claim ID, claimed amount, approved amount, deductible)
5. KYC onboarding dossiers (account type, risk rating, verification mode)
6. Vendor service agreements (monthly retainer, SLA uptime, termination notice, penalty)
7. Commercial lease agreements (monthly rent, security deposit, lock-in period, escalation)

All organisations are fictional (AuraCare, Zenith, TerraTrust, Solaris, NovaCrest, etc.).
Templates include near-duplicates with varying contractual parameters to benchmark retrieval.
PII phrasing deliberately varies across documents (Room/Apartment/Sector/c/o addresses,
spaced D O B, tabular DOB, split A/C numbers, lowercase PAN, dashed mobiles, bare UHIDs).

Writes documents to `data/docs_v2/` and ground truth to `data/docs_v2/_ground_truth.json`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from faker import Faker

from src.sanitizer.detectors import validate_verhoeff

logger = logging.getLogger(__name__)

DOCS_V2_DIR = Path("data/docs_v2")
GROUND_TRUTH_FILE = DOCS_V2_DIR / "_ground_truth.json"


def _generate_valid_aadhaar(fake: Faker) -> str:
    """Generate a 12-digit number starting with 2-9 that satisfies Verhoeff checksum."""
    while True:
        prefix = str(fake.random_int(min=2, max=9)) + "".join(
            str(fake.random_int(min=0, max=9)) for _ in range(10)
        )
        for check in range(10):
            candidate = prefix + str(check)
            if validate_verhoeff(candidate):
                return candidate


class DocBuilder:
    """Helper to incrementally build documents with exact character span tracking."""

    def __init__(self, filename: str, doc_type: str, key_facts: dict[str, str]) -> None:
        self.filename = filename
        self.doc_type = doc_type
        self.key_facts = key_facts
        self.parts: list[str] = []
        self.entities: list[dict[str, Any]] = []

    def text(self, s: str) -> DocBuilder:
        self.parts.append(s)
        return self

    def pii(self, entity_type: str, value: str, in_scope: bool = True) -> DocBuilder:
        current_len = sum(len(p) for p in self.parts)
        start = current_len
        end = start + len(value)
        self.entities.append(
            {
                "type": entity_type,
                "value": value,
                "start": start,
                "end": end,
                "in_scope": in_scope,
            }
        )
        self.parts.append(value)
        return self

    def build(self) -> tuple[str, dict[str, Any]]:
        full_text = "".join(self.parts)
        # Verify span consistency
        for ent in self.entities:
            extracted = full_text[ent["start"] : ent["end"]]
            if extracted != ent["value"]:
                raise ValueError(
                    f"Span mismatch in {self.filename} for {ent['type']}: "
                    f"'{extracted}' != '{ent['value']}'"
                )

        word_count = len(full_text.split())
        if not (300 <= word_count <= 1500):
            raise ValueError(
                f"Document {self.filename} has {word_count} words; must be between 300 and 1500 words."
            )

        metadata = {
            "filename": self.filename,
            "doc_type": self.doc_type,
            "word_count": word_count,
            "key_facts": self.key_facts,
            "pii_entities": self.entities,
        }
        return full_text, metadata


def generate_all_v2_documents() -> list[tuple[str, str, tuple[str, dict[str, Any]]]]:
    """Generate 70 synthetic enterprise documents for Corpus V2."""
    fake = Faker("en_IN")
    fake.seed_instance(99824)

    docs: list[tuple[str, str, tuple[str, dict[str, Any]]]] = []

    # ─────────────────────────────────────────────────────────────────────────
    # 1. HR POLICIES (10 Documents)
    # ─────────────────────────────────────────────────────────────────────────
    hr_configs = [
        # Starlight Technologies (Docs 1-3)
        ("hr_policy_01.txt", "Starlight Technologies Private Limited", "30 calendar days", "20 days of paid privilege leave", "3 months", "9:00 AM to 6:00 PM Monday through Friday", "ananya.sharma@starlighttech.example", "+91 98451 23450", "abcks1234m", "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066", "14-08-1988", "50100234918231", "ananya.sharma@starlightbank"),
        ("hr_policy_02.txt", "Starlight Technologies Private Limited", "60 calendar days", "24 days of paid privilege leave", "6 months", "9:00 AM to 6:00 PM Monday through Friday", "vikram.rathore@starlighttech.example", "+91 98230 45671", "BCKPR5678N", "Room 402, Shanti Nilayam Hostel, Bannerghatta Road, Bengaluru, Karnataka 560076", "22-11-1985", "50100458921345", "vikram.rathore@starlightbank"),
        ("hr_policy_03.txt", "Starlight Technologies Private Limited", "90 calendar days", "30 days of paid privilege leave", "6 months", "9:30 AM to 6:30 PM Monday through Friday", "rohit.deshmukh@starlighttech.example", "+91 98112 34567", "CDKPS9012P", "Apartment 304, Green Horizon, Whitefield Main Road, Bengaluru, Karnataka 560066", "D O B : 03-05-1992", "50100984512390", "rohit.deshmukh@starlightbank"),
        # Quantum Solstice Labs (Docs 4-6)
        ("hr_policy_04.txt", "Quantum Solstice Labs Private Limited", "45 calendar days", "21 days of paid privilege leave", "3 months", "10:00 AM to 7:00 PM with core agile hours", "kavita.nair@quantumsolstice.example", "+91-98-4512-3450", "cdeks3456r", "c/o Suresh Varma, Sector 14, Huda Colony, Gurugram, Haryana 122001", "19-03-1990", "A/C No. :\n20489912034", "kavita.nair@quantumbank"),
        ("hr_policy_05.txt", "Quantum Solstice Labs Private Limited", "60 calendar days", "24 days of paid privilege leave", "6 months", "10:00 AM to 7:00 PM with core agile hours", "siddharth.menon@quantumsolstice.example", "+91 98450 11223", "EFGHT1234S", "Flat 102 Crystal Arcade, Indiranagar 100 Feet Road, Bengaluru, Karnataka 560038", "11-12-1971", "004501589123", "siddharth.menon@quantumbank"),
        ("hr_policy_06.txt", "Quantum Solstice Labs Private Limited", "90 calendar days", "30 days of paid privilege leave", "6 months", "9:30 AM to 6:30 PM Monday through Friday", "priya.nambiar@quantumsolstice.example", "+91 98201 99887", "fghks7890t", "Sector 62, Block B, Electronic City, Noida, Uttar Pradesh 201309", "28-09-1994", "914010034567891", "priya.nambiar@quantumbank"),
        # SilverOak Logistics (Docs 7-8)
        ("hr_policy_07.txt", "SilverOak Logistics Network Limited", "30 calendar days", "18 days of paid privilege leave", "3 months", "8:30 AM to 5:30 PM Monday through Saturday", "arjun.das@silveroaklogistics.example", "+91-98765-43210", "GHIJK5678U", "House No 12, Sector 18, Vashi, Navi Mumbai, Maharashtra 400703", "15-06-1996", "50100778899123", "arjun.das@silveroakbank"),
        ("hr_policy_08.txt", "SilverOak Logistics Network Limited", "60 calendar days", "24 days of paid privilege leave", "6 months", "8:30 AM to 5:30 PM Monday through Saturday", "meera.patel@silveroaklogistics.example", "+91 98901 23456", "hijkl1234v", "Plot 88, Okhla Industrial Area Phase 3, New Delhi 110020", "18-01-1987", "10040156908123", "meera.patel@silveroakbank"),
        # AeroVanguard Dynamics (Docs 9-10)
        ("hr_policy_09.txt", "AeroVanguard Dynamics Private Limited", "45 calendar days", "21 days of paid privilege leave", "3 months", "9:00 AM to 6:00 PM Monday through Friday", "rajesh.gupta@aerovanguard.example", "+91 98451 98765", "IJKLM9012W", "Flat 201 Sri Sai Residency, Madhapur, Hyderabad, Telangana 500081", "09-12-1981", "10450500129845", "rajesh.gupta@aerobank"),
        ("hr_policy_10.txt", "AeroVanguard Dynamics Private Limited", "90 calendar days", "28 days of paid privilege leave", "6 months", "9:00 AM to 6:00 PM Monday through Friday", "sneha.kulkarni@aerovanguard.example", "+91-91-2345-6789", "jklmn5678x", "Door No 14, 2nd Main Road, Gandhi Nagar, Adyar, Chennai, Tamil Nadu 600020", "25-04-1965", "50100445566778", "sneha.kulkarni@aerobank"),
    ]

    for fname, org, notice, leave, prob, hours, email, mobile, pan, addr, dob, acct, upi in hr_configs:
        adh_raw = _generate_valid_aadhaar(fake)
        adh_fmt = f"{adh_raw[:4]} {adh_raw[4:8]} {adh_raw[8:]}"
        officer = fake.name()
        custodian = fake.name()

        b = DocBuilder(
            filename=fname,
            doc_type="hr_policy",
            key_facts={
                "notice_period": notice,
                "working_hours": hours,
                "annual_leave": leave,
                "probation_period": prob,
            },
        )
        (
            b.text(f"# {org.upper()}\n")
            .text("## COMPREHENSIVE HUMAN RESOURCES EMPLOYMENT POLICY AND CODE OF CONDUCT\n")
            .text(f"Document Reference: HR-POL-V2-{fname.replace('.txt', '').upper()}\n")
            .text("Effective Date: 1st January 2026 | Revision: 5.0\n\n")
            .text("### 1. Objective and Operating Scope\n")
            .text(
                f"This comprehensive employment handbook defines the service terms, professional obligations, "
                f"code of workplace ethics, and operational standards applicable to all full-time, part-time, "
                f"and probationary personnel employed by {org} across all corporate campuses and delivery hubs. "
                f"Adherence to this operational framework is a strict mandatory condition of employment.\n\n"
            )
            .text("### 2. Standard Working Hours and Core Attendance Guidelines\n")
            .text(
                f"The official operating business hours of the enterprise are designated as {hours}, "
                f"comprising an eight-hour productive workday alongside an allotted one-hour window for lunch and personal refreshment. "
                f"Associates assigned to operational rotations must observe assigned shifts under direct departmental oversight. "
                f"Digital biometric timestamps are mandatory for campus ingress and egress.\n\n"
            )
            .text("### 3. Annual Leave Entitlements and Separation Notice Period\n")
            .text(
                f"Each confirmed associate is granted {leave} per calendar cycle, accrued proportionately on a monthly basis. "
                f"Associates are also entitled to twelve days of medical contingency leave subject to clinical certification. "
                f"Upon voluntary resignation or formal separation, the mandatory contractual notice period is exactly {notice}. "
                f"During the initial statutory probation period of {prob}, separation notice may be executed within thirty days.\n\n"
            )
            .text("### 4. Regulatory Compliance and Ethics Officer Contact\n")
            .text(
                "The organization enforces zero tolerance for harassment, statutory non-compliance, and data breaches. "
                "For confidential inquiries regarding workplace grievances or compliance audits, contact Officer "
            )
            .pii("PERSON", officer)
            .text(" at official corporate email ")
            .pii("EMAIL_ADDRESS", email)
            .text(" or reach the ethics helpline on mobile ")
            .pii("INDIAN_MOBILE", mobile)
            .text(".\n\n")
            .text("### 5. Statutory Documentation and Employee Verification Dossier\n")
            .text(
                "Prior to payroll inclusion, every employee must furnish authenticated credentials. HR Custodian "
            )
            .pii("PERSON", custodian)
            .text(" verified employee identity. Identity document Aadhaar number ")
            .pii("AADHAAR", adh_fmt)
            .text(" was confirmed alongside Permanent Account Number (PAN) ")
            .pii("PAN", pan)
            .text(". Bank salary disbursement occurs via IFSC code ")
            .pii("IFSC", "STAR0001234")
            .text(" into corporate account ")
            .pii("BANK_ACCOUNT", acct)
            .text(". The employee domicile address on record is ")
            .pii("STREET_ADDRESS", addr)
            .text(". Employee date of birth is logged as ")
            .pii("DATE_OF_BIRTH", dob)
            .text(". Corporate expense reimbursements use verified UPI handle ")
            .pii("UPI", upi)
            .text(".\n\n")
            .text("### 6. Information Security and Intellectual Property Safeguards\n")
            .text(
                "Associates shall not transfer confidential repositories, client files, or internal architectural blueprints "
                "outside authorized systems. Violations warrant summary termination and legal proceedings under applicable laws.\n"
            )
        )
        docs.append((fname, "hr_policy", b.build()))

    # ─────────────────────────────────────────────────────────────────────────
    # 2. LOAN AGREEMENTS (10 Documents)
    # ─────────────────────────────────────────────────────────────────────────
    loan_configs = [
        # TerraTrust Capital (Docs 1-4)
        ("loan_agreement_01.txt", "TerraTrust Capital Finance Limited", "INR 25,00,000", "8.75% per annum floating", "36 months", "INR 5,000", "5010 0984 5123 90", "Room 12, Sunrise Chawl, Kurla West, Mumbai, Maharashtra 400070", "D O B : 03-05-1992", "pqrst4567u"),
        ("loan_agreement_02.txt", "TerraTrust Capital Finance Limited", "INR 50,00,000", "9.25% per annum fixed", "60 months", "INR 10,000", "50100458921345", "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066", "14-08-1988", "ABCDE1234F"),
        ("loan_agreement_03.txt", "TerraTrust Capital Finance Limited", "INR 1,00,00,000", "10.50% per annum reducing", "120 months", "INR 25,000", "20489912034", "Apartment 101, Prestige Towers, Vashi, Navi Mumbai, Maharashtra 400703", "22-11-1985", "cdeks3456r"),
        ("loan_agreement_04.txt", "TerraTrust Capital Finance Limited", "INR 2,00,00,000", "11.25% per annum fixed", "240 months", "INR 50,000", "A/C No. :\n004501589123", "Plot 88, Okhla Industrial Area Phase 3, New Delhi 110020", "19-03-1990", "EFGHT1234S"),
        # Apex Crest Financial (Docs 5-7)
        ("loan_agreement_05.txt", "Apex Crest Financial Services Limited", "INR 10,00,000", "9.00% per annum floating", "24 months", "INR 3,000", "914010034567891", "c/o Amit Sen, Salt Lake Sector 1, Kolkata, West Bengal 700064", "11-12-1971", "fghks7890t"),
        ("loan_agreement_06.txt", "Apex Crest Financial Services Limited", "INR 20,00,000", "9.75% per annum reducing", "48 months", "INR 7,500", "50100778899123", "Sector 62, Block B, Electronic City, Noida, Uttar Pradesh 201309", "28-09-1994", "GHIJK5678U"),
        ("loan_agreement_07.txt", "Apex Crest Financial Services Limited", "INR 40,00,000", "10.25% per annum fixed", "84 months", "INR 15,000", "10040156908123", "House No 12, Sector 18, Vashi, Navi Mumbai, Maharashtra 400703", "15-06-1996", "hijkl1234v"),
        # Vanguard Nexus Finserve (Docs 8-10)
        ("loan_agreement_08.txt", "Vanguard Nexus Finserve Limited", "INR 15,00,000", "8.90% per annum floating", "12 months", "INR 4,500", "10450500129845", "Flat 102 Crystal Arcade, Indiranagar 100 Feet Road, Bengaluru, Karnataka 560038", "18-01-1987", "IJKLM9012W"),
        ("loan_agreement_09.txt", "Vanguard Nexus Finserve Limited", "INR 30,00,000", "9.60% per annum reducing", "36 months", "INR 9,000", "50100445566778", "Door No 14, 2nd Main Road, Gandhi Nagar, Adyar, Chennai, Tamil Nadu 600020", "09-12-1981", "jklmn5678x"),
        ("loan_agreement_10.txt", "Vanguard Nexus Finserve Limited", "INR 60,00,000", "10.80% per annum fixed", "60 months", "INR 18,000", "30089124501", "Flat 201 Sri Sai Residency, Madhapur, Hyderabad, Telangana 500081", "25-04-1965", "KLMNO3456Y"),
    ]

    for fname, lender, amt, rate, tenure, fee, acct, addr, dob, pan in loan_configs:
        adh_raw = _generate_valid_aadhaar(fake)
        adh_fmt = f"{adh_raw[:4]} {adh_raw[4:8]} {adh_raw[8:]}"
        borrower = fake.name()
        guarantor = fake.name()

        b = DocBuilder(
            filename=fname,
            doc_type="loan_agreement",
            key_facts={
                "loan_amount": amt,
                "interest_rate": rate,
                "tenure": tenure,
                "processing_fee": fee,
            },
        )
        (
            b.text(f"# {lender.upper()}\n")
            .text("## SECURED FACILITY CREDIT AGREEMENT AND COVENANTS\n")
            .text(f"Contract Reference: LN-AGR-V2-{fname.replace('.txt', '').upper()}\n")
            .text("Execution Date: 15th January 2026 | Version: 3.4\n\n")
            .text("### 1. Parties and Sanctioned Facility\n")
            .text(
                f"This Commercial Credit Facility Agreement is executed between {lender} ('Lender') "
                f"and Borrower "
            )
            .pii("PERSON", borrower)
            .text(
                f" ('Borrower'). The Lender hereby sanctions a term credit facility of {amt} subject to "
                f"the contractual covenants and terms set forth herein.\n\n"
            )
            .text("### 3. Financial Terms and Amortization Schedule\n")
            .text(
                f"The borrower covenants to repay the principal advance over an amortization tenure of {tenure}. "
                f"The applied interest computation rate is {rate}, calculated on daily outstanding balances. "
                f"A one-time non-refundable administrative processing fee of {fee} is deducted at initial drawdown.\n\n"
            )
            .text("### 4. Collateral Security and Prepayment Covenants\n")
            .text(
                "The borrower pledges first pari passu charge over declared residential and movable assets. "
                "Foreclosure and partial prepayment are permitted following completion of twelve continuous monthly "
                "installments without punitive charges. Prepayment requests submitted prior to twelve EMIs shall attract "
                "a standardized prepayment charge of two percent on the outstanding principal balance. "
                "All insurance covers over mortgaged property must name the Lender as primary loss payee.\n\n"
            )
            .text("### 5. Borrower KYC Dossier and Disbursement Mandate\n")
            .text(
                "Statutory KYC identity verification was completed prior to loan execution. "
                "Borrower identity is verified via Aadhaar number "
            )
            .pii("AADHAAR", adh_fmt)
            .text(" and Permanent Account Number ")
            .pii("PAN", pan)
            .text(". Loan disbursement shall be credited via RTGS through IFSC code ")
            .pii("IFSC", "TERR0004567")
            .text(" directly into borrower account ")
            .pii("BANK_ACCOUNT", acct)
            .text(". The declared primary residential address is ")
            .pii("STREET_ADDRESS", addr)
            .text(". Verified date of birth is ")
            .pii("DATE_OF_BIRTH", dob)
            .text(". For loan service notifications, borrower contact mobile is ")
            .pii("INDIAN_MOBILE", "+91 98451 11223")
            .text(" and official email is ")
            .pii("EMAIL_ADDRESS", "borrower.desk@terrawealth.example")
            .text(". For periodic interest reminders, the UPI handle ")
            .pii("UPI", "borrower.emi@okhdfcbank")
            .text(" is authenticated.\n\n")
            .text("### 4. Guarantor Covenants and Default Remedies\n")
            .text(
                "Personal repayment surety is unconditionally provided by Guarantor "
            )
            .pii("PERSON", guarantor)
            .text(
                ". Upon payment default exceeding 60 calendar days, the Lender reserves full rights "
                "to invoke asset repossession, file debt recovery claims, and declare acceleration.\n\n"
            )
            .text("### 5. Governing Law and Arbitration Jurisdiction\n")
            .text(
                "This agreement shall be governed by the laws of India, with exclusive arbitral jurisdiction "
                "vested in the competent commercial tribunals at Bengaluru.\n"
            )
        )
        docs.append((fname, "loan_agreement", b.build()))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. HOSPITAL DISCHARGE SUMMARIES (10 Documents)
    # ─────────────────────────────────────────────────────────────────────────
    hosp_configs = [
        # NovaCrest Hospital (Docs 1-4)
        ("hospital_discharge_01.txt", "NovaCrest Hospital & Research Institute", "Acute Calculous Cholecystitis", "Clinically stable and afebrile", "5 days post-discharge", "Amoxicillin-Clavulanate 625mg twice daily", "UH889021", "IP2026MED77412", "Room 205, Silver Residency, JP Nagar, Bengaluru, Karnataka 560078", "14-08-1988"),
        ("hospital_discharge_02.txt", "NovaCrest Hospital & Research Institute", "Laparoscopic Appendectomy", "Ambulatory with minimal wound pain", "7 days post-discharge", "Cefixime 200mg twice daily for 5 days", "UHID: 44109823", "IP-2026-MED-88123", "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066", "22-11-1985"),
        ("hospital_discharge_03.txt", "NovaCrest Hospital & Research Institute", "Right Inguinal Hernia Mesh Repair", "Hemodynamically stable, wound clean", "10 days post-discharge", "Ciprofloxacin 500mg twice daily with Paracetamol", "UH-889021", "IP-2026-MED-77412", "Apartment 5A, Lotus Enclave, Adyar, Chennai, Tamil Nadu 600020", "D O B : 03-05-1992"),
        ("hospital_discharge_04.txt", "NovaCrest Hospital & Research Institute", "Left Knee Meniscal Debridement", "Pain managed, non-weight bearing on crutches", "14 days post-discharge", "Aceclofenac 100mg twice daily with Rabeprazole", "UH-1092834", "IP-2026-MED-99124", "Plot 88, Okhla Industrial Area Phase 3, New Delhi 110020", "19-03-1990"),
        # Apex Care Clinic (Docs 5-7)
        ("hospital_discharge_05.txt", "Apex Care Multispecialty Clinic", "Coronary Angioplasty with Drug-Eluting Stent", "Stable sinus rhythm with normal hemodynamics", "7 days post-discharge", "Aspirin 75mg with Clopidogrel 75mg once daily", "Patient Hospital ID: 98451230", "IP-2026-CARD-55102", "c/o Rajesh Gupta, Civil Lines, Jaipur, Rajasthan 302006", "11-12-1971"),
        ("hospital_discharge_06.txt", "Apex Care Multispecialty Clinic", "Paroxysmal Atrial Fibrillation Managed", "Cardiovascular stability restored", "14 days post-discharge", "Metoprolol Succinate 50mg daily in morning", "UH-776655", "IP-2026-CARD-55103", "Sector 18, Block C, Vashi, Navi Mumbai, Maharashtra 400703", "28-09-1994"),
        ("hospital_discharge_07.txt", "Apex Care Multispecialty Clinic", "Acute Inferior Wall Myocardial Infarction", "Ejection fraction 50% preserved LV function", "21 days post-discharge", "Atorvastatin 40mg once daily at bedtime", "UH-998877", "IP-2026-CARD-55104", "House No 12, Sector 18, Vashi, Navi Mumbai, Maharashtra 400703", "15-06-1996"),
        # Aura Health (Docs 8-10)
        ("hospital_discharge_08.txt", "Aura Health Trauma Centre", "Lumbar L4-L5 Microdiscectomy", "Radicular neurological pain relieved, walking assisted", "7 days post-discharge", "Pregabalin 75mg at night with Tramadol SOS", "UH-332211", "IP-2026-ORTHO-11029", "Flat 102 Crystal Arcade, Indiranagar 100 Feet Road, Bengaluru, Karnataka 560038", "18-01-1987"),
        ("hospital_discharge_09.txt", "Aura Health Trauma Centre", "Closed Reduction Distal Radius Fracture", "Plaster cast intact, capillary refill satisfactory", "10 days post-discharge", "Calcium Carbonate 500mg with Vitamin D3 daily", "UH-665544", "IP-2026-ORTHO-11030", "Door No 14, 2nd Main Road, Gandhi Nagar, Adyar, Chennai, Tamil Nadu 600020", "09-12-1981"),
        ("hospital_discharge_10.txt", "Aura Health Trauma Centre", "Bilateral Total Knee Replacement", "Bilateral surgical wounds healing, active physiotherapy", "14 days post-discharge", "Enoxaparin 40mg subcutaneous injection for 10 days", "UH-554433", "IP-2026-ORTHO-11031", "Flat 201 Sri Sai Residency, Madhapur, Hyderabad, Telangana 500081", "25-04-1965"),
    ]

    for fname, hosp, diag, status, followup, meds, uhid_str, ip_str, addr, dob in hosp_configs:
        adh_raw = _generate_valid_aadhaar(fake)
        adh_fmt = f"{adh_raw[:4]} {adh_raw[4:8]} {adh_raw[8:]}"
        patient = fake.name()
        doctor = fake.name()

        b = DocBuilder(
            filename=fname,
            doc_type="hospital_discharge",
            key_facts={
                "primary_diagnosis": diag,
                "discharge_status": status,
                "follow_up_date": followup,
                "discharge_medications": meds,
            },
        )
        (
            b.text(f"# {hosp.upper()}\n")
            .text("## INPATIENT CLINICAL DISCHARGE SUMMARY AND CARE PLAN\n")
            .text(f"Clinical Case Reference: MED-DIS-V2-{fname.replace('.txt', '').upper()}\n")
            .text("Admission Date: 10th January 2026 | Discharge Date: 17th January 2026\n\n")
            .text("### 1. Patient Demographics and Registration Identifiers\n")
            .text("Patient Name: ")
            .pii("PERSON", patient)
            .text(" | Hospital UHID: ")
            .pii("UHID", uhid_str)
            .text(" | Inpatient Admission ID: ")
            .pii("UHID", ip_str)
            .text(".\n")
            .text("Aadhaar Identity Card: ")
            .pii("AADHAAR", adh_fmt)
            .text(" | Income Tax PAN: ")
            .pii("PAN", "ABCDE1234F")
            .text(" | Mobile Phone: ")
            .pii("INDIAN_MOBILE", "+91 98450 33445")
            .text(".\n")
            .text("Emergency Contact Email: ")
            .pii("EMAIL_ADDRESS", "clinical.desk@novahealth.example")
            .text(" | Residential Address: ")
            .pii("STREET_ADDRESS", addr)
            .text(" | Date of Birth: ")
            .pii("DATE_OF_BIRTH", dob)
            .text(".\n\n")
            .text("### 2. Clinical History and Primary Admission Diagnosis\n")
            .text(
                f"The patient presented with symptomatic clinical distress and underwent emergency evaluation. "
                f"Comprehensive investigations, imaging, and biochemical panels confirmed {diag}. "
                f"Standard clinical care pathways and evidence-based therapeutic interventions were executed successfully.\n\n"
            )
            .text("### 3. Diagnostic Investigations and Laboratory Findings\n")
            .text(
                "Admission hematology demonstrated complete blood count within acceptable post-acute tolerances. "
                "Serum electrolytes, renal function panels, and hepatic markers remained stable throughout observation. "
                "Post-procedural radiographic imaging confirmed anatomical alignment without extravasation or occult hematoma.\n\n"
            )
            .text("### 4. Inpatient Hospital Course and Discharge Physical Condition\n")
            .text(
                f"The inpatient recovery phase remained clinically uneventful. At discharge, the patient's condition is "
                f"evaluated as {status}. Vital parameters, hemodynamics, and surgical wounds are satisfactory.\n\n"
            )
            .text("### 4. Discharge Medications and Outpatient Care Regime\n")
            .text(
                f"The patient is discharged on oral pharmacotherapy: {meds}. "
                f"Mandatory outpatient follow-up review is scheduled for {followup} in the specialty clinic.\n\n"
            )
            .text("### 5. Nursing Observations and Post-Operative Rehabilitation\n")
            .text(
                "Serial clinical monitoring documented stable core body temperature, clear chest auscultation, "
                "and progressive ambulation under supervised nursing care. Patient demonstrated clear comprehension "
                "of activity restrictions, dietary modifications, and emergency warning signs warranting immediate readmission.\n\n"
            )
            .text("### 6. Attending Consultant Certification and Discharge Clearance\n")
            .text("Discharge authorized and verified by Chief Attending Consultant Dr. ")
            .pii("PERSON", doctor)
            .text(
                " (Registration KMC-44912-MD). Medical insurance reimbursement processing facilitated "
                "via settlement bank account "
            )
            .pii("BANK_ACCOUNT", "50100234918231")
            .text(" through IFSC ")
            .pii("IFSC", "NOVA0001234")
            .text(".\n")
        )
        docs.append((fname, "hospital_discharge", b.build()))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. INSURANCE CLAIMS (10 Documents)
    # ─────────────────────────────────────────────────────────────────────────
    ins_configs = [
        # Zenith General Insurance (Docs 1-4)
        ("insurance_claim_01.txt", "Zenith General Insurance Company Limited", "CLM-AUT-2026-10294", "INR 85,000", "INR 72,000", "INR 2,000 compulsory deductible", "Frontal bumper impact without structural chassis distortion"),
        ("insurance_claim_02.txt", "Zenith General Insurance Company Limited", "CLM-AUT-2026-10295", "INR 1,75,000", "INR 1,55,000", "INR 3,500 compulsory deductible", "Rear side impact with sheet metal replacement required"),
        ("insurance_claim_03.txt", "Zenith General Insurance Company Limited", "CLM-AUT-2026-10296", "INR 3,50,000", "INR 3,10,000", "INR 5,000 policy excess", "Engine water inundation during urban flooding incident"),
        ("insurance_claim_04.txt", "Zenith General Insurance Company Limited", "CLM-AUT-2026-10297", "INR 7,00,000", "INR 6,25,000", "INR 10,000 policy excess", "Multi-vehicle collision on highway with total bodywork repair"),
        # Fortress Shield (Docs 5-7)
        ("insurance_claim_05.txt", "Fortress Shield Underwriters Limited", "CLM-MED-2026-55219", "INR 2,10,000", "INR 1,90,000", "INR 2,500 standard excess", "Hospitalization for acute viral encephalitis and critical care"),
        ("insurance_claim_06.txt", "Fortress Shield Underwriters Limited", "CLM-MED-2026-55220", "INR 4,80,000", "INR 4,35,000", "INR 5,000 standard excess", "Elective spinal instrumentation and stabilization surgery"),
        ("insurance_claim_07.txt", "Fortress Shield Underwriters Limited", "CLM-MED-2026-55221", "INR 9,50,000", "INR 8,70,000", "INR 10,000 policy excess", "Emergency liver transplant stabilization and ICU stay"),
        # Paramount Care (Docs 8-10)
        ("insurance_claim_08.txt", "Paramount Care Assurance Limited", "CLM-FIR-2026-78103", "INR 5,00,000", "INR 4,50,000", "INR 15,000 commercial excess", "Warehouse electrical short circuit with partial inventory loss"),
        ("insurance_claim_09.txt", "Paramount Care Assurance Limited", "CLM-FIR-2026-78104", "INR 12,00,000", "INR 10,80,000", "INR 25,000 commercial excess", "Industrial factory machinery friction fire without foul play"),
        ("insurance_claim_10.txt", "Paramount Care Assurance Limited", "CLM-FIR-2026-78105", "INR 25,00,000", "INR 22,50,000", "INR 50,000 commercial excess", "Chemical processing laboratory containment failure and burn loss"),
    ]

    for fname, insurer, clm_no, claimed, approved, ded, survey in ins_configs:
        adh_raw = _generate_valid_aadhaar(fake)
        adh_fmt = f"{adh_raw[:4]} {adh_raw[4:8]} {adh_raw[8:]}"
        claimant = fake.name()
        surveyor = fake.name()

        b = DocBuilder(
            filename=fname,
            doc_type="insurance_claim",
            key_facts={
                "claim_number": clm_no,
                "claimed_amount": claimed,
                "approved_amount": approved,
                "deductible": ded,
                "surveyor_assessment": survey,
            },
        )
        (
            b.text(f"# {insurer.upper()}\n")
            .text("## FORMAL LOSS ADJUSTMENT AND SETTLEMENT VOUCHER\n")
            .text(f"Claim Tracking Number: {clm_no}\n")
            .text("Policy Year: 2025-2026 | Assessment Status: Approved for Remittance\n\n")
            .text("### 1. Policyholder Demographics and Cover Details\n")
            .text("Policyholder: ")
            .pii("PERSON", claimant)
            .text(f" | Claim Reference: {clm_no} | Policy Code: POL-ZEN-88910.\n")
            .text("Identity Aadhaar Number: ")
            .pii("AADHAAR", adh_fmt)
            .text(" | Income Tax PAN: ")
            .pii("PAN", "ABCDE1234F")
            .text(" | Mobile: ")
            .pii("INDIAN_MOBILE", "+91 98451 88990")
            .text(".\n")
            .text("Contact Email: ")
            .pii("EMAIL_ADDRESS", "claims.desk@zenithshield.example")
            .text(" | Residential Address: ")
            .pii("STREET_ADDRESS", "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066")
            .text(" | Date of Birth: ")
            .pii("DATE_OF_BIRTH", "14-08-1988")
            .text(".\n\n")
            .text("### 2. Loss Incident Description and Claim Quantum\n")
            .text(
                f"The insured event was reported under policy conditions. Initial gross indemnity claimed was {claimed}. "
                f"Independent technical inspection and loss assessment was conducted by Licensed Surveyor "
            )
            .pii("PERSON", surveyor)
            .text(
                f" (Licence IRDAI-SLA-99210), who verified: {survey}.\n\n"
            )
            .text("### 3. Settlement Calculation and Policy Deductibles\n")
            .text(
                f"Following depreciation adjustment and application of {ded}, the net approved indemnity "
                f"payable to the claimant is finalized at {approved}.\n\n"
            )
            .text("### 4. Technical Loss Verification and Salvage Assessment\n")
            .text(
                "Physical inspection confirmed damage consistency with declared cause of loss. "
                "No prior unreported structural distress or breach of policy warranties was identified. "
                "Salvage realization value was evaluated and adjusted in the finalized settlement computation.\n\n"
            )
            .text("### 5. Policy Conditions and Coverage Verification\n")
            .text(
                "Policy terms and underwriting endorsements were reviewed by the claims committee. "
                "All insurance premium payments are up-to-date with continuous cover unbroken across previous terms. "
                "No sub-limit exclusions or non-disclosure breaches apply to this verified claim settlement.\n\n"
            )
            .text("### 6. Subrogation Rights and Legal Release\n")
            .text(
                "Upon receipt of the approved settlement amount, the policyholder unconditionally releases the insurer "
                "from all future liabilities arising out of this loss event. The policyholder assigns all recovery and "
                "subrogation rights against responsible third parties to the insurer to the extent of indemnity paid.\n\n"
            )
            .text("### 7. Electronic Disbursement Authorization\n")
            .text(
                "Electronic NEFT/RTGS fund transfer of the approved sum is authorized to policyholder "
                "bank account "
            )
            .pii("BANK_ACCOUNT", "50100234918231")
            .text(" through IFSC code ")
            .pii("IFSC", "ZENI0001234")
            .text(". Immediate settlement notification dispatched to verified UPI handle ")
            .pii("UPI", "claimant.zenith@okhdfcbank")
            .text(".\n")
        )
        docs.append((fname, "insurance_claim", b.build()))

    # ─────────────────────────────────────────────────────────────────────────
    # 5. KYC ONBOARDING FORMS (10 Documents)
    # ─────────────────────────────────────────────────────────────────────────
    kyc_configs = [
        # Beacon Mercantile Bank (Docs 1-4)
        ("kyc_form_01.txt", "Beacon Mercantile Bank Limited", "Resident Individual Demat Account", "Low Risk Category", "DigiLocker VIPV", "India exclusively"),
        ("kyc_form_02.txt", "Beacon Mercantile Bank Limited", "Non-Resident External Savings Account", "High Risk Tier-1 Category", "Aadhaar e-KYC Biometric", "United Arab Emirates and India"),
        ("kyc_form_03.txt", "Beacon Mercantile Bank Limited", "Corporate Custody Trading Account", "Medium Risk Category", "Offline Attestation", "India exclusively"),
        ("kyc_form_04.txt", "Beacon Mercantile Bank Limited", "High-Net-Worth Portfolio Account", "Medium Risk Category", "Video In-Person Verification", "Singapore and India treaty"),
        # Solaris Premier Wealth (Docs 5-7)
        ("kyc_form_05.txt", "Solaris Premier Wealth Advisory Limited", "Discretionary PMS Individual Account", "Low Risk Category", "DigiLocker VIPV", "India exclusively"),
        ("kyc_form_06.txt", "Solaris Premier Wealth Advisory Limited", "Non-Discretionary Wealth Folio", "Medium Risk Category", "Aadhaar e-KYC Biometric", "India exclusively"),
        ("kyc_form_07.txt", "Solaris Premier Wealth Advisory Limited", "Global NRI Wealth Mandate", "High Risk Tier-1 Category", "Physical In-Person Verification", "United Kingdom and India"),
        # SilverOak Rural Credit (Docs 8-10)
        ("kyc_form_08.txt", "SilverOak Rural Credit Cooperative", "Agricultural Term Credit Member Account", "Low Risk Category", "Aadhaar Biometric VIPV", "India exclusively"),
        ("kyc_form_09.txt", "SilverOak Rural Credit Cooperative", "Rural Cooperative Savings Folio", "Low Risk Category", "Offline Branch In-Person", "India exclusively"),
        ("kyc_form_10.txt", "SilverOak Rural Credit Cooperative", "MSME Enterprise Current Account", "Medium Risk Category", "DigiLocker VIPV", "India exclusively"),
    ]

    for fname, inst, acct_type, risk, verif, tax in kyc_configs:
        adh_raw = _generate_valid_aadhaar(fake)
        adh_fmt = f"{adh_raw[:4]} {adh_raw[4:8]} {adh_raw[8:]}"
        client = fake.name()
        officer = fake.name()

        b = DocBuilder(
            filename=fname,
            doc_type="kyc_form",
            key_facts={
                "account_type": acct_type,
                "risk_category": risk,
                "verification_mode": verif,
                "tax_residency": tax,
            },
        )
        (
            b.text(f"# {inst.upper()}\n")
            .text("## STATUTORY CLIENT DUE DILIGENCE AND KYC VERIFICATION DOSSIER\n")
            .text(f"Dossier Reference: KYC-V2-{fname.replace('.txt', '').upper()}\n")
            .text("Regulatory Protocol: PMLA 2002 | Assessment Cycle: 2026 Annual\n\n")
            .text("### 1. Client Identity and Account Classification\n")
            .text("Applicant Full Legal Name: ")
            .pii("PERSON", client)
            .text(f" | Applied Account Category: {acct_type} | Risk Tier: {risk}.\n")
            .text("Primary Identification Aadhaar: ")
            .pii("AADHAAR", adh_fmt)
            .text(" | Income Tax PAN: ")
            .pii("PAN", "ABCDE1234F")
            .text(" | Registered Mobile: ")
            .pii("INDIAN_MOBILE", "+91 98450 77889")
            .text(".\n")
            .text("Primary Email Address: ")
            .pii("EMAIL_ADDRESS", "kyc.client@solariswealth.example")
            .text(" | Domicile Address: ")
            .pii("STREET_ADDRESS", "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066")
            .text(" | Date of Birth: ")
            .pii("DATE_OF_BIRTH", "14-08-1988")
            .text(".\n\n")
            .text("### 2. Regulatory Due Diligence and In-Person Verification Mode\n")
            .text(
                f"Statutory identity verification was completed under SEBI/RBI regulations via {verif}. "
                f"The client declared tax residency as {tax}. FATCA self-certification confirms compliance.\n\n"
            )
            .text("### 3. Ultimate Beneficial Ownership and PEP Sanctions Declaration\n")
            .text(
                "The applicant submitted self-certification declaring absence of Politically Exposed Person (PEP) status. "
                "Screening against consolidated AML and counter-terrorist financing watchlists returned zero adverse matches. "
                "Ultimate beneficial ownership criteria are fully documented in compliance with central registry guidelines.\n\n"
            )
            .text("### 4. Nominee Succession Mandate and Attestation\n")
            .text(
                "The applicant registered a single nominee holding one hundred percent succession entitlement. "
                "Nominee identity was cross-referenced with national civil registration databases. "
                "The client executed digital e-sign attestation confirming accuracy of all declared dossier particulars.\n\n"
            )
            .text("### 5. Source of Funds and Annual Wealth Declaration\n")
            .text(
                "The client declared the primary source of funds as legitimate corporate remuneration and investment yields. "
                "Documentary proof of income, salary slips, and income tax computation forms were submitted for verification. "
                "The estimated annual turnover declaration exceeds twenty-five lakh rupees with zero suspicious transactions.\n\n"
            )
            .text("### 6. Linked Settlement Account and Nominee Declaration\n")
            .text(
                "Primary funds settlement mandate linked to verified bank account "
            )
            .pii("BANK_ACCOUNT", "50100234918231")
            .text(" maintained with IFSC code ")
            .pii("IFSC", "BEAC0001234")
            .text(". Digital mandate validated via UPI address ")
            .pii("UPI", "client.kyc@okhdfcbank")
            .text(".\n\n")
            .text("### 4. Compliance Officer Certification\n")
            .text("Verification executed and certified by Compliance Custodian ")
            .pii("PERSON", officer)
            .text(
                " (Officer ID COMP-88912). Records archived under anti-money laundering retention guidelines.\n"
            )
        )
        docs.append((fname, "kyc_form", b.build()))

    # ─────────────────────────────────────────────────────────────────────────
    # 6. VENDOR SERVICE AGREEMENTS (10 Documents — NEW CATEGORY 1)
    # ─────────────────────────────────────────────────────────────────────────
    vendor_configs = [
        # Starlight Cloud & Quantum Solstice (Docs 1-4)
        ("vendor_contract_01.txt", "Starlight Cloud Solutions Limited", "Quantum Solstice Labs", "INR 1,25,000 per month", "99.5% uptime guarantee", "30 calendar days written notice", "2% billing credit per 1 hour outage"),
        ("vendor_contract_02.txt", "Starlight Cloud Solutions Limited", "Quantum Solstice Labs", "INR 2,50,000 per month", "99.9% high-availability uptime", "60 calendar days written notice", "5% billing credit per 1 hour outage"),
        ("vendor_contract_03.txt", "Starlight Cloud Solutions Limited", "Quantum Solstice Labs", "INR 5,00,000 per month", "99.95% mission-critical uptime", "90 calendar days written notice", "10% billing credit per 1 hour outage"),
        ("vendor_contract_04.txt", "Starlight Cloud Solutions Limited", "Quantum Solstice Labs", "INR 8,50,000 per month", "99.99% fault-tolerant uptime", "120 calendar days written notice", "15% billing credit per 1 hour outage"),
        # SilverOak Logistics & Apex Crest (Docs 5-7)
        ("vendor_contract_05.txt", "SilverOak Logistics Network Limited", "Apex Crest Financial", "INR 1,80,000 per month", "99.0% standard freight uptime", "30 calendar days written notice", "3% service deduction per breach"),
        ("vendor_contract_06.txt", "SilverOak Logistics Network Limited", "Apex Crest Financial", "INR 3,60,000 per month", "99.5% priority freight uptime", "60 calendar days written notice", "5% service deduction per breach"),
        ("vendor_contract_07.txt", "SilverOak Logistics Network Limited", "Apex Crest Financial", "INR 7,20,000 per month", "99.9% express freight uptime", "90 calendar days written notice", "8% service deduction per breach"),
        # TerraTrust Digital & Pinnacle Urban (Docs 8-10)
        ("vendor_contract_08.txt", "TerraTrust Digital Systems Limited", "Pinnacle Urban Solutions", "INR 1,50,000 per month", "99.5% infrastructure availability", "30 calendar days written notice", "2.5% penalty per outage incident"),
        ("vendor_contract_09.txt", "TerraTrust Digital Systems Limited", "Pinnacle Urban Solutions", "INR 3,00,000 per month", "99.9% infrastructure availability", "60 calendar days written notice", "5.0% penalty per outage incident"),
        ("vendor_contract_10.txt", "TerraTrust Digital Systems Limited", "Pinnacle Urban Solutions", "INR 6,00,000 per month", "99.95% infrastructure availability", "90 calendar days written notice", "7.5% penalty per outage incident"),
    ]

    for fname, vendor, client_org, retainer, sla, term, penalty in vendor_configs:
        adh_raw = _generate_valid_aadhaar(fake)
        adh_fmt = f"{adh_raw[:4]} {adh_raw[4:8]} {adh_raw[8:]}"
        vendor_rep = fake.name()
        client_rep = fake.name()

        b = DocBuilder(
            filename=fname,
            doc_type="vendor_contract",
            key_facts={
                "monthly_retainer": retainer,
                "service_level_uptime": sla,
                "termination_notice": term,
                "penalty_rate": penalty,
            },
        )
        (
            b.text(f"# {vendor.upper()}\n")
            .text("## ENTERPRISE MANAGED SERVICES MASTER AGREEMENT\n")
            .text(f"Agreement ID: MSA-V2-{fname.replace('.txt', '').upper()}\n")
            .text("Effective Date: 1st February 2026 | Term: 24 Months Initial\n\n")
            .text("### 1. Engagement Scope and Contracting Parties\n")
            .text(
                f"This Master Services Agreement ('Agreement') is executed between {vendor} ('Vendor') "
                f"represented by Authorized Signatory "
            )
            .pii("PERSON", vendor_rep)
            .text(f" and Client {client_org} ('Client') represented by Representative ")
            .pii("PERSON", client_rep)
            .text(
                ". Vendor agrees to provide enterprise managed operations and hosting services.\n\n"
            )
            .text("### 2. Commercial Consideration and Retainer Fees\n")
            .text(
                f"In consideration for the managed services, Client covenants to pay a fixed commercial "
                f"monthly retainer of {retainer}. Invoices are generated monthly in arrears payable within 15 days.\n\n"
            )
            .text("### 3. Service Level Commitments and Penalties\n")
            .text(
                f"Vendor guarantees a service level availability commitment of {sla}. "
                f"In the event of unexcused service degradation exceeding allowable downtime windows, "
                f"Vendor shall issue service credits calculated at {penalty}.\n\n"
            )
            .text("### 4. Information Security and Data Protection Compliance\n")
            .text(
                "Vendor covenants to maintain ISO 27001 certified physical and logical security perimeters. "
                "All customer telemetry, transactional databases, and proprietary models processed in fulfillment of this "
                "agreement shall be encrypted at rest and in transit using industry-standard cryptographic algorithms.\n\n"
            )
            .text("### 5. Business Continuity and Disaster Recovery Obligations\n")
            .text(
                "Vendor maintains a redundant disaster recovery hot-site with automated replication. "
                "The recovery point objective (RPO) is established at under fifteen minutes, and recovery time objective (RTO) "
                "at under two hours during declared catastrophic events. Annual disaster recovery drill reports are provided to Client.\n\n"
            )
            .text("### 6. Intellectual Property Rights and Deliverable Ownership\n")
            .text(
                "All bespoke code, configurations, technical documentation, and architectural designs created by Vendor "
                "exclusively for Client under this agreement shall constitute work-made-for-hire and remain the sole property of Client. "
                "Pre-existing Vendor background intellectual property is licensed on a non-exclusive, perpetual basis.\n\n"
            )
            .text("### 7. Contractual Term and Termination Notice\n")
            .text(
                f"Either party may terminate this agreement for convenience upon providing {term}. "
                f"Immediate termination applies upon material breach uncured after 15 days.\n\n"
            )
            .text("### 8. Vendor Statutory Identifiers and Payment Mandate\n")
            .text("Vendor statutory tax identification PAN: ")
            .pii("PAN", "ABCDE1234F")
            .text(" | Signatory Aadhaar: ")
            .pii("AADHAAR", adh_fmt)
            .text(" | Contact Mobile: ")
            .pii("INDIAN_MOBILE", "+91 98450 66778")
            .text(".\n")
            .text("Official Billing Email: ")
            .pii("EMAIL_ADDRESS", "billing.services@starlightcloud.example")
            .text(" | Registered Corporate Office: ")
            .pii("STREET_ADDRESS", "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066")
            .text(" | Representative DOB: ")
            .pii("DATE_OF_BIRTH", "14-08-1988")
            .text(".\n")
            .text("Invoices shall be remitted to corporate bank account ")
            .pii("BANK_ACCOUNT", "50100234918231")
            .text(" via IFSC ")
            .pii("IFSC", "STAR0009876")
            .text(". Real-time invoice acknowledgement supported via UPI handle ")
            .pii("UPI", "vendor.settlement@okhdfcbank")
            .text(".\n")
        )
        docs.append((fname, "vendor_contract", b.build()))

    # ─────────────────────────────────────────────────────────────────────────
    # 7. COMMERCIAL LEASE AGREEMENTS (10 Documents — NEW CATEGORY 2)
    # ─────────────────────────────────────────────────────────────────────────
    lease_configs = [
        # Solaris Realty & Starlight Tech (Docs 1-4)
        ("lease_agreement_01.txt", "Solaris Realty Partners Limited", "Starlight Technologies", "INR 1,10,000 per month", "INR 3,30,000 (3 months rent)", "12 months mandatory lock-in", "5% annual escalation"),
        ("lease_agreement_02.txt", "Solaris Realty Partners Limited", "Starlight Technologies", "INR 2,25,000 per month", "INR 13,50,000 (6 months rent)", "24 months lock-in period", "7.5% biennial rent escalation"),
        ("lease_agreement_03.txt", "Solaris Realty Partners Limited", "Starlight Technologies", "INR 4,50,000 per month", "INR 40,50,000 (9 months rent)", "36 months commercial lock-in", "10% escalation every 3 years"),
        ("lease_agreement_04.txt", "Solaris Realty Partners Limited", "Starlight Technologies", "INR 9,00,000 per month", "INR 1,08,00,000 (12 months rent)", "60 months commercial lock-in", "12% escalation every 3 years"),
        # Pinnacle Urban & TerraTrust (Docs 5-7)
        ("lease_agreement_05.txt", "Pinnacle Urban Solutions Limited", "TerraTrust Capital", "INR 1,50,000 per month", "INR 4,50,000 (3 months rent)", "12 months mandatory lock-in", "5% annual escalation"),
        ("lease_agreement_06.txt", "Pinnacle Urban Solutions Limited", "TerraTrust Capital", "INR 3,20,000 per month", "INR 19,20,000 (6 months rent)", "24 months lock-in period", "7% biennial rent escalation"),
        ("lease_agreement_07.txt", "Pinnacle Urban Solutions Limited", "TerraTrust Capital", "INR 6,50,000 per month", "INR 58,50,000 (9 months rent)", "36 months commercial lock-in", "9% escalation every 3 years"),
        # Aura Commercial & SilverOak (Docs 8-10)
        ("lease_agreement_08.txt", "Aura Commercial Estates Limited", "SilverOak Logistics", "INR 1,75,000 per month", "INR 5,25,000 (3 months rent)", "12 months mandatory lock-in", "5% annual escalation"),
        ("lease_agreement_09.txt", "Aura Commercial Estates Limited", "SilverOak Logistics", "INR 3,50,000 per month", "INR 21,00,000 (6 months rent)", "24 months lock-in period", "8% biennial rent escalation"),
        ("lease_agreement_10.txt", "Aura Commercial Estates Limited", "SilverOak Logistics", "INR 7,00,000 per month", "INR 63,00,000 (9 months rent)", "36 months commercial lock-in", "10% escalation every 3 years"),
    ]

    for fname, landlord, tenant_org, rent, dep, lockin, esc in lease_configs:
        adh_raw = _generate_valid_aadhaar(fake)
        adh_fmt = f"{adh_raw[:4]} {adh_raw[4:8]} {adh_raw[8:]}"
        landlord_rep = fake.name()
        tenant_rep = fake.name()

        b = DocBuilder(
            filename=fname,
            doc_type="lease_agreement",
            key_facts={
                "monthly_rent": rent,
                "security_deposit": dep,
                "lock_in_period": lockin,
                "escalation_rate": esc,
            },
        )
        (
            b.text(f"# {landlord.upper()}\n")
            .text("## COMMERCIAL INDENTURE OF LEASE AND PREMISES LICENSE\n")
            .text(f"Indenture ID: LEASE-V2-{fname.replace('.txt', '').upper()}\n")
            .text("Term: 36 Months Fixed | Tenancy Commencement: 1st March 2026\n\n")
            .text("### 1. Demised Premises and Parties to the Indenture\n")
            .text(
                f"This Commercial Indenture of Lease is entered into between {landlord} ('Lessor') "
                f"represented by Property Custodian "
            )
            .pii("PERSON", landlord_rep)
            .text(f" and Lessee {tenant_org} ('Lessee') represented by ")
            .pii("PERSON", tenant_rep)
            .text(
                ". Lessor demises commercial office space for exclusive enterprise technology operations.\n\n"
            )
            .text("### 2. Rent Consideration, Security Deposit, and Periodic Escalation\n")
            .text(
                f"Lessee covenants to pay Lessor a net monthly lease rental of {rent}, "
                f"payable in advance on or before the 5th day of each calendar month. "
                f"Prior to handover, Lessee deposits an interest-free refundable security deposit of {dep}. "
                f"The rental consideration shall be subject to {esc}.\n\n"
            )
            .text("### 3. Tenancy Term and Mandatory Lock-In Period\n")
            .text(
                f"The initial tenancy term is 36 months, subject to a {lockin}. "
                f"Neither party may terminate the tenancy during the lock-in without full rental compensation.\n\n"
            )
            .text("### 4. Permitted Commercial Use and Facility Maintenance\n")
            .text(
                "The demised premises shall be utilized exclusively for lawful software engineering and administrative office activities. "
                "Lessee shall maintain interior fixtures, electrical distributions, and air conditioning equipment in good tenantable order. "
                "Structural repairs, exterior facades, and common building utilities remain the responsibility of Lessor.\n\n"
            )
            .text("### 5. Handover Protocol and Demised Premises Surrender\n")
            .text(
                "Upon expiry or valid termination of the lease indenture, Lessee covenants to peaceably deliver vacant possession "
                "of the demised premises to Lessor in good original condition, reasonable wear and tear excepted. "
                "All Lessee installed modular partitions, communication cables, and corporate signages shall be cleanly removed.\n\n"
            )
            .text("### 6. Premises Insurance and Mutual Indemnification\n")
            .text(
                "Lessee shall maintain comprehensive commercial general liability insurance and fire property insurance "
                "covering all internal assets and tenant improvements. Lessor maintains standard building structural cover. "
                "Each party indemnifies the other against direct third-party tort claims arising from gross operational negligence.\n\n"
            )
            .text("### 7. Lessor Credentials and Remittance Mandate\n")
            .text("Lessor Permanent Account Number: ")
            .pii("PAN", "ABCDE1234F")
            .text(" | Authorized Custodian Aadhaar: ")
            .pii("AADHAAR", adh_fmt)
            .text(" | Mobile: ")
            .pii("INDIAN_MOBILE", "+91 98450 55667")
            .text(".\n")
            .text("Contact Email: ")
            .pii("EMAIL_ADDRESS", "estates.leasing@solarisrealty.example")
            .text(" | Landlord Address: ")
            .pii("STREET_ADDRESS", "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066")
            .text(" | Custodian DOB: ")
            .pii("DATE_OF_BIRTH", "14-08-1988")
            .text(".\n")
            .text("Monthly rental remittances shall be transferred to bank account ")
            .pii("BANK_ACCOUNT", "50100234918231")
            .text(" via IFSC code ")
            .pii("IFSC", "SOLA0001234")
            .text(". Lease payment receipts confirmed via UPI address ")
            .pii("UPI", "lessor.rent@okhdfcbank")
            .text(".\n")
        )
        docs.append((fname, "lease_agreement", b.build()))

    return docs


def main() -> None:
    """Generate all V2 documents and output ground truth JSON."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Generating 70 synthetic documents for Corpus V2...")

    DOCS_V2_DIR.mkdir(parents=True, exist_ok=True)
    docs = generate_all_v2_documents()

    gt_documents: list[dict[str, Any]] = []

    for fname, doc_type, (full_text, meta) in docs:
        out_file = DOCS_V2_DIR / fname
        out_file.write_text(full_text, encoding="utf-8")
        gt_documents.append(meta)
        logger.info("Wrote %s (%d words, %d PII spans)", fname, meta["word_count"], len(meta["pii_entities"]))

    gt_data = {
        "version": "2.0",
        "description": "VeilRAG Corpus V2 Synthetic Enterprise Benchmark (70 documents)",
        "total_documents": len(gt_documents),
        "documents": gt_documents,
    }

    GROUND_TRUTH_FILE.write_text(json.dumps(gt_data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Ground truth written to %s (%d documents recorded)", GROUND_TRUTH_FILE, len(gt_documents))
    print(f"Generated {len(gt_documents)} documents in {DOCS_V2_DIR} with ground truth in {GROUND_TRUTH_FILE}")


if __name__ == "__main__":
    main()
