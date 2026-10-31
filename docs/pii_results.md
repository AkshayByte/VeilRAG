# VeilRAG PII Evaluation Results (full configuration)

- Cases evaluated: 1
- Span overlap threshold: 80%
- Configuration: Presidio + custom recognizers

## Overall

| Metric | Value | TP | FP | FN |
| --- | --- | --- | --- | --- |
| precision | 1.0000 | 2 | 0 | 0 |
| recall | 1.0000 | 2 | 0 | 0 |
| f1 | 1.0000 | 2 | 0 | 0 |
| false_positive_rate | 0.0000 | 2 | 0 | 0 |

## Per entity type

| Entity type | precision | recall | f1 | false_positive_rate | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EMAIL_ADDRESS | 1.0000|1.0000|1.0000|0.0000|1|0|0 |
| PERSON | 1.0000|1.0000|1.0000|0.0000|1|0|0 |

## Sample findings

- `true_positive` PERSON at 8-20
- `true_positive` EMAIL_ADDRESS at 24-41
