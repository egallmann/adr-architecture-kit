from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from adr_kit.api import (
    EmbodimentLinkageRequest,
    build_embodiment_linkage,
    capabilities,
)
from adr_kit.decorators import embodies, implements
from adr_kit.models import (
    ImplementationAttributionEvidenceV15,
    ImplementationAttributionEvidenceV16,
)
from adr_kit.repository import ArchitectureRepository
from adr_kit.cli.main import cli
from adr_kit.semantic_attribution.normalize import (
    AttributionNormalizationError,
    normalize_attribution_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
ADR_L_0020_UUID = "019ffdba-3c42-7c4a-a737-f6751a265d60"
COMP_0022_UUID = "019ffdba-3c42-75d5-b93b-f32f35152e32"
INV_0103_UUID = "019ffdba-3c42-7cbe-a121-06d3437129ed"


def _repository() -> ArchitectureRepository:
    repository = ArchitectureRepository(ROOT)
    repository.load()
    return repository


def _v16_record(*, relationship: str = "implements", target: str = ADR_L_0020_UUID) -> dict:
    return {
        "implementation_entity_id": "tests.example:run",
        "implementation_entity_type": "function",
        "provenance": {
            "source_file": "tests/example.py",
            "extractor": "unit-test",
            "source_pointer": "tests.example:run",
            "start_line": 10,
            "end_line": 12,
        },
        "claims": [
            {
                "relationship": relationship,
                "target_entity_id": target,
                "confidence": "declared",
            }
        ],
    }


def test_v16_provenance_span_is_typed_and_bounded() -> None:
    parsed = ImplementationAttributionEvidenceV16.model_validate(
        {
            "schema_version": "1.6",
            "type": "implementation_attribution_evidence",
            "records": [_v16_record()],
        }
    )
    assert parsed.records[0].provenance.source_pointer == "tests.example:run"
    with pytest.raises(ValueError, match="end_line"):
        ImplementationAttributionEvidenceV16.model_validate(
            {
                "schema_version": "1.6",
                "type": "implementation_attribution_evidence",
                "records": [
                    {
                        **_v16_record(),
                        "provenance": {
                            "source_file": "tests/example.py",
                            "extractor": "unit-test",
                            "end_line": 12,
                        },
                    }
                ],
            }
        )


def test_normalization_is_version_aware_and_never_strengthens_confidence() -> None:
    v15 = ImplementationAttributionEvidenceV15.model_validate(
        {
            "schema_version": "1.5",
            "type": "implementation_attribution_evidence",
            "records": [
                {
                    **_v16_record(relationship="enforces", target=INV_0103_UUID),
                    "provenance": {
                        "source_file": "tests/example.py",
                        "extractor": "unit-test",
                    },
                    "claims": [
                        {
                            "relationship": "enforces",
                            "target_entity_id": INV_0103_UUID,
                            "confidence": "heuristic",
                        }
                    ],
                }
            ],
        }
    )
    with pytest.raises(AttributionNormalizationError, match="v1.6.*enforces.*declared"):
        normalize_attribution_evidence(v15, _repository(), target_version="1.6")


def test_v16_downgrade_rejects_provenance_loss() -> None:
    v16 = ImplementationAttributionEvidenceV16.model_validate(
        {
            "schema_version": "1.6",
            "type": "implementation_attribution_evidence",
            "records": [_v16_record()],
        }
    )
    with pytest.raises(AttributionNormalizationError, match="lossy.*source_pointer"):
        normalize_attribution_evidence(v16, _repository(), target_version="1.5")


def test_v15_v16_conversion_is_lossless_when_representable() -> None:
    v15 = ImplementationAttributionEvidenceV15.model_validate(
        {
            "schema_version": "1.5",
            "type": "implementation_attribution_evidence",
            "records": [
                {
                    **_v16_record(),
                    "provenance": {
                        "source_file": "tests/example.py",
                        "extractor": "unit-test",
                    },
                }
            ],
        }
    )
    v16 = normalize_attribution_evidence(v15, _repository(), target_version="1.6")
    assert isinstance(v16, ImplementationAttributionEvidenceV16)
    assert v16.records[0].provenance.source_pointer is None
    round_trip = normalize_attribution_evidence(v16, _repository(), target_version="1.5")
    assert round_trip == v15


def test_unsupported_normalization_target_fails_explicitly() -> None:
    with pytest.raises(AttributionNormalizationError, match="unsupported target"):
        normalize_attribution_evidence(
            ImplementationAttributionEvidenceV15(),
            _repository(),
            target_version="2.0",
        )


def test_stacked_uuid_decorator_order_is_semantically_stable() -> None:
    @implements(ADR_L_0020_UUID)
    @embodies(COMP_0022_UUID)
    def first() -> None:
        pass

    @embodies(COMP_0022_UUID)
    @implements(ADR_L_0020_UUID)
    def second() -> None:
        pass

    assert first.__architecture_attribution_claims__ == second.__architecture_attribution_claims__


def test_public_linkage_consumes_explicit_external_evidence_path(tmp_path: Path) -> None:
    evidence_root = tmp_path / "workspace-state"
    evidence_root.mkdir()
    evidence_path = evidence_root / "evidence.yaml"
    evidence_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.6",
                "type": "implementation_attribution_evidence",
                "records": [
                    _v16_record(),
                    {
                        **_v16_record(),
                        "provenance": {"source_file": "tests/other.py", "extractor": "unit-test"},
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    request = EmbodimentLinkageRequest(project_root=ROOT, evidence_path=evidence_path)
    result = build_embodiment_linkage(request)

    assert result.success
    assert len(result.links) == 1
    assert len(result.links[0].occurrences) == 2
    assert result.links[0].authority_ceiling == "validated_derived_evidence"
    assert result.links[0].graph_admission_status == "not_admitted"
    assert result.links_for_implementation("tests.example:run") == result.links
    assert result.implementations_for_intent(ADR_L_0020_UUID) == result.links
    assert evidence_path.is_file()


def test_capabilities_advertise_public_linkage_contract() -> None:
    manifest = capabilities()
    assert "build_embodiment_linkage" in manifest.operations
    assert manifest.supported_evidence_attribution_versions == ("1.5", "1.6")
    assert manifest.preferred_evidence_attribution_version == "1.6"
    assert manifest.api_contract_version == "1.0"


def test_linkage_report_uses_supported_projection(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.yaml"
    evidence_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.6",
                "type": "implementation_attribution_evidence",
                "records": [_v16_record()],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        cli,
        [
            "attribution",
            "linkage-report",
            "--scope",
            str(ROOT),
            "--evidence",
            str(evidence_path),
            "--intent-entity-id",
            ADR_L_0020_UUID,
        ],
    )
    assert result.exit_code == 0, result.output
    payload = yaml.safe_load(result.output)
    assert payload["authority_ceiling"] == "validated_derived_evidence"
    assert len(payload["links"]) == 1


def test_public_linkage_returns_partial_result_for_invalid_v16_confidence(tmp_path: Path) -> None:
    valid = _v16_record()
    invalid = _v16_record(relationship="enforces", target=INV_0103_UUID)
    invalid["implementation_entity_id"] = "tests.example:invalid"
    invalid["claims"][0]["confidence"] = "inferred"
    evidence_path = tmp_path / "partial.yaml"
    evidence_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.6",
                "type": "implementation_attribution_evidence",
                "records": [valid, invalid],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    result = build_embodiment_linkage(
        EmbodimentLinkageRequest(project_root=ROOT, evidence_path=evidence_path)
    )
    assert not result.success
    assert len(result.links) == 1
    assert len(result.rejected_claims) == 1
    assert result.rejected_claims[0].confidence == "inferred"
    assert "requires confidence declared" in result.rejected_claims[0].diagnostics[0].message


def test_public_linkage_missing_claims_respects_validation_profile(tmp_path: Path) -> None:
    evidence_path = tmp_path / "empty-claims.yaml"
    empty = _v16_record()
    empty["claims"] = []
    evidence_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.6",
                "type": "implementation_attribution_evidence",
                "records": [empty],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    greenfield = build_embodiment_linkage(
        EmbodimentLinkageRequest(
            project_root=ROOT,
            evidence_path=evidence_path,
            profile="greenfield",
        )
    )
    brownfield = build_embodiment_linkage(
        EmbodimentLinkageRequest(
            project_root=ROOT,
            evidence_path=evidence_path,
            profile="brownfield",
        )
    )
    assert not greenfield.success
    assert greenfield.error_count == 1
    assert brownfield.success
    assert brownfield.warning_count == 1


def test_coverage_adds_validated_projection_counts(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.yaml"
    evidence_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.6",
                "type": "implementation_attribution_evidence",
                "records": [_v16_record()],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        cli,
        [
            "attribution",
            "coverage",
            "--scope",
            str(ROOT),
            "--evidence",
            str(evidence_path),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = yaml.safe_load(result.output)
    assert payload["validated_semantic_link_count"] == 1
    assert payload["warning_semantic_link_count"] == 0
    assert payload["rejected_semantic_claim_count"] == 0
