from __future__ import annotations

import pytest

from src.adr_kit.cli.main import cli
from src.adr_kit.compiler.backend.adr_ir_fragment_emitter import compile_logical_adr_ir_fragments
from src.adr_kit.compiler.backend.graph_emitter import emit_graph_artifact
from src.adr_kit.compiler.backend.manifest_emitter import emit_manifest_artifact
from src.adr_kit.compiler.backend.markdown_emitter import emit_markdown_artifacts
from src.adr_kit.compiler.backend.registry_emitter import emit_registry_artifacts
from src.adr_kit.compiler.driver import ArchitectureCompiler
from src.adr_kit.compiler.pipeline import CompilerPipeline, run_frontend_pipeline
from src.adr_kit.decorators import enforces_invariant, implements_adr
from src.adr_kit.generators.architecture_index_generator import ArchitectureIndexGenerator
from src.adr_kit.generators.entity_registry_generator import EntityRegistryGenerator
from src.adr_kit.generators.manifest_generator import ManifestGenerator
from src.adr_kit.generators.system_overview_generator import SystemOverviewGenerator
from src.adr_kit.integrity.validation import GeneratedArtifactValidator
from src.adr_kit.models.normalized_architecture_model import NormalizedArchitectureModel
from src.adr_kit.parser.yaml_parser import ADRParser
from src.adr_kit.projection import ProjectionInspector
from src.adr_kit.repository.architecture_repository import ArchitectureRepository
from src.adr_kit.repository.registry_loader import (
    fingerprint_payload,
    load_architecture_index,
    load_legacy_entity_registry,
    load_normalized_entity_registry,
    load_relationship_registry,
    load_remediation_ledger,
    load_unresolved_registry,
    model_payload,
)
from src.adr_kit.repository.semantic_adapter import (
    coerce_to_normalized_model,
    legacy_entity_to_normalized,
    legacy_relationships,
)
from src.adr_kit.schema.contract_validation import validate_adr_contract_bundle
from src.adr_kit.schema.implementation_attribution_validation import (
    validate_implementation_attribution_evidence,
)
from src.adr_kit.schema.repository_schema_generator import (
    generate_repository_schema_documents,
    write_repository_schema_documents,
)
from src.adr_kit.validators import ADRValidator, EntityValidator, SystemOverviewValidator


def test_implements_adr_attaches_ordered_metadata_to_function() -> None:
    @implements_adr("ADR-L-0001", "ADR-L-0013")
    def sample() -> str:
        return "ok"

    assert sample() == "ok"
    assert sample.__implements_adrs__ == ("ADR-L-0001", "ADR-L-0013")


def test_enforces_invariant_attaches_ordered_metadata_to_class() -> None:
    @enforces_invariant("INV-0006")
    class Sample:
        def value(self) -> str:
            return "ok"

    assert Sample().__class__.__enforces_invariants__ == ("INV-0006",)
    assert Sample().value() == "ok"


@pytest.mark.parametrize(
    ("factory", "args", "error_type"),
    [
        (implements_adr, (), ValueError),
        (implements_adr, ("ADR-L-0001", "ADR-L-0001"), ValueError),
        (implements_adr, ("ADR-L-0001", 7), TypeError),
        (enforces_invariant, (), ValueError),
        (enforces_invariant, ("INV-0006", " INV-0006 "), ValueError),
        (enforces_invariant, ("INV-0006", None), TypeError),
    ],
)
def test_decorator_factories_reject_invalid_inputs(factory, args, error_type) -> None:
    with pytest.raises(error_type):
        factory(*args)


def test_first_wave_public_boundaries_are_decorated() -> None:
    assert cli.__implements_adrs__ == ("ADR-L-0002", "ADR-L-0013")
    assert ArchitectureCompiler.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0013")
    assert CompilerPipeline.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0013")
    assert run_frontend_pipeline.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0013")
    assert ADRParser.__implements_adrs__ == ("ADR-L-0001",)
    assert ProjectionInspector.__implements_adrs__ == ("ADR-L-0007",)
    assert validate_adr_contract_bundle.__implements_adrs__ == ("ADR-L-0010", "ADR-L-0011")


def test_boundary_semantic_helpers_are_decorated() -> None:
    assert ArchitectureRepository.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.entity_ids.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.relationship_records.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.provenance_for_entity.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.canonical_source_ref_for_entity.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.source_refs_for_entity.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.entity_status.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.entity_domains.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.adr_status_map.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.canonical_adr_refs_for_entity.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.relationships_for_entity.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.related_entity_ids.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.unresolved_records.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.unresolved_for_entity.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.unresolved_related_entity_ids.__implements_adrs__ == ("ADR-L-0013",)
    assert EntityValidator.__implements_adrs__ == ("ADR-L-0013",)
    assert EntityValidator.validate_entity_references.__implements_adrs__ == ("ADR-L-0013",)
    assert EntityValidator.validate_entity_relationships.__implements_adrs__ == ("ADR-L-0013",)
    assert validate_implementation_attribution_evidence.__implements_adrs__ == ("ADR-L-0004", "ADR-L-0013")
    assert ArchitectureRepository.get_unresolved_by_role.__implements_adrs__ == ("ADR-L-0013",)
    assert ArchitectureRepository.get_entity_canonical_source_ref.__implements_adrs__ == ("ADR-L-0013",)
    assert ArchitectureRepository.get_entity_source_refs.__implements_adrs__ == ("ADR-L-0013",)
    assert coerce_to_normalized_model.__implements_adrs__ == ("ADR-L-0013",)
    assert legacy_entity_to_normalized.__implements_adrs__ == ("ADR-L-0013",)
    assert legacy_relationships.__implements_adrs__ == ("ADR-L-0013",)
    assert load_architecture_index.__implements_adrs__ == ("ADR-L-0013",)
    assert load_normalized_entity_registry.__implements_adrs__ == ("ADR-L-0013",)
    assert load_relationship_registry.__implements_adrs__ == ("ADR-L-0013",)
    assert load_unresolved_registry.__implements_adrs__ == ("ADR-L-0013",)
    assert load_remediation_ledger.__implements_adrs__ == ("ADR-L-0013",)
    assert load_legacy_entity_registry.__implements_adrs__ == ("ADR-L-0013",)
    assert fingerprint_payload.__implements_adrs__ == ("ADR-L-0013",)
    assert model_payload.__implements_adrs__ == ("ADR-L-0013",)


def test_generator_and_emitter_boundaries_are_decorated() -> None:
    assert ArchitectureIndexGenerator.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0013", "ADR-PC-0001")
    assert ManifestGenerator.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0010", "ADR-PC-0001")
    assert EntityRegistryGenerator.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0013", "ADR-PC-0001")
    assert SystemOverviewGenerator.__implements_adrs__ == ("ADR-L-0007",)
    assert emit_markdown_artifacts.__implements_adrs__ == ("ADR-L-0007", "ADR-PC-0001")
    assert emit_registry_artifacts.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0010", "ADR-PC-0003")
    assert emit_manifest_artifact.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0010", "ADR-PC-0003")
    assert emit_graph_artifact.__implements_adrs__ == ("ADR-L-0009", "ADR-L-0010", "ADR-PC-0003")
    assert compile_logical_adr_ir_fragments.__implements_adrs__ == ("ADR-L-0013", "ADR-L-9000")
    assert generate_repository_schema_documents.__implements_adrs__ == ("ADR-L-0010", "ADR-L-0011", "ADR-PC-0002")
    assert write_repository_schema_documents.__implements_adrs__ == ("ADR-L-0010", "ADR-L-0011", "ADR-PC-0002")


def test_invariant_enforcement_boundaries_are_decorated() -> None:
    assert GeneratedArtifactValidator.__implements_adrs__ == ("ADR-L-0007", "ADR-PC-0005")
    assert GeneratedArtifactValidator.__enforces_invariants__ == ("INV-0037", "INV-0038", "INV-0039")
    assert SystemOverviewValidator.__implements_adrs__ == ("ADR-L-0007", "ADR-PC-0005")
    assert SystemOverviewValidator.__enforces_invariants__ == ("INV-0037", "INV-0038", "INV-0039")
    assert validate_implementation_attribution_evidence.__enforces_invariants__ == ("INV-0027", "INV-0028", "INV-0029")


def test_governance_validation_boundaries_are_decorated() -> None:
    assert ADRValidator.__implements_adrs__ == ("ADR-L-0001", "ADR-L-0015", "ADR-PC-0002")
    assert ADRValidator.validate_file.__implements_adrs__ == ("ADR-L-0001", "ADR-L-0015", "ADR-PC-0002")
    assert ADRValidator._validate_governance_metadata.__enforces_invariants__ == ("INV-0064",)
    assert ADRValidator.validate_cross_references.__implements_adrs__ == ("ADR-L-0001", "ADR-L-0015", "ADR-PC-0002")
    assert ADRValidator.validate_implementation_authority_gate.__implements_adrs__ == ("ADR-L-0001", "ADR-L-0015", "ADR-PC-0002")
    assert ADRValidator.validate_implementation_authority_gate.__enforces_invariants__ == ("INV-0065",)
