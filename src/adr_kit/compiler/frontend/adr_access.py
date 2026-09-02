"""Duck-typed ADR field access for legacy and v1.3 compiler models."""

from __future__ import annotations

from typing import Any

from ...identity import UUIDV7_PATTERN
from ...models.common import ADRType


def field_get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from a Pydantic model, model extras, or plain dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, key):
        try:
            return getattr(obj, key)
        except AttributeError:
            pass
    extras = getattr(obj, "__pydantic_extra__", None)
    if isinstance(extras, dict) and key in extras:
        return extras[key]
    return default


def presentation_id(obj: Any) -> str:
    """Return the human-recognition id (alias_id) when present, else canonical id."""
    alias = field_get(obj, "alias_id")
    if isinstance(alias, str) and alias:
        return alias
    metadata = field_get(obj, "metadata")
    if isinstance(metadata, dict):
        meta_alias = metadata.get("alias_id")
        if isinstance(meta_alias, str) and meta_alias:
            return meta_alias
    value = field_get(obj, "id")
    if isinstance(value, str) and value:
        return value
    return str(obj)


def field_list(obj: Any, key: str) -> list[Any]:
    """Read a list field from a model or dict; return empty list when absent."""
    value = field_get(obj, key, None)
    if value is None:
        return []
    return list(value)


def adr_type_of(adr: Any) -> ADRType | None:
    """Return the ADRType for legacy or v1.3 ADR models."""
    value = getattr(adr, "adr_type", None)
    if value is None:
        return None
    if isinstance(value, ADRType):
        return value
    try:
        return ADRType(value)
    except ValueError:
        return None


def is_physical_system_adr(adr: Any) -> bool:
    return adr_type_of(adr) == ADRType.PHYSICAL_SYSTEM


def is_physical_component_adr(adr: Any) -> bool:
    return adr_type_of(adr) == ADRType.PHYSICAL_COMPONENT


def is_physical_adr(adr: Any) -> bool:
    return adr_type_of(adr) == ADRType.PHYSICAL


def is_logical_adr_source_ref(source_ref: str) -> bool:
    """True when source_ref is owned by a logical ADR (legacy alias or UUID)."""
    owner = source_ref.split("#", 1)[0]
    return owner.startswith("ADR-") or bool(UUIDV7_PATTERN.match(owner))


def topology_components(adr: Any) -> list[Any]:
    """Return topology component entries from typed or dict component_topology."""
    topo = getattr(adr, "component_topology", None)
    if topo is None:
        return []
    if isinstance(topo, dict):
        return list(topo.get("components") or [])
    return list(getattr(topo, "components", None) or [])


def topology_relationships(adr: Any) -> list[Any]:
    """Return topology relationship entries from typed or dict component_topology."""
    topo = getattr(adr, "component_topology", None)
    if topo is None:
        return []
    if isinstance(topo, dict):
        return list(topo.get("relationships") or [])
    return list(getattr(topo, "relationships", None) or [])


def topology_edge_fields(rel: Any) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Return (from, to, type, protocol, description) for a topology edge."""
    if isinstance(rel, dict):
        return (
            rel.get("from"),
            rel.get("to"),
            rel.get("type"),
            rel.get("protocol"),
            rel.get("description"),
        )
    return (
        getattr(rel, "from_", None) or getattr(rel, "from", None),
        getattr(rel, "to", None),
        getattr(rel, "type", None),
        getattr(rel, "protocol", None),
        getattr(rel, "description", None),
    )
