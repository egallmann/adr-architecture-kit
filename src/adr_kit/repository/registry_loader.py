"""Loader helpers for architecture repository registries."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..models import (
    ArchitectureIndex,
    EntityRegistry,
    NormalizedEntityRegistry,
    RemediationLedger,
    RelationshipRegistry,
    UnresolvedRegistry,
)
from ..parser import ADRParseError, ADRParser, ADRSchemaValidationError


def load_architecture_index(parser: ADRParser, path: Path) -> ArchitectureIndex:
    """Load and validate an architecture index."""
    return _wrap_parse(lambda: parser.parse_architecture_index(path), path)


def load_normalized_entity_registry(parser: ADRParser, path: Path) -> NormalizedEntityRegistry:
    """Load and validate a normalized entity registry."""
    return _wrap_parse(lambda: parser.parse_normalized_entity_registry(path), path)


def load_relationship_registry(parser: ADRParser, path: Path) -> RelationshipRegistry:
    """Load and validate a relationship registry."""
    return _wrap_parse(lambda: parser.parse_relationship_registry(path), path)


def load_unresolved_registry(parser: ADRParser, path: Path) -> UnresolvedRegistry:
    """Load and validate an unresolved registry."""
    return _wrap_parse(lambda: parser.parse_unresolved_registry(path), path)


def load_remediation_ledger(parser: ADRParser, path: Path) -> RemediationLedger:
    """Load and validate remediation ledger."""
    return _wrap_parse(lambda: parser.parse_remediation_ledger(path), path)


def load_legacy_entity_registry(parser: ADRParser, path: Path) -> EntityRegistry:
    """Load and validate a legacy entity registry."""
    return _wrap_parse(lambda: parser.parse_entity_registry(path), path)


def fingerprint_payload(payload: dict[str, Any]) -> str:
    """Return a deterministic hash for a loaded repository payload."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(serialized.encode("utf-8")).hexdigest()


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
