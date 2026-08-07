"""Phase 0 compatibility and version-drift controls."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPATIBILITY_CHECKER = runpy.run_path(str(ROOT / "scripts" / "check_compatibility_snapshots.py"))
canonicalize_strings = cast(
    Callable[[object], object], COMPATIBILITY_CHECKER["_canonicalize_strings"]
)
check_snapshot = cast(Callable[[Path, object], bool], COMPATIBILITY_CHECKER["_check"])
normalize_output = cast(Callable[[bytes, Path], str], COMPATIBILITY_CHECKER["_normalize_output"])
write_snapshot = cast(Callable[[Path, object], None], COMPATIBILITY_CHECKER["_write"])


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


@pytest.mark.parametrize(
    "captured",
    (b"first\nsecond\n", b"first\r\nsecond\r\n", b"first\rsecond\r"),
)
def test_cli_snapshot_output_normalizes_all_host_newlines(
    captured: bytes,
    tmp_path: Path,
) -> None:
    assert normalize_output(captured, tmp_path) == "first\nsecond\n"


def test_snapshot_writer_canonicalizes_nested_text_and_physical_newlines(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"

    write_snapshot(snapshot, {"nested": [{"stdout": "first\r\nsecond\r"}]})

    assert b"\r" not in snapshot.read_bytes()
    assert json.loads(snapshot.read_text(encoding="utf-8")) == {
        "nested": [{"stdout": "first\nsecond\n"}]
    }


def test_snapshot_checker_rejects_noncanonical_committed_text(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text('{"stdout": "first\\r\\nsecond"}\n', encoding="utf-8")

    assert canonicalize_strings("first\r\nsecond") == "first\nsecond"
    assert not check_snapshot(snapshot, {"stdout": "first\nsecond"})
