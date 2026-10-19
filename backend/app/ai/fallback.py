"""Transparent rule-based delay-risk estimate.

This is NOT a trained ML prediction. It is a fixed points system used when no trained model is
available. risk_score is None because the points are not a calibrated probability.
"""


def rule_based(f):
    points, factors = 0, []

    def add(pts, feature, reason, effect="increases_risk"):
        nonlocal points
        points += pts
        factors.append({"feature": feature, "value": round(f[feature], 1), "effect": effect, "reason": reason})

    d, p = f["days_to_deadline"], f["progress"]
    if d < 0:
        add(5, "days_to_deadline", f"Deadline passed {abs(int(d))} day(s) ago")
    elif d <= 2 and p < 80:
        add(3, "days_to_deadline", f"Only {int(d)} day(s) left but progress is {int(p)}%")
    elif d <= 5 and p < 50:
        add(2, "progress", f"{int(d)} days left but progress is only {int(p)}%")
    if f["days_since_last_update"] >= 5:
        add(2, "days_since_last_update", f"No progress update for {int(f['days_since_last_update'])} days")
    elif f["days_since_last_update"] >= 3:
        add(1, "days_since_last_update", f"No progress update for {int(f['days_since_last_update'])} days")
    if f["open_task_count"] >= 6:
        add(2, "open_task_count", f"Assignee has {int(f['open_task_count'])} open tasks")
    elif f["open_task_count"] >= 4:
        add(1, "open_task_count", f"Assignee has {int(f['open_task_count'])} open tasks")
    if f["rejection_count"] >= 2:
        add(2, "rejection_count", f"Rejected in review {int(f['rejection_count'])} times")
    elif f["rejection_count"] == 1:
        add(1, "rejection_count", "Rejected in review once")
    if f["reopen_count"] >= 1:
        add(1, "reopen_count", "Task was reopened after completion")
    if f["priority"] == 4 and p < 50 and d <= 7:
        add(1, "priority", "Critical priority with low progress and a near deadline")

    category = "High" if points >= 5 else "Medium" if points >= 2 else "Low"
    return {"risk_category": category, "risk_score": None, "points": points, "factors": factors}
