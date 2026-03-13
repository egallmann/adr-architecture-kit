"""Tests for generated documentation integrity and CLI workflows."""

from pathlib import Path

from click.testing import CliRunner

from src.adr_kit.cli.main import cli
from src.adr_kit.integrity import GeneratedArtifactStatus, GeneratedArtifactValidator
from src.adr_kit.integrity.core import (
    GeneratorIdentity,
    compute_source_hash,
    parse_integrity_header,
)
from src.adr_kit.scope import ProjectScopeResolver


def _write_workspace(workspace: Path, include_submodule: bool = False, name: str = "projection-test") -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "PROJECT.yaml").write_text(
        f"project:\n  name: {name}\narchitecture_documentation:\n  adr_directory: adrs/\n  manifest_path: adrs/manifest.yaml\n  architecture_namespace: {name}\n",
        encoding="utf-8",
    )
    (workspace / "adrs" / "logical").mkdir(parents=True, exist_ok=True)
    (workspace / "adrs" / "physical").mkdir(parents=True, exist_ok=True)
    (workspace / "adrs" / "invariants").mkdir(parents=True, exist_ok=True)

    logical = Path("tests/fixtures/valid/logical-minimal.yaml").read_text(encoding="utf-8")
    physical = Path("tests/fixtures/valid/physical-minimal.yaml").read_text(encoding="utf-8")
    invariant = Path("adrs/invariants/INV-0001-schema-validation-required.yaml").read_text(encoding="utf-8")

    (workspace / "adrs" / "logical" / "ADR-L-9999-minimal-valid-logical-adr.yaml").write_text(logical, encoding="utf-8")
    (workspace / "adrs" / "physical" / "ADR-P-9999-minimal-valid-physical-adr.yaml").write_text(physical, encoding="utf-8")
    (workspace / "adrs" / "invariants" / "INV-0001-schema-validation-required.yaml").write_text(invariant, encoding="utf-8")

    if include_submodule:
        module = workspace / "module-a"
        module.mkdir(exist_ok=True)
        (module / "package.json").write_text('{"name": "module-a"}', encoding="utf-8")
        _write_workspace(module, include_submodule=False, name="module-a")


def test_integrity_header_rejects_unknown_fields():
    text = """<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: abc
rendered_hash: def
extra_field: nope
-->
"""

    try:
        parse_integrity_header(text)
    except ValueError as exc:
        assert "Unexpected number of header fields" in str(exc)
    else:
        raise AssertionError("Expected parse_integrity_header to reject unknown fields")


def test_source_hash_changes_with_new_optional_manifest_inputs(tmp_path):
    workspace = tmp_path / "workspace"
    _write_workspace(workspace)
    scope = ProjectScopeResolver(explicit_scope=workspace).resolve()
    inputs_before = [
        path for path in (workspace / "adrs").glob("logical/*.yaml")
    ]

    before = compute_source_hash(scope.root, inputs_before, GeneratorIdentity("adr-manifest", 1))

    ledger_dir = workspace / "adrs" / "decisions" / "ledgers"
    ledger_dir.mkdir(parents=True)
    ledger_dir.joinpath("LEDGER-0001-ledger.yaml").write_text(
        "schema_version: \"1.1\"\ntype: decision_ledger\nledger_id: LEDGER-0001\nversion: \"1.0\"\ncreated_date: \"2026-03-10\"\nsource_requirements_snapshot: REQ-0001\ntarget_logical_adr: ADR-L-9999\nrequired_decisions: []\n",
        encoding="utf-8",
    )
    after_inputs = sorted(path for path in workspace.glob("adrs/**/*.yaml"))
    after = compute_source_hash(scope.root, after_inputs, GeneratorIdentity("adr-manifest", 1))

    assert before != after


def test_generate_and_validate_rendered_docs_cli(tmp_path):
    workspace = tmp_path / "workspace"
    _write_workspace(workspace)
    runner = CliRunner()

    manifest_result = runner.invoke(cli, ["generate-manifest", "--scope", str(workspace)])
    assert manifest_result.exit_code == 0, manifest_result.output

    render_result = runner.invoke(cli, ["generate-rendered-docs", "--scope", str(workspace)])
    assert render_result.exit_code == 0, render_result.output

    rendered_file = workspace / "adrs" / "rendered" / "ADR-L-9999.md"
    rendered_header = parse_integrity_header(rendered_file.read_text(encoding="utf-8"))
    assert rendered_header["artifact_kind"] == "rendered_adr_markdown"

    validate_result = runner.invoke(cli, ["validate-generated-docs", "--scope", str(workspace)])
    assert validate_result.exit_code == 0, validate_result.output
    assert "valid:" in validate_result.output


def test_validate_generated_docs_reports_tampered_output(tmp_path):
    workspace = tmp_path / "workspace"
    _write_workspace(workspace)
    runner = CliRunner()

    assert runner.invoke(cli, ["generate-manifest", "--scope", str(workspace)]).exit_code == 0
    assert runner.invoke(cli, ["generate-rendered-docs", "--scope", str(workspace)]).exit_code == 0
    rendered_file = workspace / "adrs" / "rendered" / "ADR-L-9999.md"
    rendered_file.write_text(
        rendered_file.read_text(encoding="utf-8") + "\nmanual edit\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli, ["validate-generated-docs", "--scope", str(workspace)])
    assert result.exit_code != 0
    assert GeneratedArtifactStatus.TAMPERED_GENERATED_OUTPUT.value in result.output


def test_validate_generated_docs_reports_stale_output(tmp_path):
    workspace = tmp_path / "workspace"
    _write_workspace(workspace)
    runner = CliRunner()

    assert runner.invoke(cli, ["generate-manifest", "--scope", str(workspace)]).exit_code == 0
    assert runner.invoke(cli, ["generate-rendered-docs", "--scope", str(workspace)]).exit_code == 0
    source_file = workspace / "adrs" / "logical" / "ADR-L-9999-minimal-valid-logical-adr.yaml"
    source_file.write_text(
        source_file.read_text(encoding="utf-8").replace("Minimal Valid Logical ADR", "Updated Logical ADR"),
        encoding="utf-8",
    )

    result = runner.invoke(cli, ["validate-generated-docs", "--scope", str(workspace)])
    assert result.exit_code != 0
    assert GeneratedArtifactStatus.STALE_GENERATED_OUTPUT.value in result.output


def test_validate_generated_docs_recursive_is_scope_local(tmp_path):
    workspace = tmp_path / "workspace"
    _write_workspace(workspace, include_submodule=True)
    runner = CliRunner()

    assert runner.invoke(cli, ["generate-manifest", "--scope", str(workspace), "--recursive"]).exit_code == 0
    assert runner.invoke(cli, ["generate-rendered-docs", "--scope", str(workspace), "--recursive"]).exit_code == 0
    validator = GeneratedArtifactValidator(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    results = validator.validate_recursive()

    assert "projection-test" in results
    assert "module-a" in results
    assert any("module-a" in result.artifact_path for result in results["module-a"])


def test_repo_generated_artifacts_validate():
    scope = ProjectScopeResolver().resolve()
    validator = GeneratedArtifactValidator()
    results = validator.validate_scope(scope)

    assert results, "Expected generated artifacts to be discovered"
    assert all(result.status == GeneratedArtifactStatus.VALID.value for result in results), results
