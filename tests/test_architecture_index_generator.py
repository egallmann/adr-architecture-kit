"""Tests for normalized architecture discovery generation."""

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from src.adr_kit.cli.main import cli
from src.adr_kit.generators import ArchitectureIndexGenerator
from src.adr_kit.parser import ADRParser


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def _create_fixture(root: Path, include_namespace: bool = True) -> Path:
    project_yaml = "\n".join(
        [
            'schema_version: "1.0"',
            "type: project_metadata",
            "project:",
            "  name: arch-test",
            "  description: architecture discovery fixture",
            "  type: library",
            "ownership:",
            "  team: architecture",
            "repository:",
            "  url: local",
            "  primary_branch: main",
            "architecture_documentation:",
            "  adr_directory: adrs/",
            "  manifest_path: adrs/manifest.yaml",
        ]
        + (['  architecture_namespace: "arch-test"'] if include_namespace else [])
    )
    _write_file(
        root / "PROJECT.yaml",
        project_yaml,
    )

    adr_dir = root / "adrs"
    _write_file(
        adr_dir / "logical" / "ADR-L-1000-discovery.yaml",
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-1000
        title: "Discovery"
        status: accepted
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture"]
        related_adrs: ["ADR-PC-1000"]
        context: |
          Discovery fixture.
        capabilities:
          - id: CAP-1000
            name: "Normalized discovery"
            description: "Expose a normalized registry."
            implemented_by_components: ["COMP-VALIDATOR"]
        invariants:
          - id: INV-1000
            statement: "Discovery must be deterministic."
            scope: global
            enforcement_level: must
            enforcement_mechanism: design
            verification_method: automated
            rationale: "Needed for trust."
            declaration_mode: local
        decisions:
          - id: DEC-1000
            summary: "Use a normalized architecture index."
            rationale: "Cheap to query."
            enforces_invariants: ["INV-1000"]
            enables_capabilities: ["CAP-1000"]
            governs_components: ["COMP-VALIDATOR"]
        architectural_boundaries: []
        interaction_contracts: []
        constraints: []
        non_functional_requirements: []
        gaps:
          - id: GAP-1000
            question: "Need more component detail?"
            impact: low
            blocking: false
        """,
    )
    _write_file(
        adr_dir / "physical-system" / "ADR-PS-1000-system.yaml",
        """
        schema_version: "1.0"
        adr_type: physical-system
        id: ADR-PS-1000
        title: "Discovery System"
        status: accepted
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture"]
        implements_logical: ["ADR-L-1000"]
        technologies: ["python"]
        context: |
          System for discovery.
        technology_stack:
          - category: language
            name: Python
            version: "3.12"
            rationale: "Existing runtime."
        system_boundaries:
          - id: SYSBOUND-1000
            name: Boundary
            description: Scope
        references_components: ["ADR-PC-1000"]
        """,
    )
    _write_file(
        adr_dir / "physical-component" / "ADR-PC-1000-component.yaml",
        """
        schema_version: "1.0"
        adr_type: physical-component
        id: ADR-PC-1000
        title: "Validator Component"
        status: accepted
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture"]
        implements_system: ["ADR-PS-1000"]
        implements_logical: ["ADR-L-1000"]
        technologies: ["python"]
        context: |
          Component for discovery.
        technology_stack:
          - category: language
            name: Python
            version: "3.12"
            rationale: "Existing runtime."
        component_specifications:
          - id: COMP-1000
            component_id: COMP-VALIDATOR
            name: "Validator"
            type: service
            responsibilities: "Validate architecture index output."
            generation_context:
              purpose: "Validate output."
              key_responsibilities: ["Validate output"]
            interfaces:
              - id: IFACE-1000
                type: CLI
                specification: "adr validate"
            implementation_identifiers:
              module_path: "src/validator"
            implementation_requirements:
              error_handling:
                strategy: "fail closed"
              observability:
                logging:
                  level: info
                  structured: false
                metrics:
                  - name: validations_total
                    type: counter
              testing_requirements:
                unit_test_coverage: ">= 80%"
            implements_capabilities: ["CAP-1000"]
        """,
    )
    _write_file(
        adr_dir / "invariants" / "INV-1000-deterministic.yaml",
        """
        schema_version: "1.0"
        type: invariant
        id: INV-1000
        statement: "Discovery must be deterministic."
        scope: global
        enforcement_level: must
        enforcement_mechanism: design
        verification_method: automated
        rationale: "Needed for trust."
        defined_in: ADR-L-1000
        enforced_by: ["ADR-PC-1000"]
        declaration_mode: canonical
        """,
    )
    return adr_dir


def test_architecture_index_generation_emits_normalized_artifacts(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)

    assert bundle.architecture_index.architecture_namespace == "arch-test"
    entity_ids = {entity.id for entity in bundle.entity_registry.entities}
    assert {"ADR-L-1000", "ADR-PS-1000", "ADR-PC-1000", "SYS-1000", "CAP-1000", "DEC-1000", "INV-1000", "COMP-VALIDATOR"} <= entity_ids
    invariant = next(entity for entity in bundle.entity_registry.entities if entity.id == "INV-1000")
    assert invariant.canonical_source.source_type == "standalone_invariant"
    assert any(ref.source_ref == "ADR-L-1000#INV-1000" for ref in invariant.source_refs)
    assert any(rel.relationship_type == "implemented_by" and rel.to_entity_id == "COMP-VALIDATOR" for rel in bundle.relationship_registry.relationships)
    assert any(item.id == "UGAP-ADR-L-1000-GAP-1000" for item in bundle.unresolved_registry.unresolved)


def test_architecture_index_round_trips_through_parser(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)
    paths = generator.save_bundle(bundle, generator.scope_resolver.resolve(tmp_path))
    parser = ADRParser()

    parsed_index = parser.parse_architecture_index(paths["architecture_index"])
    parsed_entities = parser.parse_normalized_entity_registry(paths["entity_registry"])
    parsed_relationships = parser.parse_relationship_registry(paths["relationship_registry"])
    parsed_unresolved = parser.parse_unresolved_registry(paths["unresolved_registry"])

    assert parsed_index.type == "architecture_index"
    assert parsed_entities.type == "normalized_entity_registry"
    assert parsed_relationships.type == "relationship_registry"
    assert parsed_unresolved.type == "unresolved_registry"
    assert len({item.id for item in parsed_unresolved.unresolved}) == len(parsed_unresolved.unresolved)


def test_architecture_index_requires_namespace(tmp_path):
    adr_dir = _create_fixture(tmp_path, include_namespace=False)

    with pytest.raises(ValueError, match="architecture_namespace"):
        ArchitectureIndexGenerator().generate_from_directory(adr_dir)


def test_generate_architecture_index_cli(tmp_path):
    _create_fixture(tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["generate-architecture-index", "--scope", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Generated architecture index" in result.output
    assert (tmp_path / "adrs" / "index" / "architecture-index.yaml").exists()

    list_result = runner.invoke(cli, ["entities", "list", "--scope", str(tmp_path), "--type", "capability"])
    assert list_result.exit_code == 0, list_result.output
    assert "CAP-1000" in list_result.output


def test_generate_entity_registry_cli_uses_architecture_index_pipeline(tmp_path):
    _create_fixture(tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["generate-entity-registry", "--scope", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Generated legacy entity registry" in result.output
    assert "Architecture index:" in result.output
    assert (tmp_path / "adrs" / "index" / "architecture-index.yaml").exists()
    assert (tmp_path / "adrs" / "entities" / "registry.yaml").exists()


def test_architecture_index_generation_is_deterministic(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()

    bundle_one = generator.generate_from_directory(adr_dir)
    bundle_two = generator.generate_from_directory(adr_dir)

    assert generator.render_yaml(bundle_one.entity_registry) == generator.render_yaml(bundle_two.entity_registry)
    assert generator.render_yaml(bundle_one.relationship_registry) == generator.render_yaml(bundle_two.relationship_registry)
    assert generator.render_yaml(bundle_one.unresolved_registry) == generator.render_yaml(bundle_two.unresolved_registry)


def test_architecture_index_validation_rejects_broken_entity_relationship_summary(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)

    component = next(entity for entity in bundle.entity_registry.entities if entity.id == "COMP-VALIDATOR")
    component.relationships.related_to.append("MISSING-ENTITY")

    with pytest.raises(ValueError, match="Entity relationship summary references unknown entity"):
        generator._validate_bundle(bundle.entity_registry, bundle.relationship_registry, bundle.unresolved_registry)


def test_architecture_index_validation_rejects_unknown_unresolved_source_entity(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)

    bundle.unresolved_registry.unresolved[0].source_entity_id = "ADR-L-9999"

    with pytest.raises(ValueError, match="Unresolved record references unknown source entity"):
        generator._validate_bundle(bundle.entity_registry, bundle.relationship_registry, bundle.unresolved_registry)
