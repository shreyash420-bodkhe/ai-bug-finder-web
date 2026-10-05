from __future__ import annotations

import ast
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"


def _summary(issues: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(issues),
        "errors": sum(issue.get("severity") == "error" for issue in issues),
        "warnings": sum(issue.get("severity") == "warning" for issue in issues),
    }


FRIENDLY_MESSAGES = {
    "NameError": "Python cannot find this variable or function. Define it first or import it before using it.",
    "TypeError": "This operation uses incompatible value types. Convert the values or change the operation.",
    "SyntaxError": "Python cannot understand this code structure. Check the colon, brackets, quotes, and indentation near this line.",
    "Security": "This code uses an operation that may execute commands or code. Replace it with a safer API before using untrusted input.",
    "LogicError": "The code may run, but its behavior is probably not what you intended. Check the condition or control flow.",
    "RuntimeTimeout": "The code did not finish quickly enough. Check for an infinite loop or reduce the amount of work.",
}


def _friendly_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    friendly: list[dict[str, Any]] = []
    for issue in issues:
        updated = dict(issue)
        if "message" in issue:
            updated["message"] = FRIENDLY_MESSAGES.get(issue.get("category"), issue["message"])
        friendly.append(updated)
    return friendly


def _local_response(local_result: dict[str, Any]) -> dict[str, Any]:
    issues = _friendly_issues(local_result.get("issues", []))
    summary = local_result.get("summary", {})
    if issues:
        explanation = (
            f"The local analyzers found {summary.get('total', len(issues))} issue(s). "
            "Review the findings and the conservative fix before applying it."
        )
    else:
        explanation = "The local analyzers did not find a supported issue pattern in this file."
    if not local_result.get("fixed_code") and issues:
        explanation += " Local mode does not invent missing variables or program requirements; add an AI API key for a full-code review."
    return {
        "source": "local analyzer",
        "explanation": explanation,
        "issues": issues,
        "summary": _summary(issues),
        "fixed_code": local_result.get("fixed_code"),
    }


def _parse_model_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1])
    result = json.loads(cleaned)
    if not isinstance(result, dict):
        raise ValueError("The assistant response was not a JSON object.")
    return result


def _validated_fixed_code(fixed_code: Any) -> str | None:
    if not isinstance(fixed_code, str) or not fixed_code.strip():
        return None
    try:
        ast.parse(fixed_code)
    except SyntaxError:
        return None
    return fixed_code


def _validated_line_number(value: Any, line_count: int) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if isinstance(value, int) and 1 <= value <= line_count:
        return value
    return None


def _model_response(
    source: str,
    filename: str,
    request: str,
    local_result: dict[str, Any],
    api_key: str,
    model: str,
    endpoint: str,
    history_context: list[dict[str, Any]],
) -> dict[str, Any]:
    prompt = {
        "filename": filename,
        "request": request or "Identify and fix the supported errors in this file.",
        "local_findings": local_result.get("issues", []),
        "previous_reviews": history_context,
        "source_lines": [
            {"line": line_number, "code": line}
            for line_number, line in enumerate(source.splitlines(), start=1)
        ],
        "source_code": source,
    }
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful Python code-review assistant. Identify real bugs, explain them "
                    "briefly, and return a complete corrected file only when a correction is clear. "
                    "Never invent missing requirements or secrets. Return JSON with exactly these keys: "
                    "explanation (string), issues (array of objects with title, message, solution, "
                    "line (the exact 1-based source line number, or null if it cannot be located), severity, "
                    "and optional code_solution), "
                    "fixed_code (string or null). Use previous_reviews as project-specific context, "
                    "but verify the current source independently and do not blindly repeat old fixes. "
                    "Use the supplied source_lines map for all line numbers."
                ),
            },
            {"role": "user", "content": json.dumps(prompt)},
        ],
    }
    request_data = json.dumps(body).encode("utf-8")
    http_request = Request(
        endpoint,
        data=request_data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(http_request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    result = _parse_model_content(content)
    fixed_code = _validated_fixed_code(result.get("fixed_code"))
    raw_issues = result.get("issues", [])
    line_count = len(source.splitlines())
    issues = []
    if isinstance(raw_issues, list):
        for issue in raw_issues:
            if isinstance(issue, dict):
                normalized_issue = dict(issue)
                normalized_issue["line"] = _validated_line_number(issue.get("line"), line_count)
                issues.append(normalized_issue)
    return {
        "source": f"AI model ({model})",
        "explanation": str(result.get("explanation", "The assistant reviewed the file.")),
        "issues": issues,
        "summary": _summary(issues),
        "fixed_code": fixed_code,
    }


def analyze_with_ai(
    source: str,
    filename: str,
    request: str,
    local_result: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    endpoint: str = DEFAULT_ENDPOINT,
    history_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Review code locally, optionally augmenting the result with an OpenAI-compatible model."""
    resolved_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_key:
        return _local_response(local_result)
    try:
        return _model_response(
            source,
            filename,
            request,
            local_result,
            resolved_key,
            model,
            endpoint,
            history_context or [],
        )
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError, ValueError) as error:
        fallback = _local_response(local_result)
        fallback["source"] = "local analyzer (AI unavailable)"
        fallback["explanation"] += f" The optional AI request could not be completed: {error}."
        return fallback
