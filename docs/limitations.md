# Known Limitations and Architectural Boundaries — VeilRAG

This document outlines the current detection boundaries, unhandled entity categories, and empirical leakage rates measured across the VeilRAG pipeline.

---

## 1. Unimplemented Entity Recognizers (Removed from `modes.yaml`)

The following entity types were previously scaffolded in `modes.yaml` under `code` mode but do **not** have functioning recognizers or pattern matchers in Presidio or VeilRAG detectors. They have been removed from mode configurations to avoid over-promising security coverage:

| Entity Type | Description | Status | Rationale / Future Roadmap |
| :--- | :--- | :---: | :--- |
| `CONNECTION_STRING` | Database and service URI strings (e.g., `postgres://...`, `mongodb://...`) | **Not Implemented** | High variance in syntax across database drivers; requires dedicated URI parser or specialized connection regex. |
| `PASSWORD` | Cleartext passwords and authentication tokens | **Not Implemented** | Lacks standard syntax structure; generic entropy detection triggers false positives on hashes, UUIDs, and random tokens. |
| `PEM_BLOCK` | X.509 certificate headers (`-----BEGIN CERTIFICATE-----`) | **Not Implemented** | Multiline delimiter parsing is outside the scope of current single-line regex detectors. |
| `PRIVATE_KEY` | Cryptographic private key headers (e.g. standard PKCS private key blocks) | **Not Implemented** | Block-level key headers require dedicated multiline scanner (flagged for future secret-scanning hook). |

---

## 2. Document-Level Out-of-Scope Gaps & Prompt 4A Resolution

Prior to Prompt 4A, the synthetic enterprise corpus ([`data/docs/`](file:///d:/Projects/VeilRAG/data/docs/)) contained three intentionally planted out-of-scope entity categories that accounted for an 86.63% out-of-scope leak rate and a 37.04% overall corpus character leak rate.

In Prompt 4A (`recognizers-frozen-v3`), dedicated contextual coverage recognizers ([`src/sanitizer/recognizers/coverage.py`](file:///d:/Projects/VeilRAG/src/sanitizer/recognizers/coverage.py)) were developed and integrated into `PIPELINE_MODE = "full"`:

| Entity Type | Original Gap Description | Prompt 4A Resolution Mechanism | New Leak Rate | Fact Survival Impact |
| :--- | :--- | :--- | :---: | :---: |
| `STREET_ADDRESS` | Unhandled in general NER; street addresses, flats, premises missed. | Contextual Indian address regex anchored from `Flat/House/Plot/No.` through a valid 6-digit PIN code (`[1-9]\d{5}`). | **0% (0/15)** | None (0 business facts affected). |
| `BANK_ACCOUNT` | Lacks checksum; raw 9–18 digit matching caused collisions. | Context-constrained 9–18 digit recognizer (`account`, `a/c`, `acct`) with priority span ranking over generic credit cards. | **0% (0/15)** | None (0 business facts affected). |
| `DATE_OF_BIRTH` | Generic date recognizers corrupted business facts and tenures. | Strict context window (~30 chars: `DOB`, `date of birth`, `born on`) for `dd-mm-yyyy`, `dd/mm/yyyy`, and textual dates. | **0% (0/15)** | **100% Retained** (60/60 facts preserved). |

---

## 3. Measured Ingestion Character Leakage Audit

Across the 15 enterprise documents (305–446 words each, containing 162 planted entities and 60 key business facts) evaluated in [`docs/ingest_report.md`](file:///d:/Projects/VeilRAG/docs/ingest_report.md):

| Scope | Leaked Characters | Gold Characters | Measured Character Leak Rate | Security Invariant Status |
| :--- | :---: | :---: | :---: | :--- |
| **Strict In-Scope Pattern & Structured PII** (Aadhaar, PAN, Email, Mobile, IFSC, UPI, Bank Account, Street Address, DOB) | **0** | **2,846** | **0.00% (Zero Leaks)** | **PASS** — Zero leaks across stored chunks, metadata, and raw disk files. |
| **In-Scope Person Names** | **20** | **340** | **5.88%** (1/27 names unredacted) | **Documented** — Statistical spaCy NER missed `"Vikramaditya Rathore"` in `hr_policy_02.txt`. |
| **Total In-Scope Corpus Leak (Post-Prompt 4A)** | **20** | **3,186** | **0.0063 (0.63%)** | **PASS** — Dropped from **37.04%** down to **0.63%**; well below the 5% security threshold. |
| **Historical Baseline (Pre-Prompt 4A with Out-of-Scope Gaps)** | 1,180 | 3,186 | 0.3704 (37.04%) | *Resolved by Prompt 4A coverage recognizers.* |

---

## 4. Business Fact Preservation Invariant

Redaction is intentionally constrained to avoid over-redacting business logic:
- Enabling `DATE_TIME` and `LOCATION` destroys **24 out of 60 business facts** in Corpus V1 (including notice periods, working hours, and overseas residency).
- By excluding aggressive date and location redaction from `PIPELINE_MODE = "full"`, VeilRAG preserves a **100% Fact Survival Rate (60/60 facts retained)** on Corpus V1 and **99.3% (288/290 facts retained)** on Corpus V2 while strictly guaranteeing zero leaks for core pattern-based in-scope PII.

---

## 5. Corpus V2 Generalization Benchmark & Unseen Phrasing Gaps

In Prompt 4B, VeilRAG was benchmarked against a 70-document generalization corpus ([`data/docs_v2/`](file:///d:/Projects/VeilRAG/data/docs_v2/)) spanning 7 document categories (140 ChromaDB chunks) under frozen recognizers (`recognizers-frozen-v3`). Deliberate linguistic variations and alternate phrasings were introduced to stress-test generalization boundaries.

As mandated by zero-tuning evaluation protocols, these recognizers were **not modified**; instead, empirical failure modes are categorized below as **unseen phrasing not covered**:

| Failure Category | Affected Type | Leaked / Planted | Leak Rate | Root Cause & Unseen Phrasing Analysis |
| :--- | :---: | :---: | :---: | :--- |
| **Address Anchors: Unseen Prefixes** | `STREET_ADDRESS` | 5 / 70 | 7.1% | **Unseen phrasing not covered**: Address recognizer was anchored strictly on `(?:Flat\|House\|Plot\|No\.?\|#)`. Addresses starting with `Room` (e.g. `Room 402, Shanti Nilayam Hostel...`) and `Sector` (e.g. `Sector 62, Block B, Electronic City...`) failed prefix anchoring and leaked into chunk text. |
| **Hospital ID Variations** | `UHID` | 4 / 20 | 20.0% | **Unseen phrasing not covered**: Recognizer targeted strictly hyphenated formats (`UH-\d+` and `IP-\d{4}-MED-\d+`). Bare numeric IDs (`UH889021`), unhyphenated admission IDs (`IP2026MED77412`), and labeled colons (`UHID: 44109823`) were not matched. |
| **Statistical NER Variance** | `PERSON` | 16 / 140 | 11.4% | Out-of-vocabulary Indian personal names (`Azad Tank`, `Ekaja Ram`, `Neelima Badal`, etc.) missed by statistical `en_core_web_sm` spaCy model without dictionary lookup or contextual boosting. |
| **Robustly Redacted Patterns** | `AADHAAR`, `PAN`, `INDIAN_MOBILE`, `EMAIL_ADDRESS`, `IFSC`, `UPI`, `BANK_ACCOUNT`, `DATE_OF_BIRTH` | 0 / 550 | **0.0% (Zero Leaks)** | High generalization: zero leaks across all 70 instances of each core structured identifier despite varied formatting (e.g. spaced DOBs, lowercase PANs, dashed mobiles, newline-adjacent accounts). |

### Summary Metrics on Corpus V2
- **Documents Audited**: 70
- **Total Chunks**: 140
- **Fact Survival**: 288/290 (99.3%)
- **Character Leak Rate**: 0.0878 (8.78%)
- **Over-Redaction Rate**: 0.0047 (0.47%)
- **Metadata Leaks**: 0 (0.0%)


