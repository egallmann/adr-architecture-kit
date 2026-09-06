"""Private normalized-bundle assembly shared by repository and SDK adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar, cast

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
from ..models.v2_0 import (
    NormalizedArchitectureModelV2,
    NormalizedEntityRegistryV2,
    NormalizedEntityV2,
    RelationshipRegistryV2,
    UnresolvedRegistryV2,
)
from ..models.v2_1 import (
    NormalizedArchitectureModelV21,
    NormalizedEntityRegistryV21,
    NormalizedEntityV21,
    RelationshipRegistryV21,
    UnresolvedRegistryV21,
)
from ..models.v2_2 import (
    NormalizedArchitectureModelV22,
    NormalizedEntityRegistryV22,
    NormalizedEntityV22,
    RelationshipRegistryV22,
    UnresolvedRegistryV22,
)
from ..parser import ADRParser
from .registry_loader import (
    fingerprint_payload,
    load_architecture_index,
    load_normalized_entity_registry,
    load_normalized_entity_registry_v2,
    load_normalized_entity_registry_v21,
    load_normalized_entity_registry_v22,
    load_relationship_registry,
    load_relationship_registry_v2,
    load_relationship_registry_v21,
    load_relationship_registry_v22,
    load_remediation_ledger,
    load_unresolved_registry,
    load_unresolved_registry_v2,
    load_unresolved_registry_v21,
    load_unresolved_registry_v22,
    model_payload,
    peek_registry_schema_version,
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
NormalizedModelVersion = Literal["1.1", "2.0", "2.1", "2.2"]


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
    model_version: NormalizedModelVersion = "1.1"


@dataclass(frozen=True)
class NormalizedBundleV2:
    """Private loaded representation for model 2.0 UUID identity bundles."""

    architecture_index: ArchitectureIndex
    entity_registry: NormalizedEntityRegistryV2
    relationship_registry: RelationshipRegistryV2
    unresolved_registry: UnresolvedRegistryV2
    remediation_ledger: RemediationLedger | None
    subsets: dict[str, list[NormalizedEntityV2]]
    fingerprint: str
    model: NormalizedArchitectureModelV2
    model_version: NormalizedModelVersion = "2.0"


@dataclass(frozen=True)
class NormalizedBundleV21:
    """Private loaded representation for the explicit model 2.1 boundary."""

    architecture_index: ArchitectureIndex
    entity_registry: NormalizedEntityRegistryV21
    relationship_registry: RelationshipRegistryV21
    unresolved_registry: UnresolvedRegistryV21
    remediation_ledger: RemediationLedger | None
    subsets: dict[str, list[NormalizedEntityV21]]
    fingerprint: str
    model: NormalizedArchitectureModelV21
    model_version: NormalizedModelVersion = "2.1"


@dataclass(frozen=True)
class NormalizedBundleV22:
    """Private loaded representation for the explicit model 2.2 boundary."""

    architecture_index: ArchitectureIndex
    entity_registry: NormalizedEntityRegistryV22
    relationship_registry: RelationshipRegistryV22
    unresolved_registry: UnresolvedRegistryV22
    remediation_ledger: RemediationLedger | None
    subsets: dict[str, list[NormalizedEntityV22]]
    fingerprint: str
    model: NormalizedArchitectureModelV22
    model_version: NormalizedModelVersion = "2.2"


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
    available_paths: set[str] | None = None,
) -> NormalizedBundle:
    primary_registry = load_registry(architecture_index.entity_registry_path)
    primary_by_id = {entity.id: entity for entity in primary_registry.entities}
    subsets: dict[str, list[NormalizedEntity]] = {}
    subset_models: dict[str, NormalizedEntityRegistry] = {}
    for field_name, (subset_name, expected_type) in SUBSET_TYPES.items():
        relative_path = str(getattr(architecture_index, field_name))
        exists = (
            relative_path in available_paths
            if available_paths is not None
            else resolve_index_reference(scope_root, relative_path).exists()
        )
        if not exists:
            continue
        registry = load_registry(relative_path)
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


def _validate_subset_v2(
    registry: NormalizedEntityRegistryV2,
    subset_name: str,
    expected_type: str,
    primary_by_id: dict[str, NormalizedEntityV2],
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


def _assemble_v2(
    scope_root: Path,
    architecture_index: ArchitectureIndex,
    load_registry: Callable[[str], NormalizedEntityRegistryV2],
    relationship_registry: RelationshipRegistryV2,
    unresolved_registry: UnresolvedRegistryV2,
    remediation_ledger: RemediationLedger | None,
    available_paths: set[str] | None = None,
) -> NormalizedBundleV2:
    primary_registry = load_registry(architecture_index.entity_registry_path)
    primary_by_id = {entity.id: entity for entity in primary_registry.entities}
    subsets: dict[str, list[NormalizedEntityV2]] = {}
    subset_models: dict[str, NormalizedEntityRegistryV2] = {}
    for field_name, (subset_name, expected_type) in SUBSET_TYPES.items():
        relative_path = str(getattr(architecture_index, field_name))
        exists = (
            relative_path in available_paths
            if available_paths is not None
            else resolve_index_reference(scope_root, relative_path).exists()
        )
        if not exists:
            continue
        registry = load_registry(relative_path)
        _validate_subset_v2(registry, subset_name, expected_type, primary_by_id)
        subsets[subset_name] = list(registry.entities)
        subset_models[subset_name] = registry

    fingerprint = fingerprint_payload(
        {
            "mode": "normalized",
            "model_version": "2.0",
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
    model = NormalizedArchitectureModelV2(
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
    return NormalizedBundleV2(
        architecture_index=architecture_index,
        entity_registry=primary_registry,
        relationship_registry=relationship_registry,
        unresolved_registry=unresolved_registry,
        remediation_ledger=remediation_ledger,
        subsets=subsets,
        fingerprint=fingerprint,
        model=model,
    )


def _assemble_v21(
    scope_root: Path,
    architecture_index: ArchitectureIndex,
    load_registry: Callable[[str], NormalizedEntityRegistryV21],
    relationship_registry: RelationshipRegistryV21,
    unresolved_registry: UnresolvedRegistryV21,
    remediation_ledger: RemediationLedger | None,
    available_paths: set[str] | None = None,
) -> NormalizedBundleV21:
    primary_registry = load_registry(architecture_index.entity_registry_path)
    primary_by_id = {entity.id: entity for entity in primary_registry.entities}
    subsets: dict[str, list[NormalizedEntityV21]] = {}
    subset_models: dict[str, NormalizedEntityRegistryV21] = {}
    for field_name, (subset_name, expected_type) in SUBSET_TYPES.items():
        relative_path = str(getattr(architecture_index, field_name))
        exists = (
            relative_path in available_paths
            if available_paths is not None
            else resolve_index_reference(scope_root, relative_path).exists()
        )
        if not exists:
            continue
        registry = load_registry(relative_path)
        for entity in registry.entities:
            primary_entity = primary_by_id.get(entity.id)
            if primary_entity is None:
                raise ValueError(
                    f"Subset registry {subset_name} references unknown entity ID: {entity.id}"
                )
            if entity.entity_type != expected_type:
                raise ValueError(
                    f"Subset registry {subset_name} has mismatched entity_type for {entity.id}"
                )
        subsets[subset_name] = list(registry.entities)
        subset_models[subset_name] = registry
    fingerprint = fingerprint_payload(
        {
            "mode": "normalized",
            "model_version": "2.1",
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
    model = NormalizedArchitectureModelV21(
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
    return NormalizedBundleV21(
        architecture_index=architecture_index,
        entity_registry=primary_registry,
        relationship_registry=relationship_registry,
        unresolved_registry=unresolved_registry,
        remediation_ledger=remediation_ledger,
        subsets=subsets,
        fingerprint=fingerprint,
        model=model,
    )


def _assemble_v22(
    scope_root: Path,
    architecture_index: ArchitectureIndex,
    load_registry: Callable[[str], NormalizedEntityRegistryV22],
    relationship_registry: RelationshipRegistryV22,
    unresolved_registry: UnresolvedRegistryV22,
    remediation_ledger: RemediationLedger | None,
    available_paths: set[str] | None = None,
) -> NormalizedBundleV22:
    primary_registry = load_registry(architecture_index.entity_registry_path)
    primary_by_id = {entity.id: entity for entity in primary_registry.entities}
    subsets: dict[str, list[NormalizedEntityV22]] = {}
    subset_models: dict[str, NormalizedEntityRegistryV22] = {}
    for field_name, (subset_name, expected_type) in SUBSET_TYPES.items():
        relative_path = str(getattr(architecture_index, field_name))
        exists = (
            relative_path in available_paths
            if available_paths is not None
            else resolve_index_reference(scope_root, relative_path).exists()
        )
        if not exists:
            continue
        registry = load_registry(relative_path)
        for entity in registry.entities:
            primary_entity = primary_by_id.get(entity.id)
            if primary_entity is None:
                raise ValueError(
                    f"Subset registry {subset_name} references unknown entity ID: {entity.id}"
                )
            if entity.entity_type != expected_type:
                raise ValueError(
                    f"Subset registry {subset_name} has mismatched entity_type for {entity.id}"
                )
        subsets[subset_name] = list(registry.entities)
        subset_models[subset_name] = registry
    fingerprint = fingerprint_payload(
        {
            "mode": "normalized",
            "model_version": "2.2",
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
    model = NormalizedArchitectureModelV22(
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
    return NormalizedBundleV22(
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
) -> NormalizedBundle | NormalizedBundleV2 | NormalizedBundleV21 | NormalizedBundleV22:
    """Load one normalized bundle from repository-owned artifact paths."""

    root = Path(scope_root).resolve()
    index = load_architecture_index(parser, index_path)
    entity_registry_path = resolve_index_reference(root, index.entity_registry_path)
    model_version = peek_registry_schema_version(entity_registry_path)
    remediation_path = discover_repository_paths(root).remediation_ledger
    remediation = (
        load_remediation_ledger(parser, remediation_path) if remediation_path.exists() else None
    )

    if model_version == "2.2":

        def load_registry_v22(relative_path: str) -> NormalizedEntityRegistryV22:
            return load_normalized_entity_registry_v22(
                parser,
                resolve_index_reference(root, relative_path),
            )

        return _assemble_v22(
            root,
            index,
            load_registry_v22,
            load_relationship_registry_v22(
                parser,
                resolve_index_reference(root, index.relationship_registry_path),
            ),
            load_unresolved_registry_v22(
                parser,
                resolve_index_reference(root, index.unresolved_registry_path),
            ),
            remediation,
        )

    if model_version == "2.1":

        def load_registry_v21(relative_path: str) -> NormalizedEntityRegistryV21:
            return load_normalized_entity_registry_v21(
                parser,
                resolve_index_reference(root, relative_path),
            )

        return _assemble_v21(
            root,
            index,
            load_registry_v21,
            load_relationship_registry_v21(
                parser,
                resolve_index_reference(root, index.relationship_registry_path),
            ),
            load_unresolved_registry_v21(
                parser,
                resolve_index_reference(root, index.unresolved_registry_path),
            ),
            remediation,
        )

    if model_version == "2.0":

        def load_registry_v2(relative_path: str) -> NormalizedEntityRegistryV2:
            return load_normalized_entity_registry_v2(
                parser,
                resolve_index_reference(root, relative_path),
            )

        relationship_registry_v2 = load_relationship_registry_v2(
            parser,
            resolve_index_reference(root, index.relationship_registry_path),
        )
        unresolved_registry_v2 = load_unresolved_registry_v2(
            parser,
            resolve_index_reference(root, index.unresolved_registry_path),
        )
        return _assemble_v2(
            root,
            index,
            load_registry_v2,
            relationship_registry_v2,
            unresolved_registry_v2,
            remediation,
        )

    def load_registry(relative_path: str) -> NormalizedEntityRegistry:
        loaded = load_normalized_entity_registry(
            parser,
            resolve_index_reference(root, relative_path),
        )
        return cast(NormalizedEntityRegistry, loaded)

    relationship_registry = cast(
        RelationshipRegistry,
        load_relationship_registry(
            parser,
            resolve_index_reference(root, index.relationship_registry_path),
        ),
    )
    unresolved_registry = cast(
        UnresolvedRegistry,
        load_unresolved_registry(
            parser,
            resolve_index_reference(root, index.unresolved_registry_path),
        ),
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
) -> NormalizedBundle | NormalizedBundleV21 | NormalizedBundleV22:
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

    entity_registry_payload = yaml.safe_load(content(index.entity_registry_path).decode("utf-8"))
    if (
        isinstance(entity_registry_payload, dict)
        and entity_registry_payload.get("schema_version") == "2.2"
    ):

        def load_registry_v22(relative_path: str) -> NormalizedEntityRegistryV22:
            return _model_from_bytes(
                NormalizedEntityRegistryV22, content(relative_path), relative_path
            )

        return _assemble_v22(
            root,
            index,
            load_registry_v22,
            _model_from_bytes(
                RelationshipRegistryV22,
                content(index.relationship_registry_path),
                index.relationship_registry_path,
            ),
            _model_from_bytes(
                UnresolvedRegistryV22,
                content(index.unresolved_registry_path),
                index.unresolved_registry_path,
            ),
            None,
            set(artifacts),
        )

    if (
        isinstance(entity_registry_payload, dict)
        and entity_registry_payload.get("schema_version") == "2.1"
    ):

        def load_registry_v21(relative_path: str) -> NormalizedEntityRegistryV21:
            return _model_from_bytes(
                NormalizedEntityRegistryV21, content(relative_path), relative_path
            )

        return _assemble_v21(
            root,
            index,
            load_registry_v21,
            _model_from_bytes(
                RelationshipRegistryV21,
                content(index.relationship_registry_path),
                index.relationship_registry_path,
            ),
            _model_from_bytes(
                UnresolvedRegistryV21,
                content(index.unresolved_registry_path),
                index.unresolved_registry_path,
            ),
            None,
            set(artifacts),
        )

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
        set(artifacts),
    )
