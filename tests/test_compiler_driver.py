from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from src.adr_kit.cli.main import cli
from src.adr_kit.compiler import ArchitectureCompiler, CompilerConfig
from src.adr_kit.scope import ProjectScopeResolver
from tests.golden.helpers import clone_scope_sources, generate_deterministic_outputs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _artifact_map(result) -> dict[str, bytes]:
    return {artifact.path.as_posix(): artifact.content for artifact in result.artifacts}


def test_architecture_compiler_dry_run_emits_default_artifacts(tmp_path):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            dry_run=True,
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    artifact_paths = {artifact.path.as_posix() for artifact in result.artifacts}
    assert result.success is True
    assert "adrs/index/architecture-index.yaml" in artifact_paths
    assert "adrs/entities/registry.yaml" in artifact_paths
    assert "adrs/manifest.yaml" in artifact_paths
    assert any(path.startswith("adrs/rendered/ADR-") for path in artifact_paths)
    assert not (workspace / "adrs" / "index" / "architecture-index.yaml").exists()
    assert result.statistics.artifacts_emitted == len(result.artifacts)


def test_architecture_compiler_matches_deterministic_registry_and_manifest_outputs(tmp_path):
    workspace = tmp_path / "workspace"
    generated = generate_deterministic_outputs(_repo_root(), workspace)

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            dry_run=True,
            emit={"registries", "manifest"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    artifacts = _artifact_map(result)
    assert artifacts["adrs/index/architecture-index.yaml"] == generated["architecture_index"].read_bytes()
    assert artifacts["adrs/index/entity-registry.yaml"] == generated["entity_registry"].read_bytes()
    assert artifacts["adrs/index/relationship-registry.yaml"] == generated["relationship_registry"].read_bytes()
    assert artifacts["adrs/index/unresolved-registry.yaml"] == generated["unresolved_registry"].read_bytes()
    assert artifacts["adrs/index/decision-registry.yaml"] == generated["decision_registry"].read_bytes()
    assert artifacts["adrs/index/capability-registry.yaml"] == generated["capability_registry"].read_bytes()
    assert artifacts["adrs/index/invariant-registry.yaml"] == generated["invariant_registry"].read_bytes()
    assert artifacts["adrs/index/component-registry.yaml"] == generated["component_registry"].read_bytes()
    assert artifacts["adrs/index/system-registry.yaml"] == generated["system_registry"].read_bytes()
    assert artifacts["adrs/entities/registry.yaml"] == generated["legacy_entity_registry"].read_bytes()
    assert artifacts["adrs/manifest.yaml"] == generated["manifest"].read_bytes()


def test_architecture_compiler_pinned_timestamp_is_deterministic(tmp_path):
    workspace_one = tmp_path / "workspace-one"
    workspace_two = tmp_path / "workspace-two"
    clone_scope_sources(_repo_root(), workspace_one)
    clone_scope_sources(_repo_root(), workspace_two)

    config = CompilerConfig(dry_run=True, pinned_timestamp="2026-01-01T00:00:00Z")
    result_one = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace_one)).compile(config=config)
    result_two = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace_two)).compile(config=config)

    assert _artifact_map(result_one) == _artifact_map(result_two)


def test_architecture_compiler_check_detects_drift(tmp_path):
    workspace = tmp_path / "workspace"
    generate_deterministic_outputs(_repo_root(), workspace)
    (workspace / "adrs" / "manifest.yaml").write_text("drifted\n", encoding="utf-8")

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            dry_run=True,
            check=True,
            emit={"registries", "manifest"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is False
    assert [(item.code, item.message) for item in result.diagnostics.as_list()] == [
        ("E702", "Compiled artifact drift detected: adrs/manifest.yaml"),
    ]


def test_architecture_compiler_can_validate_contract_in_memory(tmp_path):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            dry_run=True,
            emit={"registries"},
            profile="greenfield",
            metadata={"validate_contract": "true"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is True
    assert all(diagnostic.code != "E704" for diagnostic in result.diagnostics.as_list())


def test_compile_cli_can_validate_contract_greenfield(tmp_path):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(workspace),
            "--emit",
            "registries",
            "--dry-run",
            "--validate-contract",
            "--contract-profile",
            "greenfield",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Contract validation: greenfield" in result.output
    assert "Success: True" in result.output


def test_compile_cli_can_validate_contract_brownfield(tmp_path):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(workspace),
            "--emit",
            "registries",
            "--dry-run",
            "--validate-contract",
            "--contract-profile",
            "brownfield",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Contract validation: brownfield" in result.output


def test_compile_cli_exits_non_zero_when_contract_validation_fails(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    from src.adr_kit.compiler import driver as driver_module
    from src.adr_kit.schema.contract_validation import ContractValidationIssue, ContractValidationResult

    monkeypatch.setattr(
        driver_module,
        "validate_kernel_contract_bundle",
        lambda *args, **kwargs: ContractValidationResult(
            profile="greenfield",
            outcome="non_compliant",
            issues=(ContractValidationIssue(path="entities[0]", message="forced failure"),),
            sentinel_field_count=0,
            non_complete_entity_count=0,
            completeness_counts={"complete": 1},
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(workspace),
            "--emit",
            "registries",
            "--dry-run",
            "--validate-contract",
            "--contract-profile",
            "greenfield",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 1, result.output
    assert "ERROR: E704 forced failure" in result.output
