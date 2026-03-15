from __future__ import annotations

from pathlib import Path

import pytest

from src.adr_kit.models import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    ImplementationAttributionEvidence,
    ImplementationAttributionProvenance,
    ImplementationAttributionRecord,
    NormalizedArchitectureModel,
    NormalizedEntity,
    NormalizedEntityRegistry,
)
from src.adr_kit.schema.implementation_attribution_validation import (
    validate_implementation_attribution_evidence,
)


def _adr_entity(adr_id: str, *, status: str = "accepted") -> NormalizedEntity:
    return NormalizedEntity(
        id=adr_id,
        entity_type="adr",
        name=adr_id,
        summary="test adr",
        canonical_source=CanonicalSource(
            source_type="logical_adr",
            source_ref=adr_id,
            artifact_path=f"adrs/logical/{adr_id}.yaml",
        ),
        metadata={"status": status, "domains": ["test"], "tags": ["traceability"]},
        completeness=Completeness(status="complete", missing_fields=[]),
        provenance=DiscoveryProvenance(
            source_type="adr",
            source_ref=adr_id,
            extraction_phase="test",
            classification="explicit",
            generator="test",
        ),
    )


def _evidence(*records: ImplementationAttributionRecord) -> ImplementationAttributionEvidence:
    return ImplementationAttributionEvidence(records=list(records))


def _model(*entities: NormalizedEntity) -> NormalizedArchitectureModel:
    return NormalizedArchitectureModel(
        mode="normalized",
        scope_root=".",
        architecture_namespace="test",
        fingerprint="test-model",
        entities=list(entities),
        relationships=[],
        unresolved=[],
        validation_summary=None,
        source_coverage=None,
    )


def _record(*adrs: str) -> ImplementationAttributionRecord:
    return ImplementationAttributionRecord(
        implementation_entity_id="function.process_claim_event",
        implementation_entity_type="function",
        attributed_adrs=list(adrs),
        provenance=ImplementationAttributionProvenance(
            source_file="src/claims/consumer.py",
            extractor="python-function-extractor",
            commit="deadbeef",
        ),
    )


def test_greenfield_rejects_missing_required_attribution():
    registry = NormalizedEntityRegistry(entities=[_adr_entity("ADR-L-0001")])

    result = validate_implementation_attribution_evidence(
        registry,
        _evidence(_record()),
        profile="greenfield",
    )

    assert result.is_valid is False
    assert result.error_count == 1
    assert "missing required architecture attribution" in result.issues[0].message


@pytest.mark.parametrize("profile", ["brownfield", "migration"])
def test_legacy_profiles_tolerate_missing_attribution_as_warning(profile: str):
    registry = NormalizedEntityRegistry(entities=[_adr_entity("ADR-L-0001")])

    result = validate_implementation_attribution_evidence(
        registry,
        _evidence(_record()),
        profile=profile,  # type: ignore[arg-type]
    )

    assert result.is_valid is True
    assert result.warning_count == 1
    assert result.error_count == 0


def test_missing_adr_reference_is_an_error():
    registry = NormalizedEntityRegistry(entities=[_adr_entity("ADR-L-0001")])

    result = validate_implementation_attribution_evidence(
        registry,
        _evidence(_record("ADR-L-9999")),
        profile="brownfield",
    )

    assert result.is_valid is False
    assert result.error_count == 1
    assert "referenced ADR does not exist" in result.issues[0].message


def test_superseded_adr_reference_is_a_warning():
    registry = NormalizedEntityRegistry(
        entities=[
            _adr_entity("ADR-L-0001"),
            _adr_entity("ADR-L-0002", status="superseded"),
        ]
    )

    result = validate_implementation_attribution_evidence(
        registry,
        _evidence(_record("ADR-L-0002")),
        profile="greenfield",
    )

    assert result.is_valid is True
    assert result.warning_count == 1
    assert result.error_count == 0
    assert "referenced ADR is superseded" in result.issues[0].message


def test_validation_accepts_normalized_architecture_model_input():
    model = _model(
        _adr_entity("ADR-L-0001"),
        _adr_entity("ADR-L-0002", status="superseded"),
    )

    result = validate_implementation_attribution_evidence(
        model,
        _evidence(_record("ADR-L-0001", "ADR-L-0002")),
        profile="greenfield",
    )

    assert result.is_valid is True
    assert result.warning_count == 1
    assert result.error_count == 0


def test_helper_module_no_longer_declares_private_model_coercion() -> None:
    source = Path(
        "src/adr_kit/schema/implementation_attribution_validation.py"
    ).read_text(encoding="utf-8")

    assert "def _coerce_model(" not in source
