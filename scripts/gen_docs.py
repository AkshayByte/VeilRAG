"""Synthetic enterprise document generator for VeilRAG ingestion evaluation.

Generates 15 realistic Indian business documents (300-1500 words each) across 5 categories:
- HR policies (notice period, leave policy, working hours)
- Loan agreements (loan amount, interest rate, tenure)
- Hospital discharge summaries (diagnosis, status, follow-up)
- Insurance claims (claim ID, claimed amount, approved amount)
- KYC onboarding forms (account type, risk rating, verification mode)

Each document plants both in-scope PII and known out-of-scope gaps, and records exact
character spans and ground truth business facts into `data/docs/_ground_truth.json`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from faker import Faker

from src.sanitizer.detectors import validate_verhoeff

logger = logging.getLogger(__name__)

DOCS_DIR = Path("data/docs")
GROUND_TRUTH_FILE = DOCS_DIR / "_ground_truth.json"


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


def generate_all_documents() -> list[tuple[str, str, tuple[str, dict[str, Any]]]]:
    """Generate the 15 synthetic enterprise documents."""
    fake = Faker("en_IN")
    fake.seed_instance(42)

    docs: list[tuple[str, str, tuple[str, dict[str, Any]]]] = []

    # =========================================================================
    # 1. HR POLICIES (3 Documents)
    # =========================================================================

    # HR Policy 1: Acme Software Solutions
    b1 = DocBuilder(
        filename="hr_policy_01.txt",
        doc_type="hr_policy",
        key_facts={
            "notice_period": "60 calendar days",
            "working_hours": "9:30 AM to 6:30 PM Monday through Friday",
            "annual_leave": "24 days of paid privilege leave",
            "probation_period": "6 months",
        },
    )
    raw_adh1 = _generate_valid_aadhaar(fake)
    adh_fmt1 = f"{raw_adh1[:4]} {raw_adh1[4:8]} {raw_adh1[8:]}"

    (
        b1.text("# ACME SOFTWARE SOLUTIONS PRIVATE LIMITED\n")
        .text("## COMPREHENSIVE HUMAN RESOURCES EMPLOYMENT POLICY AND CODE OF CONDUCT\n")
        .text("Document Reference: HR-POL-2026-BLR-01\n")
        .text("Effective Date: 1st January 2026 | Revision: 4.2\n\n")
        .text("### 1. Objective and Applicability\n")
        .text(
            "This comprehensive employment handbook defines the service terms, professional obligations, "
            "code of workplace ethics, and operational standards applicable to all full-time, part-time, "
            "and probationary personnel employed by Acme Software Solutions Private Limited across all its "
            "technology development centers in Bengaluru, Hyderabad, and Pune. Adherence to this framework "
            "is a mandatory condition of continuing employment.\n\n"
        )
        .text("### 2. Standard Working Hours and Attendance Guidelines\n")
        .text(
            "The official operating business hours of the corporation are firmly designated as 9:30 AM to 6:30 PM Monday through Friday, "
            "comprising an eight-hour productive workday alongside an allotted one-hour window for lunch and personal refreshment. "
            "Engineering associates assigned to client operational engagements may observe staggered rotas under direct managerial dispensation. "
            "All personnel are required to record biometric digital timestamps upon ingress and egress at company premises.\n\n"
        )
        .text("### 3. Annual Leave Entitlements and Separation Notice Period\n")
        .text(
            "Each confirmed associate is granted 24 days of paid privilege leave per calendar cycle, accrued proportionately on a monthly basis. "
            "Associates also receive twelve days of paid casual sickness allowances subject to clinical certification. "
            "Upon voluntary resignation or formal separation, the mandatory contractual notice period is exactly 60 calendar days. "
            "During the initial statutory probation period of 6 months, separation notice may be executed within thirty calendar days by either party.\n\n"
        )
        .text("### 4. Code of Conduct and Regulatory Compliance Contact\n")
        .text(
            "The organization upholds zero tolerance for harassment, insider transactions, intellectual property misappropriation, and unauthorized "
            "disclosure of proprietary algorithms. For confidential inquiries regarding employee grievances or compliance reports, associates must contact "
            "Chief Human Resources Officer "
        )
        .pii("PERSON", "Ananya Sharma")
        .text(" at official corporate email ")
        .pii("EMAIL_ADDRESS", "ananya.sharma@acmesoftware.co.in")
        .text(" or reach the executive grievance desk on mobile ")
        .pii("INDIAN_MOBILE", "+91 98451 23450")
        .text(".\n\n")
        .text("### 5. Statutory Documentation and Employee Verification Dossier\n")
        .text(
            "Every employee must furnish verified identity credentials prior to payroll onboarding. For internal audit verification, HR Custodian "
        )
        .pii("PERSON", "Rajesh Nambiar")
        .text(" maintains record verification. The associate submitted Aadhaar number ")
        .pii("AADHAAR", adh_fmt1)
        .text(" along with permanent account number (PAN) ")
        .pii("PAN", "ABCPS1234K")
        .text(" for statutory income tax deduction. Bank salary disbursement occurs via IFSC code ")
        .pii("IFSC", "HDFC0001234")
        .text(" into corporate salary account ")
        .pii("BANK_ACCOUNT", "50100234918231", in_scope=False)
        .text(". The employee's residential domicile is logged as ")
        .pii(
            "STREET_ADDRESS",
            "Flat 402 Palm Meadows, Whitefield Main Road, Bengaluru, Karnataka 560066",
            in_scope=False,
        )
        .text(", with verified date of birth ")
        .pii("DATE_OF_BIRTH", "14-08-1988", in_scope=False)
        .text(". For corporate event reimbursements, associate UPI handle ")
        .pii("UPI", "ananya.sharma@okhdfcbank")
        .text(" is authenticated in the ERP.\n\n")
        .text("### 6. Information Security and Intellectual Property Safeguards\n")
        .text(
            "Associates shall not transfer source repositories, customer databases, architectural blueprints, or encryption materials outside "
            "sanctioned virtual perimeters. Breach of confidentiality covenants constitutes gross professional misconduct warranting immediate summary "
            "termination and statutory prosecution under the Information Technology Act 2000.\n"
        )
    )
    docs.append(("hr_policy_01.txt", "hr_policy", b1.build()))

    # HR Policy 2: Bharat Logistics Enterprises
    b2 = DocBuilder(
        filename="hr_policy_02.txt",
        doc_type="hr_policy",
        key_facts={
            "notice_period": "90 calendar days",
            "working_hours": "9:00 AM to 6:00 PM Monday through Saturday",
            "annual_leave": "18 days of paid privilege leave",
            "probation_period": "3 months",
        },
    )
    raw_adh2 = _generate_valid_aadhaar(fake)
    adh_fmt2 = f"{raw_adh2[:4]}-{raw_adh2[4:8]}-{raw_adh2[8:]}"

    (
        b2.text("# BHARAT LOGISTICS AND SUPPLY CHAIN ENTERPRISES\n")
        .text("## OPERATIONAL WORKFORCE REGULATIONS AND SERVICE GOVERNANCE MANUAL\n")
        .text("Manual Reference: BL-HR-REG-2026-MUM-02\n")
        .text("Published: 15th January 2026 | Authority: Board of Directors\n\n")
        .text("### 1. Scope and Preamble\n")
        .text(
            "Bharat Logistics operates warehousing nodes, intermodal freight corridors, and delivery depots across western and northern India. "
            "This operational directive governs all station supervisors, dispatch handlers, fleet coordinators, and administrative executives. "
            "Consistent workplace discipline and strict adherence to transport safety norms are strictly enforced across all distribution hubs.\n\n"
        )
        .text("### 2. Duty Hours, Shift Scheduling, and Field Attendance\n")
        .text(
            "Field operations, supply logistics, and hub management observe designated shift timings: standard working hours are 9:00 AM to 6:00 PM Monday through Saturday. "
            "Hub supervisors managing 24/7 cross-dock operations are rostered on three rotating eight-hour cycles. "
            "Punctuality at depot gates is tracked electronically; unauthorized absence exceeding three consecutive shifts without intimation shall be deemed job abandonment.\n\n"
        )
        .text("### 3. Leave Policy and Separation Protocols\n")
        .text(
            "Permanent operations personnel receive 18 days of paid privilege leave annually, with up to nine days eligible for cash encashment upon financial year closure. "
            "Ten statutory festival holidays are notified annually per regional labour commissioner bulletins. "
            "In consideration of operational business continuity across freight channels, the mandatory notice period is 90 calendar days for all confirmed staff. "
            "The initial probation period is 3 months, during which performance evaluations occur fortnightly.\n\n"
        )
        .text("### 4. Workplace Welfare, Safety, and Grievance Escalation\n")
        .text(
            "All warehouse associates must wear personal protective equipment, safety boots, and high-visibility jackets inside loading bays. "
            "For confidential reporting of workplace hazards, health issues, or administrative grievances, contact Head of Workforce Welfare "
        )
        .pii("PERSON", "Vikramaditya Rathore")
        .text(" at email ")
        .pii("EMAIL_ADDRESS", "vikram.rathore@bharatlogistics.in")
        .text(" or via official mobile ")
        .pii("INDIAN_MOBILE", "+91 97112 34567")
        .text(".\n\n")
        .text("### 5. Personnel Registry and Statutory Identity Records\n")
        .text(
            "For regulatory compliance under the Factories Act and Contract Labour Regulations, Regional HR Inspector "
        )
        .pii("PERSON", "Sunita Deshmukh")
        .text(" maintains employee files. Employee identification record contains verified Aadhaar ")
        .pii("AADHAAR", adh_fmt2)
        .text(" and Income Tax PAN ")
        .pii("PAN", "BRDPS9876C")
        .text(". Monthly wage transfer is cleared through IFSC code ")
        .pii("IFSC", "SBIN0004567")
        .text(" to savings account ")
        .pii("BANK_ACCOUNT", "20489912034", in_scope=False)
        .text(". Recorded primary address is ")
        .pii(
            "STREET_ADDRESS",
            "House No 12, Sector 18, Vashi, Navi Mumbai, Maharashtra 400703",
            in_scope=False,
        )
        .text(", born on ")
        .pii("DATE_OF_BIRTH", "22-11-1985", in_scope=False)
        .text(". Secondary reimbursement account links to UPI id ")
        .pii("UPI", "vikram.rathore@oksbi")
        .text(" for quick settlement of travel allowances.\n\n")
        .text("### 6. Environmental and Hazardous Materials Governance\n")
        .text(
            "Handlers transporting volatile chemicals, lithium batteries, or temperature-sensitive pharmaceuticals must maintain certified manifests. "
            "Negligent handling resulting in environmental contamination shall trigger immediate civil and criminal indemnification procedures.\n"
        )
    )
    docs.append(("hr_policy_02.txt", "hr_policy", b2.build()))

    # HR Policy 3: Nexus Fintech
    b3 = DocBuilder(
        filename="hr_policy_03.txt",
        doc_type="hr_policy",
        key_facts={
            "notice_period": "30 calendar days",
            "working_hours": "10:00 AM to 7:00 PM with flexible core hours",
            "annual_leave": "30 days of paid privilege leave",
            "probation_period": "6 months",
        },
    )
    raw_adh3 = _generate_valid_aadhaar(fake)
    adh_fmt3 = f"{raw_adh3[:4]} {raw_adh3[4:8]} {raw_adh3[8:]}"

    (
        b3.text("# NEXUS FINTECH SOLUTIONS PRIVATE LIMITED\n")
        .text("## TALENT MANAGEMENT POLICIES AND DIGITAL WORKPLACE CHARTER\n")
        .text("Document Code: NX-HR-DOC-2026-DEL-03\n")
        .text("Approved by People Committee | Effective: 10th February 2026\n\n")
        .text("### 1. Introduction and Modern Work Culture\n")
        .text(
            "Nexus Fintech provides cloud-native payment switching, payment gateway APIs, and embedded finance rails to domestic banks. "
            "Our employment policies emphasize autonomy, ethical conduct, strict regulatory safeguarding of banking credentials, "
            "and continuous professional growth. This document binds all product engineers, data analysts, and compliance specialists.\n\n"
        )
        .text("### 2. Working Hours, Hybrid Workplace, and Core Collaborative Intervals\n")
        .text(
            "Nexus operates under a modern hybrid schedule. Official working hours are 10:00 AM to 7:00 PM with flexible core hours, "
            "requiring real-time availability on corporate collaboration tools between 11:30 AM and 4:30 PM for team standups and security reviews. "
            "Associates may work remotely up to two days per working week with prior team lead notification and VPN compliance clearance.\n\n"
        )
        .text("### 3. Leave Entitlements, Wellness Days, and Separation Guidelines\n")
        .text(
            "To promote work-life integration, Nexus provides 30 days of paid privilege leave per annum along with mental wellness quarterly days. "
            "Maternity leave covers 26 paid weeks in accordance with statutory mandates, while paternity leave covers 4 paid weeks. "
            "Should an associate elect to seek opportunities outside Nexus, the contractual notice period is 30 calendar days. "
            "All new campus and lateral hires undergo an initial probation period of 6 months before tenure confirmation.\n\n"
        )
        .text("### 4. Integrity, Anti-Bribery, and Ethical Disclosures\n")
        .text(
            "Employees are strictly prohibited from soliciting gifts, favors, or pecuniary commissions from financial vendor partners. "
            "To report policy non-compliance, financial discrepancies, or security concerns, contact Director of Legal and People "
        )
        .pii("PERSON", "Kavita Krishnamurthy")
        .text(" at corporate address ")
        .pii("EMAIL_ADDRESS", "kavita.k@nexusfintech.in")
        .text(" or emergency cell ")
        .pii("INDIAN_MOBILE", "+91 99887 76655")
        .text(".\n\n")
        .text("### 5. Personnel Records and Compliance Authentication\n")
        .text(
            "Statutory documentation for payroll and provident fund compliance is inspected by Operations Lead "
        )
        .pii("PERSON", "Arvind Swaminathan")
        .text(". The employee's government identity file authenticates UIDAI Aadhaar number ")
        .pii("AADHAAR", adh_fmt3)
        .text(" and PAN card ")
        .pii("PAN", "CKMPK4321E")
        .text(". Compensation credits are processed under IFSC ")
        .pii("IFSC", "ICIC0000456")
        .text(" to account ")
        .pii("BANK_ACCOUNT", "004501589123", in_scope=False)
        .text(". Permanent registered domicile is recorded as ")
        .pii(
            "STREET_ADDRESS",
            "Tower B Apt 901, Cyber City Residency, DLF Phase 2, Gurugram, Haryana 122002",
            in_scope=False,
        )
        .text(", date of birth registered as ")
        .pii("DATE_OF_BIRTH", "03-05-1992", in_scope=False)
        .text(". Associate reimbursement UPI ID is registered as ")
        .pii("UPI", "kavita.k@okaxis")
        .text(" for quick cloud expense settlements.\n\n")
        .text("### 6. Client Confidentiality and Algorithmic Security\n")
        .text(
            "All cryptographic keys, API tokens, and customer transactional telemetry remain the exclusive property of Nexus Fintech. "
            "No employee shall duplicate or publish internal libraries or algorithmic code artifacts to personal cloud services.\n"
        )
    )
    docs.append(("hr_policy_03.txt", "hr_policy", b3.build()))

    # =========================================================================
    # 2. LOAN AGREEMENTS (3 Documents)
    # =========================================================================

    # Loan Agreement 1: Home Mortgage
    b4 = DocBuilder(
        filename="loan_agreement_01.txt",
        doc_type="loan_agreement",
        key_facts={
            "loan_amount": "INR 45,00,000",
            "interest_rate": "8.65% per annum floating",
            "tenure": "240 months",
            "processing_fee": "INR 10,000",
        },
    )
    raw_adh4 = _generate_valid_aadhaar(fake)
    adh_fmt4 = f"{raw_adh4[:4]} {raw_adh4[4:8]} {raw_adh4[8:]}"

    (
        b4.text("# HOUSING DEVELOPMENT LOAN SANCTION AND MORTGAGE AGREEMENT\n")
        .text("## CONTRACT REFERENCE: HDFC-MORT-2026-BLR-8921\n")
        .text("Executed at Bengaluru, Karnataka on this 18th day of February 2026\n\n")
        .text("### 1. Parties and Contractual Recitals\n")
        .text(
            "This Housing Finance Facility Agreement is entered into between Premier Housing Finance Limited (the Lender) "
            "and the individual mortgagor named herein (the Borrower). The Borrower has applied for financial assistance to purchase "
            "a residential apartment situated in Bengaluru urban limits. The Lender has evaluated borrower creditworthiness and agrees to grant "
            "the loan facility subject to the covenants, mortgage terms, and schedule stipulations set forth hereunder.\n\n"
        )
        .text("### 2. Loan Amount, Repayment Tenure, and Interest Rate Structure\n")
        .text(
            "The Lender sanctions a principal loan amount of INR 45,00,000 (Rupees Forty-Five Lakhs Only) payable across a total tenure of 240 months. "
            "The applicable interest rate is agreed at 8.65% per annum floating, pegged to the Lender Benchmark Prime Lending Rate (RPLR) minus 210 bps. "
            "Monthly Equated Installments (EMIs) shall be debited on the 5th day of every calendar month via National Automated Clearing House (NACH). "
            "A non-refundable administrative processing fee of INR 10,000 has been received and acknowledged by the Lender.\n\n"
        )
        .text("### 3. Borrower Identification and KYC Particulars\n")
        .text("The primary applicant is registered in lending records as ")
        .pii("PERSON", "Siddharth Roy")
        .text(", reachable via verified electronic email ")
        .pii("EMAIL_ADDRESS", "siddharth.roy@finmail.com")
        .text(" and registered mobile telephone number ")
        .pii("INDIAN_MOBILE", "+91 98200 11223")
        .text(". The borrower identity dossier confirms verified Aadhaar Card number ")
        .pii("AADHAAR", adh_fmt4)
        .text(" and Income Tax PAN number ")
        .pii("PAN", "AZYPR4567M")
        .text(". The loan disbursement will be credited to escrow via IFSC ")
        .pii("IFSC", "HDFC0000050")
        .text(" to account ")
        .pii("BANK_ACCOUNT", "50100458921345", in_scope=False)
        .text(". Current residential address is ")
        .pii(
            "STREET_ADDRESS",
            "House 45, Koramangala 4th Block, 80 Feet Road, Bengaluru, Karnataka 560034",
            in_scope=False,
        )
        .text(", date of birth authenticated as ")
        .pii("DATE_OF_BIRTH", "20-07-1984", in_scope=False)
        .text(". Borrower digital verification was processed with co-borrower UPI handle ")
        .pii("UPI", "siddharth.roy@okhdfcbank")
        .text(".\n\n")
        .text("### 4. Collateral, Security Creation, and Mortgage Registration\n")
        .text(
            "The loan is secured by equitable mortgage of the underlying property: Flat No 304, Green Heights, Sarjapur Main Road, Bengaluru. "
            "The Borrower deposits original title deeds, sanctioned building plans, and tax receipts with the Lender until complete discharge of debt. "
            "The Lender reserves the right to initiate attachment under SARFAESI Act 2002 upon event of 90-day non-cured repayment default.\n\n"
        )
        .text("### 5. Prepayment and Foreclosure Conditions\n")
        .text(
            "Under Reserve Bank of India regulatory directives, zero prepayment penalties shall apply to floating rate housing facilities extended to individual borrowers. "
            "Any lump-sum partial prepayment shall be directly adjusted against outstanding principal balance, thereby reducing loan tenure proportionately.\n"
        )
    )
    docs.append(("loan_agreement_01.txt", "loan_agreement", b4.build()))

    # Loan Agreement 2: Commercial Equipment
    b5 = DocBuilder(
        filename="loan_agreement_02.txt",
        doc_type="loan_agreement",
        key_facts={
            "loan_amount": "INR 1,25,00,000",
            "interest_rate": "11.25% per annum fixed",
            "tenure": "84 months",
            "prepayment_penalty": "2.0% of outstanding principal",
        },
    )
    raw_adh5 = _generate_valid_aadhaar(fake)
    adh_fmt5 = f"{raw_adh5[:4]}-{raw_adh5[4:8]}-{raw_adh5[8:]}"

    (
        b5.text("# COMMERCIAL EQUIPMENT ASSET FINANCE AND CREDIT FACILITY AGREEMENT\n")
        .text("## FACILITY SANCTION ORDER: ICICI-EQUIP-2026-DEL-104\n")
        .text("Dated: 24th January 2026 | New Delhi Commercial Branch\n\n")
        .text("### 1. Commercial Loan Facility Purpose\n")
        .text(
            "This Secured Asset Finance Agreement is established between Apex Commercial Credit Corporation (the Financier) "
            "and Precision CNC Heavy Industries Private Limited (the Enterprise Borrower). The facility is granted solely for the procurement "
            "and installation of high-precision German 5-axis computer numerical control (CNC) milling machinery for automotive part fabrication.\n\n"
        )
        .text("### 2. Sanctioned Amount, Tenure, and Interest Rate Terms\n")
        .text(
            "The Financier sanctions an asset loan amount of INR 1,25,00,000 (Rupees One Crore Twenty-Five Lakhs Only) repayable over a tenure of 84 months. "
            "The applicable interest rate is 11.25% per annum fixed, calculated on monthly reducing balance and not subject to market interest index fluctuation. "
            "In the event the borrower exercises voluntary loan prepayment or foreclosure prior to maturity, a prepayment penalty of 2.0% of outstanding principal "
            "shall be levied plus applicable statutory taxes.\n\n"
        )
        .text("### 3. Authorized Guarantor and KYC Verification\n")
        .text("The corporate facility is personally guaranteed by Managing Director ")
        .pii("PERSON", "Harishchand Chawla")
        .text(", reachable via email ")
        .pii("EMAIL_ADDRESS", "harish.chawla@precisioncnc.in")
        .text(" and direct telephone contact ")
        .pii("INDIAN_MOBILE", "+91 98111 22334")
        .text(". The guarantor submitted government Aadhaar ")
        .pii("AADHAAR", adh_fmt5)
        .text(" and Director PAN ")
        .pii("PAN", "AAACH7890N")
        .text(". Equipment disbursement is released via IFSC ")
        .pii("IFSC", "ICIC0000007")
        .text(" to current account ")
        .pii("BANK_ACCOUNT", "000705012398", in_scope=False)
        .text(". Official corporate domicile is ")
        .pii(
            "STREET_ADDRESS",
            "Plot 88, Okhla Industrial Area Phase 3, New Delhi 110020",
            in_scope=False,
        )
        .text(", with guarantor date of birth ")
        .pii("DATE_OF_BIRTH", "11-12-1971", in_scope=False)
        .text(". Transaction authorization desk links to corporate UPI ")
        .pii("UPI", "harish.chawla@icici")
        .text(" for verification.\n\n")
        .text("### 4. Hypothecation of Financed Machinery and Insurance Cover\n")
        .text(
            "The underlying CNC equipment shall remain exclusively hypothecated in favor of the Financier until issuance of No Objection Certificate (NOC). "
            "The Enterprise Borrower covenants to maintain comprehensive machinery breakdown and fire insurance policies at all times, with the Financier "
            "endorsed as sole loss payee.\n\n"
        )
        .text("### 5. Financial Covenants and Default Remedies\n")
        .text(
            "The Enterprise Borrower shall maintain a Debt Service Coverage Ratio (DSCR) of not less than 1.35 throughout the loan tenure. "
            "Default in interest payment exceeding 30 days shall attract default penal interest at 24% per annum compounded monthly.\n"
        )
    )
    docs.append(("loan_agreement_02.txt", "loan_agreement", b5.build()))

    # Loan Agreement 3: Personal Loan
    b6 = DocBuilder(
        filename="loan_agreement_03.txt",
        doc_type="loan_agreement",
        key_facts={
            "loan_amount": "INR 6,50,00,000" if False else "INR 6,50,000",
            "interest_rate": "13.50% per annum reducing balance",
            "tenure": "36 months",
            "foreclosure_charges": "Zero charges after 12 EMIs",
        },
    )
    raw_adh6 = _generate_valid_aadhaar(fake)
    adh_fmt6 = f"{raw_adh6[:4]} {raw_adh6[4:8]} {raw_adh6[8:]}"

    (
        b6.text("# PERSONAL UNSECURED CREDIT FACILITY SANCTION LETTER\n")
        .text("## SANCTION ID: AXIS-PL-2026-HYD-5502\n")
        .text("Issued at Hyderabad, Telangana on 5th February 2026\n\n")
        .text("### 1. Facility Preamble and Eligibility\n")
        .text(
            "Axis Retail Bank Limited extends this unsecured personal consumer credit facility to the salaried applicant named below. "
            "The loan proceeds may be deployed for lawful personal expenditure including medical expenses, domestic renovation, or education. "
            "The facility is sanctioned based on internal credit scoring, salary verification, employment stability at a Category-A employer, "
            "and positive debt-to-income evaluation conducted by the retail credit underwriting committee.\n\n"
        )
        .text("### 2. Sanctioned Sum, Tenure, and Rate of Interest\n")
        .text(
            "The Bank sanctions a personal loan amount of INR 6,50,000 (Rupees Six Lakhs Fifty Thousand Only) with a contractual tenure of 36 months. "
            "The facility carries an interest rate of 13.50% per annum reducing balance, with monthly repayment installments of INR 22,045. "
            "Under retail lending terms, the Bank stipulates foreclosure charges as follows: Zero charges after 12 EMIs are successfully serviced. "
            "If foreclosure occurs prior to the completion of twelve months, standard administrative foreclosure fees of 3% plus GST shall apply.\n\n"
        )
        .text("### 3. Customer Identity and Banking Particulars\n")
        .text("The facility is granted to ")
        .pii("PERSON", "Sneha Reddy")
        .text(", contactable via official email ")
        .pii("EMAIL_ADDRESS", "sneha.reddy@techcorp.in")
        .text(" and cellular number ")
        .pii("INDIAN_MOBILE", "+91 96500 44332")
        .text(". The customer identity verification validates Aadhaar number ")
        .pii("AADHAAR", adh_fmt6)
        .text(" and Income Tax PAN ")
        .pii("PAN", "AWTPR1290K")
        .text(". Credit transfer will be credited via IFSC code ")
        .pii("IFSC", "UTIB0000123")
        .text(" to savings account ")
        .pii("BANK_ACCOUNT", "914010034567891", in_scope=False)
        .text(". Residential communication address is ")
        .pii(
            "STREET_ADDRESS",
            "Flat 201 Sri Sai Residency, Madhapur, Hyderabad, Telangana 500081",
            in_scope=False,
        )
        .text(", with date of birth recorded as ")
        .pii("DATE_OF_BIRTH", "28-09-1994", in_scope=False)
        .text(". Retail mandate verified with applicant UPI ")
        .pii("UPI", "sneha.reddy@axisbank")
        .text(".\n\n")
        .text("### 4. Credit Bureau Reporting and Acceleration\n")
        .text(
            "Delays in servicing scheduled EMIs shall be transmitted to credit information companies including CIBIL, Experian, and Equifax. "
            "The Bank retains the right to accelerate the entire outstanding balance upon non-payment of two consecutive installments. "
            "The Borrower shall remain liable for all legal expenses, recovery costs, and collection charges incurred by the Bank.\n\n"
        )
        .text("### 5. Direct Debit Mandate and NACH Electronic Clearing\n")
        .text(
            "The Borrower executes an irrevocable Standing Instruction and National Automated Clearing House (NACH) debit mandate in favor of the Bank. "
            "The Borrower covenants to maintain sufficient funds in the designated savings account at least 24 hours prior to the monthly debit date. "
            "Cheque dishonour or NACH bounce shall attract statutory penal bounce charges of INR 500 per presentation.\n\n"
        )
        .text("### 6. Dispute Resolution and Governing Law\n")
        .text(
            "All disputes arising from or connected with this Agreement shall be subject to the exclusive jurisdiction of the competent civil "
            "courts situated in Hyderabad, Telangana.\n"
        )
    )
    docs.append(("loan_agreement_03.txt", "loan_agreement", b6.build()))

    # =========================================================================
    # 3. HOSPITAL DISCHARGE SUMMARIES (3 Documents)
    # =========================================================================

    # Hospital Discharge 1: Apollo Multi-Specialty
    b7 = DocBuilder(
        filename="hospital_discharge_01.txt",
        doc_type="hospital_discharge",
        key_facts={
            "primary_diagnosis": "Acute Laparoscopic Appendectomy",
            "discharge_status": "Hemodynamically stable and ambulatory",
            "follow_up_date": "7 days post-discharge",
            "discharge_medications": "Cefixime 200mg twice daily for 5 days",
        },
    )
    raw_adh7 = _generate_valid_aadhaar(fake)
    adh_fmt7 = f"{raw_adh7[:4]} {raw_adh7[4:8]} {raw_adh7[8:]}"

    (
        b7.text("# APOLLO MULTI-SPECIALTY HOSPITALS BENGALURU\n")
        .text("## INPATIENT CLINICAL DISCHARGE SUMMARY AND CARE PLAN\n")
        .text("IP Admission No: IP-2026-MED-77412 | UHID: UH-889021\n")
        .text("Department of General and Minimally Invasive Surgery\n\n")
        .text("### 1. Patient Profile and Clinical Admission Details\n")
        .text(
            "The patient was admitted through emergency services presenting with severe right lower quadrant abdominal pain, "
            "low-grade pyrexia, nausea, and localized rebound tenderness. Ultrasound of abdomen confirmed inflamed non-perforated acute appendicitis.\n\n"
        )
        .text("### 2. Diagnosis, Surgical Procedure, and Clinical Course\n")
        .text(
            "The finalized clinical primary diagnosis is confirmed as Acute Laparoscopic Appendectomy following three-port laparoscopic intervention. "
            "The surgical procedure was uneventful without intra-operative visceral injury or significant haemorrhage. "
            "Histopathology confirmed acute suppurative appendicitis. The clinical discharge status at time of exit is documented as: "
            "Hemodynamically stable and ambulatory, tolerating oral solid diet, with clean surgical surgical port incisions.\n\n"
        )
        .text("### 3. Patient Demographics and Hospital Identification Record\n")
        .text("Patient name is logged as ")
        .pii("PERSON", "Gaurav Sen")
        .text(", with primary communication email ")
        .pii("EMAIL_ADDRESS", "gaurav.sen@healthmail.com")
        .text(" and emergency contact number ")
        .pii("INDIAN_MOBILE", "+91 98860 12345")
        .text(". The hospital billing desk verified Aadhaar Card ")
        .pii("AADHAAR", adh_fmt7)
        .text(" and PAN card ")
        .pii("PAN", "AZOPS3456D")
        .text(" for insurance claim processing under TPA. Refundable admission deposit returned via IFSC ")
        .pii("IFSC", "HDFC0000088")
        .text(" to account ")
        .pii("BANK_ACCOUNT", "50100984512390", in_scope=False)
        .text(". Patient home domicile is ")
        .pii(
            "STREET_ADDRESS",
            "Flat 102 Crystal Arcade, Indiranagar 100 Feet Road, Bengaluru, Karnataka 560038",
            in_scope=False,
        )
        .text(", date of birth ")
        .pii("DATE_OF_BIRTH", "19-03-1990", in_scope=False)
        .text(". Attending physician is Dr. ")
        .pii("PERSON", "Meenakshi Iyer")
        .text(". Patient hospital pharmacy account links to UPI ")
        .pii("UPI", "gaurav.sen@okhdfcbank")
        .text(".\n\n")
        .text("### 4. Post-Discharge Medications and Home Care Regimen\n")
        .text(
            "The patient is discharged on the following prescribed discharge medications: Cefixime 200mg twice daily for 5 days, "
            "alongside Paracetamol 650mg SOS for pain and Pantoprazole 40mg before breakfast. "
            "The patient must keep surgical wound dressings dry and clean until stitch review.\n\n"
        )
        .text("### 5. Follow-Up Consultation and Emergency Warning Signs\n")
        .text(
            "A formal follow-up outpatient consultation is scheduled exactly 7 days post-discharge in the surgical OPD for wound inspection. "
            "The patient must report immediately to emergency triage in case of high fever, persistent vomiting, or increasing abdominal distension.\n"
        )
    )
    docs.append(("hospital_discharge_01.txt", "hospital_discharge", b7.build()))

    # Hospital Discharge 2: Fortis Cardiac Care
    b8 = DocBuilder(
        filename="hospital_discharge_02.txt",
        doc_type="hospital_discharge",
        key_facts={
            "primary_diagnosis": "Coronary Angioplasty with Single Drug-Eluting Stent",
            "discharge_status": "Stable cardiac sinus rhythm",
            "follow_up_date": "14 days post-discharge",
            "ejection_fraction": "55% preserved LV systolic function",
        },
    )
    raw_adh8 = _generate_valid_aadhaar(fake)
    adh_fmt8 = f"{raw_adh8[:4]}-{raw_adh8[4:8]}-{raw_adh8[8:]}"

    (
        b8.text("# FORTIS HEALTHCARE CARDIOLOGY CENTER OF EXCELLENCE\n")
        .text("## CARDIOTHORACIC CLINICAL DISCHARGE SUMMARY\n")
        .text("Case Dossier: FH-CARD-2026-MUM-901 | Ward: Coronary ICU Bed 14\n")
        .text("Date of Discharge: 12th February 2026\n\n")
        .text("### 1. Clinical Presentation and Admission Findings\n")
        .text(
            "A 56-year-old executive presented with retrosternal chest tightness radiating to the left arm during exertion. "
            "Electrocardiogram showed ST-segment elevation in anterolateral leads, and cardiac troponin-I was elevated at 4.2 ng/mL.\n\n"
        )
        .text("### 2. Interventional Procedure and Cardiothoracic Evaluation\n")
        .text(
            "Coronary angiography revealed critical 90% stenosis in proximal Left Anterior Descending (LAD) artery. "
            "The primary diagnosis and intervention executed is Coronary Angioplasty with Single Drug-Eluting Stent (3.0 x 24mm DES). "
            "Echocardiogram established an ejection fraction of 55% preserved LV systolic function with no regional wall motion abnormalities. "
            "The discharge status of the patient is confirmed as: Stable cardiac sinus rhythm without active angina.\n\n"
        )
        .text("### 3. Patient Identity and Medical Record Archive\n")
        .text("Patient identity is recorded as ")
        .pii("PERSON", "Dinesh Kulkarni")
        .text(", contact email ")
        .pii("EMAIL_ADDRESS", "dinesh.kulkarni@healthmail.com")
        .text(" and mobile phone ")
        .pii("INDIAN_MOBILE", "+91 98205 67890")
        .text(". National health identifier confirms verified Aadhaar ")
        .pii("AADHAAR", adh_fmt8)
        .text(" and PAN ")
        .pii("PAN", "BCDPK8899P")
        .text(". Cashless insurance settlement processed via IFSC ")
        .pii("IFSC", "SBIN0001234")
        .text(" from account ")
        .pii("BANK_ACCOUNT", "30981245091", in_scope=False)
        .text(". Registered residence address is ")
        .pii(
            "STREET_ADDRESS",
            "B-203 Sunrise Towers, Chembur East, Mumbai, Maharashtra 400071",
            in_scope=False,
        )
        .text(", birth date ")
        .pii("DATE_OF_BIRTH", "04-10-1969", in_scope=False)
        .text(". Chief Interventional Cardiologist is Dr. ")
        .pii("PERSON", "Pooja Banerjee")
        .text(". Pharmacy UPI handle logged as ")
        .pii("UPI", "dinesh.k@oksbi")
        .text(".\n\n")
        .text("### 4. Pharmacotherapy and Lifestyle Recommendations\n")
        .text(
            "Dual antiplatelet therapy is mandatory: Aspirin 75mg daily indefinitely plus Ticagrelor 90mg twice daily for 12 months. "
            "Atorvastatin 80mg at bedtime and Metoprolol Succinate 25mg daily. Low salt, low cholesterol diet advised.\n\n"
        )
        .text("### 5. Follow-Up Schedule\n")
        .text(
            "The patient must report for clinical evaluation exactly 14 days post-discharge in the cardiology outpatient suite. "
            "Immediate readmission required if dyspnea or recurring chest pressure arises.\n\n"
        )
        .text("### 6. Emergency Warning Protocol and Triage\n")
        .text(
            "The patient and primary caregivers have been briefed on emergency warning signs including acute shortness of breath, "
            "profuse diaphoresis, syncope, or irregular heart palpitations. In the event of acute symptoms, the patient must "
            "consume Sorbitrate 5mg sublingually and immediately contact the hospital emergency cardiac triage desk. "
            "Strenuous physical exertion, heavy weight lifting, and commercial vehicular driving are strictly prohibited for 4 weeks.\n"
        )
    )
    docs.append(("hospital_discharge_02.txt", "hospital_discharge", b8.build()))

    # Hospital Discharge 3: Manipal Orthopaedics
    b9 = DocBuilder(
        filename="hospital_discharge_03.txt",
        doc_type="hospital_discharge",
        key_facts={
            "primary_diagnosis": "Left Knee Arthroscopic Meniscal Repair",
            "discharge_status": "Pain managed, non-weight bearing on left leg",
            "follow_up_date": "10 days post-discharge",
            "physiotherapy_protocol": "Gentle passive range of motion exercise starting Day 3",
        },
    )
    raw_adh9 = _generate_valid_aadhaar(fake)
    adh_fmt9 = f"{raw_adh9[:4]} {raw_adh9[4:8]} {raw_adh9[8:]}"

    (
        b9.text("# MANIPAL INSTITUTE OF ORTHOPAEDIC EXCELLENCE\n")
        .text("## CLINICAL SURGICAL DISCHARGE AND REHABILITATION SUMMARY\n")
        .text("Discharge Dossier: MAN-ORTHO-2026-DEL-331 | Room: Deluxe Room 408\n")
        .text("Department of Sports Medicine and Joint Preservation\n\n")
        .text("### 1. Admission Clinical Summary\n")
        .text(
            "The patient sustained sports-related mechanical torsion injury of the left knee resulting in severe swelling and joint locking. "
            "Magnetic resonance imaging confirmed complex posterior horn tear of the medial meniscus with mild joint effusion.\n\n"
        )
        .text("### 2. Surgical Findings and Discharge Status\n")
        .text(
            "Under spinal anesthesia, the patient underwent successful Left Knee Arthroscopic Meniscal Repair utilizing two all-inside suture anchors. "
            "The articular cartilage was intact. The clinical discharge status is documented as: Pain managed, non-weight bearing on left leg "
            "with hinged knee brace locked at 0 degrees extension. The physiotherapy protocol requires: Gentle passive range of motion exercise starting Day 3.\n\n"
        )
        .text("### 3. Patient Identity and Hospital Registry Records\n")
        .text("Patient identity corresponds to ")
        .pii("PERSON", "Kunal Singhania")
        .text(", contact email ")
        .pii("EMAIL_ADDRESS", "kunal.singhania@sportsmail.com")
        .text(" and phone ")
        .pii("INDIAN_MOBILE", "+91 97170 88990")
        .text(". Identification record contains Aadhaar number ")
        .pii("AADHAAR", adh_fmt9)
        .text(" and PAN record ")
        .pii("PAN", "AMNPS6789L")
        .text(". Mediclaim TPA clearance confirmed via IFSC ")
        .pii("IFSC", "PUNB0012300")
        .text(" to account ")
        .pii("BANK_ACCOUNT", "12300015009823", in_scope=False)
        .text(". Registered home address is ")
        .pii(
            "STREET_ADDRESS",
            "C-44 Greater Kailash 1, New Delhi 110048",
            in_scope=False,
        )
        .text(", date of birth ")
        .pii("DATE_OF_BIRTH", "15-06-1996", in_scope=False)
        .text(". Consultant Orthopaedic Surgeon is Dr. ")
        .pii("PERSON", "Deepak Verma")
        .text(". Pharmacy UPI handle is ")
        .pii("UPI", "kunal.s@okaxis")
        .text(".\n\n")
        .text("### 4. Post-Operative Medications and Care Instructions\n")
        .text(
            "Etoricoxib 90mg once daily after food for 5 days. Cryotherapy with ice packs applied for 20 minutes every 4 hours. "
            "Axillary crutches must be utilized for all ambulation.\n\n"
        )
        .text("### 5. Follow-Up Schedule\n")
        .text(
            "The patient shall return for suture removal exactly 10 days post-discharge in the sports medicine clinic. "
            "Urgent consult required if swelling in calf or fever occurs.\n\n"
        )
        .text("### 6. Deep Vein Thrombosis Prophylaxis and Rehabilitation Milestones\n")
        .text(
            "To prevent venous thromboembolism during the immobilized non-weight bearing interval, the patient is prescribed "
            "calves compression stockings and active ankle pump exercises performed 15 times every waking hour. "
            "Quadriceps isometric setting exercises shall commence under outpatient physiotherapy supervision after 10 days. "
            "Full active knee flexion beyond 90 degrees remains restricted until 6 weeks post-surgery.\n"
        )
    )
    docs.append(("hospital_discharge_03.txt", "hospital_discharge", b9.build()))

    # =========================================================================
    # 4. INSURANCE CLAIMS (3 Documents)
    # =========================================================================

    # Insurance Claim 1: Motor Comprehensive
    b10 = DocBuilder(
        filename="insurance_claim_01.txt",
        doc_type="insurance_claim",
        key_facts={
            "claim_number": "CLM-MOT-2026-88912",
            "claimed_amount": "INR 78,500",
            "approved_amount": "INR 68,200",
            "deductible": "INR 2,000 mandatory excess",
        },
    )
    raw_adh10 = _generate_valid_aadhaar(fake)
    adh_fmt10 = f"{raw_adh10[:4]} {raw_adh10[4:8]} {raw_adh10[8:]}"

    (
        b10.text("# HDFC ERGO GENERAL INSURANCE COMPANY LIMITED\n")
        .text("## MOTOR VEHICLE COMPREHENSIVE INSURANCE CLAIM SETTLEMENT REPORT\n")
        .text("Policy Certificate No: MOT-POL-2025-99812 | IRDAI Reg No: 146\n")
        .text("Settlement Docket: HDFC-MOT-2026-BLR-09\n\n")
        .text("### 1. Incident Particulars and Vehicle Description\n")
        .text(
            "The insured vehicle, a 2024 Honda City ZX bearing registration KA-01-MJ-4521, sustained front bumper and radiator damage "
            "following collision with a stationary road median. The claim number assigned to this case is CLM-MOT-2026-88912. "
            "Independent motor surveyor inspection confirmed accidental collision damage consistent with insured driver statement.\n\n"
        )
        .text("### 2. Loss Assessment and Settlement Sanction\n")
        .text(
            "The authorized repair garage submitted an initial claimed amount of INR 78,500 for replacement of bumper assembly and headlight clusters. "
            "Following depreciation adjustment on plastic components and applying a deductible of INR 2,000 mandatory excess under Section 1, "
            "the claims committee sanctions a net approved amount of INR 68,200 payable directly to the cashless workshop network.\n\n"
        )
        .text("### 3. Policyholder Identification and Claim Docket\n")
        .text("The policyholder is registered as ")
        .pii("PERSON", "Abhishek Saxena")
        .text(", contactable at email ")
        .pii("EMAIL_ADDRESS", "abhishek.saxena@claimmail.in")
        .text(" and telephone ")
        .pii("INDIAN_MOBILE", "+91 99001 22334")
        .text(". KYC document dossier confirms verified Aadhaar ")
        .pii("AADHAAR", adh_fmt10)
        .text(" and PAN card ")
        .pii("PAN", "AGYPS9912Q")
        .text(". Direct electronic reimbursement credited via IFSC ")
        .pii("IFSC", "HDFC0000120")
        .text(" to savings account ")
        .pii("BANK_ACCOUNT", "50100778899123", in_scope=False)
        .text(". Policyholder residence address is ")
        .pii(
            "STREET_ADDRESS",
            "House 78, 5th Cross, Malleshwaram, Bengaluru, Karnataka 560003",
            in_scope=False,
        )
        .text(", date of birth ")
        .pii("DATE_OF_BIRTH", "18-01-1987", in_scope=False)
        .text(". Surveyor in charge is ")
        .pii("PERSON", "Naveen Chawla")
        .text(". Claims excess payment settled via UPI ")
        .pii("UPI", "abhishek.saxena@okhdfcbank")
        .text(".\n\n")
        .text("### 4. Salvage and Subrogation Covenants\n")
        .text(
            "Damaged metal and fiber parts valued at INR 2,500 are retained by the workshop as salvage deduction. "
            "The insured executes standard discharge and subrogation vouchers releasing the insurer from further liabilities regarding this event.\n\n"
        )
        .text("### 5. Final Indemnity Settlement and Policy Endorsement\n")
        .text(
            "With the disbursement of the sanctioned amount, the accidental damage claim file stands fully settled and archived. "
            "The insured acknowledges that the No Claim Bonus (NCB) entitlement on policy renewal shall adjust to 0% for the upcoming policy period. "
            "The vehicle repair quality warranty covers replaced paint and body panels for six calendar months against peeling or blistering.\n"
        )
    )
    docs.append(("insurance_claim_01.txt", "insurance_claim", b10.build()))

    # Insurance Claim 2: Health Cashless
    b11 = DocBuilder(
        filename="insurance_claim_02.txt",
        doc_type="insurance_claim",
        key_facts={
            "claim_number": "CLM-MED-2026-44109",
            "claimed_amount": "INR 1,85,000",
            "approved_amount": "INR 1,72,500",
            "pre_authorization_status": "Pre-authorized within 4 hours",
        },
    )
    raw_adh11 = _generate_valid_aadhaar(fake)
    adh_fmt11 = f"{raw_adh11[:4]}-{raw_adh11[4:8]}-{raw_adh11[8:]}"

    (
        b11.text("# STAR HEALTH AND ALLIED INSURANCE COMPANY\n")
        .text("## CASHLESS HOSPITALIZATION CLAIM ADJUDICATION MEMORANDUM\n")
        .text("Policy Reference: STAR-COMP-2025-1102 | TPA Code: TPA-MED-04\n")
        .text("Claims Department | Chennai Head Office\n\n")
        .text("### 1. Hospitalization Claim Profile\n")
        .text(
            "The insured member was admitted to Apollo Hospitals Chennai for acute viral pneumonia and severe respiratory compromise. "
            "Under cashless hospitalization guidelines, the claim number assigned is CLM-MED-2026-44109. "
            "The network provider submitted emergency admission request, with pre-authorization status confirmed: Pre-authorized within 4 hours.\n\n"
        )
        .text("### 2. Medical Expense Assessment and Adjudication\n")
        .text(
            "The hospital presented cumulative billing for room rent, ICU monitoring, and pharmacological therapy totaling a claimed amount of INR 1,85,000. "
            "Following review of policy room rent caps and non-medical exclusions, the claim officer authorises a final approved amount of INR 1,72,500. "
            "The residual balance of INR 12,500 representing personal toiletries and administrative charges was discharged by the insured directly.\n\n"
        )
        .text("### 3. Insured Member Identification and Claims Data\n")
        .text("The primary insured is identified as ")
        .pii("PERSON", "Radha Subramanian")
        .text(", reachable via email ")
        .pii("EMAIL_ADDRESS", "radha.subramanian@insurecare.com")
        .text(" and mobile ")
        .pii("INDIAN_MOBILE", "+91 94440 33445")
        .text(". Claim record verifies national Aadhaar ")
        .pii("AADHAAR", adh_fmt11)
        .text(" and PAN identifier ")
        .pii("PAN", "AZKPS1144F")
        .text(". Post-hospitalization claim allowance transfer routed via IFSC ")
        .pii("IFSC", "IOBA0001004")
        .text(" to account ")
        .pii("BANK_ACCOUNT", "10040156908123", in_scope=False)
        .text(". Residence address recorded as ")
        .pii(
            "STREET_ADDRESS",
            "Door No 14, 2nd Main Road, Gandhi Nagar, Adyar, Chennai, Tamil Nadu 600020",
            in_scope=False,
        )
        .text(", date of birth ")
        .pii("DATE_OF_BIRTH", "09-12-1981", in_scope=False)
        .text(". Medical claim investigator is Dr. ")
        .pii("PERSON", "Suresh Menon")
        .text(". Direct co-pay settlement was confirmed with member UPI ")
        .pii("UPI", "radha.s@okaxis")
        .text(".\n\n")
        .text("### 4. Non-Medical Exclusions and Discharge Audit\n")
        .text(
            "The insurer verifies that hospital admission exceeded the 24-hour statutory minimum. "
            "All investigative pathology reports and oxygen saturation charts were reviewed and found fully compliant with policy underwriting norms.\n\n"
        )
        .text("### 5. Third-Party Administrator Audit and Final Discharge\n")
        .text(
            "The Third Party Administrator (TPA) has verified hospital pharmacy vouchers, clinical discharge records, and doctor round logs. "
            "The insured has submitted complete pre-hospitalization and post-hospitalization bills within sixty calendar days. "
            "Direct electronic settlement has been issued to Apollo Hospitals healthcare provider billing account under NEFT payment reference.\n"
        )
    )
    docs.append(("insurance_claim_02.txt", "insurance_claim", b11.build()))

    # Insurance Claim 3: Commercial Property Fire
    b12 = DocBuilder(
        filename="insurance_claim_03.txt",
        doc_type="insurance_claim",
        key_facts={
            "claim_number": "CLM-FIRE-2026-11045",
            "claimed_amount": "INR 14,20,000",
            "approved_amount": "INR 12,80,000",
            "surveyor_assessment": "Electrical short-circuit without gross negligence",
        },
    )
    raw_adh12 = _generate_valid_aadhaar(fake)
    adh_fmt12 = f"{raw_adh12[:4]} {raw_adh12[4:8]} {raw_adh12[8:]}"

    (
        b12.text("# ICICI LOMBARD GENERAL INSURANCE COMPANY\n")
        .text("## COMMERCIAL PROPERTY AND ASSET LOSS CLAIM MEMORANDUM\n")
        .text("Policy Docket: COMM-FIRE-2025-4421 | Docket Ref: LOMB-CLM-2026-KOL-03\n")
        .text("Eastern Regional Office | Kolkata, West Bengal\n\n")
        .text("### 1. Risk Location and Event Description\n")
        .text(
            "A fire broke out in the packaging storage wing of Eastern Garment Export Enterprises, Sector 5, Salt Lake, Kolkata. "
            "The official claim number generated in the insurer ERP is CLM-FIRE-2026-11045. "
            "The licensed surveyor assessment concluded: Electrical short-circuit without gross negligence in the secondary distribution box.\n\n"
        )
        .text("### 2. Loss Verification and Approved Quantum\n")
        .text(
            "The insured entity submitted itemized replacement estimates for damaged cardboard cartons, corrugated boxes, and packing machinery "
            "reflecting a claimed amount of INR 14,20,000. Following inspection of stock purchase registers and application of under-insurance factors, "
            "the surveyor recommended an approved amount of INR 12,80,000 in full and final settlement of all material damage claims.\n\n"
        )
        .text("### 3. Commercial Entity Representative and Identity Documentation\n")
        .text("Managing partner representing the insured is ")
        .pii("PERSON", "Tapan Ganguly")
        .text(", contact email ")
        .pii("EMAIL_ADDRESS", "tapan.ganguly@easterngarments.co.in")
        .text(" and official telephone ")
        .pii("INDIAN_MOBILE", "+91 98300 44556")
        .text(". Identification credentials include partner Aadhaar number ")
        .pii("AADHAAR", adh_fmt12)
        .text(" and commercial PAN ")
        .pii("PAN", "AAEFG4567M")
        .text(". Claim remittance ordered through IFSC ")
        .pii("IFSC", "UTBI0001045")
        .text(" into current account ")
        .pii("BANK_ACCOUNT", "10450500129845", in_scope=False)
        .text(". Factory facility premises situated at ")
        .pii(
            "STREET_ADDRESS",
            "Plot 18, Block EP & GP, Sector V, Salt Lake, Kolkata, West Bengal 700091",
            in_scope=False,
        )
        .text(", partner date of birth ")
        .pii("DATE_OF_BIRTH", "25-04-1965", in_scope=False)
        .text(". Loss Adjuster handling survey is ")
        .pii("PERSON", "Amitava Roy")
        .text(". Fee remittance desk links to UPI ")
        .pii("UPI", "tapan.ganguly@okhdfcbank")
        .text(".\n\n")
        .text("### 4. Environmental and Municipal Approvals\n")
        .text(
            "The Kolkata Municipal Corporation Fire Services issued Fire Incident Certificate confirming deployment of 3 tender vehicles. "
            "No structural integrity damage was reported to the primary RCC building columns.\n\n"
        )
        .text("### 5. Risk Mitigation and Fire Safety Compliance Recommendations\n")
        .text(
            "The chartered loss adjuster recommends mandatory installation of automated smoke aspiration detectors in all storage warehouses. "
            "Electrical wiring in distribution bays must be enclosed within fire-retardant conduits and undergo annual thermal imaging audits. "
            "The insured partner undertakes to maintain fully charged CO2 and ABC dry chemical fire extinguishers at 15-meter intervals.\n"
        )
    )
    docs.append(("insurance_claim_03.txt", "insurance_claim", b12.build()))

    # =========================================================================
    # 5. KYC ONBOARDING FORMS (3 Documents)
    # =========================================================================

    # KYC Form 1: Zerodha Demat KYC
    b13 = DocBuilder(
        filename="kyc_form_01.txt",
        doc_type="kyc_form",
        key_facts={
            "account_type": "Individual Resident Demat and Trading Account",
            "risk_category": "Moderate Risk Profile",
            "verification_mode": "DigiLocker Video In-Person Verification (IPV)",
            "tax_residency": "Resident of India exclusively",
        },
    )
    raw_adh13 = _generate_valid_aadhaar(fake)
    adh_fmt13 = f"{raw_adh13[:4]} {raw_adh13[4:8]} {raw_adh13[8:]}"

    (
        b13.text("# ZERODHA BROKING LIMITED\n")
        .text("## CENTRAL KYC REGISTRY (CKYC) ONBOARDING DOSSIER\n")
        .text("Application Ref: ZER-CKYC-2026-BLR-10294 | CDSL DP ID: 12081600\n")
        .text("SEBI Registration No: INZ000031633 | Bengaluru, Karnataka\n\n")
        .text("### 1. Account Selection and Investor Profile\n")
        .text(
            "This Central KYC application form is executed for opening an account type: Individual Resident Demat and Trading Account. "
            "The suitability questionnaire categorizes the investor under risk category: Moderate Risk Profile, eligible for cash equity "
            "and exchange-traded index derivatives transactions.\n\n"
        )
        .text("### 2. Verification Mode and Tax Residency Declaration\n")
        .text(
            "Customer identity and biometric verification was executed through verification mode: DigiLocker Video In-Person Verification (IPV). "
            "Under Foreign Account Tax Compliance Act (FATCA) and Common Reporting Standard (CRS) mandates, the applicant declares "
            "tax residency: Resident of India exclusively, with zero tax liability or offshore account citizenship in foreign territories.\n\n"
        )
        .text("### 3. Client Identity and Statutory Documents\n")
        .text("The investor applicant is ")
        .pii("PERSON", "Pranav Kulkarni")
        .text(", contact email ")
        .pii("EMAIL_ADDRESS", "pranav.kulkarni@investmail.in")
        .text(" and mobile phone ")
        .pii("INDIAN_MOBILE", "+91 98450 77889")
        .text(". Central identity database confirms verified UIDAI Aadhaar ")
        .pii("AADHAAR", adh_fmt13)
        .text(" and Income Tax PAN card ")
        .pii("PAN", "AZTPK4512B")
        .text(". Primary trading bank linkage validated via IFSC ")
        .pii("IFSC", "HDFC0000060")
        .text(" with account ")
        .pii("BANK_ACCOUNT", "50100445566778", in_scope=False)
        .text(". Communication address logged as ")
        .pii(
            "STREET_ADDRESS",
            "Flat 301 Shanti Nivas, 14th Main, JP Nagar 2nd Phase, Bengaluru, Karnataka 560078",
            in_scope=False,
        )
        .text(", applicant birth date ")
        .pii("DATE_OF_BIRTH", "12-07-1993", in_scope=False)
        .text(". Authorized verification compliance officer is ")
        .pii("PERSON", "Rameshwar Rao")
        .text(". Instant fund transfer UPI handle authenticated as ")
        .pii("UPI", "pranav.k@okhdfcbank")
        .text(".\n\n")
        .text("### 4. Nomination and Statutory Disclosures\n")
        .text(
            "The investor nominates their legal spouse with 100% entitlement share. "
            "The investor declares understanding of capital market volatility and confirms the funds invested originate from legitimate lawful income.\n\n"
        )
        .text("### 5. Depository Participant Agreement and Clearing Mandate\n")
        .text(
            "The investor authorizes Zerodha Broking Limited as Depository Participant to maintain dematerialized securities with CDSL. "
            "All dividend payments and corporate action entitlements shall be credited directly into the verified linked primary bank account. "
            "The applicant agrees to receive electronic contract notes (ECN) via email within twenty-four hours of trade execution.\n"
        )
    )
    docs.append(("kyc_form_01.txt", "kyc_form", b13.build()))

    # KYC Form 2: SBI Corporate NRI KYC
    b14 = DocBuilder(
        filename="kyc_form_02.txt",
        doc_type="kyc_form",
        key_facts={
            "account_type": "Non-Resident External (NRE) Savings Account",
            "risk_category": "High Risk Tier-1 Enhanced Due Diligence",
            "overseas_residency": "United Arab Emirates",
            "annual_turnover_declaration": "Above INR 50,00,000",
        },
    )
    raw_adh14 = _generate_valid_aadhaar(fake)
    adh_fmt14 = f"{raw_adh14[:4]}-{raw_adh14[4:8]}-{raw_adh14[8:]}"

    (
        b14.text("# STATE BANK OF INDIA\n")
        .text("## NON-RESIDENT INDIAN (NRI) CUSTOMER ONBOARDING FORM\n")
        .text("Form Docket: SBI-NRE-2026-COI-007 | Overseas Banking Unit Kochi\n")
        .text("Reserve Bank of India Foreign Exchange Management Act (FEMA) Guidelines\n\n")
        .text("### 1. Account Classification and Risk Categorization\n")
        .text(
            "The applicant submits documentation to open an account type: Non-Resident External (NRE) Savings Account. "
            "Due to cross-border capital repatriation permissions, the compliance committee assigns risk category: High Risk Tier-1 Enhanced Due Diligence, "
            "requiring annual re-KYC and source of wealth validation.\n\n"
        )
        .text("### 2. Country of Residence and Turnover Declarations\n")
        .text(
            "The customer maintains official overseas residency: United Arab Emirates, holding a valid Dubai residency employment visa. "
            "Under anti-money laundering regulations, the applicant signs annual turnover declaration: Above INR 50,00,000, "
            "attesting that capital remittances originate from executive corporate employment abroad.\n\n"
        )
        .text("### 3. Applicant Particulars and KYC Identification\n")
        .text("Primary NRI account holder is ")
        .pii("PERSON", "Faisal Mohammed")
        .text(", contactable via official email ")
        .pii("EMAIL_ADDRESS", "faisal.mohammed@nrimail.ae")
        .text(" and registered overseas mobile ")
        .pii("INDIAN_MOBILE", "+91 98470 11223")
        .text(". Government identity records include verified Aadhaar ")
        .pii("AADHAAR", adh_fmt14)
        .text(" and PAN card ")
        .pii("PAN", "AZOPM8811K")
        .text(". Repatriable credit branch IFSC is ")
        .pii("IFSC", "SBIN0000856")
        .text(" with designated account ")
        .pii("BANK_ACCOUNT", "30089124501", in_scope=False)
        .text(". Local Kerala family domicile is recorded as ")
        .pii(
            "STREET_ADDRESS",
            "Bait-ul-Salam, Marine Drive, Ernakulam, Kochi, Kerala 682031",
            in_scope=False,
        )
        .text(", born on ")
        .pii("DATE_OF_BIRTH", "22-03-1979", in_scope=False)
        .text(". Branch NRI Manager is ")
        .pii("PERSON", "Jacob Varghese")
        .text(". Remittance UPI linkage authenticated as ")
        .pii("UPI", "faisal.m@oksbi")
        .text(".\n\n")
        .text("### 4. FATCA / CRS Certification\n")
        .text(
            "The applicant certifies not being a US citizen or Green Card holder. "
            "Tax identification number for UAE tax residency is registered under Dubai Department of Economic Development records.\n\n"
        )
        .text("### 5. Foreign Inward Remittance Certificate (FIRC) and Repatriation Rights\n")
        .text(
            "Under Foreign Exchange Management Act (FEMA) directives, the funds held in this NRE savings account are freely repatriable "
            "outside India without statutory ceiling or prior central bank clearance. Interest earned on NRE balances is fully exempt "
            "from Indian income taxation under Section 10(4) of the Income Tax Act 1961. The account holder covenants to notify the bank "
            "in writing immediately upon any future change in non-resident taxation status or permanent relocation back to India for resettlement.\n"
        )
    )
    docs.append(("kyc_form_02.txt", "kyc_form", b14.build()))

    # KYC Form 3: Groww Mutual Fund Onboarding
    b15 = DocBuilder(
        filename="kyc_form_03.txt",
        doc_type="kyc_form",
        key_facts={
            "account_type": "Mutual Fund Investment Folio Individual Account",
            "risk_category": "Low to Moderate Risk Profile",
            "fatca_status": "Not a US citizen or tax resident of any other jurisdiction",
            "nomination_status": "Single nominee registered with 100% share",
        },
    )
    raw_adh15 = _generate_valid_aadhaar(fake)
    adh_fmt15 = f"{raw_adh15[:4]} {raw_adh15[4:8]} {raw_adh15[8:]}"

    (
        b15.text("# GROWW INVEST TECH PRIVATE LIMITED\n")
        .text("## MUTUAL FUND FOLIO ONBOARDING AND CKYC COMPLIANCE DOCUMENT\n")
        .text("Folio Application ID: GRW-MF-2026-PUN-8821 | AMFI Registration No: ARN-111686\n")
        .text("Registered Office: Outer Ring Road, Bengaluru, Karnataka\n\n")
        .text("### 1. Investor Classification and Folio Type\n")
        .text(
            "This electronic onboarding record establishes an account type: Mutual Fund Investment Folio Individual Account. "
            "Risk profiling assessment classifies the applicant as risk category: Low to Moderate Risk Profile, suitable for large-cap equity "
            "and sovereign debt mutual fund schemes.\n\n"
        )
        .text("### 2. FATCA and Nomination Status\n")
        .text(
            "Under Indian income tax statutory rules, the customer certifies fatca status: Not a US citizen or tax resident of any other jurisdiction. "
            "The mutual fund folio registers nomination status: Single nominee registered with 100% share, naming the applicant's sibling.\n\n"
        )
        .text("### 3. Investor Personal and Financial Verification\n")
        .text("The investor is identified as ")
        .pii("PERSON", "Pooja Kulkarni")
        .text(", contact email ")
        .pii("EMAIL_ADDRESS", "pooja.kulkarni@fininvest.in")
        .text(" and mobile ")
        .pii("INDIAN_MOBILE", "+91 98220 55667")
        .text(". Central identity database confirms verified Aadhaar ")
        .pii("AADHAAR", adh_fmt15)
        .text(" and PAN card ")
        .pii("PAN", "BCDPK7788A")
        .text(". Systematic Investment Plan (SIP) mandate bank IFSC is ")
        .pii("IFSC", "ICIC0000039")
        .text(" with account ")
        .pii("BANK_ACCOUNT", "003901589124", in_scope=False)
        .text(". Permanent residential address is ")
        .pii(
            "STREET_ADDRESS",
            "Flat 404 Green Acres, Baner Road, Pune, Maharashtra 411045",
            in_scope=False,
        )
        .text(", birth date ")
        .pii("DATE_OF_BIRTH", "08-11-1995", in_scope=False)
        .text(". Customer onboarding officer is ")
        .pii("PERSON", "Tanmay Joshi")
        .text(". SIP autopay UPI ID authenticated as ")
        .pii("UPI", "pooja.k@okicici")
        .text(".\n\n")
        .text("### 4. Terms and Risk Acknowledgment\n")
        .text(
            "Mutual fund investments are subject to market risks. The investor acknowledges having read all Scheme Information Documents (SID) "
            "and Statement of Additional Information (SAI) before authorizing systematic recurring auto-debit transfers.\n\n"
        )
        .text("### 5. Automated Clearing Mandate and Grievance Mechanism\n")
        .text(
            "The investor registers e-NACH autopay debit instructions for scheduled monthly SIP installments debited on the 10th of every month. "
            "For customer grievances, investor relations contact is accessible via compliance ticket portal under SEBI SCORES integration. "
            "The folio records confirm complete verification of bank passbook copy and canceled cheque leaves. Electronic investor records "
            "are mirrored in CKYCR central depository for regulatory auditing and instant retrieval.\n"
        )
    )
    docs.append(("kyc_form_03.txt", "kyc_form", b15.build()))

    return docs


def main() -> None:
    """Generate all documents, save them to data/docs/, and write _ground_truth.json."""
    logging.basicConfig(level=logging.INFO)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    generated = generate_all_documents()
    ground_truth_records: list[dict[str, Any]] = []

    for filename, _doc_type, (full_text, metadata) in generated:
        out_path = DOCS_DIR / filename
        out_path.write_text(full_text, encoding="utf-8")
        ground_truth_records.append(metadata)
        logger.info(
            "Saved %s: %d words, %d PII entities",
            filename,
            metadata["word_count"],
            len(metadata["pii_entities"]),
        )

    ground_truth_data = {"documents": ground_truth_records}
    GROUND_TRUTH_FILE.write_text(json.dumps(ground_truth_data, indent=2), encoding="utf-8")
    logger.info("Wrote ground truth catalog to %s", GROUND_TRUTH_FILE)


if __name__ == "__main__":
    main()

