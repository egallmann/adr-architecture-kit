"""Canonical ``schema/v*.*`` JSON must match bundled ``src/adr_kit/schema/v*_*``.

Mirrors ``Check package schema parity`` in ``.github/workflows/adr-governance.yml``.
Keeps installs that load schemas via ``importlib.resources`` aligned with repo-root authority.
"""

from __future__ import annotations

import filecmp
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _schema_parity_mismatches(root: Path) -> list[str]:
    mismatches: list[str] = []
    for version in ("v1.0", "v1.1"):
        canonical_dir = root / "schema" / version
        bundled_dir = root / "src" / "adr_kit" / "schema" / version.replace(".", "_")
        for canonical in sorted(canonical_dir.glob("*.json")):
            bundled = bundled_dir / canonical.name
            if not bundled.exists():
                mismatches.append(f"MISSING in package bundle: {bundled}")
            elif not filecmp.cmp(canonical, bundled, shallow=False):
                mismatches.append(f"DRIFT: {canonical} vs {bundled}")
    return mismatches


def test_package_json_schema_canonical_matches_bundled_copies():
    mismatches = _schema_parity_mismatches(REPO_ROOT)
    assert not mismatches, (
        "schema/ must byte-match src/adr_kit/schema/ (see adr-governance.yml):\n  "
        + "\n  ".join(mismatches)
    )
