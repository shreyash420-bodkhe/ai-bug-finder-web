from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any


def build_report(source: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_lines": len(source.splitlines()),
        **result,
    }


def report_as_json(source: str, result: dict[str, Any]) -> str:
    return json.dumps(build_report(source, result), indent=2)


def report_as_markdown(source: str, result: dict[str, Any]) -> str:
    report = build_report(source, result)
    lines = ["# AI Bug Finder Report", "", f"Generated: {report['generated_at']}", "", "## Summary", "", f"- Total findings: {report['summary']['total']}", f"- Errors: {report['summary']['errors']}", f"- Warnings: {report['summary']['warnings']}", "", "## Findings", ""]
    if not report["issues"]:
        lines.append("No issues detected.")
    for issue in report["issues"]:
        lines.extend([f"### {issue['title']}", f"Line {issue.get('line', 1)}: {issue['message']}", "", f"**Suggested fix:** {issue['solution']}", ""])
    return "\n".join(lines)
