# PhishGuard — ML-Powered Phishing Website Detection System

> A multi-tier cybersecurity application combining a **Python Scikit-Learn Machine Learning Service** with an **Enterprise Java Spring Boot & Hibernate Backend**.

---

## Architecture Overview

```
PhishGuard/
├── ml-service/          # Python 3.9 · Flask · Scikit-learn · Random Forest Classifier
│   ├── app.py           # REST Inference API (GET /health, POST /predict)
│   ├── dataset/         # Kaggle 507k URL benchmark dataset splits (train.csv, test.csv)
│   ├── model/           # Serialized Joblib model bundle & in-memory predictor
│   ├── results/         # Evaluation benchmarks, 5-fold CV reports, comparison charts
│   ├── tests/           # 8-point automated E2E test suite (pytest / unittest)
│   └── training/        # Feature engineering, training, and packaging pipelines
│
└── spring-backend/      # Java 21 · Spring Boot 3.3.4 · Spring Data JPA · MySQL · Thymeleaf
    ├── pom.xml          # Maven build descriptor
    └── src/
        ├── main/        # Spring Boot application, configuration, controllers
        └── test/        # Unit & integration tests (isolated H2 test profile)
```

---

## Service Coordinates & Ports

| Component | Technology | Default Port | Primary URL / Probe |
| :--- | :--- | :---: | :--- |
| **ML Inference Service** | Python Flask | `5000` | `http://127.0.0.1:5000/health` |
| **Web & API Backend** | Java Spring Boot | `8080` | `http://127.0.0.1:8080/` |

---

## Quick Start on macOS

### 1. Launch the ML Inference Service
```bash
cd ml-service
source venv/bin/activate
python app.py
```

### 2. Launch the Spring Boot Backend
```bash
cd spring-backend
mvn spring-boot:run
```
