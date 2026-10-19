"""Train + evaluate the delay-risk model. Run:  flask --app run train-model

Steps: generate SYNTHETIC data -> stratified train/test split -> compare against two baselines ->
save model (joblib) + metadata (json). Metrics describe synthetic held-out data only."""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from app.ai.features import FEATURES
from app.ai.synthetic_data import generate

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def _scores(y_true, y_pred):
    return {"precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4)}


def train(n_samples=3000, seed=42, out_dir=ARTIFACT_DIR):
    X, y = generate(n_samples, seed)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=seed)

    model = RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=5,
                                   class_weight="balanced", random_state=seed, n_jobs=1)
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    proba = model.predict_proba(X_te)[:, 1]

    majority = DummyClassifier(strategy="most_frequent").fit(X_tr, y_tr)
    idx = {name: i for i, name in enumerate(FEATURES)}
    rule_pred = ((X_te[:, idx["days_to_deadline"]] <= 3) & (X_te[:, idx["progress"]] < 70)).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_te, pred, labels=[0, 1]).ravel()
    metrics = {**_scores(y_te, pred), "roc_auc": round(float(roc_auc_score(y_te, proba)), 4),
               "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
               "baseline_f1": _scores(y_te, rule_pred)["f1"],
               "baseline_majority_f1": _scores(y_te, majority.predict(X_te))["f1"],
               "test_size": int(len(y_te)), "positive_rate": round(float(y.mean()), 4)}
    now = datetime.now(timezone.utc)
    meta = {"model_version": "rf-synthetic-" + now.strftime("%Y-%m-%d"),
            "trained_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "trained_on": "synthetic",
            "n_samples": n_samples, "features": FEATURES,
            "medians": {n: float(np.median(X_tr[:, i])) for n, i in idx.items()},
            "metrics": metrics,
            "notes": "Metrics measured on synthetic held-out data. They do not show real-world accuracy."}

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / "delay_model.joblib")
    (out_dir / "delay_model.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
