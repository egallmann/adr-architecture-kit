"""Phase 2 RED/GREEN contracts for stable topology identity migration."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from adr_kit.cli.main import cli
from adr_kit.migrators.topology_identity import TopologyIdentityMigrator
from adr_kit.parser import ADRParser
from adr_kit.scope import ProjectScopeResolver

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "v1_2" / "physical-system-topology.yaml"


def _scope(root: Path, payload: dict):
    shutil.copy2(ROOT / "PROJECT.yaml", root / "PROJECT.yaml")
    destination = root / "adrs" / "physical-system" / "ADR-PS-9801-topology.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    resolver = ProjectScopeResolver(explicit_scope=root)
    return resolver.resolve(), destination


def _legacy_payload() -> dict:
    payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    payload["schema_version"] = "1.0"
    components = payload["component_topology"]["components"]
    components[0].pop("id")
    components[1].pop("id")
    payload["component_topology"]["relationships"][0] = {
        "from": "gateway",
        "to": "worker",
        "type": "calls",
    }
    payload["data_flows"][0]["path"] = ["gateway", "worker"]
    return payload


def test_topology_migration_is_dry_run_first_and_deterministic(tmp_path: Path) -> None:
    scope, path = _scope(tmp_path, _legacy_payload())
    before = path.read_bytes()
    migrator = TopologyIdentityMigrator()

    first = migrator.plan(scope)
    second = migrator.plan(scope)

    assert first == second
    assert not first.diagnostics
    assert path.read_bytes() == before
    assert [(item.pointer, item.after) for item in first.changes] == [
        ("/schema_version", "1.2"),
        ("/component_topology/components/0/id", "TOPO-0001"),
        ("/component_topology/components/1/id", "TOPO-0002"),
        ("/component_topology/relationships/0/from", "TOPO-0001"),
        ("/component_topology/relationships/0/to", "TOPO-0002"),
        ("/data_flows/0/path/0", "TOPO-0001"),
        ("/data_flows/0/path/1", "TOPO-0002"),
    ]


def test_topology_migration_preserves_ids_rewrites_mixed_refs_and_is_idempotent(
    tmp_path: Path,
) -> None:
    payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    scope, path = _scope(tmp_path, payload)
    migrator = TopologyIdentityMigrator()

    plan = migrator.apply(scope)
    migrated = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert plan.changed_files == (path,)
    assert [item["id"] for item in migrated["component_topology"]["components"]] == [
        "TOPO-0001",
        "TOPO-0002",
    ]
    assert migrated["component_topology"]["relationships"][0]["to"] == "TOPO-0002"
    assert migrated["data_flows"][0]["path"] == ["TOPO-0001", "TOPO-0002"]
    ADRParser().parse_physical_system_adr(path)
    assert not migrator.plan(scope).changes


@pytest.mark.parametrize(
    ("mutation", "code", "reference"),
    [
        ("ambiguous", "ambiguous_name", "gateway"),
        ("dangling_name", "dangling_reference", "missing"),
        ("dangling_id", "dangling_reference", "TOPO-9999"),
    ],
)
def test_topology_migration_refuses_ambiguous_or_dangling_references(
    tmp_path: Path, mutation: str, code: str, reference: str
) -> None:
    payload = _legacy_payload()
    if mutation == "ambiguous":
        duplicate = dict(payload["component_topology"]["components"][0])
        payload["component_topology"]["components"].append(duplicate)
    elif mutation == "dangling_name":
        payload["component_topology"]["relationships"][0]["to"] = reference
    else:
        payload["data_flows"][0]["path"][1] = reference
    scope, path = _scope(tmp_path, payload)
    before = path.read_bytes()
    migrator = TopologyIdentityMigrator()

    plan = migrator.plan(scope)

    assert any(item.code == code and reference in item.message for item in plan.diagnostics)
    with pytest.raises(ValueError, match="Topology migration blocked"):
        migrator.apply(scope)
    assert path.read_bytes() == before


def test_v12_model_rejects_dangling_topology_ids(tmp_path: Path) -> None:
    payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    payload["data_flows"][0]["path"][1] = "TOPO-9999"
    _, path = _scope(tmp_path, payload)

    with pytest.raises(Exception, match="TOPO-9999"):
        ADRParser().parse_physical_system_adr(path)


def test_topology_migration_cli_previews_then_applies(tmp_path: Path) -> None:
    _, path = _scope(tmp_path, _legacy_payload())
    runner = CliRunner()

    preview = runner.invoke(cli, ["migrate-topology-ids", "--scope", str(tmp_path)])
    assert preview.exit_code == 0
    assert "no files changed" in preview.output
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["schema_version"] == "1.0"

    applied = runner.invoke(cli, ["migrate-topology-ids", "--scope", str(tmp_path), "--apply"])
    assert applied.exit_code == 0
    assert "Applied topology migration to 1 file" in applied.output
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["schema_version"] == "1.2"
