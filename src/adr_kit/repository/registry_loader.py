"""Loader helpers for architecture repository registries."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..decorators import implements_adr
from ..models import (
    ArchitectureIndex,
    EntityRegistry,
    NormalizedEntityRegistry,
    RemediationLedger,
    RelationshipRegistry,
    UnresolvedRegistry,
)
from ..parser import ADRParseError, ADRParser, ADRSchemaValidationError


@implements_adr("ADR-L-0013")
def load_architecture_index(parser: ADRParser, path: Path) -> ArchitectureIndex:
    """Load and validate an architecture index."""
    return _wrap_parse(lambda: parser.parse_architecture_index(path), path)


@implements_adr("ADR-L-0013")
def load_normalized_entity_registry(parser: ADRParser, path: Path) -> NormalizedEntityRegistry:
    """Load and validate a normalized entity registry."""
    return _wrap_parse(lambda: parser.parse_normalized_entity_registry(path), path)


@implements_adr("ADR-L-0013")
def load_relationship_registry(parser: ADRParser, path: Path) -> RelationshipRegistry:
    """Load and validate a relationship registry."""
    return _wrap_parse(lambda: parser.parse_relationship_registry(path), path)


@implements_adr("ADR-L-0013")
def load_unresolved_registry(parser: ADRParser, path: Path) -> UnresolvedRegistry:
    """Load and validate an unresolved registry."""
    return _wrap_parse(lambda: parser.parse_unresolved_registry(path), path)


@implements_adr("ADR-L-0013")
def load_remediation_ledger(parser: ADRParser, path: Path) -> RemediationLedger:
    """Load and validate remediation ledger."""
    return _wrap_parse(lambda: parser.parse_remediation_ledger(path), path)


@implements_adr("ADR-L-0013")
def load_legacy_entity_registry(parser: ADRParser, path: Path) -> EntityRegistry:
    """Load and validate a legacy entity registry."""
    return _wrap_parse(lambda: parser.parse_entity_registry(path), path)


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
            key: _canonicalize_payload(item, parent_key=key)
            for key, item in sorted(value.items())
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
        return lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

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
        "supersedes",
        "superseded_by",
        "refines",
        "domains",
        "tags",
    }:
        return lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    return None
