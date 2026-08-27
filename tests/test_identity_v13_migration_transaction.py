"""R10 — identity v1.3 migration dry-run/apply/recovery tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from adr_kit.migrators.identity_v13 import IdentityV13Migrator
from tests.support.uuidv7_fixtures import UUIDV7_SEQUENCE, sequential_mint
from tests.test_identity_v13_migrator import _write_logical, _write_project


def _mint_factory() -> tuple[IdentityV13Migrator, list[str]]:
    minted: list[str] = []
    base_mint = sequential_mint(UUIDV7_SEQUENCE)

    def mint() -> str:
        value = base_mint()
        minted.append(value)
        return value

    return IdentityV13Migrator(mint=mint), minted


def _seal_map(tmp_path: Path):
    planner, _ = _mint_factory()
    planned = planner.plan(tmp_path).identity_map
    return planner.seal(planned, approver="tester", sealed_at="2026-01-01T00:00:00Z")


def test_dry_run_does_not_mutate_sources(tmp_path: Path) -> None:
    _write_project(tmp_path)
    path = _write_logical(tmp_path)
    before = path.read_text(encoding="utf-8")
    sealed = _seal_map(tmp_path)
    applicator = IdentityV13Migrator()
    writes = applicator.apply(tmp_path, sealed, dry_run=True)

    assert writes
    assert path.read_text(encoding="utf-8") == before
    assert not (tmp_path / "adrs" / "migrations" / "canonical-identity-v13-map.yaml").exists()


def test_apply_rejects_unsealed_map(tmp_path: Path) -> None:
    _write_project(tmp_path)
    _write_logical(tmp_path)
    planner, _ = _mint_factory()
    planned = planner.plan(tmp_path).identity_map
    applicator = IdentityV13Migrator()

    with pytest.raises(ValueError, match="not sealed|fingerprint|judgment"):
        applicator.apply(tmp_path, planned)


def test_apply_is_atomic_and_recoverable(tmp_path: Path) -> None:
    _write_project(tmp_path)
    path = _write_logical(tmp_path)
    before = path.read_text(encoding="utf-8")
    sealed = _seal_map(tmp_path)
    journal = tmp_path / ".adr-kit" / "identity-v13-journal" / "fault"
    applicator = IdentityV13Migrator()

    def fault(phase: str) -> None:
        if phase.startswith("during_commit:"):
            raise RuntimeError("injected commit fault")

    with pytest.raises(RuntimeError, match="injected commit fault"):
        applicator.apply(tmp_path, sealed, fault=fault, journal_root=journal)

    assert path.read_text(encoding="utf-8") == before
    applicator.recover(journal, tmp_path)
    assert path.read_text(encoding="utf-8") == before


def test_apply_sealed_map_never_remints(tmp_path: Path) -> None:
    _write_project(tmp_path)
    _write_logical(tmp_path)
    sealed = _seal_map(tmp_path)
    expected = {entry.alias_id: entry.uuid for entry in sealed.entries}
    applicator, minted = _mint_factory()
    applicator.apply(tmp_path, sealed)

    rewritten = yaml.safe_load(
        (tmp_path / "adrs" / "logical" / "ADR-L-9001.yaml").read_text(encoding="utf-8")
    )
    assert rewritten["schema_version"] == "1.3"
    assert rewritten["alias_id"] == "ADR-L-9001"
    assert rewritten["id"] == expected["ADR-L-9001"]
    assert minted == []
    assert applicator.mint_count == 0
    map_path = tmp_path / "adrs" / "migrations" / "canonical-identity-v13-map.yaml"
    assert map_path.is_file()
