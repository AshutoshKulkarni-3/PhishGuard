"""
PhishGuard — Production Inference Predictor
============================================
Lightweight inference engine that loads the serialized model artifact ONCE into
memory and performs real-time URL and feature-vector predictions.

Features:
  - Loads model bundle once upon initialization (Singleton / In-Memory pattern).
  - Guarantees exact feature ordering across training and inference.
  - Safe extraction from raw URL strings without network calls.
  - Returns classification label, probabilities, and extracted features.
  - Zero re-training during inference requests.
"""

import os
import sys
import time
from typing import Dict, Any, List, Union, Optional

import joblib
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from training.feature_extraction import FEATURE_NAMES, extract_features

DEFAULT_MODEL_PATH = os.path.join(SCRIPT_DIR, "phishguard_model.joblib")


class PhishGuardPredictor:
    """
    Production inference wrapper for PhishGuard.
    Loads the Joblib bundle once and provides thread-safe prediction methods.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        if not os.path.isfile(self.model_path):
            raise FileNotFoundError(
                f"Model artifact not found at: {self.model_path}. "
                "Please run `python training/package_model.py` or `python training/train.py`."
            )

        # ── Load model artifact once into memory ──
        t0 = time.time()
        self._bundle = joblib.load(self.model_path)
        self.load_time_sec = time.time() - t0

        if isinstance(self._bundle, dict) and "model" in self._bundle:
            self.model = self._bundle["model"]
            self.feature_names = self._bundle.get("feature_names", FEATURE_NAMES)
            self.label_mapping = self._bundle.get("label_mapping", {0: "legitimate", 1: "phishing"})
            self.decision_threshold = self._bundle.get("decision_threshold", 0.50)
            self.version_info = self._bundle.get("environment", {})
        else:
            # Direct estimator fallback
            self.model = self._bundle
            self.feature_names = FEATURE_NAMES
            self.label_mapping = {0: "legitimate", 1: "phishing"}
            self.decision_threshold = 0.50
            self.version_info = {}

    def predict_features(self, features: Union[Dict[str, Any], List[float], np.ndarray, pd.DataFrame]) -> Dict[str, Any]:
        """
        Run inference on a pre-extracted feature vector.

        Parameters
        ----------
        features : dict, list, ndarray, or pd.DataFrame
            Must contain values corresponding to the 23 features in `self.feature_names`.

        Returns
        -------
        dict
            Prediction output including predicted_class, label, and probabilities.
        """
        t0 = time.time()

        if isinstance(features, dict):
            # Verify and construct single-row DataFrame in exact column order
            row = [features.get(f, 0.0) for f in self.feature_names]
            df_input = pd.DataFrame([row], columns=self.feature_names)
        elif isinstance(features, pd.DataFrame):
            # Ensure columns match exact order
            missing = set(self.feature_names) - set(features.columns)
            if missing:
                raise ValueError(f"Input DataFrame is missing required features: {missing}")
            df_input = features[self.feature_names]
        elif isinstance(features, (list, np.ndarray)):
            arr = np.array(features)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            if arr.shape[1] != len(self.feature_names):
                raise ValueError(
                    f"Feature vector length mismatch: expected {len(self.feature_names)}, got {arr.shape[1]}"
                )
            df_input = pd.DataFrame(arr, columns=self.feature_names)
        else:
            raise TypeError(f"Unsupported features type: {type(features)}")

        # Predict probabilities
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(df_input)[0]
            # classes_ are usually [0, 1]
            p_legit = float(probs[0])
            p_phish = float(probs[1]) if len(probs) > 1 else float(1.0 - p_legit)
        else:
            pred_raw = int(self.model.predict(df_input)[0])
            p_phish = 1.0 if pred_raw == 1 else 0.0
            p_legit = 1.0 - p_phish

        # Apply threshold
        predicted_class = 1 if p_phish >= self.decision_threshold else 0
        predicted_label = self.label_mapping.get(predicted_class, "phishing" if predicted_class == 1 else "legitimate")
        confidence = p_phish if predicted_class == 1 else p_legit

        elapsed_ms = (time.time() - t0) * 1000.0

        return {
            "predicted_class": int(predicted_class),
            "label": predicted_label,
            "is_phishing": bool(predicted_class == 1),
            "confidence": round(float(confidence), 4),
            "probabilities": {
                "legitimate": round(float(p_legit), 4),
                "phishing": round(float(p_phish), 4)
            },
            "decision_threshold": self.decision_threshold,
            "inference_time_ms": round(float(elapsed_ms), 3)
        }

    def predict_url(self, url: str) -> Dict[str, Any]:
        """
        Run end-to-end inference on a raw URL string:
        1. Safely extract 23 lexical/structural features without network I/O.
        2. Run inference through the trained model.
        3. Return structured prediction results.
        """
        t0 = time.time()
        # 1. Feature extraction
        feats = extract_features(url)
        # 2. Predict
        res = self.predict_features(feats)
        # 3. Augment with URL and feature dict
        res["url"] = url
        res["features"] = feats
        res["total_time_ms"] = round((time.time() - t0) * 1000.0, 3)
        return res


# Global singleton cache
_PREDICTOR_INSTANCE: Optional[PhishGuardPredictor] = None


def get_predictor(model_path: Optional[str] = None) -> PhishGuardPredictor:
    """
    Get or create a cached instance of PhishGuardPredictor.
    Guarantees the model is loaded into memory only ONCE per process.
    """
    global _PREDICTOR_INSTANCE
    if _PREDICTOR_INSTANCE is None:
        _PREDICTOR_INSTANCE = PhishGuardPredictor(model_path=model_path)
    return _PREDICTOR_INSTANCE
