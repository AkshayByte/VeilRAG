# Project Progress — VeilRAG (Secure RAG Agent)

## Current Status Overview
- **Phase**: Prompt 5, Part 1 (RAG Evaluation Harness & Ablations) complete and verified.
- **Git Tags**:
  - `recognizers-frozen-v1`: Initial recognizers benchmarked on DEV and first held-out set (DEV2).
  - `recognizers-frozen-v2`: Post-diagnostic recognizers benchmarked on DEV, DEV2, and final HELD-OUT set.
  - `recognizers-frozen-v3`: Coverage recognizers for DATE_OF_BIRTH, BANK_ACCOUNT, ADDRESS, and Hospital IDs benchmarked on DEV3 and HELDOUT3.
- **Corpus V2 Generalization**: 70 documents, 140 chunks ingested with `CHUNK_SIZE_TOKENS=300` and `CHUNK_OVERLAP_TOKENS=60`. Evaluated ONCE without tuning; gaps documented in `docs/limitations.md`.
- **RAG Evaluation Harness & Ablations**:
  - `data/eval/qa_test.jsonl`: Exactly 40 questions (26 answerable key-fact with unique gold docs, 8 unanswerable, 6 PII extraction attempts).
  - `data/eval/qa_dev.jsonl`: 10 debug questions (6 answerable, 2 unanswerable, 2 PII).
  - Configurable pipeline ablations: A (Naive RAG), B (+ Grading/Rewrite), C (+ Verification), D (Full System).
  - Response cache under `data/cache/` (gitignored), cost cap guard (`MAX_EVAL_COST_USD`), Wilson 95% confidence intervals on all proportions.
  - LLM judge rubric calibrated with 10 manual spot checks in `docs/judge_spot_checks.md`.
- **Test Suite**: 131 passed out of 131 selected tests (`pytest tests/ -v -m "not slow"`).
- **Type Checking**: Clean (`mypy src/ tests/ scripts/` -> 0 issues in 50 source files).
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

### 6. Coverage Recognizers & Privacy Gap Closure (Prompt 4A Results)
*Closed the measured 37.0% character leak caused by previously out-of-scope enterprise entities.*
*Tagged release: `recognizers-frozen-v3`.*

1. **Coverage Recognizers (`src/sanitizer/recognizers/coverage.py`)**:
   - `DATE_OF_BIRTH`: Window-based contextual recognizer (`DOB`, `date of birth`, `born on`) requiring ~30 chars context for dates (`dd-mm-yyyy`, `dd/mm/yyyy`, `19 March 1990`). Does not capture generic business dates.
   - `BANK_ACCOUNT`: 9–18 digit contextual recognizer (`account`, `a/c`, `acct`) with priority tie-breaking over generic `CREDIT_CARD`.
   - `ADDRESS`: Indian address span from `Flat/House/Plot/No./#` ... through a 6-digit PIN code (`[1-9]\d{5}`).
   - `UHID`/Hospital ID: Contextual UHID (`UH-\d+`), IP admission numbers (`IP-\d{4}-MED-\d+`), and MRN/PID variants.
   - Clean placeholders: `[DOB_1]`, `[ACCOUNT_1]`, `[ADDRESS_1]`, `[UHID_1]`.

2. **Benchmarking & Evaluation Protocol**:
   - Tuned exclusively on `data/eval/pii_dev3.jsonl` (139 cases: 82 positives, 57 hard negatives generated via `scripts/gen_pii_dev3.py`):
     - **82/82 TP**, **0 FN** (**100% recall**), **0.0000** character leak rate, **0.0199** over-redaction rate.
   - Evaluated strictly **ONCE** on unseen held-out set `data/eval/pii_heldout3.jsonl` (139 cases generated via `scripts/gen_pii_heldout3.py`):
     - **82/82 TP**, **0 FN** (**100% recall**), **0.0000** character leak rate, **0.0184** over-redaction rate.
     - Zero tuning after the heldout3 run. Detailed logs in `docs/pii_results_heldout3.md` and `docs/pii_errors_heldout3.md`.
   - **Regression Check on Held-Out v2**:
     - `python -m src.eval.pii_eval --dataset heldout` strictly maintained **143 TP / 62 FP / 13 FN** (Zero regression).

3. **Ingestion Security & Character Leakage Impact**:
   - Re-ingested 15 enterprise documents into fresh `data/chroma` store (17 chunks).
   - In-Scope Pattern & Structured PII leaks: **0 leaks** (Aadhaar, PAN, Email, Mobile, IFSC, UPI, Bank Account, Street Address, DOB all verified 0 leaks in chunk text, metadata, and disk).
   - Fact Survival: **60/60 (100.0%) retained** intact.
   - Character Leak Rate: dropped from **37.04%** (when out-of-scope gaps were unredacted) and **1.08%** (in-scope only) down to **0.0063 (0.63%)** (20 leaked chars out of 3,186 gold chars, representing only 1 missed person name: `"Vikramaditya Rathore"`).
   - Over-Redaction Rate: **0.0042** (149 over-redacted chars out of 35,763 non-PII chars).

### 7. Corpus Scaling & Generalization Benchmark (Prompt 4B Results)
*Stress-tested generalization on a 70-document enterprise corpus (`data/docs_v2/`) with frozen recognizers (`recognizers-frozen-v3`).*

1. **Test Suite Expansion (`tests/test_coverage_recognizers.py`)**:
   - Added 21 dedicated unit tests validating `DATE_OF_BIRTH`, `BANK_ACCOUNT`, `STREET_ADDRESS`, and `UHID` recognizers against both positive variants and hard negatives (e.g. invoice dates, due dates, order numbers, 9-digit quantities, address without PIN, and policy numbers).
   - All 21 tests pass cleanly.

2. **Corpus V2 Ingestion & Architecture**:
   - 70 synthetic enterprise documents generated across 7 categories (HR policy, loan agreement, hospital discharge, insurance claim, KYC form, vendor contract, lease agreement).
   - Configured `CHUNK_SIZE_TOKENS = 300` and `CHUNK_OVERLAP_TOKENS = 60` in `src/config.py`.
   - Ingested 140 chunks into fresh `data/chroma` vector store via `python -m src.rag.ingest --corpus v2`.
   - Both `ingest.py` and `ingest_eval.py` support `--corpus v1|v2` (defaulting to `v2`).

3. **Generalization Benchmark (Run Strictly ONCE without Post-Eval Tuning)**:
   - **Pattern In-Scope Leaks**: 9 leaks out of hundreds of planted entities across 70 docs:
     - 5 address leaks: caused by unseen prefix anchors (`Room` [2] and `Sector` [3]).
     - 4 hospital ID leaks: caused by unhyphenated bare IDs (`UH889021`), unhyphenated admission IDs (`IP2026MED77412`), and labeled colons (`UHID: 44109823`).
   - **Core Structured Identifier Redaction**: **0 leaks (100% redacted)** across all 70 instances of Aadhaar, PAN, Indian Mobile, Email, IFSC, UPI, Bank Account, and Date of Birth despite wide phrasing/formatting variations.
   - **Person Name Leak Rate**: 11.4% (16/140) due to statistical NER variance on out-of-vocabulary Indian names.
   - **Character Leak Rate**: **0.0878** (8.78%).
   - **Over-Redaction Rate**: **0.0047** (0.47%).
   - **Fact Survival**: **288/290 (99.3%)** key business facts retained intact.
   - **Metadata Leaks**: **0 (0.0%)**.
   - Failure modes documented in `docs/limitations.md` as "unseen phrasing not covered" in strict compliance with freeze rules.

4. **Regression Guard**:
   - `python -m src.eval.pii_eval --dataset heldout` strictly maintained **143 TP / 62 FP / 13 FN** (Recall 0.9167, Precision 0.6976).

### 8. CI Hardening & Pre-Push Verification
*Hardened test environment isolation, vector store validation, and automated clean clone checks.*

1. **Test Session Store Isolation (`tests/conftest.py`)**:
   - Session-scoped autouse fixture redirects `settings.chroma_persist_dir` to a temporary directory (`tmp_path_factory.mktemp("chroma")`), ingests corpus v1 there, and restores the setting on teardown.
   - Tests run strictly against isolated corpus v1 on every machine, never mutating or relying on real `data/chroma`.
   - Removed heuristic document source guessing; tests state target corpus explicitly (`corpus="v1"`).

2. **Ingestion Store Integrity Checks (`src/eval/ingest_eval.py` & `tests/test_ingest_eval.py`)**:
   - `run_ingest_eval` raises `ValueError` if the vector store contains 0 chunks or fewer chunks than documents.
   - Added unit test asserting empty store raises `ValueError`.
   - Added unit test asserting a temporary store with a planted unredacted PII value strictly triggers the `SECURITY VIOLATION` `AssertionError`.

3. **CI Pipeline Hardening (`.github/workflows/ci.yml`)**:
   - Added `python -m src.eval.ingest_eval --corpus v1` immediately after corpus v1 ingestion.
   - Guarantees the zero-leak security invariant is verified on every push and pull request.

4. **Clean Clone Pre-Push Check (`scripts/clean_clone_check.ps1` & `AGENTS.md`)**:
   - Clones repo to a fresh temporary workspace, creates a virtual environment, installs dependencies matching `ci.yml`, and runs ingestion, evaluation, `ruff`, `mypy`, and `pytest`.
   - Documented mandatory pre-push verification rule in `AGENTS.md`.

### 9. RAG Evaluation Harness & Ablations (Prompt 5, Part 1 Results)
*Built rigorous evaluation harness and benchmark questions programmatically from `data/docs_v2/_ground_truth.json`.*

1. **Benchmark Question Datasets (`scripts/gen_qa.py`)**:
   - `data/eval/qa_test.jsonl`: Exactly 40 questions:
     - 26 answerable key-fact questions, each with a **unique gold document** (26 distinct documents) and exact gold string.
     - 8 unanswerable questions (organisations and domains absent from corpus) with `gold_doc: null` and `gold_value: null`.
     - 6 adversarial PII extraction attempts ("What is the Aadhaar/PAN/DOB in <doc>?"), each with a unique gold document and non-empty `planted_values`.
   - `data/eval/qa_dev.jsonl`: 10 debug questions (6 answerable, 2 unanswerable, 2 PII) on disjoint documents.

2. **Configurable Pipeline Ablations (`src/rag/agent.py`)**:
   - Configurable flags `enable_grading`, `enable_rewrite`, `enable_verification`, `enable_output_guard` with default `True` preserving existing agent behavior.
   - Four benchmark ablations:
     - **Ablation A (Naive RAG)**: Top-k retrieval + direct generation (grading, rewriting, verification, and output_guard disabled).
     - **Ablation B (+ Grading / Rewrite)**: Relevance grading of retrieved chunks + up to 2 query rewrites.
     - **Ablation C (+ Verification)**: Factual claim verification against context + single regeneration if hallucinated.
     - **Ablation D (Full System)**: Full corrective-RAG system + `output_guard` PII sanitization.

3. **Evaluation Harness Metrics (`src/eval/rag_eval.py`)**:
   - **Retrieval Hit Rate**: Gold document in retrieved candidate chunks (programmatic, no LLM).
   - **Answer Correctness**: Programmatic match of gold value in answer (primary metric, no LLM judge).
   - **Citation Correctness**: Verification that cited chunk ID belongs to the gold document.
   - **Refusal Accuracy**: Explicit refusal ("I don't know") on the 8 unanswerable questions.
   - **PII Leak Rate**: Comprehensive scan against planted ground-truth substrings AND Presidio/regex scan via `sanitize(answer, mode=PIPELINE_MODE)`. Reports 0 only after scanning all answers.
   - **Faithfulness (Secondary)**: LLM judge with fixed rubric. 10 manual calibration spot checks documented in `docs/judge_spot_checks.md`.
   - **Wilson 95% Confidence Intervals**: Exact binomial confidence intervals computed for all proportions.

4. **Safety Rails & Infrastructure**:
   - On-disk response caching under `data/cache/` (gitignored) via `CachedLLMAdapter`, preserving type boundary.
   - Cost cap guard via `MAX_EVAL_COST_USD` environment variable or `--max-cost` CLI flag aborting runs on budget overruns.
   - Warmup query executed and discarded prior to collecting p50/p95 latency metrics.
   - `docs/rag_results.md` automatically generated with run metadata, comparative matrix, and per-question error diagnostics.

---

## Verified Evaluation & Test Commands
```bash
# 1. Full Unit Test Suite (131 tests passing)
pytest tests/ -v -m "not slow"

# 2. RAG Evaluation Harness Unit Tests (11 tests passing)
pytest tests/test_rag_eval.py -v

# 3. Pre-Push Clean Clone Check
powershell -ExecutionPolicy Bypass -File scripts/clean_clone_check.ps1

# 4. Held-Out PII Eval Regression Guard (143 TP / 62 FP / 13 FN)
python -m src.eval.pii_eval --dataset heldout

# 5. RAG Evaluation Harness (Fake Provider CI Verification)
python -m src.eval.rag_eval --provider fake --dataset dev --limit 5

# 6. RAG Evaluation Harness (Real Provider Execution)
python -m src.eval.rag_eval --provider anthropic --dataset test --ablation all

# 7. Type and Linting Checks
ruff check src/ tests/ scripts/
mypy src/ tests/ scripts/
```

---

## What is Next
- **Prompt 5, Part 2**: Run live evaluation against real LLM providers (`anthropic` / `ollama`), analyze ablation trade-offs, and measure adversarial prompt injection resistance.
