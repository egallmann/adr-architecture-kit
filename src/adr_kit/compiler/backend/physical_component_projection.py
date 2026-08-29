"""Disposable ADR-PC human-projection view model.

Not a public SDK contract. Field X exists -> view field Y -> template section Z.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from ...decorators import implements_adr
from ...identity import UUIDV7_PATTERN
from ..frontend.adr_access import field_get, presentation_id
from ..ir.rel_graph import IRRelationship
from .neighbor_paths import SEMANTIC_ARCHITECTURE

_UUID_RE = UUIDV7_PATTERN
_GENERIC_UUID_RE = __import__("re").compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

PREFERRED_IMPLEMENTATION_IDENTIFIER_KEYS: tuple[str, ...] = (
    "module_path",
    "service_name",
    "entry_point",
    "test_path",
)
IMPLEMENTATION_IDENTIFIER_ROLES: dict[str, str] = {
    "module_path": "Primary implementation",
    "service_name": "Service",
    "entry_point": "Entry point",
    "test_path": "Primary tests",
}
SPECIALIZED_DIRECTION_LABELS: dict[tuple[str, str], str] = {
    ("depends_on", "outgoing"): "Depends on",
    ("depends_on", "incoming"): "Depended on by",
    ("implements_logical", "outgoing"): "Implements logical authority",
    ("implements_logical", "incoming"): "Logical authority implemented by",
    ("implements_system", "outgoing"): "Implements system",
    ("implements_system", "incoming"): "System implemented by",
    ("provides_interface", "outgoing"): "Provides interface",
    ("provides_interface", "incoming"): "Interface provided by",
    ("consumes_interface", "outgoing"): "Consumes interface",
    ("consumes_interface", "incoming"): "Interface consumed by",
    ("composed_of", "outgoing"): "Composed of",
    ("composed_of", "incoming"): "Contained in",
    ("implemented_by", "outgoing"): "Implemented by",
    ("implemented_by", "incoming"): "Implements",
}
_PREFERRED_GROUP_ORDER: tuple[str, ...] = (
    "Depends on",
    "Depended on by",
    "Provides interface",
    "Consumes interface",
    "Implements logical authority",
    "Logical authority implemented by",
    "Implements system",
    "System implemented by",
    "Contained in",
    "Composed of",
    "Implemented by",
    "Implements",
)
_GAP_FIELD_ORDER: tuple[str, ...] = (
    "id",
    "alias_id",
    "question",
    "context",
    "impact",
    "blocking",
    "affects",
    "options",
    "decision_required_from",
    "status",
    "evidence",
    "epistemic_state",
)
ARCHITECTURE_POSITION_NOTE = (
    "Physical-component ADRs author component, interface, and implementation "
    "entities. Topology is not authored here; neighborhood uses compiled semantic "
    "architecture edges plus structural bridges."
)


def looks_like_uuid(value: str | None) -> bool:
    """True when a string is a UUID (v7 or generic RFC 4122)."""
    if not isinstance(value, str) or not value:
        return False
    return bool(_UUID_RE.match(value) or _GENERIC_UUID_RE.match(value))


def preserve_markdown(text: str | None) -> str:
    """Normalize newlines without collapsing authored Markdown structure."""
    if text is None:
        return ""
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip()


def humanize_key(key: str) -> str:
    """Deterministic human label for an authored mapping key."""
    label = key.replace("_", " ").strip()
    if not label:
        return key
    return label[:1].upper() + label[1:]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _nonempty_text(value: Any) -> str | None:
    text = preserve_markdown(_text(value)) if value is not None else ""
    return text if text else None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        item = preserve_markdown(value)
        return [item] if item else []
    items: list[str] = []
    for entry in value:
        text = preserve_markdown(_text(entry))
        if text:
            items.append(text)
    return items


def _as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    extras = getattr(value, "__pydantic_extra__", None)
    dumped: dict[str, Any] = {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python", exclude_none=True)
    elif extras and isinstance(extras, dict):
        dumped = dict(extras)
    else:
        for key in getattr(value, "model_fields", {}):
            dumped[key] = getattr(value, key, None)
    return {key: item for key, item in dumped.items() if item is not None}


def _as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    return [value]


@dataclass(frozen=True)
class LabeledValue:
    label: str
    value: str


@dataclass(frozen=True)
class RelationshipItemView:
    label: str
    canonical_path: str
    target_display: str


@dataclass(frozen=True)
class RelationshipGroupView:
    heading: str
    items: tuple[RelationshipItemView, ...]


@dataclass(frozen=True)
class ArchitecturePositionView:
    note: str
    containing_systems: tuple[str, ...]
    logical_authority: tuple[str, ...]
    owned_components: tuple[str, ...]
    component_types: tuple[str, ...]
    purposes: tuple[str, ...]
    outgoing_dependencies: tuple[str, ...]
    incoming_dependents: tuple[str, ...]
    provided_interface_types: tuple[str, ...]
    implementation_locations: tuple[str, ...]
    relationship_groups: tuple[RelationshipGroupView, ...]


@dataclass(frozen=True)
class InterfaceView:
    alias_id: str
    heading: str
    interface_type: str
    specification: str
    contract_reference: str | None
    contract_tests: str | None


@dataclass(frozen=True)
class AlternativeRow:
    name: str
    rejected_because: str


@dataclass(frozen=True)
class ImplementationDecisionView:
    alias_id: str
    heading: str
    summary: str
    rationale: str
    alternatives: tuple[AlternativeRow, ...]
    consequences: tuple[str, ...]


@dataclass(frozen=True)
class MetricView:
    name: str
    metric_type: str
    description: str | None


@dataclass(frozen=True)
class LoggingView:
    level: str | None
    structured: str | None


@dataclass(frozen=True)
class EngineeringContractView:
    failure_semantics: str | None
    logging: LoggingView | None
    metrics: tuple[MetricView, ...]
    unit_test_coverage: str | None
    nested_integration_tests: str | None
    component_testing_requirements: tuple[str, ...]
    dependencies: tuple[str, ...]
    upstream_services: tuple[str, ...]
    downstream_services: tuple[str, ...]
    algorithms: tuple[LabeledValue, ...]
    extra_requirement_rows: tuple[LabeledValue, ...]


@dataclass(frozen=True)
class ImplementationLocationRow:
    role: str
    location: str


@dataclass(frozen=True)
class MigrationRow:
    entity_type: str
    historical_alias: str
    current_alias: str
    source: str


@dataclass(frozen=True)
class GapView:
    heading: str
    fields: tuple[LabeledValue, ...]
    body: str | None


@dataclass(frozen=True)
class ChangeSafetyView:
    component_alias: str | None
    must_preserve: tuple[str, ...]
    public_interfaces: tuple[str, ...]
    depends_on: tuple[str, ...]
    depended_on_by: tuple[str, ...]
    verify_with: tuple[str, ...]
    known_gaps: tuple[str, ...]


@dataclass(frozen=True)
class TechnologyChoiceView:
    name: str
    category: str
    version: str
    rationale: str


@dataclass(frozen=True)
class ComponentContractView:
    alias_id: str
    name: str
    component_type: str
    description: str | None
    purpose: str | None
    responsibilities: str | None
    key_responsibilities: tuple[str, ...]
    constraints: tuple[str, ...]
    success_criteria: tuple[str, ...]
    implements_capabilities: tuple[str, ...]
    interfaces: tuple[InterfaceView, ...]
    engineering: EngineeringContractView | None
    implementation_locations: tuple[ImplementationLocationRow, ...]
    change_safety: ChangeSafetyView


@dataclass
class PhysicalComponentProjection:
    """Type-specific disposable presentation model for one ADR-PC."""

    identity_rows: tuple[LabeledValue, ...]
    architecture_position: ArchitecturePositionView
    component_contracts: tuple[ComponentContractView, ...]
    change_safety_blocks: tuple[ChangeSafetyView, ...]
    interfaces: tuple[InterfaceView, ...]
    implementation_decisions: tuple[ImplementationDecisionView, ...]
    engineering_contracts: tuple[tuple[str, EngineeringContractView], ...]
    implementation_locations: tuple[tuple[str, tuple[ImplementationLocationRow, ...]], ...]
    migration_rows: tuple[MigrationRow, ...]
    technology_stack: tuple[TechnologyChoiceView, ...]
    notes: str | None
    architecture_impact_rows: tuple[LabeledValue, ...]
    gaps: tuple[GapView, ...]
    related_adrs: tuple[str, ...] = field(default_factory=tuple)


def direction_label(verb: str, direction: str) -> str:
    """Human phrase for a subject-relative semantic edge."""
    specialized = SPECIALIZED_DIRECTION_LABELS.get((verb, direction))
    if specialized:
        return specialized
    if direction == "outgoing":
        return f"Outgoing {verb}"
    if direction == "incoming":
        return f"Incoming {verb}"
    return verb


def _join_unique(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _entity_alias(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    model = adr_models_by_id.get(entity_id)
    if model is not None:
        alias = field_get(model, "alias_id")
        if isinstance(alias, str) and alias:
            return alias
    entity = entities.get(entity_id) if hasattr(entities, "get") else None
    if entity is not None:
        return presentation_id(entity)
    return entity_id


def _entity_secondary(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str | None:
    model = adr_models_by_id.get(entity_id)
    if model is not None:
        title = field_get(model, "title")
        if isinstance(title, str) and title.strip() and not looks_like_uuid(title):
            return title.strip()
    entity = entities.get(entity_id) if hasattr(entities, "get") else None
    if entity is None:
        return None
    metadata = entity.metadata if isinstance(getattr(entity, "metadata", None), dict) else {}
    if getattr(entity, "entity_type", None) == "interface":
        interface_type = metadata.get("interface_type")
        if isinstance(interface_type, str) and interface_type.strip():
            return interface_type.strip()
    name = getattr(entity, "name", None)
    if isinstance(name, str) and name.strip() and not looks_like_uuid(name):
        alias = presentation_id(entity)
        if name.strip() != alias:
            return name.strip()
    return None


def human_node_label(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    """Alias plus name/title (or interface type) for Mermaid display labels."""
    alias = _entity_alias(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
    if looks_like_uuid(alias):
        secondary = _entity_secondary(
            entity_id, entities=entities, adr_models_by_id=adr_models_by_id
        )
        return secondary or alias
    secondary = _entity_secondary(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
    if secondary and secondary != alias:
        return f"{alias}<br/>{secondary}"
    return alias


def human_endpoint_heading(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    """`Name (ALIAS)` heading; never prefers UUID when an alias exists."""
    alias = _entity_alias(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
    secondary = _entity_secondary(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
    if looks_like_uuid(alias) and secondary:
        return secondary
    if secondary and secondary != alias:
        return f"{secondary} ({alias})"
    return alias


def human_inventory_name(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    """Secondary display name for internal-structure inventory rows."""
    secondary = _entity_secondary(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
    if secondary:
        return secondary
    alias = _entity_alias(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
    if not looks_like_uuid(alias):
        return alias
    return ""


def _format_ref(
    ref_id: str,
    *,
    resolve_present_ref: Callable[[str], Any],
    format_present_ref: Callable[[Any], str],
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    ref = resolve_present_ref(ref_id)
    formatted = format_present_ref(ref)
    heading = human_endpoint_heading(
        ref_id, entities=entities, adr_models_by_id=adr_models_by_id
    )
    if looks_like_uuid(formatted) and heading and not looks_like_uuid(heading):
        return heading
    if ref.link and not getattr(ref, "unresolved", False):
        return formatted
    if heading and heading != formatted and not looks_like_uuid(heading):
        return heading
    return formatted


def _identity_rows(
    adr: Any,
    *,
    adr_type: str,
    status: str,
    alias_id: str,
    format_ref: Callable[[str], str],
) -> tuple[LabeledValue, ...]:
    rows: list[LabeledValue] = [
        LabeledValue("Type", adr_type),
        LabeledValue("Status", status),
        LabeledValue("Alias", alias_id),
    ]
    schema_version = _nonempty_text(field_get(adr, "schema_version"))
    if schema_version:
        rows.append(LabeledValue("Authoring contract", f"authoring v{schema_version}"))
    created = _nonempty_text(field_get(adr, "created_date"))
    if created:
        rows.append(LabeledValue("Created", created))
    modified = _nonempty_text(field_get(adr, "modified_date"))
    if modified:
        rows.append(LabeledValue("Modified", modified))
    authors = _string_list(field_get(adr, "authors"))
    if authors:
        rows.append(LabeledValue("Authors", ", ".join(authors)))
    domains = _string_list(field_get(adr, "domains"))
    if domains:
        rows.append(LabeledValue("Domains", ", ".join(domains)))
    tags = _string_list(field_get(adr, "tags"))
    if tags:
        rows.append(LabeledValue("Tags", ", ".join(tags)))
    logical_refs = [
        format_ref(item) for item in field_get(adr, "implements_logical") or [] if isinstance(item, str)
    ]
    if logical_refs:
        rows.append(LabeledValue("Implements Logical", ", ".join(logical_refs)))
    system_refs = [
        format_ref(item) for item in field_get(adr, "implements_system") or [] if isinstance(item, str)
    ]
    if system_refs:
        rows.append(LabeledValue("Implements System", ", ".join(system_refs)))
    return tuple(rows)


def _interface_view(interface: Any) -> InterfaceView | None:
    alias_id = _nonempty_text(field_get(interface, "alias_id")) or ""
    interface_type = _nonempty_text(field_get(interface, "type")) or ""
    if not alias_id and looks_like_uuid(_text(field_get(interface, "id"))):
        alias_id = interface_type or "interface"
    if not alias_id:
        alias_id = _text(field_get(interface, "id") or "interface")
    if interface_type:
        heading = f"{alias_id} — {interface_type}"
    else:
        heading = alias_id
    specification = preserve_markdown(field_get(interface, "specification") or "")
    return InterfaceView(
        alias_id=alias_id,
        heading=heading,
        interface_type=interface_type,
        specification=specification,
        contract_reference=_nonempty_text(field_get(interface, "contract_reference")),
        contract_tests=_nonempty_text(field_get(interface, "contract_tests")),
    )


def _implementation_locations(identifiers: Any) -> tuple[ImplementationLocationRow, ...]:
    mapping = _as_mapping(identifiers)
    if not mapping:
        return ()
    rows: list[ImplementationLocationRow] = []
    seen: set[str] = set()
    for key in PREFERRED_IMPLEMENTATION_IDENTIFIER_KEYS:
        if key not in mapping:
            continue
        value = _nonempty_text(mapping.get(key))
        if not value or looks_like_uuid(value):
            continue
        rows.append(
            ImplementationLocationRow(
                role=IMPLEMENTATION_IDENTIFIER_ROLES[key],
                location=value,
            )
        )
        seen.add(key)
    extra_keys = sorted(
        key
        for key, value in mapping.items()
        if key not in seen and _nonempty_text(value) and not looks_like_uuid(str(value))
        and not isinstance(value, (dict, list))
    )
    for key in extra_keys:
        value = _nonempty_text(mapping.get(key))
        if not value:
            continue
        rows.append(ImplementationLocationRow(role=humanize_key(key), location=value))
    return tuple(rows)


def _format_nested_value(value: Any) -> str | None:
    if value is None or value == "" or value == [] or value == {}:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return preserve_markdown(value) or None
    if isinstance(value, list):
        parts = [item for item in (_format_nested_value(entry) for entry in value) if item]
        return "; ".join(parts) if parts else None
    if isinstance(value, dict):
        parts = []
        for key in sorted(value):
            formatted = _format_nested_value(value[key])
            if formatted:
                parts.append(f"{humanize_key(str(key))}: {formatted}")
        return "; ".join(parts) if parts else None
    mapping = _as_mapping(value)
    if mapping:
        return _format_nested_value(mapping)
    text = preserve_markdown(_text(value))
    return text or None


def _engineering_contract(component: Any) -> EngineeringContractView | None:
    requirements = field_get(component, "implementation_requirements")
    req_map = _as_mapping(requirements)
    error_handling = _as_mapping(field_get(requirements, "error_handling") if requirements else None)
    if not error_handling and "error_handling" in req_map:
        error_handling = _as_mapping(req_map.get("error_handling"))
    failure = _nonempty_text(error_handling.get("strategy")) if error_handling else None

    observability = _as_mapping(field_get(requirements, "observability") if requirements else None)
    if not observability:
        observability = _as_mapping(req_map.get("observability"))
    logging_map = _as_mapping(observability.get("logging")) if observability else {}
    logging_view = None
    if logging_map:
        level = _nonempty_text(logging_map.get("level"))
        structured_raw = logging_map.get("structured")
        structured = None
        if structured_raw is not None and structured_raw != "":
            if isinstance(structured_raw, bool):
                structured = "true" if structured_raw else "false"
            else:
                structured = _nonempty_text(structured_raw)
        extra_logging = [
            LabeledValue(humanize_key(str(key)), formatted)
            for key, value in logging_map.items()
            if key not in {"level", "structured"}
            for formatted in [_format_nested_value(value)]
            if formatted
        ]
        if extra_logging:
            extra_text = "; ".join(f"{row.label}: {row.value}" for row in extra_logging)
            structured = f"{structured}; {extra_text}" if structured else extra_text
        if level or structured:
            logging_view = LoggingView(level=level, structured=structured)

    metrics: list[MetricView] = []
    for metric in _as_items(observability.get("metrics") if observability else None):
        metric_map = _as_mapping(metric) if not isinstance(metric, str) else {}
        name = _nonempty_text(metric_map.get("name") if metric_map else metric)
        metric_type = _nonempty_text(metric_map.get("type")) if metric_map else None
        if not name:
            continue
        metrics.append(
            MetricView(
                name=name,
                metric_type=metric_type or "",
                description=_nonempty_text(metric_map.get("description")) if metric_map else None,
            )
        )

    nested_testing = _as_mapping(
        field_get(requirements, "testing_requirements") if requirements else None
    )
    if not nested_testing:
        nested_testing = _as_mapping(req_map.get("testing_requirements"))
    unit_coverage = _nonempty_text(nested_testing.get("unit_test_coverage")) if nested_testing else None
    nested_integration = (
        _nonempty_text(nested_testing.get("integration_tests")) if nested_testing else None
    )
    extra_nested_testing = []
    if nested_testing:
        for key, value in nested_testing.items():
            if key in {"unit_test_coverage", "integration_tests"}:
                continue
            formatted = _format_nested_value(value)
            if formatted:
                extra_nested_testing.append(LabeledValue(humanize_key(str(key)), formatted))

    component_testing = tuple(_string_list(field_get(component, "testing_requirements")))
    dependencies = tuple(_string_list(field_get(component, "dependencies")))
    upstream = tuple(_string_list(field_get(component, "upstream_services")))
    downstream = tuple(_string_list(field_get(component, "downstream_services")))

    algorithms: list[LabeledValue] = []
    for algorithm in _as_items(req_map.get("algorithms")):
        algo_map = _as_mapping(algorithm)
        name = _nonempty_text(algo_map.get("name")) or "Algorithm"
        parts = []
        spec = _nonempty_text(algo_map.get("specification"))
        if spec:
            parts.append(spec)
        rationale = _nonempty_text(algo_map.get("rationale"))
        if rationale:
            parts.append(f"Rationale: {rationale}")
        complexity = _nonempty_text(algo_map.get("complexity"))
        if complexity:
            parts.append(f"Complexity: {complexity}")
        edges = _string_list(algo_map.get("edge_cases"))
        if edges:
            parts.append("Edge cases: " + "; ".join(edges))
        if parts:
            algorithms.append(LabeledValue(name, "\n".join(parts)))

    reserved = {
        "error_handling",
        "observability",
        "testing_requirements",
        "algorithms",
    }
    extra_rows: list[LabeledValue] = list(extra_nested_testing)
    for key, value in req_map.items():
        if key in reserved:
            continue
        formatted = _format_nested_value(value)
        if formatted:
            extra_rows.append(LabeledValue(humanize_key(str(key)), formatted))

    if not any(
        [
            failure,
            logging_view,
            metrics,
            unit_coverage,
            nested_integration,
            component_testing,
            dependencies,
            upstream,
            downstream,
            algorithms,
            extra_rows,
        ]
    ):
        return None
    return EngineeringContractView(
        failure_semantics=failure,
        logging=logging_view,
        metrics=tuple(metrics),
        unit_test_coverage=unit_coverage,
        nested_integration_tests=nested_integration,
        component_testing_requirements=component_testing,
        dependencies=dependencies,
        upstream_services=upstream,
        downstream_services=downstream,
        algorithms=tuple(algorithms),
        extra_requirement_rows=tuple(extra_rows),
    )


def _decision_view(decision: Any) -> ImplementationDecisionView | None:
    alias_id = _nonempty_text(field_get(decision, "alias_id")) or _text(
        field_get(decision, "id") or "decision"
    )
    if looks_like_uuid(alias_id):
        alias_id = _nonempty_text(field_get(decision, "alias_name")) or alias_id
    summary = preserve_markdown(field_get(decision, "summary") or "")
    if not summary and not alias_id:
        return None
    heading = alias_id
    if summary:
        heading = f"{alias_id} — {summary}" if alias_id else summary
    alternatives: list[AlternativeRow] = []
    for alt in _as_items(field_get(decision, "alternatives_considered")):
        alt_map = _as_mapping(alt) if not isinstance(alt, str) else {}
        name = _nonempty_text(alt_map.get("name") if alt_map else alt)
        rejected = _nonempty_text(alt_map.get("rejected_because")) if alt_map else None
        if name or rejected:
            alternatives.append(
                AlternativeRow(name=name or "", rejected_because=rejected or "")
            )
    consequences: list[str] = []
    raw_consequences = field_get(decision, "consequences")
    if isinstance(raw_consequences, list):
        consequences.extend(_string_list(raw_consequences))
    else:
        cons_map = _as_mapping(raw_consequences)
        for key in ("positive", "negative"):
            for item in _string_list(cons_map.get(key)):
                consequences.append(f"{humanize_key(key)}: {item}")
        for key, value in cons_map.items():
            if key in {"positive", "negative"}:
                continue
            formatted = _format_nested_value(value)
            if formatted:
                consequences.append(f"{humanize_key(str(key))}: {formatted}")
    return ImplementationDecisionView(
        alias_id=alias_id,
        heading=heading,
        summary=summary,
        rationale=preserve_markdown(field_get(decision, "rationale") or ""),
        alternatives=tuple(alternatives),
        consequences=tuple(consequences),
    )


def _migration_rows(adr: Any) -> tuple[MigrationRow, ...]:
    origin = field_get(adr, "migration_origin")
    remapped = field_get(origin, "remapped_entities") if origin is not None else None
    if remapped is None and isinstance(origin, dict):
        remapped = origin.get("remapped_entities")
    rows: list[MigrationRow] = []
    for item in _as_items(remapped):
        mapping = _as_mapping(item)
        entity_type = _nonempty_text(mapping.get("entity_type")) or ""
        historical = _nonempty_text(mapping.get("from")) or ""
        current = _nonempty_text(mapping.get("to")) or ""
        source = _nonempty_text(mapping.get("source_pointer")) or ""
        if not any([entity_type, historical, current, source]):
            continue
        rows.append(
            MigrationRow(
                entity_type=entity_type,
                historical_alias=historical,
                current_alias=current,
                source=source,
            )
        )
    return tuple(rows)


def _gap_view(gap: Any, index: int) -> GapView:
    if isinstance(gap, str):
        text = preserve_markdown(gap)
        return GapView(heading=f"Gap {index}", fields=(), body=text or None)
    mapping = _as_mapping(gap)
    alias = _nonempty_text(mapping.get("alias_id")) or _nonempty_text(mapping.get("id"))
    if alias and looks_like_uuid(alias):
        alias = None
    question = _nonempty_text(mapping.get("question"))
    heading = alias or question or f"Gap {index}"
    if alias and question:
        heading = f"{alias}: {question}"
    fields: list[LabeledValue] = []
    seen = {"id", "alias_id", "question"}
    for key in _GAP_FIELD_ORDER:
        if key in seen or key not in mapping:
            continue
        formatted = _format_nested_value(mapping.get(key))
        if formatted:
            fields.append(LabeledValue(humanize_key(str(key)), formatted))
            seen.add(key)
    for key in sorted(mapping):
        if key in seen:
            continue
        formatted = _format_nested_value(mapping.get(key))
        if formatted:
            fields.append(LabeledValue(humanize_key(str(key)), formatted))
    return GapView(heading=heading, fields=tuple(fields), body=None)


def _technology_stack(adr: Any) -> tuple[TechnologyChoiceView, ...]:
    rows: list[TechnologyChoiceView] = []
    for tech in _as_items(field_get(adr, "technology_stack")):
        mapping = _as_mapping(tech)
        name = _nonempty_text(mapping.get("name")) or ""
        if not name:
            continue
        rows.append(
            TechnologyChoiceView(
                name=name,
                category=_nonempty_text(mapping.get("category")) or "",
                version=_nonempty_text(mapping.get("version")) or "",
                rationale=preserve_markdown(mapping.get("rationale") or ""),
            )
        )
    return tuple(rows)


def _ego_ids(subject_id: str, adr: Any) -> set[str]:
    ego = {subject_id}
    for component in _as_items(field_get(adr, "component_specifications")):
        for key in ("id", "component_id"):
            value = field_get(component, key)
            if isinstance(value, str) and value:
                ego.add(value)
        for interface in _as_items(field_get(component, "interfaces")):
            value = field_get(interface, "id")
            if isinstance(value, str) and value:
                ego.add(value)
    for decision in _as_items(field_get(adr, "implementation_decisions")):
        value = field_get(decision, "id")
        if isinstance(value, str) and value:
            ego.add(value)
    return ego


def _subject_relationships(
    *,
    ego: set[str],
    relationships: Iterable[IRRelationship],
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> tuple[dict[str, list[str]], dict[str, list[RelationshipItemView]]]:
    grouped: dict[str, list[RelationshipItemView]] = defaultdict(list)
    grouped_keys: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    outgoing_depends: list[str] = []
    incoming_depends: list[str] = []
    for rel in relationships:
        verb = rel.relationship_type
        if verb not in SEMANTIC_ARCHITECTURE:
            continue
        from_in = rel.from_entity_id in ego
        to_in = rel.to_entity_id in ego
        if from_in == to_in and not (from_in and to_in):
            continue
        if from_in and to_in:
            direction = "outgoing"
        elif from_in:
            direction = "outgoing"
        else:
            direction = "incoming"
        if not from_in and not to_in:
            continue
        heading = direction_label(verb, direction)
        from_alias = _entity_alias(
            rel.from_entity_id, entities=entities, adr_models_by_id=adr_models_by_id
        )
        to_alias = _entity_alias(
            rel.to_entity_id, entities=entities, adr_models_by_id=adr_models_by_id
        )
        from_heading = human_endpoint_heading(
            rel.from_entity_id, entities=entities, adr_models_by_id=adr_models_by_id
        )
        to_heading = human_endpoint_heading(
            rel.to_entity_id, entities=entities, adr_models_by_id=adr_models_by_id
        )
        canonical = f"{from_alias} -[:{verb}]-> {to_alias}"
        target = to_heading if direction == "outgoing" else from_heading
        key = (verb, rel.from_entity_id, rel.to_entity_id)
        if key in grouped_keys[heading]:
            continue
        grouped_keys[heading].add(key)
        item = RelationshipItemView(
            label=target,
            canonical_path=canonical,
            target_display=target,
        )
        grouped[heading].append(item)
        if verb == "depends_on" and direction == "outgoing":
            outgoing_depends.append(to_heading)
        elif verb == "depends_on" and direction == "incoming":
            incoming_depends.append(from_heading)
    return {"outgoing": outgoing_depends, "incoming": incoming_depends}, dict(grouped)


def _ordered_groups(
    grouped: dict[str, list[RelationshipItemView]],
) -> tuple[RelationshipGroupView, ...]:
    headings = [name for name in _PREFERRED_GROUP_ORDER if name in grouped]
    headings.extend(sorted(name for name in grouped if name not in _PREFERRED_GROUP_ORDER))
    groups: list[RelationshipGroupView] = []
    for heading in headings:
        items = tuple(
            sorted(grouped[heading], key=lambda item: (item.canonical_path, item.label))
        )
        if items:
            groups.append(RelationshipGroupView(heading=heading, items=items))
    return tuple(groups)


def _component_depends(
    *,
    component: Any,
    relationships: Iterable[IRRelationship],
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    component_ids = {
        value
        for key in ("id", "component_id")
        for value in [field_get(component, key)]
        if isinstance(value, str) and value
    }
    outgoing: list[str] = []
    incoming: list[str] = []
    for rel in relationships:
        if rel.relationship_type != "depends_on":
            continue
        if rel.from_entity_id in component_ids and rel.to_entity_id not in component_ids:
            outgoing.append(
                human_endpoint_heading(
                    rel.to_entity_id, entities=entities, adr_models_by_id=adr_models_by_id
                )
            )
        elif rel.to_entity_id in component_ids and rel.from_entity_id not in component_ids:
            incoming.append(
                human_endpoint_heading(
                    rel.from_entity_id, entities=entities, adr_models_by_id=adr_models_by_id
                )
            )
    return _join_unique(outgoing), _join_unique(incoming)


def _change_safety(
    *,
    component: Any,
    component_alias: str | None,
    interfaces: tuple[InterfaceView, ...],
    outgoing: tuple[str, ...],
    incoming: tuple[str, ...],
    gaps: tuple[GapView, ...],
) -> ChangeSafetyView:
    generation = _as_mapping(field_get(component, "generation_context"))
    constraints = tuple(_string_list(generation.get("constraints")))
    success = list(_string_list(generation.get("success_criteria")))
    locations = _implementation_locations(field_get(component, "implementation_identifiers"))
    for row in locations:
        if row.role == "Primary tests":
            success.append(row.location)
    engineering = _engineering_contract(component)
    if engineering:
        if engineering.unit_test_coverage:
            success.append(engineering.unit_test_coverage)
        if engineering.nested_integration_tests:
            success.append(engineering.nested_integration_tests)
        success.extend(engineering.component_testing_requirements)
    public_interfaces = tuple(
        f"{iface.alias_id} — {iface.interface_type}" if iface.interface_type else iface.alias_id
        for iface in interfaces
        if iface.alias_id
    )
    gap_headings = tuple(gap.heading for gap in gaps)
    return ChangeSafetyView(
        component_alias=component_alias,
        must_preserve=constraints,
        public_interfaces=public_interfaces,
        depends_on=outgoing,
        depended_on_by=incoming,
        verify_with=_join_unique(success),
        known_gaps=gap_headings,
    )


@implements_adr("ADR-L-0007")
def build_physical_component_projection(
    *,
    adr: Any,
    subject_id: str,
    alias_id: str,
    adr_type: str,
    status: str,
    entities: Any,
    relationships: Iterable[IRRelationship],
    adr_models_by_id: dict[str, Any],
    resolve_present_ref: Callable[[str], Any],
    format_present_ref: Callable[[Any], str],
) -> PhysicalComponentProjection:
    """Extract a disposable ADR-PC presentation model from authored + compiled state."""
    relationship_list = list(relationships)

    def format_ref(ref_id: str) -> str:
        return _format_ref(
            ref_id,
            resolve_present_ref=resolve_present_ref,
            format_present_ref=format_present_ref,
            entities=entities,
            adr_models_by_id=adr_models_by_id,
        )

    identity_rows = _identity_rows(
        adr,
        adr_type=adr_type,
        status=status,
        alias_id=alias_id,
        format_ref=format_ref,
    )
    ego = _ego_ids(subject_id, adr)
    depends, grouped = _subject_relationships(
        ego=ego,
        relationships=relationship_list,
        entities=entities,
        adr_models_by_id=adr_models_by_id,
    )
    relationship_groups = _ordered_groups(grouped)
    outgoing = _join_unique(depends.get("outgoing", []))
    incoming = _join_unique(depends.get("incoming", []))

    containing_systems = tuple(
        format_ref(item)
        for item in field_get(adr, "implements_system") or []
        if isinstance(item, str)
    )
    logical_authority = tuple(
        format_ref(item)
        for item in field_get(adr, "implements_logical") or []
        if isinstance(item, str)
    )

    gaps = tuple(
        _gap_view(gap, index)
        for index, gap in enumerate(_as_items(field_get(adr, "gaps")), start=1)
        if _as_mapping(gap) or (isinstance(gap, str) and gap.strip())
    )

    component_contracts: list[ComponentContractView] = []
    all_interfaces: list[InterfaceView] = []
    engineering_contracts: list[tuple[str, EngineeringContractView]] = []
    location_groups: list[tuple[str, tuple[ImplementationLocationRow, ...]]] = []
    owned_components: list[str] = []
    component_types: list[str] = []
    purposes: list[str] = []
    location_summaries: list[str] = []
    interface_types: list[str] = []

    for component in _as_items(field_get(adr, "component_specifications")):
        alias = _nonempty_text(field_get(component, "alias_id")) or _text(
            field_get(component, "id") or "component"
        )
        if looks_like_uuid(alias):
            alias = _nonempty_text(field_get(component, "name")) or alias
        name = _nonempty_text(field_get(component, "name")) or alias
        component_type = _nonempty_text(field_get(component, "type")) or ""
        owned_components.append(
            f"{alias} — {name} ({component_type})" if component_type else f"{alias} — {name}"
        )
        if component_type:
            component_types.append(component_type)
        generation = _as_mapping(field_get(component, "generation_context"))
        purpose = _nonempty_text(generation.get("purpose"))
        if purpose:
            purposes.append(purpose)
        interfaces = tuple(
            view
            for interface in _as_items(field_get(component, "interfaces"))
            for view in [_interface_view(interface)]
            if view is not None
        )
        all_interfaces.extend(interfaces)
        interface_types.extend(iface.interface_type for iface in interfaces if iface.interface_type)
        locations = _implementation_locations(field_get(component, "implementation_identifiers"))
        if locations:
            location_groups.append((alias, locations))
            location_summaries.extend(f"{row.role}: {row.location}" for row in locations)
        engineering = _engineering_contract(component)
        if engineering:
            engineering_contracts.append((alias, engineering))
        capability_refs = []
        for cap_id in field_get(component, "implements_capabilities") or []:
            if isinstance(cap_id, str) and cap_id:
                capability_refs.append(format_ref(cap_id))
        cap_outgoing, cap_incoming = _component_depends(
            component=component,
            relationships=relationship_list,
            entities=entities,
            adr_models_by_id=adr_models_by_id,
        )
        change_safety = _change_safety(
            component=component,
            component_alias=alias if len(_as_items(field_get(adr, "component_specifications"))) > 1 else None,
            interfaces=interfaces,
            outgoing=cap_outgoing,
            incoming=cap_incoming,
            gaps=gaps,
        )
        component_contracts.append(
            ComponentContractView(
                alias_id=alias,
                name=name,
                component_type=component_type,
                description=_nonempty_text(field_get(component, "description")),
                purpose=purpose,
                responsibilities=_nonempty_text(field_get(component, "responsibilities")),
                key_responsibilities=tuple(_string_list(generation.get("key_responsibilities"))),
                constraints=tuple(_string_list(generation.get("constraints"))),
                success_criteria=tuple(_string_list(generation.get("success_criteria"))),
                implements_capabilities=tuple(capability_refs),
                interfaces=interfaces,
                engineering=engineering,
                implementation_locations=locations,
                change_safety=change_safety,
            )
        )

    decisions = tuple(
        view
        for decision in _as_items(field_get(adr, "implementation_decisions"))
        for view in [_decision_view(decision)]
        if view is not None
    )

    impact_rows: list[LabeledValue] = []
    related = [
        format_ref(item) for item in field_get(adr, "related_adrs") or [] if isinstance(item, str)
    ]
    if related:
        impact_rows.append(LabeledValue("Related ADRs", ", ".join(related)))
    supersedes = [
        format_ref(item) for item in field_get(adr, "supersedes") or [] if isinstance(item, str)
    ]
    if supersedes:
        impact_rows.append(LabeledValue("Supersedes", ", ".join(supersedes)))
    superseded_by = field_get(adr, "superseded_by")
    if isinstance(superseded_by, str) and superseded_by:
        impact_rows.append(LabeledValue("Superseded by", format_ref(superseded_by)))

    contained = [
        item.target_display
        for group in relationship_groups
        if group.heading == "Contained in"
        for item in group.items
    ]

    position = ArchitecturePositionView(
        note=ARCHITECTURE_POSITION_NOTE,
        containing_systems=_join_unique([*containing_systems, *contained]),
        logical_authority=_join_unique(logical_authority),
        owned_components=_join_unique(owned_components),
        component_types=_join_unique(component_types),
        purposes=_join_unique(purposes),
        outgoing_dependencies=outgoing,
        incoming_dependents=incoming,
        provided_interface_types=_join_unique(interface_types),
        implementation_locations=_join_unique(location_summaries),
        relationship_groups=relationship_groups,
    )

    change_blocks = tuple(contract.change_safety for contract in component_contracts)
    notes = _nonempty_text(field_get(adr, "notes"))

    return PhysicalComponentProjection(
        identity_rows=identity_rows,
        architecture_position=position,
        component_contracts=tuple(component_contracts),
        change_safety_blocks=change_blocks,
        interfaces=tuple(all_interfaces),
        implementation_decisions=decisions,
        engineering_contracts=tuple(engineering_contracts),
        implementation_locations=tuple(location_groups),
        migration_rows=_migration_rows(adr),
        technology_stack=_technology_stack(adr),
        notes=notes,
        architecture_impact_rows=tuple(impact_rows),
        gaps=gaps,
        related_adrs=tuple(related),
    )
