"""Logical ADR -> Architecture IR fragment compiler for the stable logical profile."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...models.logical_adr import LogicalADR
from ...parser import ADRParser
from .adr_ir_fragment_rendering import (
    canonical_json_bytes,
    lower_ascii,
    norm,
    sha256_hex,
    sha256_prefixed_hex,
    sort_ids_utf8,
    sort_records_by_id,
)


LOGICAL_ADR_IR_PROFILE_VERSION = "logical_adr_ir_fragment.v1"
SUPPORTED_LOGICAL_ADR_SCHEMA_VERSION = "1.0"
DECISION_SUPPORTS_CAPABILITY_RELATIONSHIP = "decision_supports_capability"


class AdrIrFragmentCompileError(ValueError):
    """Compilation failed and emitted no IR fragment records."""


@dataclass(frozen=True)
class AdrIrSourceDescriptor:
    """Pipeline-supplied and/or deterministically derived source identity for one ADR."""

    artifact_uri: str
    input_ref: str


@dataclass(frozen=True)
class AdrIrFragmentCompileResult:
    """Deterministic logical ADR compilation result."""

    entities: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    canonical_fragment_bytes: bytes

    @property
    def records(self) -> list[dict[str, Any]]:
        """Return the globally sorted entity + relationship record set."""

        return sort_records_by_id([*self.entities, *self.relationships])


def compile_logical_adr_ir_fragments(
    *,
    adr_file_paths: list[Path],
    namespace: str,
    artifact_kind: str,
    last_updated: str,
    adapter_schema_version: str = LOGICAL_ADR_IR_PROFILE_VERSION,
    scope_root: Path | None = None,
    source_overrides: dict[Path, AdrIrSourceDescriptor] | None = None,
    parser: ADRParser | None = None,
) -> AdrIrFragmentCompileResult:
    """Compile explicit Logical ADR files into deterministic Architecture IR fragments."""

    if not adr_file_paths:
        raise AdrIrFragmentCompileError("At least one ADR file path is required.")
    if adapter_schema_version != LOGICAL_ADR_IR_PROFILE_VERSION:
        raise AdrIrFragmentCompileError(
            "Unsupported version pair: adapter schema version must be "
            f"{LOGICAL_ADR_IR_PROFILE_VERSION!r}."
        )

    parser = parser or ADRParser()
    ordered_paths = sorted((Path(path) for path in adr_file_paths), key=lambda item: item.as_posix())
    descriptor_map = _resolve_source_descriptors(
        ordered_paths,
        scope_root=scope_root,
        source_overrides=source_overrides or {},
    )

    pending_capabilities: list[tuple[dict[str, Any], dict[str, Any]]] = []
    pending_decisions: list[tuple[dict[str, Any], dict[str, Any]]] = []
    pending_relationships: list[tuple[dict[str, Any], dict[str, Any]]] = []

    emitted_capability_ids: set[str] = set()
    emitted_decision_ids: set[str] = set()
    emitted_relationship_ids: set[str] = set()
    emitted_entity_ids: set[str] = set()
    relationship_triples: set[tuple[str, str, str]] = set()

    for path in ordered_paths:
        try:
            raw = parser.parse_yaml(path)
            logical = parser.parse_logical_adr(path)
        except Exception as exc:
            raise AdrIrFragmentCompileError(f"Failed to parse Logical ADR {path}: {exc}") from exc
        source = descriptor_map[path.resolve()]

        _validate_profile_v1(raw, logical, adapter_schema_version=adapter_schema_version)

        capability_by_slug: dict[str, tuple[dict[str, Any], str]] = {}
        referenced_slugs: set[str] = set()

        for capability in logical.capabilities:
            slug_norm = lower_ascii(capability.id)
            if slug_norm in capability_by_slug:
                raise AdrIrFragmentCompileError(
                    f"Duplicate capability slug after normalization in {path}: {slug_norm}"
                )

            capability_id = _build_hashed_id(
                "capability",
                {
                    "namespace": namespace,
                    "slug": slug_norm,
                },
            )
            if capability_id in emitted_entity_ids or capability_id in emitted_capability_ids:
                raise AdrIrFragmentCompileError(f"Duplicate emitted capability id: {capability_id}")

            capability_record = {
                "id": capability_id,
                "kind": "capability",
                "slug": slug_norm,
                "title": norm(capability.name),
                "description": norm(capability.description),
                "status": logical.status.value,
            }

            normalized_tags = _normalize_tags(logical.tags)
            if normalized_tags:
                capability_record["tags"] = normalized_tags

            capability_fragment = _build_provenance_fragment(
                schema_version=logical.schema_version,
                document_id=norm(logical.id),
                decision_id="",
                record_kind="capability",
                record_id=capability_id,
                namespace=namespace,
            )

            capability_by_slug[slug_norm] = (capability_record, capability.id)
            pending_capabilities.append(
                (
                    capability_record,
                    _build_provenance(
                        artifact_uri=source.artifact_uri,
                        artifact_kind=artifact_kind,
                        last_updated=last_updated,
                        input_ref=source.input_ref,
                        adapter_schema_version=adapter_schema_version,
                        fragment=capability_fragment,
                    ),
                )
            )
            emitted_entity_ids.add(capability_id)
            emitted_capability_ids.add(capability_id)

        for decision in logical.decisions:
            if not decision.enables_capabilities:
                raise AdrIrFragmentCompileError(
                    f"Decision {decision.id} in {path} must enable at least one capability."
                )

            decision_key = _build_adr_decision_key(logical.id, decision.id)
            decision_id = _build_hashed_id(
                "decision",
                {
                    "namespace": namespace,
                    "adr_id": decision_key,
                },
            )
            if decision_id in emitted_entity_ids or decision_id in emitted_decision_ids:
                raise AdrIrFragmentCompileError(f"Duplicate emitted decision id: {decision_id}")

            decision_record = {
                "id": decision_id,
                "kind": "decision",
                "adr_id": decision_key,
                "status": _map_decision_status(logical.status.value),
                "authority_tier": _map_authority_tier(logical.status.value),
                "summary": norm(decision.summary),
            }
            supersedes = [norm(item) for item in decision.supersedes if norm(item)]
            if supersedes:
                decision_record["supersedes"] = supersedes

            decision_fragment = _build_provenance_fragment(
                schema_version=logical.schema_version,
                document_id=norm(logical.id),
                decision_id=norm(decision.id),
                record_kind="decision",
                record_id=decision_id,
                namespace=namespace,
            )
            pending_decisions.append(
                (
                    decision_record,
                    _build_provenance(
                        artifact_uri=source.artifact_uri,
                        artifact_kind=artifact_kind,
                        last_updated=last_updated,
                        input_ref=source.input_ref,
                        adapter_schema_version=adapter_schema_version,
                        fragment=decision_fragment,
                    ),
                )
            )
            emitted_entity_ids.add(decision_id)
            emitted_decision_ids.add(decision_id)

            for capability_ref in decision.enables_capabilities:
                resolved_slug = lower_ascii(capability_ref)
                capability_entry = capability_by_slug.get(resolved_slug)
                if capability_entry is None:
                    raise AdrIrFragmentCompileError(
                        f"Decision {decision.id} in {path} references unknown capability: {capability_ref}"
                    )
                capability_record, _ = capability_entry
                referenced_slugs.add(resolved_slug)

                relationship_triple = (
                    decision_id,
                    DECISION_SUPPORTS_CAPABILITY_RELATIONSHIP,
                    str(capability_record["id"]),
                )
                if relationship_triple in relationship_triples:
                    raise AdrIrFragmentCompileError(
                        "Duplicate relationship triple emitted for "
                        f"{decision.id} -> {capability_record['id']}"
                    )
                relationship_triples.add(relationship_triple)

                relationship_id = _build_hashed_id(
                    "rel",
                    {
                        "namespace": namespace,
                        "type": DECISION_SUPPORTS_CAPABILITY_RELATIONSHIP,
                        "from_id": decision_id,
                        "to_id": capability_record["id"],
                    },
                )
                if relationship_id in emitted_relationship_ids:
                    raise AdrIrFragmentCompileError(f"Duplicate emitted relationship id: {relationship_id}")

                relationship_record = {
                    "id": relationship_id,
                    "type": DECISION_SUPPORTS_CAPABILITY_RELATIONSHIP,
                    "from_id": decision_id,
                    "to_id": capability_record["id"],
                }
                relationship_fragment = _build_provenance_fragment(
                    schema_version=logical.schema_version,
                    document_id=norm(logical.id),
                    decision_id=norm(decision.id),
                    record_kind="relationship",
                    record_id=relationship_id,
                    namespace=namespace,
                )
                pending_relationships.append(
                    (
                        relationship_record,
                        _build_provenance(
                            artifact_uri=source.artifact_uri,
                            artifact_kind=artifact_kind,
                            last_updated=last_updated,
                            input_ref=source.input_ref,
                            adapter_schema_version=adapter_schema_version,
                            fragment=relationship_fragment,
                        ),
                    )
                )
                emitted_relationship_ids.add(relationship_id)

        unreferenced = sorted(
            set(capability_by_slug) - referenced_slugs,
            key=lambda item: item.encode("utf-8"),
        )
        if unreferenced:
            raise AdrIrFragmentCompileError(
                f"Every capability must be referenced by a decision in {path}; "
                f"unreferenced: {', '.join(unreferenced)}"
            )

    entities = _finalize_records([*pending_capabilities, *pending_decisions])
    relationships = _finalize_records(pending_relationships)
    canonical_fragment_bytes = canonical_json_bytes(sort_records_by_id([*entities, *relationships]))
    return AdrIrFragmentCompileResult(
        entities=entities,
        relationships=relationships,
        canonical_fragment_bytes=canonical_fragment_bytes,
    )


def _resolve_source_descriptors(
    file_paths: list[Path],
    *,
    scope_root: Path | None,
    source_overrides: dict[Path, AdrIrSourceDescriptor],
) -> dict[Path, AdrIrSourceDescriptor]:
    resolved_paths = [path.resolve() for path in file_paths]
    override_map = {Path(path).resolve(): descriptor for path, descriptor in source_overrides.items()}

    if scope_root is None:
        scope_root_path = Path(os.path.commonpath([str(path.parent) for path in resolved_paths])).resolve()
    else:
        scope_root_path = scope_root.resolve()

    descriptor_map: dict[Path, AdrIrSourceDescriptor] = {}
    for path in resolved_paths:
        if path in override_map:
            descriptor_map[path] = override_map[path]
            continue

        try:
            relative = path.relative_to(scope_root_path)
        except ValueError as exc:
            raise AdrIrFragmentCompileError(
                f"ADR path {path} is outside the selected scope root {scope_root_path}"
            ) from exc

        relative_posix = relative.as_posix()
        derived = AdrIrSourceDescriptor(
            artifact_uri=f"repo://{relative_posix}",
            input_ref=f"repo://{relative_posix}",
        )
        descriptor_map[path] = derived
    return descriptor_map


def _validate_profile_v1(
    raw: dict[str, Any],
    logical: LogicalADR,
    *,
    adapter_schema_version: str,
) -> None:
    if logical.schema_version != SUPPORTED_LOGICAL_ADR_SCHEMA_VERSION:
        raise AdrIrFragmentCompileError(
            "Unsupported version pair: ADR schema version must be "
            f"{SUPPORTED_LOGICAL_ADR_SCHEMA_VERSION!r} when adapter schema version is "
            f"{adapter_schema_version!r}."
        )
    if logical.adr_type.value != "logical":
        raise AdrIrFragmentCompileError(f"Unsupported adr_type: {logical.adr_type.value}")
    if not logical.id.startswith("ADR-L-"):
        raise AdrIrFragmentCompileError(
            f"Unsupported logical ADR id for the logical ADR IR profile v1: {logical.id}"
        )
    if "constraints" not in raw or not isinstance(raw["constraints"], list):
        raise AdrIrFragmentCompileError("constraints[] must exist and be an empty array.")
    if raw["constraints"]:
        raise AdrIrFragmentCompileError("constraints[] must be empty for the logical ADR IR profile v1.")
    if "invariants" not in raw or not isinstance(raw["invariants"], list):
        raise AdrIrFragmentCompileError("invariants[] must exist and be an empty array.")
    if raw["invariants"]:
        raise AdrIrFragmentCompileError("invariants[] must be empty for the logical ADR IR profile v1.")
    if not logical.decisions:
        raise AdrIrFragmentCompileError("decisions[] must be non-empty.")
    if not logical.capabilities:
        raise AdrIrFragmentCompileError("capabilities[] must be non-empty.")
    for decision in logical.decisions:
        if decision.governs_components:
            raise AdrIrFragmentCompileError(
                "governs_components must be absent or empty under the logical ADR IR "
                f"profile v1: {decision.id}"
            )


def _build_adr_decision_key(document_id: str, decision_id: str) -> str:
    return norm(f"{norm(document_id)}\u001f{norm(decision_id)}")


def _build_hashed_id(prefix: str, payload: dict[str, str]) -> str:
    return f"{prefix}:{sha256_hex(payload)}"


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized = {norm(tag) for tag in tags if norm(tag)}
    return sort_ids_utf8(normalized)


def _map_decision_status(status: str) -> str:
    mapping = {
        "proposed": "draft",
        "accepted": "promoted",
        "deprecated": "superseded",
        "superseded": "superseded",
    }
    return mapping[status]


def _map_authority_tier(status: str) -> str:
    mapping = {
        "proposed": "draft",
        "accepted": "promoted",
        "deprecated": "unknown",
        "superseded": "unknown",
    }
    return mapping[status]


def _build_provenance_fragment(
    *,
    schema_version: str,
    document_id: str,
    decision_id: str,
    record_kind: str,
    record_id: str,
    namespace: str,
) -> dict[str, str]:
    return {
        "schema_version": norm(schema_version),
        "document_id": norm(document_id),
        "decision_id": decision_id,
        "record_kind": record_kind,
        "record_id": record_id,
        "namespace": namespace,
    }


def _build_provenance(
    *,
    artifact_uri: str,
    artifact_kind: str,
    last_updated: str,
    input_ref: str,
    adapter_schema_version: str,
    fragment: dict[str, str],
) -> dict[str, Any]:
    return {
        "source": {
            "adapter": "adr",
            "artifact_uri": artifact_uri,
            "artifact_kind": artifact_kind,
        },
        "last_updated": last_updated,
        "derivation_chain": [
            {
                "step": 0,
                "adapter": "adr",
                "operation": "compile_logical_adr_to_ir_fragment",
                "input_ref": input_ref,
                "adapter_schema_version": adapter_schema_version,
                "content_hash": sha256_prefixed_hex(fragment),
            }
        ],
    }


def _finalize_records(
    records_with_provenance: list[tuple[dict[str, Any], dict[str, Any]]]
) -> list[dict[str, Any]]:
    final_records = []
    for record, provenance in records_with_provenance:
        merged = dict(record)
        merged["provenance"] = provenance
        final_records.append(merged)
    return sort_records_by_id(final_records)
