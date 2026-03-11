"""
Model Validation Script
========================
Tests the trained Isolation Forest against anomaly data.

This is NOT retraining. It loads the trained model and runs predictions.

INPUT:  models/isolation_forest.pkl
        models/scaler.pkl
        processed_data/features_test_anomaly.csv
        processed_data/features_train_normal.csv (for comparison)

OUTPUT: Console report + models/validation_results.png
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.metrics import (
    classification_report, confusion_matrix,
    precision_score, recall_score, f1_score
)

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_FILE = 'models/isolation_forest.pkl'
SCALER_FILE = 'models/scaler.pkl'
NORMAL_FILE = 'processed_data/features_train_normal.csv'
ANOMALY_FILE = 'processed_data/features_test_anomaly.csv'
OUTPUT_DIR = Path('models')

# ============================================================
# LOAD MODEL (no retraining happens here)
# ============================================================

def load_model():
    print("=" * 60)
    print("LOADING TRAINED MODEL")
    print("=" * 60)

    model = joblib.load(MODEL_FILE)
    scaler = joblib.load(SCALER_FILE)

    print(f"✓ Model loaded from:  {MODEL_FILE}")
    print(f"✓ Scaler loaded from: {SCALER_FILE}")
    print(f"  Model type: {type(model).__name__}")
    print(f"  NOTE: model.predict() is called below — NO retraining")

    return model, scaler


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(model, scaler):
    """Load and scale both datasets using the EXISTING scaler (no refitting)."""

    feature_cols = None
    if hasattr(scaler, 'feature_names_in_'):
        feature_cols = list(scaler.feature_names_in_)

    def load_and_scale(csv_path, label):
        df = pd.read_csv(csv_path)
        drop_cols = [c for c in ['timestamp', 'scenario', 'is_anomaly'] if c in df.columns]

        if feature_cols is not None:
            # Use exact same columns the model was trained on
            X = df[feature_cols]
        else:
            X = df.drop(columns=drop_cols, errors='ignore')

        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
        X_scaled = scaler.transform(X)   # transform only — NOT fit_transform
        print(f"  ✓ {label}: {len(X):,} rows scaled")
        return X_scaled, df

    print("\n" + "=" * 60)
    print("PREPARING TEST DATA")
    print("=" * 60)

    X_normal_scaled, df_normal = load_and_scale(NORMAL_FILE, "Normal")
    X_anomaly_scaled, df_anomaly = load_and_scale(ANOMALY_FILE, "Anomaly (stress+failure)")

    return X_normal_scaled, X_anomaly_scaled, df_anomaly


# ============================================================
# RUN PREDICTIONS
# ============================================================

def predict(model, X_normal, X_anomaly, df_anomaly):
    print("\n" + "=" * 60)
    print("RUNNING PREDICTIONS (no retraining)")
    print("=" * 60)

    # Predict on normal holdout
    normal_preds = model.predict(X_normal)       # -1=anomaly, 1=normal
    normal_scores = model.score_samples(X_normal)

    # Predict on anomaly data
    anomaly_preds = model.predict(X_anomaly)
    anomaly_scores = model.score_samples(X_anomaly)

    # Results summary
    n_normal = len(normal_preds)
    n_anomaly = len(anomaly_preds)

    normal_correct = (normal_preds == 1).sum()         # Correctly labelled as normal
    anomaly_detected = (anomaly_preds == -1).sum()     # Correctly detected as anomaly

    print(f"\n  NORMAL DATA ({n_normal:,} samples):")
    print(f"    Correctly classified normal: {normal_correct:,} ({normal_correct/n_normal*100:.1f}%)")
    print(f"    False positives (wrong alarm): {(normal_preds == -1).sum():,} ({(normal_preds == -1).sum()/n_normal*100:.1f}%)")

    print(f"\n  ANOMALY DATA ({n_anomaly:,} samples — stress + failure):")
    print(f"    Anomalies detected: {anomaly_detected:,} ({anomaly_detected/n_anomaly*100:.1f}%)")
    print(f"    Missed anomalies:   {(anomaly_preds == 1).sum():,} ({(anomaly_preds == 1).sum()/n_anomaly*100:.1f}%)")

    # --------------------------------------------------------
    # Formal evaluation metrics
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("EVALUATION METRICS")
    print("=" * 60)

    # Ground truth: 0=normal, 1=anomaly
    y_true = np.concatenate([
        np.zeros(n_normal, dtype=int),
        np.ones(n_anomaly, dtype=int)
    ])

    # Model predictions: convert -1/1 → 1/0 (anomaly=1, normal=0)
    all_preds = np.concatenate([normal_preds, anomaly_preds])
    y_pred = np.where(all_preds == -1, 1, 0)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    print(f"\n  Precision: {precision:.3f}  (of flagged anomalies, how many were real?)")
    print(f"  Recall:    {recall:.3f}  (of real anomalies, how many did we catch?)")
    print(f"  F1-Score:  {f1:.3f}  (balance of precision and recall)")

    # Per-scenario breakdown
    if 'scenario' in pd.read_csv(ANOMALY_FILE).columns:
        df_anomaly_orig = pd.read_csv(ANOMALY_FILE)
        # Trim to same length (in case of shape mismatch)
        n = min(len(anomaly_preds), len(df_anomaly_orig))
        df_anomaly_orig = df_anomaly_orig.iloc[:n].copy()
        df_anomaly_orig['model_pred'] = anomaly_preds[:n]
        df_anomaly_orig['detected'] = (df_anomaly_orig['model_pred'] == -1).astype(int)

        print("\n  Per-scenario detection rate:")
        for scenario, group in df_anomaly_orig.groupby('scenario'):
            detected = group['detected'].sum()
            total = len(group)
            print(f"    {scenario:10s}: {detected:,}/{total:,} detected ({detected/total*100:.1f}%)")

    return (normal_preds, normal_scores, anomaly_preds, anomaly_scores,
            precision, recall, f1)


# ============================================================
# VISUALIZE
# ============================================================

def visualize(normal_scores, anomaly_scores, normal_preds, anomaly_preds):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Isolation Forest — Validation Results', fontsize=14, fontweight='bold')

    # Score distributions
    ax = axes[0]
    ax.hist(normal_scores, bins=50, alpha=0.7, color='steelblue', label=f'Normal (n={len(normal_scores):,})')
    ax.hist(anomaly_scores, bins=50, alpha=0.7, color='crimson', label=f'Anomaly (n={len(anomaly_scores):,})')
    ax.set_xlabel('Anomaly Score (lower = more anomalous)')
    ax.set_ylabel('Count')
    ax.set_title('Score Distribution\nNormal vs Anomaly')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Detection rates
    ax = axes[1]
    categories = ['Normal\n(should be 1)', 'Anomaly\n(should be -1)']
    correct = [
        (normal_preds == 1).sum() / len(normal_preds) * 100,
        (anomaly_preds == -1).sum() / len(anomaly_preds) * 100,
    ]
    wrong = [100 - c for c in correct]

    x = np.arange(len(categories))
    bars1 = ax.bar(x, correct, color=['steelblue', 'crimson'], alpha=0.8, label='Correctly classified')
    bars2 = ax.bar(x, wrong, bottom=correct, color='lightgray', alpha=0.6, label='Misclassified')

    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_ylabel('Percentage (%)')
    ax.set_ylim(0, 110)
    ax.set_title('Classification Accuracy\nby Data Type')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    for bar, val in zip(bars1, correct):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.1f}%',
                ha='center', va='center', fontweight='bold', color='white', fontsize=12)

    plt.tight_layout()
    out_path = OUTPUT_DIR / 'validation_results.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Chart saved: {out_path}")
    plt.close()


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n")
    print("=" * 60)
    print("MODEL VALIDATION — NO RETRAINING")
    print("=" * 60)
    print("This script tests the trained model on unseen anomaly data.")
    print("model.fit() is NEVER called here.\n")

    model, scaler = load_model()
    X_normal, X_anomaly, df_anomaly = prepare_data(model, scaler)

    (normal_preds, normal_scores,
     anomaly_preds, anomaly_scores,
     precision, recall, f1) = predict(model, X_normal, X_anomaly, df_anomaly)

    visualize(normal_scores, anomaly_scores, normal_preds, anomaly_preds)

    print("\n" + "=" * 60)
    print("✅ VALIDATION COMPLETE")
    print("=" * 60)
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  F1-Score:  {f1:.3f}")
    print(f"\n  Chart: models/validation_results.png")
    print(f"\nNext step: Run ml_service.py for live demo\n")


if __name__ == "__main__":
    main()
