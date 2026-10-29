# PhishGuard — Serialized Model & Inference Artifacts

This directory contains the production-ready machine learning artifacts for the **PhishGuard** phishing website detection service.

---

## 1. Artifact Directory Structure

```
model/
├── phishguard_model.joblib   # Self-contained production inference bundle (Estimator + Feature metadata)
├── metadata.json             # Human- & machine-readable package metadata and environment specs
├── predictor.py              # In-memory inference engine (Singleton pattern, zero retraining)
├── random_forest.joblib      # Raw trained Random Forest classifier
├── decision_tree.joblib      # Raw trained Decision Tree classifier
├── logistic_regression.joblib# Raw trained Logistic Regression Pipeline
└── README.md                 # This file
```

---

## 2. Environment & Dependency Specifications

| Component | Exact Version | Purpose |
| :--- | :--- | :--- |
| **Python** | `3.9.18` | Runtime environment |
| **Scikit-learn** | `1.4.2` | Random Forest Estimator & Pipeline serialization |
| **Joblib** | `1.4.2` | Fast persistence & array compression (`compress=3`) |
| **NumPy** | `1.26.4` | Numeric array representation |
| **Pandas** | `2.2.2` | DataFrame structure for feature alignment |

> **Critical Note on Pickling/Joblib Compatibility:**  
> Joblib artifacts serialize Python bytecode and NumPy internal data structures. Deserializing on a different minor version of Scikit-Learn (e.g. 1.2 or 1.5) may cause unpickling warnings or incompatible tree structures. Always run inference in the provided virtual environment with **Scikit-learn 1.4.2**.

---

## 3. Contents of `phishguard_model.joblib`

The artifact is saved as a structured dictionary rather than an unadorned estimator. This guarantees that inference always matches training:

```python
{
    "model": <RandomForestClassifier(n_estimators=100, max_depth=25, ...)>,
    "model_name": "Random Forest Classifier",
    "algorithm": "sklearn.ensemble.RandomForestClassifier",
    "feature_names": [
        "url_length", "hostname_length", "domain_length", "tld_length",
        "path_length", "query_length", "n_dots", "n_hyphens",
        "n_underscores", "n_digits", "n_special_chars", "n_slashes",
        "n_query_params", "has_at_symbol", "has_ip_hostname", "is_https",
        "has_port", "n_subdomains", "has_suspicious_keyword", "url_entropy",
        "domain_has_hyphen", "has_double_slash_in_path", "path_token_count"
    ],
    "feature_count": 23,
    "label_mapping": {0: "legitimate", 1: "phishing"},
    "decision_threshold": 0.50,
    "environment": {
        "python_version": "3.9.18",
        "scikit_learn_version": "1.4.2",
        "joblib_version": "1.4.2"
    }
}
```

---

## 4. How Inference Works (In-Memory / Zero Re-Training)

In a web API (Flask), **a model must NEVER be re-trained on incoming requests**:
1. When the server launches, `get_predictor()` loads `phishguard_model.joblib` **once** into memory.
2. Incoming HTTP requests pass URLs to `predictor.predict_url(url)`.
3. The method extracts the 23 lexical features safely without network calls, arranges them into a DataFrame with exact column names in `FEATURE_NAMES` order, and invokes `model.predict_proba()`.
4. Inference latency is **~14 ms**, enabling real-time browser extension and backend API evaluation.

---

## 5. How to Retrain and Regenerate the Artifacts

To reproduce or retrain the model from scratch on new data:

```bash
# 1. Activate the environment
cd ml-service
source venv/bin/activate

# 2. (Optional) Re-prepare clean dataset splits
python training/prepare_dataset.py

# 3. Train all candidate models and save to model/
python training/train.py --force-extract

# 4. Evaluate models, run 5-fold CV, and select top performer
python training/evaluate_and_select.py

# 5. Package into the self-contained production bundle
python training/package_model.py

# 6. Run verification tests on the packaged artifact
python training/test_inference.py
```

---

## 6. Academic Disclaimer (Viva Note)

- Sample predictions on arbitrary URLs confirm the **functional validity** of the inference pipeline (features align properly, probabilities sum to 1.0, exceptions are caught).
- Sample tests **do not prove real-world accuracy**.
- Statistical efficacy was proven on the **101,439 held-out test split**:
  - **Accuracy:** 93.17%
  - **Precision:** 92.34%
  - **Recall:** 75.98%
  - **F1-Score:** 0.8336
  - **5-Fold CV F1:** 0.8319 ± 0.0022
