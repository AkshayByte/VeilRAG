# VeilRAG PII Sanitization Evaluation Report — Held-Out Coverage Dataset (HELDOUT3)

> Measured evaluation of local fail-closed PII sanitization against labeled ground truth for newly added coverage recognizers (`DATE_OF_BIRTH`, `BANK_ACCOUNT`, `ADDRESS`, `UHID`).
> Generated under frozen tag `recognizers-frozen-v3` with a completely disjoint random seed (`88419`) and unseen sentence templates. Evaluated strictly ONCE without post-hoc tuning.

---

## 1. Executive Summary & Comparison

| Metric | VeilRAG (Full) | Presidio (Baseline) | Absolute Lift |
| :--- | :---: | :---: | :---: |
| **Precision** | **0.8367** | 0.0000 | **+83.67%** |
| **Recall** | **1.0000** | 0.0000 | **+100.00%** |
| **F1 Score** | **0.9111** | 0.0000 | **+91.11%** |
| **Clean-case FPR** | **0.2807** (16/57 flagged) | 0.8246 (47/57 flagged) | **-54.39%** |
| **Character Leak Rate** | **0.0000** (0/2125 chars) | 0.4946 (1051/2125 chars) | **-49.46%** |
| **Character Over-Redaction** | **0.0184** (157/8531 chars) | 0.0686 (585/8531 chars) | **-5.02%** |
| **True Positives** | **82** | 0 | **+82** |
| **False Positives** | **16** | 255 | **-239** |
| **False Negatives** | **0** | 82 | **-82** |

---

## 2. Per-Entity Type Breakdown (VeilRAG Full Configuration)

```
==========================================================================================
 VEILRAG FULL CONFIGURATION (PRESIDIO + CUSTOM RECOGNIZERS) [HELDOUT3 SET] (Cases: 139, IoU: 80%)
==========================================================================================
Entity Type              | Precision | Recall    | F1        | Clean FPR | TP   | FP   | FN  
------------------------------------------------------------------------------------------
ADDRESS                  | 1.0000    | 1.0000    | 1.0000    | 0.0000    | 20   | 0    | 0   
BANK_ACCOUNT             | 1.0000    | 1.0000    | 1.0000    | 0.0000    | 20   | 0    | 0   
DATE_OF_BIRTH            | 1.0000    | 1.0000    | 1.0000    | 0.0000    | 24   | 0    | 0   
INDIAN_MOBILE            | 0.0000    | 0.0000    | 0.0000    | 0.1404    | 0    | 8    | 0   
PERSON                   | 0.0000    | 0.0000    | 0.0000    | 0.0175    | 0    | 1    | 0   
PHONE_NUMBER             | 0.0000    | 0.0000    | 0.0000    | 0.0351    | 0    | 2    | 0   
UHID                     | 1.0000    | 1.0000    | 1.0000    | 0.0000    | 18   | 0    | 0   
US_SSN                   | 0.0000    | 0.0000    | 0.0000    | 0.0877    | 0    | 5    | 0   
------------------------------------------------------------------------------------------
OVERALL                  | 0.8367    | 1.0000    | 0.9111    | 0.2807    | 82   | 16   | 0   
==========================================================================================
  Type-Agnostic Leak Rate:         0.0000 (0/2125 gold PII chars unredacted)
  Type-Agnostic Over-Redaction:    0.0184 (157/8531 non-PII chars redacted)
==========================================================================================
```

---

## 3. Presidio Baseline Configuration (No Custom Recognizers)

```
==========================================================================================
 BASELINE CONFIGURATION (PRESIDIO BUILT-INS ONLY) [HELDOUT3 SET] (Cases: 139, IoU: 80%)
==========================================================================================
Entity Type              | Precision | Recall    | F1        | Clean FPR | TP   | FP   | FN  
------------------------------------------------------------------------------------------
ADDRESS                  | 0.0000    | 0.0000    | 0.0000    | 0.0000    | 0    | 0    | 20  
BANK_ACCOUNT             | 0.0000    | 0.0000    | 0.0000    | 0.0000    | 0    | 0    | 20  
DATE_OF_BIRTH            | 0.0000    | 0.0000    | 0.0000    | 0.0000    | 0    | 0    | 24  
DATE_TIME                | 0.0000    | 0.0000    | 0.0000    | 0.3509    | 0    | 55   | 0   
LOCATION                 | 0.0000    | 0.0000    | 0.0000    | 0.2105    | 0    | 54   | 0   
PERSON                   | 0.0000    | 0.0000    | 0.0000    | 0.0175    | 0    | 7    | 0   
PHONE_NUMBER             | 0.0000    | 0.0000    | 0.0000    | 0.1754    | 0    | 18   | 0   
UHID                     | 0.0000    | 0.0000    | 0.0000    | 0.0000    | 0    | 0    | 18  
UK_NHS                   | 0.0000    | 0.0000    | 0.0000    | 0.0175    | 0    | 1    | 0   
US_BANK_NUMBER           | 0.0000    | 0.0000    | 0.0000    | 0.2982    | 0    | 37   | 0   
US_DRIVER_LICENSE        | 0.0000    | 0.0000    | 0.0000    | 0.5439    | 0    | 78   | 0   
US_PASSPORT              | 0.0000    | 0.0000    | 0.0000    | 0.0877    | 0    | 5    | 0   
------------------------------------------------------------------------------------------
OVERALL                  | 0.0000    | 0.0000    | 0.0000    | 0.8246    | 0    | 255  | 82  
==========================================================================================
  Type-Agnostic Leak Rate:         0.4946 (1051/2125 gold PII chars unredacted)
  Type-Agnostic Over-Redaction:    0.0686 (585/8531 non-PII chars redacted)
==========================================================================================
```

---

## 4. Key Takeaways
1. **Zero Leaks Across New Types**: 100% recall achieved on all 4 new entity types (`DATE_OF_BIRTH`, `BANK_ACCOUNT`, `ADDRESS`, `UHID`).
2. **Zero False Positives from Coverage Recognizers**: Not a single false positive was produced by `DateOfBirthRecognizer`, `BankAccountRecognizer`, `AddressRecognizer`, or `HospitalIDRecognizer`.
3. **Hard Negative Robustness**: Every invoice/due date, 6-digit OTP, order number, 9-digit quantity, address without PIN, and standalone PIN code was correctly ignored by the new recognizers.

