"""Tests for the architecture repository abstraction."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from adr_kit.cli.main import cli
from adr_kit.generators import ArchitectureIndexGenerator
from adr_kit.repository import ArchitectureRegistryError, ArchitectureRepository
from tests.test_architecture_index_generator import _create_fixture


def _generate_bundle(scope_root: Path) -> dict[str, Path]:
    adr_dir = _create_fixture(scope_root)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)
    return generator.save_bundle(bundle, generator.scope_resolver.resolve(scope_root))


def _write_legacy_registry(scope_root: Path) -> Path:
    legacy_path = scope_root / "adrs" / "entities" / "registry.yaml"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(
        "\n".join(
            [
                'schema_version: "1.1"',
                "type: entity_registry",
                "entities:",
                "  - entity_id: CAP-9000",
                "    entity_type: capability",
                '    name: "Legacy capability"',
                "    introduced_by: ADR-L-9000",
                "    lifecycle_stage: active",
                "    source_path: adrs/logical/ADR-L-9000.yaml",
                "    source_artifact_type: logical_adr",
                "    domains: [legacy]",
                "    related_adrs: []",
                "    realized_by: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return legacy_path


def _write_project_yaml(scope_root: Path, *, project_name: str) -> None:
    (scope_root / "PROJECT.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: project_metadata",
                "project:",
                f'  name: "{project_name}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_repository_loads_normalized_bundle(tmp_path: Path) -> None:
    _generate_bundle(tmp_path)

    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()
    model = repository.get_model()

    assert repository.mode == "normalized"
    assert model.mode == "normalized"
    assert model.architecture_namespace == "arch-test"
    assert model.fingerprint == repository.fingerprint()
    assert any(entity.id == "CAP-1000" for entity in repository.get_entities())
    assert [entity.id for entity in repository.get_capabilities()] == ["CAP-1000"]
    assert [entity.id for entity in repository.get_components()] == ["COMP-VALIDATOR"]
    assert any(rel.to_entity_id == "COMP-VALIDATOR" for rel in repository.get_relationships())


def test_repository_query_entities_filters_deterministically(tmp_path: Path) -> None:
    _generate_bundle(tmp_path)

    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()

    assert [entity.id for entity in repository.query_entities(entity_type="capability")] == ["CAP-1000"]
    assert [entity.id for entity in repository.query_entities(adr="ADR-L-1000")] == [
        "ADR-L-1000",
        "CAP-1000",
        "DEC-1000",
        "INV-1000",
    ]
    assert repository.query_entities(domain="validation") == []
    assert repository.query_entities(status="proposed") == []


def test_repository_exposes_contract_bundle_view_in_normalized_mode(tmp_path: Path) -> None:
    _generate_bundle(tmp_path)

    repository = ArchitectureRepository(project_root=tmp_path)
    contract_bundle = repository.get_contract_bundle_view()

    assert contract_bundle.architecture_index.entity_registry_path == "adrs/index/entity-registry.yaml"
    assert len(contract_bundle.entity_registry.entities) == len(repository.get_entities())
    assert contract_bundle.remediation_ledger is None


def test_repository_exposes_semantic_relationship_and_provenance_helpers(tmp_path: Path) -> None:
    _generate_bundle(tmp_path)

    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()

    relationships = repository.get_relationships_for_entity("CAP-1000")
    assert any(item.relationship_id == "declared_in:CAP-1000:ADR-L-1000" for item in relationships)
    assert repository.get_unresolved_for_entity("CAP-1000") == []
    assert repository.get_adr_status("ADR-L-1000") == "accepted"
    assert repository.get_entity_adr_refs("CAP-1000") == ["ADR-L-1000"]
    assert repository.get_entity_canonical_source_ref("CAP-1000") == "ADR-L-1000#CAP-1000"
    assert repository.get_entity_source_refs("CAP-1000") == []
    provenance = repository.get_entity_provenance("CAP-1000")
    assert provenance is not None
    assert provenance.source_ref == "ADR-L-1000#CAP-1000"
    assert repository.get_unresolved_by_role("CAP-1000", role="any") == []
    assert repository.find_adrs_referencing_entity("CAP-1000") == ["ADR-L-1000", "ADR-PC-1000"]


def test_repository_exposes_manifest_index_and_corpus_summary(tmp_path: Path) -> None:
    _generate_bundle(tmp_path)
    runner = CliRunner()
    manifest_result = runner.invoke(cli, ["generate-manifest", "--scope", str(tmp_path)])
    assert manifest_result.exit_code == 0, manifest_result.output

    repository = ArchitectureRepository(project_root=tmp_path)

    manifest = repository.get_manifest()
    index = repository.get_index()
    summary = repository.get_corpus_summary()

    assert manifest.type == "manifest"
    assert index.type == "architecture_index"
    assert summary.mode == "normalized"
    assert summary.entity_counts["adr"] == 3
    assert summary.adr_counts_by_type["logical"] == 1
    assert summary.adr_counts_by_type["physical-system"] == 1
    assert summary.adr_counts_by_type["physical-component"] == 1
    assert summary.adr_counts_by_status["accepted"] == 3
    assert summary.relationship_count > 0
    assert summary.source_coverage is not None


def test_repository_next_id_uses_forward_authoring_directories(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1001"
    assert repository.next_id("physical-system") == "ADR-PS-1001"
    assert repository.next_id("physical-component") == "ADR-PC-1001"


def test_repository_next_id_uses_declared_ids_not_filenames(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    logical_path = tmp_path / "adrs" / "logical" / "ADR-L-0001-misleading-name.yaml"
    logical_path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-L-1099",
                'title: "Declared ID wins"',
                "status: proposed",
                'created_date: "2026-04-14"',
                'authors: ["test.author"]',
                'domains: ["test"]',
                "context: |",
                "  Filename should not drive next-id allocation.",
                "decisions:",
                "  - id: DEC-9999",
                '    summary: "Use declared IDs"',
                '    rationale: "Canonical identity lives in the artifact body."',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1100"


def test_repository_next_id_ignores_declared_ids_with_other_prefixes(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    stray_path = tmp_path / "adrs" / "logical" / "ADR-L-9999-stray.yaml"
    stray_path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-V-9090",
                'title: "Vision artifact in logical directory"',
                "status: proposed",
                'created_date: "2026-04-14"',
                'authors: ["test.author"]',
                'domains: ["test"]',
                "vision_category: true",
                "context: |",
                "  This should not advance ADR-L sequence.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1001"


def test_repository_next_id_rejects_duplicate_declared_ids(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    duplicate_path = tmp_path / "adrs" / "logical" / "ADR-L-2000-duplicate.yaml"
    duplicate_path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-L-1000",
                'title: "Duplicate declared ID"',
                "status: proposed",
                'created_date: "2026-04-14"',
                'authors: ["test.author"]',
                'domains: ["test"]',
                "context: |",
                "  Duplicate IDs must fail clearly.",
                "decisions:",
                "  - id: DEC-9998",
                '    summary: "Reject duplicates"',
                '    rationale: "Declared IDs are authoritative."',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    repository = ArchitectureRepository(project_root=tmp_path)

    with pytest.raises(ArchitectureRegistryError, match="Duplicate ADR ID"):
        repository.next_id("logical")


def test_repository_next_id_is_monotonic_and_non_reusable(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    repository = ArchitectureRepository(project_root=tmp_path)
    logical_path = tmp_path / "adrs" / "logical" / "ADR-L-1000-discovery.yaml"

    assert repository.next_id("logical") == "ADR-L-1001"

    logical_path.unlink()

    assert repository.next_id("logical") == "ADR-L-1002"


def test_repository_next_id_ignores_reserved_range_for_normal_allocation(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    normal_high_path = tmp_path / "adrs" / "logical" / "ADR-L-8001-normal.yaml"
    normal_high_path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-L-8001",
                'title: "High normal-range ADR"',
                "status: proposed",
                'created_date: "2026-04-14"',
                'authors: ["test.author"]',
                'domains: ["test"]',
                "context: |",
                "  Normal-range artifact below the reserved band.",
                "decisions:",
                "  - id: DEC-8001",
                '    summary: "Still normal"',
                '    rationale: "IDs below 9000 participate in forward allocation."',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    reserved_path = tmp_path / "adrs" / "logical" / "ADR-L-9001-reserved.yaml"
    reserved_path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-L-9001",
                'title: "Reserved exceptional import"',
                "status: proposed",
                'created_date: "2026-04-14"',
                'authors: ["test.author"]',
                'domains: ["test"]',
                "context: |",
                "  Reserved-range artifact.",
                "decisions:",
                "  - id: DEC-9001",
                '    summary: "Reserved range"',
                '    rationale: "Should not advance normal allocation."',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-8002"


def test_repository_next_id_fails_when_normal_band_is_exhausted(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    allocation_state = tmp_path / ".adr-id-allocation.yaml"
    allocation_state.write_text(
        "allocation:\n  logical: 8999\n",
        encoding="utf-8",
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    with pytest.raises(ArchitectureRegistryError, match="allocation band exhausted"):
        repository.next_id("logical")


def test_repository_falls_back_to_legacy_mode(tmp_path: Path) -> None:
    _write_project_yaml(tmp_path, project_name="legacy-scope")
    _write_legacy_registry(tmp_path)

    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()
    model = repository.get_model()

    assert repository.mode == "legacy"
    assert model.mode == "legacy"
    assert model.architecture_namespace == "legacy-scope"
    assert repository.find_entity("CAP-9000") is not None
    assert [entity.id for entity in repository.get_entities()] == ["CAP-9000"]
    assert [entity.id for entity in repository.get_capabilities()] == ["CAP-9000"]
    assert repository.get_invariants() == []
    assert [entity.id for entity in model.entities_by_type("capability")] == ["CAP-9000"]
    assert model.find_entity("CAP-9000") is not None
    assert repository.get_entity_canonical_source_ref("CAP-9000") == "ADR-L-9000#CAP-9000"
    assert model.canonical_adr_refs_for_entity("CAP-9000") == ["ADR-L-9000"]
    assert [rel.relationship_type for rel in repository.get_relationships()] == ["declared_in"]


def test_repository_rejects_contract_bundle_view_in_legacy_mode(tmp_path: Path) -> None:
    _write_legacy_registry(tmp_path)

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="legacy repository mode"):
        repository.get_contract_bundle_view()


def test_repository_load_is_idempotent_and_reload_refreshes_disk(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    repository = ArchitectureRepository(project_root=tmp_path)

    repository.load()
    original_fingerprint = repository.fingerprint()
    original_name = repository.get_capabilities()[0].name

    capability_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    capability = next(entity for entity in capability_data["entities"] if entity["entity_type"] == "capability")
    capability["name"] = "Changed capability"
    paths["entity_registry"].write_text(yaml.safe_dump(capability_data, sort_keys=False), encoding="utf-8")

    repository.load()
    assert repository.fingerprint() == original_fingerprint
    assert repository.get_capabilities()[0].name == original_name

    repository.reload()
    assert repository.fingerprint() != original_fingerprint
    assert repository.get_capabilities()[0].name == "Changed capability"


def test_repository_fingerprint_ignores_entity_order_reordering(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()
    original_fingerprint = repository.fingerprint()

    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    entity_data["entities"].reverse()
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    capability_data = yaml.safe_load(paths["capability_registry"].read_text(encoding="utf-8"))
    capability_data["entities"].reverse()
    paths["capability_registry"].write_text(yaml.safe_dump(capability_data, sort_keys=False), encoding="utf-8")

    repository.reload()

    assert repository.fingerprint() == original_fingerprint
    assert repository.get_entity_adr_refs("CAP-1000") == ["ADR-L-1000"]


def test_repository_fingerprint_changes_on_semantically_relevant_content_change(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()
    original_fingerprint = repository.fingerprint()

    index_data = yaml.safe_load(paths["architecture_index"].read_text(encoding="utf-8"))
    index_data["architecture_namespace"] = "modified-namespace"
    paths["architecture_index"].write_text(yaml.safe_dump(index_data, sort_keys=False), encoding="utf-8")

    repository.reload()

    assert repository.fingerprint() != original_fingerprint


def test_repository_rejects_subset_entity_missing_from_primary_registry(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    component_data = yaml.safe_load(paths["component_registry"].read_text(encoding="utf-8"))
    component_data["entities"][0]["id"] = "COMP-MISSING"
    paths["component_registry"].write_text(yaml.safe_dump(component_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="unknown entity ID"):
        repository.load()


def test_repository_rejects_subset_entity_type_mismatch(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    component_data = yaml.safe_load(paths["component_registry"].read_text(encoding="utf-8"))
    component_data["entities"][0]["entity_type"] = "capability"
    paths["component_registry"].write_text(yaml.safe_dump(component_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="mismatched entity_type"):
        repository.load()


def test_repository_rejects_subset_canonical_source_mismatch(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    component_data = yaml.safe_load(paths["component_registry"].read_text(encoding="utf-8"))
    component_data["entities"][0]["canonical_source"]["source_ref"] = "ADR-PC-9999#COMP-VALIDATOR"
    paths["component_registry"].write_text(yaml.safe_dump(component_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="canonical_source.source_ref"):
        repository.load()


def test_repository_keeps_baseline_usable_when_additive_subset_is_missing(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    paths["component_registry"].unlink()

    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()

    assert repository.get_entities()
    assert repository.get_components()
    assert repository._get_subset("components") == []


def test_repository_rejects_index_path_traversal_outside_scope(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    index_data = yaml.safe_load(paths["architecture_index"].read_text(encoding="utf-8"))
    index_data["entity_registry_path"] = "../outside.yaml"
    paths["architecture_index"].write_text(yaml.safe_dump(index_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="escapes scope root"):
        repository.load()


def test_repository_rejects_absolute_index_reference(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    index_data = yaml.safe_load(paths["architecture_index"].read_text(encoding="utf-8"))
    index_data["entity_registry_path"] = str(paths["entity_registry"].resolve())
    paths["architecture_index"].write_text(yaml.safe_dump(index_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="must be relative to scope root"):
        repository.load()


def test_repository_allows_in_scope_duplicate_path_shapes(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    index_data = yaml.safe_load(paths["architecture_index"].read_text(encoding="utf-8"))
    index_data["entity_registry_path"] = "adrs/index/../index/entity-registry.yaml"
    paths["architecture_index"].write_text(yaml.safe_dump(index_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()

    assert repository.find_entity("CAP-1000") is not None


def test_repository_rejects_unsupported_architecture_index_schema_version(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    index_data = yaml.safe_load(paths["architecture_index"].read_text(encoding="utf-8"))
    index_data["schema_version"] = "9.9"
    paths["architecture_index"].write_text(yaml.safe_dump(index_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="Failed to load registry"):
        repository.load()


def test_repository_fails_when_index_referenced_registry_is_missing(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    paths["relationship_registry"].unlink()

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="Failed to load registry"):
        repository.load()


def test_repository_fails_on_malformed_registry(tmp_path: Path) -> None:
    paths = _generate_bundle(tmp_path)
    paths["decision_registry"].write_text("[]\n", encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="Failed to load registry"):
        repository.load()


def test_repository_fingerprint_requires_loadable_state(tmp_path: Path) -> None:
    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="Architecture discovery registry not found"):
        repository.fingerprint()


def test_entities_cli_uses_repository_in_normalized_mode(tmp_path: Path) -> None:
    _generate_bundle(tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["entities", "capabilities", "--scope", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "CAP-1000" in result.output

    relationships_result = runner.invoke(
        cli,
        ["entities", "relationships", "--scope", str(tmp_path), "--entity", "CAP-1000"],
    )
    summary_result = runner.invoke(cli, ["entities", "summary", "--scope", str(tmp_path)])

    assert relationships_result.exit_code == 0, relationships_result.output
    assert "declared_in:CAP-1000:ADR-L-1000" in relationships_result.output
    assert summary_result.exit_code == 0, summary_result.output
    assert "entity_counts:" in summary_result.output
    assert "adr_counts_by_type:" in summary_result.output


def test_entities_cli_uses_repository_in_legacy_mode(tmp_path: Path) -> None:
    _write_legacy_registry(tmp_path)
    runner = CliRunner()

    list_result = runner.invoke(cli, ["entities", "list", "--scope", str(tmp_path)])
    get_result = runner.invoke(cli, ["entities", "get", "CAP-9000", "--scope", str(tmp_path)])
    capabilities_result = runner.invoke(cli, ["entities", "capabilities", "--scope", str(tmp_path)])

    assert list_result.exit_code == 0, list_result.output
    assert "CAP-9000" in list_result.output
    assert get_result.exit_code == 0, get_result.output
    assert "Legacy capability" in get_result.output
    assert capabilities_result.exit_code == 0, capabilities_result.output
    assert "CAP-9000" in capabilities_result.output


def test_next_id_cli_and_repository_reject_legacy_physical_authoring(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    repository = ArchitectureRepository(project_root=tmp_path)
    runner = CliRunner()

    with pytest.raises(ArchitectureRegistryError, match="Unsupported ADR type"):
        repository.next_id("physical")

    result = runner.invoke(cli, ["next-id", "--scope", str(tmp_path), "--type", "logical"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "ADR-L-1001"


def test_cli_no_longer_declares_raw_contract_bundle_loader() -> None:
    cli_source = Path("src/adr_kit/cli/main.py").read_text(encoding="utf-8")

    assert "def _load_contract_bundle(" not in cli_source
    assert "ModelView" not in cli_source
    assert "RegistryView" not in cli_source
    assert "load_architecture_index" not in cli_source


def test_repository_prefers_normalized_mode_when_both_sources_exist(tmp_path: Path) -> None:
    _generate_bundle(tmp_path)
    _write_legacy_registry(tmp_path)

    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()

    assert repository.mode == "normalized"
    assert repository.find_entity("CAP-1000") is not None
    assert repository.find_entity("CAP-9000") is None


def test_repository_no_longer_declares_local_adr_ref_helper() -> None:
    source = Path("src/adr_kit/repository/architecture_repository.py").read_text(encoding="utf-8")

    assert "def _entity_adr_refs(" not in source
