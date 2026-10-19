"""Static analysis entry point. This is RULE-BASED analysis, not machine learning."""
import ast

from app.analysis.ast_rules import run_ast_rules
from app.analysis.ruff_runner import run_ruff

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
MAX_FINDINGS = 200


def _syntax_finding(line, message):
    return {"rule_id": "SYNTAX", "severity": "critical", "category": "syntax", "line": line, "message": message,
            "explanation": "Python cannot run code that has a syntax error; the program stops before it starts.",
            "suggestion": "Fix the syntax at the reported line (check brackets, colons and indentation).",
            "tool": "ast"}


def analyze_python(code, use_ruff=True):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"syntax_valid": False, "findings": [_syntax_finding(exc.lineno, f"Syntax error: {exc.msg}")],
                "tools_used": ["ast"], "notes": []}
    except (RecursionError, MemoryError, ValueError):
        return {"syntax_valid": False, "findings": [_syntax_finding(None, "The code could not be parsed safely")],
                "tools_used": ["ast"], "notes": []}

    findings, tools, notes = run_ast_rules(tree), ["ast"], []
    if use_ruff:
        ruff_findings, note = run_ruff(code)
        if note:
            notes.append(note)
        else:
            tools.append("ruff")
            # Drop built-in findings that Ruff already reports on the same line and category.
            seen = {(f["line"], f["category"]) for f in ruff_findings}
            findings = [f for f in findings if (f["line"], f["category"]) not in seen] + ruff_findings
    findings.sort(key=lambda f: (f["line"] or 0, SEVERITY_ORDER[f["severity"]]))
    if len(findings) > MAX_FINDINGS:
        findings = findings[:MAX_FINDINGS]
        notes.append(f"Only the first {MAX_FINDINGS} findings are shown.")
    return {"syntax_valid": True, "findings": findings, "tools_used": tools, "notes": notes}
