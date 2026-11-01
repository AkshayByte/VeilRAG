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
- Enabling `DATE_TIME` and `LOCATION` destroys **24 out of 60 business facts** (including notice periods, working hours, and overseas residency).
- By excluding aggressive date and location redaction from `PIPELINE_MODE = "full"`, VeilRAG preserves a **100% Fact Survival Rate (60/60 facts retained)** while strictly guaranteeing zero leaks for pattern-based in-scope PII.

