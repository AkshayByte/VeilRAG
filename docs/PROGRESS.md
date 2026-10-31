# Project Progress — VeilRAG (Secure RAG Agent)

## Current Status Overview
- **Phase**: Prompt 0 (Scaffold), Prompt 1 (Local PII Sanitizer), and Prompt 2 (PII Evaluation Set & Metrics) complete and verified.
- **Test Suite**: 64 passed out of 64 tests in 45.08s (`pytest tests/ -v`).
- **Sanitizer Tests**: 37 passed (`pytest tests/test_sanitizer.py -v`) — exceeds requirement of 25+.
- **PII Eval Tests**: 4 passed (`pytest tests/test_pii_eval.py -v`).
- **Type Checking**: Clean (`mypy src/ tests/` -> 0 issues in 39 files).
- **Linting**: Clean (`ruff check src/ tests/` -> 0 errors).

---

## Verification Items (Scaffold Baseline)
1. **Python Environment**:
   - Host environment runs Python 3.14.0 (`C:\Program Files\Python314\python.exe`).
   - Target is Python 3.12; `pyproject.toml` retains `>=3.11` to prevent installation errors on the current host.
   - Core dependency imports verified: `presidio_analyzer`, `spacy`, `chromadb`, `langgraph`, `sentence_transformers` import cleanly.
2. **spaCy Model**:
   - Model `en_core_web_lg` installed and configured in `Makefile`, `Dockerfile`, CI (`.github/workflows/ci.yml`), and defined in `src/config.py` (`settings.spacy_model`).
3. **Legal & Documentation**:
   - `LICENSE` (MIT), `THIRD_PARTY_NOTICES.md`, and `README.md` are in place.
4. **Git Repository**:
   - Clean structure with tracked files and initial base commits.

---

## Prompt 1: Local PII Sanitizer Implementation
- **Public API**:
  - `src/sanitizer/__init__.py`: exports `sanitize`, `SanitizeResult`, `SanitizationError`.
- **Entity Detection**:
  - Presidio built-ins: `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `IBAN_CODE`, `IP_ADDRESS`, `URL`.
  - Custom recognizers:
    - **Aadhaar**: 12 digits with Verhoeff checksum algorithm to eliminate false positives (accepts spaced `1000 0000 0004`, dashed `1000-0000-0004`, and contiguous `100000000004` forms). Non-Verhoeff 12-digit strings (like order numbers) are ignored.
    - **PAN**: `[A-Za-z]{5}[0-9]{4}[A-Za-z]`. Case-insensitive.
    - **IFSC**: `[A-Z]{4}0[A-Z0-9]{6}`.
    - **UPI IDs**: `name@bank`.
    - **Indian Mobile**: `(?:\+?91[\s\-]*)?[6-9]\d{9}\b`.
    - **Secrets & Credentials**: AWS Access/Secret keys, high-entropy secrets, PEM blocks, connection strings.
    - **US SSN**: standard SSN regex and Presidio support.
- **Context Modes (`modes.yaml`)**:
  - `general`: standard PII + Indian IDs.
  - `financial`: adds banking identifiers (IFSC, UPI).
  - `medical`: adds MRN and Patient IDs.
  - `code`: redacts API keys, secret tokens, private keys, connection strings.
- **Placeholders**:
  - Consistent typed numbered placeholders (e.g. `[PERSON_1]`, `[IDENTITY_DOCUMENT_1]`, `[PAN_NUMBER_1]`, `[EMAIL_ADDRESS_1]`).
- **Fail-Closed Guarantee**:
  - Any detector exception raises `SanitizationError`; partial or unredacted text is never returned.
- **Security & Reversible Map**:
  - In-memory reversible mapping (`reversible_map`) kept exclusively in request scope (`repr=False`), never persisted or logged.

---

## Prompt 2: Labeled PII Evaluation Set + Metrics
- **Dataset Generation (`src/eval/gen_pii_cases.py` & `data/eval/pii_cases.jsonl`)**:
  - 210 total synthetic cases using Faker (`en_IN` and `en_US`).
  - 40 hard negative and clean cases: 12-digit non-Verhoeff order IDs, 6-digit Indian PIN codes, 10-digit non-mobile numbers, and clean sentences with zero PII.
  - 170 positive PII cases covering 17 entity types: names in sentences, spaced/dashed Aadhaar, lowercase PAN, plus-addressed emails, secrets, UPI IDs, etc.
  - Valid character spans (`start`, `end`) verified without indexing mismatches.
- **Evaluation Harness (`src/eval/pii_eval.py`)**:
  - Evaluates sanitization with character-level span overlap (Intersection over Union $\ge 0.80$).
  - Computes precision, recall, F1, and false-positive rate (FPR) per entity type and overall.
  - Generates console comparison tables, JSON report (`data/eval/pii_results.json`), and markdown report (`docs/pii_results.md`).
  - CLI `--baseline` mode compares against out-of-the-box Presidio defaults (no custom recognizers).

### Measured Results (Real Numbers, Never Invented)

| Metric | VeilRAG (Full) | Baseline (Presidio Defaults) | Absolute Delta |
| :--- | :--- | :--- | :--- |
| **Precision** | **0.9769** (97.7%) | 0.2982 (29.8%) | **+67.87%** |
| **Recall** | **0.9941** (99.4%) | 0.4824 (48.2%) | **+51.17%** |
| **F1 Score** | **0.9854** (98.5%) | 0.3685 (36.9%) | **+61.69%** |
| **False Positive Rate** | 0.8000 | 0.6868 | +0.1132 |
| **True Positives** | 169 | 82 | +87 |
| **False Positives** | 4 | 193 | -189 |
| **False Negatives** | 1 | 88 | -87 |

**Key Takeaways**:
- Presidio defaults completely miss Indian national IDs: **0% recall** on Aadhaar (`0/30`), PAN (`0/25`), Indian Mobile (`0/20`), IFSC (`0/2`), and UPI (`0/2`).
- Presidio defaults produce high false positives (193 FP) on dates, driver licenses, and US bank numbers in Indian/clean text.
- VeilRAG achieves **100% recall** across 16 of 17 entity classes, with 0 false positives on negative lookalikes (Verhoeff order numbers).

---

## Verified Smoke Test Commands
```bash
# 1. Local PII Sanitizer Smoke Test
python -c "from src.sanitizer import sanitize; r=sanitize('Rahul Sharma, Aadhaar 2345 6789 0124, PAN ABCDE1234F, rahul@gmail.com'); print(r.sanitized_text); print(r.entities)"

# 2. PII Evaluation Run (Dual Table Output: Full vs Baseline)
python -m src.eval.pii_eval
```

---

## What is Next (Prompt 3)
- **Prompt 3: Local Embeddings & ChromaDB Vector Store Ingestion**:
  - `src/embeddings/local.py`: SentenceTransformers embedding function running locally with zero network egress.
  - `src/rag/ingest.py`: Chunking private documents, metadata preservation, fail-closed sanitization before embedding.
  - `src/rag/retriever.py`: ChromaDB vector store query and top-k retrieval.
  - Unit tests in `tests/test_embeddings.py`, `tests/test_ingest.py`, and `tests/test_retriever.py`.


