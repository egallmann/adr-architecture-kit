"""Private normalized-bundle assembly shared by repository and SDK adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

import yaml
from pydantic import BaseModel

from ..decorators import implements_adr
from ..models import (
    ArchitectureIndex,
    NormalizedArchitectureModel,
    NormalizedEntity,
    NormalizedEntityRegistry,
    RemediationLedger,
    RelationshipRegistry,
    UnresolvedRegistry,
)
from ..parser import ADRParser
from .registry_loader import (
    fingerprint_payload,
    load_architecture_index,
    load_normalized_entity_registry,
    load_remediation_ledger,
    load_relationship_registry,
    load_unresolved_registry,
    model_payload,
)
from .registry_paths import discover_repository_paths, resolve_index_reference

SUBSET_TYPES: dict[str, tuple[str, str]] = {
    "component_registry_path": ("components", "component"),
    "capability_registry_path": ("capabilities", "capability"),
    "decision_registry_path": ("decisions", "decision"),
    "invariant_registry_path": ("invariants", "invariant"),
    "system_registry_path": ("systems", "system"),
}

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class NormalizedBundle:
    """Private loaded representation used to populate supported boundaries."""

    architecture_index: ArchitectureIndex
    entity_registry: NormalizedEntityRegistry
    relationship_registry: RelationshipRegistry
    unresolved_registry: UnresolvedRegistry
    remediation_ledger: RemediationLedger | None
    subsets: dict[str, list[NormalizedEntity]]
    fingerprint: str
    model: NormalizedArchitectureModel


def _validate_subset(
    registry: NormalizedEntityRegistry,
    subset_name: str,
    expected_type: str,
    primary_by_id: dict[str, NormalizedEntity],
) -> None:
    for entity in registry.entities:
        primary_entity = primary_by_id.get(entity.id)
        if primary_entity is None:
            raise ValueError(
                f"Subset registry {subset_name} references unknown entity ID: {entity.id}"
            )
        if entity.entity_type != expected_type:
            raise ValueError(
                f"Subset registry {subset_name} has mismatched entity_type for {entity.id}: "
                f"expected {expected_type}, got {entity.entity_type}"
            )
        if entity.canonical_source.source_ref != primary_entity.canonical_source.source_ref:
            raise ValueError(
                f"Subset registry {subset_name} has mismatched canonical_source.source_ref "
                f"for {entity.id}"
            )


def _assemble(
    scope_root: Path,
    architecture_index: ArchitectureIndex,
    load_registry: Callable[[str], NormalizedEntityRegistry],
    relationship_registry: RelationshipRegistry,
    unresolved_registry: UnresolvedRegistry,
    remediation_ledger: RemediationLedger | None,
) -> NormalizedBundle:
    primary_registry = load_registry(architecture_index.entity_registry_path)
    primary_by_id = {entity.id: entity for entity in primary_registry.entities}
    subsets: dict[str, list[NormalizedEntity]] = {}
    subset_models: dict[str, NormalizedEntityRegistry] = {}
    for field_name, (subset_name, expected_type) in SUBSET_TYPES.items():
        registry = load_registry(str(getattr(architecture_index, field_name)))
        _validate_subset(registry, subset_name, expected_type, primary_by_id)
        subsets[subset_name] = list(registry.entities)
        subset_models[subset_name] = registry

    fingerprint = fingerprint_payload(
        {
            "mode": "normalized",
            "architecture_index": model_payload(architecture_index),
            "entity_registry": model_payload(primary_registry),
            "relationship_registry": model_payload(relationship_registry),
            "unresolved_registry": model_payload(unresolved_registry),
            "remediation_ledger": model_payload(remediation_ledger),
            "subset_registries": {
                name: model_payload(model) for name, model in sorted(subset_models.items())
            },
        }
    )
    model = NormalizedArchitectureModel(
        mode="normalized",
        scope_root=str(scope_root),
        architecture_namespace=architecture_index.architecture_namespace,
        fingerprint=fingerprint,
        entities=list(primary_registry.entities),
        relationships=list(relationship_registry.relationships),
        unresolved=list(unresolved_registry.unresolved),
        validation_summary=architecture_index.validation_summary,
        source_coverage=architecture_index.source_coverage,
    )
    return NormalizedBundle(
        architecture_index=architecture_index,
        entity_registry=primary_registry,
        relationship_registry=relationship_registry,
        unresolved_registry=unresolved_registry,
        remediation_ledger=remediation_ledger,
        subsets=subsets,
        fingerprint=fingerprint,
        model=model,
    )


@implements_adr("ADR-L-0013", "ADR-PC-0004")
def load_normalized_bundle_from_paths(
    parser: ADRParser,
    scope_root: Path,
    index_path: Path,
) -> NormalizedBundle:
    """Load one normalized bundle from repository-owned artifact paths."""

    root = Path(scope_root).resolve()
    index = load_architecture_index(parser, index_path)

    def load_registry(relative_path: str) -> NormalizedEntityRegistry:
        return load_normalized_entity_registry(
            parser,
            resolve_index_reference(root, relative_path),
        )

    relationship_registry = load_relationship_registry(
        parser,
        resolve_index_reference(root, index.relationship_registry_path),
    )
    unresolved_registry = load_unresolved_registry(
        parser,
        resolve_index_reference(root, index.unresolved_registry_path),
    )
    remediation_path = discover_repository_paths(root).remediation_ledger
    remediation = (
        load_remediation_ledger(parser, remediation_path) if remediation_path.exists() else None
    )
    return _assemble(
        root,
        index,
        load_registry,
        relationship_registry,
        unresolved_registry,
        remediation,
    )


def _model_from_bytes(model_type: type[ModelT], content: bytes, relative_path: str) -> ModelT:
    try:
        payload: Any = yaml.safe_load(content.decode("utf-8"))
        return model_type.model_validate(payload)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        raise ValueError(f"Failed to load emitted registry: {relative_path}: {exc}") from exc


@implements_adr("ADR-L-0013", "ADR-PC-0004")
def load_normalized_bundle_from_bytes(
    scope_root: Path,
    artifacts: Mapping[str, bytes],
) -> NormalizedBundle:
    """Build a detached normalized bundle directly from emitted artifact bytes."""

    root = Path(scope_root).resolve()

    def content(relative_path: str) -> bytes:
        normalized = resolve_index_reference(root, relative_path).relative_to(root).as_posix()
        try:
            return artifacts[normalized]
        except KeyError as exc:
            raise ValueError(f"Required emitted registry is missing: {normalized}") from exc

    index_path = "adrs/index/architecture-index.yaml"
    index = _model_from_bytes(ArchitectureIndex, content(index_path), index_path)

    def load_registry(relative_path: str) -> NormalizedEntityRegistry:
        return _model_from_bytes(
            NormalizedEntityRegistry,
            content(relative_path),
            relative_path,
        )

    relationship_registry = _model_from_bytes(
        RelationshipRegistry,
        content(index.relationship_registry_path),
        index.relationship_registry_path,
    )
    unresolved_registry = _model_from_bytes(
        UnresolvedRegistry,
        content(index.unresolved_registry_path),
        index.unresolved_registry_path,
    )
    return _assemble(
        root,
        index,
        load_registry,
        relationship_registry,
        unresolved_registry,
        None,
    )
