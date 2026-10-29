"""
PhishGuard — ML Inference Service (Flask REST API)
===================================================
Production-grade Flask microservice providing real-time phishing URL detection
for PhishGuard. Designed for integration with the Java Spring Boot backend.

Endpoints:
  - GET  /health   : Health-check and model readiness probe.
  - POST /predict  : Predict whether a submitted URL is phishing or legitimate.

Design Guarantees:
  1. Eager Model Loading: The Joblib model bundle is loaded ONCE into memory at server
     startup, ensuring zero training or unpickling latency on incoming HTTP requests.
  2. Offline Lexical Analysis: No network requests, DNS queries, or DOM execution are
     ever made for submitted URLs.
  3. Consistent Pipeline: Strictly applies the exact 23 lexical/structural features
     used during model training and evaluation.
  4. Spring Boot Friendly Contract: Returns a predictable, typed JSON DTO schema.
  5. Security & Sanitization: Generic error messages prevent leaking internal stack
     traces, filesystem paths, or library versions.
  6. Scientific Disclaimer: Explicitly documents probability source and caveats.
"""

import logging
import os
import sys
import time
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Ensure project root (ml-service) is on sys.path ──────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Load environment variables from .env if present
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

from model.predictor import get_predictor

# ── Logging Configuration ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("phishguard-api")

# ── Application Factory & Configuration ─────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Enable cross-origin requests for dev/frontend/Spring Boot integration

HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
PORT = int(os.environ.get("FLASK_PORT", 5050))
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "t")

MAX_URL_LENGTH = 2048  # RFC standard practical URL limit to guard against ReDoS/memory exhaustion

# ── Eager Model Initialization (Loaded ONCE at server startup) ──────────────
logger.info("Initializing PhishGuard predictor and loading model bundle into memory...")
try:
    predictor = get_predictor()
    logger.info(
        "Model successfully loaded: %s (Feature count: %d, Load time: %.3fs)",
        predictor.model.__class__.__name__,
        len(predictor.feature_names),
        predictor.load_time_sec,
    )
except Exception as e:
    logger.critical("Failed to load model artifact at startup: %s", str(e), exc_info=True)
    predictor = None


# ══════════════════════════════════════════════════════════════════════════════
# Error Handlers (Clean JSON, zero internal filesystem leaks)
# ══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "status": "error",
        "error_code": "BAD_REQUEST",
        "message": getattr(error, "description", "The request body is invalid or malformed.")
    }), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "error_code": "NOT_FOUND",
        "message": "The requested resource was not found on this server."
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "status": "error",
        "error_code": "METHOD_NOT_ALLOWED",
        "message": f"HTTP {request.method} method is not allowed for this endpoint."
    }), 405


@app.errorhandler(415)
def unsupported_media_type(error):
    return jsonify({
        "status": "error",
        "error_code": "UNSUPPORTED_MEDIA_TYPE",
        "message": "Unsupported Media Type. Request header must specify Content-Type: application/json."
    }), 415


@app.errorhandler(500)
def internal_server_error(error):
    logger.error("Internal Server Error: %s", str(error), exc_info=True)
    return jsonify({
        "status": "error",
        "error_code": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred while processing the request. Please try again later."
    }), 500


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health_check():
    """
    Service health and readiness probe.
    Returns status: 'healthy' if service is up and model is loaded in memory.
    """
    model_ready = predictor is not None and predictor.model is not None
    return jsonify({
        "status": "healthy" if model_ready else "degraded",
        "service": "PhishGuard ML Inference Service",
        "model_loaded": model_ready,
        "algorithm": predictor.model.__class__.__name__ if model_ready else None,
        "features_supported": len(predictor.feature_names) if model_ready else 0,
        "version": "1.0.0"
    }), 200 if model_ready else 503


@app.route("/predict", methods=["POST"])
def predict():
    """
    POST /predict
    Analyzes a URL using purely offline lexical/structural feature extraction
    and returns model classification, confidence, and suspicious indicator flags.

    Request JSON Contract:
      {
        "url": "https://example.com/login"
      }
    """
    if predictor is None:
        logger.error("Predict endpoint invoked but model is not initialized.")
        return jsonify({
            "status": "error",
            "error_code": "SERVICE_UNAVAILABLE",
            "message": "Inference model is currently unavailable."
        }), 503

    # 1. Enforce JSON Content-Type
    if not request.is_json:
        return jsonify({
            "status": "error",
            "error_code": "UNSUPPORTED_MEDIA_TYPE",
            "message": "Request payload must be formatted as JSON with Content-Type: application/json."
        }), 415

    # 2. Extract and parse body
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "error_code": "INVALID_PAYLOAD",
            "message": "Request body must be a valid JSON object."
        }), 400

    raw_url = data.get("url")

    # 3. Validate URL input presence and type
    if raw_url is None:
        return jsonify({
            "status": "error",
            "error_code": "MISSING_URL_FIELD",
            "message": "Missing required field: 'url'."
        }), 400

    if not isinstance(raw_url, str):
        return jsonify({
            "status": "error",
            "error_code": "INVALID_URL_TYPE",
            "message": "Field 'url' must be a string."
        }), 400

    url = raw_url.strip()
    if not url:
        return jsonify({
            "status": "error",
            "error_code": "EMPTY_URL",
            "message": "Field 'url' cannot be empty or whitespace only."
        }), 400

    if len(url) > MAX_URL_LENGTH:
        return jsonify({
            "status": "error",
            "error_code": "URL_TOO_LONG",
            "message": f"URL length ({len(url)}) exceeds maximum permitted length of {MAX_URL_LENGTH} characters."
        }), 400

    # 4. Perform Safe Offline Inference
    t0 = time.time()
    try:
        result = predictor.predict_url(url)
    except Exception as e:
        logger.error("Inference execution failure on URL: %s", str(e), exc_info=True)
        return jsonify({
            "status": "error",
            "error_code": "INFERENCE_ERROR",
            "message": "An error occurred during feature extraction or model inference."
        }), 500

    duration_ms = (time.time() - t0) * 1000.0

    # 5. Extract high-signal indicators for Spring Boot UI / Alerts
    features = result.get("features", {})
    indicators = {
        "has_ip": bool(features.get("has_ip_hostname", 0) == 1),
        "has_ip_hostname": bool(features.get("has_ip_hostname", 0) == 1),
        "has_at_symbol": bool(features.get("has_at_symbol", 0) == 1),
        "has_suspicious_keyword": bool(features.get("has_suspicious_keyword", 0) == 1),
        "is_https": bool(features.get("is_https", 0) == 1),
        "has_port": bool(features.get("has_port", 0) == 1),
        "domain_has_hyphen": bool(features.get("domain_has_hyphen", 0) == 1),
        "has_double_slash_in_path": bool(features.get("has_double_slash_in_path", 0) == 1),
        "subdomain_count": int(features.get("n_subdomains", 0)),
        "n_subdomains": int(features.get("n_subdomains", 0)),
        "url_length": int(features.get("url_length", 0)),
        "url_entropy": float(features.get("url_entropy", 0.0)),
        "path_token_count": int(features.get("path_token_count", 0)),
    }

    # 6. Assemble Spring Boot friendly JSON Response
    response_payload: Dict[str, Any] = {
        "status": "success",
        "url": url,
        "prediction": result["label"],          # "phishing" or "legitimate"
        "is_phishing": result["is_phishing"],    # boolean flag for easy if-statements
        "confidence": result["confidence"],      # float between 0.0 and 1.0
        "confidence_type": "raw_ensemble_vote_probability",
        "probabilities": {
            "legitimate": result["probabilities"]["legitimate"],
            "phishing": result["probabilities"]["phishing"]
        },
        "indicators": indicators,
        "meta": {
            "model_name": "Random Forest Classifier",
            "version": "1.0.0",
            "threshold": result["decision_threshold"],
            "features_extracted": len(features),
            "inference_time_ms": round(duration_ms, 2)
        },
        "disclaimer": (
            "Prediction is based strictly on offline lexical and structural URL analysis "
            "without visiting the website or executing page content. A 'legitimate' prediction "
            "does not guarantee safety."
        )
    }

    return jsonify(response_payload), 200


# ══════════════════════════════════════════════════════════════════════════════
# Local Development Server Runner
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("Starting PhishGuard ML API development server on http://%s:%d", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=DEBUG)
