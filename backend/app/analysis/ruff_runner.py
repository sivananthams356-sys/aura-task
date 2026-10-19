"""Run Ruff on submitted code WITHOUT executing it. Safe subprocess use: argument list (no shell),
code passed through stdin, fixed filename label, timeout, output size cap."""
import json
import subprocess
import sys

TIMEOUT_SECONDS = 10
SELECT = "E,W,F,B,S,C90"

CATEGORY_BY_PREFIX = [("F401", "unused_code"), ("F841", "unused_code"), ("F8", "bug_risk"), ("F", "bug_risk"),
                      ("E7", "bug_risk"), ("E9", "syntax"), ("E", "style"), ("W", "style"),
                      ("B", "bug_risk"), ("S", "security"), ("C90", "maintainability")]
EXPLANATIONS = {
    "F401": "Unused imports add clutter and can hide real dependencies.",
    "F821": "Using a name that is never defined raises NameError when that line runs.",
    "F841": "A variable that is assigned but never used often signals a typo or unfinished logic.",
    "F811": "Redefining a name silently replaces the earlier definition.",
    "E722": "A bare 'except:' also catches KeyboardInterrupt/SystemExit and hides real bugs.",
    "E501": "Very long lines are hard to read and review.",
    "C901": "Highly complex functions are harder to test and more likely to hide bugs.",
    "B006": "A mutable default argument is shared between calls and causes surprising state.",
}


def _severity(code):
    if code in ("S101",) or code.startswith(("W", "E5", "E4")):
        return "info"
    if code in ("F821", "F822", "F823"):
        return "high"
    if code.startswith("S"):
        return "high" if code in ("S102", "S307", "S301", "S602", "S605", "S608") else "medium"
    if code.startswith(("B", "F8", "E7")) or code in ("F811",):
        return "medium"
    return "low"


def _category(code):
    for prefix, category in CATEGORY_BY_PREFIX:
        if code.startswith(prefix):
            return category
    return "style"


def run_ruff(code):
    """Return (findings, error_note). error_note is None on success."""
    cmd = [sys.executable, "-m", "ruff", "check", "--isolated", "--select", SELECT, "--line-length", "100",
           "--output-format", "json", "--stdin-filename", "submission.py", "-"]
    try:
        proc = subprocess.run(cmd, input=code, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return [], "Ruff timed out; only built-in checks were run."
    except OSError:
        return [], "Ruff could not be started; only built-in checks were run."
    # Ruff exits 0 (clean) or 1 (findings) and always prints a JSON list. Anything else
    # (e.g. "No module named ruff" also exits 1 but prints no JSON) counts as a failure.
    if proc.returncode not in (0, 1) or not proc.stdout.strip():
        return [], "Ruff is not installed or failed; only built-in checks were run."
    try:
        items = json.loads(proc.stdout[:2_000_000])
        if not isinstance(items, list):
            raise ValueError
    except ValueError:
        return [], "Ruff output could not be read; only built-in checks were run."
    findings = []
    for item in items:
        code_id = item.get("code") or "RUFF"
        findings.append({
            "rule_id": code_id, "severity": _severity(code_id), "category": _category(code_id),
            "line": (item.get("location") or {}).get("row"), "message": item.get("message", "")[:300],
            "explanation": EXPLANATIONS.get(code_id, f"Ruff rule {code_id} flags a common bug-risk or style problem."),
            "suggestion": f"Fix the reported issue, or read the documentation for Ruff rule {code_id}.",
            "tool": "ruff"})
    return findings, None
