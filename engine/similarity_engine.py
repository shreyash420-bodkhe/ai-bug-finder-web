from __future__ import annotations

import re
from typing import Any


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", text.lower()))


def similarity_score(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def rank_similar(issues: list[dict[str, Any]], catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for issue in issues:
        text = f"{issue.get('category', '')} {issue.get('title', '')} {issue.get('message', '')}"
        candidates = sorted(catalog, key=lambda item: similarity_score(text, json_text(item)), reverse=True)
        ranked.append({**issue, "similar_matches": candidates[:3]})
    return ranked


def json_text(item: dict[str, Any]) -> str:
    return " ".join(str(value) for value in item.values())
