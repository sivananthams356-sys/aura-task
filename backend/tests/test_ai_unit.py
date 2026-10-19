"""Pure unit tests for the AI module (no Flask needed)."""
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from app.ai import predict as ai
from app.ai.fallback import rule_based
from app.ai.features import FEATURES, clean_features, task_to_features
from app.ai.synthetic_data import generate
from app.ai.train import train

RISKY = dict(progress=10, days_to_deadline=1, priority=4, estimated_hours=30, hours_logged=2,
             open_task_count=8, rejection_count=2, reopen_count=1, days_since_last_update=7)
SAFE = dict(progress=90, days_to_deadline=20, priority=2, estimated_hours=10, hours_logged=9,
            open_task_count=1, rejection_count=0, reopen_count=0, days_since_last_update=0.5)
NO_MODEL_DIR = Path(tempfile.gettempdir()) / "aura_no_model_here"


def _trained_dir():
    directory = Path(tempfile.mkdtemp())
    train(n_samples=1500, out_dir=directory)
    return directory


def test_features_are_computed_from_current_state_only():
    now = datetime(2026, 10, 18, 12, 0)
    task = SimpleNamespace(progress=40, deadline=(now + timedelta(days=5)).date(), priority="High",
                           estimated_hours=10, actual_hours=None, rejection_count=1, reopen_count=0,
                           last_progress_update=now - timedelta(days=2), created_at=now - timedelta(days=9))
    f = task_to_features(task, open_task_count=3, now=now)
    assert list(f) == FEATURES
    assert f["days_to_deadline"] == 5 and f["priority"] == 3 and f["hours_logged"] == 0
    assert round(f["days_since_last_update"]) == 2


def test_clean_features_handles_missing_garbage_and_out_of_range():
    f = clean_features({"progress": "abc", "days_to_deadline": None, "priority": 99, "estimated_hours": float("nan"),
                        "open_task_count": -5, "unknown_extra_field": 1})
    assert list(f) == FEATURES and f["progress"] == 0.0 and f["priority"] == 4.0
    assert f["open_task_count"] == 0.0 and f["estimated_hours"] == 8.0
    assert clean_features({}, medians={"progress": 33})["progress"] == 33.0


def test_rule_based_fallback_levels_and_labels():
    risky, safe = rule_based(clean_features(RISKY)), rule_based(clean_features(SAFE))
    assert risky["risk_category"] == "High" and safe["risk_category"] == "Low"
    assert risky["risk_score"] is None and risky["factors"]


def test_synthetic_data_is_reproducible_and_has_both_classes():
    X1, y1 = generate(500, seed=1)
    X2, y2 = generate(500, seed=1)
    assert (X1 == X2).all() and (y1 == y2).all() and 0.1 < y1.mean() < 0.9 and X1.shape[1] == len(FEATURES)


def test_training_reports_metrics_and_beats_majority_baseline():
    directory = _trained_dir()
    meta = ai.model_info(directory)
    assert meta["model_available"] and meta["trained_on"] == "synthetic"
    m = meta["metrics"]
    for key in ("precision", "recall", "f1", "roc_auc", "confusion_matrix", "baseline_f1", "baseline_majority_f1"):
        assert key in m
    assert m["f1"] > m["baseline_majority_f1"] and 0.5 < m["roc_auc"] <= 1.0
    assert "synthetic" in meta["notes"].lower()


def test_model_inference_ranks_risky_above_safe_and_explains():
    directory = _trained_dir()
    risky, safe = ai.predict(RISKY, directory), ai.predict(SAFE, directory)
    assert risky["method"] == safe["method"] == "ml_model"
    assert risky["risk_score"] > safe["risk_score"] and 0 <= safe["risk_score"] <= 1
    assert risky["risk_category"] in ("Medium", "High") and risky["factors"] and risky["suggested_actions"]
    assert all({"feature", "value", "effect", "reason"} <= set(f) for f in risky["factors"])
    odd = ai.predict({}, directory)                          # missing values must not crash
    assert odd["risk_category"] in ("Low", "Medium", "High")


def test_fallback_is_used_when_model_missing_or_corrupt():
    out = ai.predict(RISKY, NO_MODEL_DIR)
    assert out["method"] == "rule_based" and out["risk_score"] is None and out["model_version"] is None
    assert ai.model_info(NO_MODEL_DIR)["model_available"] is False
    corrupt = Path(tempfile.mkdtemp())
    (corrupt / "delay_model.joblib").write_bytes(b"not a model")
    (corrupt / "delay_model.json").write_text("{}")
    assert ai.predict(RISKY, corrupt)["method"] == "rule_based"
