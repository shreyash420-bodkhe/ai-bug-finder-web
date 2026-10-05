from __future__ import annotations

import re
from typing import Any

from database import BugDatabase


def match_bugs(issues: list[dict[str, Any]], database: BugDatabase | None = None) -> list[dict[str, Any]]:
    database = database or BugDatabase()
    catalog = database.load()
    matches: list[dict[str, Any]] = []
    for issue in issues:
        text = f"{issue.get('category', '')} {issue.get('title', '')} {issue.get('message', '')}"
        match = next((bug for bug in catalog if re.search(bug["pattern"], text, re.IGNORECASE)), None)
        matches.append({**issue, "bug_id": match["id"] if match else None, "solution": match["solution"] if match else "Review the diagnostic and inspect nearby values."})
    return matches
