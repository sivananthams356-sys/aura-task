"""Pure unit tests for the static-analysis module (no Flask needed)."""
from app.analysis.runner import analyze_python


def _rules(code):
    return {f["rule_id"] for f in analyze_python(code)["findings"]}


def test_syntax_error_gives_single_critical_finding():
    r = analyze_python("def broken(:\n    pass")
    assert r["syntax_valid"] is False and len(r["findings"]) == 1
    assert r["findings"][0]["rule_id"] == "SYNTAX" and r["findings"][0]["line"] == 1


def test_clean_code_has_no_builtin_findings():
    assert analyze_python("def add(a, b):\n    return a + b\n", use_ruff=False)["findings"] == []


def test_risky_patterns_detected():
    code = ("import os, sys\n"
            "def f(x, items=[]):\n    unused = 1\n    eval('1')\n    os.system('ls ' + x)\n"
            "    password = 'hunter2'\n    n = int(input('n'))\n    return n\n"
            "try:\n    pass\nexcept:\n    pass\n")
    rules = {f["rule_id"] for f in analyze_python(code, use_ruff=False)["findings"]}
    assert {"AST001", "AST002", "AST003", "AST004", "AST005", "AST006", "AST007", "AST008"} <= rules


def test_every_finding_has_all_required_fields():
    findings = analyze_python("import os\neval('1')\n")["findings"]
    assert findings
    for f in findings:
        assert {"rule_id", "severity", "category", "line", "message", "explanation", "suggestion", "tool"} <= set(f)
        assert f["severity"] in ("info", "low", "medium", "high", "critical") and f["explanation"] and f["suggestion"]


def test_input_conversion_inside_try_is_not_flagged():
    code = "try:\n    n = int(input('n'))\nexcept ValueError:\n    n = 0\nprint(n)\n"
    assert "AST003" not in _rules(code)


def test_extremely_nested_input_does_not_crash():
    r = analyze_python("(" * 100000)
    assert r["syntax_valid"] is False and r["findings"][0]["rule_id"] == "SYNTAX"


def test_tool_notes_are_honest_when_ruff_missing(monkeypatch=None):
    r = analyze_python("import os\n")
    assert "ast" in r["tools_used"]
    assert ("ruff" in r["tools_used"]) != bool(r["notes"])       # either Ruff ran, or a note says it did not
