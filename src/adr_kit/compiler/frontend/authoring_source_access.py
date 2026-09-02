"""Authoring source access for projection fields absent from typed v1.5 models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .adr_access import field_get

# Present in corpus YAML but not authorized on CapabilityV13 / v1.5 logical models.
CAPABILITY_SOURCE_ONLY_FIELDS: frozenset[str] = frozenset({"acceptance_criteria"})


def load_authoring_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return payload


def index_raw_capabilities(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    capabilities = raw.get("capabilities")
    if not isinstance(capabilities, list):
        return indexed
    for item in capabilities:
        if not isinstance(item, dict):
            continue
        for key in (item.get("id"), item.get("alias_id")):
            if isinstance(key, str) and key:
                indexed[key] = item
    return indexed


def match_raw_capability(
    capability: Any,
    *,
    raw_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for key in (field_get(capability, "id"), field_get(capability, "alias_id")):
        if isinstance(key, str) and key in raw_by_key:
            return raw_by_key[key]
    return None


def capability_field_from_source(
    capability: Any,
    field: str,
    *,
    raw_by_key: dict[str, dict[str, Any]],
) -> Any:
    """Read a capability field from the parsed model, else from authoring source."""
    value = field_get(capability, field)
    if value not in (None, "", [], ()):
        return value
    if field not in CAPABILITY_SOURCE_ONLY_FIELDS:
        return value
    raw = match_raw_capability(capability, raw_by_key=raw_by_key)
    if raw is None:
        return value
    return raw.get(field, value)


def capability_fields_dropped_by_parse(
    capability: Any,
    *,
    raw_by_key: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    """Return source-only capability fields present in YAML but absent from parsed model."""
    raw = match_raw_capability(capability, raw_by_key=raw_by_key)
    if raw is None:
        return ()
    dropped: list[str] = []
    for field in sorted(CAPABILITY_SOURCE_ONLY_FIELDS):
        if field not in raw or raw[field] in (None, "", []):
            continue
        parsed = field_get(capability, field)
        if parsed in (None, "", [], ()):
            dropped.append(field)
    return tuple(dropped)
