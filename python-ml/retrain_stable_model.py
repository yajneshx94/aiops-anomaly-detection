"""
Retrain Isolation Forest — 5 Stable Features
=============================================
Drops features that drift with traffic rate or container age.
Keeps only features stable regardless of Podinfo traffic level.

STABLE FEATURES (5):
  go_goroutines                          — always 9-18 when healthy
  process_open_fds                       — always 9-11 when healthy
  heap_utilization_ratio                 — always ~1.20 when healthy
  avg_request_duration_sec               — near 0 when healthy
  http_request_duration_seconds_sum_rate — low when healthy

DROPPED (too dependent on traffic load):
  http_requests_total_rate_per_sec       — varies with traffic generator
  http_request_duration_seconds_count_rate — same
  process_cpu_seconds_total_rate_per_sec — varies
  go_memstats_alloc_bytes                — low on fresh container
  go_memstats_heap_inuse_bytes           — low on fresh container

INPUT:  processed_data/features_train_normal.csv   (your original 34k samples)
OUTPUT: models/isolation_forest.pkl
        models/scaler.pkl
        models/model_metadata.txt
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────

INPUT_FILE = 'processed_data/features_train_normal.csv'
MODEL_DIR  = Path('models/')

STABLE_FEATURES = [
    'go_goroutines',
    'process_open_fds',
    'heap_utilization_ratio',
    'avg_request_duration_sec',
    'http_request_duration_seconds_sum_rate',
]

CONTAMINATION  = 0.05
N_ESTIMATORS   = 100
MAX_SAMPLES    = 256
RANDOM_STATE   = 42

# ─── MAIN ──────────────────────────────────────────────────────────────────

def main():
    print('=' * 55)
    print('  Retrain Isolation Forest — 5 Stable Features')
    print('=' * 55)

    # Load
    print(f'\nLoading {INPUT_FILE}...')
    df = pd.read_csv(INPUT_FILE)
    print(f'  {len(df):,} rows loaded')

    X = df[STABLE_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    print(f'  {len(X.columns)} features: {list(X.columns)}')

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train
    print('\nTraining Isolation Forest...')
    model = IsolationForest(
        contamination=CONTAMINATION,
        n_estimators=N_ESTIMATORS,
        max_samples=MAX_SAMPLES,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    # Self-check
    scores = model.score_samples(X_scaled)
    preds  = model.predict(X_scaled)
    normal_pct = (preds == 1).mean() * 100
    print(f'\nSelf-check:')
    print(f'  Normal:  {(preds==1).sum():,} ({normal_pct:.1f}%)')
    print(f'  Anomaly: {(preds==-1).sum():,} ({100-normal_pct:.1f}%)')
    print(f'  Score range: [{scores.min():.4f}, {scores.max():.4f}]')
    print(f'  Mean normal score: {scores.mean():.4f}')

    # Backup old models
    for fname in ['isolation_forest.pkl', 'scaler.pkl']:
        old = MODEL_DIR / fname
        bak = MODEL_DIR / fname.replace('.pkl', '_backup.pkl')
        if old.exists():
            if bak.exists():
                bak.unlink()
            old.rename(bak)
            print(f'  Backed up {fname}')

    # Save
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model,  MODEL_DIR / 'isolation_forest.pkl')
    joblib.dump(scaler, MODEL_DIR / 'scaler.pkl')

    # Metadata
    with open(MODEL_DIR / 'model_metadata.txt', 'w') as f:
        f.write('ISOLATION FOREST MODEL METADATA\n')
        f.write('=' * 50 + '\n\n')
        f.write(f'Trained: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write('Config:\n')
        f.write(f'  contamination = {CONTAMINATION}\n')
        f.write(f'  n_estimators  = {N_ESTIMATORS}\n')
        f.write(f'  max_samples   = {MAX_SAMPLES}\n\n')
        f.write(f'Training data: {len(X):,} normal samples\n\n')
        f.write(f'Features ({len(STABLE_FEATURES)}):\n')
        for col in STABLE_FEATURES:
            f.write(f'  - {col}\n')
        f.write('\nDropped features (traffic/container-age sensitive):\n')
        for col in ['http_requests_total_rate_per_sec',
                    'http_request_duration_seconds_count_rate',
                    'process_cpu_seconds_total_rate_per_sec',
                    'go_memstats_alloc_bytes',
                    'go_memstats_heap_inuse_bytes']:
            f.write(f'  - {col}\n')
        f.write(f'\nMean normal score: {scores.mean():.4f}\n')
        f.write('Anomaly threshold: -0.50\n')

    print(f'\n  ✓ Model saved:    {MODEL_DIR}/isolation_forest.pkl')
    print(f'  ✓ Scaler saved:   {MODEL_DIR}/scaler.pkl')
    print(f'  ✓ Metadata saved: {MODEL_DIR}/model_metadata.txt')

    print('\n' + '=' * 55)
    print('  NEXT STEPS:')
    print('  1. Restart Python ML service: python ml_service.py')
    print('  2. Hard-refresh the dashboard: Ctrl+Shift+R')
    print('  3. Fresh Podinfo should now score ~-0.45 (NORMAL)')
    print('=' * 55 + '\n')


if __name__ == '__main__':
    main()
