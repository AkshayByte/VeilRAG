# Project Progress — VeilRAG (Secure RAG Agent)

## Current Status Overview
- **Phase**: Prompt 0 (Scaffold) & Prompt 1 (Local PII Sanitizer) complete and verified.
- **Test Suite**: 61 passed out of 61 tests in 32.89s (`pytest tests/ -v`).
- **Sanitizer Tests**: 37 passed (`pytest tests/test_sanitizer.py -v`) — exceeds requirement of 25+.
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
    - **PAN**: `[A-Z]{5}[0-9]{4}[A-Z]`.
    - **IFSC**: `[A-Z]{4}0[A-Z0-9]{6}`.
    - **UPI IDs**: `name@bank`.
    - **Indian Mobile**: `+91` / 10 digits starting with 6–9.
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

## Verified Smoke Test Commands
```bash
# Smoke test with valid Verhoeff Aadhaar test vector
python -c "from src.sanitizer import sanitize; r=sanitize('Rahul Sharma, Aadhaar 2345 6789 0124, PAN ABCDE1234F, rahul@gmail.com'); print(r.sanitized_text); print(r.entities)"
```
**Output**:
```text
[PERSON_1], Aadhaar [IDENTITY_DOCUMENT_1], PAN [PAN_NUMBER_1], [EMAIL_ADDRESS_1]
[EntitySpan(entity_type='PERSON', start=0, end=12, score=0.85), EntitySpan(entity_type='IDENTITY_DOCUMENT', start=22, end=36, score=0.95), EntitySpan(entity_type='PAN_NUMBER', start=42, end=52, score=0.9), EntitySpan(entity_type='EMAIL_ADDRESS', start=54, end=69, score=1.0)]
```
*(Note: `2345 6789 0123` fails the Verhoeff checksum algorithm as check digit is 4; thus `2345 6789 0124` is used for positive validation, while `2345 6789 0123` serves as a verified negative test case for order-number lookalikes.)*

---

## What is Next
- **Prompt 2**: Local Embeddings & ChromaDB Vector Store Ingestion (`src/embeddings/local.py`, `src/rag/ingest.py`, `src/rag/retriever.py`).
  - Implement local embeddings with `sentence-transformers` (no network egress).
  - Document chunking and metadata preservation.
  - Fail-closed redaction prior to vector store insertion.
