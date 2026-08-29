"""Fail-closed coverage registry for Projection v3 (authoring v1.5)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Literal

from ....decorators import implements_adr, enforces_invariant

Disposition = Literal[
    "RENDER_PRIMARY",
    "RENDER_DETAIL",
    "RENDER_AS_RELATIONSHIP",
    "RENDER_SUMMARY_AND_DETAIL",
    "PROJECTION_CONTROL_INPUT",
    "GOVERNANCE_METADATA",
    "INTENTIONALLY_NOT_RENDERED",
    "UNSUPPORTED_OR_STALE",
]

DISPOSITIONS: frozenset[str] = frozenset(
    {
        "RENDER_PRIMARY",
        "RENDER_DETAIL",
        "RENDER_AS_RELATIONSHIP",
        "RENDER_SUMMARY_AND_DETAIL",
        "PROJECTION_CONTROL_INPUT",
        "GOVERNANCE_METADATA",
        "INTENTIONALLY_NOT_RENDERED",
        "UNSUPPORTED_OR_STALE",
    }
)

REGISTRY_PATH = Path(__file__).resolve().parent / "authoring_v1_5.yaml"
SCHEMA_DIR = Path(__file__).resolve().parents[5] / "schema" / "authoring" / "v1.5"

_PREFIX_RULES: tuple[tuple[str, Disposition], ...] = (
    ("/schema_version", "GOVERNANCE_METADATA"),
    ("/id", "GOVERNANCE_METADATA"),
    ("/alias_id", "RENDER_PRIMARY"),
    ("/alias_name", "RENDER_PRIMARY"),
    ("/adr_type", "RENDER_PRIMARY"),
    ("/title", "RENDER_PRIMARY"),
    ("/status", "RENDER_PRIMARY"),
    ("/created_date", "GOVERNANCE_METADATA"),
    ("/modified_date", "GOVERNANCE_METADATA"),
    ("/authors", "GOVERNANCE_METADATA"),
    ("/domains", "RENDER_DETAIL"),
    ("/tags", "RENDER_DETAIL"),
    ("/context", "RENDER_PRIMARY"),
    ("/extension_entities", "RENDER_DETAIL"),
    ("/extension_relationships", "RENDER_AS_RELATIONSHIP"),
    ("/decisions", "RENDER_SUMMARY_AND_DETAIL"),
    ("/capabilities", "RENDER_SUMMARY_AND_DETAIL"),
    ("/invariants", "RENDER_SUMMARY_AND_DETAIL"),
    ("/constraints", "RENDER_DETAIL"),
    ("/non_functional_requirements", "RENDER_DETAIL"),
    ("/gaps", "RENDER_DETAIL"),
    ("/related_adrs", "RENDER_AS_RELATIONSHIP"),
    ("/supersedes", "RENDER_AS_RELATIONSHIP"),
    ("/superseded_by", "RENDER_AS_RELATIONSHIP"),
    ("/implements_logical", "RENDER_AS_RELATIONSHIP"),
    ("/implements_system", "RENDER_AS_RELATIONSHIP"),
    ("/technology_stack", "RENDER_DETAIL"),
    ("/technologies", "RENDER_DETAIL"),
    ("/system", "RENDER_PRIMARY"),
    ("/system_boundaries", "RENDER_DETAIL"),
    ("/component_topology", "PROJECTION_CONTROL_INPUT"),
    ("/component_specifications", "RENDER_SUMMARY_AND_DETAIL"),
    ("/substrate_bindings", "GOVERNANCE_METADATA"),
    ("/rule_bindings", "GOVERNANCE_METADATA"),
    ("/evidence_expectations", "GOVERNANCE_METADATA"),
    ("/introduces_entities", "INTENTIONALLY_NOT_RENDERED"),
    ("/modifies_entities", "INTENTIONALLY_NOT_RENDERED"),
    ("/realizes_entities", "INTENTIONALLY_NOT_RENDERED"),
    ("/references_components", "UNSUPPORTED_OR_STALE"),
    ("/ownership", "GOVERNANCE_METADATA"),
    ("/governance", "GOVERNANCE_METADATA"),
    ("/projection_signals", "INTENTIONALLY_NOT_RENDERED"),
    ("/ai_projectable", "INTENTIONALLY_NOT_RENDERED"),
    ("/vision_category", "GOVERNANCE_METADATA"),
    ("/promotable_to_logical", "GOVERNANCE_METADATA"),
    ("/architectural_boundaries", "RENDER_DETAIL"),
    ("/interaction_contracts", "RENDER_DETAIL"),
    ("/integration_patterns", "RENDER_DETAIL"),
    ("/data_flows", "RENDER_DETAIL"),
    ("/deployment_model", "RENDER_DETAIL"),
    ("/scalability_strategy", "RENDER_DETAIL"),
    ("/failure_modes", "RENDER_DETAIL"),
    ("/operational_requirements", "RENDER_DETAIL"),
    ("/conversation_metadata", "GOVERNANCE_METADATA"),
    ("/architecture_patterns", "RENDER_DETAIL"),
    ("/data_architecture", "RENDER_DETAIL"),
    ("/implementation_decisions", "RENDER_DETAIL"),
    ("/integration_points", "RENDER_DETAIL"),
    ("/exposed_interfaces", "RENDER_DETAIL"),
    ("/external_dependencies", "RENDER_DETAIL"),
    ("/notes", "RENDER_DETAIL"),
    ("/decision", "RENDER_SUMMARY_AND_DETAIL"),
    ("/migration_origin", "GOVERNANCE_METADATA"),
)


class CoverageRegistryError(ValueError):
    """Raised when a current-authoring field lacks a coverage disposition."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_properties(schema: dict[str, Any], directory: Path) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for item in schema.get("allOf") or []:
        if isinstance(item, dict) and "$ref" in item:
            ref = str(item["$ref"]).split("#", 1)[0]
            if ref:
                properties.update(_merge_properties(_load_json(directory / ref), directory))
        elif isinstance(item, dict):
            properties.update(_merge_properties(item, directory))
    properties.update(schema.get("properties") or {})
    return properties


def _walk_properties(properties: dict[str, Any], prefix: str) -> set[str]:
    pointers: set[str] = set()
    for name, spec in properties.items():
        pointer = f"{prefix}/{name}"
        pointers.add(pointer)
        if not isinstance(spec, dict):
            continue
        nested = spec.get("properties")
        if isinstance(nested, dict):
            pointers |= _walk_properties(nested, pointer)
        items = spec.get("items")
        if isinstance(items, dict) and isinstance(items.get("properties"), dict):
            pointers |= _walk_properties(items["properties"], pointer)
            for allof in items.get("allOf") or []:
                if isinstance(allof, dict) and isinstance(allof.get("properties"), dict):
                    pointers |= _walk_properties(allof["properties"], pointer)
        for allof in spec.get("allOf") or []:
            if isinstance(allof, dict) and isinstance(allof.get("properties"), dict):
                pointers |= _walk_properties(allof["properties"], pointer)
    return pointers


@implements_adr("ADR-L-0007")
def collect_schema_field_pointers(adr_type: str) -> set[str]:
    """Return JSON-pointer field paths for one authoring v1.5 ADR type."""
    filenames = {
        "logical": "adr-logical.schema.json",
        "physical-system": "adr-physical-system.schema.json",
        "physical-component": "adr-physical-component.schema.json",
    }
    filename = filenames[adr_type]
    schema = _load_json(SCHEMA_DIR / filename)
    properties = _merge_properties(schema, SCHEMA_DIR)
    return _walk_properties(properties, "")


def _default_disposition(pointer: str) -> Disposition:
    best: Disposition | None = None
    best_len = -1
    for prefix, disposition in _PREFIX_RULES:
        if pointer == prefix or pointer.startswith(prefix + "/"):
            if len(prefix) > best_len:
                best = disposition
                best_len = len(prefix)
    if best is None:
        if "bindings" in pointer or "evidence" in pointer:
            return "GOVERNANCE_METADATA"
        return "RENDER_DETAIL"
    return best


def _pydantic_field_pointers(model_cls: type) -> set[str]:
    from pydantic import BaseModel

    pointers: set[str] = set()
    for name, field in model_cls.model_fields.items():
        pointers.add(f"/{name}")
        annotation = field.annotation
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())
        candidates = [annotation, *args]
        if origin is not None:
            candidates.append(origin)
        for candidate in candidates:
            if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                for nested in candidate.model_fields:
                    pointers.add(f"/{name}/{nested}")
    return pointers


def built_in_registry() -> dict[str, dict[str, Disposition]]:
    """Return the complete v1.5 coverage map keyed by adr_type then pointer."""
    from ....models.v1_5.logical_adr import LogicalADRv15
    from ....models.v1_5.physical_adr import PhysicalComponentADRv15
    from ....models.v1_5.physical_system_adr import PhysicalSystemADRv15

    models = {
        "logical": LogicalADRv15,
        "physical-system": PhysicalSystemADRv15,
        "physical-component": PhysicalComponentADRv15,
    }
    registry: dict[str, dict[str, Disposition]] = {}
    for adr_type, model_cls in models.items():
        pointers = collect_schema_field_pointers(adr_type) | _pydantic_field_pointers(model_cls)
        for prefix, _disposition in _PREFIX_RULES:
            pointers.add(prefix)
        table = {
            pointer: _default_disposition(pointer) for pointer in sorted(pointers)
        }
        if adr_type == "physical-component":
            table["/component_topology"] = "UNSUPPORTED_OR_STALE"
        elif adr_type == "logical":
            table.pop("/component_topology", None)
        registry[adr_type] = table
    return registry


_REGISTRY = built_in_registry()


@implements_adr("ADR-L-0007")
@enforces_invariant("INV-0101")
def disposition_for(*, adr_type: str, pointer: str) -> Disposition:
    table = _REGISTRY.get(adr_type)
    if table is None or pointer not in table:
        raise CoverageRegistryError(
            f"No coverage disposition for {adr_type} field {pointer}; UNCLASSIFIED is not permitted"
        )
    return table[pointer]


def iter_model_pointers(payload: Any, prefix: str = "") -> Iterable[str]:
    if not isinstance(payload, dict):
        return
    for key, value in payload.items():
        pointer = f"{prefix}/{key}"
        yield pointer
        if isinstance(value, dict):
            yield from iter_model_pointers(value, pointer)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            yield from iter_model_pointers(value[0], pointer)


@implements_adr("ADR-L-0007")
def assert_current_authoring_coverage(adr: Any) -> None:
    """Fail closed when a parsed v1.5 field has no coverage disposition."""
    schema_version = str(getattr(adr, "schema_version", "") or "")
    if schema_version != "1.5":
        return
    adr_type = getattr(getattr(adr, "adr_type", None), "value", getattr(adr, "adr_type", None))
    adr_type_value = str(adr_type or "")
    if adr_type_value not in _REGISTRY:
        return
    payload = adr.model_dump(mode="python", exclude_none=True)
    for pointer in iter_model_pointers(payload):
        if pointer not in _REGISTRY[adr_type_value]:
            # Nested instance keys beyond schema property walk still need a parent
            # disposition; require the longest registered prefix.
            parent = pointer
            while parent and parent not in _REGISTRY[adr_type_value]:
                parent = parent.rsplit("/", 1)[0]
            if not parent:
                raise CoverageRegistryError(
                    f"Parsed field {pointer} on {adr_type_value} has no coverage disposition"
                )
        else:
            disposition_for(adr_type=adr_type_value, pointer=pointer)
