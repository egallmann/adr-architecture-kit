"""R9 — identity v1.3 migration preflight/plan/seal tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from adr_kit.identity import mint_uuidv7
from adr_kit.migrators.identity_v13 import IdentityV13Migrator


def _write_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "PROJECT.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: project_metadata",
                "project:",
                '  name: "mig-test"',
                "architecture_documentation:",
                '  adr_directory: "adrs/"',
                '  architecture_namespace: "mig-test"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "adrs" / "logical").mkdir(parents=True, exist_ok=True)


def _write_logical(root: Path, adr_id: str = "ADR-L-9001") -> Path:
    path = root / "adrs" / "logical" / f"{adr_id}.yaml"
    path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                f"id: {adr_id}",
                'title: "Migration Fixture"',
                "status: accepted",
                'created_date: "2026-01-01"',
                'authors: ["test"]',
                'domains: ["test"]',
                "context: |",
                "  Fixture for identity migration.",
                "decisions:",
                "  - id: DEC-9001",
                '    summary: "Migrate identity"',
                '    rationale: "Need UUID identity."',
                "capabilities:",
                "  - id: CAP-9001",
                '    name: "Migrate"',
                '    description: "Capability under test"',
                "invariants:",
                "  - id: INV-9001",
                '    statement: "UUID identity is required"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_preflight_does_not_mint_on_blockers(tmp_path: Path) -> None:
    _write_project(tmp_path)
    # Missing architecture_namespace blocker via empty PROJECT rewrite
    (tmp_path / "PROJECT.yaml").write_text(
        'schema_version: "1.0"\ntype: project_metadata\nproject:\n  name: x\n',
        encoding="utf-8",
    )
    counter = {"n": 0}

    def mint() -> str:
        counter["n"] += 1
        return mint_uuidv7(
            timestamp_ms=1_700_000_000_000 + counter["n"], rand_bytes=bytes([counter["n"]] * 10)
        )

    migrator = IdentityV13Migrator(mint=mint)
    result = migrator.preflight(tmp_path)
    plan = migrator.plan(tmp_path)

    assert not result.ok
    assert not plan.ok
    assert migrator.mint_count == 0
    assert counter["n"] == 0


def test_plan_mints_once_after_green_preflight(tmp_path: Path) -> None:
    _write_project(tmp_path)
    _write_logical(tmp_path)
    counter = {"n": 0}

    def mint() -> str:
        counter["n"] += 1
        return mint_uuidv7(
            timestamp_ms=1_700_000_000_000 + counter["n"], rand_bytes=bytes([counter["n"]] * 10)
        )

    migrator = IdentityV13Migrator(mint=mint)
    result = migrator.plan(tmp_path)

    assert result.ok
    assert result.identity_map.architecture_namespace == "mig-test"
    assert result.identity_map.baseline_fingerprint.startswith("sha256:")
    assert len(result.identity_map.entries) >= 4  # ADR + DEC + CAP + INV
    assert migrator.mint_count == len(result.identity_map.entries)
    assert all(entry.uuid for entry in result.identity_map.entries)


def test_seal_requires_closed_judgment_queues(tmp_path: Path) -> None:
    _write_project(tmp_path)
    _write_logical(tmp_path)
    migrator = IdentityV13Migrator(
        mint=lambda: mint_uuidv7(timestamp_ms=1_700_000_000_000, rand_bytes=b"\x01" * 10)
    )
    # Force deterministic unique mints
    values = [
        mint_uuidv7(timestamp_ms=1_700_000_000_000 + i, rand_bytes=bytes([i] * 10))
        for i in range(1, 20)
    ]
    idx = {"i": 0}

    def mint() -> str:
        value = values[idx["i"]]
        idx["i"] += 1
        return value

    migrator = IdentityV13Migrator(mint=mint)
    planned = migrator.plan(tmp_path).identity_map
    for entry in planned.entries:
        if entry.classification == "review_required":
            entry.disposition = "pending"
    # Ensure at least one review-required entry for this assertion path
    planned.entries[0].classification = "review_required"
    planned.entries[0].disposition = "pending"
    planned.review_queues["alias_conflicts"] = [planned.entries[0].occurrence_key]

    with pytest.raises(ValueError, match="open judgment queues"):
        migrator.seal(planned, approver="tester", sealed_at="2026-01-01T00:00:00Z")

    sealed = migrator.seal(
        planned,
        approver="tester",
        sealed_at="2026-01-01T00:00:00Z",
        dispositions={planned.entries[0].occurrence_key: "accepted"},
    )
    assert sealed.seal["sealed"] is True
    assert sealed.seal["map_fingerprint"]
    assert migrator.verify_sealed(sealed) == []
