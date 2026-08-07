from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from adr_kit.cli.main import cli
from adr_kit.compiler import ArchitectureCompiler, CompilationMode, CompilerConfig
from adr_kit.scope import ProjectScopeResolver
from tests.golden.helpers import clone_scope_sources, generate_deterministic_outputs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _artifact_map(result) -> dict[str, bytes]:
    return {artifact.path.as_posix(): artifact.content for artifact in result.artifacts}


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8", newline="\n")


def _create_scope_fixture(root: Path, *, project_name: str, namespace: str, suffix: str) -> None:
    _write_file(
        root / "PROJECT.yaml",
        f"""
schema_version: "1.0"
type: project_metadata
project:
  name: {project_name}
  description: recursive compile fixture
  type: library
ownership:
  team: architecture
repository:
  url: local
  primary_branch: develop
architecture_documentation:
  adr_directory: adrs/
  manifest_path: adrs/manifest.yaml
  architecture_namespace: "{namespace}"
""",
    )
    _write_file(
        root / "adrs" / "logical" / f"ADR-L-{suffix}-fixture.yaml",
        f"""
schema_version: "1.0"
adr_type: logical
id: ADR-L-{suffix}
title: "Fixture {suffix}"
status: accepted
created_date: "2026-03-14"
authors: ["test.author"]
domains: ["architecture"]
related_adrs: []
context: |
  Recursive compile fixture {suffix}.
capabilities:
  - id: CAP-{suffix}
    name: "Capability {suffix}"
    description: "A capability for fixture {suffix}."
    implemented_by_components: ["COMP-{suffix}"]
invariants:
  - id: INV-{suffix}
    statement: "Fixture {suffix} must compile deterministically."
    scope: global
    enforcement_level: must
    enforcement_mechanism: design
    verification_method: automated
    rationale: "Needed for trust."
    declaration_mode: local
decisions:
  - id: DEC-{suffix}
    summary: "Use recursive compile for fixture {suffix}."
    rationale: "Needed for testing."
    enforces_invariants: ["INV-{suffix}"]
    enables_capabilities: ["CAP-{suffix}"]
architectural_boundaries: []
interaction_contracts: []
constraints: []
non_functional_requirements: []
gaps: []
""",
    )
    _write_file(
        root / "adrs" / "physical-system" / f"ADR-PS-{suffix}-system.yaml",
        f"""
schema_version: "1.0"
adr_type: physical-system
id: ADR-PS-{suffix}
title: "System {suffix}"
status: accepted
created_date: "2026-03-14"
authors: ["test.author"]
domains: ["architecture"]
implements_logical: ["ADR-L-{suffix}"]
technologies: ["python"]
context: |
  Recursive compile system fixture {suffix}.
technology_stack:
  - category: language
    name: Python
    version: "3.12"
    rationale: "Existing runtime."
system_boundaries:
  - id: SYSBOUND-{suffix}
    name: Boundary {suffix}
    description: Scope
references_components: ["ADR-PC-{suffix}"]
""",
    )
    _write_file(
        root / "adrs" / "physical-component" / f"ADR-PC-{suffix}-component.yaml",
        f"""
schema_version: "1.0"
adr_type: physical-component
id: ADR-PC-{suffix}
title: "Component {suffix}"
status: accepted
created_date: "2026-03-14"
authors: ["test.author"]
domains: ["architecture"]
implements_system: ["ADR-PS-{suffix}"]
implements_logical: ["ADR-L-{suffix}"]
technologies: ["python"]
context: |
  Recursive compile component fixture {suffix}.
technology_stack:
  - category: language
    name: Python
    version: "3.12"
    rationale: "Existing runtime."
component_specifications:
  - id: COMP-{suffix}
    component_id: COMP-{suffix}
    name: "Component {suffix}"
    type: service
    responsibilities: "Compile fixture {suffix}."
    generation_context:
      purpose: "Compile fixture {suffix}."
      key_responsibilities: ["Compile fixture {suffix}"]
    interfaces:
      - id: IFACE-{suffix}
        type: CLI
        specification: "adr compile"
    implementation_identifiers:
      module_path: "src/component_{suffix}"
    implementation_requirements:
      error_handling:
        strategy: "fail closed"
      observability:
        logging:
          level: info
          structured: false
        metrics:
          - name: recursive_compile_total
            type: counter
      testing_requirements:
        unit_test_coverage: ">= 80%"
    implements_capabilities: ["CAP-{suffix}"]
""",
    )
    _write_file(
        root / "adrs" / "invariants" / f"INV-{suffix}-fixture.yaml",
        f"""
schema_version: "1.0"
type: invariant
id: INV-{suffix}
statement: "Fixture {suffix} must compile deterministically."
scope: global
enforcement_level: must
enforcement_mechanism: design
verification_method: automated
rationale: "Needed for trust."
defined_in: ADR-L-{suffix}
enforced_by: ["ADR-PC-{suffix}"]
declaration_mode: canonical
""",
    )


def _create_recursive_workspace(root: Path) -> Path:
    _create_scope_fixture(root, project_name="workspace-root", namespace="workspace-root", suffix="1100")
    submodule_root = root / "submodule"
    _create_scope_fixture(submodule_root, project_name="workspace-sub", namespace="workspace-sub", suffix="2100")
    return submodule_root


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
    assert "adrs/index/architecture-graph.yaml" not in artifact_paths
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


def test_architecture_compiler_check_infers_timestamp_from_disk(tmp_path):
    workspace = tmp_path / "workspace"
    generate_deterministic_outputs(_repo_root(), workspace)

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            dry_run=True,
            check=True,
            emit={"registries", "manifest"},
        )
    )

    assert result.success is True
    assert all(item.code != "E702" for item in result.diagnostics.as_list())
    assert all(item.code != "E705" for item in result.diagnostics.as_list())


def test_architecture_compiler_regeneration_reuses_existing_timestamp(tmp_path):
    workspace = tmp_path / "workspace"
    generated = generate_deterministic_outputs(_repo_root(), workspace)
    expected_manifest = generated["manifest"].read_bytes()
    expected_index = generated["architecture_index"].read_bytes()

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(config=CompilerConfig(emit={"registries", "manifest"}))

    assert result.success is True
    assert generated["manifest"].read_bytes() == expected_manifest
    assert generated["architecture_index"].read_bytes() == expected_index


def test_architecture_compiler_check_fails_when_generated_timestamps_disagree(tmp_path):
    workspace = tmp_path / "workspace"
    generated = generate_deterministic_outputs(_repo_root(), workspace)
    manifest_data = generated["manifest"].read_text(encoding="utf-8").replace("2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z")
    (workspace / "adrs" / "manifest.yaml").write_text(manifest_data, encoding="utf-8")

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            dry_run=True,
            check=True,
            emit={"registries", "manifest"},
        )
    )

    assert result.success is False
    assert any(item.code == "E705" for item in result.diagnostics.as_list())


def test_architecture_compiler_blocks_non_approved_implementation_authority(tmp_path):
    workspace = tmp_path / "workspace"
    _create_scope_fixture(workspace, project_name="workspace-root", namespace="workspace-root", suffix="3100")
    logical_path = workspace / "adrs" / "logical" / "ADR-L-3100-fixture.yaml"
    logical_path.write_text(
            logical_path.read_text(encoding="utf-8").replace(
                "context: |\n  Recursive compile fixture 3100.\n",
                "context: |\n  Recursive compile fixture 3100.\ngovernance:\n  steelman_review_required: true\n  steelman_review_completed: false\n  implementation_authority: implementation_authoritative\n  approved_by: erik\n  approved_date: \"2026-03-18T12:00:00Z\"\n",
            ),
            encoding="utf-8",
        )

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            dry_run=True,
            emit={"registries", "manifest"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is False
    assert any(item.code == "E706" for item in result.diagnostics.as_list())


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

    from adr_kit.compiler import driver as driver_module
    from adr_kit.schema.contract_validation import ContractValidationIssue, ContractValidationResult

    monkeypatch.setattr(
        driver_module,
        "validate_adr_contract_bundle",
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


def test_compile_cli_can_emit_architecture_graph(tmp_path):
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
            "graph",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "graph: adrs/index/architecture-graph.yaml" in result.output
    assert (workspace / "adrs" / "index" / "architecture-graph.yaml").exists()


def test_compile_cli_can_emit_architecture_graph_recursively(tmp_path):
    workspace = tmp_path / "workspace"
    _create_recursive_workspace(workspace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(workspace),
            "--emit",
            "graph",
            "--recursive",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (workspace / "adrs" / "index" / "architecture-graph.yaml").exists()
    assert (workspace / "submodule" / "adrs" / "index" / "architecture-graph.yaml").exists()


def test_architecture_compiler_normal_mode_fails_on_contract_error(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    from adr_kit.compiler import driver as driver_module
    from adr_kit.schema.contract_validation import ContractValidationIssue, ContractValidationResult

    monkeypatch.setattr(
        driver_module,
        "validate_adr_contract_bundle",
        lambda *args, **kwargs: ContractValidationResult(
            profile="greenfield",
            outcome="non_compliant",
            issues=(ContractValidationIssue(path="entities[0]", message="forced failure"),),
            sentinel_field_count=0,
            non_complete_entity_count=0,
            completeness_counts={"complete": 1},
        ),
    )

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            mode=CompilationMode.NORMAL,
            dry_run=True,
            emit={"registries"},
            profile="greenfield",
            metadata={"validate_contract": "true"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is False
    assert [(item.code, item.message) for item in result.diagnostics.as_list()] == [
        ("E704", "forced failure"),
    ]


def test_architecture_compiler_lenient_mode_tolerates_contract_error(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    from adr_kit.compiler import driver as driver_module
    from adr_kit.schema.contract_validation import ContractValidationIssue, ContractValidationResult

    monkeypatch.setattr(
        driver_module,
        "validate_adr_contract_bundle",
        lambda *args, **kwargs: ContractValidationResult(
            profile="greenfield",
            outcome="non_compliant",
            issues=(ContractValidationIssue(path="entities[0]", message="forced failure"),),
            sentinel_field_count=0,
            non_complete_entity_count=0,
            completeness_counts={"complete": 1},
        ),
    )

    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=workspace))
    result = compiler.compile(
        config=CompilerConfig(
            mode=CompilationMode.LENIENT,
            dry_run=True,
            emit={"registries"},
            profile="greenfield",
            metadata={"validate_contract": "true"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is True
    assert [(item.code, item.message) for item in result.diagnostics.as_list()] == [
        ("E704", "forced failure"),
    ]


def test_compile_cli_supports_public_mode_surface(tmp_path):
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
            "--mode",
            "strict",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Mode: strict" in result.output


def test_compile_cli_lenient_mode_allows_tolerated_contract_failure(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    clone_scope_sources(_repo_root(), workspace)

    from adr_kit.compiler import driver as driver_module
    from adr_kit.schema.contract_validation import ContractValidationIssue, ContractValidationResult

    monkeypatch.setattr(
        driver_module,
        "validate_adr_contract_bundle",
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
            "--mode",
            "lenient",
            "--validate-contract",
            "--contract-profile",
            "greenfield",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Mode: lenient" in result.output
    assert "Success: True" in result.output
    assert "ERROR: E704 forced failure" in result.output


def test_architecture_compiler_compile_recursive_discovers_expected_scopes(tmp_path):
    submodule_root = _create_recursive_workspace(tmp_path)
    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=tmp_path))

    result = compiler.compile_recursive(
        config=CompilerConfig(
            dry_run=True,
            emit={"registries", "manifest"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is True
    assert [item.scope.root for item in result.scope_results] == [tmp_path.resolve(), submodule_root.resolve()]
    assert result.statistics.scopes_compiled == 2
    assert result.statistics.successful_scopes == 2
    assert result.statistics.failed_scopes == 0


def test_architecture_compiler_compile_recursive_emits_scope_local_artifacts(tmp_path):
    _create_recursive_workspace(tmp_path)
    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=tmp_path))

    result = compiler.compile_recursive(
        config=CompilerConfig(
            dry_run=True,
            emit={"registries"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert len(result.scope_results) == 2
    for scoped in result.scope_results:
        artifact_paths = {artifact.path.as_posix() for artifact in scoped.result.artifacts}
        assert "adrs/index/architecture-index.yaml" in artifact_paths
        assert "adrs/entities/registry.yaml" in artifact_paths
        assert not (scoped.scope.root / "adrs" / "index" / "architecture-index.yaml").exists()


def test_architecture_compiler_compile_recursive_can_validate_contract_per_scope(tmp_path):
    _create_recursive_workspace(tmp_path)
    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=tmp_path))

    result = compiler.compile_recursive(
        config=CompilerConfig(
            dry_run=True,
            emit={"registries"},
            profile="greenfield",
            metadata={"validate_contract": "true"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is True
    assert result.statistics.scopes_compiled == 2
    assert all(scoped.result.success for scoped in result.scope_results)


def test_architecture_compiler_compile_recursive_aggregates_failed_scope(tmp_path, monkeypatch):
    _create_recursive_workspace(tmp_path)
    compiler = ArchitectureCompiler(scope_resolver=ProjectScopeResolver(explicit_scope=tmp_path))
    original_compile = compiler.compile

    def compile_with_forced_failure(scope=None, config=None):
        if getattr(scope, "root", None) == (tmp_path / "submodule").resolve():
            raise ValueError("forced recursive failure")
        return original_compile(scope, config)

    monkeypatch.setattr(compiler, "compile", compile_with_forced_failure)

    result = compiler.compile_recursive(
        config=CompilerConfig(
            dry_run=True,
            emit={"registries"},
            pinned_timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert result.success is False
    assert result.statistics.scopes_compiled == 2
    assert result.statistics.failed_scopes == 1
    assert any(item.code == "E799" for item in result.diagnostics.as_list())


def test_compile_cli_recursive_dry_run_reports_all_scopes(tmp_path):
    _create_recursive_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(tmp_path),
            "--recursive",
            "--emit",
            "registries,manifest",
            "--dry-run",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Compiling architecture artifacts recursively..." in result.output
    assert "Scopes compiled: 2" in result.output
    assert "Scope: workspace-root" in result.output
    assert "Scope: workspace-sub" in result.output


def test_compile_cli_recursive_check_detects_drift(tmp_path):
    _create_recursive_workspace(tmp_path)
    runner = CliRunner()

    compile_result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(tmp_path),
            "--recursive",
            "--emit",
            "registries,manifest",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )
    assert compile_result.exit_code == 0, compile_result.output

    (tmp_path / "submodule" / "adrs" / "manifest.yaml").write_text("drifted\n", encoding="utf-8")

    check_result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(tmp_path),
            "--recursive",
            "--emit",
            "registries,manifest",
            "--timestamp",
            "2026-01-01T00:00:00Z",
            "--check",
        ],
    )

    assert check_result.exit_code == 1, check_result.output
    assert "Scope: workspace-sub" in check_result.output
    assert "E702" in check_result.output


def test_compile_cli_recursive_can_validate_contract_greenfield(tmp_path):
    _create_recursive_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(tmp_path),
            "--recursive",
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
    assert "Scopes compiled: 2" in result.output


def test_generate_manifest_recursive_uses_recursive_compiler_defaults(tmp_path):
    _create_recursive_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "generate-manifest",
            "--scope",
            str(tmp_path),
            "--recursive",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "adrs" / "manifest.yaml").exists()
    assert (tmp_path / "submodule" / "adrs" / "manifest.yaml").exists()


def test_generate_manifest_recursive_rejects_explicit_output_path(tmp_path):
    _create_recursive_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "generate-manifest",
            "--scope",
            str(tmp_path),
            "--recursive",
            "--output",
            str(tmp_path / "combined-manifest.yaml"),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "--output is not supported with --recursive" in result.output


def test_generate_entity_registry_recursive_uses_recursive_compiler_defaults(tmp_path):
    _create_recursive_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "generate-entity-registry",
            "--scope",
            str(tmp_path),
            "--recursive",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "adrs" / "entities" / "registry.yaml").exists()
    assert (tmp_path / "submodule" / "adrs" / "entities" / "registry.yaml").exists()
