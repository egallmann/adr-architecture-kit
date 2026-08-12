"""Tests for deterministic entity registry generation and query surfaces."""

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from adr_kit.cli.main import cli
from adr_kit.generators import EntityRegistryGenerator
from adr_kit.parser import ADRParser


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def _create_scope_fixture(root: Path) -> Path:
    _write_file(
        root / "PROJECT.yaml",
        """
        project:
          name: entity-registry-test
        architecture_documentation:
          adr_directory: adrs
          manifest_path: adrs/manifest.yaml
          architecture_namespace: entity-registry-test
        """,
    )

    adr_dir = root / "adrs"

    _write_file(
        adr_dir / "logical" / "ADR-L-1000-derived-discovery.yaml",
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-1000
        title: "Derived discovery surfaces"
        status: accepted
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture", "tooling"]
        introduces_entities:
          - CAP-1000
          - INV-1000
        related_adrs:
          - ADR-PC-1000
        context: |
          Define explicit discovery surfaces for agents.
        capabilities:
          - id: CAP-1000
            name: "Entity registry lookup"
            description: "Provide machine-stable lookup for architecture entities."
            rationale: "Agents should query normalized derived indexes."
        invariants:
          - id: INV-1000
            statement: "Agent workflows MUST prefer indexed lookup over free-text traversal."
            scope: "architecture"
            enforcement_level: must
            enforcement_mechanism: design
            verification_method: automated
            rationale: "Explicit discovery surfaces are cheaper and more deterministic."
        architectural_boundaries: []
        interaction_contracts: []
        constraints: []
        non_functional_requirements: []
        decisions:
          - id: DEC-1000
            summary: "Use a derived entity registry as the normalized discovery surface."
            rationale: "Registry queries are deterministic and cheap."
        gaps: []
        """,
    )

    _write_file(
        adr_dir / "physical-system" / "ADR-PS-1000-toolkit-discovery-system.yaml",
        """
        schema_version: "1.0"
        adr_type: physical-system
        id: ADR-PS-1000
        title: "Toolkit discovery system"
        status: accepted
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture", "tooling"]
        implements_logical:
          - ADR-L-1000
        technologies:
          - python
          - yaml
        context: |
          The toolkit discovery system governs registry generation and query surfaces.
        technology_stack:
          - category: language
            name: "Python"
            version: "3.12"
            rationale: "Existing toolkit runtime."
        system_boundaries:
          - id: SYSBOUND-1000
            name: "ADR toolkit boundary"
            description: "Scope of the registry generation subsystem."
            external_dependencies: []
            exposed_interfaces:
              - "CLI"
        component_topology:
          components:
            - name: "Entity Registry Component"
              type: service
              purpose: "Generates and queries the entity registry"
              implements_adr: "ADR-PC-1000"
          relationships: []
        integration_patterns: []
        data_flows: []
        deployment_model:
          hosting: cloud
        scalability_strategy:
          horizontal_scaling: "N/A"
          bottlenecks: []
        failure_modes: []
        operational_requirements:
          monitoring: "CLI and test validation"
          logging: "stdout"
          security: "workspace local"
        gaps: []
        """,
    )

    _write_file(
        adr_dir / "physical-component" / "ADR-PC-1000-entity-registry.yaml",
        """
        schema_version: "1.0"
        adr_type: physical-component
        id: ADR-PC-1000
        title: "Entity Registry Component"
        status: accepted
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture", "tooling"]
        implements_system:
          - ADR-PS-1000
        implements_logical:
          - ADR-L-1000
        introduces_entities:
          - COMP-1000
          - IFACE-1000
          - IMPL-1000
        realizes_entities:
          - CAP-1000
          - INV-1000
        technologies:
          - python
          - click
          - pyyaml
        context: |
          The entity registry component generates and serves deterministic query results.
        technology_stack:
          - category: language
            name: "Python"
            version: "3.12"
            rationale: "Existing toolkit runtime."
        component_specifications:
          - id: COMP-1000
            name: "Entity Registry Generator"
            type: service
            responsibilities: |
              Generate a deterministic registry and provide query results.
            generation_context:
              purpose: "Generate and query a deterministic entity registry."
              key_responsibilities:
                - "Scan canonical architecture artifacts"
                - "Normalize explicit entities"
                - "Serve deterministic query results"
              constraints:
                - "Fail on duplicate global entity IDs"
              success_criteria:
                - "Repeated regeneration produces identical output"
            implements_capabilities:
              - CAP-1000
            realizes_entities:
              - INV-1000
            interfaces:
              - id: IFACE-1000
                type: CLI
                specification: "adr entities list|get|invariants|capabilities"
                contract_tests: "CLI output is deterministic and queryable."
            implementation_identifiers:
              module_path: "src/adr_kit/generators/entity_registry_generator.py"
              service_name: "entity-registry"
              repository: "local"
              entry_point: "src/adr_kit/cli/main.py"
              test_path: "tests/test_entity_registry_generator.py"
            implementation_requirements:
              algorithms: []
              error_handling:
                strategy: "Fail hard on duplicate entity IDs"
                error_types: []
              observability:
                logging:
                  level: "info"
                  structured: false
                  correlation_id: false
                  sensitive_data_handling: "No sensitive data"
                metrics:
                  - name: "entity_registry_generation_total"
                    type: counter
                    description: "Registry generations executed"
                    labels: ["scope"]
                tracing:
                  enabled: false
                  sampler: "always_off"
                  propagation: "none"
              testing_requirements:
                unit_test_coverage: ">= 80%"
                integration_tests: "Registry generation and CLI query coverage."
                contract_tests: "Schema and CLI output validation."
                performance_tests: "Deterministic regeneration with no diff."
                test_data: "Synthetic ADR corpus."
              security_requirements:
                authentication: "N/A"
                authorization: "N/A"
                input_validation: "Schema and parser validation."
                rate_limiting:
                  strategy: "N/A"
                  limits: []
              performance_requirements:
                latency:
                  p50: "50ms"
                  p95: "200ms"
                  p99: "500ms"
                throughput: "N/A"
                resource_limits:
                  cpu: "250m"
                  memory: "256Mi"
                  connections: 1
        data_architecture: []
        deployment_model:
          hosting: cloud
        operational_requirements:
          monitoring: "CLI and tests"
          logging: "stdout"
          security: "workspace local"
        implementation_decisions:
          - id: IMPL-1000
            summary: "Sort registry entities by ID and fail on duplicate global entity IDs."
            rationale: "Deterministic output is required for agent consumption."
            alternatives_considered: []
            implements_invariants:
              - INV-1000
        integration_points: []
        gaps: []
        """,
    )

    return adr_dir


def test_entity_registry_includes_explicit_entities_from_adrs(tmp_path):
    """Registry should normalize explicit introduced entities from ADR sources."""
    adr_dir = _create_scope_fixture(tmp_path)

    registry = EntityRegistryGenerator().generate_from_directory(adr_dir)
    entities = {entity.entity_id: entity for entity in registry.entities}

    assert list(entities) == sorted(entities)
    assert {"CAP-1000", "COMP-1000", "IFACE-1000", "IMPL-1000", "INV-1000"} <= set(entities)
    assert entities["CAP-1000"].source_artifact_type.value == "logical_adr"
    assert entities["COMP-1000"].source_artifact_type.value == "physical_component_adr"
    assert "CAP-1000" in (entities["COMP-1000"].relationships.implements or [])
    assert "INV-1000" in (entities["COMP-1000"].relationships.realizes or [])


def test_entity_registry_generation_is_deterministic(tmp_path):
    """Repeated generation with unchanged inputs should be byte-identical."""
    adr_dir = _create_scope_fixture(tmp_path)
    generator = EntityRegistryGenerator()

    registry_one = generator.generate_from_directory(adr_dir)
    registry_two = generator.generate_from_directory(adr_dir)

    assert generator.render_registry_yaml(registry_one) == generator.render_registry_yaml(registry_two)


def test_entity_registry_rejects_duplicate_explicit_entity_ids(tmp_path):
    """Explicitly introduced entity IDs must be globally unique."""
    adr_dir = _create_scope_fixture(tmp_path)
    _write_file(
        adr_dir / "logical" / "ADR-L-1001-duplicate-capability.yaml",
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-1001
        title: "Duplicate capability"
        status: proposed
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture"]
        introduces_entities:
          - CAP-1000
        context: |
          This ADR intentionally collides with an existing explicit capability ID.
        capabilities:
          - id: CAP-1000
            name: "Duplicate entity id"
            description: "Intentional collision for validation."
            rationale: "Test duplicate detection."
        architectural_boundaries: []
        interaction_contracts: []
        constraints: []
        non_functional_requirements: []
        invariants: []
        decisions:
          - id: DEC-1001
            summary: "Keep collision for test"
            rationale: "The generator should fail hard."
        gaps: []
        """,
    )

    with pytest.raises(ValueError, match="Duplicate entity ID CAP-1000"):
        EntityRegistryGenerator().generate_from_directory(adr_dir)


def test_cli_entity_queries_use_generated_registry(tmp_path):
    """CLI entity queries should read the architecture index bundle and return deterministic YAML."""
    adr_dir = _create_scope_fixture(tmp_path)
    scope_root = adr_dir.parent
    runner = CliRunner()

    generate = runner.invoke(cli, ["generate-entity-registry", "--scope", str(scope_root)])
    assert generate.exit_code == 0, generate.output
    assert "Generated legacy entity registry" in generate.output
    assert (scope_root / "adrs" / "index" / "architecture-index.yaml").exists()

    list_result = runner.invoke(
        cli,
        ["entities", "list", "--scope", str(scope_root), "--type", "capability"],
    )
    assert list_result.exit_code == 0, list_result.output
    assert "CAP-1000" in list_result.output
    assert "INV-1000" not in list_result.output

    get_result = runner.invoke(
        cli,
        ["entities", "get", "INV-1000", "--scope", str(scope_root)],
    )
    assert get_result.exit_code == 0, get_result.output
    assert "logical_adr" in get_result.output or "INV-1000" in get_result.output
    assert "INV-1000" in get_result.output

    invariants_result = runner.invoke(
        cli,
        ["entities", "invariants", "--scope", str(scope_root), "--adr", "ADR-L-1000"],
    )
    assert invariants_result.exit_code == 0, invariants_result.output
    assert "INV-1000" in invariants_result.output

    capabilities_result = runner.invoke(
        cli,
        ["entities", "capabilities", "--scope", str(scope_root), "--domain", "tooling"],
    )
    assert capabilities_result.exit_code == 0, capabilities_result.output
    assert "CAP-1000" in capabilities_result.output


def test_cli_fails_cleanly_when_registry_missing(tmp_path):
    """Entity query CLI should direct callers to generate the architecture index first."""
    _write_file(
        tmp_path / "PROJECT.yaml",
        """
        project:
          name: missing-registry
        """,
    )
    (tmp_path / "adrs").mkdir(parents=True, exist_ok=True)

    runner = CliRunner()
    result = runner.invoke(cli, ["entities", "list", "--scope", str(tmp_path)])

    assert result.exit_code != 0
    assert "Run 'adr generate-architecture-index' or 'adr generate-entity-registry' first." in result.output


def test_repo_registry_contains_adr_l_0008_entities():
    """Dogfood the current repo corpus and ensure ADR-L-0008 entities are indexable."""
    adr_dir = Path("adrs")
    if not adr_dir.exists():
        pytest.skip("Repository ADR directory not found")

    registry = EntityRegistryGenerator(parser=ADRParser()).generate_from_directory(adr_dir)
    entity_ids = {entity.entity_id for entity in registry.entities}

    assert {"CAP-0015", "CAP-0016", "INV-0040", "INV-0041", "INV-0042"} <= entity_ids
