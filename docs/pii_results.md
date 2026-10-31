# VeilRAG PII Sanitization Evaluation Report

> Measured evaluation of local fail-closed PII sanitization against labeled ground truth.
> Generated from synthetic cases using Faker (`en_IN` and `en_US`).

## Metric Definitions

- **Clean-case False Positive Rate (Clean FPR)**: `(PII-free cases where ANY entity was flagged) / (number of PII-free cases)`. Measures the proportion of non-PII documents incorrectly subjected to redaction.
- **Span Precision**: `TP / (TP + FP)`. The proportion of flagged spans that truly correspond to ground-truth PII. The span error rate is `1 - precision` (the share of flagged spans that are wrong).
- **Recall**: `TP / (TP + FN)`. The proportion of ground-truth PII entities successfully detected and redacted.
- **F1 Score**: `2 * (Precision * Recall) / (Precision + Recall)`. Harmonic mean of precision and recall.

## 1. Development Dataset Evaluation (DEV)

- **Dataset**: `data/eval/pii_cases.jsonl`
- Used during development of custom recognizers and detectors.

### DEV Set: VeilRAG vs Presidio Baseline Summary

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |
|:---|:---:|:---:|:---:|
| **Precision** | 0.9769 | 0.2982 | +0.6787 |
| **Recall** | 0.9941 | 0.4824 | +0.5117 |
| **F1 Score** | 0.9854 | 0.3685 | +0.6169 |
| **Clean-case FPR** | 0.1000 | 0.4250 | -0.3250 |

### DEV Set — VeilRAG Full Configuration

- Cases evaluated: 210
- PII-free clean cases: 40
- Flagged clean cases: 4 (Clean-case FPR: 0.1000)
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

### DEV Set — Presidio Baseline Configuration

- Cases evaluated: 210
- PII-free clean cases: 40
- Flagged clean cases: 17 (Clean-case FPR: 0.4250)
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

## 2. Held-Out Dataset Evaluation (HELD-OUT)

- **Dataset**: `data/eval/pii_heldout.jsonl`
- Frozen recognizers (`recognizers-frozen-v1`). Evaluated strictly once without tuning.

### HELD-OUT Set: VeilRAG vs Presidio Baseline Summary

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |
|:---|:---:|:---:|:---:|
| **Precision** | 0.5636 | 0.1274 | +0.4362 |
| **Recall** | 0.7949 | 0.3013 | +0.4936 |
| **F1 Score** | 0.6596 | 0.1790 | +0.4806 |
| **Clean-case FPR** | 0.3167 | 0.7333 | -0.4166 |

### HELD-OUT Set — VeilRAG Full Configuration

- Cases evaluated: 216
- PII-free clean cases: 60
- Flagged clean cases: 19 (Clean-case FPR: 0.3167)
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | Clean FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| `AWS_SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `CREDIT_CARD` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 1 | 0 | 1 |
| `IDENTITY_DOCUMENT` | 0.8800 | 0.7333 | 0.8000 | 0.0500 | 22 | 3 | 8 |
| `IFSC_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| `INDIAN_MOBILE` | 0.5833 | 0.7000 | 0.6364 | 0.1667 | 14 | 10 | 6 |
| `PAN_NUMBER` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `PERSON` | 0.1978 | 0.5143 | 0.2857 | 0.0167 | 18 | 73 | 17 |
| `PHONE_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0833 | 0 | 10 | 0 |
| `SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `UPI_ID` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 4 | 0 | 0 |
| `US_SSN` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3 | 0 | 0 |
| **OVERALL** | **0.5636** | **0.7949** | **0.6596** | **0.3167** | **124** | **96** | **32** |

### HELD-OUT Set — Presidio Baseline Configuration

- Cases evaluated: 216
- PII-free clean cases: 60
- Flagged clean cases: 44 (Clean-case FPR: 0.7333)
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

## Limitations

- **Synthetic Data**: Both the development and held-out evaluation sets are synthetically generated using Faker (`en_IN` and `en_US`). Real-world private documents exhibit messier token distributions, arbitrary OCR errors, multi-column tables, scanned PDFs, and handwriting not fully represented in synthetic text strings.
- **English-Heavy**: All cases use English and Romanized Hinglish. Hindi or other regional Indian script inputs (Devanagari, Tamil, Telugu, etc.) are outside the current Presidio analyzer configuration.
- **Same Author as Recognizers**: Synthetic generation templates were conceived by the same development framework as the custom regex and Presidio recognizers, which may create unintended shared structural priors despite distinct random seeds and decoupled template vocabularies.
