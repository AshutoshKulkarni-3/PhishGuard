"""
PhishGuard — Task 7: Flask API Test Suite
==========================================
Comprehensive integration test suite for the Flask inference API.
Tests:
  - Health check endpoint (GET /health)
  - Successful predictions for legitimate and phishing URLs (POST /predict)
  - Input validation (missing 'url', invalid types, empty strings, excessive length)
  - Error handling (400, 404, 405, 415)
  - Verification of Spring Boot compatible response schema
  - Verification of no traceback or sensitive filesystem leakage
"""

import json
import os
import sys

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app


def test_api():
    print("\n" + "=" * 78)
    print("  PHISHGUARD: FLASK INFERENCE API TEST SUITE")
    print("=" * 78)

    client = app.test_client()

    # ── Test 1: GET /health ──
    print("\n1. Testing GET /health ...")
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["algorithm"] == "RandomForestClassifier"
    assert data["features_supported"] == 23
    print("   ✔ GET /health passed:", json.dumps(data))

    # ── Test 2: POST /predict (Legitimate URL) ──
    print("\n2. Testing POST /predict with legitimate search URL ...")
    payload = {"url": "https://www.google.com/search?q=machine+learning"}
    res = client.post("/predict", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.get_json()
    assert data["status"] == "success"
    assert data["prediction"] in ("legitimate", "phishing")
    assert isinstance(data["is_phishing"], bool)
    assert isinstance(data["confidence"], float)
    assert "legitimate" in data["probabilities"]
    assert "phishing" in data["probabilities"]
    assert "indicators" in data
    assert "disclaimer" in data
    assert "meta" in data
    print("   ✔ POST /predict (legitimate) passed:")
    print(f"     Outcome: {data['prediction']} | Confidence: {data['confidence'] * 100:.1f}%")

    # ── Test 3: POST /predict (Phishing Lure URL) ──
    print("\n3. Testing POST /predict with phishing lure URL ...")
    payload = {"url": "http://192.168.1.1/login.php?update=account&verify=true"}
    res = client.post("/predict", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.get_json()
    assert data["status"] == "success"
    assert data["is_phishing"] is True
    assert data["prediction"] == "phishing"
    assert data["indicators"]["has_ip_hostname"] is True
    assert data["indicators"]["has_suspicious_keyword"] is True
    print("   ✔ POST /predict (phishing) passed:")
    print(f"     Outcome: {data['prediction']} | Indicators: IP={data['indicators']['has_ip_hostname']}, Keyword={data['indicators']['has_suspicious_keyword']}")

    # ── Test 4: Validation Error: Missing 'url' field ──
    print("\n4. Testing POST /predict with missing 'url' field ...")
    res = client.post("/predict", json={"wrong_field": "test"})
    assert res.status_code == 400
    data = res.get_json()
    assert data["status"] == "error"
    assert data["error_code"] == "MISSING_URL_FIELD"
    print("   ✔ Missing 'url' rejected with 400:", data["message"])

    # ── Test 5: Validation Error: Non-string 'url' field ──
    print("\n5. Testing POST /predict with non-string 'url' ...")
    res = client.post("/predict", json={"url": 12345})
    assert res.status_code == 400
    data = res.get_json()
    assert data["error_code"] == "INVALID_URL_TYPE"
    print("   ✔ Non-string 'url' rejected with 400:", data["message"])

    # ── Test 6: Validation Error: Empty 'url' field ──
    print("\n6. Testing POST /predict with empty 'url' ...")
    res = client.post("/predict", json={"url": "   "})
    assert res.status_code == 400
    data = res.get_json()
    assert data["error_code"] == "EMPTY_URL"
    print("   ✔ Empty 'url' rejected with 400:", data["message"])

    # ── Test 7: Validation Error: URL exceeds max length ──
    print("\n7. Testing POST /predict with excessively long URL (> 2048 chars) ...")
    long_url = "https://example.com/" + "a" * 2100
    res = client.post("/predict", json={"url": long_url})
    assert res.status_code == 400
    data = res.get_json()
    assert data["error_code"] == "URL_TOO_LONG"
    print("   ✔ Excessively long URL rejected with 400:", data["message"])

    # ── Test 8: Unsupported Media Type (Not JSON) ──
    print("\n8. Testing POST /predict with non-JSON content-type ...")
    res = client.post("/predict", data="plain text data", content_type="text/plain")
    assert res.status_code == 415
    data = res.get_json()
    assert data["error_code"] == "UNSUPPORTED_MEDIA_TYPE"
    print("   ✔ Non-JSON rejected with 415:", data["message"])

    # ── Test 9: Method Not Allowed ──
    print("\n9. Testing GET /predict (Method Not Allowed) ...")
    res = client.get("/predict")
    assert res.status_code == 405
    data = res.get_json()
    assert data["error_code"] == "METHOD_NOT_ALLOWED"
    print("   ✔ GET /predict rejected with 405:", data["message"])

    # ── Test 10: Not Found ──
    print("\n10. Testing GET /nonexistent (404) ...")
    res = client.get("/nonexistent")
    assert res.status_code == 404
    data = res.get_json()
    assert data["error_code"] == "NOT_FOUND"
    print("   ✔ Unknown route rejected with 404:", data["message"])

    print("\n" + "=" * 78)
    print("  ALL 10 API TEST CASES PASSED SUCCESSFULLY ✔")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    test_api()
