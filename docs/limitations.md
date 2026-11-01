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

## 2. Document-Level Out-of-Scope Gaps

The synthetic enterprise corpus ([`data/docs/`](file:///d:/Projects/VeilRAG/data/docs/)) includes intentionally planted out-of-scope entities (`in_scope=false` in [`data/docs/_ground_truth.json`](file:///d:/Projects/VeilRAG/data/docs/_ground_truth.json)) to benchmark current recognizer boundaries:

| Entity Type | Description | Observed Leak Rate | Architectural Reason |
| :--- | :--- | :---: | :--- |
| `STREET_ADDRESS` | Physical residential, clinical, and corporate addresses | **100% (15/15)** | General spaCy NER maps locations to `GPE`/`LOC`, which misses full street addresses, premises, flat numbers, and pin codes. |
| `BANK_ACCOUNT` | 11–16 digit bank account numbers | **100% (15/15)** | Account numbers lack fixed checksums (unlike Verhoeff for Aadhaar or Luhn for Credit Cards). Redacting generic 11–16 digit numbers causes unacceptable false positive collisions with internal tracking IDs and policy numbers. |
| `DATE_OF_BIRTH` | Dates of birth (e.g., `14-08-1988`, `22/11/1982`) | **6.7% (1/15)** | Enabling Presidio's generic `DATE_TIME` recognizer corrupts business facts (notice periods, hospital follow-up intervals, loan tenures). Specific date-of-birth contextual recognition is planned for a future release. |

---

## 3. Measured Ingestion Character Leakage Audit

Across the 15 enterprise documents (305–446 words each, containing 160 planted entities and 60 key business facts) evaluated in [`docs/ingest_report.md`](file:///d:/Projects/VeilRAG/docs/ingest_report.md):

| Scope | Leaked Characters | Gold Characters | Measured Character Leak Rate | Security Invariant Status |
| :--- | :---: | :---: | :---: | :--- |
| **Strict In-Scope Pattern PII** | **0** | **1,507** | **0.00% (Zero Leaks)** | **PASS** — Zero leaks for Aadhaar, PAN, Email, Mobile, IFSC, and UPI. |
| **In-Scope Person Names** | **20** | **340** | **5.88%** (1/27 names unredacted) | **Documented** — spaCy NER missed `"Vikramaditya Rathore"` in `hr_policy_02.txt`. |
| **In-Scope Combined (Reported)** | **20** | **1,847** | **0.0108 (1.08%)** | **PASS** — Under the 5% character leakage threshold. |
| **Out-of-Scope (Known Gaps)** | **1,160** | **1,339** | **0.8663 (86.63%)** | **Documented** — Unredacted street addresses, account numbers, and DOBs. |
| **Total Combined Corpus Leak** | **1,180** | **3,186** | **0.3704 (37.04%)** | **Documented** — 37.0% overall character leak when out-of-scope gaps are included. |

---

## 4. Business Fact Preservation Invariant

Redaction is intentionally constrained to avoid over-redacting business logic:
- Enabling `DATE_TIME` and `LOCATION` destroys **24 out of 60 business facts** (including notice periods, working hours, and overseas residency).
- By excluding aggressive date and location redaction from `PIPELINE_MODE = "full"`, VeilRAG preserves a **100% Fact Survival Rate (60/60 facts retained)** while strictly guaranteeing zero leaks for pattern-based in-scope PII.

