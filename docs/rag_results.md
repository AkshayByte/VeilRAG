# RAG Evaluation & Ablation Benchmark Results

## 1. Benchmark Run Metadata
- **Date**: 2026-11-01 18:04:46 UTC
- **Git Commit**: `e85c5c4`
- **Dataset**: `dev`
- **LLM Provider**: `fake`
- **LLM Model**: `fake-model`
- **Temperature**: `0.0`
- **Judge Model**: `fake-model` (Rubric calibrated in `docs/judge_spot_checks.md`)

> [!WARNING]
> **TEST / CI STUB NOTICE**: This run was executed with `LLM_PROVIDER=fake`. Fake provider returns deterministic test fixtures for pipeline verification; these quality metrics are synthetic placeholders and must NOT be interpreted as real LLM model evaluation numbers.

## 2. Comparative Ablation Matrix

Ablation Definitions:
- **A (Naive RAG)**: Retrieve top-k chunks, generate answer directly without grading or verification.
- **B (+ Grading / Rewrite)**: LLM relevance grading of retrieved chunks + up to 2 query rewrites.
- **C (+ Verification)**: Factual claim verification against context + single regeneration if hallucinated.
- **D (Full System)**: Full corrective-RAG system + `output_guard` PII sanitization of final answer.

| Metric | Ablation A (Naive) | Ablation B (+ Grade/Rewrite) | Ablation C (+ Verification) | Ablation D (Full System) |
| :--- | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate** | 2/2 (100.0%, 95% CI [34.2%, 100.0%]) | 2/2 (100.0%, 95% CI [34.2%, 100.0%]) | 2/2 (100.0%, 95% CI [34.2%, 100.0%]) | 2/2 (100.0%, 95% CI [34.2%, 100.0%]) |
| **Answer Correctness (Exact)** | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) |
| **Citation Correctness** | 1/2 (50.0%, 95% CI [9.5%, 90.5%]) | 1/2 (50.0%, 95% CI [9.5%, 90.5%]) | 1/2 (50.0%, 95% CI [9.5%, 90.5%]) | 1/2 (50.0%, 95% CI [9.5%, 90.5%]) |
| **Refusal Accuracy (Unanswerable)** | N/A | N/A | N/A | N/A |
| **PII Leak Rate (Lower is better)** | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) |
| **Faithfulness (LLM Judge)** | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) | 0/2 (0.0%, 95% CI [0.0%, 65.8%]) |
| **Latency p50 / p95 (Warm)** | 203ms / 203ms | 125ms / 125ms | 159ms / 159ms | 135ms / 135ms |
| **Avg Tokens / Query** | 1268 | 2636 | 3848 | 3848 |
| **Total Cost ($ USD)** | $0.0000 | $0.0000 | $0.0000 | $0.0000 |

---

## 3. Per-Question Failure & Error Diagnostic List

### Ablation A (Naive RAG) Failures (2/2)

- **[qa_dev_01] (key_fact)**: What is the mandatory separation notice period in HR policy document hr_policy_01 of STARLIGHT TECHNOLOGIES PRIVATE LIMITED?
  - **Expected**: `30 calendar days`
  - **Answer**: `According to [hr_policy_01.txt#chunk_0], the verified details are documented.`
  - *Failure*: Answer mismatch: expected '30 calendar days' in answer
  - *Failure*: Judge flagged unfaithful: I don't know.
- **[qa_dev_02] (key_fact)**: What is the applied interest rate in loan agreement document loan_agreement_01 of TERRATRUST CAPITAL FINANCE LIMITED?
  - **Expected**: `8.75% per annum floating`
  - **Answer**: `According to [loan_agreement_02.txt#chunk_0], the verified details are documented.`
  - *Failure*: Answer mismatch: expected '8.75% per annum floating' in answer
  - *Failure*: Citation missing or invalid for gold doc
  - *Failure*: Judge flagged unfaithful: I don't know.

### Ablation B (+ Grading / Rewrite) Failures (2/2)

- **[qa_dev_01] (key_fact)**: What is the mandatory separation notice period in HR policy document hr_policy_01 of STARLIGHT TECHNOLOGIES PRIVATE LIMITED?
  - **Expected**: `30 calendar days`
  - **Answer**: `According to [hr_policy_01.txt#chunk_0], the verified details are documented.`
  - *Failure*: Answer mismatch: expected '30 calendar days' in answer
  - *Failure*: Judge flagged unfaithful: I don't know.
- **[qa_dev_02] (key_fact)**: What is the applied interest rate in loan agreement document loan_agreement_01 of TERRATRUST CAPITAL FINANCE LIMITED?
  - **Expected**: `8.75% per annum floating`
  - **Answer**: `According to [loan_agreement_02.txt#chunk_0], the verified details are documented.`
  - *Failure*: Answer mismatch: expected '8.75% per annum floating' in answer
  - *Failure*: Citation missing or invalid for gold doc
  - *Failure*: Judge flagged unfaithful: I don't know.

### Ablation C (+ Verification) Failures (2/2)

- **[qa_dev_01] (key_fact)**: What is the mandatory separation notice period in HR policy document hr_policy_01 of STARLIGHT TECHNOLOGIES PRIVATE LIMITED?
  - **Expected**: `30 calendar days`
  - **Answer**: `According to [hr_policy_01.txt#chunk_0], the verified details are documented.`
  - *Failure*: Answer mismatch: expected '30 calendar days' in answer
  - *Failure*: Judge flagged unfaithful: I don't know.
- **[qa_dev_02] (key_fact)**: What is the applied interest rate in loan agreement document loan_agreement_01 of TERRATRUST CAPITAL FINANCE LIMITED?
  - **Expected**: `8.75% per annum floating`
  - **Answer**: `According to [loan_agreement_02.txt#chunk_0], the verified details are documented.`
  - *Failure*: Answer mismatch: expected '8.75% per annum floating' in answer
  - *Failure*: Citation missing or invalid for gold doc
  - *Failure*: Judge flagged unfaithful: I don't know.

### Ablation D (Full System) Failures (2/2)

- **[qa_dev_01] (key_fact)**: What is the mandatory separation notice period in HR policy document hr_policy_01 of STARLIGHT TECHNOLOGIES PRIVATE LIMITED?
  - **Expected**: `30 calendar days`
  - **Answer**: `According to [hr_policy_01.txt#chunk_0], the verified details are documented.`
  - *Failure*: Answer mismatch: expected '30 calendar days' in answer
  - *Failure*: Judge flagged unfaithful: I don't know.
- **[qa_dev_02] (key_fact)**: What is the applied interest rate in loan agreement document loan_agreement_01 of TERRATRUST CAPITAL FINANCE LIMITED?
  - **Expected**: `8.75% per annum floating`
  - **Answer**: `According to [loan_agreement_02.txt#chunk_0], the verified details are documented.`
  - *Failure*: Answer mismatch: expected '8.75% per annum floating' in answer
  - *Failure*: Citation missing or invalid for gold doc
  - *Failure*: Judge flagged unfaithful: I don't know.

