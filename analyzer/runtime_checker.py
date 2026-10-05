from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import re
import shutil
from typing import Any


def check_runtime(source: str, timeout_seconds: float = 2.0) -> list[dict[str, Any]]:
    """Run code locally or in a restricted Docker container when configured."""
    try:
        sandbox = os.getenv("BUGFINDER_RUNTIME_SANDBOX", "local").lower()
        if sandbox == "docker":
            if not shutil.which("docker"):
                return [{
                    "category": "RuntimeSandboxError",
                    "title": "Docker sandbox is unavailable",
                    "message": "Set BUGFINDER_RUNTIME_SANDBOX=local or install Docker before running smoke tests.",
                    "line": 1,
                    "column": 1,
                    "severity": "warning",
                    "rule": "sandbox-unavailable",
                    "output": "",
                }]
            command = [
                "docker", "run", "--rm", "--network", "none", "--cpus", "0.5",
                "--memory", "128m", "--pids-limit", "64", "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "python:3.12-slim",
                "python", "-I", "-c", source,
            ]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
        else:
            with tempfile.TemporaryDirectory(prefix="bugfinder-runtime-") as working_dir:
                environment = {
                    key: value
                    for key, value in os.environ.items()
                    if key in {"PATH", "SystemRoot", "WINDIR", "TEMP", "TMP"}
                }
                completed = subprocess.run(
                    [sys.executable, "-I", "-c", source],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    cwd=working_dir,
                    env=environment,
                    start_new_session=True,
                )
    except subprocess.TimeoutExpired:
        return [{
            "category": "RuntimeTimeout",
            "title": "Possible infinite loop",
            "message": f"Execution exceeded the {timeout_seconds:g}-second smoke-test limit.",
            "line": 1,
            "column": 1,
            "severity": "warning",
            "rule": "runtime-timeout",
            "output": "",
        }]
    if completed.returncode != 0:
        error_text = completed.stderr.strip()
        match = re.search(r"([A-Za-z]+Error):\s*(.*)", error_text)
        category = match.group(1) if match else "RuntimeError"
        message = match.group(2) if match else error_text.splitlines()[-1] if error_text else "Code exited with an error."
        return [{
            "category": category,
            "title": category,
            "message": message,
            "line": 1,
            "column": 1,
            "severity": "error",
            "output": completed.stdout,
        }]
    return [{
        "category": "Runtime",
        "title": "Execution completed",
        "message": "Code ran without raising an exception.",
        "line": 1,
        "column": 1,
        "severity": "success",
        "output": completed.stdout,
    }]
