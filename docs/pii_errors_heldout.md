# Held-Out Dataset (DEV2) Error Analysis Report

This document presents a comprehensive diagnostic error analysis of all 96 False Positives (FP) and 32 False Negatives (FN) observed during the one-shot evaluation of the frozen VeilRAG configuration (`recognizers-frozen-v1`) against the 216-case held-out dataset (`data/eval/pii_heldout.jsonl`).

---

## Executive Summary of Held-Out Errors

| Metric | Full Configuration | Presidio Baseline |
| :--- | :---: | :---: |
| **Evaluated Cases** | 216 | 216 |
| **Clean Cases (Zero PII)** | 60 | 60 |
| **Flagged Clean Cases (Clean FPR)** | **19** (31.67%) | **44** (73.33%) |
| **True Positives (TP)** | 124 | 47 |
| **False Positives (FP)** | 96 | 322 |
| **False Negatives (FN)** | 32 | 109 |

---

## 1. Deep Dive: The 73 `PERSON` False Positives

SpaCy's standard English statistical model (`en_core_web_lg`) generated 73 False Positives for the `PERSON` entity type. These errors fall into three mutually exclusive root causes:

### Cause A: Boundary / Tokenization Mismatches with Gold Spans (21 cases)
In these cases, a legitimate person name was present in the text, but spaCy's predicted entity boundary deviated from the gold annotation, causing the Intersection over Union (IoU) overlap to fall below the 80% threshold:
- **Trailing newlines & labels in multi-line memos** (e.g. Case 1):
  - Text: `Team status update:\nLead architect: Rose Brown\nSprint goal: Database sharding.`
  - Gold: `Rose Brown` [start: 36, end: 46]
  - Predicted: `Rose Brown\nSprint` [start: 36, end: 53] (IoU: 0.59)
- **Hindi honorifics and postpositions attached to names** (e.g. Cases 2, 7, 15, 23, 31):
  - Text: `Kripya Robin Patel ji se approval leke release pipeline trigger kar do.`
  - Gold: `Robin Patel` [start: 7, end: 18]
  - Predicted: `Kripya Robin Patel ji se` [start: 0, end: 24] (IoU: 0.46)
- **Compound first/last name splitting** (e.g. Case 2):
  - Text: `Bhai Hope Taylor ko bolo meeting room 4 mein turant join karein.`
  - Gold: `Hope Taylor` [start: 5, end: 16]
  - Predicted: `Bhai Hope` [start: 0, end: 9] (IoU: 0.25) and `Taylor ko bolo meeting` [start: 10, end: 32] (IoU: 0.22)
- **Single name component predictions** (e.g. Case 5):
  - Text: `...Faith Jackson...` -> Predicted only `Jackson` (IoU: 0.54).

### Cause B: Romanized Hindi (Hinglish) Vocabulary Hallucinations (50 cases)
Because `en_core_web_lg` was trained exclusively on standard English syntax, common Romanized Hindi verbs, conjunctions, and conversational markers were misclassified as person names:
- The verb `kar` (do): Flagged as a PERSON in `...pipeline trigger kar do.` across multiple cases (Cases 7, 15, 23, 31, etc.).
- Conversational phrases: `ko bolo meeting` (tell him to join meeting) in Case 34; `ho chuka hai` (has been completed) in Cases 39 and 46; `Kripya apna Adhar` in Cases 35 and 42.

### Cause C: Capitalized Technical Terminology at Sentence Boundaries (2 cases)
- Case 191: Text `Spectrometer reading registered wavelength 5892641032 angstroms.`
  - Gold: `[]` (Clean case)
  - Predicted: `Spectrometer` [0:12] as `PERSON`.
  - Cause: Capitalized single-word subject at the beginning of a sentence.

---

## 2. Deep Dive: `PHONE_NUMBER` vs `INDIAN_MOBILE` (Type Confusion vs Real Misses)

### A. Type Confusion (5 cases)
Standard Indian 10-digit mobile numbers formatted with international prefixes (e.g. `+91-68902-66069`) were detected by Microsoft Presidio's built-in `PhoneRecognizer` as `PHONE_NUMBER`. Because the gold label was `INDIAN_MOBILE`, strict per-entity evaluation counted these as:
- +1 False Positive for `PHONE_NUMBER`
- +1 False Negative for `INDIAN_MOBILE`
- **Affected Cases**: 91, 95, 99, 107.
- **Dotted Aadhaar misclassified as Phone** (Case 61): `9172.0673.7607` was flagged as `PHONE_NUMBER` by Presidio.

### B. Substring Collisions on 12-digit Non-Mobile Numbers (10 cases)
In clean cases containing 12-digit numbers (Cases 157, 159, 168, 169, 170, 171, 173, 175, 177, 179), the regex for `INDIAN_MOBILE` (`(?:\+?91[\s\-]*)?[6-9]\d{9}\b`) lacked a negative lookbehind `(?<!\d)`. Consequently, the trailing 10 digits of a 12-digit tracking or serial number (e.g. `109283746519` -> `9283746519`) were extracted as an Indian mobile number. This is a real recognizer pattern defect.

### C. Real Telephony Misses (1 case)
- Case 93: Text `Bhai mujhe 7081873626 pe WhatsApp call kar lo jab time mile.`
  - Gold: `INDIAN_MOBILE` `7081873626`
  - Cause: Presidio built-in phone detector requires international dialing prefixes or English keywords; our custom detector prioritizes prefixed forms.

---

## 3. Deep Dive: The 8 Aadhaar Misses

All 8 Aadhaar misses occurred in the positive Aadhaar partition (Cases 35 to 64):

| Case ID | Text / Format | Unredacted Aadhaar Value | Root Cause |
| :---: | :--- | :---: | :--- |
| **37** | `Customer Aadhaar slip details:\nCardholder ID: 2967.0519.0500` | `2967.0519.0500` | Dotted delimiter (`.`) not matched by regex |
| **41** | `Attached document: Scanned copy of resident UID 7311.5329.9858` | `7311.5329.9858` | Dotted delimiter (`.`) not matched by regex |
| **45** | `Resident presented valid aadhar enrolment slip bearing 5108.2546.4175` | `5108.2546.4175` | Dotted delimiter (`.`) not matched by regex |
| **46** | `Aapka e-Aadhaar 677476553060 successfully authenticate ho chuka hai.` | `677476553060` | Hyphenated context `e-Aadhaar` missed bare keyword check |
| **49** | `Kripya apna Adhar no 4149.8095.0890 portal pe re-upload karein.` | `4149.8095.0890` | Dotted delimiter (`.`) not matched by regex |
| **53** | `Aapka e-Aadhaar 5729.7939.7234 successfully authenticate ho chuka hai.` | `5729.7939.7234` | Dotted delimiter (`.`) not matched by regex |
| **57** | `Identity verification failure: UIDAI reference 5818.6845.6912 mismatch` | `5818.6845.6912` | Dotted delimiter (`.`) not matched by regex |
| **61** | `Government pension scheme linked to Aadhaar 9172.0673.7607 without errors.` | `9172.0673.7607` | Dotted delimiter (`.`) not matched by regex |

### Summary of Aadhaar Misses:
- **Dotted Delimiters (`\d{4}\.\d{4}\.\d{4}`)**: **7 misses** (87.5%). The pattern `\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b` supported only spaces and hyphens.
- **Context Keyword Variations (`e-Aadhaar`)**: **1 miss** (12.5%). Bare 12-digit number without recognized delimiter or whitespace around `Aadhaar`.

---

## 4. Deep Dive: The 19 Clean-Case False Positives

Out of 60 PII-free clean hard negatives, 19 cases triggered false positive detections:

1. **Substring Indian Mobile False Positives (10 cases)**:
   - Caused by lack of `(?<!\d)` negative lookbehind in `INDIAN_MOBILE` regex:
   - Case 157: `109283746519` flagged as `9283746519`
   - Case 159: `156473829102` flagged as `6473829102`
   - Case 168: `456789012340` flagged as `6789012340`
   - Case 169: `567890123453` flagged as `7890123453`
   - Case 170: `678901234566` flagged as `8901234566`
   - Case 171: `789012345679` flagged as `9012345679`
   - Case 173: `987654321011` flagged as `7654321011`
   - Case 175: `888899990001` flagged as `8899990001`
   - Case 177: `777788889990` flagged as `7788889990`
   - Case 179: `666677778881` flagged as `6677778881`

2. **Presidio Built-in Phone Detections on Non-Phone Digit Sequences (5 cases)**:
   - Presidio built-in telephony regex identified random numeric sequences as phone numbers:
   - Case 158: `Warehouse pallet locator 112233445566 confirmed in aisle 12.` -> `112233445566`
   - Case 188: `Server CPU benchmark completed in 0123456789 nanoseconds...` -> `0123456789`
   - Case 189: `Unix epoch timestamp 1714582930 recorded during system reboot.` -> `1714582930`
   - Case 193: `Thermal sensor output calibrated at 0987654321 millivolts...` -> `0987654321`
   - Case 194: `Optical disk sector index 1234509876 verified during read cycle.` -> `1234509876`

3. **Verhoeff-Valid Non-Aadhaar Sequences (3 cases)**:
   - Bare 12-digit numbers that pass Verhoeff checksum algorithm:
   - Case 164: `Retail point-of-sale receipt 200000000009 archived in sales ledger.` -> `200000000009`
   - Case 165: `Production batch serial 234567890124 passed quality assurance.` -> `234567890124`
   - Case 166: `Factory assembly tracking 987654321096 cataloged in system inventory.` -> `987654321096`

4. **SpaCy NER Capitalized Noun Error (1 case)**:
   - Case 191: `Spectrometer reading registered wavelength 5892641032 angstroms.` -> `Spectrometer`

