"""SYNTHETIC development data. Labels come from a formula written by the developer plus noise,
so a model trained on this data only re-learns that formula. Its metrics say NOTHING about
real-world accuracy. Replace with real task history when it exists (see docs/architecture.md)."""
import numpy as np

from app.ai.features import FEATURES


def generate(n=3000, seed=42):
    rng = np.random.default_rng(seed)
    priority = rng.integers(1, 5, n)
    estimated = rng.uniform(2, 60, n).round(1)
    days_left = rng.integers(-2, 31, n)
    progress = np.clip(rng.normal(50, 25, n), 0, 99).round()
    logged = np.clip(estimated * (progress / 100) * rng.uniform(0.7, 1.5, n), 0, None).round(1)
    open_tasks = rng.integers(0, 10, n)
    rejections = rng.poisson(0.4, n)
    reopens = rng.poisson(0.15, n)
    since_update = rng.exponential(2.5, n).round(1)

    remaining_hours = (100 - progress) / 100 * estimated
    pressure = np.clip(remaining_hours / np.maximum(days_left + 1, 1), 0, 12)
    logit = (-3.2 + 0.45 * pressure + 0.18 * open_tasks + 0.6 * rejections + 0.7 * reopens
             + 0.15 * since_update + 0.08 * (priority - 2) + 2.0 * (days_left < 0)
             + rng.normal(0, 0.8, n))
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)

    columns = {"progress": progress, "days_to_deadline": days_left, "priority": priority,
               "estimated_hours": estimated, "hours_logged": logged, "open_task_count": open_tasks,
               "rejection_count": rejections, "reopen_count": reopens, "days_since_last_update": since_update}
    X = np.column_stack([columns[name] for name in FEATURES]).astype(float)
    return X, y
