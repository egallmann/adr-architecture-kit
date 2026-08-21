"""Private implementation of the supported embodiment-linkage SDK operation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from .. import __version__
from ..decorators import embodies, enforces, implements
from ..models import ImplementationAttributionEvidenceV15, ImplementationAttributionEvidenceV16
from ..repository import ArchitectureRepository
from ..semantic_attribution.normalize import semantic_records
from ..semantic_attribution.vocabulary import RELATIONSHIP_ORDER, allowed_target_entity_types
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

_RELATIONSHIP_RANK = {name: index for index, name in enumerate(RELATIONSHIP_ORDER)}


def _provenance(record: Any) -> LinkageProvenance:
    value = record.provenance
    return LinkageProvenance(
        source_file=value.source_file,
        extractor=value.extractor,
        commit=value.commit,
        source_pointer=getattr(value, "source_pointer", None),
        start_line=getattr(value, "start_line", None),
        end_line=getattr(value, "end_line", None),
    )


def _occurrence_key(value: LinkageOccurrence) -> tuple[object, ...]:
    provenance = value.provenance
    return (
        provenance.source_file,
        provenance.source_pointer or "",
        provenance.start_line or 0,
        provenance.end_line or 0,
        provenance.extractor,
        provenance.commit or "",
        value.confidence,
        value.source_language or "",
    )


def _diagnostic(code: str, message: str, path: str, *, severity: str = "error") -> Diagnostic:
    return Diagnostic(
        severity=cast(Any, severity),
        code=code,
        message=message,
        path=path,
    )


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


@implements("019ffdba-3c42-7304-ab2f-bcd01cc6f9d3")
@enforces("019ffdba-3c42-74ea-993d-990027e528c0")
@embodies("019ffdba-3c42-75d5-b93b-f32f35152e32")
def build_embodiment_linkage(request: EmbodimentLinkageRequest) -> EmbodimentLinkageResult:
    """Resolve explicit evidence into a deterministic non-authoritative projection."""

    if not isinstance(request, EmbodimentLinkageRequest):
        raise TypeError("request must be an EmbodimentLinkageRequest")
    evidence = _parse_evidence(request.evidence_path)
    try:
        repository = ArchitectureRepository(request.project_root)
        repository.load()
    except Exception as exc:
        raise RepositoryError("Architecture repository could not be opened for linkage") from exc

    diagnostics: list[Diagnostic] = []
    rejected: list[RejectedEmbodimentClaim] = []
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    implementation_types: dict[str, str] = {}
    seen_occurrences: dict[tuple[object, ...], tuple[str, str, str | None]] = {}

    for record_index, record in enumerate(semantic_records(evidence)):
        provenance = _provenance(record)
        if not record.claims:
            severity = "error" if request.profile == "greenfield" else "warning"
            diagnostics.append(
                _diagnostic(
                    "attribution.missing_claims",
                    "implementation artifact is missing required architecture attribution",
                    f"records[{record_index}].claims",
                    severity=severity,
                )
            )
        previous_type = implementation_types.setdefault(
            record.implementation_entity_id, record.implementation_entity_type
        )
        type_conflict = previous_type != record.implementation_entity_type
        seen_in_record: set[tuple[str, str]] = set()
        for claim_index, claim in enumerate(record.claims):
            path = f"records[{record_index}].claims[{claim_index}]"
            occurrence = LinkageOccurrence(
                confidence=claim.confidence,
                provenance=provenance,
                source_language=record.attribution_source_language,
            )
            occurrence_identity = (
                record.implementation_entity_id,
                claim.relationship,
                claim.target_entity_id,
                *_occurrence_key(occurrence)[:-2],
            )
            claim_diagnostics: list[Diagnostic] = []
            pair = (claim.relationship, claim.target_entity_id)
            if pair in seen_in_record:
                claim_diagnostics.append(
                    _diagnostic(
                        "attribution.duplicate_claim",
                        "duplicate relationship/target claim within one record",
                        path,
                    )
                )
            seen_in_record.add(pair)
            if occurrence_identity in seen_occurrences:
                previous_path, previous_confidence, previous_language = seen_occurrences[
                    occurrence_identity
                ]
                if (
                    previous_confidence == occurrence.confidence
                    and previous_language == occurrence.source_language
                ):
                    code = "attribution.duplicate_occurrence"
                    message = f"exact evidence occurrence already declared at {previous_path}"
                else:
                    code = "attribution.conflicting_occurrence"
                    message = (
                        "evidence occurrence has conflicting confidence or source-language "
                        f"qualifiers relative to {previous_path}"
                    )
                claim_diagnostics.append(_diagnostic(code, message, path))
            else:
                seen_occurrences[occurrence_identity] = (
                    path,
                    occurrence.confidence,
                    occurrence.source_language,
                )
            if type_conflict:
                claim_diagnostics.append(
                    _diagnostic(
                        "attribution.conflicting_implementation_type",
                        f"implementation entity was previously typed {previous_type}",
                        path,
                    )
                )
            if (
                evidence.schema_version == "1.6"
                and claim.relationship == "enforces"
                and claim.confidence != "declared"
            ):
                claim_diagnostics.append(
                    _diagnostic(
                        "attribution.v16_enforces_confidence",
                        "v1.6 enforces requires confidence declared",
                        path,
                    )
                )

            entity = repository.find_entity_by_uuid(claim.target_entity_id)
            if entity is None:
                claim_diagnostics.append(
                    _diagnostic(
                        "attribution.unresolved_target",
                        f"referenced architecture entity does not exist: {claim.target_entity_id}",
                        path,
                    )
                )
            else:
                if (
                    claim.asserted_target_entity_type is not None
                    and claim.asserted_target_entity_type != entity.entity_type
                ):
                    claim_diagnostics.append(
                        _diagnostic(
                            "attribution.asserted_type_mismatch",
                            f"asserted target type {claim.asserted_target_entity_type} does not match {entity.entity_type}",
                            path,
                        )
                    )
                if entity.entity_type not in allowed_target_entity_types(claim.relationship):
                    claim_diagnostics.append(
                        _diagnostic(
                            "attribution.illegal_target_type",
                            f"{claim.relationship} does not admit target type {entity.entity_type}",
                            path,
                        )
                    )

            errors = [item for item in claim_diagnostics if item.severity == "error"]
            diagnostics.extend(claim_diagnostics)
            if errors or entity is None:
                rejected.append(
                    RejectedEmbodimentClaim(
                        implementation_entity_id=record.implementation_entity_id,
                        implementation_entity_type=record.implementation_entity_type,
                        relationship=claim.relationship,
                        target_entity_id=claim.target_entity_id,
                        confidence=claim.confidence,
                        provenance=provenance,
                        diagnostics=tuple(claim_diagnostics),
                    )
                )
                continue

            warnings: list[Diagnostic] = []
            if entity.lifecycle_stage in {"deprecated", "superseded"}:
                warning = _diagnostic(
                    "attribution.target_lifecycle",
                    f"referenced architecture entity is {entity.lifecycle_stage}",
                    path,
                    severity="warning",
                )
                warnings.append(warning)
                diagnostics.append(warning)
            key = (record.implementation_entity_id, claim.relationship, claim.target_entity_id)
            bucket = grouped.setdefault(
                key,
                {
                    "implementation_entity_type": record.implementation_entity_type,
                    "entity": entity,
                    "occurrences": [],
                    "diagnostics": [],
                },
            )
            bucket["occurrences"].append(occurrence)
            bucket["diagnostics"].extend(warnings)

    links: list[EmbodimentIntentLink] = []
    for (implementation_id, relationship, target_id), bucket in grouped.items():
        entity = bucket["entity"]
        occurrences = tuple(sorted(bucket["occurrences"], key=_occurrence_key))
        link_diagnostics = tuple(bucket["diagnostics"])
        links.append(
            EmbodimentIntentLink(
                implementation_entity_id=implementation_id,
                implementation_entity_type=bucket["implementation_entity_type"],
                relationship=cast(Any, relationship),
                target_entity_id=target_id,
                target_entity_type=entity.entity_type,
                target_alias_id=entity.alias_id,
                target_alias_name=entity.alias_name,
                target_lifecycle=entity.lifecycle_stage,
                occurrences=occurrences,
                validation_status="warning" if link_diagnostics else "valid",
                diagnostics=link_diagnostics,
            )
        )
    links.sort(
        key=lambda link: (
            link.implementation_entity_id,
            _RELATIONSHIP_RANK[link.relationship],
            link.target_entity_id,
            _occurrence_key(link.occurrences[0]) if link.occurrences else (),
        )
    )
    rejected.sort(
        key=lambda item: (
            item.implementation_entity_id,
            _RELATIONSHIP_RANK.get(item.relationship, 99),
            item.target_entity_id,
            item.provenance.source_file,
            item.provenance.source_pointer or "",
            item.provenance.start_line or 0,
        )
    )
    error_count = sum(item.severity == "error" for item in diagnostics)
    warning_count = sum(item.severity == "warning" for item in diagnostics)
    return EmbodimentLinkageResult(
        request=request,
        success=error_count == 0,
        evidence_schema_version=evidence.schema_version,
        architecture_fingerprint=repository.fingerprint(),
        links=tuple(links),
        rejected_claims=tuple(rejected),
        diagnostics=tuple(diagnostics),
        error_count=error_count,
        warning_count=warning_count,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )
