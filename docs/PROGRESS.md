# Project Progress — VeilRAG (Secure RAG Agent)

## Current Status Overview
- **Phase**: Improvement Pass on PII Sanitizer & Measurement Integrity complete and verified.
- **Git Tags**:
  - `recognizers-frozen-v1`: Initial recognizers benchmarked on DEV and first held-out set (DEV2).
  - `recognizers-frozen-v2`: Post-diagnostic recognizers benchmarked on DEV, DEV2, and final HELD-OUT set.
- **Test Suite**: 71 passed out of 71 tests (`pytest tests/ -v`).
- **Sanitizer Tests**: 42 passed (`pytest tests/test_sanitizer.py -v`).
- **PII Eval Tests**: 7 passed (`pytest tests/test_pii_eval.py -v`).
- **Type Checking**: Clean (`mypy src/ tests/ scripts/` -> 0 issues in 40 source files).
- **Linting**: Clean (`ruff check src/ tests/ scripts/` -> 0 errors).

---

## Verification & Environment Parity
1. **Python Environment**:
   - Python 3.12 alignment across `Dockerfile` (`FROM python:3.12-slim`), GitHub Actions CI (`python-version: "3.12"`), and `pyproject.toml` (`requires-python = ">=3.11,<3.13"`, `target-version = "py312"`, `python_version = "3.12"`).
   - Core dependency imports verified: `presidio_analyzer`, `spacy`, `chromadb`, `langgraph`, `sentence_transformers` import cleanly.
2. **spaCy Model**:
   - Model `en_core_web_lg` configured in `Makefile`, `Dockerfile`, CI (`.github/workflows/ci.yml`), and defined in `src/config.py` (`settings.spacy_model`).
3. **Legal & Documentation**:
   - `LICENSE` (MIT), `THIRD_PARTY_NOTICES.md`, `README.md`, `docs/pii_results.md`, `docs/pii_errors.md`, and `docs/pii_errors_heldout.md` in place.
4. **Git Repository**:
   - Clean structure with tracked files, commit history, and release tags `recognizers-frozen-v1` and `recognizers-frozen-v2`.

---

## Recognizer Specifications & Invariants
- **Public API**:
  - `src/sanitizer/__init__.py`: exports `sanitize`, `SanitizeResult`, `SanitizationError`.
- **Entity Detection & Recognizer Rules**:
  - **Aadhaar**: 12 digits with Verhoeff checksum algorithm. Numbers starting with 0 or 1 are strictly rejected per UIDAI specification. Delimiters supported: spaced (`2345 6789 0124`), dashed (`2345-6789-0124`), dotted (`2345.6789.0124`), and contiguous (`234567890124`). Confidence score is context-weighted: 0.85 when Aadhaar context words (`aadhaar`, `uid`, `aadhar`, `enrolment`) are nearby, and 0.40 when bare.
  - **PAN**: `[A-Za-z]{5}[0-9]{4}[A-Za-z]`. Case-insensitive (accepts uppercase and lowercase).
  - **IFSC**: `[A-Z]{4}0[A-Z0-9]{6}`.
  - **UPI IDs**: `name@bank`.
  - **Indian Mobile**: `(?<!\d)(?:\+?91[\s\-]*)?[6-9]\d{4}[-\s]?\d{5}\b`. Formatted numbers (+91, 5+5 digit blocks, dashed) supported; negative lookbehind `(?<!\d)` strictly prevents false-positive substring collisions on 12-digit barcodes.
  - **Secrets & Credentials**: AWS Access/Secret keys, high-entropy secrets, PEM blocks, connection strings.
  - **Presidio built-ins**: `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `IBAN_CODE`, `IP_ADDRESS`, `URL`, `US_SSN`.
- **Placeholders**:
  - Clean user-friendly placeholders: `[AADHAAR_1]`, `[PAN_1]`, `[UPI_1]`, `[IFSC_1]`, `[PHONE_1]`, `[PERSON_1]`, `[EMAIL_ADDRESS_1]`, etc. Numbering is consistent within a document.
- **Fail-Closed Guarantee**:
  - Any detector exception raises `SanitizationError`; partial or unredacted text is never returned.
- **Security & Reversible Map**:
  - In-memory reversible mapping (`reversible_map`) kept exclusively in request scope (`repr=False`), never persisted or logged.

---

## Measured Evaluation Results (Real Numbers, Never Invented)

### 1. Development Dataset (DEV) — 210 cases (40 clean hard negatives)

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Delta |
| :--- | :---: | :---: | :---: |
| **Precision** | **0.9769** | 0.2982 | **+67.87%** |
| **Recall** | **0.9941** | 0.4824 | **+51.17%** |
| **F1 Score** | **0.9854** | 0.3685 | **+61.69%** |
| **Clean-case FPR** | **0.1000** | 0.4250 | **-32.50%** |
| **Character Leak Rate** | **0.0052** (14/2682 chars) | 0.2677 (718/2682 chars) | **-26.25%** |
| **Over-Redaction Rate** | **0.0043** (49/11276 chars) | 0.0364 (410/11276 chars) | **-3.21%** |
| **True Positives** | 169 | 82 | +87 |
| **False Positives** | 4 | 193 | -189 |
| **False Negatives** | 1 | 88 | -87 |

---

### 2. First Held-Out Run / Development Set 2 (DEV2) — 216 cases (60 clean hard negatives)
*Pre-fix one-shot run on `recognizers-frozen-v1`. Detailed diagnostic error report in `docs/pii_errors_heldout.md`.*

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Delta |
| :--- | :---: | :---: | :---: |
| **Precision** | **0.5636** | 0.1274 | **+43.62%** |
| **Recall** | **0.7949** | 0.3013 | **+49.36%** |
| **F1 Score** | **0.6596** | 0.1790 | **+48.06%** |
| **Clean-case FPR** | **0.3167** | 0.7333 | **-41.66%** |
| **True Positives** | 124 | 47 | +77 |
| **False Positives** | 96 | 322 | -226 |
| **False Negatives** | 32 | 109 | -77 |

---

### 3. Final Held-Out Dataset (HELD-OUT) — 222 cases (66 clean hard negatives)
*Evaluated strictly ONCE under frozen recognizers (`recognizers-frozen-v2`). Completely disjoint templates tested.*

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |
| :--- | :---: | :---: | :---: |
| **Precision** | **0.6976** | 0.1538 | **+54.38%** |
| **Recall** | **0.9167** | 0.3590 | **+55.77%** |
| **F1 Score** | **0.7922** | 0.2154 | **+57.68%** |
| **Clean-case FPR** | **0.1364** (9/66 flagged) | 0.6667 (44/66 flagged) | **-53.03%** |
| **Character Leak Rate** | **0.0061** (15/2443 chars) | 0.2767 (676/2443 chars) | **-27.06%** |
| **Over-Redaction Rate** | **0.0503** (722/14348 chars) | 0.0984 (1412/14348 chars) | **-4.81%** |
| **True Positives** | 143 | 56 | +87 |
| **False Positives** | 62 | 308 | -246 |
| **False Negatives** | 13 | 100 | -87 |

**Core Highlights**:
- **99.39% Character Protection**: Type-agnostic character leak rate is 0.0061 (only 15 sensitive characters unredacted out of 2,443 across the entire corpus).
- **100% Recall Across Core ID & Credentials**:
  - `IDENTITY_DOCUMENT` (Aadhaar): 30/30 (100% recall, F1: 0.9524)
  - `PAN_NUMBER`: 25/25 (100% recall, 100% precision, F1: 1.0000)
  - `EMAIL_ADDRESS`: 25/25 (100% recall, 100% precision, F1: 1.0000)
  - `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `SECRET_KEY`, `US_SSN`, `IBAN_CODE`, `IFSC_CODE`, `UPI_ID`: 100% recall and 100% precision.
- **Zero Substring Barcode False Positives**: `INDIAN_MOBILE` precision improved to 1.0000 (0 false positives).

---

## Verified Evaluation & Test Commands
```bash
# 1. Full Unit Test Suite (71 tests passing)
pytest tests/ -v

# 2. DEV Set Evaluation (VeilRAG vs Presidio Baseline)
python -m src.eval.pii_eval --dataset dev

# 3. DEV2 Set Evaluation (Pre-Fix Held-Out Run)
python -m src.eval.pii_eval --dataset dev2

# 4. Final HELD-OUT Set Evaluation (VeilRAG vs Presidio Baseline)
python -m src.eval.pii_eval --dataset heldout

# 5. Type and Linting Checks
ruff check src/ tests/ scripts/
mypy src/ tests/ scripts/
```

---

## What is Next
- **Prompt 3**: Ingestion pipeline (`src/rag/ingest.py`) & ChromaDB vector store with sentence-transformers local embeddings.
- Ensure documents are sanitized via `src.sanitizer.sanitize` *before* chunking and embedding.
- Maintain hash-chained audit logging for each ingested document chunk.
