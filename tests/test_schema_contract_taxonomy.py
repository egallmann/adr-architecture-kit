"""Deterministic verification for the family-first schema taxonomy."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from posixpath import normpath
from urllib.parse import urldefrag, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO_ROOT / "tests" / "fixtures" / "schema-contract-inventory.json"


def _inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _walk_refs(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                found.append(child)
            found.extend(_walk_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_refs(child))
    return found


def test_frozen_inventory_is_exact_and_target_membership_is_preserved() -> None:
    inventory = _inventory()
    records = inventory["records"]
    assert inventory["discovered_counts"] == {"canonical": 49, "package_mirrors": 45}
    assert len(records) == 49
    assert len({record["canonical_path"] for record in records}) == 49
    assert len({record["target_path"] for record in records}) == 49

    for record in records:
        target = REPO_ROOT / record["target_path"]
        assert target.is_file(), target
        assert target.read_bytes()  # the fixture must never describe an empty contract
        import hashlib

        assert hashlib.sha256(target.read_bytes()).hexdigest() == record["sha256"]


def test_only_stable_v1_is_a_bare_numeric_root_exception() -> None:
    for record in _inventory()["records"]:
        target = record["target_path"]
        if target.startswith("schema/v"):
            assert target.startswith("schema/v1.0/")


def test_explicit_package_mirror_mappings_are_byte_equal() -> None:
    for record in _inventory()["records"]:
        mirror = record["package_mirror_path"]
        if not mirror:
            continue
        assert (REPO_ROOT / mirror).read_bytes() == (
            REPO_ROOT / record["target_path"]
        ).read_bytes()


def test_schema_refs_are_uri_well_formed_and_local_targets_exist() -> None:
    records = _inventory()["records"]
    target_by_canonical = {r["canonical_path"]: r["target_path"] for r in records}
    for record in _inventory()["records"]:
        schema_path = REPO_ROOT / record["target_path"]
        document = json.loads(schema_path.read_text(encoding="utf-8"))
        for reference in _walk_refs(document):
            parsed = urlparse(reference)
            assert not parsed.scheme or parsed.scheme in {"http", "https"}
            path, _fragment = urldefrag(reference)
            if not path or parsed.scheme:
                continue
            # Resolve against the frozen pre-relocation path, then project
            # through the approved inventory mapping. This checks URI
            # integrity independently of the new filesystem placement.
            old_ref = normpath(str(PurePosixPath(record["canonical_path"]).parent / path))
            assert old_ref in target_by_canonical, (record["canonical_path"], reference)
            assert (REPO_ROOT / target_by_canonical[old_ref]).is_file()


def test_fixture_is_explicitly_non_authoritative() -> None:
    assert _inventory()["authority"] == "NON-AUTHORITATIVE VERIFICATION SNAPSHOT"


def test_active_references_do_not_use_retired_canonical_paths() -> None:
    """Active docs/scripts/tests point at family-first paths, not retired roots."""
    retired = ("schema/v1.1/", "schema/v1.2/", "schema/v1.3/", "schema/v1.5/", "schema/v2.0/")
    roots = ("README.md", "CONTRIBUTING.md", "docs", "scripts", "tests", "src/adr_kit")
    ignored = {
        INVENTORY_PATH,
        Path(__file__),
        REPO_ROOT / "docs" / "design-journal",
        # Golden projections preserve historical ADR text as derived snapshots;
        # they are not active path consumers.
        REPO_ROOT / "tests" / "golden" / "expected",
    }
    offenders: list[str] = []
    for root in roots:
        base = REPO_ROOT / root
        paths = [base] if base.is_file() else base.rglob("*")
        for path in paths:
            if (
                path in ignored
                or any(parent in ignored for parent in path.parents)
                or not path.is_file()
                or ".tmp" in path.parts
                or path.suffix.lower() not in {".md", ".py", ".yaml", ".yml"}
            ):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(token in text for token in retired):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, "retired canonical schema paths remain in active files: " + ", ".join(offenders)
