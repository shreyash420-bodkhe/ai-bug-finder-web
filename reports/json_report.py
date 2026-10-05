from __future__ import annotations

import json
from typing import Any

from .report_generator import build_report


def create_json_report(source: str, result: dict[str, Any]) -> str:
    return json.dumps(build_report(source, result), indent=2)
