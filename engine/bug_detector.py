from __future__ import annotations

from typing import Any

from analyzer import analyze_ast, analyze_logic, check_runtime, check_syntax, scan_security
from .bug_matcher import match_bugs
from .fix_generator import generate_fix
from .solution_generator import generate_solutions


def detect_bugs(source: str, run_code: bool = True) -> dict[str, Any]:
    issues = check_syntax(source)
    if not issues:
        issues.extend(analyze_ast(source))
        issues.extend(scan_security(source))
        issues.extend(analyze_logic(source))
        if run_code and not any(issue.get("category") == "Security" for issue in issues):
            runtime = check_runtime(source)
            if runtime and runtime[0]["severity"] != "success":
                statically_detected_type_error_lines = {
                    issue.get("line")
                    for issue in issues
                    if issue.get("rule") == "literal-type-error"
                }
                issues.extend(
                    issue
                    for issue in runtime
                    if not (
                        issue.get("category") == "TypeError"
                        and issue.get("line") in statically_detected_type_error_lines
                    )
                )
    issues = generate_solutions(match_bugs(issues))
    fixed_code = generate_fix(source, issues)
    errors = sum(issue.get("severity") == "error" for issue in issues)
    warnings = sum(issue.get("severity") == "warning" for issue in issues)
    return {"issues": issues, "summary": {"total": len(issues), "errors": errors, "warnings": warnings}, "fixed_code": fixed_code}
