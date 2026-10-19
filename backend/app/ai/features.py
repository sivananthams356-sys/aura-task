"""Feature processing for delay-risk prediction.

LEAKAGE RULE: every feature is computed only from information that exists at prediction time
(current progress, time left, workload, history so far). Nothing recorded after the deadline
or after completion is used.
"""
from datetime import datetime, timezone

FEATURES = [
    "progress", "days_to_deadline", "priority", "estimated_hours", "hours_logged",
    "open_task_count", "rejection_count", "reopen_count", "days_since_last_update",
]
PRIORITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}

# Valid ranges, used to clip odd/unseen inputs before prediction.
RANGES = {
    "progress": (0, 100), "days_to_deadline": (-365, 365), "priority": (1, 4),
    "estimated_hours": (0, 1000), "hours_logged": (0, 10000), "open_task_count": (0, 100),
    "rejection_count": (0, 50), "reopen_count": (0, 50), "days_since_last_update": (0, 365),
}
# Used only when a value is missing AND no trained medians are available.
DEFAULTS = {
    "progress": 0, "days_to_deadline": 7, "priority": 2, "estimated_hours": 8, "hours_logged": 0,
    "open_task_count": 3, "rejection_count": 0, "reopen_count": 0, "days_since_last_update": 1,
}


def task_to_features(task, open_task_count, now=None):
    """Build the feature dict from a task-like object (works with the SQLAlchemy Task)."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    last = task.last_progress_update or task.created_at or now
    return {
        "progress": task.progress,
        "days_to_deadline": (task.deadline - now.date()).days if task.deadline else None,
        "priority": PRIORITY_RANK.get(task.priority, 2),
        "estimated_hours": task.estimated_hours,
        "hours_logged": task.actual_hours or 0,
        "open_task_count": open_task_count,
        "rejection_count": task.rejection_count or 0,
        "reopen_count": task.reopen_count or 0,
        "days_since_last_update": max((now - last).total_seconds() / 86400.0, 0.0),
    }


def clean_features(raw, medians=None):
    """Coerce to floats, fill missing values (trained median, else default), clip to valid range."""
    out = {}
    for name in FEATURES:
        value = raw.get(name)
        try:
            value = float(value)
            if value != value:  # NaN
                raise ValueError
        except (TypeError, ValueError):
            value = float((medians or {}).get(name, DEFAULTS[name]))
        low, high = RANGES[name]
        out[name] = min(max(value, low), high)
    out["priority"] = float(round(out["priority"]))
    return out
