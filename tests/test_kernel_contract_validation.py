from __future__ import annotations

import pytest
import yaml
from click.testing import CliRunner

from src.adr_kit.cli.main import cli
from src.adr_kit.parser import ADRParser
from src.adr_kit.repository import ArchitectureRegistryError, ArchitectureRepository
from src.adr_kit.repository.registry_loader import (
    load_architecture_index,
    load_normalized_entity_registry,
    load_relationship_registry,
    load_unresolved_registry,
)
from src.adr_kit.repository.registry_paths import discover_repository_paths, resolve_index_reference
from src.adr_kit.schema.contract_validation import validate_kernel_contract_bundle
from tests.test_architecture_repository import _generate_bundle


def _write_remediation_ledger(tmp_path, entries):
    ledger_path = tmp_path / "adrs" / "governance" / "remediation-ledger.yaml"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "type": "remediation_ledger",
                "entries": entries,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return ledger_path


def _write_project_file(root, *, name: str, namespace: str | None = None):
    project_file = root / "PROJECT.yaml"
    project_file.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: project_metadata",
                "project:",
                f"  name: {name}",
                "  description: test project",
                "  type: library",
                "ownership:",
                "  team: architecture",
                "repository:",
                "  url: local",
                "  primary_branch: main",
                "architecture_documentation:",
                "  adr_directory: adrs/",
                "  manifest_path: adrs/manifest.yaml",
                f'  architecture_namespace: "{namespace or name}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return project_file


def _create_recursive_contract_workspace(tmp_path):
    root = tmp_path / "workspace"
    child = root / "module-a"
    child.mkdir(parents=True, exist_ok=True)
    (child / "package.json").write_text('{"name": "module-a"}', encoding="utf-8")

    _write_project_file(root, name="workspace")
    _write_project_file(child, name="module-a")
    _generate_bundle(root)
    _generate_bundle(child)
    return root, child


def test_repository_rejects_missing_required_metadata_key(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    capability = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "capability")
    del capability["metadata"]["adr_id"]
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="missing required metadata key"):
        repository.load()


def test_repository_rejects_sentinel_backed_content_by_default(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    component = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "component")
    component["metadata"]["module_path"] = "__NOT_YET_MODELED__"
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    repository = ArchitectureRepository(project_root=tmp_path)
    with pytest.raises(ArchitectureRegistryError, match="sentinel-backed content"):
        repository.load()


def test_contract_validator_allows_permitted_sentinel_fields_in_brownfield(tmp_path):
    paths = _generate_bundle(tmp_path)
    parser_payload = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    component = next(entity for entity in parser_payload["entities"] if entity["entity_type"] == "component")
    component["metadata"]["module_path"] = "__NOT_YET_MODELED__"
    paths["entity_registry"].write_text(yaml.safe_dump(parser_payload, sort_keys=False), encoding="utf-8")

    parser = ADRParser()
    repository_paths = discover_repository_paths(tmp_path)
    architecture_index = load_architecture_index(parser, repository_paths.architecture_index)
    entity_registry = load_normalized_entity_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.entity_registry_path),
    )
    relationship_registry = load_relationship_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.relationship_registry_path),
    )
    unresolved_registry = load_unresolved_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.unresolved_registry_path),
    )

    result = validate_kernel_contract_bundle(
        architecture_index,
        entity_registry,
        relationship_registry,
        unresolved_registry,
        profile="brownfield",
    )

    assert result.outcome == "sentinel_compliant"


def test_validate_contract_cli_reports_greenfield_failure_for_sentinel(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    component = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "component")
    component["metadata"]["module_path"] = "__NOT_YET_MODELED__"
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-contract", "--scope", str(tmp_path), "--contract-profile", "greenfield"])

    assert result.exit_code == 1, result.output
    assert "outcome: non_compliant" in result.output
    assert "sentinel-backed content is not allowed for profile=greenfield" in result.output


def test_validate_contract_cli_reports_brownfield_sentinel_compliance(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    component = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "component")
    component["metadata"]["module_path"] = "__NOT_YET_MODELED__"
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-contract", "--scope", str(tmp_path), "--contract-profile", "brownfield"])

    assert result.exit_code == 0, result.output
    assert "profile: brownfield" in result.output
    assert "outcome: sentinel_compliant" in result.output
    assert "sentinel_field_count: 1" in result.output


def test_validate_contract_cli_enforces_sentinel_threshold(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    component = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "component")
    component["metadata"]["module_path"] = "__NOT_YET_MODELED__"
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "validate-contract",
            "--scope",
            str(tmp_path),
            "--contract-profile",
            "brownfield",
            "--max-sentinel-fields",
            "0",
        ],
    )

    assert result.exit_code == 1, result.output
    assert "sentinel_field_count: 1" in result.output
    assert "sentinel_threshold_exceeded: true" in result.output


def test_validate_contract_cli_rejects_partial_in_greenfield(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    capability = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "capability")
    capability["completeness"]["status"] = "partial"
    capability["completeness"]["missing_fields"] = ["summary"]
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-contract", "--scope", str(tmp_path), "--contract-profile", "greenfield"])

    assert result.exit_code == 1, result.output
    assert "outcome: non_compliant" in result.output
    assert "completeness.status=partial is not allowed for profile=greenfield" in result.output


def test_validate_contract_cli_allows_reference_only_in_brownfield(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    capability = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "capability")
    capability["completeness"]["status"] = "reference_only"
    capability["completeness"]["missing_fields"] = ["summary", "metadata.implemented_by_components"]
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-contract", "--scope", str(tmp_path), "--contract-profile", "brownfield"])

    assert result.exit_code == 0, result.output
    assert "profile: brownfield" in result.output
    assert "non_complete_entity_count: 1" in result.output
    assert "reference_only: 1" in result.output


def test_validate_contract_cli_rejects_reference_only_in_migration(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    capability = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "capability")
    capability["completeness"]["status"] = "reference_only"
    capability["completeness"]["missing_fields"] = ["summary"]
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-contract", "--scope", str(tmp_path), "--contract-profile", "migration"])

    assert result.exit_code == 1, result.output
    assert "completeness.status=reference_only is not allowed for profile=migration" in result.output


def test_validate_contract_cli_enforces_non_complete_threshold(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    capability = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "capability")
    capability["completeness"]["status"] = "partial"
    capability["completeness"]["missing_fields"] = ["summary"]
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "validate-contract",
            "--scope",
            str(tmp_path),
            "--contract-profile",
            "brownfield",
            "--max-non-complete-entities",
            "0",
        ],
    )

    assert result.exit_code == 1, result.output
    assert "non_complete_entity_count: 1" in result.output
    assert "completeness_threshold_exceeded: true" in result.output


def test_validate_contract_cli_enforces_approved_no_regression_rule(tmp_path):
    paths = _generate_bundle(tmp_path)
    entity_data = yaml.safe_load(paths["entity_registry"].read_text(encoding="utf-8"))
    component = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "component")
    component["metadata"]["module_path"] = "__NOT_YET_MODELED__"
    paths["entity_registry"].write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")
    _write_remediation_ledger(
        tmp_path,
        [
            {
                "field_ref": "entity:COMP-VALIDATOR.metadata.module_path",
                "state": "approved",
                "authority_ref": "ADR-L-0011",
                "approved_by": "architecture-authority",
                "approved_at": "2026-03-14T00:00:00Z",
            }
        ],
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-contract", "--scope", str(tmp_path), "--contract-profile", "brownfield"])

    assert result.exit_code == 1, result.output
    assert "remediation_ledger_present: true" in result.output
    assert "approved field cannot regress to sentinel-backed content" in result.output


def test_governance_checks_cli_runs_contract_bundle_without_tests(tmp_path):
    _generate_bundle(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["governance-checks", "--scope", str(tmp_path), "--skip-tests"])

    assert result.exit_code == 0, result.output
    assert "== Greenfield contract validation ==" in result.output
    assert "== Brownfield ratchet validation ==" in result.output
    assert "outcome: compliant" in result.output


def test_validate_contract_cli_recursive_validates_all_scopes(tmp_path):
    workspace, child = _create_recursive_contract_workspace(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "validate-contract",
            "--scope",
            str(workspace),
            "--contract-profile",
            "greenfield",
            "--recursive",
        ],
    )

    assert result.exit_code == 0, result.output
    assert f"({workspace.resolve()})" in result.output
    assert f"({child.resolve()})" in result.output
    assert result.output.count("Project scope:") == 2


def test_validate_contract_cli_recursive_reports_scope_failure(tmp_path):
    workspace, child = _create_recursive_contract_workspace(tmp_path)
    child_paths = discover_repository_paths(child)
    architecture_index = load_architecture_index(ADRParser(), child_paths.architecture_index)
    entity_registry_path = resolve_index_reference(child, architecture_index.entity_registry_path)
    entity_data = yaml.safe_load(entity_registry_path.read_text(encoding="utf-8"))
    component = next(entity for entity in entity_data["entities"] if entity["entity_type"] == "component")
    component["metadata"]["module_path"] = "__NOT_YET_MODELED__"
    entity_registry_path.write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "validate-contract",
            "--scope",
            str(workspace),
            "--contract-profile",
            "greenfield",
            "--recursive",
        ],
    )

    assert result.exit_code == 1, result.output
    assert f"({workspace.resolve()})" in result.output
    assert f"({child.resolve()})" in result.output
    assert "sentinel-backed content is not allowed for profile=greenfield" in result.output


def test_validate_project_metadata_cli_reports_valid_project(tmp_path):
    project_file = _write_project_file(tmp_path, name="test-project")

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-project-metadata", "--file", str(project_file)])

    assert result.exit_code == 0, result.output
    assert "PROJECT.yaml valid:" in result.output
    assert "Project: test-project" in result.output


def test_validate_project_metadata_cli_recursive_validates_all_scopes(tmp_path):
    workspace, child = _create_recursive_contract_workspace(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "validate-project-metadata",
            "--scope",
            str(workspace),
            "--recursive",
        ],
    )

    assert result.exit_code == 0, result.output
    assert f"({workspace.resolve()})" in result.output
    assert f"({child.resolve()})" in result.output
    assert f"PROJECT.yaml valid: {workspace / 'PROJECT.yaml'}" in result.output
    assert f"PROJECT.yaml valid: {child / 'PROJECT.yaml'}" in result.output


def test_validate_project_metadata_cli_recursive_reports_subscope_failure(tmp_path):
    workspace, child = _create_recursive_contract_workspace(tmp_path)
    (child / "PROJECT.yaml").write_text("not: valid: yaml\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "validate-project-metadata",
            "--scope",
            str(workspace),
            "--recursive",
        ],
    )

    assert result.exit_code == 1, result.output
    assert f"({workspace.resolve()})" in result.output
    assert f"({child.resolve()})" in result.output
    assert f"ERROR: {child / 'PROJECT.yaml'}:" in result.output


def test_contract_validator_accepts_pending_approval_for_replaced_value(tmp_path):
    _generate_bundle(tmp_path)
    _write_remediation_ledger(
        tmp_path,
        [
            {
                "field_ref": "entity:COMP-VALIDATOR.metadata.module_path",
                "state": "pending_approval",
            }
        ],
    )

    parser = ADRParser()
    repository_paths = discover_repository_paths(tmp_path)
    architecture_index = load_architecture_index(parser, repository_paths.architecture_index)
    entity_registry = load_normalized_entity_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.entity_registry_path),
    )
    relationship_registry = load_relationship_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.relationship_registry_path),
    )
    unresolved_registry = load_unresolved_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.unresolved_registry_path),
    )
    remediation_ledger = parser.parse_remediation_ledger(repository_paths.remediation_ledger)

    result = validate_kernel_contract_bundle(
        architecture_index,
        entity_registry,
        relationship_registry,
        unresolved_registry,
        profile="brownfield",
        remediation_ledger=remediation_ledger,
    )

    assert result.outcome == "compliant"


def test_contract_validator_rejects_sentinel_state_when_value_is_replaced(tmp_path):
    _generate_bundle(tmp_path)
    _write_remediation_ledger(
        tmp_path,
        [
            {
                "field_ref": "entity:COMP-VALIDATOR.metadata.module_path",
                "state": "sentinel",
            }
        ],
    )

    parser = ADRParser()
    repository_paths = discover_repository_paths(tmp_path)
    architecture_index = load_architecture_index(parser, repository_paths.architecture_index)
    entity_registry = load_normalized_entity_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.entity_registry_path),
    )
    relationship_registry = load_relationship_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.relationship_registry_path),
    )
    unresolved_registry = load_unresolved_registry(
        parser,
        resolve_index_reference(tmp_path, architecture_index.unresolved_registry_path),
    )
    remediation_ledger = parser.parse_remediation_ledger(repository_paths.remediation_ledger)

    result = validate_kernel_contract_bundle(
        architecture_index,
        entity_registry,
        relationship_registry,
        unresolved_registry,
        profile="brownfield",
        remediation_ledger=remediation_ledger,
    )

    assert result.outcome == "non_compliant"
    assert any(
        issue.message == "sentinel ledger entry requires current field value to remain sentinel-backed"
        for issue in result.issues
    )


def test_governance_checks_cli_recursive_runs_scope_local_bundle_without_tests(tmp_path):
    workspace, child = _create_recursive_contract_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "governance-checks",
            "--scope",
            str(workspace),
            "--recursive",
            "--skip-tests",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "== Greenfield contract validation ==" in result.output
    assert "== Brownfield ratchet validation ==" in result.output
    assert "== Generated documentation validation ==" in result.output
    assert "== Project metadata validation ==" in result.output
    assert f"({workspace.resolve()})" in result.output
    assert f"({child.resolve()})" in result.output
