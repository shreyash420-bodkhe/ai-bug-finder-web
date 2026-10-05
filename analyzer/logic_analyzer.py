from __future__ import annotations

import ast
from typing import Any


def analyze_logic(source: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
            has_break = any(isinstance(child, ast.Break) for child in ast.walk(node))
            if not has_break:
                issues.append({
                    "category": "LogicError",
                    "title": "Possible infinite loop",
                    "message": "This while True loop has no break statement in its body.",
                    "line": node.lineno,
                    "column": node.col_offset + 1,
                    "severity": "warning",
                    "rule": "infinite-loop",
                })
        if isinstance(node, ast.Compare) and isinstance(node.ops[0], (ast.Is, ast.IsNot)):
            if any(isinstance(value, ast.Constant) and value.value not in (None, True, False) for value in node.comparators):
                issues.append({
                    "category": "LogicError",
                    "title": "Use equality for value comparison",
                    "message": "The 'is' operator compares object identity; use == for ordinary values.",
                    "line": node.lineno,
                    "column": node.col_offset + 1,
                    "severity": "warning",
                    "rule": "identity-comparison",
                })
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = node.left.value if isinstance(node.left, ast.Constant) else None
            right = node.right.value if isinstance(node.right, ast.Constant) else None
            left_is_string = type(left) is str
            right_is_string = type(right) is str
            left_is_number = type(left) in (int, float)
            right_is_number = type(right) in (int, float)
            if (left_is_string and right_is_number) or (left_is_number and right_is_string):
                string_type = "str"
                number_type = "int" if type(left if left_is_number else right) is int else "float"
                issues.append({
                    "category": "TypeError",
                    "title": "Cannot add a string and a number",
                    "message": (
                        f"This expression combines a {string_type} and a {number_type}. "
                        "Convert both values to the type you intend before adding them."
                    ),
                    "line": node.lineno,
                    "column": node.col_offset + 1,
                    "severity": "error",
                    "rule": "literal-type-error",
                })
    return issues
