from __future__ import annotations

import ast
from typing import Any


def check_syntax(source: str) -> list[dict[str, Any]]:
    """Return syntax diagnostics without raising for invalid user input."""
    try:
        ast.parse(source)
    except SyntaxError as error:
        return [{
            "category": "SyntaxError",
            "title": "Invalid Python syntax",
            "message": error.msg,
            "line": error.lineno or 1,
            "column": error.offset or 1,
            "severity": "error",
        }]
    return []
