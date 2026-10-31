# VeilRAG PII Sanitization Evaluation Report

> Measured evaluation of local fail-closed PII sanitization against labeled ground truth.
> Generated from synthetic cases using Faker (`en_IN` and `en_US`).

## Executive Summary

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |
|:---|:---:|:---:|:---:|
| **Precision** | 0.9769 | 0.2982 | +0.6787 |
| **Recall** | 0.9941 | 0.4824 | +0.5117 |
| **F1 Score** | 0.9854 | 0.3685 | +0.6169 |
| **False Positive Rate** | 0.8000 | 0.6868 | +0.1132 |

### VeilRAG Full Configuration (Presidio + Custom Recognizers)

- Cases evaluated: 210
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `AWS_SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1 | 0 | 0 |
| `CREDIT_CARD` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `IDENTITY_DOCUMENT` | 0.9375 | 1.0000 | 0.9677 | 1.0000 | 30 | 2 | 0 |
| `IFSC_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `INDIAN_MOBILE` | 0.9524 | 1.0000 | 0.9756 | 1.0000 | 20 | 1 | 0 |
| `IP_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `MEDICAL_RECORD_NUMBER` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1 | 0 | 0 |
| `PAN_NUMBER` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `PERSON` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 35 | 0 | 0 |
| `PHONE_NUMBER` | 0.9333 | 0.9333 | 0.9333 | 0.5000 | 14 | 1 | 1 |
| `SECRET_KEY` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `UPI_ID` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `URL` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `US_SSN` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| **OVERALL** | **0.9769** | **0.9941** | **0.9854** | **0.8000** | **169** | **4** | **1** |

### Baseline Configuration (Presidio Built-ins Only)

- Cases evaluated: 210
- Span overlap threshold (IoU): 80%

| Entity Type | Precision | Recall | F1 Score | FPR | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `AWS_ACCESS_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `AWS_SECRET_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 1 |
| `CREDIT_CARD` | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 1 | 0 | 1 |
| `DATE_TIME` | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0 | 56 | 0 |
| `EMAIL_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 25 | 0 | 0 |
| `IBAN_CODE` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `IDENTITY_DOCUMENT` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 30 |
| `IFSC_CODE` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `INDIAN_MOBILE` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 20 |
| `IP_ADDRESS` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 0 | 0 |
| `MEDICAL_RECORD_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 1 |
| `PAN_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 25 |
| `PERSON` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 35 | 0 | 0 |
| `PHONE_NUMBER` | 0.3684 | 0.9333 | 0.5283 | 0.9600 | 14 | 24 | 1 |
| `SECRET_KEY` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `UK_NHS` | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0 | 2 | 0 |
| `UPI_ID` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| `URL` | 0.0714 | 1.0000 | 0.1333 | 1.0000 | 2 | 26 | 0 |
| `US_BANK_NUMBER` | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0 | 36 | 0 |
| `US_DRIVER_LICENSE` | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0 | 48 | 0 |
| `US_ITIN` | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0 | 1 | 0 |
| `US_SSN` | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 1 | 0 | 1 |
| **OVERALL** | **0.2982** | **0.4824** | **0.3685** | **0.6868** | **82** | **193** | **88** |

## Evaluation Methodology

- **Dataset**: 210 synthetic test cases generated with Faker.
- **Locales**: `en_IN` (Indian identifiers) and `en_US` (US/Global formats).
- **Metric Matching**: IoU span overlap threshold >= 80%.
- **Negative Cases**: Non-PII lookalikes (order numbers failing Verhoeff checksum, PIN codes, device serials) and clean sentences with zero PII.
- **Strict Zero-Hallucination Metrics**: All numbers come directly from execution.
