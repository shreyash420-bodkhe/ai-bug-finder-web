from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

from .bug_detector import detect_bugs


def analyze_project_folder(project_dir: str | Path, run_code: bool = False) -> dict[str, Any]:
    """Analyze every Python file in a project folder and write corrected files back to disk."""
    root = Path(project_dir)
    if not root.exists():
        raise FileNotFoundError(f"Project folder does not exist: {root}")

    python_files = sorted(path for path in root.rglob("*.py") if path.is_file())
    issue_entries: list[dict[str, Any]] = []
    fixed_files: list[str] = []
    summary = {"total": 0, "errors": 0, "warnings": 0}

    for file_path in python_files:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        result = detect_bugs(source, run_code=run_code)
        issues = result.get("issues", [])
        for issue in issues:
            issue_record = dict(issue)
            issue_record["file"] = str(file_path.relative_to(root))
            issue_entries.append(issue_record)

        summary["total"] += len(issues)
        summary["errors"] += sum(issue.get("severity") == "error" for issue in issues)
        summary["warnings"] += sum(issue.get("severity") == "warning" for issue in issues)

        fixed_code = result.get("fixed_code")
        if fixed_code is not None:
            file_path.write_text(fixed_code, encoding="utf-8")
            fixed_files.append(str(file_path.relative_to(root)))

    return {
        "files_analyzed": len(python_files),
        "fixed_files": fixed_files,
        "summary": summary,
        "issues": issue_entries,
    }


def create_fixed_project_zip(project_dir: str | Path, zip_name: str | None = None) -> bytes:
    """Create a zipped copy of a project folder with the corrected files included."""
    root = Path(project_dir)
    archive_name = zip_name or f"{root.name or 'project'}-fixed"
    output = io.BytesIO()

    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(root.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, arcname=f"{archive_name}/{file_path.relative_to(root).as_posix()}")

    return output.getvalue()
