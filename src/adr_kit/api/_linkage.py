"""Public embodiment-linkage adapter backed by the canonical semantic core."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from .. import __version__
from ..core import execute_semantic_core_request
from ..decorators import embodies, enforces, implements
from ..models import ImplementationAttributionEvidenceV15, ImplementationAttributionEvidenceV16
from ..repository import ArchitectureRepository
from ..semantic_attribution.normalize import semantic_records
from ._contracts import (
    API_CONTRACT_VERSION,
    Diagnostic,
    EmbodimentIntentLink,
    EmbodimentLinkageRequest,
    EmbodimentLinkageResult,
    LinkageOccurrence,
    LinkageProvenance,
    RejectedEmbodimentClaim,
)
from ._errors import OperationError, RepositoryError


def _parse_evidence(
    path: Path,
) -> ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise OperationError(f"Evidence could not be read: {path}") from exc
    if not isinstance(payload, dict):
        raise OperationError("Evidence document must be a mapping")
    version = payload.get("schema_version")
    try:
        if version == "1.5":
            return ImplementationAttributionEvidenceV15.model_validate(payload)
        if version == "1.6":
            return ImplementationAttributionEvidenceV16.model_validate(payload)
    except Exception as exc:
        raise OperationError(f"Evidence schema {version!r} could not be parsed") from exc
    raise OperationError(
        f"build_embodiment_linkage supports evidence schema 1.5 or 1.6, not {version!r}"
    )


def _diagnostic_from(value: object) -> Diagnostic:
    item = value if isinstance(value, dict) else {}
    severity = str(item.get("severity", "error"))
    if severity not in {"info", "warning", "error"}:
        severity = "error"
    return Diagnostic(
        severity=cast(Any, severity),
        code=str(item.get("code", "attribution.invalid")),
        message=str(item.get("message", "attribution validation failed")),
        path=str(item["path"]) if item.get("path") is not None else None,
    )


def _provenance_from(value: object) -> LinkageProvenance:
    item = value if isinstance(value, dict) else {}
    return LinkageProvenance(
        source_file=str(item.get("source_file", "")),
        extractor=str(item.get("extractor", "")),
        commit=item.get("commit"),
        source_pointer=item.get("source_pointer"),
        start_line=item.get("start_line"),
        end_line=item.get("end_line"),
    )


def _occurrence_from(value: object) -> LinkageOccurrence:
    item = value if isinstance(value, dict) else {}
    return LinkageOccurrence(
        confidence=cast(Any, str(item.get("confidence", ""))),
        provenance=_provenance_from(item.get("provenance")),
        source_language=item.get("source_language"),
    )


@implements("019ffdba-3c42-7304-ab2f-bcd01cc6f9d3")
@enforces("019ffdba-3c42-74ea-993d-990027e528c0")
@embodies("019ffdba-3c42-75d5-b93b-f32f35152e32")
def build_embodiment_linkage(request: EmbodimentLinkageRequest) -> EmbodimentLinkageResult:
    """Resolve attribution through the canonical shared semantic core."""

    if not isinstance(request, EmbodimentLinkageRequest):
        raise TypeError("request must be an EmbodimentLinkageRequest")
    evidence = _parse_evidence(request.evidence_path)
    try:
        repository = ArchitectureRepository(request.project_root)
        repository.load()
        core_result = execute_semantic_core_request(
            {
                "core_contract_version": "1.0",
                "operation": "build_embodiment_linkage",
                "profile": request.profile,
                "evidence_schema_version": evidence.schema_version,
                "architecture_fingerprint": repository.fingerprint(),
                "records": [
                    record.model_dump(mode="json") for record in semantic_records(evidence)
                ],
                "entities": [
                    entity.model_dump(mode="json") for entity in repository.get_entities()
                ],
            }
        )
    except OperationError, RepositoryError:
        raise
    except Exception as exc:
        raise OperationError("Embodiment linkage could not complete") from exc

    diagnostics = tuple(_diagnostic_from(item) for item in core_result.get("diagnostics", []))
    links = tuple(
        EmbodimentIntentLink(
            implementation_entity_id=str(item.get("implementation_entity_id", "")),
            implementation_entity_type=str(item.get("implementation_entity_type", "")),
            relationship=cast(Any, str(item.get("relationship", ""))),
            target_entity_id=str(item.get("target_entity_id", "")),
            target_entity_type=str(item.get("target_entity_type", "")),
            target_alias_id=str(item.get("target_alias_id", "")),
            target_alias_name=str(item.get("target_alias_name", "")),
            target_lifecycle=str(item.get("target_lifecycle", "")),
            occurrences=tuple(_occurrence_from(value) for value in item.get("occurrences", [])),
            validation_status=cast(Any, str(item.get("validation_status", "valid"))),
            diagnostics=tuple(_diagnostic_from(value) for value in item.get("diagnostics", [])),
            authority_ceiling=str(item.get("authority_ceiling", "validated_derived_evidence")),
            graph_admission_status=str(item.get("graph_admission_status", "not_admitted")),
        )
        for item in core_result.get("links", [])
        if isinstance(item, dict)
    )
    rejected = tuple(
        RejectedEmbodimentClaim(
            implementation_entity_id=str(item.get("implementation_entity_id", "")),
            implementation_entity_type=str(item.get("implementation_entity_type", "")),
            relationship=str(item.get("relationship", "")),
            target_entity_id=str(item.get("target_entity_id", "")),
            confidence=str(item.get("confidence", "")),
            provenance=_provenance_from(item.get("provenance")),
            diagnostics=tuple(_diagnostic_from(value) for value in item.get("diagnostics", [])),
        )
        for item in core_result.get("rejected_claims", [])
        if isinstance(item, dict)
    )
    return EmbodimentLinkageResult(
        request=request,
        success=bool(core_result.get("success", False)),
        evidence_schema_version=str(
            core_result.get("evidence_schema_version", evidence.schema_version)
        ),
        architecture_fingerprint=str(
            core_result.get("architecture_fingerprint", repository.fingerprint())
        ),
        links=links,
        rejected_claims=rejected,
        diagnostics=diagnostics,
        error_count=int(core_result.get("error_count", 0)),
        warning_count=int(core_result.get("warning_count", 0)),
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )
