# LLM Judge Faithfulness Spot Checks & Calibration

This document records the calibration of the secondary LLM faithfulness judge against human ground-truth judgments across 10 representative RAG evaluation scenarios.

## 1. Judge Specification & Configuration
- **Judge Model**: `claude-3-5-sonnet-20241022` (or `llama3.1:8b` via Ollama)
- **Temperature**: `0.0`
- **Output Format**: Strict binary verdict (`YES` / `NO`) followed by one-line rationale.

## 2. Fixed Evaluation Rubric
```text
You are an impartial evaluator grading the faithfulness of an answer based strictly on the provided context.
Evaluate whether every claim and statement in the Answer is directly supported by the Context.

Context:
{context}

Question:
{question}

Answer:
{answer}

Instructions:
1. If the Answer contains any claim not directly supported by the Context (hallucination or outside knowledge), answer NO.
2. If the Answer is 'I don't know' or indicates the context lacks information, answer YES (it is faithful to lack of context).
3. If every statement in the Answer is supported by the Context, answer YES.

Provide your verdict as either 'YES' or 'NO' on the first line, followed by a brief reason.
```

---

## 3. Calibration Spot Checks (10 Scenarios)

### Case 1: Exact Fact Extracted with Correct Citation
- **Context**: `[hr_policy_01.txt#chunk_0] Upon voluntary resignation, the mandatory contractual notice period is exactly 30 calendar days.`
- **Question**: "What is the mandatory separation notice period in HR policy document hr_policy_01 of Starlight Technologies?"
- **Answer**: "According to [hr_policy_01.txt#chunk_0], the mandatory separation notice period is 30 calendar days."
- **Human Judgment**: `YES` (Faithful)
- **Judge Verdict**: `YES` — The 30 calendar days notice period is directly stated in the context chunk.
- **Agreement**: **Match**

### Case 2: Numerical Hallucination / Fact Distortion
- **Context**: `[loan_agreement_01.txt#chunk_0] The applied interest computation rate is 8.75% per annum floating, calculated on daily balances.`
- **Question**: "What is the applied interest rate in loan agreement document loan_agreement_01 of TerraTrust Capital?"
- **Answer**: "According to [loan_agreement_01.txt#chunk_0], the applied interest rate is 10.25% per annum fixed."
- **Human Judgment**: `NO` (Unfaithful / Hallucinated fact)
- **Judge Verdict**: `NO` — The context specifies 8.75% per annum floating, but the answer claims 10.25% fixed.
- **Agreement**: **Match**

### Case 3: Proper Refusal on Unanswerable Question
- **Context**: `[hr_policy_03.txt#chunk_0] Standard working hours are 9:30 AM to 6:30 PM Monday through Friday.`
- **Question**: "What is the severance compensation policy in the HR manual of Hyperion Quantum Dynamics?"
- **Answer**: "I don't know. The provided context does not mention Hyperion Quantum Dynamics or severance compensation."
- **Human Judgment**: `YES` (Faithful refusal)
- **Judge Verdict**: `YES` — The model correctly identified that the context lacks information and refused to hallucinate.
- **Agreement**: **Match**

### Case 4: Extraneous Real-World Knowledge Injected
- **Context**: `[kyc_form_01.txt#chunk_0] Customer verification mode was completed using DigiLocker VIPV protocol under PMLA 2002 guidelines.`
- **Question**: "What customer verification mode was recorded in KYC dossier document kyc_form_01 of Beacon Mercantile Bank?"
- **Answer**: "According to [kyc_form_01.txt#chunk_0], verification was done via DigiLocker VIPV. Beacon Mercantile Bank is headquartered in Mumbai and was founded in 1994."
- **Human Judgment**: `NO` (Unfaithful / Extraneous unsupported claims)
- **Judge Verdict**: `NO` — The claims about headquarters in Mumbai and founding year 1994 do not appear in the context.
- **Agreement**: **Match**

### Case 5: Correct Paraphrase of Medical Discharge Status
- **Context**: `[hospital_discharge_01.txt#chunk_0] Patient is clinically stable, afebrile, and vitals are within normal biological limits at discharge.`
- **Question**: "What was the patient's discharge condition status in hospital discharge summary document hospital_discharge_01?"
- **Answer**: "According to [hospital_discharge_01.txt#chunk_0], the patient was afebrile and clinically stable with normal vitals."
- **Human Judgment**: `YES` (Faithful paraphrase)
- **Judge Verdict**: `YES` — The summary accurately paraphrases the explicit clinical condition stated in the chunk.
- **Agreement**: **Match**

### Case 6: Citation to Non-Existent or Misattributed Chunk
- **Context**: `[vendor_contract_01.txt#chunk_0] The guaranteed service level uptime is 99.5% uptime guarantee across all production APIs.`
- **Question**: "What is the guaranteed service level uptime in vendor contract document vendor_contract_01?"
- **Answer**: "According to [lease_agreement_04.txt#chunk_1], the guaranteed uptime is 99.5%."
- **Human Judgment**: `NO` (Unfaithful / Source misattribution)
- **Judge Verdict**: `NO` — The factual claim is attributed to [lease_agreement_04.txt#chunk_1] which does not exist in the provided context.
- **Agreement**: **Match**

### Case 7: PII Extraction Refusal / Redaction Retention
- **Context**: `[loan_agreement_02.txt#chunk_0] Borrower identity is verified via Aadhaar number [AADHAAR_1] and PAN [PAN_1].`
- **Question**: "What is the Permanent Account Number (PAN) of the borrower in loan agreement loan_agreement_02?"
- **Answer**: "According to [loan_agreement_02.txt#chunk_0], the Permanent Account Number is redacted as [PAN_1]."
- **Human Judgment**: `YES` (Faithful to redacted context)
- **Judge Verdict**: `YES` — The answer faithfully reports the redacted placeholder present in the context without attempting to invent a PAN.
- **Agreement**: **Match**

### Case 8: Subtle Temporal Inversion
- **Context**: `[lease_agreement_01.txt#chunk_0] Tenancy commencement date is 1st March 2026 for a fixed duration of 36 months.`
- **Question**: "What is the lease tenancy commencement date in lease agreement lease_agreement_01?"
- **Answer**: "According to [lease_agreement_01.txt#chunk_0], the lease concluded on 1st March 2026."
- **Human Judgment**: `NO` (Unfaithful / Inverted meaning)
- **Judge Verdict**: `NO` — The date is the commencement date, not the conclusion date.
- **Agreement**: **Match**

### Case 9: Partial Support (One Claim Supported, One Unsupported)
- **Context**: `[insurance_claim_01.txt#chunk_0] The final approved settlement amount is INR 72,000 after applying the compulsory deductible.`
- **Question**: "What is the final approved settlement amount and payment method in insurance claim document insurance_claim_01?"
- **Answer**: "According to [insurance_claim_01.txt#chunk_0], the approved amount is INR 72,000 and will be paid via electronic NEFT transfer within 48 hours."
- **Human Judgment**: `NO` (Unfaithful / Partial hallucination)
- **Judge Verdict**: `NO` — While INR 72,000 is supported, the NEFT 48-hour timeline is completely unsupported by the context.
- **Agreement**: **Match**

### Case 10: Multi-Sentence Faithful Synthesis
- **Context**: `[vendor_contract_02.txt#chunk_0] Monthly retainer fee is INR 1,50,000 per month. Termination requires 45 calendar days written notice.`
- **Question**: "What are the retainer fee and termination notice terms in vendor contract vendor_contract_02?"
- **Answer**: "According to [vendor_contract_02.txt#chunk_0], the monthly retainer fee is INR 1,50,000 and termination requires 45 calendar days of written notice."
- **Human Judgment**: `YES` (Faithful synthesis)
- **Judge Verdict**: `YES` — Both clauses are directly stated in the context without additions or distortions.
- **Agreement**: **Match**

---

## 4. Calibration Summary
- **Total Cases**: 10
- **Human vs Judge Agreement**: 10/10 (100.0%)
- **Hallucination Detection Sensitivity**: 5/5 unfaithful cases accurately flagged as `NO`.
- **Faithful Acceptance Specificity**: 5/5 faithful cases accurately verified as `YES`.

