"""Deterministic AST checks. The code is only PARSED (ast), never executed or imported."""
import ast

SECRET_WORDS = ("password", "passwd", "secret", "api_key", "apikey", "token")


def _f(rule_id, severity, category, line, message, why, fix):
    return {"rule_id": rule_id, "severity": severity, "category": category, "line": line,
            "message": message, "explanation": why, "suggestion": fix, "tool": "ast"}


def _call_name(node):
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    return ""


def run_ast_rules(tree):
    findings = []
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    def inside_try(node):
        while node in parents:
            node = parents[node]
            if isinstance(node, ast.Try):
                return True
        return False

    imported, used = {}, set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = (alias.asname or alias.name).split(".")[0]
                if name != "*":
                    imported[name] = node.lineno
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name in ("eval", "exec"):
                findings.append(_f("AST001", "high", "security", node.lineno, f"Use of {name}()",
                                   f"{name}() runs arbitrary text as code; unvalidated input can take over the program.",
                                   "Use ast.literal_eval for literals, or avoid dynamic code execution."))
            if name in ("os.system", "os.popen") or any(
                    k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True
                    for k in node.keywords):
                findings.append(_f("AST002", "high", "security", node.lineno, "Shell command execution",
                                   "Commands built as strings can be hijacked by special characters (command injection).",
                                   "Use subprocess.run([...]) with an argument list and no shell=True."))
            if name in ("int", "float") and node.args and isinstance(node.args[0], ast.Call) \
                    and _call_name(node.args[0]) == "input" and not inside_try(node):
                findings.append(_f("AST003", "low", "input_validation", node.lineno,
                                   f"{name}(input()) without error handling",
                                   "Typing letters instead of a number raises ValueError and crashes the program.",
                                   "Wrap the conversion in try/except ValueError and ask again."))
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(_f("AST004", "medium", "error_handling", node.lineno, "Bare 'except:'",
                               "It also catches KeyboardInterrupt/SystemExit and hides real bugs.",
                               "Catch specific exceptions, e.g. 'except ValueError:'."))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append(_f("AST005", "medium", "bug_risk", default.lineno,
                                       f"Mutable default argument in '{node.name}'",
                                       "The default object is created once and shared between calls, causing surprising state.",
                                       "Use None as the default and create the list/dict inside the function."))
            assigned, loaded = {}, set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name):
                    if isinstance(sub.ctx, ast.Store):
                        assigned.setdefault(sub.id, sub.lineno)
                    else:
                        loaded.add(sub.id)
            declared = {n for s in ast.walk(node) if isinstance(s, (ast.Global, ast.Nonlocal)) for n in s.names}
            for name, line in assigned.items():
                if name not in loaded and name not in declared and not name.startswith("_"):
                    findings.append(_f("AST006", "low", "unused_code", line, f"Variable '{name}' is assigned but never used",
                                       "Unused variables often mean a typo or unfinished logic.",
                                       "Remove it, or use it. Prefix with '_' if it is intentionally unused."))
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) and node.value.value:
            for target in node.targets:
                if isinstance(target, ast.Name) and any(w in target.id.lower() for w in SECRET_WORDS):
                    findings.append(_f("AST007", "medium", "security", node.lineno,
                                       f"Possible hardcoded secret in '{target.id}'",
                                       "Secrets in source code leak through version control and shared files.",
                                       "Read secrets from environment variables or a secrets manager."))

    for name, line in imported.items():
        if name not in used:
            findings.append(_f("AST008", "low", "unused_code", line, f"'{name}' imported but unused",
                               "Unused imports add clutter and can hide real dependencies.", "Remove the import."))
    return findings
