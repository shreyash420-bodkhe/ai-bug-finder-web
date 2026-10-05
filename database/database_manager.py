from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BugDatabase:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path(__file__).with_name("bugs.json"))

    def load(self) -> list[dict[str, Any]]:
        with self.path.open(encoding="utf-8") as file:
            return json.load(file)

    def load_catalog(self, name: str) -> Any:
        path = self.path.with_name(name)
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    def solutions(self) -> dict[str, str]:
        return self.load_catalog("solutions.json")

    def fixes(self) -> dict[str, dict[str, Any]]:
        return self.load_catalog("fixes.json")

    def code_solutions(self) -> dict[str, str]:
        return self.load_catalog("code_solutions.json")

    def find_matches(self, text: str) -> list[dict[str, Any]]:
        import re

        return [
            bug for bug in self.load()
            if re.search(bug["pattern"], text, flags=re.IGNORECASE)
        ]
