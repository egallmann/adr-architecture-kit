"""Phase 0 compatibility and version-drift controls."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_script(relative_path: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    script = ROOT / relative_path
    assert script.is_file(), f"missing Phase 0 control: {relative_path}"
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_python_and_cli_compatibility_snapshots_match() -> None:
    result = _run_script("scripts/check_compatibility_snapshots.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_runtime_installed_metadata_and_cli_versions_match() -> None:
    result = _run_script("scripts/check_version_consistency.py")
    assert result.returncode == 0, result.stdout + result.stderr
