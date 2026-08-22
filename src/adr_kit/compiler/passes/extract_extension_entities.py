"""Shared extraction pass for v1.4 consumer extension records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...compiler.ir import IREntity, IRRelationship
from ...semantic_extensions import validate_extension_type


@dataclass(frozen=True)
class ExtensionExtractionResult:
    entities: tuple[IREntity, ...]
    relationships: tuple[IRRelationship, ...]


def _dump(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="python")
    return dict(item)


def extract_extension_entities(
    adrs: list[tuple[object, Path]],
    *,
    architecture_namespace: str,
    source_path,
    canonical,
    provenance,
) -> ExtensionExtractionResult:
    """Extract validated extension entities and authored relationships.

    The parser owns record-local validation; this pass owns corpus namespace
    ownership and endpoint existence.  It never allocates identity.
    """

    entities: list[IREntity] = []
    relationships: list[IRRelationship] = []
    known_ids: set[str] = set()
    known_aliases: set[str] = set()

    for adr, path in adrs:
        artifact = source_path(path)
        adr_id = str(getattr(adr, "id"))
        for index, raw in enumerate(getattr(adr, "extension_entities", []) or []):
            item = _dump(raw)
            entity_id = str(item["id"])
            alias_id = str(item["alias_id"])
            if entity_id in known_ids:
                raise ValueError(f"Duplicate extension entity UUID: {entity_id}")
            if alias_id in known_aliases:
                raise ValueError(f"Duplicate extension entity alias: {alias_id}")
            validate_extension_type(
                str(item["entity_type"]),
                architecture_namespace=architecture_namespace,
                kind="entity",
            )
            known_ids.add(entity_id)
            known_aliases.add(alias_id)
            source_ref = f"{adr_id}#/extension_entities/{index}"
            rationale = str(item["rationale"])
            entities.append(
                IREntity(
                    id=entity_id,
                    entity_type=str(item["entity_type"]),
                    name=str(item["alias_name"]),
                    summary=" ".join(rationale.split())[:220],
                    canonical_source=canonical("extension_entity", source_ref, artifact),
                    metadata={
                        "alias_id": alias_id,
                        "alias_name": str(item["alias_name"]),
                        "status": getattr(adr, "status").value,
                    },
                    extension={
                        "properties": dict(item.get("properties") or {}),
                        "rationale": rationale,
                    },
                    provenance=provenance(
                        "extension_entity", source_ref, "extract_extension", "explicit"
                    ),
                )
            )

        for index, raw in enumerate(getattr(adr, "extension_relationships", []) or []):
            item = _dump(raw)
            relationship_id = str(item["id"])
            alias_id = str(item["alias_id"])
            validate_extension_type(
                str(item["relationship_type"]),
                architecture_namespace=architecture_namespace,
                kind="relationship",
            )
            source_ref = f"{adr_id}#/extension_relationships/{index}"
            relationships.append(
                IRRelationship(
                    relationship_type=str(item["relationship_type"]),
                    from_entity_id=str(item["from_entity_id"]),
                    to_entity_id=str(item["to_entity_id"]),
                    canonical_source_ref=source_ref,
                    id=relationship_id,
                    alias_id=alias_id,
                    alias_name=str(item["alias_name"]),
                    extension={
                        "properties": dict(item.get("properties") or {}),
                        "rationale": str(item["rationale"]),
                    },
                    source_owner_id=adr_id,
                    source_pointer=source_ref,
                )
            )

    entity_ids = known_ids | {entity.id for entity in entities}
    for relationship in relationships:
        if (
            relationship.from_entity_id not in entity_ids
            or relationship.to_entity_id not in entity_ids
        ):
            # Core UUID endpoints are resolved by the caller after core extraction.
            continue
    return ExtensionExtractionResult(tuple(entities), tuple(relationships))
