from __future__ import annotations

import pytest

from src.adr_kit.cli.main import cli
from src.adr_kit.compiler.driver import ArchitectureCompiler
from src.adr_kit.compiler.pipeline import CompilerPipeline, run_frontend_pipeline
from src.adr_kit.decorators import enforces_invariant, implements_adr
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
from src.adr_kit.schema.contract_validation import validate_kernel_contract_bundle
from src.adr_kit.schema.implementation_attribution_validation import (
    validate_implementation_attribution_evidence,
)
from src.adr_kit.validators import EntityValidator


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
    assert validate_kernel_contract_bundle.__implements_adrs__ == ("ADR-L-0010", "ADR-L-0011")


def test_boundary_semantic_helpers_are_decorated() -> None:
    assert ArchitectureRepository.__implements_adrs__ == ("ADR-L-0013",)
    assert NormalizedArchitectureModel.__implements_adrs__ == ("ADR-L-0013",)
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
