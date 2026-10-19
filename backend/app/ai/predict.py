"""Delay-risk inference: trained model when available, otherwise the rule-based fallback.

SECURITY: the model file is loaded only from our own artifacts folder (joblib/pickle must never be
loaded from user uploads)."""
import json

import joblib

from app.ai.fallback import rule_based
from app.ai.features import FEATURES, clean_features
from app.ai.train import ARTIFACT_DIR

_cache = {"dir": None, "model": None, "meta": None}

REASONS = {
    "progress": lambda v: f"Progress is {v:.0f}%",
    "days_to_deadline": lambda v: f"{v:.0f} day(s) until the deadline" if v >= 0 else f"Deadline passed {-v:.0f} day(s) ago",
    "priority": lambda v: f"Priority level {v:.0f} of 4",
    "estimated_hours": lambda v: f"Estimated effort is {v:.0f} hours",
    "hours_logged": lambda v: f"{v:.0f} hours logged so far",
    "open_task_count": lambda v: f"Assignee has {v:.0f} open tasks",
    "rejection_count": lambda v: f"Rejected in review {v:.0f} time(s)",
    "reopen_count": lambda v: f"Reopened {v:.0f} time(s)",
    "days_since_last_update": lambda v: f"No progress update for {v:.0f} day(s)",
}
ACTIONS = {
    "progress": "Check progress with the assignee",
    "days_to_deadline": "Review the deadline or reduce the scope",
    "open_task_count": "Review the assignee's workload",
    "rejection_count": "Clarify requirements and review criteria",
    "reopen_count": "Clarify requirements and review criteria",
    "days_since_last_update": "Ask the assignee for a progress update",
    "estimated_hours": "Re-check the effort estimate",
    "hours_logged": "Re-check the effort estimate",
    "priority": "Confirm the priority with the assignee",
}


def load_model(directory=ARTIFACT_DIR, force=False):
    """Return (model, metadata) or (None, None) when no valid trained model exists."""
    if not force and _cache["dir"] == str(directory) and _cache["model"] is not None:
        return _cache["model"], _cache["meta"]
    try:
        model = joblib.load(directory / "delay_model.joblib")
        meta = json.loads((directory / "delay_model.json").read_text(encoding="utf-8"))
        if meta.get("features") != FEATURES or getattr(model, "n_features_in_", None) != len(FEATURES):
            return None, None
    except Exception:  # missing/corrupt file -> use the fallback
        return None, None
    _cache.update(dir=str(directory), model=model, meta=meta)
    return model, meta


def model_info(directory=ARTIFACT_DIR):
    model, meta = load_model(directory)
    if model is None:
        return {"model_available": False, "trained_on": None, "model_version": None, "trained_at": None,
                "metrics": None, "notes": "No trained model found. Rule-based estimates are being used. "
                                          "Run: flask --app run train-model"}
    return {"model_available": True, "trained_on": meta["trained_on"], "model_version": meta["model_version"],
            "trained_at": meta["trained_at"], "metrics": meta["metrics"], "notes": meta["notes"]}


def _category(score):
    return "High" if score >= 0.66 else "Medium" if score >= 0.33 else "Low"


def _actions(factors):
    seen = []
    for f in factors:
        if f["effect"] == "increases_risk" and ACTIONS.get(f["feature"]) and ACTIONS[f["feature"]] not in seen:
            seen.append(ACTIONS[f["feature"]])
    return seen[:4] or ["Continue monitoring progress"]


def predict(raw_features, directory=ARTIFACT_DIR):
    model, meta = load_model(directory)
    medians = meta["medians"] if meta else None
    f = clean_features(raw_features, medians)
    if model is None:
        r = rule_based(f)
        return {"risk_category": r["risk_category"], "risk_score": None, "method": "rule_based",
                "model_version": None, "factors": r["factors"], "suggested_actions": _actions(r["factors"])}

    x = [[f[n] for n in FEATURES]]
    score = float(model.predict_proba(x)[0][1])
    # Local explanation: how much does the score drop if one feature is replaced by its typical (median) value?
    factors = []
    for i, name in enumerate(FEATURES):
        x2 = [list(x[0])]
        x2[0][i] = medians[name]
        delta = score - float(model.predict_proba(x2)[0][1])
        if abs(delta) >= 0.02:
            factors.append({"feature": name, "value": round(f[name], 1), "impact": round(delta, 3),
                            "effect": "increases_risk" if delta > 0 else "reduces_risk",
                            "reason": REASONS[name](f[name])})
    factors.sort(key=lambda d: abs(d["impact"]), reverse=True)
    factors = factors[:4]
    return {"risk_category": _category(score), "risk_score": round(score, 3), "method": "ml_model",
            "model_version": meta["model_version"], "factors": factors, "suggested_actions": _actions(factors)}
