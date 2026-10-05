from __future__ import annotations

import ast
from typing import Any


RISK_MESSAGES = {
    "eval": "Dynamic evaluation can execute untrusted input.",
    "exec": "Dynamic execution can execute arbitrary code.",
    "system": "Shell execution can inject operating-system commands.",
    "Popen": "Process execution needs strict argument and input validation.",
    "run": "Process execution needs strict argument and input validation.",
    "loads": "Deserializing untrusted data can execute malicious payloads.",
}


def analyze_security(source: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
            if name in RISK_MESSAGES:
                issues.append({
                    "category": "Security",
                    "title": f"Review use of {name}()",
                    "message": RISK_MESSAGES[name],
                    "line": node.lineno,
                    "column": node.col_offset + 1,
                    "severity": "warning",
                    "rule": f"unsafe-{name.lower()}",
                })
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and any(token in target.id.lower() for token in ("password", "secret", "api_key", "token")):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        issues.append({
                            "category": "Security",
                            "title": "Possible hardcoded secret",
                            "message": "Move credentials to environment variables or a secrets manager.",
                            "line": node.lineno,
                            "column": node.col_offset + 1,
                            "severity": "warning",
                            "rule": "hardcoded-secret",
                        })
    return issues
