# Project Progress — VeilRAG (Secure RAG Agent)

## Current Status Overview
- **Phase**: Prompt 0 (Scaffold), Prompt 1 (Local PII Sanitizer), Prompt 2 (PII Evaluation Set & Metrics), and Measurement Integrity Pass complete and verified.
- **Git Tag**: `recognizers-frozen-v1` tagged; recognizers frozen for strictly honest evaluation.
- **Test Suite**: 66 passed out of 66 tests (`pytest tests/ -v`).
- **Sanitizer Tests**: 39 passed (`pytest tests/test_sanitizer.py -v`).
- **PII Eval Tests**: 6 passed (`pytest tests/test_pii_eval.py -v`).
- **Type Checking**: Clean (`mypy src/ tests/` -> 0 issues in 39 source files).
- **Linting**: Clean (`ruff check src/ tests/` -> 0 errors).

---

## Verification Items (Scaffold Baseline)
1. **Python Environment**:
   - Host environment runs Python 3.14.0 (`C:\Program Files\Python314\python.exe`).
   - Dockerfile pins `python:3.11-slim`, CI pins `python-version: "3.11"`, `pyproject.toml` pins `>=3.11`.
   - Core dependency imports verified: `presidio_analyzer`, `spacy`, `chromadb`, `langgraph`, `sentence_transformers` import cleanly.
2. **spaCy Model**:
   - Model `en_core_web_lg` installed and configured in `Makefile`, `Dockerfile`, CI (`.github/workflows/ci.yml`), and defined in `src/config.py` (`settings.spacy_model`).
3. **Legal & Documentation**:
   - `LICENSE` (MIT), `THIRD_PARTY_NOTICES.md`, `README.md`, `docs/pii_results.md`, and `docs/pii_errors.md` in place.
4. **Git Repository**:
   - Clean structure with tracked files, commit history, and release tag `recognizers-frozen-v1`.

---

## Recognizer Specifications & Invariants
- **Public API**:
  - `src/sanitizer/__init__.py`: exports `sanitize`, `SanitizeResult`, `SanitizationError`.
- **Entity Detection & Recognizer Rules**:
  - **Aadhaar**: 12 digits with Verhoeff checksum algorithm. Numbers starting with 0 or 1 are strictly rejected per UIDAI specification. Confidence score is context-weighted: 0.85 when Aadhaar context words (`aadhaar`, `uid`, `aadhar`, `enrolment`) are nearby, and 0.40 when bare.
  - **PAN**: `[A-Za-z]{5}[0-9]{4}[A-Za-z]`. Case-insensitive (accepts uppercase and lowercase).
  - **IFSC**: `[A-Z]{4}0[A-Z0-9]{6}`.
  - **UPI IDs**: `name@bank`.
  - **Indian Mobile**: `(?:\+?91[\s\-]*)?[6-9]\d{9}\b`.
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
| **Precision** | **0.9769** (97.7%) | 0.2982 (29.8%) | **+67.87%** |
| **Recall** | **0.9941** (99.4%) | 0.4824 (48.2%) | **+51.17%** |
| **F1 Score** | **0.9854** (98.5%) | 0.3685 (36.9%) | **+61.69%** |
| **Clean-case FPR** | **0.1000** (10.0%) | 0.4250 (42.5%) | **-32.50%** |
| **True Positives** | 169 | 82 | +87 |
| **False Positives** | 4 | 193 | -189 |
| **False Negatives** | 1 | 88 | -87 |

*Error analysis for all 4 FPs and 1 FN documented in [`docs/pii_errors.md`](file:///d:/Projects/VeilRAG/docs/pii_errors.md).*

### 2. Held-Out Dataset (HELD-OUT) — 216 cases (60 clean hard negatives)
*Evaluated ONCE with frozen recognizers (`recognizers-frozen-v1`). Features typos in labels, common-word names, lowercase PAN, dotted digits, and Hinglish sentences.*

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Delta |
| :--- | :---: | :---: | :---: |
| **Precision** | **0.5636** (56.4%) | 0.1274 (12.7%) | **+43.62%** |
| **Recall** | **0.7949** (79.5%) | 0.3013 (30.1%) | **+49.36%** |
| **F1 Score** | **0.6596** (66.0%) | 0.1790 (17.9%) | **+48.06%** |
| **Clean-case FPR** | **0.3167** (31.7%) | 0.7333 (73.3%) | **-41.66%** |
| **True Positives** | 124 | 47 | +77 |
| **False Positives** | 96 | 322 | -226 |
| **False Negatives** | 32 | 109 | -77 |

**Key Findings**:
- **Baseline Presidio Collapses**: Drops to 30.1% recall and 73.3% FPR with 322 false positives on Indian and formatted data.
- **VeilRAG Core Strength**: Delivers **100% recall** across `PAN_NUMBER`, `EMAIL_ADDRESS`, `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `IFSC_CODE`, `UPI_ID`, `SECRET_KEY`, `US_SSN`, `CREDIT_CARD`.
- **Honest Generalization Gap**: Common English words used as person names ("Will", "Rose", "Hope", "Summer") and dotted numbers test NER limits, establishing transparent baseline metrics for resume evaluation.

---

## Verified Smoke Test Commands
```bash
# 1. Local PII Sanitizer Smoke Test
python -c "from src.sanitizer import sanitize; r=sanitize('Rahul Sharma, Aadhaar 2345 6789 0124, PAN ABCDE1234F, rahul@gmail.com'); print(r.sanitized_text); print(r.entities)"

# 2. DEV Set Evaluation (VeilRAG vs Presidio Baseline)
python -m src.eval.pii_eval --dataset dev

# 3. HELD-OUT Set Evaluation (VeilRAG vs Presidio Baseline)
python -m src.eval.pii_eval --dataset heldout

# 4. HELD-OUT Set Baseline Only
python -m src.eval.pii_eval --dataset heldout --baseline
```

---

## What is Next (Prompt 3)
- **Prompt 3: Local Embeddings & ChromaDB Vector Store Ingestion**:
  - `src/embeddings/local.py`: SentenceTransformers (`all-MiniLM-L6-v2`) wrapper with local caching and zero network egress.
  - Generate synthetic private customer documents in `data/docs/`.
  - `src/rag/ingest.py`: Chunking private documents, metadata preservation, fail-closed sanitization before vector embedding.
  - `src/rag/retriever.py`: ChromaDB local persistent store and top-$k$ similarity retrieval.
  - Unit tests in `tests/test_embeddings.py`, `tests/test_ingest.py`, and `tests/test_retriever.py`.
  - Unit tests in `tests/test_embeddings.py`, `tests/test_ingest.py`, and `tests/test_retriever.py`.


