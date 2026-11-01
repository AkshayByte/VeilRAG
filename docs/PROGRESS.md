# Project Progress — VeilRAG (Secure RAG Agent)

## Current Status Overview
- **Phase**: Prompt 4 (Corrective-RAG LangGraph Agent with Factual Verification & Output Guard) complete and verified.
- **Git Tags**:
  - `recognizers-frozen-v1`: Initial recognizers benchmarked on DEV and first held-out set (DEV2).
  - `recognizers-frozen-v2`: Post-diagnostic recognizers benchmarked on DEV, DEV2, and final HELD-OUT set.
- **Test Suite**: 97 passed out of 97 selected tests (`pytest tests/ -v -m "not slow"`).
- **Type Checking**: Clean (`mypy src/ tests/ scripts/` -> 0 issues in 44 source files).
- **Linting**: Clean (`ruff check src/ tests/ scripts/` -> 0 errors).

---

## Verification & Environment Parity
1. **Python Environment**:
   - Python 3.14 alignment across `Dockerfile` (`FROM python:3.14-slim`), GitHub Actions CI (`python-version: "3.14"`), and `pyproject.toml` (`requires-python = ">=3.11"`, `target-version = "py314"`, `python_version = "3.14"`).
   - Core dependency imports verified: `presidio_analyzer`, `spacy`, `chromadb`, `langgraph`, `sentence_transformers` import cleanly.
2. **spaCy Model**:
   - Model `en_core_web_lg` configured in `Makefile`, `Dockerfile`, CI (`.github/workflows/ci.yml`), and defined in `src/config.py` (`settings.spacy_model`).
3. **Legal & Documentation**:
   - `LICENSE` (MIT), `THIRD_PARTY_NOTICES.md`, `README.md`, `docs/pii_results.md`, `docs/pii_errors.md`, `docs/pii_errors_heldout.md`, `docs/ingest_report.md`, and `docs/limitations.md` in place.
4. **Git Repository**:
   - Clean structure with tracked files, commit history, and release tags `recognizers-frozen-v1` and `recognizers-frozen-v2`.

---

## Recognizer Specifications & Invariants
- **Public API**:
  - `src/sanitizer/__init__.py`: exports `sanitize`, `SanitizedText`, `SanitizeResult`, `SanitizationError`.
  - Mode `"full"` in `modes.yaml`: Union of all 19 working entity recognizers.
  - Central `PIPELINE_MODE = "full"` constant in `src/config.py` governs ingestion, query path, rewriting, and guards.
- **Type-Enforced Redaction Boundary**:
  - `SanitizedText(str)` subclass can only be instantiated inside `src.sanitizer.sanitize()` via a private sentinel.
  - Slicing or concatenating automatically produces a plain `str`, stripping the `SanitizedText` brand.
  - All downstream ingestion, embedding (`EmbeddingModel.embed`, `embed_query`), vector store (`VectorStore.search`, `VectorStore.add`), and LLM adapter entry points (`complete`, `acomplete`, `astream`) strictly reject plain `str` inputs with `TypeError`.
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
  - In-memory reversible mapping (`reversible_map`) kept exclusively in request scope (`repr=False`), never persisted or logged. Discarded immediately during document ingestion.

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

*(Note: The held-out dataset was adjusted twice post-generation: (1) Stripe-style keys were replaced with runtime-constructed mock secrets to satisfy GitHub push protection, (2) an over-correction that temporarily changed AWS access keys to an AWSK prefix was reverted because it made them undetectable by construction, restoring the exact original AKIA vectors).*

**Core Highlights**:
- **99.39% Character Protection**: Type-agnostic character leak rate is 0.0061 (only 15 sensitive characters unredacted out of 2,443 across the entire corpus).
- **100% Recall Across Core ID & Credentials**:
  - `IDENTITY_DOCUMENT` (Aadhaar): 30/30 (100% recall, F1: 0.9524)
  - `PAN_NUMBER`: 25/25 (100% recall, 100% precision, F1: 1.0000)
  - `EMAIL_ADDRESS`: 25/25 (100% recall, 100% precision, F1: 1.0000)
  - `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `SECRET_KEY`, `US_SSN`, `IBAN_CODE`, `IFSC_CODE`, `UPI_ID`: 100% recall and 100% precision.
- **Zero Substring Barcode False Positives**: `INDIAN_MOBILE` precision improved to 1.0000 (0 false positives).

---

### 4. Secure Ingestion & Local Retrieval Audit (Prompt 3 Results)
*Evaluated across 15 synthetic enterprise documents (300-1500 words each) and 19 ChromaDB chunks.*
*Detailed breakdown and audit trail in `docs/ingest_report.md`.*

| Evaluation Metric | Measured Result | Security Target | Status |
| :--- | :--- | :--- | :--- |
| **Pattern PII Leaks (Aadhaar, PAN, Email, Mobile, IFSC, UPI)** | **0** | 0 leaks | **PASS (Zero Leaks)** |
| **Metadata Raw PII Leaks** | **0** | 0 leaks | **PASS** |
| **Raw Disk ChromaDB File Leaks (In-Scope)** | **0** | 0 leaks | **PASS** |
| **Person Name Leak Rate** | **3.7%** (1/27) | Report only | Documented |
| **Out-of-Scope Leak Rate (Known Architectural Gaps)** | **68.9%** (31/45) | Report only | Documented |
| **Character Leak Rate (Type-Agnostic)** | **0.0108** (20/1847 chars) | < 0.05 | **PASS** |
| **Over-Redaction Rate** | **0.0070** (260/37102 chars) | < 0.10 | **PASS** |
| **Business Fact Survival Rate** | **100.0%** (60/60) | 100% | **PASS (100% Retained)** |

**Key Ingestion Findings**:
1. **Zero-Leak Invariant**: Zero occurrences of pattern-based in-scope PII strings in ChromaDB chunk text, metadata dictionaries, or binary files on disk (`data/chroma`).
2. **Fact Survival (100%)**: Every key contractual fact (notice period, leave days, loan amount, interest rate, discharge diagnosis, approved claim amount, and KYC verification mode) was preserved uncorrupted in the stored chunks.
3. **Fail-Closed and Idempotent**: Whole-document sanitization is fail-closed per document; deterministic chunk indexing ensures idempotency on repeated ingestion runs.

---

### 5. Corrective-RAG LangGraph Agent & Safety Boundary (Prompt 4 Results)
*Stateful Corrective-RAG agent with factual verification, output guard, and fail-closed safety invariants.*
*Graph exported to `docs/agent_graph.md` via `LangGraph.draw_mermaid()`.*

1. **Architecture & State Machine (`src/rag/agent.py`)**:
   - Typed state `AgentState` manages execution trace, latency, tokens, cost, and entity counts.
   - **`sanitize_query`**: Sanitizes user query with `mode=PIPELINE_MODE` (`"full"`) and `placeholder_prefix="Q_"`.
   - **`retrieve`**: Locates top candidate chunks via local embeddings and ChromaDB vector store.
   - **`grade_documents`**: LLM evaluates candidate chunks for query relevance (binary yes/no).
   - **`rewrite_query`**: Triggers when fewer than 2 chunks are relevant. Re-sanitizes rewritten query (max 2 rewrites).
   - **`generate`**: Context-bound generation strictly citing chunk IDs (e.g. `[doc_id#chunk_n]`). Returns "I don't know." if < 2 relevant chunks.
   - **`verify_answer`**: Fact-checking step verifying all claims are grounded in context. Regenerates once if unsupported claims are detected; falls back to "I don't know.".
   - **`output_guard`**: Re-sanitizes final response under `PIPELINE_MODE`, logs entity counts, and generates revealed text if requested.
   - Hard execution limit enforced (max 15 graph steps).

2. **Single LLM Adapter Interface (`src/llm.py`)**:
   - `LLM_PROVIDER = fake | ollama | anthropic` (defaults to deterministic offline `fake`).
   - Strict `SanitizedText` brand enforcement across `complete()`, `acomplete()`, and `astream()` (`TypeError` on plain `str`).
   - Token usage and cost tracking ($3/M in, $15/M out for Claude 3.5 Sonnet).
   - Security invariant: Full prompts and answers are **never logged** at any logging level. Only token counts, cost, provider, and duration are recorded in telemetry.

3. **Placeholder Collision Prevention**:
   - Query placeholders use prefix `Q_` (e.g., `[Q_PERSON_1]`, `[Q_AADHAAR_1]`), preventing collision with chunk tokens (`[PERSON_1]`, `[AADHAAR_1]`).
   - Sanitizer idempotency verified: `sanitize(sanitize(x)) == sanitize(x)` for placeholder text.

4. **Query-Scoped Revealing (`--reveal`)**:
   - Reverses only placeholders generated from the user's query (`query_reversible_map`).
   - Chunk originals are never stored in the vector store and cannot be revealed.

5. **Regression Guard**:
   - `python -m src.eval.pii_eval --dataset heldout` verified at **143 TP / 62 FP / 13 FN** (Zero regression).

---

## Verified Evaluation & Test Commands
```bash
# 1. Full Unit Test Suite (97 tests passing)
pytest tests/ -v -m "not slow"

# 2. Held-Out PII Eval Regression Guard (143 TP / 62 FP / 13 FN)
python -m src.eval.pii_eval --dataset heldout

# 3. Corrective-RAG CLI Commands
python -m src.rag.cli ask "What is the notice period in hr_policy_01?"
python -m src.rag.cli ask "What is the secret recipe for Martian space pie?"
python -m src.rag.cli ask "My Aadhaar is 2345 6789 0124. What is the loan tenure?" --show-prompts
python -m src.rag.cli peek --full
python -m src.rag.cli query "notice period"

# 4. Ingestion Security & Fact Survival Audit
python -m src.eval.ingest_eval

# 5. Type and Linting Checks
ruff check src/ tests/ scripts/
mypy src/ tests/ scripts/
```

---

## What is Next
- **Prompt 5**: End-to-end RAG evaluation & quality metrics (answer correctness, citation fidelity, hallucination rate, and adversarial injection resistance).
- Integrate hash-chained audit logging across all graph steps.
