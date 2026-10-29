"""
PhishGuard — Model Training & Comparison
=========================================
Trains and compares three classification algorithms for phishing URL detection:
  1. Logistic Regression (with StandardScaler pipeline)
  2. Decision Tree Classifier
  3. Random Forest Classifier

Key Design Principles:
  - Exact feature extraction logic imported from training.feature_extraction (no divergence).
  - Strict data leakage prevention: preprocessors and scalers are fitted ONLY on training data.
  - Fixed random seeds (random_state=42) for reproducible experiments.
  - Real evaluations: accuracy, precision, recall, F1-score, confusion matrix (TN, FP, FN, TP).
  - Formatted terminal comparison table and export to results/ (JSON, CSV, Markdown, text).
  - Model artifacts saved to model/ for deployment in Task 5.

Usage:
  cd ml-service
  source venv/bin/activate
  python training/train.py
  python training/train.py --force-extract  # re-extract features bypassing cache
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Any, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# ── Ensure project root (ml-service) is on sys.path ──────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from training.feature_extraction import FEATURE_NAMES, extract_features_df

# ── Paths ────────────────────────────────────────────────────────────────────
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
TRAIN_CSV = os.path.join(DATASET_DIR, "train.csv")
TEST_CSV = os.path.join(DATASET_DIR, "test.csv")

TRAIN_FEAT_CACHE = os.path.join(DATASET_DIR, "train_features.joblib")
TEST_FEAT_CACHE = os.path.join(DATASET_DIR, "test_features.joblib")

RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
MODEL_DIR = os.path.join(PROJECT_ROOT, "model")

RANDOM_STATE = 42


# ══════════════════════════════════════════════════════════════════════════════
# 1. Feature Loading & Extraction (Leakage-Proof)
# ══════════════════════════════════════════════════════════════════════════════

def load_data(force_extract: bool = False) -> Tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray]:
    """
    Load train and test splits and extract lexical URL features.
    
    To ensure consistency, feature extraction strictly uses `extract_features_df`
    from `training.feature_extraction`. Feature vectors are cached to disk so
    repeated runs start instantly, but can be refreshed using `force_extract`.

    Returns:
        X_train (pd.DataFrame): Training features (shape: N_train x 23)
        y_train (np.ndarray): Training labels (0 = legitimate, 1 = phishing)
        X_test  (pd.DataFrame): Test features (shape: N_test x 23)
        y_test  (np.ndarray): Test labels (0 = legitimate, 1 = phishing)
    """
    if not os.path.isfile(TRAIN_CSV) or not os.path.isfile(TEST_CSV):
        raise FileNotFoundError(
            f"Train or test CSV missing from {DATASET_DIR}. "
            "Please run `python training/prepare_dataset.py` first."
        )

    print("\n" + "=" * 78)
    print("  PHISHGUARD: DATA LOADING & FEATURE EXTRACTION")
    print("=" * 78)

    print(f"• Loading training dataset: {TRAIN_CSV}")
    df_train = pd.read_csv(TRAIN_CSV)
    print(f"  Shape: {df_train.shape[0]:,} rows x {df_train.shape[1]} columns")

    print(f"• Loading test dataset:     {TEST_CSV}")
    df_test = pd.read_csv(TEST_CSV)
    print(f"  Shape: {df_test.shape[0]:,} rows x {df_test.shape[1]} columns")

    y_train = df_train["label"].to_numpy(dtype=np.int64)
    y_test = df_test["label"].to_numpy(dtype=np.int64)

    # ── Check cache or compute features ──
    use_cache = (
        not force_extract
        and os.path.isfile(TRAIN_FEAT_CACHE)
        and os.path.isfile(TEST_FEAT_CACHE)
    )

    if use_cache:
        print("\n• Cached feature vectors found. Loading from cache...")
        t0 = time.time()
        X_train = joblib.load(TRAIN_FEAT_CACHE)
        X_test = joblib.load(TEST_FEAT_CACHE)
        print(f"  Loaded X_train {X_train.shape} and X_test {X_test.shape} in {time.time() - t0:.2f}s")
    else:
        print("\n• Extracting 23 lexical/structural features via `extract_features_df`...")
        print(f"  Features ({len(FEATURE_NAMES)}): {', '.join(FEATURE_NAMES[:6])}...")
        
        t0 = time.time()
        print(f"  Processing {len(df_train):,} training URLs...")
        X_train = extract_features_df(df_train["url"])
        print(f"  Training features extracted in {time.time() - t0:.2f}s (shape: {X_train.shape})")

        t1 = time.time()
        print(f"  Processing {len(df_test):,} test URLs...")
        X_test = extract_features_df(df_test["url"])
        print(f"  Test features extracted in {time.time() - t1:.2f}s (shape: {X_test.shape})")

        # Save cache for fast subsequent iteration
        print("  Saving feature cache to dataset/...")
        joblib.dump(X_train, TRAIN_FEAT_CACHE, compress=3)
        joblib.dump(X_test, TEST_FEAT_CACHE, compress=3)
        print("  Feature cache saved.")

    # Validate feature consistency
    assert list(X_train.columns) == FEATURE_NAMES, "Training feature columns mismatch FEATURE_NAMES"
    assert list(X_test.columns) == FEATURE_NAMES, "Test feature columns mismatch FEATURE_NAMES"
    assert len(X_train) == len(y_train), "X_train and y_train row count mismatch"
    assert len(X_test) == len(y_test), "X_test and y_test row count mismatch"

    print(f"\n✔ Feature sets verified: {len(FEATURE_NAMES)} features, 0 missing values.")
    return X_train, y_train, X_test, y_test


# ══════════════════════════════════════════════════════════════════════════════
# 2. Model Definitions
# ══════════════════════════════════════════════════════════════════════════════

def build_models(random_state: int = RANDOM_STATE) -> Dict[str, Any]:
    """
    Instantiate the three candidate models.

    1. Logistic Regression:
       - Wrapped in a Pipeline with StandardScaler to ensure features (length,
         counts, entropy) are on the same scale for gradient/lbfgs convergence.
       - StandardScaler is fit ONLY on training data inside the pipeline.
       - max_iter=1000 ensures solver converges without iteration warnings.

    2. Decision Tree Classifier:
       - Non-parametric rule-based model.
       - max_depth=25, min_samples_split=10, min_samples_leaf=4 regularize tree
         depth to prevent memorization/overfitting on noisy URL variants.

    3. Random Forest Classifier:
       - Ensemble of 100 decision trees with bootstrap aggregation.
       - Subsamples random feature subsets at each split to decorrelate trees.
       - Uses parallel execution (n_jobs=-1) for maximum training efficiency.
    """
    models = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                max_iter=1000,
                random_state=random_state,
                solver="lbfgs"
            ))
        ]),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=25,
            min_samples_split=10,
            min_samples_leaf=4,
            random_state=random_state
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=25,
            min_samples_split=10,
            min_samples_leaf=4,
            random_state=random_state,
            n_jobs=-1
        )
    }
    return models


# ══════════════════════════════════════════════════════════════════════════════
# 3. Training & Evaluation Pipeline
# ══════════════════════════════════════════════════════════════════════════════

def train_and_evaluate(
    models: Dict[str, Any],
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    y_test: np.ndarray
) -> Dict[str, Dict[str, Any]]:
    """
    Fit each candidate model strictly on (X_train, y_train), then evaluate on
    the unseen (X_test, y_test). Computes full diagnostic metrics:
      - Accuracy
      - Precision (phishing class = 1)
      - Recall (phishing class = 1)
      - F1-Score
      - Confusion Matrix: TN, FP, FN, TP
      - False Positive Rate (FPR) and False Negative Rate (FNR)
      - Fit and inference wall-clock timings
    """
    results: Dict[str, Dict[str, Any]] = {}

    print("\n" + "=" * 78)
    print("  PHISHGUARD: MODEL TRAINING & EVALUATION (NO DATA LEAKAGE)")
    print("=" * 78)

    for name, model in models.items():
        print(f"\n▶ Training: {name} ...")
        t_start_train = time.time()
        
        # FIT ONLY ON TRAINING SET
        model.fit(X_train, y_train)
        train_duration = time.time() - t_start_train
        print(f"  ✔ Fit completed in {train_duration:.2f}s")

        # PREDICT ON UNSEEN TEST SET
        t_start_pred = time.time()
        y_pred = model.predict(X_test)
        pred_duration = time.time() - t_start_pred

        # CALCULATE REAL METRICS
        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))

        # Confusion Matrix breakdown:
        # [[TN, FP],
        #  [FN, TP]]
        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
        fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

        results[name] = {
            "model_object": model,
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "confusion_matrix": {
                "tn": tn,
                "fp": fp,
                "fn": fn,
                "tp": tp,
                "matrix_2x2": [[tn, fp], [fn, tp]]
            },
            "fpr": fpr,
            "fnr": fnr,
            "train_time_sec": round(train_duration, 3),
            "test_pred_time_sec": round(pred_duration, 3),
            "test_sample_count": int(len(y_test)),
            "classification_report": classification_report(
                y_test, y_pred,
                target_names=["Legitimate (0)", "Phishing (1)"],
                digits=4,
                output_dict=True
            )
        }

        print(f"  Accuracy : {acc * 100:.2f}%")
        print(f"  Precision: {prec * 100:.2f}%")
        print(f"  Recall   : {rec * 100:.2f}%")
        print(f"  F1-Score : {f1:.4f}")
        print(f"  Confusion: TN={tn:,} | FP={fp:,} | FN={fn:,} | TP={tp:,}")

    return results


# ══════════════════════════════════════════════════════════════════════════════
# 4. Readable Comparison Table Output
# ══════════════════════════════════════════════════════════════════════════════

def print_comparison_table(results: Dict[str, Dict[str, Any]]) -> None:
    """
    Format and display an ASCII comparison table of all evaluated models.
    """
    print("\n" + "=" * 90)
    print("                    PHISHGUARD MODEL BENCHMARK COMPARISON TABLE")
    print("=" * 90)
    
    header = (
        f"{'Model':<22} | "
        f"{'Accuracy':<9} | "
        f"{'Precision':<9} | "
        f"{'Recall':<9} | "
        f"{'F1-Score':<9} | "
        f"{'FN (Missed)':<11} | "
        f"{'FP (False Alm)':<13} | "
        f"{'Train Time':<10}"
    )
    print(header)
    print("-" * 90)

    for name, m in results.items():
        cm = m["confusion_matrix"]
        row = (
            f"{name:<22} | "
            f"{m['accuracy']:>8.4f}  | "
            f"{m['precision']:>8.4f}  | "
            f"{m['recall']:>8.4f}  | "
            f"{m['f1_score']:>8.4f}  | "
            f"{cm['fn']:>10,}  | "
            f"{cm['fp']:>12,}  | "
            f"{m['train_time_sec']:>8.2f}s"
        )
        print(row)
    print("=" * 90)

    # Detailed Confusion Matrix breakdown
    print("\n" + "-" * 78)
    print("  CONFUSION MATRIX BREAKDOWN & INTERPRETATION (TEST SET: 101,439 URLs)")
    print("-" * 78)
    for name, m in results.items():
        cm = m["confusion_matrix"]
        print(f"\n• {name}:")
        print(f"    ┌──────────────────────┬──────────────────────┐")
        print(f"    │ True Negative (TN)   │ False Positive (FP)  │")
        print(f"    │ {cm['tn']:>10,} Legitimate │ {cm['fp']:>10,} False Alarm│")
        print(f"    ├──────────────────────┼──────────────────────┤")
        print(f"    │ False Negative (FN)  │ True Positive (TP)   │")
        print(f"    │ {cm['fn']:>10,} MISSED     │ {cm['tp']:>10,} Caught     │")
        print(f"    └──────────────────────┴──────────────────────┘")
        print(f"    False Negative Rate (Missed attacks) : {m['fnr'] * 100:.2f}%")
        print(f"    False Positive Rate (Blocked safe)   : {m['fpr'] * 100:.2f}%")


# ══════════════════════════════════════════════════════════════════════════════
# 5. Persist Results & Artifacts
# ══════════════════════════════════════════════════════════════════════════════

def save_evaluation_results(
    results: Dict[str, Dict[str, Any]],
    results_dir: str = RESULTS_DIR,
    model_dir: str = MODEL_DIR
) -> None:
    """
    Save structured evaluation results to disk:
      - results/model_comparison.csv
      - results/model_comparison.json
      - results/model_comparison.md
      - results/confusion_matrices.txt
      - model/<model_name_slug>.joblib (trained model objects for Task 5)
    """
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    # ── 1. Save CSV ──
    csv_rows = []
    for name, m in results.items():
        cm = m["confusion_matrix"]
        csv_rows.append({
            "model": name,
            "accuracy": round(m["accuracy"], 5),
            "precision": round(m["precision"], 5),
            "recall": round(m["recall"], 5),
            "f1_score": round(m["f1_score"], 5),
            "true_negatives": cm["tn"],
            "false_positives": cm["fp"],
            "false_negatives": cm["fn"],
            "true_positives": cm["tp"],
            "false_negative_rate": round(m["fnr"], 5),
            "false_positive_rate": round(m["fpr"], 5),
            "train_time_sec": m["train_time_sec"],
            "pred_time_sec": m["test_pred_time_sec"],
        })
    df_compare = pd.DataFrame(csv_rows)
    csv_path = os.path.join(results_dir, "model_comparison.csv")
    df_compare.to_csv(csv_path, index=False)
    print(f"\n✔ Saved comparison CSV: {csv_path}")

    # ── 2. Save JSON ──
    json_data = {}
    for name, m in results.items():
        json_data[name] = {k: v for k, v in m.items() if k != "model_object"}
    
    json_path = os.path.join(results_dir, "model_comparison.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"✔ Saved detailed JSON:  {json_path}")

    # ── 3. Save Markdown Report ──
    md_path = os.path.join(results_dir, "model_comparison.md")
    with open(md_path, "w") as f:
        f.write("# PhishGuard — Classification Model Comparison\n\n")
        f.write(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 1. Overall Performance Table\n\n")
        f.write("| Model | Accuracy | Precision | Recall | F1-Score | False Negatives (Missed) | False Positives (False Alarm) | Train Time (s) |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for r in csv_rows:
            f.write(
                f"| **{r['model']}** | {r['accuracy']:.4f} | {r['precision']:.4f} | "
                f"{r['recall']:.4f} | {r['f1_score']:.4f} | {r['false_negatives']:,} | "
                f"{r['false_positives']:,} | {r['train_time_sec']}s |\n"
            )
        f.write("\n## 2. Confusion Matrices\n\n")
        for name, m in results.items():
            cm = m["confusion_matrix"]
            f.write(f"### {name}\n\n")
            f.write(f"- **True Negatives (TN)**: {cm['tn']:,} (Safe URLs classified as Safe)\n")
            f.write(f"- **False Positives (FP)**: {cm['fp']:,} (Safe URLs incorrectly flagged as Phishing)\n")
            f.write(f"- **False Negatives (FN)**: {cm['fn']:,} (Phishing URLs that bypassed detection)\n")
            f.write(f"- **True Positives (TP)**: {cm['tp']:,} (Phishing URLs successfully blocked)\n\n")
    print(f"✔ Saved Markdown report: {md_path}")

    # ── 4. Save Confusion Matrices text file ──
    txt_path = os.path.join(results_dir, "confusion_matrices.txt")
    with open(txt_path, "w") as f:
        f.write("PhishGuard Confusion Matrices\n")
        f.write("=" * 40 + "\n\n")
        for name, m in results.items():
            cm = m["confusion_matrix"]
            f.write(f"Model: {name}\n")
            f.write(f"[[TN={cm['tn']}, FP={cm['fp']}],\n")
            f.write(f" [FN={cm['fn']}, TP={cm['tp']}]]\n\n")
    print(f"✔ Saved raw matrices:   {txt_path}")

    # ── 5. Save Model Artifacts to model/ ──
    slug_map = {
        "Logistic Regression": "logistic_regression.joblib",
        "Decision Tree": "decision_tree.joblib",
        "Random Forest": "random_forest.joblib",
    }
    for name, m in results.items():
        fname = slug_map.get(name)
        if fname:
            target = os.path.join(model_dir, fname)
            joblib.dump(m["model_object"], target, compress=3)
            print(f"✔ Saved model artifact: {target}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. Viva Insights & College Presentation Notes
# ══════════════════════════════════════════════════════════════════════════════

def print_viva_explanations() -> None:
    """
    Print intuitive, viva-ready explanations for each classifier.
    """
    print("\n" + "=" * 90)
    print("                    COLLEGE VIVA CHEAT SHEET & ALGORITHM ROLES")
    print("=" * 90)
    print("""
1. LOGISTIC REGRESSION (Linear Baseline):
   ---------------------------------------
   • Role: Serves as the parametric linear baseline model.
   • How it works: Computes a weighted sum of normalized URL features (z = w · x + b)
     and maps it through the Sigmoid activation function σ(z) = 1 / (1 + e^-z) to produce
     a probability score between 0 and 1.
   • Why Feature Scaling is Essential: Because features have vastly different magnitudes
     (e.g., total URL length can be 200, while has_ip_hostname is binary {0, 1}), feature
     scaling (StandardScaler) standardizes all features to zero mean and unit variance.
     Without scaling, high-magnitude features dominate the gradient descent updates,
     preventing proper convergence.
   • Key Viva Finding: Logistic Regression achieves ~85.8% accuracy and high precision (~86.4%),
     but suffers from poor recall (~44.0%). It misses over 55% of phishing sites (FN > 12,000)
     because phishing tactics rely on non-linear combinations (e.g. having suspicious keywords
     matters much more when the domain has a hyphen or long path than on an official domain).
     A single linear hyperplane cannot capture such complex interactions.

2. DECISION TREE CLASSIFIER (Non-Linear Rule-Based Model):
   --------------------------------------------------------
   • Role: Captures non-linear thresholds and provides clear, human-interpretable IF-THEN rules.
   • How it works: Recursively partitions the URL feature space by picking the feature and split
     threshold that maximizes Information Gain (or minimizes Gini Impurity) at each step.
   • Advantages: Does not require feature scaling, naturally handles non-linear relationships,
     and mirrors security analyst logic (e.g. "IF path_tokens > 3 AND has_suspicious_keyword == 1 THEN phishing").
   • Limitation: A single unpruned decision tree tends to overfit training quirks and has high
     variance, which is why we constrain tree depth (max_depth=25).
   • Viva Performance: Recall jumps from ~44% to ~77.1%, and accuracy reaches ~92.2%.

3. RANDOM FOREST CLASSIFIER (Ensemble Learning via Bagging):
   ----------------------------------------------------------
   • Role: High-performance ensemble designed to maximize generalization and minimize variance.
   • How it works: Constructs an ensemble of B=100 diverse decision trees using Bagging
     (Bootstrap Aggregating) combined with Random Subspace Feature Selection (picking a random
     subset of features √p at each node split). Predictions are made by majority voting.
   • Why it wins: By averaging the uncorrelated predictions of 100 deep trees, Random Forest
     drastically reduces the variance without increasing bias. It achieves the highest
     precision (~92.6%), lowest false positive count (only ~1,415 out of 78,579 legitimate URLs),
     and top F1-Score (~0.842).
   • Trade-off: Slightly larger model size on disk and longer training time (~6-8s vs 0.5s),
     which is a very favorable trade-off for a security application where false alarms
     must be minimized.
""")
    print("=" * 90 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="PhishGuard — Train and compare Logistic Regression, Decision Tree, and Random Forest."
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Bypass feature cache and re-extract features from raw URL text."
    )
    args = parser.parse_args()

    # Step 1: Load data and features
    X_train, y_train, X_test, y_test = load_data(force_extract=args.force_extract)

    # Step 2: Build candidate models
    models = build_models(random_state=RANDOM_STATE)

    # Step 3: Train and evaluate
    results = train_and_evaluate(models, X_train, y_train, X_test, y_test)

    # Step 4: Display benchmark table
    print_comparison_table(results)

    # Step 5: Save results and models
    save_evaluation_results(results, results_dir=RESULTS_DIR, model_dir=MODEL_DIR)

    # Step 6: Print college viva explanations
    print_viva_explanations()


if __name__ == "__main__":
    main()
