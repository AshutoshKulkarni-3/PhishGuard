# PhishGuard — ML Service

> Machine-learning component of the **PhishGuard** phishing-website detection system.  
> Stack: **Python 3.9 · Flask · scikit-learn · pandas · NumPy**

---

## Directory Layout

```
ml-service/
├── app.py              # Flask application entry point
├── requirements.txt    # Pinned Python dependencies
├── .gitignore          # VEnvs, caches, model artefacts, secrets
├── dataset/            # Raw & processed datasets (git-ignored)
├── training/           # Feature engineering & model training scripts
├── model/              # Serialised model files (git-ignored)
└── README.md           # This file
```

---

## Quick Start

### 1 · Create a Virtual Environment

```bash
# Inside ml-service/
python3 -m venv venv
```

### 2 · Activate the Virtual Environment

```bash
# macOS / Linux
source venv/bin/activate

# Windows (for reference)
venv\Scripts\activate
```

Your shell prompt will change to show `(venv)` when active.

### 3 · Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4 · Run the Flask Development Server

```bash
python app.py
```

The service will start on **http://127.0.0.1:5000**.  
Visit `http://127.0.0.1:5000/health` to confirm it is running.

### 5 · Verify Installed Packages

```bash
pip list
```

### 6 · Deactivate When Done

```bash
deactivate
```

---

## Environment Variables

Copy `.env.example` → `.env` and fill in values before running:

| Variable      | Description                        | Default       |
|---------------|------------------------------------|---------------|
| `FLASK_ENV`   | `development` or `production`      | `development` |
| `FLASK_PORT`  | Port the Flask server listens on   | `5000`        |
| `MODEL_PATH`  | Path to the serialised model file  | `model/`      |

---

## Roadmap

- [x] Task 1: Environment setup & project scaffolding
- [x] Task 2: Dataset preparation & cleaning (`training/prepare_dataset.py`)
- [x] Task 3: URL feature extraction (`training/feature_extraction.py`)
- [x] Task 4: Model training and 3-algorithm comparison (`training/train.py`)
- [x] Task 5: Performance analysis, 5-fold CV & model selection (`training/evaluate_and_select.py`)
- [x] Task 6: Packaging selected model for inference (`training/package_model.py`, `model/predictor.py`)
- [x] Task 7: Flask inference API (`app.py`, `training/test_api.py`)
- [x] Task 8: End-to-end ML testing (`tests/test_end_to_end.py`)
- [ ] Task 9: Integration with Java Spring Boot backend

---

## End-to-End Automated Testing (Task 8)

Run the unified 8-point automated test suite:

```bash
cd ml-service
source venv/bin/activate

# Using pytest:
pytest tests/test_end_to_end.py -v

# Or using standard unittest:
python -m unittest tests/test_end_to_end.py
```

---

## Java Spring Boot Integration Target (Task 9)

The upcoming Spring Boot application should connect to:
- **Base URL:** `http://127.0.0.1:5000` (or `http://localhost:5000`)
- **Health Probe:** `GET http://127.0.0.1:5000/health`
- **Inference Endpoint:** `POST http://127.0.0.1:5000/predict`
- **Request Header:** `Content-Type: application/json`
- **Request Body:** `{"url": "<target_url_string>"}`

---

## Running the Flask Inference API (Task 7)

### 1. Start the API Server
```bash
cd ml-service
source venv/bin/activate
python app.py
```
The service starts at **http://127.0.0.1:5000**.

### 2. Run API Integration Tests
```bash
python training/test_api.py
```

### 3. Test with `curl`

**Health Check:**
```bash
curl -X GET http://127.0.0.1:5000/health
```

**Predict Legitimate URL:**
```bash
curl -X POST http://127.0.0.1:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.google.com/search?q=cybersecurity"}'
```

**Predict Phishing Lure:**
```bash
curl -X POST http://127.0.0.1:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"url": "http://192.168.1.1/login.php?update=account&verify=true"}'
```

---

## Model Training & Inference Verification (Tasks 4, 5, 6)

1. **Train all 3 classifiers:**
   ```bash
   python training/train.py
   ```

2. **Run 5-Fold Cross-Validation, generate charts, and select model:**
   ```bash
   python training/evaluate_and_select.py
   ```

3. **Package the production bundle for inference:**
   ```bash
   python training/package_model.py
   ```

4. **Verify inference pipeline in an isolated process:**
   ```bash
   python training/test_inference.py
   ```

---

## Dependencies

| Package        | Version  | Purpose                        |
|----------------|----------|--------------------------------|
| numpy          | 1.26.4   | Numerical computing            |
| pandas         | 2.2.2    | Data manipulation              |
| scikit-learn   | 1.4.2    | ML algorithms & evaluation     |
| flask          | 3.0.3    | REST API framework             |
| flask-cors     | 4.0.1    | Cross-origin resource sharing  |
| joblib         | 1.4.2    | Model serialisation            |
| python-dotenv  | 1.0.1    | `.env` file loading            |
