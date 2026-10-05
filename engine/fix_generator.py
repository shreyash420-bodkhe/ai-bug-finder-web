from __future__ import annotations

import re
from typing import Any

from database import BugDatabase


def generate_fix(source: str, issues: list[dict[str, Any]]) -> str | None:
    """Apply conservative fixes for patterns where the intended replacement is clear."""
    fixed = source
    changed = False
    fix_catalog = BugDatabase().fixes()
    for issue in issues:
        line = issue.get("line")
        if not line:
            continue
        rule = issue.get("rule")
        if rule in fix_catalog and not fix_catalog[rule].get("safe", False):
            continue
        lines = fixed.splitlines(keepends=True)
        if line > len(lines):
            continue
        original = lines[line - 1]
        if issue.get("rule") == "identity-comparison":
            updated = re.sub(r"\bis\s+not\b", "!=", original, count=1)
            if updated == original:
                updated = re.sub(r"\bis\b", "==", original, count=1)
            lines[line - 1] = updated
            fixed = "".join(lines)
            changed |= updated != original
        elif issue.get("rule") == "infinite-loop" and original.strip() == "while True:":
            body_start = line
            body_end = min(len(lines), line + 5)
            body = "".join(lines[body_start:body_end])
            if re.search(r"\b([A-Za-z_]\w*)\.pop\s*\(", body):
                queue_name = re.search(r"\b([A-Za-z_]\w*)\.pop\s*\(", body).group(1)
                updated = original.replace("while True", f"while {queue_name}", 1)
                lines[line - 1] = updated
                fixed = "".join(lines)
                changed |= updated != original
        elif issue.get("category") == "Security" and issue.get("rule") == "unsafe-eval":
            updated = original.replace("eval(", "ast.literal_eval(", 1)
            if updated != original and "import ast" not in fixed:
                fixed = "import ast\n" + fixed
                line += 1
            lines = fixed.splitlines(keepends=True)
            if line <= len(lines):
                lines[line - 1] = updated
                fixed = "".join(lines)
                changed |= updated != original
        elif issue.get("category") == "TypeError" and "+" in original:
            string_literal = r'(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'
            number_literal = r"-?\d+(?:\.\d+)?"
            literal_addition = re.compile(
                rf"({string_literal})\s*\+\s*({number_literal})"
                rf"|({number_literal})\s*\+\s*({string_literal})"
            )

            def convert_literal_addition(match: re.Match[str]) -> str:
                if match.group(1) is not None:
                    left, right = match.group(1), match.group(2)
                else:
                    left, right = match.group(3), match.group(4)
                return f"str({left}) + str({right})"

            updated = literal_addition.sub(convert_literal_addition, original, count=1)
            lines[line - 1] = updated
            fixed = "".join(lines)
            changed |= updated != original
        elif issue.get("category") == "SyntaxError" and "expected ':'" in issue.get("message", ""):
            stripped = original.rstrip("\r\n").rstrip()
            if stripped and not stripped.endswith(":") and re.match(r"^(\s*)(def|class|if|elif|else|for|while|try|except|finally|with|async\s+def)\b", stripped):
                newline = "\n" if original.endswith("\n") else ""
                lines[line - 1] = f"{stripped}:{newline}"
                fixed = "".join(lines)
                changed = True
    return fixed if changed else None
