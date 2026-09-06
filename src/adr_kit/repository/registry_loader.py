"""Loader helpers for architecture repository registries."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import yaml

from ..decorators import implements_adr
from ..models import (
    ArchitectureIndex,
    EntityRegistry,
    NormalizedEntityRegistry,
    RemediationLedger,
    RelationshipRegistry,
    UnresolvedRegistry,
)
from ..models.v2_0 import (
    NormalizedEntityRegistryV2,
    RelationshipRegistryV2,
    UnresolvedRegistryV2,
)
from ..models.v2_1 import (
    NormalizedEntityRegistryV21,
    RelationshipRegistryV21,
    UnresolvedRegistryV21,
)
from ..models.v2_2 import (
    NormalizedEntityRegistryV22,
    RelationshipRegistryV22,
    UnresolvedRegistryV22,
)
from ..parser import ADRParseError, ADRParser, ADRSchemaValidationError


@implements_adr("ADR-L-0013")
def peek_registry_schema_version(path: Path) -> str:
    """Return the declared schema_version for a registry YAML file."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to load registry: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Failed to load registry: {path}: expected mapping")
    version = payload.get("schema_version")
    if version in ("1.1", "2.0", "2.1", "2.2"):
        return str(version)
    raise ValueError(f"Failed to load registry: {path}: unsupported schema_version {version!r}")


@implements_adr("ADR-L-0013")
def load_architecture_index(parser: ADRParser, path: Path) -> ArchitectureIndex:
    """Load and validate an architecture index."""
    return cast(ArchitectureIndex, _wrap_parse(lambda: parser.parse_architecture_index(path), path))


@implements_adr("ADR-L-0013")
def load_normalized_entity_registry(
    parser: ADRParser, path: Path
) -> NormalizedEntityRegistry | NormalizedEntityRegistryV2:
    """Load and validate a normalized entity registry (1.1, 2.0, or 2.1)."""
    version = peek_registry_schema_version(path)
    if version == "2.2":
        return load_normalized_entity_registry_v22(parser, path)
    if version == "2.0":
        return load_normalized_entity_registry_v2(parser, path)
    if version == "2.1":
        return load_normalized_entity_registry_v21(parser, path)
    return cast(
        NormalizedEntityRegistry,
        _wrap_parse(lambda: parser.parse_normalized_entity_registry(path), path),
    )


@implements_adr("ADR-L-0013", "ADR-L-0019")
def load_normalized_entity_registry_v2(parser: ADRParser, path: Path) -> NormalizedEntityRegistryV2:
    """Load and validate a model 2.0 normalized entity registry."""
    return cast(
        NormalizedEntityRegistryV2,
        _wrap_parse(
            lambda: NormalizedEntityRegistryV2.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013", "ADR-L-0023")
def load_normalized_entity_registry_v21(parser: ADRParser, path: Path) -> NormalizedEntityRegistryV21:
    """Load and validate a model 2.1 normalized entity registry."""
    return cast(
        NormalizedEntityRegistryV21,
        _wrap_parse(
            lambda: NormalizedEntityRegistryV21.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013")
def load_relationship_registry(
    parser: ADRParser, path: Path
) -> RelationshipRegistry | RelationshipRegistryV2:
    """Load and validate a relationship registry (1.1, 2.0, or 2.1)."""
    version = peek_registry_schema_version(path)
    if version == "2.2":
        return load_relationship_registry_v22(parser, path)
    if version == "2.0":
        return load_relationship_registry_v2(parser, path)
    if version == "2.1":
        return load_relationship_registry_v21(parser, path)
    return cast(
        RelationshipRegistry,
        _wrap_parse(lambda: parser.parse_relationship_registry(path), path),
    )


@implements_adr("ADR-L-0013", "ADR-L-0019")
def load_relationship_registry_v2(parser: ADRParser, path: Path) -> RelationshipRegistryV2:
    """Load and validate a model 2.0 relationship registry."""
    return cast(
        RelationshipRegistryV2,
        _wrap_parse(
            lambda: RelationshipRegistryV2.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013", "ADR-L-0023")
def load_relationship_registry_v21(parser: ADRParser, path: Path) -> RelationshipRegistryV21:
    """Load and validate a model 2.1 canonical/compatibility relationship registry."""
    return cast(
        RelationshipRegistryV21,
        _wrap_parse(
            lambda: RelationshipRegistryV21.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013")
def load_unresolved_registry(
    parser: ADRParser, path: Path
) -> UnresolvedRegistry | UnresolvedRegistryV2:
    """Load and validate an unresolved registry (1.1, 2.0, or 2.1)."""
    version = peek_registry_schema_version(path)
    if version == "2.2":
        return load_unresolved_registry_v22(parser, path)
    if version == "2.0":
        return load_unresolved_registry_v2(parser, path)
    if version == "2.1":
        return load_unresolved_registry_v21(parser, path)
    return cast(
        UnresolvedRegistry,
        _wrap_parse(lambda: parser.parse_unresolved_registry(path), path),
    )


@implements_adr("ADR-L-0013", "ADR-L-0019")
def load_unresolved_registry_v2(parser: ADRParser, path: Path) -> UnresolvedRegistryV2:
    """Load and validate a model 2.0 unresolved registry."""
    return cast(
        UnresolvedRegistryV2,
        _wrap_parse(
            lambda: UnresolvedRegistryV2.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013", "ADR-L-0023")
def load_unresolved_registry_v21(parser: ADRParser, path: Path) -> UnresolvedRegistryV21:
    """Load and validate a model 2.1 unresolved registry."""
    return cast(
        UnresolvedRegistryV21,
        _wrap_parse(
            lambda: UnresolvedRegistryV21.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013", "ADR-L-0025")
def load_normalized_entity_registry_v22(parser: ADRParser, path: Path) -> NormalizedEntityRegistryV22:
    """Load and validate a model 2.2 normalized entity registry."""
    return cast(
        NormalizedEntityRegistryV22,
        _wrap_parse(
            lambda: NormalizedEntityRegistryV22.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013", "ADR-L-0025")
def load_relationship_registry_v22(parser: ADRParser, path: Path) -> RelationshipRegistryV22:
    """Load and validate a model 2.2 relationship registry."""
    return cast(
        RelationshipRegistryV22,
        _wrap_parse(
            lambda: RelationshipRegistryV22.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013", "ADR-L-0025")
def load_unresolved_registry_v22(parser: ADRParser, path: Path) -> UnresolvedRegistryV22:
    """Load and validate a model 2.2 unresolved registry."""
    return cast(
        UnresolvedRegistryV22,
        _wrap_parse(
            lambda: UnresolvedRegistryV22.model_validate(parser.parse_yaml(path)),
            path,
        ),
    )


@implements_adr("ADR-L-0013")
def load_remediation_ledger(parser: ADRParser, path: Path) -> RemediationLedger:
    """Load and validate remediation ledger."""
    return cast(RemediationLedger, _wrap_parse(lambda: parser.parse_remediation_ledger(path), path))


@implements_adr("ADR-L-0013")
def load_legacy_entity_registry(parser: ADRParser, path: Path) -> EntityRegistry:
    """Load and validate a legacy entity registry."""
    return cast(EntityRegistry, _wrap_parse(lambda: parser.parse_entity_registry(path), path))


@implements_adr("ADR-L-0013")
def fingerprint_payload(payload: dict[str, Any]) -> str:
    """Return a deterministic hash for a loaded repository payload."""
    serialized = json.dumps(
        _canonicalize_payload(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


@implements_adr("ADR-L-0013")
def model_payload(model: Any) -> Any:
    """Return a deterministic JSON-serializable model payload."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json", exclude_none=True)
    return model


def _wrap_parse(loader: Any, path: Path) -> Any:
    try:
        return loader()
    except (ADRParseError, ADRSchemaValidationError, ValueError) as exc:
        raise ValueError(f"Failed to load registry: {path}: {exc}") from exc


def _canonicalize_payload(value: Any, *, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            key: _canonicalize_payload(item, parent_key=key) for key, item in sorted(value.items())
        }

    if isinstance(value, list):
        canonical_items = [_canonicalize_payload(item, parent_key=parent_key) for item in value]
        sort_key = _list_sort_key(parent_key, canonical_items)
        if sort_key is None:
            return canonical_items
        return sorted(canonical_items, key=sort_key)

    return value


def _list_sort_key(parent_key: str | None, items: list[Any]):
    if not items:
        return None

    if all(not isinstance(item, (dict, list)) for item in items):
        return lambda item: json.dumps(
            item, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )

    if all(isinstance(item, dict) and "id" in item for item in items):
        return lambda item: str(item["id"])

    if all(isinstance(item, dict) and "relationship_id" in item for item in items):
        return lambda item: str(item["relationship_id"])

    if all(isinstance(item, dict) and "source_ref" in item for item in items):
        return lambda item: (
            str(item.get("source_ref", "")),
            str(item.get("mention_role", "")),
            str(item.get("artifact_path", "")),
            str(item.get("source_type", "")),
        )

    if parent_key in {
        "declared_in",
        "references",
        "related_to",
        "enforces",
        "enabled_by",
        "enables",
        "governs",
        "implemented_by",
        "embodied_in",
        "implements_logical",
        "supersedes",
        "superseded_by",
        "refines",
        "domains",
        "tags",
    }:
        return lambda item: json.dumps(
            item, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )

    return None
