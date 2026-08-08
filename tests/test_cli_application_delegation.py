"""CLI behavior preservation and application-service delegation contracts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from adr_kit.api import _operations as application_service
from adr_kit.cli.main import cli
from tests.test_architecture_index_generator import _create_fixture

ROOT = Path(__file__).resolve().parents[1]


def _check_snapshots() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_compatibility_snapshots.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_validate_delegation_matches_behavior_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegate = getattr(application_service, "validate_for_cli", None)
    assert callable(delegate), "validate CLI must delegate to the shared application service"
    calls = 0

    def tracking_delegate(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return delegate(*args, **kwargs)

    monkeypatch.setattr(application_service, "validate_for_cli", tracking_delegate)
    root = tmp_path / "project"
    _create_fixture(root)

    result = CliRunner().invoke(cli, ["validate", "--scope", str(root)])

    assert result.exit_code == 0, result.output
    assert calls == 1


def test_compile_delegation_matches_behavior_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegate = getattr(application_service, "compile_for_cli", None)
    assert callable(delegate), "compile CLI must delegate to the shared application service"
    calls = 0

    def tracking_delegate(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return delegate(*args, **kwargs)

    monkeypatch.setattr(application_service, "compile_for_cli", tracking_delegate)
    root = tmp_path / "project"
    _create_fixture(root)

    result = CliRunner().invoke(
        cli,
        [
            "compile",
            "--scope",
            str(root),
            "--dry-run",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == 1


def test_cli_surface_snapshot_is_unchanged() -> None:
    result = _check_snapshots()
    assert result.returncode == 0, result.stdout + result.stderr


def test_cli_generated_artifacts_are_byte_identical() -> None:
    result = _check_snapshots()
    assert result.returncode == 0, result.stdout + result.stderr
