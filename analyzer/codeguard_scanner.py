from __future__ import annotations

from typing import Any

from .security_analyzer import analyze_security


def scan_security(source: str) -> list[dict[str, Any]]:
    return analyze_security(source)
