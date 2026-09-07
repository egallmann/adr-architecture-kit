"""Packaged compatibility contract resources must mirror repository authority."""

from __future__ import annotations

import filecmp
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cli_surface_snapshot_mirror_matches_bundled_copy() -> None:
    canonical = REPO_ROOT / "contracts" / "compatibility" / "cli-surface.json"
    bundled = REPO_ROOT / "src" / "adr_kit" / "compatibility" / "cli-surface.json"
    assert bundled.is_file(), f"MISSING in package bundle: {bundled}"
    assert filecmp.cmp(canonical, bundled, shallow=False), f"DRIFT: {canonical} vs {bundled}"


def test_cli_surface_snapshot_loads_from_package_resources() -> None:
    from adr_kit.compatibility import load_cli_surface_snapshot

    payload = load_cli_surface_snapshot()
    assert isinstance(payload["commands"], dict)
    assert "validate" in payload["commands"]
    assert "generate-system-overview" in payload["commands"]


def test_python_surface_snapshot_mirror_matches_bundled_copy() -> None:
    canonical = REPO_ROOT / "contracts" / "compatibility" / "python-surface.json"
    bundled = REPO_ROOT / "src" / "adr_kit" / "compatibility" / "python-surface.json"
    assert bundled.is_file(), f"MISSING in package bundle: {bundled}"
    assert filecmp.cmp(canonical, bundled, shallow=False), f"DRIFT: {canonical} vs {bundled}"


def test_host_capability_snapshot_mirror_matches_bundled_copy() -> None:
    canonical = REPO_ROOT / "contracts" / "compatibility" / "host-capabilities.json"
    bundled = REPO_ROOT / "src" / "adr_kit" / "compatibility" / "host-capabilities.json"
    assert bundled.is_file(), f"MISSING in package bundle: {bundled}"
    assert filecmp.cmp(canonical, bundled, shallow=False), f"DRIFT: {canonical} vs {bundled}"


def test_host_capability_snapshot_loads_from_package_resources() -> None:
    from adr_kit.compatibility import load_host_capabilities_snapshot

    payload = load_host_capabilities_snapshot()
    assert payload["peer_host_operations"]
    assert payload["pending_host_operations"]
