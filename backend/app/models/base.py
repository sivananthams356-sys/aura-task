from datetime import datetime, timezone

ROLES = ("admin", "manager", "employee")
PRIORITIES = ("Low", "Medium", "High", "Critical")
STATUSES = ("Pending", "In Progress", "Under Review", "Completed", "Blocked")
OPEN_STATUSES = ("Pending", "In Progress", "Under Review", "Blocked")
SEVERITIES = ("info", "low", "medium", "high", "critical")
RISK_CATEGORIES = ("Low", "Medium", "High")


def utcnow():
    """Naive UTC datetime (stored that way in the database)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None
