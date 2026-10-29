"""
PhishGuard — Dataset Preparation
=================================
Dataset : "Phishing Site URLs" by Tarun Tiwari
Source  : https://www.kaggle.com/datasets/taruntiwarihp/phishing-site-urls
File    : dataset/phishing_site_urls.csv

Columns (confirmed from Kaggle):
    URL   – raw URL string
    Label – "good" (legitimate) | "bad" (phishing)

Steps
-----
1. Inspect raw CSV (shape, dtypes, sample rows) — NO assumptions.
2. Identify URL column and label column automatically.
3. Normalise labels  →  0 = legitimate,  1 = phishing.
4. Remove invalid records: missing URLs, non-string URLs, duplicate URLs.
5. Handle conflicting labels (same URL with different labels).
6. Report class distribution and imbalance ratio.
7. Stratified train/test split (80/20, random_state=42).
8. Save cleaned dataset + split files to dataset/ (original file untouched).
"""

import sys
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATASET_DIR  = os.path.join(PROJECT_ROOT, "dataset")
RAW_FILE     = os.path.join(DATASET_DIR, "phishing_site_urls.csv")

OUT_CLEANED  = os.path.join(DATASET_DIR, "cleaned.csv")
OUT_TRAIN    = os.path.join(DATASET_DIR, "train.csv")
OUT_TEST     = os.path.join(DATASET_DIR, "test.csv")

RANDOM_SEED  = 42
TEST_SIZE    = 0.20   # 80 % train, 20 % test

# ── Label mapping (dataset-specific) ──────────────────────────────────────────
# "good" → 0 (legitimate),  "bad" → 1 (phishing)
LABEL_MAP = {"good": 0, "bad": 1}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 0 — Validate file exists
# ══════════════════════════════════════════════════════════════════════════════
def check_raw_file():
    if not os.path.isfile(RAW_FILE):
        print(f"\n❌  Raw dataset not found at: {RAW_FILE}")
        print(
            "\nPlease download it first:\n"
            "  1. Set up Kaggle API credentials (see README / Task 2 instructions).\n"
            "  2. Run inside ml-service/ with venv active:\n"
            "       kaggle datasets download -d taruntiwarihp/phishing-site-urls "
            "--path dataset/ --unzip\n"
            "  3. The file 'phishing_site_urls.csv' will appear in dataset/.\n"
        )
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Inspect raw CSV (no mutations yet)
# ══════════════════════════════════════════════════════════════════════════════
def inspect_raw(df):
    sep = "─" * 60
    print(f"\n{sep}")
    print("STEP 1 · RAW CSV INSPECTION")
    print(sep)
    print(f"  Shape            : {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"  Columns          : {list(df.columns)}")
    print(f"\n  Data types:\n{df.dtypes.to_string()}")
    print(f"\n  Null counts:\n{df.isnull().sum().to_string()}")
    print(f"\n  First 3 rows:\n{df.head(3).to_string(index=False)}")
    if "Label" in df.columns:
        dist = df["Label"].value_counts(dropna=False)
        print(f"\n  Raw label distribution:\n{dist.to_string()}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Identify columns
# ══════════════════════════════════════════════════════════════════════════════
def identify_columns(df):
    sep = "─" * 60
    print(f"\n{sep}")
    print("STEP 2 · COLUMN IDENTIFICATION")
    print(sep)

    url_candidates   = ["URL", "url", "Url", "website", "domain", "link"]
    label_candidates = ["Label", "label", "class", "Class", "status", "target"]

    url_col   = next((c for c in url_candidates   if c in df.columns), None)
    label_col = next((c for c in label_candidates if c in df.columns), None)

    if url_col is None or label_col is None:
        print(f"  Could not auto-detect columns. Found: {list(df.columns)}")
        print("  Assign URL_COL and LABEL_COL manually at the top of this script.")
        sys.exit(1)

    print(f"  URL column   → '{url_col}'")
    print(f"  Label column → '{label_col}'")
    return url_col, label_col


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Normalise labels
# ══════════════════════════════════════════════════════════════════════════════
def normalise_labels(df, label_col):
    sep = "─" * 60
    print(f"\n{sep}")
    print("STEP 3 · LABEL NORMALISATION")
    print(sep)

    unique_labels = df[label_col].dropna().unique()
    print(f"  Unique raw labels: {sorted(str(l) for l in unique_labels)}")

    df = df.copy()
    df[label_col] = df[label_col].astype(str).str.strip().str.lower()

    case_map = {k.lower(): v for k, v in LABEL_MAP.items()}
    before   = len(df)
    df["label"] = df[label_col].map(case_map)

    unknown_mask = df["label"].isna()
    n_unknown    = unknown_mask.sum()
    if n_unknown > 0:
        print(f"  {n_unknown:,} rows had unrecognised labels — dropping them.")
        print(f"  Unrecognised values: {df.loc[unknown_mask, label_col].unique()}")
        df = df[~unknown_mask].copy()
    else:
        print("  All labels mapped successfully.")

    df["label"] = df["label"].astype(int)
    print(f"  Encoding: {LABEL_MAP}  →  0=legitimate, 1=phishing")
    print(f"  Rows after label normalisation: {before:,} → {len(df):,}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Clean invalid records
# ══════════════════════════════════════════════════════════════════════════════
def clean_records(df, url_col):
    sep = "─" * 60
    print(f"\n{sep}")
    print("STEP 4 · CLEANING INVALID RECORDS")
    print(sep)

    start = len(df)

    mask_null = df[url_col].isna()
    n_null    = mask_null.sum()
    df        = df[~mask_null].copy()
    print(f"  Removed {n_null:,} rows with null URL.")

    mask_empty = df[url_col].astype(str).str.strip() == ""
    n_empty    = mask_empty.sum()
    df         = df[~mask_empty].copy()
    print(f"  Removed {n_empty:,} rows with empty URL.")

    mask_short = df[url_col].astype(str).str.len() < 4
    n_short    = mask_short.sum()
    df         = df[~mask_short].copy()
    print(f"  Removed {n_short:,} rows with URL length < 4 chars.")

    n_before_dedup = len(df)
    df             = df.drop_duplicates(subset=[url_col], keep="first").copy()
    n_dup          = n_before_dedup - len(df)
    print(f"  Removed {n_dup:,} duplicate URL rows (kept first occurrence).")

    print(f"\n  Rows after cleaning: {start:,} → {len(df):,}  "
          f"(removed {start - len(df):,} total)")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Handle conflicting labels
# ══════════════════════════════════════════════════════════════════════════════
def handle_conflicts(df, url_col):
    sep = "─" * 60
    print(f"\n{sep}")
    print("STEP 5 · CONFLICTING LABEL CHECK")
    print(sep)

    label_per_url = df.groupby(url_col)["label"].nunique()
    conflict_urls = label_per_url[label_per_url > 1].index
    n_conflict    = len(conflict_urls)

    if n_conflict == 0:
        print("  No conflicting labels found.")
    else:
        print(f"  {n_conflict:,} URLs appear with conflicting labels — dropping them.")
        df = df[~df[url_col].isin(conflict_urls)].copy()
        print(f"  Rows remaining: {len(df):,}")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Class distribution report
# ══════════════════════════════════════════════════════════════════════════════
def report_distribution(df):
    sep = "─" * 60
    print(f"\n{sep}")
    print("STEP 6 · CLASS DISTRIBUTION")
    print(sep)

    counts = df["label"].value_counts().sort_index()
    total  = len(df)
    legit  = counts.get(0, 0)
    phish  = counts.get(1, 0)
    pct_l  = legit / total * 100
    pct_p  = phish / total * 100
    ratio  = max(legit, phish) / max(min(legit, phish), 1)

    print(f"  Total records          : {total:,}")
    print(f"  Legitimate (label=0)   : {legit:,}  ({pct_l:.1f} %)")
    print(f"  Phishing   (label=1)   : {phish:,}  ({pct_p:.1f} %)")
    print(f"  Majority/Minority ratio: {ratio:.2f} : 1")

    if ratio > 3.0:
        print("\n  CLASS IMBALANCE DETECTED (ratio > 3:1).")
        print("  Consider class_weight='balanced' or SMOTE during training.")
    else:
        print("\n  Class distribution is reasonably balanced.")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Train / Test split
# ══════════════════════════════════════════════════════════════════════════════
def split_dataset(df, url_col):
    sep = "─" * 60
    print(f"\n{sep}")
    print("STEP 7 · TRAIN / TEST SPLIT")
    print(sep)

    clean = df[[url_col, "label"]].copy()
    clean.rename(columns={url_col: "url"}, inplace=True)

    X = clean["url"]
    y = clean["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        random_state=RANDOM_SEED,
        stratify=y,
    )

    train_df = pd.DataFrame({"url": X_train, "label": y_train})
    test_df  = pd.DataFrame({"url": X_test,  "label": y_test})

    print(f"  Strategy    : stratified split  (preserves class ratio in both sets)")
    print(f"  Random seed : {RANDOM_SEED}")
    print(f"  Train set   : {len(train_df):,} rows  "
          f"  label counts: {train_df['label'].value_counts().to_dict()}")
    print(f"  Test  set   : {len(test_df):,} rows   "
          f"  label counts: {test_df['label'].value_counts().to_dict()}")

    train_ratio = train_df["label"].mean()
    test_ratio  = test_df["label"].mean()
    print(f"\n  Phishing fraction — train: {train_ratio:.4f}  test: {test_ratio:.4f}")

    return train_df, test_df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8 — Save outputs (never overwrite raw file)
# ══════════════════════════════════════════════════════════════════════════════
def save_outputs(clean_df, train_df, test_df, url_col):
    sep = "─" * 60
    print(f"\n{sep}")
    print("STEP 8 · SAVING OUTPUT FILES")
    print(sep)

    clean_out = clean_df[[url_col, "label"]].copy()
    clean_out.rename(columns={url_col: "url"}, inplace=True)
    clean_out.to_csv(OUT_CLEANED, index=False)
    print(f"  Cleaned dataset → {OUT_CLEANED}  ({len(clean_out):,} rows)")

    train_df.to_csv(OUT_TRAIN, index=False)
    print(f"  Training split  → {OUT_TRAIN}  ({len(train_df):,} rows)")

    test_df.to_csv(OUT_TEST, index=False)
    print(f"  Test split      → {OUT_TEST}  ({len(test_df):,} rows)")

    print(f"\n  Original file '{os.path.basename(RAW_FILE)}' was NOT modified.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  PhishGuard — Dataset Preparation")
    print("=" * 60)

    check_raw_file()

    print(f"\n  Loading: {RAW_FILE}")
    df        = pd.read_csv(RAW_FILE)
    raw_count = len(df)
    inspect_raw(df)

    url_col, label_col = identify_columns(df)
    df = normalise_labels(df, label_col)
    df = clean_records(df, url_col)
    df = handle_conflicts(df, url_col)
    report_distribution(df)
    train_df, test_df = split_dataset(df, url_col)
    save_outputs(df, train_df, test_df, url_col)

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Records BEFORE cleaning : {raw_count:,}")
    print(f"  Records AFTER  cleaning : {len(df):,}")
    print(f"  Records removed         : {raw_count - len(df):,}")
    print(f"  Train rows              : {len(train_df):,}")
    print(f"  Test  rows              : {len(test_df):,}")
    print("\n  Dataset preparation complete.\n")


if __name__ == "__main__":
    main()
