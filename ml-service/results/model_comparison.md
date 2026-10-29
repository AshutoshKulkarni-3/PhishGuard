# PhishGuard — Classification Model Comparison

Generated at: 2026-10-13 15:56:42

## 1. Overall Performance Table

| Model | Accuracy | Precision | Recall | F1-Score | False Negatives (Missed) | False Positives (False Alarm) | Train Time (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | 0.8582 | 0.8640 | 0.4403 | 0.5834 | 12,794 | 1,585 | 0.525s |
| **Decision Tree** | 0.9214 | 0.8684 | 0.7674 | 0.8148 | 5,318 | 2,658 | 2.02s |
| **Random Forest** | 0.9316 | 0.9234 | 0.7598 | 0.8336 | 5,492 | 1,441 | 6.744s |

## 2. Confusion Matrices

### Logistic Regression

- **True Negatives (TN)**: 76,994 (Safe URLs classified as Safe)
- **False Positives (FP)**: 1,585 (Safe URLs incorrectly flagged as Phishing)
- **False Negatives (FN)**: 12,794 (Phishing URLs that bypassed detection)
- **True Positives (TP)**: 10,066 (Phishing URLs successfully blocked)

### Decision Tree

- **True Negatives (TN)**: 75,921 (Safe URLs classified as Safe)
- **False Positives (FP)**: 2,658 (Safe URLs incorrectly flagged as Phishing)
- **False Negatives (FN)**: 5,318 (Phishing URLs that bypassed detection)
- **True Positives (TP)**: 17,542 (Phishing URLs successfully blocked)

### Random Forest

- **True Negatives (TN)**: 77,138 (Safe URLs classified as Safe)
- **False Positives (FP)**: 1,441 (Safe URLs incorrectly flagged as Phishing)
- **False Negatives (FN)**: 5,492 (Phishing URLs that bypassed detection)
- **True Positives (TP)**: 17,368 (Phishing URLs successfully blocked)

