"""
PhishGuard — Task 6: Package Model Artifact for Production Inference
=====================================================================
Packages the trained Random Forest classifier into a self-contained,
production-ready Joblib artifact containing:
  - Trained Scikit-Learn Estimator / Pipeline
  - Exact ordered feature names (FEATURE_NAMES)
  - Target label mapping ({0: "legitimate", 1: "phishing"})
  - Default classification decision threshold (0.50)
  - Dependency versions (scikit-learn 1.4.2, joblib 1.4.2, python 3.9.18)
  - Training metrics summary & hash/timestamp

Saves:
  - model/phishguard_model.joblib
  - model/metadata.json
"""

import json
import os
import platform
import sys
import time
from typing import Dict, Any

import joblib
import sklearn

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from training.feature_extraction import FEATURE_NAMES

MODEL_DIR = os.path.join(PROJECT_ROOT, "model")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

SOURCE_MODEL_PATH = os.path.join(MODEL_DIR, "random_forest.joblib")
DEST_BUNDLE_PATH = os.path.join(MODEL_DIR, "phishguard_model.joblib")
METADATA_JSON_PATH = os.path.join(MODEL_DIR, "metadata.json")


def package_model_artifact() -> None:
    print("\n" + "=" * 78)
    print("  PHISHGUARD: PACKAGING MODEL ARTIFACT FOR INFERENCE")
    print("=" * 78)

    if not os.path.isfile(SOURCE_MODEL_PATH):
        raise FileNotFoundError(
            f"Source model artifact not found at {SOURCE_MODEL_PATH}. "
            "Please run `python training/train.py` first."
        )

    print(f"• Loading trained model from: {SOURCE_MODEL_PATH}")
    model_obj = joblib.load(SOURCE_MODEL_PATH)

    # Load performance metrics if available from Task 4 / 5
    comp_json_path = os.path.join(RESULTS_DIR, "model_comparison.json")
    metrics_summary = {}
    if os.path.isfile(comp_json_path):
        with open(comp_json_path, "r") as f:
            full_results = json.load(f)
            if "Random Forest" in full_results:
                rf_res = full_results["Random Forest"]
                metrics_summary = {
                    "accuracy": rf_res.get("accuracy"),
                    "precision": rf_res.get("precision"),
                    "recall": rf_res.get("recall"),
                    "f1_score": rf_res.get("f1_score"),
                    "confusion_matrix": rf_res.get("confusion_matrix"),
                    "test_sample_count": rf_res.get("test_sample_count")
                }

    # Bundle definition
    bundle: Dict[str, Any] = {
        "model": model_obj,
        "model_name": "Random Forest Classifier",
        "algorithm": "sklearn.ensemble.RandomForestClassifier",
        "feature_names": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "label_mapping": {
            0: "legitimate",
            1: "phishing"
        },
        "inverse_label_mapping": {
            "legitimate": 0,
            "phishing": 1
        },
        "decision_threshold": 0.50,
        "environment": {
            "python_version": platform.python_version(),
            "scikit_learn_version": sklearn.__version__,
            "joblib_version": joblib.__version__,
            "os_platform": platform.platform()
        },
        "metrics_heldout_test": metrics_summary,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }

    print("• Serializing bundled artifact to Joblib (compression=3)...")
    joblib.dump(bundle, DEST_BUNDLE_PATH, compress=3)
    file_size_mb = os.path.getsize(DEST_BUNDLE_PATH) / (1024 * 1024)
    print(f"  ✔ Artifact saved: {DEST_BUNDLE_PATH} ({file_size_mb:.2f} MB)")

    # Save standalone metadata JSON (without binary model) for quick inspection
    meta_json_data = {k: v for k, v in bundle.items() if k != "model"}
    with open(METADATA_JSON_PATH, "w") as f:
        json.dump(meta_json_data, f, indent=2)
    print(f"  ✔ Metadata saved: {METADATA_JSON_PATH}")

    print("\n" + "=" * 78)
    print("  PACKAGE SPECIFICATION:")
    print("=" * 78)
    print(f"  Algorithm            : {bundle['algorithm']}")
    print(f"  Feature Dimension    : {bundle['feature_count']} features")
    print(f"  Target Labels        : 0 -> 'legitimate', 1 -> 'phishing'")
    print(f"  Python Version       : {bundle['environment']['python_version']}")
    print(f"  Scikit-Learn Version : {bundle['environment']['scikit_learn_version']}")
    print(f"  Joblib Version       : {bundle['environment']['joblib_version']}")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    package_model_artifact()
