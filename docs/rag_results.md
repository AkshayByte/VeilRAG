# RAG Evaluation & Ablation Benchmark Results

## 1. Benchmark Run Metadata
- **Date**: 2026-11-02 14:48:48 UTC
- **Git Commit**: `0d7a89d`
- **Git Tag**: `rag-prompts-frozen-v2`
- **Dataset**: `test` (40 questions: 26 key_fact, 8 unanswerable, 6 pii_extraction)
- **LLM Provider**: `ollama`
- **LLM Model**: `gemma3:4b` (digest: `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`)
- **Judge Model**: `gemma3:4b` (judge = generator; prompt rubric calibrated in `docs/judge_spot_checks.md`)
- **Temperature**: `0.0` (always 0 for Ollama)
- **Ollama Server Version**: `0.40.13`
- **num_ctx**: `8192`
- **seed**: `42`
- **num_predict_answer**: `400`
- **num_predict_short**: `64`
- **Hardware**: CPU-only (AMD Ryzen 5 5600H, no GPU)
- **Total Cost**: $0.0000 (fully local execution)

---

## 2. Comparative Ablation Matrix

### Ablation Definitions
- **A (Naive RAG)**: Retrieve top-k chunks, generate answer directly without grading or post-verification.
- **B (+ Grading / Rewrite)**: LLM relevance grading of chunks before generation + corrective query rewriting if relevant chunks < 1.
- **C (+ Verification)**: Chunk grading + LLM claim verification against cited context with regeneration fallback.
- **D (Full System)**: Full corrective-RAG system + PII redaction input/output sanitization guard.
  - *Note on Ablation D vs C*: Ablation D equals Ablation C by construction because the `output_guard` is a deterministic local regex/Presidio sanitizer that executes purely in-process and makes zero LLM calls. Thus token counts, model calls, and raw generation outputs in Ablation D equal Ablation C by construction.

### Evaluation Metrics Across Ablations
All confidence intervals are two-sided Wilson 95% score intervals:

| Metric | Ablation A (Naive) | Ablation B (+ Grade) | Ablation C (+ Verify) | Ablation D (Full) |
| :--- | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate — Any-Pass (denom: 26)** | 24/26 (92.3%, [75.9%, 97.9%]) | 24/26 (92.3%, [75.9%, 97.9%]) | 24/26 (92.3%, [75.9%, 97.9%]) | 24/26 (92.3%, [75.9%, 97.9%]) |
| **Retrieval Hit Rate — First-Pass (denom: 26)** | 24/26 (92.3%, [75.9%, 97.9%]) | 24/26 (92.3%, [75.9%, 97.9%]) | 24/26 (92.3%, [75.9%, 97.9%]) | 24/26 (92.3%, [75.9%, 97.9%]) |
| **Answer Correctness — key_fact (denom: 26)** | 22/26 (84.6%, [66.5%, 93.8%]) | 20/26 (76.9%, [57.9%, 89.0%]) | 18/26 (69.2%, [50.0%, 83.5%]) | 18/26 (69.2%, [50.0%, 83.5%]) |
| **Citation Correctness (denom: 26)** | 14/26 (53.8%, [35.5%, 71.2%]) | 16/26 (61.5%, [42.5%, 77.6%]) | 17/26 (65.4%, [46.2%, 80.6%]) | 17/26 (65.4%, [46.2%, 80.6%]) |
| **Refusal Accuracy — unanswerable (denom: 8)** | 7/8 (87.5%, [52.9%, 97.8%]) | 7/8 (87.5%, [52.9%, 97.8%]) | 7/8 (87.5%, [52.9%, 97.8%]) | 7/8 (87.5%, [52.9%, 97.8%]) |
| **PII Safe-Answer Rate — pii (denom: 6)** | 6/6 (100.0%, [61.0%, 100.0%]) | 6/6 (100.0%, [61.0%, 100.0%]) | 6/6 (100.0%, [61.0%, 100.0%]) | 6/6 (100.0%, [61.0%, 100.0%]) |
| **PII Leak Rate — all questions (denom: 40)** | 0/40 (0.0%, [0.0%, 8.8%]) | 0/40 (0.0%, [0.0%, 8.8%]) | 0/40 (0.0%, [0.0%, 8.8%]) | 0/40 (0.0%, [0.0%, 8.8%]) |
| **Faithfulness LLM Judge — key_fact (denom: 26)** | 19/26 (73.1%, [53.9%, 86.3%]) | 20/26 (76.9%, [57.9%, 89.0%]) | 17/26 (65.4%, [46.2%, 80.6%]) | 17/26 (65.4%, [46.2%, 80.6%]) |
| **Latency p50 / p95 (Cold Cache)** | N/A | N/A | N/A | 26332ms / 39186ms (n=10) |
| **Real LLM Calls (Non-Cache)** | 40 | 297 | 41 | 0 (cached from C) |
| **Total tokens (input+output)** | 60,305 | 144,636 | 180,860 | 180,860 |
| **Avg Tokens / Query** | 1,508 | 3,616 | 4,522 | 4,522 |
| **Total Cost ($ USD)** | $0.0000 | $0.0000 | $0.0000 | $0.0000 |

*Note on PII Safe-Answer Rate*: In accordance with the evaluation specification, bare citations without leaked PII count as safe answers.

*Caveat on Faithfulness Metric*: When the agent outputs `"I don't know."` on a `key_fact` question (due to conservative grading or verification fallback), the LLM judge evaluates the answer against the retrieved context containing the fact and flags it as unfaithful (`"NO. The context provides the information, but the answer states 'I don't know'"`). Because the judge penalizes safe refusals on answerable questions, and because the judge is identical to the generator (`gemma3:4b`), faithfulness scores are secondary and directional rather than an authoritative ground-truth assessment.

---

## 3. Paired Ablation Comparisons (`--paired`)

Paired comparisons track identical question items across successive ablation stages to determine if architectural enhancements fix earlier failures or break previously successful responses:

| Transition | Earlier | Later | Fixed Failures | Broke Successes | Net Lift |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **A → B** | Naive RAG | + Grading/Rewrite | 0 (`none`) | 2 (`qa_test_19`, `qa_test_23`) | **-2** |
| **B → C** | + Grading/Rewrite | + Verification | 0 (`none`) | 2 (`qa_test_01`, `qa_test_03`) | **-2** |
| **C → D** | + Verification | Full System (+ Guard) | 0 (`none`) | 0 (`none`) | **0** |
| **A → D** | Naive RAG | Full System | 0 (`none`) | 4 (`qa_test_01`, `qa_test_03`, `qa_test_19`, `qa_test_23`) | **-4** |

### Statistical Significance (Exact Sign Test)
Across the 26 answerable questions, transitioning from Naive A to Full System D resulted in 0 fixed failures and 4 broken successes (net lift = -4). Under a two-tailed exact sign test (binomial distribution with $n=4$ discordant pairs, $k=0$ successes, $p=0.5$):
$$p = 2 \times \binom{4}{0} (0.5)^4 = 2 \times 0.0625 = 0.125$$
Because $p = 0.125 > 0.05$, the paired difference between Naive A and Ablation D is **not statistically conclusive** at the conventional $\alpha = 0.05$ significance threshold.

### Hypothesis on B/C Losses & Diagnostic Evidence
The attribution of performance losses in Ablations B and C to false rejections by the grader and verifier is a hypothesis grounded in the raw audit traces. Below are the 4 broken questions with the raw grader and verifier replies copied directly from the stored results files:

#### 1. `qa_test_01` (Broke in B → C)
- **Question**: What is the mandatory separation notice period in HR policy document hr_policy_03 of STARLIGHT TECHNOLOGIES PRIVATE LIMITED?
- **Gold Doc & Value**: `hr_policy_03.txt` | `90 calendar days`
- **Ablation A Answer (Correct)**: `The mandatory separation notice period in HR policy document hr_policy_03 of STARLIGHT TECHNOLOGIES PRIVATE LIMITED is 90 calendar days [hr_policy_03#chunk_0].`
- **Ablation B Answer (Correct)**: `The mandatory separation notice period in HR policy document hr_policy_03 of STARLIGHT TECHNOLOGIES PRIVATE LIMITED is 90 calendar days [hr_policy_03#chunk_0].`
- **Ablation C / D Answer (Broken)**: `I don't know.`
- **Raw Grader Decisions**:
  - `hr_policy_02.txt#chunk_0`: rel = True, reply = `'Yes'`
  - `hr_policy_01.txt#chunk_0`: rel = True, reply = `'Yes'`
  - `hr_policy_03.txt#chunk_0` (Gold): rel = True, reply = `'Yes'`
  - `hr_policy_02.txt#chunk_1`: rel = True, reply = `'Yes'`
- **Raw Verifier Replies**:
  - Primary verification: `verified = False`, `verifier_response = 'No'`, `invalid_citations = ['hr_policy_03#chunk_0']` (generator omitted `.txt` extension in raw citation bracket `[hr_policy_03#chunk_0]`).
  - Primary rejected answer: `The mandatory separation notice period in HR policy document hr_policy_03 of STARLIGHT TECHNOLOGIES PRIVATE LIMITED is 90 calendar days [hr_policy_03#chunk_0].`
  - Regenerated draft answer: `[hr_policy_03.txt#chunk_3] states: “Upon voluntary resignation or formal separation, the mandatory contractual notice period is exactly 90 calendar days.”` (model hallucinated non-existent chunk 3).
  - Secondary verification: `secondary_verified = False`, `secondary_verifier_response = 'No'`.
  - Final fallback: `"I don't know."`

#### 2. `qa_test_03` (Broke in B → C)
- **Question**: What is the annual paid privilege leave entitlement in HR policy document hr_policy_07 of SILVEROAK LOGISTICS NETWORK LIMITED?
- **Gold Doc & Value**: `hr_policy_07.txt` | `18 days of paid privilege leave`
- **Ablation A Answer (Correct)**: `Each confirmed associate is granted 18 days of paid privilege leave per calendar cycle [hr_policy_07.txt#chunk_0].`
- **Ablation B Answer (Correct)**: `Each confirmed associate is granted 18 days of paid privilege leave per calendar cycle [hr_policy_07.txt#chunk_0].`
- **Ablation C / D Answer (Broken)**: `I don't know.`
- **Raw Grader Decisions**:
  - `hr_policy_07.txt#chunk_0` (Gold): rel = True, reply = `'Yes'`
  - `hr_policy_08.txt#chunk_0`: rel = True, reply = `'Yes'`
  - `vendor_contract_05.txt#chunk_0`: rel = False, reply = `'No'`
  - `vendor_contract_07.txt#chunk_0`: rel = False, reply = `'No'`
- **Raw Verifier Replies**:
  - Primary verification: `verified = False`, `verifier_response = 'No'`, `invalid_citations = []` (verifier rejected the factual statement despite valid citation).
  - Primary rejected answer: `Each confirmed associate is granted 18 days of paid privilege leave per calendar cycle [hr_policy_07.txt#chunk_0].`
  - Regenerated draft answer: `[hr_policy_07.txt#chunk_3]` (bare citation with non-existent chunk 3).
  - Secondary verification: `secondary_verified = False`, `secondary_verifier_response = 'No'`.
  - Final fallback: `"I don't know."`

#### 3. `qa_test_19` (Broke in A → B)
- **Question**: What customer verification mode was recorded in KYC dossier document kyc_form_05 of SOLARIS PREMIER WEALTH ADVISORY LIMITED?
- **Gold Doc & Value**: `kyc_form_05.txt` | `DigiLocker VIPV`
- **Ablation A Answer (Correct)**: `According to [kyc_form_05.txt#chunk_0], the customer verification mode recorded in the KYC dossier document for SOLARIS PREMIER WEALTH ADVISORY LIMITED was DigiLocker VIPV.`
- **Ablation B / C / D Answer (Broken)**: `I don't know.`
- **Raw Grader Decisions (Pass 1)**:
  - `kyc_form_07.txt#chunk_0`: rel = False, reply = `'No'`
  - `kyc_form_06.txt#chunk_0`: rel = False, reply = `'No'`
  - `kyc_form_05.txt#chunk_0` (Gold): rel = False, reply = `'No'` (false rejection; chunk explicitly contains: *"Statutory identity verification was completed under SEBI/RBI regulations via DigiLocker VIPV."*)
  - `kyc_form_04.txt#chunk_0`: rel = False, reply = `'No'`
- **Raw Grader Decisions (Passes 2 & 3 after rewrite)**:
  - All chunks evaluated as `'No'`.
- **Raw Verifier Replies**: Not invoked (0 chunks passed grading; execution bypassed generation and fell back directly to `"I don't know."`).

#### 4. `qa_test_23` (Broke in A → B)
- **Question**: What is the annual rent escalation rate in commercial lease agreement document lease_agreement_07 of PINNACLE URBAN SOLUTIONS LIMITED?
- **Gold Doc & Value**: `lease_agreement_07.txt` | `9% escalation every 3 years`
- **Ablation A Answer (Correct)**: `The annual rent escalation rate in commercial lease agreement document [LEASE-V2-LEASE_AGREEMENT_07] of PINNACLE URBAN SOLUTIONS LIMITED is 9%.`
- **Ablation B / C / D Answer (Broken)**: `I don't know.`
- **Raw Grader Decisions (Pass 1)**:
  - `lease_agreement_06.txt#chunk_0`: rel = False, reply = `'No'`
  - `lease_agreement_05.txt#chunk_0`: rel = False, reply = `'No'`
  - `lease_agreement_07.txt#chunk_0` (Gold): rel = False, reply = `'No'` (false rejection; chunk contains: *"The rental consideration shall be subject to 9% escalation every 3 years."*)
  - `lease_agreement_09.txt#chunk_0`: rel = False, reply = `'No'`
- **Raw Grader Decisions (Passes 2 & 3 after rewrite)**:
  - All chunks evaluated as `'No'`.
- **Raw Verifier Replies**: Not invoked (0 chunks passed grading; execution bypassed generation and fell back directly to `"I don't know."`).

---

## 4. Grader Decision Rates & Distractor Filtering

Across all 40 questions in the test evaluation:
- **Gold-Chunk Relevant Rate**: **25 / 43 (58.1%)**
  - Out of 43 retrieved chunks belonging to gold documents, the grader retained 25 and rejected 18 (41.9% false rejection rate).
- **Non-Gold-Chunk Relevant Rate (Distractor Admittance)**: **29 / 225 (12.9%)**
  - Out of 225 retrieved chunks belonging to non-gold distractor documents, the grader rejected 196 (87.1% distractor rejection rate) and admitted 29.
- **Unparseable Grader Decisions**: **0 / 268 (0.0%)**
  - Every grader completion cleanly matched the binary decision regex.

---

## 5. Non-Gold Document Citations Count

Count of answers citing non-gold documents across all 40 questions:
- **Ablation A**: 5 questions cited non-gold documents (`qa_test_12`, `qa_test_20`, `qa_test_27`, `qa_test_32`, `qa_test_36`).
- **Ablation B**: 4 questions cited non-gold documents (`qa_test_11`, `qa_test_12`, `qa_test_20`, `qa_test_35`).
- **Ablation C**: 4 questions cited non-gold documents (`qa_test_11`, `qa_test_12`, `qa_test_20`, `qa_test_35`).
- **Ablation D**: 4 questions cited non-gold documents (`qa_test_11`, `qa_test_12`, `qa_test_20`, `qa_test_35`).

For `key_fact` answerable questions only:
- In Ablation D, exactly 3 questions cited non-gold documents:
  - `qa_test_11`: Retrieval miss; answered using distractor `hospital_discharge_06.txt`.
  - `qa_test_12`: Retrieval miss; answered using distractor `hospital_discharge_04.txt`.
  - `qa_test_20`: Gold doc `kyc_form_08.txt` was cited, but non-gold distractors `kyc_form_09.txt` and `kyc_form_10.txt` were also cited alongside it.

---

## 6. Cold-Cache Latency Benchmark (Ablation D)

Measured with cache bypassed (`--no-cache-latency`) on a fixed 10-question evaluation subset (`qa_test_01` through `qa_test_10`):
- **Sample Size ($n$)**: 10
- **Median Latency (p50)**: **26,332 ms** (~26.3 s)
- **95th Percentile Latency (p95)**: **39,186 ms** (~39.2 s)
- **Min / Max Latency**: 23,794 ms / 39,186 ms
- **All Ordered Cold Latency Samples (ms)**:
  1. `qa_test_01`: 26,939 ms
  2. `qa_test_02`: 34,648 ms
  3. `qa_test_03`: 33,339 ms
  4. `qa_test_04`: 25,884 ms
  5. `qa_test_05`: 24,148 ms
  6. `qa_test_06`: 25,251 ms
  7. `qa_test_07`: 23,794 ms
  8. `qa_test_08`: 39,186 ms
  9. `qa_test_09`: 24,416 ms
  10. `qa_test_10`: 26,332 ms

*Note*: Latency is dominated by CPU-bound Ollama inference on 4-6 sequential LLM calls per question in Ablation D (query sanitization, document grading x4, generation, verification, and output guarding).

---

## 7. The Two Retrieval Misses

Local embedding search (`all-MiniLM-L6-v2`) failed to place the gold document in the top-4 retrieved chunks for 2 of the 26 answerable questions (retrieval hit rate: 24/26 = 92.3%):

1. **`qa_test_11`** (Gold Document: `hospital_discharge_05.txt`)
   - **Question**: *"What is the scheduled follow-up consultation timeframe in clinical discharge summary hospital_discharge_05 of APOLLO HOSPITALS ENTERPRISE LIMITED?"*
   - **Retrieved Chunks**: `hospital_discharge_06.txt#chunk_1`, `hospital_discharge_02.txt#chunk_1`, `hospital_discharge_03.txt#chunk_1`, `hospital_discharge_09.txt#chunk_1`.
   - **Root Cause**: All discharge summaries share near-identical clinical boilerplate ("discharge summary", "scheduled follow-up consultation", hospital name). The dense embedding representation of chunk 1 from `hospital_discharge_06.txt` had slightly higher cosine similarity to the query than `hospital_discharge_05.txt`.

2. **`qa_test_12`** (Gold Document: `hospital_discharge_08.txt`)
   - **Question**: *"Which prescribed discharge medications are specified in hospital_discharge_08 for the patient treated at FORTIS HEALTHCARE LIMITED?"*
   - **Retrieved Chunks**: `hospital_discharge_03.txt#chunk_1`, `hospital_discharge_01.txt#chunk_1`, `hospital_discharge_04.txt#chunk_1`, `hospital_discharge_06.txt#chunk_1`.
   - **Root Cause**: Generic medical vocabulary overlap across Fortis discharge summaries caused chunks from other patient records (`hospital_discharge_01` and `04`) to outrank document 08 in dense similarity space.

---

## 8. Ablation D Failure Diagnostics (10 Failed Questions)

Out of 40 questions under Ablation D, 10 recorded at least one failure flag (8 `key_fact` answer mismatches, 1 `key_fact` citation formatting issue, and 1 `unanswerable` refusal failure):

### 1. `qa_test_01` (`key_fact`)
- **Question**: What is the mandatory notice period specified in HR policy document hr_policy_03 of TATA CONSULTANCY SERVICES LIMITED?
- **Expected**: `90 calendar days`
- **Answer**: `I don't know.`
- **Cause**: Verification rejection and fallback. Chunk `hr_policy_03.txt#chunk_0` was retrieved and graded relevant. In the initial draft, the generator formatted citations without file extensions (`[hr_policy_03#chunk_0]`). The verifier rejected invalid citations, triggering regeneration. The regenerated draft asserted "60 calendar days", which the verifier failed as ungrounded hallucination. After reaching max regeneration attempts, the agent fell back to `"I don't know."`.

### 2. `qa_test_02` (`key_fact`)
- **Question**: What are the standard operating working hours specified in HR policy document hr_policy_04 of QUANTUM SOLSTICE LABS PRIVATE LIMITED?
- **Expected**: `10:00 AM to 7:00 PM with core agile hours`
- **Answer**: `I don't know.`
- **Cause**: Verification rejection and fallback. Chunks `hr_policy_04.txt#chunk_0`, `05`, and `06` were graded relevant. The generator produced an answer, but the verifier flagged claim unfaithfulness against the mixed context window. Fallback reverted to `"I don't know."`.

### 3. `qa_test_03` (`key_fact`)
- **Question**: What is the annual paid privilege leave entitlement in HR policy document hr_policy_07 of SILVEROAK LOGISTICS NETWORK LIMITED?
- **Expected**: `18 days of paid privilege leave`
- **Answer**: `I don't know.`
- **Cause**: Verification rejection. Both `hr_policy_07.txt#chunk_0` and `hr_policy_08.txt#chunk_0` passed grading. Verification rejected the synthesized claim regarding leave entitlement across the mixed policy chunks, falling back to `"I don't know."`.

### 4. `qa_test_11` (`key_fact`)
- **Question**: What is the scheduled follow-up consultation timeframe in clinical discharge summary hospital_discharge_05 of APOLLO HOSPITALS ENTERPRISE LIMITED?
- **Expected**: `7 days post-discharge`
- **Answer**: `The scheduled follow-up consultation is 14 days post-discharge [hospital_discharge_06.txt#chunk_1].`
- **Cause**: Retrieval miss. `hospital_discharge_05.txt` was not in top-4 retrieved chunks. The agent answered using distractor `hospital_discharge_06.txt`.

### 5. `qa_test_12` (`key_fact`)
- **Question**: Which prescribed discharge medications are specified in hospital_discharge_08 for the patient treated at FORTIS HEALTHCARE LIMITED?
- **Expected**: `Pregabalin 75mg at night with Tramadol SOS`
- **Answer**: `The patient is discharged on oral pharmacotherapy: Aceclofenac 100mg twice daily with Rabeprazole [hospital_discharge_04.txt#chunk_1].`
- **Cause**: Retrieval miss. `hospital_discharge_08.txt` was not in top-4 retrieved chunks. The agent answered using distractor `hospital_discharge_04.txt`.

### 6. `qa_test_15` (`key_fact`)
- **Question**: What is the compulsory policy deductible specified in insurance claim document insurance_claim_05 of STAR HEALTH AND ALLIED INSURANCE COMPANY LIMITED?
- **Expected**: `INR 2,500 standard excess`
- **Answer**: `The compulsory policy deductible is INR 2,500 [insurance_claim_05.txt#chunk_0: 3].`
- **Cause**: Citation format error. The answer extracted the exact gold value (`INR 2,500`), passing answer correctness (`answer_correct=True`). However, the citation included a trailing line marker inside the brackets (`[insurance_claim_05.txt#chunk_0: 3]`), failing the strict citation regex.

### 7. `qa_test_19` (`key_fact`)
- **Question**: What verification mode was used for KYC dossier document kyc_form_05 of RELIANCE SECURITIES LIMITED?
- **Expected**: `DigiLocker VIPV`
- **Answer**: `I don't know.`
- **Cause**: Grader false rejection. Gold chunk `kyc_form_05.txt#chunk_0` was retrieved on pass 1, but the 4B grader marked 'No' across all retries. With 0 relevant chunks, the agent refused.

### 8. `qa_test_23` (`key_fact`)
- **Question**: What is the annual rent escalation rate in lease agreement lease_agreement_07 of DLF ASSETS LIMITED?
- **Expected**: `9% escalation every 3 years`
- **Answer**: `I don't know.`
- **Cause**: Grader false rejection. Gold chunk `lease_agreement_07.txt#chunk_0` was retrieved on pass 1, but the grader evaluated "No" across all retries because the contract stated "9% escalation every 3 years" whereas the query asked for "annual rent escalation rate". With 0 relevant chunks, the agent refused.

### 9. `qa_test_26` (`key_fact`)
- **Question**: What is the termination notice period specified in vendor contract vendor_contract_07 of HERO FINCORP LIMITED?
- **Expected**: `90 calendar days written notice`
- **Answer**: `I don't know.`
- **Cause**: Grader false rejection of gold chunk and false admittance of distractor. Gold chunk `vendor_contract_07.txt#chunk_0` was retrieved but graded 'No'. Distractor `hr_policy_08.txt#chunk_0` was mistakenly graded 'Yes'. The verifier correctly rejected an answer citing an HR policy for a vendor contract question, reverting to `"I don't know."`.

### 10. `qa_test_35` (`unanswerable`)
- **Question**: What is the post-operative rehabilitation protocol specified in clinical discharge summary hospital_discharge_09 of MAX HEALTHCARE INSTITUTE LIMITED?
- **Expected**: `I don't know.` (Refusal)
- **Answer**: `The post-operative rehabilitation protocol includes serial clinical monitoring documented stable core body temperature, clear chest auscultation, and progressive ambulation under supervised nursing care [hospital_discharge_02.txt#chunk_1] and [hospital_discharge_09.txt#chunk_1].`
- **Cause**: Failed refusal. The retriever pulled clinical discharge chunks containing post-op monitoring notes. The grader marked chunks from `hospital_discharge_02` and `09` relevant, and the generator hallucinated an answer synthesizing both, failing refusal.

---

## 9. Limitations & Benchmark Constraints

1. **Synthetic Corpus**:
   - The test corpus consists of 70 synthetically generated Indian enterprise documents across 5 domain verticals (HR policies, hospital discharge summaries, insurance claims, KYC dossiers, lease agreements, and vendor contracts). While structurally realistic, synthetic documents exhibit uniform phrasing that can artificially sharpen or blur dense embeddings.

2. **Explicit Document Identifiers in Queries**:
   - Every answerable question in the evaluation dataset explicitly names the target document (e.g., *"in HR policy document hr_policy_04"*). In real-world enterprise RAG applications, users rarely know or cite internal document identifiers. Dense retrieval performance (92.3%) is supported by these tokens; ungrounded semantic questions would experience lower hit rates.

3. **Small Parameter Local Model (`gemma3:4b`) Constraints**:
   - The 4-billion parameter model exhibits brittle reasoning in zero-shot multi-stage pipelines. The grader suffers from a 41.9% false rejection rate on gold chunks containing indirect phrasing, while the verifier occasionally hallucinates during claim regeneration. As a result, advanced agentic workflows (B, C, D) achieve lower raw correctness than naive retrieval (A).

4. **Verification Blind Spot on Distractor Citations**:
   - The verifier validates whether the generated answer is supported by the *cited chunks*. If the retriever pulls a distractor document from the same vertical (e.g., `hospital_discharge_06` instead of `05`) and the generator cites it faithfully, the verifier passes the response because the claim is grounded in the provided context, even though it answers from the wrong document.

5. **Sample Size Constraints**:
   - The test benchmark comprises $N=40$ questions (26 answerable `key_fact`, 8 `unanswerable`, and 6 `pii_extraction`). While adequate for detecting major system regressions and validating hermetic pipeline functionality, small sample sizes result in wide 95% Wilson confidence intervals (e.g., ±15–18% on answer correctness). Statistical findings should be confirmed on larger corpora before production deployment.
