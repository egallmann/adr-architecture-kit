"""Phase 0 compatibility and version-drift controls."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast, Protocol

import pytest

from tests.test_architecture_index_generator import _create_fixture
from tests.test_compiler_driver import _create_recursive_workspace

ROOT = Path(__file__).resolve().parents[1]


class PrepareCheck(Protocol):
    def __call__(self, root: Path, *, drift: bool) -> None: ...


COMPATIBILITY_CHECKER = runpy.run_path(str(ROOT / "scripts" / "check_compatibility_snapshots.py"))
canonicalize_strings = cast(
    Callable[[object], object], COMPATIBILITY_CHECKER["_canonicalize_strings"]
)
check_snapshot = cast(Callable[[Path, object], bool], COMPATIBILITY_CHECKER["_check"])
normalize_output = cast(Callable[[bytes, Path], str], COMPATIBILITY_CHECKER["_normalize_output"])
prepare_check = cast(PrepareCheck, COMPATIBILITY_CHECKER["_prepare_check"])
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


def test_cli_snapshot_output_normalizes_macos_private_prefix(tmp_path: Path) -> None:
    root = (tmp_path / "fixture").resolve()
    root.mkdir(parents=True, exist_ok=True)
    posix = root.as_posix()
    if not posix.startswith("/"):
        pytest.skip("macOS /private path aliasing is POSIX-only")

    if posix.startswith("/private/"):
        held = Path(posix.removeprefix("/private"))
        printed = posix
    else:
        held = root
        printed = f"/private{posix}"

    captured = (
        f"Project scope: arch-test ({printed})\n"
        f"ERROR {printed}/adrs/logical/ADR-L-1000-discovery.yaml\n"
    ).encode("utf-8")

    assert normalize_output(captured, held) == (
        "Project scope: arch-test (<FIXTURE_ROOT>)\n"
        "ERROR <FIXTURE_ROOT>/adrs/logical/ADR-L-1000-discovery.yaml\n"
    )


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


def test_compatibility_fixture_sources_are_byte_stable_across_hosts(tmp_path: Path) -> None:
    basic_root = tmp_path / "basic"
    recursive_root = tmp_path / "recursive"
    _create_fixture(basic_root)
    _create_recursive_workspace(recursive_root)

    fixture_paths = (*basic_root.rglob("*.yaml"), *recursive_root.rglob("*.yaml"))
    assert fixture_paths
    for path in fixture_paths:
        assert b"\r" not in path.read_bytes(), path


def test_drift_fixture_is_byte_stable_across_hosts(tmp_path: Path) -> None:
    root = tmp_path / "drift"
    _create_fixture(root)

    prepare_check(root, drift=True)

    assert (root / "adrs" / "manifest.yaml").read_bytes() == b"drifted\n"
