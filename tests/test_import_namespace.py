"""Prevent source-tree namespace aliases from bypassing installed-package tests."""

from __future__ import annotations

from pathlib import Path


def test_tests_and_maintenance_scripts_use_canonical_package_namespace() -> None:
    root = Path(__file__).resolve().parents[1]
    forbidden = "src" + ".adr_kit"
    offenders: list[str] = []

    for directory in (root / "tests", root / "scripts"):
        for path in sorted(directory.rglob("*.py")):
            if forbidden in path.read_text(encoding="utf-8"):
                offenders.append(path.relative_to(root).as_posix())

    assert offenders == [], f"replace {forbidden} with adr_kit in: {offenders}"
