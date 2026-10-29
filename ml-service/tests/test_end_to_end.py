"""
PhishGuard — End-to-End System Integration Test Suite
======================================================
Automated test suite verifying the complete machine learning lifecycle:
  1. Dataset preparation and split file integrity
  2. URL feature extraction schema, consistency, and edge cases
  3. Training and evaluation results across all 3 classifiers
  4. Model artifact persistence, loading, and metadata schema
  5. Flask REST API startup and GET /health readiness probe
  6. POST /predict execution and Spring Boot JSON response contract
  7. Input validation, malicious/oversized inputs, and HTTP error codes
  8. In-memory model persistence (zero retraining on incoming requests)

Run with:
  cd ml-service
  source venv/bin/activate
  pytest tests/test_end_to_end.py -v
  # or standard library:
  python -m unittest tests/test_end_to_end.py
"""

import json
import math
import os
import sys
import unittest

import joblib
import numpy as np
import pandas as pd

# ── Ensure project root is in sys.path ───────────────────────────────────────
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from model.predictor import PhishGuardPredictor, get_predictor
from training.feature_extraction import FEATURE_NAMES, extract_features, extract_features_df


class TestPhishGuardEndToEnd(unittest.TestCase):
    """Full End-to-End Test Suite for PhishGuard ML Service."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = PROJECT_ROOT
        cls.dataset_dir = os.path.join(PROJECT_ROOT, "dataset")
        cls.results_dir = os.path.join(PROJECT_ROOT, "results")
        cls.model_dir = os.path.join(PROJECT_ROOT, "model")

        cls.client = app.test_client()
        cls.client.testing = True

    # ══════════════════════════════════════════════════════════════════════════
    # 1. Dataset Preparation Runs Successfully
    # ══════════════════════════════════════════════════════════════════════════
    def test_01_dataset_preparation(self):
        """Verify train, test, and cleaned dataset files exist and meet schema requirements."""
        train_csv = os.path.join(self.dataset_dir, "train.csv")
        test_csv = os.path.join(self.dataset_dir, "test.csv")
        cleaned_csv = os.path.join(self.dataset_dir, "cleaned.csv")

        self.assertTrue(os.path.isfile(train_csv), "train.csv missing from dataset/")
        self.assertTrue(os.path.isfile(test_csv), "test.csv missing from dataset/")
        self.assertTrue(os.path.isfile(cleaned_csv), "cleaned.csv missing from dataset/")

        # Verify dataset row counts and columns
        df_train = pd.read_csv(train_csv, nrows=100)
        df_test = pd.read_csv(test_csv, nrows=100)

        self.assertListEqual(list(df_train.columns), ["url", "label"])
        self.assertListEqual(list(df_test.columns), ["url", "label"])

        # Check parsed CSV row counts
        n_train = len(pd.read_csv(train_csv))
        n_test = len(pd.read_csv(test_csv))

        self.assertEqual(n_train, 405752, f"Expected 405,752 train rows, found {n_train}")
        self.assertEqual(n_test, 101439, f"Expected 101,439 test rows, found {n_test}")

    # ══════════════════════════════════════════════════════════════════════════
    # 2. Feature Extraction Produces Expected Features
    # ══════════════════════════════════════════════════════════════════════════
    def test_02_feature_extraction(self):
        """Verify feature extraction extracts 23 features consistently and safely."""
        self.assertEqual(len(FEATURE_NAMES), 23, "FEATURE_NAMES must have exactly 23 features")

        # Test single URL extraction
        test_url = "http://192.168.1.1/login.php?update=account&verify=true"
        feats = extract_features(test_url)

        self.assertIsInstance(feats, dict)
        self.assertListEqual(list(feats.keys()), FEATURE_NAMES)
        self.assertEqual(feats["has_ip_hostname"], 1)
        self.assertEqual(feats["has_suspicious_keyword"], 1)
        self.assertEqual(feats["is_https"], 0)
        self.assertEqual(feats["n_query_params"], 2)

        # Test empty URL returns zero-vector
        empty_feats = extract_features("")
        self.assertEqual(sum(empty_feats.values()), 0)

        # Test batch extraction
        urls = ["https://example.com", "http://test.org/auth"]
        df_batch = extract_features_df(urls)
        self.assertEqual(df_batch.shape, (2, 23))
        self.assertListEqual(list(df_batch.columns), FEATURE_NAMES)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. All Three Algorithms Trained and Evaluated
    # ══════════════════════════════════════════════════════════════════════════
    def test_03_three_algorithms_trained_and_evaluated(self):
        """Verify all three models have real evaluation metrics and cross-validation."""
        comp_json = os.path.join(self.results_dir, "model_comparison.json")
        cv_json = os.path.join(self.results_dir, "cross_validation_results.json")

        self.assertTrue(os.path.isfile(comp_json), "model_comparison.json missing")
        self.assertTrue(os.path.isfile(cv_json), "cross_validation_results.json missing")

        with open(comp_json, "r") as f:
            results = json.load(f)

        expected_models = ["Logistic Regression", "Decision Tree", "Random Forest"]
        for m in expected_models:
            self.assertIn(m, results, f"Model {m} not found in evaluation results")
            metrics = results[m]
            self.assertIn("accuracy", metrics)
            self.assertIn("precision", metrics)
            self.assertIn("recall", metrics)
            self.assertIn("f1_score", metrics)
            self.assertIn("confusion_matrix", metrics)

            # Ensure non-trivial realistic scores
            self.assertGreater(metrics["accuracy"], 0.70)
            self.assertGreater(metrics["precision"], 0.70)

        # Confirm Random Forest had top F1-Score
        self.assertGreaterEqual(
            results["Random Forest"]["f1_score"],
            results["Decision Tree"]["f1_score"]
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 4. Selected Model Can Be Saved and Loaded
    # ══════════════════════════════════════════════════════════════════════════
    def test_04_selected_model_saved_and_loaded(self):
        """Verify model bundle exists, loads cleanly, and holds metadata."""
        bundle_path = os.path.join(self.model_dir, "phishguard_model.joblib")
        meta_path = os.path.join(self.model_dir, "metadata.json")

        self.assertTrue(os.path.isfile(bundle_path), "phishguard_model.joblib missing")
        self.assertTrue(os.path.isfile(meta_path), "metadata.json missing")

        # Load bundle in isolation
        bundle = joblib.load(bundle_path)
        self.assertIsInstance(bundle, dict)
        self.assertIn("model", bundle)
        self.assertIn("feature_names", bundle)
        self.assertIn("decision_threshold", bundle)
        self.assertIn("environment", bundle)

        predictor = PhishGuardPredictor(bundle_path)
        self.assertEqual(len(predictor.feature_names), 23)
        self.assertEqual(predictor.decision_threshold, 0.50)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. Flask API Starts and Responds to Health Endpoint
    # ══════════════════════════════════════════════════════════════════════════
    def test_05_flask_api_health_endpoint(self):
        """Verify GET /health returns 200 OK and readiness status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["model_loaded"])
        self.assertEqual(data["features_supported"], 23)
        self.assertEqual(data["version"], "1.0.0")

    # ══════════════════════════════════════════════════════════════════════════
    # 6. Valid URL Requests Receive Documented JSON Format
    # ══════════════════════════════════════════════════════════════════════════
    def test_06_flask_api_valid_predictions(self):
        """Verify POST /predict returns the complete Spring Boot compatible schema."""
        test_payloads = [
            ("https://www.google.com/search?q=machine+learning", False, "legitimate"),
            ("https://www.google.com", False, "legitimate"),
            ("https://github.com", False, "legitimate"),
            ("http://192.168.1.1/login.php?update=account&verify=true", True, "phishing")
        ]

        for url, expected_is_phish, expected_label in test_payloads:
            response = self.client.post("/predict", json={"url": url})
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            # Assert contract keys
            for key in ["status", "url", "prediction", "is_phishing", "confidence",
                        "confidence_type", "probabilities", "indicators", "meta", "disclaimer"]:
                self.assertIn(key, data, f"Missing key '{key}' in prediction response")

            self.assertEqual(data["status"], "success")
            self.assertEqual(data["url"], url)
            self.assertEqual(data["prediction"], expected_label)
            self.assertEqual(data["is_phishing"], expected_is_phish)
            self.assertEqual(data["confidence_type"], "raw_ensemble_vote_probability")

            # Check probabilities normalization
            p_legit = data["probabilities"]["legitimate"]
            p_phish = data["probabilities"]["phishing"]
            self.assertTrue(math.isclose(p_legit + p_phish, 1.0, abs_tol=1e-3))

            # Check indicators
            self.assertIn("has_ip_hostname", data["indicators"])
            self.assertIn("has_suspicious_keyword", data["indicators"])
            self.assertIn("is_https", data["indicators"])

    # ══════════════════════════════════════════════════════════════════════════
    # 7. Robust Error Handling & Input Validation
    # ══════════════════════════════════════════════════════════════════════════
    def test_07_input_validation_and_errors(self):
        """Verify API handles missing, invalid, and oversized inputs with proper HTTP codes."""
        # 400: Missing 'url' field
        res = self.client.post("/predict", json={"wrong_key": "http://test.com"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error_code"], "MISSING_URL_FIELD")

        # 400: Non-string 'url' field
        res = self.client.post("/predict", json={"url": 12345})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error_code"], "INVALID_URL_TYPE")

        # 400: Empty 'url' field
        res = self.client.post("/predict", json={"url": "   "})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error_code"], "EMPTY_URL")

        # 400: Oversized URL (> 2048 chars)
        res = self.client.post("/predict", json={"url": "https://example.com/" + "a" * 2100})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error_code"], "URL_TOO_LONG")

        # 415: Non-JSON body
        res = self.client.post("/predict", data="not json", content_type="text/plain")
        self.assertEqual(res.status_code, 415)
        self.assertEqual(res.get_json()["error_code"], "UNSUPPORTED_MEDIA_TYPE")

        # 405: Method Not Allowed
        res = self.client.get("/predict")
        self.assertEqual(res.status_code, 405)
        self.assertEqual(res.get_json()["error_code"], "METHOD_NOT_ALLOWED")

        # 404: Not Found
        res = self.client.get("/nonexistent_endpoint")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.get_json()["error_code"], "NOT_FOUND")

    # ══════════════════════════════════════════════════════════════════════════
    # 8. API Uses Saved Model Without Retraining
    # ══════════════════════════════════════════════════════════════════════════
    def test_08_api_uses_saved_model_without_retraining(self):
        """Verify the model estimator identity in memory remains strictly constant across requests."""
        predictor = get_predictor()
        initial_model_id = id(predictor.model)

        # Run 5 sequential prediction requests
        for i in range(5):
            res = self.client.post("/predict", json={"url": f"https://example{i}.com"})
            self.assertEqual(res.status_code, 200)

            current_model_id = id(predictor.model)
            self.assertEqual(
                initial_model_id,
                current_model_id,
                "Model was reloaded or re-instantiated between requests!"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
