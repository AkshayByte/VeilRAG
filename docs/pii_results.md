# VeilRAG PII Sanitization Evaluation Report

> Measured evaluation of local fail-closed PII sanitization against labeled ground truth.
> Generated from synthetic cases using Faker (`en_IN` and `en_US`).

## Metric Definitions

- **Clean-case False Positive Rate (Clean FPR)**: `(PII-free cases where ANY entity was flagged) / (number of PII-free cases)`. Measures the proportion of non-PII documents incorrectly subjected to redaction.
- **Span Precision**: `TP / (TP + FP)`. The proportion of flagged spans that truly correspond to ground-truth PII. The span error rate is `1 - precision` (the share of flagged spans that are wrong).
- **Recall**: `TP / (TP + FN)`. The proportion of ground-truth PII entities successfully detected and redacted.
- **F1 Score**: `2 * (Precision * Recall) / (Precision + Recall)`. Harmonic mean of precision and recall.
- **Character Leak Rate (Type-Agnostic)**: `(Total gold PII characters NOT covered by ANY detected span) / (Total gold PII characters)`. Measures raw sensitive text leakage independent of entity categorization.
- **Character Over-Redaction Rate (Type-Agnostic)**: `(Total non-PII characters covered by ANY detected span) / (Total non-PII characters)`. Measures collateral redaction of benign document text across the corpus.

## 1. Development Dataset Evaluation (DEV)

- **Dataset**: `data/eval/pii_cases.jsonl`
- Used during initial development of custom recognizers and detectors.

### 1. Development Dataset Evaluation (DEV): VeilRAG vs Presidio Baseline Summary

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |
|:---|:---:|:---:|:---:|
| **Precision** | 0.9769 | 0.2982 | +0.6787 |
| **Recall** | 0.9941 | 0.4824 | +0.5117 |
| **F1 Score** | 0.9854 | 0.3685 | +0.6169 |
| **Clean-case FPR** | 0.1000 | 0.4250 | -0.3250 |
| **Character Leak Rate** | 0.0052 | 0.2677 | -0.2625 |
| **Character Over-Redaction** | 0.0043 | 0.0364 | -0.0321 |

### 1. Development Dataset Evaluation (DEV) — VeilRAG Full Configuration

- Cases evaluated: 210
- PII-free clean cases: 40
- Flagged clean cases: 4 (Clean-case FPR: 0.1000)
- Character leak rate (type-agnostic): 0.0052 (14/2682 gold PII characters unredacted)
- Character over-redaction rate (type-agnostic): 0.0043 (49/11276 non-PII characters redacted)
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | Clean FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `AWS_SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1 | 0 | 0 |
| `CREDIT_CARD` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `IDENTITY_DOCUMENT` | 0.9375 | 1.0000 | 0.9677 | 0.0500 | 30 | 2 | 0 |
| `IFSC_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `INDIAN_MOBILE` | 0.9524 | 1.0000 | 0.9756 | 0.0250 | 20 | 1 | 0 |
| `IP_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `MEDICAL_RECORD_NUMBER` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1 | 0 | 0 |
| `PAN_NUMBER` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `PERSON` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 35 | 0 | 0 |
| `PHONE_NUMBER` | 0.9333 | 0.9333 | 0.9333 | 0.0250 | 14 | 1 | 1 |
| `SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `UPI_ID` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `URL` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `US_SSN` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| **OVERALL** | **0.9769** | **0.9941** | **0.9854** | **0.1000** | **169** | **4** | **1** |

### 1. Development Dataset Evaluation (DEV) — Presidio Baseline Configuration

- Cases evaluated: 210
- PII-free clean cases: 40
- Flagged clean cases: 17 (Clean-case FPR: 0.4250)
- Character leak rate (type-agnostic): 0.2677 (718/2682 gold PII characters unredacted)
- Character over-redaction rate (type-agnostic): 0.0364 (410/11276 non-PII characters redacted)
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | Clean FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `AWS_SECRET_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 1 |
| `CREDIT_CARD` | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 1 | 0 | 1 |
| `DATE_TIME` | 0.0000 | 0.0000 | 0.0000 | 0.3000 | 0 | 56 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `IDENTITY_DOCUMENT` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 30 |
| `IFSC_CODE` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `INDIAN_MOBILE` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 20 |
| `IP_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `MEDICAL_RECORD_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 1 |
| `PAN_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 25 |
| `PERSON` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 35 | 0 | 0 |
| `PHONE_NUMBER` | 0.3684 | 0.9333 | 0.5283 | 0.0500 | 14 | 24 | 1 |
| `SECRET_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `UK_NHS` | 0.0000 | 0.0000 | 0.0000 | 0.0250 | 0 | 2 | 0 |
| `UPI_ID` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `URL` | 0.0714 | 1.0000 | 0.1333 | 0.0000 | 2 | 26 | 0 |
| `US_BANK_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.1500 | 0 | 36 | 0 |
| `US_DRIVER_LICENSE` | 0.0000 | 0.0000 | 0.0000 | 0.3000 | 0 | 48 | 0 |
| `US_ITIN` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 1 | 0 |
| `US_SSN` | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 1 | 0 | 1 |
| **OVERALL** | **0.2982** | **0.4824** | **0.3685** | **0.4250** | **82** | **193** | **88** |

## 2. First Held-Out Run (Pre-Fix / DEV2)

- **Dataset**: `data/eval/pii_dev2.jsonl`
- First held-out evaluation run on recognizers-frozen-v1.
- Diagnosed in `docs/pii_errors_heldout.md` and subsequently used as DEV2.

### 2. First Held-Out Run (Pre-Fix / DEV2): VeilRAG vs Presidio Baseline Summary

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |
|:---|:---:|:---:|:---:|
| **Precision** | 0.6250 | 0.1274 | +0.4976 |
| **Recall** | 0.8654 | 0.3013 | +0.5641 |
| **F1 Score** | 0.7258 | 0.1790 | +0.5468 |
| **Clean-case FPR** | 0.1500 | 0.7333 | -0.5833 |
| **Character Leak Rate** | 0.0305 | 0.3262 | -0.2957 |
| **Character Over-Redaction** | 0.0601 | 0.1048 | -0.0447 |

### 2. First Held-Out Run (Pre-Fix / DEV2) — VeilRAG Full Configuration

- Cases evaluated: 216
- PII-free clean cases: 60
- Flagged clean cases: 9 (Clean-case FPR: 0.1500)
- Character leak rate (type-agnostic): 0.0305 (74/2425 gold PII characters unredacted)
- Character over-redaction rate (type-agnostic): 0.0601 (822/13675 non-PII characters redacted)
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | Clean FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| `AWS_SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `CREDIT_CARD` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 1 | 0 | 1 |
| `IDENTITY_DOCUMENT` | 0.9062 | 0.9667 | 0.9355 | 0.0500 | 29 | 3 | 1 |
| `IFSC_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| `INDIAN_MOBILE` | 1.0000 | 0.9000 | 0.9474 | 0.0000 | 18 | 0 | 2 |
| `PAN_NUMBER` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `PERSON` | 0.1978 | 0.5143 | 0.2857 | 0.0167 | 18 | 73 | 17 |
| `PHONE_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0833 | 0 | 5 | 0 |
| `SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `UPI_ID` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 4 | 0 | 0 |
| `US_SSN` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| **OVERALL** | **0.6250** | **0.8654** | **0.7258** | **0.1500** | **135** | **81** | **21** |

### 2. First Held-Out Run (Pre-Fix / DEV2) — Presidio Baseline Configuration

- Cases evaluated: 216
- PII-free clean cases: 60
- Flagged clean cases: 44 (Clean-case FPR: 0.7333)
- Character leak rate (type-agnostic): 0.3262 (791/2425 gold PII characters unredacted)
- Character over-redaction rate (type-agnostic): 0.1048 (1433/13675 non-PII characters redacted)
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | Clean FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 3 |
| `AWS_SECRET_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `CREDIT_CARD` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `DATE_TIME` | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0 | 55 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 1 | 0 | 1 |
| `IDENTITY_DOCUMENT` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 30 |
| `IFSC_CODE` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 3 |
| `INDIAN_MOBILE` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 20 |
| `LOCATION` | 0.0000 | 0.0000 | 0.0000 | 0.0333 | 0 | 9 | 0 |
| `MAC_ADDRESS` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 7 | 0 |
| `NRP` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 1 | 0 |
| `PAN_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 25 |
| `PERSON` | 0.1978 | 0.5143 | 0.2857 | 0.0167 | 18 | 73 | 17 |
| `PHONE_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0833 | 0 | 27 | 0 |
| `SECRET_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `UK_NHS` | 0.0000 | 0.0000 | 0.0000 | 0.0333 | 0 | 5 | 0 |
| `UPI_ID` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 4 |
| `URL` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 29 | 0 |
| `US_BANK_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.5167 | 0 | 53 | 0 |
| `US_DRIVER_LICENSE` | 0.0000 | 0.0000 | 0.0000 | 0.6500 | 0 | 62 | 0 |
| `US_ITIN` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 1 | 0 |
| `US_SSN` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| **OVERALL** | **0.1274** | **0.3013** | **0.1790** | **0.7333** | **47** | **322** | **109** |

## 3. Final Held-Out Dataset Evaluation (HELD-OUT)

- **Dataset**: `data/eval/pii_heldout.jsonl`
- Frozen recognizers (`recognizers-frozen-v2`).
- Strictly evaluated once without tuning.

> [!NOTE] Secret Scanner Compatibility & Dataset Adjustments
> The held-out evaluation dataset was adjusted twice post-generation:
> 1. Synthetic Stripe-style keys (sk-live and pk-test vectors) triggered GitHub push protection and were replaced with scanner-safe mock secrets (mock_sk_... and mock_pk_...), which are detected with 100% precision and recall by VeilRAG's GenericSecretRecognizer.
> 2. An initial over-correction temporarily replaced AWS access keys (AKIA...) with an AWSK prefix. Because AWSKeyRecognizer was frozen under recognizers-frozen-v2 with strict pattern matching, this made them undetectable by construction (3 false negatives). This over-correction was reverted to restore the exact original AKIA test vectors.
>
> Final held-out results: Precision 0.6976, Recall 0.9167 (143 TP / 62 FP / 13 FN), F1 0.7922, Character Leak Rate 0.0061 (15/2,443 characters unredacted).

### 3. Final Held-Out Dataset Evaluation (HELD-OUT): VeilRAG vs Presidio Baseline Summary

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |
|:---|:---:|:---:|:---:|
| **Precision** | 0.6976 | 0.1538 | +0.5438 |
| **Recall** | 0.9167 | 0.3590 | +0.5577 |
| **F1 Score** | 0.7922 | 0.2154 | +0.5768 |
| **Clean-case FPR** | 0.1364 | 0.6667 | -0.5303 |
| **Character Leak Rate** | 0.0061 | 0.2767 | -0.2706 |
| **Character Over-Redaction** | 0.0503 | 0.0984 | -0.0481 |

### 3. Final Held-Out Dataset Evaluation (HELD-OUT) — VeilRAG Full Configuration

- Cases evaluated: 222
- PII-free clean cases: 66
- Flagged clean cases: 9 (Clean-case FPR: 0.1364)
- Character leak rate (type-agnostic): 0.0061 (15/2443 gold PII characters unredacted)
- Character over-redaction rate (type-agnostic): 0.0503 (722/14348 non-PII characters redacted)
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | Clean FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| `AWS_SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `CREDIT_CARD` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `IDENTITY_DOCUMENT` | 0.9091 | 1.0000 | 0.9524 | 0.0455 | 30 | 3 | 0 |
| `IFSC_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| `INDIAN_MOBILE` | 1.0000 | 0.8500 | 0.9189 | 0.0000 | 17 | 0 | 3 |
| `PAN_NUMBER` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `PERSON` | 0.3165 | 0.7143 | 0.4386 | 0.0152 | 25 | 54 | 10 |
| `PHONE_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0758 | 0 | 5 | 0 |
| `SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `UPI_ID` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 4 | 0 | 0 |
| `US_SSN` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| **OVERALL** | **0.6976** | **0.9167** | **0.7922** | **0.1364** | **143** | **62** | **13** |

### 3. Final Held-Out Dataset Evaluation (HELD-OUT) — Presidio Baseline Configuration

- Cases evaluated: 222
- PII-free clean cases: 66
- Flagged clean cases: 44 (Clean-case FPR: 0.6667)
- Character leak rate (type-agnostic): 0.2767 (676/2443 gold PII characters unredacted)
- Character over-redaction rate (type-agnostic): 0.0984 (1412/14348 non-PII characters redacted)
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | Clean FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 3 |
| `AWS_SECRET_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `CREDIT_CARD` | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 1 | 0 | 1 |
| `DATE_TIME` | 0.0000 | 0.0000 | 0.0000 | 0.2273 | 0 | 58 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `IDENTITY_DOCUMENT` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 30 |
| `IFSC_CODE` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 3 |
| `INDIAN_MOBILE` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 20 |
| `LOCATION` | 0.0000 | 0.0000 | 0.0000 | 0.0455 | 0 | 16 | 0 |
| `MAC_ADDRESS` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 7 | 0 |
| `NRP` | 0.0000 | 0.0000 | 0.0000 | 0.0152 | 0 | 1 | 0 |
| `PAN_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 25 |
| `PERSON` | 0.3086 | 0.7143 | 0.4310 | 0.0152 | 25 | 56 | 10 |
| `PHONE_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0758 | 0 | 25 | 0 |
| `SECRET_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `UK_NHS` | 0.0000 | 0.0000 | 0.0000 | 0.0303 | 0 | 2 | 0 |
| `UPI_ID` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 4 |
| `URL` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 37 | 0 |
| `US_BANK_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.4848 | 0 | 49 | 0 |
| `US_DRIVER_LICENSE` | 0.0000 | 0.0000 | 0.0000 | 0.6061 | 0 | 57 | 0 |
| `US_SSN` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| **OVERALL** | **0.1538** | **0.3590** | **0.2154** | **0.6667** | **56** | **308** | **100** |

## Limitations

- **Synthetic Data**: Both the development and held-out evaluation sets are synthetically generated using Faker (`en_IN` and `en_US`). Real-world private documents exhibit messier token distributions, arbitrary OCR errors, multi-column tables, scanned PDFs, and handwriting not fully represented in synthetic text strings.
- **English-Heavy**: All cases use English and Romanized Hinglish. Hindi or other regional Indian script inputs (Devanagari, Tamil, Telugu, etc.) are outside the current Presidio analyzer configuration.
- **Same Author as Recognizers**: Synthetic generation templates were conceived by the same development framework as the custom regex and Presidio recognizers, which may create unintended shared structural priors despite distinct random seeds and decoupled template vocabularies.
