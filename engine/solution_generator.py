from __future__ import annotations

from typing import Any

from database import BugDatabase


def generate_solutions(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    database = BugDatabase()
    catalog = database.solutions()
    code_catalog = database.code_solutions()
    solutions: list[dict[str, Any]] = []
    for issue in issues:
        category = issue.get("category", "")
        rule = issue.get("rule", "")
        fallback = catalog.get(category, "Inspect the reported line and add a focused test for this case.")
        code_fallback = code_catalog.get(category) or code_catalog.get(rule)
        solutions.append({
            **issue,
            "solution": issue.get("solution") or fallback,
            "code_solution": issue.get("code_solution") or code_fallback,
        })
    return solutions
