# VeilRAG Secure Ingestion & Local Retrieval Audit Report

> [!IMPORTANT] Ingestion Invariant Verification
> **Strict Zero-Leak Boundary**: All pattern-based and structured in-scope PII types (Aadhaar, PAN, Email, Mobile, IFSC, UPI, Bank Account, Street Address, DOB) have **0 leaks** across stored chunk text, metadata, and raw disk files.

## 1. Executive Summary & Core Security Metrics

| Evaluation Metric | Measured Result | Security Target | Status |
| :--- | :--- | :--- | :--- |
| **Pattern/Structured PII Leaks (Aadhaar, PAN, Email, Mobile, IFSC, UPI, Account, Address, DOB)** | **0** | 0 leaks | **PASS (Zero Leaks)** |
| **Metadata Raw PII Leaks** | **0** | 0 leaks | **PASS** |
| **Raw Disk ChromaDB File Leaks (In-Scope)** | **0** | 0 leaks | **PASS** |
| **Person Name Leak Rate** | **3.7%** (1/27) | Report only | Documented |
| **Out-of-Scope Leak Rate (Known Gaps)** | **0.0%** (0/0) | Report only | Documented |
| **Character Leak Rate (Type-Agnostic)** | **0.0063** (20/3186 chars) | < 0.05 | **PASS** |
| **Over-Redaction Rate** | **0.0042** (149/35763 chars) | < 0.10 | **PASS** |
| **Business Fact Survival Rate** | **100.0%** (60/60) | 100% | **PASS (100% Retained)** |

## 2. Ingestion Dataset Specification

- **Total Documents Ingested**: 15 docs (300–1500 words each)
- **Total Chunks Stored**: 17 chunks in ChromaDB (`cosine` space)
- **Document Categories**: 3 HR Policies, 3 Loan Agreements, 3 Hospital Summaries, 3 Insurance Claims, 3 KYC Forms
- **Redaction Architecture**: Whole-document sanitization before chunking; ephemeral reversible map immediately discarded
- **Metadata Schema**: `source`, `doc_type`, `chunk_id`, `chunk_index`, `entity_count`, `risk_score`, and per-type entity counts only

## 3. Fact Survival Audit (Business Invariant Preservation)

All key business facts (notice periods, loan terms, clinical diagnoses, approved claims, and KYC verification modes) survived whole-document redaction and chunking intact:

| Document | Fact Name | Fact Value | Survived in Stored Chunks |
| :--- | :--- | :--- | :---: |
| `hr_policy_01.txt` | notice_period | `60 calendar days` | ✅ YES |
| `hr_policy_01.txt` | working_hours | `9:30 AM to 6:30 PM Monday through Friday` | ✅ YES |
| `hr_policy_01.txt` | annual_leave | `24 days of paid privilege leave` | ✅ YES |
| `hr_policy_01.txt` | probation_period | `6 months` | ✅ YES |
| `hr_policy_02.txt` | notice_period | `90 calendar days` | ✅ YES |
| `hr_policy_02.txt` | working_hours | `9:00 AM to 6:00 PM Monday through Saturday` | ✅ YES |
| `hr_policy_02.txt` | annual_leave | `18 days of paid privilege leave` | ✅ YES |
| `hr_policy_02.txt` | probation_period | `3 months` | ✅ YES |
| `hr_policy_03.txt` | notice_period | `30 calendar days` | ✅ YES |
| `hr_policy_03.txt` | working_hours | `10:00 AM to 7:00 PM with flexible core hours` | ✅ YES |
| `hr_policy_03.txt` | annual_leave | `30 days of paid privilege leave` | ✅ YES |
| `hr_policy_03.txt` | probation_period | `6 months` | ✅ YES |
| `loan_agreement_01.txt` | loan_amount | `INR 45,00,000` | ✅ YES |
| `loan_agreement_01.txt` | interest_rate | `8.65% per annum floating` | ✅ YES |
| `loan_agreement_01.txt` | tenure | `240 months` | ✅ YES |
| `loan_agreement_01.txt` | processing_fee | `INR 10,000` | ✅ YES |
| `loan_agreement_02.txt` | loan_amount | `INR 1,25,00,000` | ✅ YES |
| `loan_agreement_02.txt` | interest_rate | `11.25% per annum fixed` | ✅ YES |
| `loan_agreement_02.txt` | tenure | `84 months` | ✅ YES |
| `loan_agreement_02.txt` | prepayment_penalty | `2.0% of outstanding principal` | ✅ YES |
| `loan_agreement_03.txt` | loan_amount | `INR 6,50,000` | ✅ YES |
| `loan_agreement_03.txt` | interest_rate | `13.50% per annum reducing balance` | ✅ YES |
| `loan_agreement_03.txt` | tenure | `36 months` | ✅ YES |
| `loan_agreement_03.txt` | foreclosure_charges | `Zero charges after 12 EMIs` | ✅ YES |
| `hospital_discharge_01.txt` | primary_diagnosis | `Acute Laparoscopic Appendectomy` | ✅ YES |
| `hospital_discharge_01.txt` | discharge_status | `Hemodynamically stable and ambulatory` | ✅ YES |
| `hospital_discharge_01.txt` | follow_up_date | `7 days post-discharge` | ✅ YES |
| `hospital_discharge_01.txt` | discharge_medications | `Cefixime 200mg twice daily for 5 days` | ✅ YES |
| `hospital_discharge_02.txt` | primary_diagnosis | `Coronary Angioplasty with Single Drug-Eluting Stent` | ✅ YES |
| `hospital_discharge_02.txt` | discharge_status | `Stable cardiac sinus rhythm` | ✅ YES |
| `hospital_discharge_02.txt` | follow_up_date | `14 days post-discharge` | ✅ YES |
| `hospital_discharge_02.txt` | ejection_fraction | `55% preserved LV systolic function` | ✅ YES |
| `hospital_discharge_03.txt` | primary_diagnosis | `Left Knee Arthroscopic Meniscal Repair` | ✅ YES |
| `hospital_discharge_03.txt` | discharge_status | `Pain managed, non-weight bearing on left leg` | ✅ YES |
| `hospital_discharge_03.txt` | follow_up_date | `10 days post-discharge` | ✅ YES |
| `hospital_discharge_03.txt` | physiotherapy_protocol | `Gentle passive range of motion exercise starting Day 3` | ✅ YES |
| `insurance_claim_01.txt` | claim_number | `CLM-MOT-2026-88912` | ✅ YES |
| `insurance_claim_01.txt` | claimed_amount | `INR 78,500` | ✅ YES |
| `insurance_claim_01.txt` | approved_amount | `INR 68,200` | ✅ YES |
| `insurance_claim_01.txt` | deductible | `INR 2,000 mandatory excess` | ✅ YES |
| `insurance_claim_02.txt` | claim_number | `CLM-MED-2026-44109` | ✅ YES |
| `insurance_claim_02.txt` | claimed_amount | `INR 1,85,000` | ✅ YES |
| `insurance_claim_02.txt` | approved_amount | `INR 1,72,500` | ✅ YES |
| `insurance_claim_02.txt` | pre_authorization_status | `Pre-authorized within 4 hours` | ✅ YES |
| `insurance_claim_03.txt` | claim_number | `CLM-FIRE-2026-11045` | ✅ YES |
| `insurance_claim_03.txt` | claimed_amount | `INR 14,20,000` | ✅ YES |
| `insurance_claim_03.txt` | approved_amount | `INR 12,80,000` | ✅ YES |
| `insurance_claim_03.txt` | surveyor_assessment | `Electrical short-circuit without gross negligence` | ✅ YES |
| `kyc_form_01.txt` | account_type | `Individual Resident Demat and Trading Account` | ✅ YES |
| `kyc_form_01.txt` | risk_category | `Moderate Risk Profile` | ✅ YES |
| `kyc_form_01.txt` | verification_mode | `DigiLocker Video In-Person Verification (IPV)` | ✅ YES |
| `kyc_form_01.txt` | tax_residency | `Resident of India exclusively` | ✅ YES |
| `kyc_form_02.txt` | account_type | `Non-Resident External (NRE) Savings Account` | ✅ YES |
| `kyc_form_02.txt` | risk_category | `High Risk Tier-1 Enhanced Due Diligence` | ✅ YES |
| `kyc_form_02.txt` | overseas_residency | `United Arab Emirates` | ✅ YES |
| `kyc_form_02.txt` | annual_turnover_declaration | `Above INR 50,00,000` | ✅ YES |
| `kyc_form_03.txt` | account_type | `Mutual Fund Investment Folio Individual Account` | ✅ YES |
| `kyc_form_03.txt` | risk_category | `Low to Moderate Risk Profile` | ✅ YES |
| `kyc_form_03.txt` | fatca_status | `Not a US citizen or tax resident of any other jurisdiction` | ✅ YES |
| `kyc_form_03.txt` | nomination_status | `Single nominee registered with 100% share` | ✅ YES |

## 4. Known Out-of-Scope Architectural Gaps

With `recognizers-frozen-v3`, former out-of-scope gaps (`STREET_ADDRESS`, `BANK_ACCOUNT`, `DATE_OF_BIRTH`) have been brought in-scope and verified with **0 leaks**.
Remaining unhandled categories are documented in `docs/limitations.md`:
- **CONNECTION_STRING**: Database connection URIs.
- **PASSWORD**: Cleartext passwords and authentication tokens.
- **PEM_BLOCK / PRIVATE_KEY**: Cryptographic key and certificate blocks.
- **PERSON**: Statistical NER variance (e.g. 1/27 names unredacted).

These gaps are fully accounted for and isolated from core security invariants.

## 5. Security Invariant Verification Proof

```text
Ingestion Verification: 15 Documents, 17 Chunks
In-Scope Pattern PII Leaks: 0 / ZERO TOLERANCE MET
Fact Survival: 60/60 (100.0%)
Character Leak Rate: 0.0063
Over-Redaction Rate: 0.0042
ChromaDB Store Integrity: VERIFIED COSINE EMBEDDING SPACE
```
