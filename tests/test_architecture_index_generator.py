"""Tests for normalized architecture discovery generation."""

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from adr_kit.compiler.frontend import CachedADRParser
from adr_kit.compiler.passes import (
    detect_unresolved,
    DetectUnresolvedPass,
    DeriveRelationshipsPass,
    DerivedGapSignal,
    FixedOrderArchitecturePassRunner,
    ResolveInvariantCanonicalPass,
    ExtractLogicalEntitiesPass,
    ExtractPhysicalEntitiesPass,
    derive_relationships,
    ScoreCompletenessPass,
    UnresolvedDetectionResult,
    ValidateBundlePass,
    extract_logical_entities,
    extract_physical_entities,
    resolve_invariant_canonical,
    score_completeness,
    validate_bundle,
)
from adr_kit.cli.main import cli
from adr_kit.generators import ArchitectureIndexGenerator
from adr_kit.models import SourceRef
from adr_kit.parser import ADRParser


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8", newline="\n")


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


def test_compile_cli_writes_selected_artifacts(tmp_path):
    _create_fixture(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(tmp_path),
            "--emit",
            "registries,manifest",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Compiling architecture artifacts..." in result.output
    assert (tmp_path / "adrs" / "index" / "architecture-index.yaml").exists()
    assert (tmp_path / "adrs" / "manifest.yaml").exists()
    assert not (tmp_path / "adrs" / "rendered" / "ADR-L-1000.md").exists()


def test_compile_cli_check_detects_drift(tmp_path):
    _create_fixture(tmp_path)
    runner = CliRunner()

    compile_result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(tmp_path),
            "--emit",
            "registries,manifest",
            "--timestamp",
            "2026-01-01T00:00:00Z",
        ],
    )
    assert compile_result.exit_code == 0, compile_result.output

    (tmp_path / "adrs" / "manifest.yaml").write_text("drifted\n", encoding="utf-8")

    check_result = runner.invoke(
        cli,
        [
            "compile",
            "--scope",
            str(tmp_path),
            "--emit",
            "registries,manifest",
            "--timestamp",
            "2026-01-01T00:00:00Z",
            "--check",
        ],
    )

    assert check_result.exit_code == 1
    assert "E702" in check_result.output


def test_architecture_index_generation_is_deterministic(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()

    bundle_one = generator.generate_from_directory(adr_dir)
    bundle_two = generator.generate_from_directory(adr_dir)

    assert generator.render_yaml(bundle_one.entity_registry) == generator.render_yaml(bundle_two.entity_registry)
    assert generator.render_yaml(bundle_one.relationship_registry) == generator.render_yaml(bundle_two.relationship_registry)
    assert generator.render_yaml(bundle_one.unresolved_registry) == generator.render_yaml(bundle_two.unresolved_registry)


def test_architecture_index_generator_uses_cached_parser_across_repeated_runs(tmp_path):
    adr_dir = _create_fixture(tmp_path)

    class TrackingParser(ADRParser):
        def __init__(self):
            super().__init__()
            self.calls: list[tuple[str, str]] = []

        def parse_yaml(self, file_path):
            self.calls.append(("parse_yaml", str(Path(file_path).resolve())))
            return super().parse_yaml(file_path)

        def parse_logical_adr(self, file_path):
            self.calls.append(("parse_logical_adr", str(Path(file_path).resolve())))
            return super().parse_logical_adr(file_path)

        def parse_adr(self, file_path):
            self.calls.append(("parse_adr", str(Path(file_path).resolve())))
            return super().parse_adr(file_path)

        def parse_invariant(self, file_path):
            self.calls.append(("parse_invariant", str(Path(file_path).resolve())))
            return super().parse_invariant(file_path)

    tracking_parser = TrackingParser()
    generator = ArchitectureIndexGenerator(parser=tracking_parser)

    assert isinstance(generator.parser, CachedADRParser)

    generator.generate_from_directory(adr_dir)
    generator.generate_from_directory(adr_dir)

    assert tracking_parser.calls.count(("parse_yaml", str((tmp_path / "PROJECT.yaml").resolve()))) == 1
    assert tracking_parser.calls.count(("parse_logical_adr", str((adr_dir / "logical" / "ADR-L-1000-discovery.yaml").resolve()))) == 1
    assert tracking_parser.calls.count(("parse_adr", str((adr_dir / "physical-system" / "ADR-PS-1000-system.yaml").resolve()))) == 1
    assert tracking_parser.calls.count(("parse_adr", str((adr_dir / "physical-component" / "ADR-PC-1000-component.yaml").resolve()))) == 1
    assert tracking_parser.calls.count(("parse_invariant", str((adr_dir / "invariants" / "INV-1000-deterministic.yaml").resolve()))) == 1


def test_architecture_index_generator_clears_diagnostics_each_run(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()

    generator.diagnostics.error("E099", "stale diagnostic")

    generator.generate_from_directory(adr_dir)

    assert generator.diagnostics.as_list() == []


def test_score_completeness_preserves_current_generator_semantics():
    assert score_completeness().model_dump(mode="json") == {
        "status": "complete",
        "missing_fields": [],
    }
    assert score_completeness([]).model_dump(mode="json") == {
        "status": "complete",
        "missing_fields": [],
    }
    assert score_completeness(["metadata.module_path"]).model_dump(mode="json") == {
        "status": "partial",
        "missing_fields": ["metadata.module_path"],
    }


def test_architecture_index_generator_complete_delegates_to_pass():
    generator = ArchitectureIndexGenerator()
    completeness = generator._complete(["summary"])

    assert completeness == ScoreCompletenessPass().run(["summary"])


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


def test_validate_bundle_pass_reports_deterministic_diagnostics(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)

    component = next(entity for entity in bundle.entity_registry.entities if entity.id == "COMP-VALIDATOR")
    component.relationships.related_to.append("MISSING-ENTITY")
    bundle.unresolved_registry.unresolved[0].source_entity_id = "ADR-L-9999"

    result = ValidateBundlePass().run(
        bundle.entity_registry,
        bundle.relationship_registry,
        bundle.unresolved_registry,
    )

    assert result.is_valid is False
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "E403",
            "Entity relationship summary references unknown entity: COMP-VALIDATOR.related_to -> MISSING-ENTITY",
        ),
        (
            "E405",
            "Unresolved record references unknown source entity: UGAP-ADR-L-1000-GAP-1000 -> ADR-L-9999",
        ),
    ]


def test_validate_bundle_helper_matches_generator_failure_message(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)
    bundle.unresolved_registry.unresolved[0].source_entity_id = "ADR-L-9999"

    result = validate_bundle(
        bundle.entity_registry,
        bundle.relationship_registry,
        bundle.unresolved_registry,
    )

    assert result.first_error is not None
    with pytest.raises(ValueError, match=result.first_error.message):
        generator._validate_bundle(bundle.entity_registry, bundle.relationship_registry, bundle.unresolved_registry)


def test_extract_logical_entities_matches_current_fixture_shape(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    logical_files, _, _ = generator._discover_source_files(adr_dir)
    logical_adrs = [(generator.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
    scope = generator.scope_resolver.resolve(tmp_path)

    result = extract_logical_entities(
        logical_adrs,
        source_path=lambda file_path: generator._source_path(scope, file_path),
        canonical=generator._canonical,
        provenance=generator._provenance,
        summary=generator._summary,
        complete=generator._complete,
        classify_author_gap=generator._classify_author_gap,
    )

    assert [item.entity.id for item in result.entities] == ["ADR-L-1000", "CAP-1000", "DEC-1000"]
    assert all(item.allow_reference_merge is False for item in result.entities)
    assert result.invariant_mentions["INV-1000"][0].source_ref == "ADR-L-1000#INV-1000"
    assert result.invariant_mentions["INV-1000"][0].artifact_path == "adrs/logical/ADR-L-1000-discovery.yaml"
    assert [item.id for item in result.unresolved] == ["UGAP-ADR-L-1000-GAP-1000"]
    assert result.unresolved[0].provenance.classification == "explicit"


def test_extract_logical_entities_pass_matches_helper(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    logical_files, _, _ = generator._discover_source_files(adr_dir)
    logical_adrs = [(generator.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
    scope = generator.scope_resolver.resolve(tmp_path)

    direct = extract_logical_entities(
        logical_adrs,
        source_path=lambda file_path: generator._source_path(scope, file_path),
        canonical=generator._canonical,
        provenance=generator._provenance,
        summary=generator._summary,
        complete=generator._complete,
        classify_author_gap=generator._classify_author_gap,
    )
    via_pass = ExtractLogicalEntitiesPass().run(
        logical_adrs,
        source_path=lambda file_path: generator._source_path(scope, file_path),
        canonical=generator._canonical,
        provenance=generator._provenance,
        summary=generator._summary,
        complete=generator._complete,
        classify_author_gap=generator._classify_author_gap,
    )

    assert direct.entities == via_pass.entities
    assert direct.invariant_mentions == via_pass.invariant_mentions
    assert direct.unresolved == via_pass.unresolved


def test_extract_physical_entities_matches_current_fixture_shape(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    _, physical_files, _ = generator._discover_source_files(adr_dir)
    physical_adrs = [(generator.parser.parse_adr(path), path.resolve()) for path in physical_files]
    scope = generator.scope_resolver.resolve(tmp_path)

    result = extract_physical_entities(
        physical_adrs,
        source_path=lambda file_path: generator._source_path(scope, file_path),
        canonical=generator._canonical,
        provenance=generator._provenance,
        summary=generator._summary,
        complete=generator._complete,
        system_entity_id=generator._system_entity_id,
    )

    assert [item.entity.id for item in result.entities] == [
        "ADR-PS-1000",
        "SYS-1000",
        "ADR-PC-1000",
        "COMP-VALIDATOR",
        "IFACE-1000",
    ]
    assert [item.allow_reference_merge for item in result.entities] == [
        True,
        False,
        True,
        False,
        False,
    ]
    assert result.system_ids == {"ADR-PS-1000": "SYS-1000"}


def test_extract_physical_entities_pass_matches_helper(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    _, physical_files, _ = generator._discover_source_files(adr_dir)
    physical_adrs = [(generator.parser.parse_adr(path), path.resolve()) for path in physical_files]
    scope = generator.scope_resolver.resolve(tmp_path)

    direct = extract_physical_entities(
        physical_adrs,
        source_path=lambda file_path: generator._source_path(scope, file_path),
        canonical=generator._canonical,
        provenance=generator._provenance,
        summary=generator._summary,
        complete=generator._complete,
        system_entity_id=generator._system_entity_id,
    )
    via_pass = ExtractPhysicalEntitiesPass().run(
        physical_adrs,
        source_path=lambda file_path: generator._source_path(scope, file_path),
        canonical=generator._canonical,
        provenance=generator._provenance,
        summary=generator._summary,
        complete=generator._complete,
        system_entity_id=generator._system_entity_id,
    )

    assert direct.entities == via_pass.entities
    assert direct.system_ids == via_pass.system_ids


def test_resolve_invariant_canonical_prefers_standalone_and_preserves_references(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    logical_files, _, invariant_files = generator._discover_source_files(adr_dir)
    logical_adrs = [(generator.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
    standalone_invariants = [(generator.parser.parse_invariant(path), path.resolve()) for path in invariant_files]
    scope = generator.scope_resolver.resolve(tmp_path)

    logical_result = extract_logical_entities(
        logical_adrs,
        source_path=lambda file_path: generator._source_path(scope, file_path),
        canonical=generator._canonical,
        provenance=generator._provenance,
        summary=generator._summary,
        complete=generator._complete,
        classify_author_gap=generator._classify_author_gap,
    )
    invariant_mentions = {
        inv_id: [(mention.payload, mention.artifact_path, mention.source_ref) for mention in mentions]
        for inv_id, mentions in logical_result.invariant_mentions.items()
    }
    for invariant, path in standalone_invariants:
        artifact = generator._source_path(scope, path)
        invariant_mentions.setdefault(invariant.id, []).append(
            (
                {
                    "name": invariant.id,
                    "summary": generator._summary(invariant.statement),
                    "metadata": {
                        "defined_in": invariant.defined_in,
                        "scope": invariant.scope,
                        "statement": invariant.statement,
                        "enforcement_level": invariant.enforcement_level.value,
                        "declaration_mode": invariant.declaration_mode or "canonical",
                        "upheld_by_decisions": list(invariant.upheld_by_decisions),
                        "enforced_by": list(invariant.enforced_by),
                    },
                },
                artifact,
                invariant.id,
            )
        )

    result = resolve_invariant_canonical(
        invariant_mentions,
        canonical=generator._canonical,
        provenance=generator._provenance,
        complete=generator._complete,
    )

    selection = result.selections["INV-1000"]
    assert selection.entity.canonical_source.source_type == "standalone_invariant"
    assert selection.entity.canonical_source.source_ref == "INV-1000"
    assert [ref.source_ref for ref in selection.reference_source_refs] == ["ADR-L-1000#INV-1000"]


def test_resolve_invariant_canonical_pass_matches_helper(tmp_path):
    generator = ArchitectureIndexGenerator()
    invariant_mentions = {
        "INV-1000": [
            (
                {
                    "name": "INV-1000",
                    "summary": "Discovery must be deterministic.",
                    "metadata": {
                        "adr_id": "ADR-L-1000",
                        "scope": "global",
                        "statement": "Discovery must be deterministic.",
                        "enforcement_level": "must",
                        "declaration_mode": "local",
                        "upheld_by_decisions": [],
                    },
                },
                "adrs/logical/ADR-L-1000-discovery.yaml",
                "ADR-L-1000#INV-1000",
            )
        ]
    }

    direct = resolve_invariant_canonical(
        invariant_mentions,
        canonical=generator._canonical,
        provenance=generator._provenance,
        complete=generator._complete,
    )
    via_pass = ResolveInvariantCanonicalPass().run(
        invariant_mentions,
        canonical=generator._canonical,
        provenance=generator._provenance,
        complete=generator._complete,
    )

    assert direct.entities == via_pass.entities
    assert direct.selections == via_pass.selections


def test_derive_relationships_matches_current_fixture_shape(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)
    logical_files, physical_files, invariant_files = generator._discover_source_files(adr_dir)
    logical_adrs = [(generator.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
    physical_adrs = [(generator.parser.parse_adr(path), path.resolve()) for path in physical_files]
    standalone_invariants = [(generator.parser.parse_invariant(path), path.resolve()) for path in invariant_files]
    entities = {entity.id: entity for entity in bundle.entity_registry.entities}
    system_ids = {"ADR-PS-1000": "SYS-1000"}

    result = derive_relationships(
        entities=entities,
        logical_adrs=logical_adrs,
        standalone_invariants=standalone_invariants,
        physical_adrs=physical_adrs,
        system_ids=system_ids,
        relationship_id=generator._relationship_id,
    )

    assert [item.model_dump(mode="json") for item in result.relationships] == [
        item.model_dump(mode="json") for item in bundle.relationship_registry.relationships
    ]
    assert [item.gap_id for item in result.generator_gaps] == []


def test_derive_relationships_emits_gap_signals_for_missing_targets(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)
    logical_files, physical_files, invariant_files = generator._discover_source_files(adr_dir)
    logical_adrs = [(generator.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
    physical_adrs = [(generator.parser.parse_adr(path), path.resolve()) for path in physical_files]
    standalone_invariants = [(generator.parser.parse_invariant(path), path.resolve()) for path in invariant_files]
    entities = {entity.id: entity for entity in bundle.entity_registry.entities if entity.id != "COMP-VALIDATOR"}
    system_ids = {"ADR-PS-1000": "SYS-1000"}

    result = derive_relationships(
        entities=entities,
        logical_adrs=logical_adrs,
        standalone_invariants=standalone_invariants,
        physical_adrs=physical_adrs,
        system_ids=system_ids,
        relationship_id=generator._relationship_id,
    )

    assert any(
        item == DerivedGapSignal(
            gap_id="GAP-IMPL-CAP-1000-COMP-VALIDATOR",
            gap_type="capability_without_implementing_component",
            source_entity_id="CAP-1000",
            severity="important",
            source_ref="ADR-L-1000#CAP-1000",
            evidence=["ADR-L-1000", "COMP-VALIDATOR"],
            related_entity_id="COMP-VALIDATOR",
            expected_relationship="implemented_by",
        )
        for item in result.generator_gaps
    )


def test_derive_relationships_pass_matches_helper(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)
    logical_files, physical_files, invariant_files = generator._discover_source_files(adr_dir)
    logical_adrs = [(generator.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
    physical_adrs = [(generator.parser.parse_adr(path), path.resolve()) for path in physical_files]
    standalone_invariants = [(generator.parser.parse_invariant(path), path.resolve()) for path in invariant_files]
    entities = {entity.id: entity for entity in bundle.entity_registry.entities}
    system_ids = {"ADR-PS-1000": "SYS-1000"}

    direct = derive_relationships(
        entities=entities,
        logical_adrs=logical_adrs,
        standalone_invariants=standalone_invariants,
        physical_adrs=physical_adrs,
        system_ids=system_ids,
        relationship_id=generator._relationship_id,
    )
    via_pass = DeriveRelationshipsPass().run(
        entities=entities,
        logical_adrs=logical_adrs,
        standalone_invariants=standalone_invariants,
        physical_adrs=physical_adrs,
        system_ids=system_ids,
        relationship_id=generator._relationship_id,
    )

    assert direct.relationships == via_pass.relationships
    assert direct.generator_gaps == via_pass.generator_gaps


def test_detect_unresolved_matches_current_generator_shape(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)
    logical_files, physical_files, invariant_files = generator._discover_source_files(adr_dir)
    logical_adrs = [(generator.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
    physical_adrs = [(generator.parser.parse_adr(path), path.resolve()) for path in physical_files]
    standalone_invariants = [(generator.parser.parse_invariant(path), path.resolve()) for path in invariant_files]
    entities = {entity.id: entity for entity in bundle.entity_registry.entities if entity.id != "COMP-VALIDATOR"}

    derivation = derive_relationships(
        entities=entities,
        logical_adrs=logical_adrs,
        standalone_invariants=standalone_invariants,
        physical_adrs=physical_adrs,
        system_ids={"ADR-PS-1000": "SYS-1000"},
        relationship_id=generator._relationship_id,
    )

    result = detect_unresolved(
        derivation.generator_gaps,
        provenance=generator._provenance,
    )

    assert result == UnresolvedDetectionResult(
        unresolved=[
            next(item for item in result.unresolved if item.id == "GAP-IMPL-CAP-1000-COMP-VALIDATOR")
        ]
    )
    unresolved = result.unresolved[0]
    assert unresolved.gap_class == "generator_derived"
    assert unresolved.gap_type == "capability_without_implementing_component"
    assert unresolved.source_entity_id == "CAP-1000"
    assert unresolved.related_entity_id == "COMP-VALIDATOR"
    assert unresolved.expected_relationship == "implemented_by"
    assert unresolved.provenance.source_type == "derived_registry"
    assert unresolved.provenance.classification == "derived"


def test_detect_unresolved_pass_matches_helper():
    generator = ArchitectureIndexGenerator()
    gaps = [
        DerivedGapSignal(
            gap_id="GAP-1000",
            gap_type="unresolved_reference",
            source_entity_id="DEC-1000",
            severity="important",
            source_ref="ADR-L-1000#DEC-1000",
            evidence=["ADR-L-1000", "CAP-1000"],
            related_entity_id="CAP-1000",
            expected_relationship="enables",
        )
    ]

    direct = detect_unresolved(gaps, provenance=generator._provenance)
    via_pass = DetectUnresolvedPass().run(gaps, provenance=generator._provenance)

    assert direct == via_pass


def test_fixed_order_pass_runner_matches_current_generator_sequence(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    logical_files, physical_files, invariant_files = generator._discover_source_files(adr_dir)
    logical_adrs = [(generator.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
    physical_adrs = [(generator.parser.parse_adr(path), path.resolve()) for path in physical_files]
    standalone_invariants = [(generator.parser.parse_invariant(path), path.resolve()) for path in invariant_files]
    scope = generator.scope_resolver.resolve(tmp_path)

    entities = {}
    relationships = {}
    unresolved = []
    system_ids = {}

    def add_entity(entity, allow_reference_merge=False):
        existing = entities.get(entity.id)
        if existing is None:
            entities[entity.id] = entity
            return
        if allow_reference_merge:
            generator._append_source_ref(
                existing,
                SourceRef(
                    source_type=entity.canonical_source.source_type,
                    source_ref=entity.canonical_source.source_ref,
                    artifact_path=entity.canonical_source.artifact_path,
                    mention_role="reference",
                ),
            )
            return
        raise ValueError(f"Duplicate canonical entity ID {entity.id}")

    def collect_standalone_invariant_mentions(mentions):
        for invariant, path in standalone_invariants:
            artifact = generator._source_path(scope, path)
            mentions.setdefault(invariant.id, []).append(
                (
                    {
                        "name": invariant.id,
                        "summary": generator._summary(invariant.statement),
                        "metadata": {
                            "defined_in": invariant.defined_in,
                            "scope": invariant.scope,
                            "statement": invariant.statement,
                            "enforcement_level": invariant.enforcement_level.value,
                            "declaration_mode": invariant.declaration_mode or "canonical",
                            "upheld_by_decisions": list(invariant.upheld_by_decisions),
                            "enforced_by": list(invariant.enforced_by),
                        },
                    },
                    artifact,
                    invariant.id,
                )
            )

    result = FixedOrderArchitecturePassRunner().run(
        logical_adrs=logical_adrs,
        physical_adrs=physical_adrs,
        standalone_invariants=standalone_invariants,
        entities=entities,
        relationships=relationships,
        unresolved=unresolved,
        system_ids=system_ids,
        source_path=lambda file_path: generator._source_path(scope, file_path),
        canonical=generator._canonical,
        provenance=generator._provenance,
        summary=generator._summary,
        complete=generator._complete,
        classify_author_gap=generator._classify_author_gap,
        system_entity_id=generator._system_entity_id,
        relationship_id=generator._relationship_id,
        add_entity=add_entity,
        append_source_ref=generator._append_source_ref,
        collect_standalone_invariant_mentions=collect_standalone_invariant_mentions,
    )

    bundle = generator.generate_from_directory(adr_dir)

    assert [item.entity.id for item in result.logical_extraction.entities] == ["ADR-L-1000", "CAP-1000", "DEC-1000"]
    assert [item.entity.id for item in result.invariant_resolution.entities] == ["INV-1000"]
    assert [item.entity.id for item in result.physical_extraction.entities] == [
        "ADR-PS-1000",
        "SYS-1000",
        "ADR-PC-1000",
        "COMP-VALIDATOR",
        "IFACE-1000",
    ]
    assert [item.relationship_id for item in result.relationship_derivation.relationships] == [
        item.relationship_id for item in bundle.relationship_registry.relationships
    ]
    assert [item.id for item in result.unresolved_detection.unresolved] == []


def test_fixed_order_pass_runner_validate_matches_helper(tmp_path):
    adr_dir = _create_fixture(tmp_path)
    generator = ArchitectureIndexGenerator()
    bundle = generator.generate_from_directory(adr_dir)

    direct = validate_bundle(
        bundle.entity_registry,
        bundle.relationship_registry,
        bundle.unresolved_registry,
    )
    via_runner = FixedOrderArchitecturePassRunner().validate(
        bundle.entity_registry,
        bundle.relationship_registry,
        bundle.unresolved_registry,
    )

    assert direct == via_runner
