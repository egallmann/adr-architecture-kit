"""Canonical schema JSON must match explicit package mirror mappings.

Mirrors ``Check package schema parity`` in ``.github/workflows/adr-governance.yml``.
Keeps installs that load schemas via ``importlib.resources`` aligned with repo-root authority.
"""

from __future__ import annotations

import filecmp
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY = REPO_ROOT / "tests" / "fixtures" / "schema-contract-inventory.json"


def _schema_parity_mismatches(root: Path) -> list[str]:
    mismatches: list[str] = []
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    for record in inventory["records"]:
        mirror = record["package_mirror_path"]
        if not mirror:
            continue
        canonical = root / record["target_path"]
        bundled = root / mirror
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


def test_promotion_contract_schema_mirror_matches_bundled_copy():
    canonical = (
        REPO_ROOT
        / "contracts"
        / "design-journal-promotion-contract"
        / "v0.1"
        / "schema.json"
    )
    bundled = (
        REPO_ROOT
        / "src"
        / "adr_kit"
        / "promotion"
        / "schemas"
        / "promotion_contract_v0_1.json"
    )
    assert canonical.is_file(), f"missing canonical mirror: {canonical}"
    assert bundled.is_file(), f"missing packaged bundle: {bundled}"
    assert filecmp.cmp(canonical, bundled, shallow=False), (
        "contracts/design-journal-promotion-contract/v0.1/schema.json must byte-match "
        "src/adr_kit/promotion/schemas/promotion_contract_v0_1.json"
    )
