"""Disposable ADR-PS human-projection view model.

Not a public SDK contract. Field X exists -> view field Y -> template section Z.

Shares presentation utilities with ADR-PC enrichment. Semantic models stay
system-specific: this module answers system architecture, not component contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from ...decorators import implements_adr
from ..frontend.adr_access import field_get, topology_components, topology_edge_fields, topology_relationships
from ..ir.rel_graph import IRRelationship
from .human_adr_projection import escape_mermaid_label, mermaid_node_id
from .projection_editorial import is_trivial_ps_topology
from .physical_component_projection import (
    GapView,
    LabeledValue,
    TechnologyChoiceView,
    _as_items,
    _as_mapping,
    _format_nested_value,
    _format_ref,
    _gap_view,
    _identity_rows,
    _join_unique,
    _nonempty_text,
    _string_list,
    _technology_stack,
    human_node_label,
    looks_like_uuid,
    preserve_markdown,
)

TOPOLOGY_VERB_PHRASES: dict[str, str] = {
    "depends_on": "depends on",
    "calls": "calls",
    "publishes_to": "publishes to",
    "subscribes_to": "subscribes to",
    "reads_from": "reads from",
    "writes_to": "writes to",
}
KNOWN_OPERATIONAL_KEYS: tuple[str, ...] = (
    "monitoring",
    "logging",
    "backup_recovery",
    "security",
)
OPERATIONAL_LABELS: dict[str, str] = {
    "monitoring": "Monitoring",
    "logging": "Logging",
    "backup_recovery": "Backup recovery",
    "security": "Security",
}
KNOWN_DEPLOYMENT_KEYS: tuple[str, ...] = (
    "hosting",
    "orchestration",
    "scaling_strategy",
)
DEPLOYMENT_LABELS: dict[str, str] = {
    "hosting": "Hosting",
    "orchestration": "Orchestration",
    "scaling_strategy": "Scaling strategy",
}
ARCHITECTURE_POSITION_NOTE = (
    "Topology handles are local authoring labels, not graph identities."
)
TOPOLOGY_HANDLE_NOTE = ARCHITECTURE_POSITION_NOTE
_EDGE_SPLIT_THRESHOLD = 16
_FAILURE_CARD_MITIGATION_LENGTH = 160


def _md_cell(text: str | None) -> str:
    """Escape Markdown table cell content without truncating authored text."""
    if not text:
        return ""
    return str(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>").replace("|", "\\|")


def _absent_cell(text: str | None) -> str:
    return _md_cell(text) if text else "—"


def _component_heading(alias: str, name: str | None) -> str:
    if name and name != alias and not looks_like_uuid(name):
        return f"{alias} — {name}"
    return alias


def _owning_adr_id(
    component_ref: str,
    *,
    relationships: Iterable[IRRelationship],
    entity: Any,
) -> str | None:
    for rel in relationships:
        if rel.relationship_type == "declared_in" and rel.from_entity_id == component_ref:
            return rel.to_entity_id
    metadata = entity.metadata if entity is not None and isinstance(getattr(entity, "metadata", None), dict) else {}
    owner = metadata.get("adr_id")
    return owner if isinstance(owner, str) and owner else None


def _component_spec(component_ref: str, owner_id: str | None, adr_models_by_id: dict[str, Any]) -> Any | None:
    if not owner_id:
        return None
    model = adr_models_by_id.get(owner_id)
    if model is None:
        return None
    for spec in _as_items(field_get(model, "component_specifications")):
        spec_id = field_get(spec, "id") or field_get(spec, "component_id")
        if spec_id == component_ref:
            return spec
    return None


@dataclass(frozen=True)
class SystemIdentityView:
    alias_id: str
    name: str | None
    heading: str


@dataclass(frozen=True)
class SystemBoundaryView:
    alias_id: str
    name: str
    heading: str
    description: str
    external_dependencies: tuple[str, ...]
    exposed_interfaces: tuple[str, ...]


@dataclass(frozen=True)
class SystemComponentMembershipView:
    local_handle: str
    component_ref: str
    component_alias: str
    component_name: str
    heading: str
    component_type: str
    purpose: str
    authority_display: str
    authority_alias: str | None


@dataclass(frozen=True)
class SystemTopologyRelationshipView:
    from_ref: str
    to_ref: str
    from_heading: str
    to_heading: str
    verb: str
    human_phrase: str
    protocol: str | None
    description: str | None


@dataclass(frozen=True)
class IntegrationPatternView:
    pattern_name: str
    application: str
    components_affected: tuple[str, ...]
    rationale: str | None


@dataclass(frozen=True)
class DataFlowView:
    flow_id: str
    name: str
    heading: str
    description: str
    path_labels: tuple[str, ...]
    data_type: str | None
    volume: str | None
    latency_requirements: str | None


@dataclass(frozen=True)
class ScalabilityView:
    horizontal_scaling: str | None
    vertical_scaling: str | None
    bottlenecks: tuple[str, ...]
    capacity_planning: str | None


@dataclass(frozen=True)
class FailureModeView:
    scenario: str
    impact: str
    mitigation: str
    detection: str | None
    recovery: str | None


@dataclass(frozen=True)
class SystemChangeSafetyView:
    logical_contracts: tuple[str, ...]
    constituent_components: tuple[str, ...]
    internal_relationships: tuple[str, ...]
    external_dependencies: tuple[str, ...]
    exposed_interfaces: tuple[str, ...]
    operational_requirements: tuple[LabeledValue, ...]
    failure_mode_index: tuple[str, ...]
    known_gaps: tuple[str, ...]


@dataclass(frozen=True)
class ArchitecturePositionView:
    note: str
    system_heading: str
    component_count: int
    boundary_count: int
    relationship_count: int
    external_dependency_count: int
    logical_authority: tuple[str, ...]
    exposed_surfaces: tuple[str, ...]
    topology_verbs: tuple[str, ...]


@dataclass
class PhysicalSystemProjection:
    """Type-specific disposable presentation model for one ADR-PS."""

    identity_rows: tuple[LabeledValue, ...]
    architecture_position: ArchitecturePositionView
    topology_handle_note: str | None
    system: SystemIdentityView | None
    components: tuple[SystemComponentMembershipView, ...]
    topology_graphs: tuple[str, ...]
    relationships: tuple[SystemTopologyRelationshipView, ...]
    handle_index: tuple[LabeledValue, ...]
    boundaries: tuple[SystemBoundaryView, ...]
    change_safety: SystemChangeSafetyView
    integration_patterns: tuple[IntegrationPatternView, ...]
    data_flows: tuple[DataFlowView, ...]
    scalability: ScalabilityView | None
    failure_modes: tuple[FailureModeView, ...]
    failure_modes_as_cards: bool
    operational_requirements: tuple[LabeledValue, ...]
    deployment_rows: tuple[LabeledValue, ...]
    technology_stack: tuple[TechnologyChoiceView, ...]
    architecture_impact_rows: tuple[LabeledValue, ...]
    gaps: tuple[GapView, ...]
    related_adrs: tuple[str, ...] = field(default_factory=tuple)


def _resolve_component(
    component_ref: str,
    *,
    entities: Any,
    relationships: Iterable[IRRelationship],
    adr_models_by_id: dict[str, Any],
    format_ref: Callable[[str], str],
) -> tuple[str, str, str, str, str | None, str]:
    entity = entities.get(component_ref) if hasattr(entities, "get") else None
    owner_id = _owning_adr_id(component_ref, relationships=relationships, entity=entity)
    spec = _component_spec(component_ref, owner_id, adr_models_by_id)
    alias = ""
    if entity is not None:
        alias = str(field_get(entity, "alias_id") or "")
        metadata = entity.metadata if isinstance(getattr(entity, "metadata", None), dict) else {}
        if not alias:
            meta_alias = metadata.get("alias_id")
            if isinstance(meta_alias, str):
                alias = meta_alias
    if spec is not None and (not alias or looks_like_uuid(alias)):
        spec_alias = _nonempty_text(field_get(spec, "alias_id"))
        if spec_alias:
            alias = spec_alias
    if not alias:
        alias = component_ref
    name = ""
    if entity is not None:
        entity_name = getattr(entity, "name", None)
        if isinstance(entity_name, str) and entity_name.strip() and not looks_like_uuid(entity_name):
            name = entity_name.strip()
    if spec is not None and not name:
        name = _nonempty_text(field_get(spec, "name")) or ""
    component_type = ""
    if spec is not None:
        component_type = _nonempty_text(field_get(spec, "type")) or ""
    authority_display = ""
    authority_alias = None
    if owner_id:
        authority_display = format_ref(owner_id)
        owner_model = adr_models_by_id.get(owner_id)
        if owner_model is not None:
            authority_alias = _nonempty_text(field_get(owner_model, "alias_id"))
        if not authority_alias and not looks_like_uuid(authority_display):
            authority_alias = authority_display
    heading = _component_heading(alias, name)
    return alias, name, heading, component_type, authority_alias, authority_display


def _membership_views(
    adr: Any,
    *,
    entities: Any,
    relationships: Iterable[IRRelationship],
    adr_models_by_id: dict[str, Any],
    format_ref: Callable[[str], str],
) -> tuple[tuple[SystemComponentMembershipView, ...], dict[str, SystemComponentMembershipView]]:
    by_handle: dict[str, SystemComponentMembershipView] = {}
    members: list[SystemComponentMembershipView] = []
    for component in topology_components(adr):
        handle = _nonempty_text(field_get(component, "id")) or ""
        component_ref = _nonempty_text(field_get(component, "component_ref")) or ""
        purpose = preserve_markdown(field_get(component, "purpose") or "")
        alias, name, heading, component_type, authority_alias, authority_display = _resolve_component(
            component_ref,
            entities=entities,
            relationships=relationships,
            adr_models_by_id=adr_models_by_id,
            format_ref=format_ref,
        )
        view = SystemComponentMembershipView(
            local_handle=handle,
            component_ref=component_ref,
            component_alias=alias,
            component_name=name,
            heading=heading,
            component_type=component_type,
            purpose=purpose,
            authority_display=authority_display,
            authority_alias=authority_alias,
        )
        members.append(view)
        if handle:
            by_handle[handle] = view
    return tuple(members), by_handle


def _heading_for_handle(
    handle: str | None,
    by_handle: dict[str, SystemComponentMembershipView],
) -> str:
    if not handle:
        return ""
    member = by_handle.get(handle)
    if member is not None:
        return member.heading
    return handle


def _relationship_views(
    adr: Any,
    by_handle: dict[str, SystemComponentMembershipView],
) -> tuple[SystemTopologyRelationshipView, ...]:
    views: list[SystemTopologyRelationshipView] = []
    for rel in topology_relationships(adr):
        from_handle, to_handle, verb, protocol, description = topology_edge_fields(rel)
        if not verb:
            continue
        from_member = by_handle.get(from_handle or "")
        to_member = by_handle.get(to_handle or "")
        views.append(
            SystemTopologyRelationshipView(
                from_ref=from_member.component_ref if from_member else (from_handle or ""),
                to_ref=to_member.component_ref if to_member else (to_handle or ""),
                from_heading=_heading_for_handle(from_handle, by_handle),
                to_heading=_heading_for_handle(to_handle, by_handle),
                verb=verb,
                human_phrase=TOPOLOGY_VERB_PHRASES.get(verb, verb.replace("_", " ")),
                protocol=_nonempty_text(protocol),
                description=_nonempty_text(description),
            )
        )
    return tuple(views)


def _render_topology_graph(
    components: tuple[SystemComponentMembershipView, ...],
    relationships: tuple[SystemTopologyRelationshipView, ...],
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    lines = ["flowchart LR"]
    for member in components:
        node = mermaid_node_id(member.component_ref or member.local_handle)
        label = escape_mermaid_label(
            human_node_label(
                member.component_ref,
                entities=entities,
                adr_models_by_id=adr_models_by_id,
            )
            if member.component_ref
            else member.heading
        )
        lines.append(f'  {node}["{label}"]')
    for rel in relationships:
        src = mermaid_node_id(rel.from_ref)
        dst = mermaid_node_id(rel.to_ref)
        verb = escape_mermaid_label(rel.verb)
        lines.append(f'  {src} -->|"{verb}"| {dst}')
    lines.append("")
    return "\n".join(lines)


def _topology_graphs(
    components: tuple[SystemComponentMembershipView, ...],
    relationships: tuple[SystemTopologyRelationshipView, ...],
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> tuple[str, ...]:
    if not components:
        return ()
    if is_trivial_ps_topology(len(components), len(relationships)):
        return ()

    def render(
        nodes: tuple[SystemComponentMembershipView, ...],
        edges: tuple[SystemTopologyRelationshipView, ...],
    ) -> str:
        return _render_topology_graph(
            nodes, edges, entities=entities, adr_models_by_id=adr_models_by_id
        )

    if len(relationships) <= _EDGE_SPLIT_THRESHOLD:
        return (render(components, relationships),)
    by_verb: dict[str, list[SystemTopologyRelationshipView]] = {}
    for rel in relationships:
        by_verb.setdefault(rel.verb, []).append(rel)
    graphs: list[str] = []
    used: set[str] = set()
    for verb in sorted(by_verb):
        edges = tuple(by_verb[verb])
        refs = {endpoint for rel in edges for endpoint in (rel.from_ref, rel.to_ref)}
        nodes = tuple(member for member in components if member.component_ref in refs)
        graphs.append(render(nodes, edges))
        used.update(refs)
    isolated = tuple(member for member in components if member.component_ref not in used)
    if isolated:
        graphs.append(render(isolated, ()))
    return tuple(graphs)


def _boundary_views(adr: Any) -> tuple[SystemBoundaryView, ...]:
    views: list[SystemBoundaryView] = []
    for boundary in _as_items(field_get(adr, "system_boundaries")):
        alias_id = _nonempty_text(field_get(boundary, "id")) or ""
        name = _nonempty_text(field_get(boundary, "name")) or ""
        heading = f"{alias_id} — {name}" if alias_id and name else (alias_id or name)
        views.append(
            SystemBoundaryView(
                alias_id=alias_id,
                name=name,
                heading=heading,
                description=preserve_markdown(field_get(boundary, "description") or ""),
                external_dependencies=tuple(_string_list(field_get(boundary, "external_dependencies"))),
                exposed_interfaces=tuple(_string_list(field_get(boundary, "exposed_interfaces"))),
            )
        )
    return tuple(views)


def _integration_views(
    adr: Any,
    by_handle: dict[str, SystemComponentMembershipView],
) -> tuple[IntegrationPatternView, ...]:
    views: list[IntegrationPatternView] = []
    for pattern in _as_items(field_get(adr, "integration_patterns")):
        name = _nonempty_text(field_get(pattern, "pattern_name")) or ""
        application = preserve_markdown(field_get(pattern, "application") or "")
        if not name and not application:
            continue
        affected = tuple(
            _heading_for_handle(handle, by_handle)
            for handle in _string_list(field_get(pattern, "components_affected"))
        )
        views.append(
            IntegrationPatternView(
                pattern_name=name,
                application=application,
                components_affected=affected,
                rationale=preserve_markdown(field_get(pattern, "rationale") or "") or None,
            )
        )
    return tuple(views)


def _data_flow_views(
    adr: Any,
    by_handle: dict[str, SystemComponentMembershipView],
) -> tuple[DataFlowView, ...]:
    views: list[DataFlowView] = []
    for flow in _as_items(field_get(adr, "data_flows")):
        flow_id = _nonempty_text(field_get(flow, "id")) or ""
        name = _nonempty_text(field_get(flow, "name")) or ""
        heading = f"{flow_id} — {name}" if flow_id and name else (flow_id or name)
        path = tuple(
            _heading_for_handle(handle, by_handle) for handle in _string_list(field_get(flow, "path"))
        )
        views.append(
            DataFlowView(
                flow_id=flow_id,
                name=name,
                heading=heading,
                description=preserve_markdown(field_get(flow, "description") or ""),
                path_labels=path,
                data_type=_nonempty_text(field_get(flow, "data_type")),
                volume=_nonempty_text(field_get(flow, "volume")),
                latency_requirements=_nonempty_text(field_get(flow, "latency_requirements")),
            )
        )
    return tuple(views)


def _scalability_view(adr: Any) -> ScalabilityView | None:
    raw = field_get(adr, "scalability_strategy")
    mapping = _as_mapping(raw)
    if not mapping:
        return None
    view = ScalabilityView(
        horizontal_scaling=preserve_markdown(mapping.get("horizontal_scaling") or "") or None,
        vertical_scaling=preserve_markdown(mapping.get("vertical_scaling") or "") or None,
        bottlenecks=tuple(_string_list(mapping.get("bottlenecks"))),
        capacity_planning=preserve_markdown(mapping.get("capacity_planning") or "") or None,
    )
    if not any([view.horizontal_scaling, view.vertical_scaling, view.bottlenecks, view.capacity_planning]):
        return None
    return view


def _failure_mode_views(adr: Any) -> tuple[FailureModeView, ...]:
    views: list[FailureModeView] = []
    for item in _as_items(field_get(adr, "failure_modes")):
        mapping = _as_mapping(item)
        scenario = _nonempty_text(mapping.get("scenario")) or ""
        impact = _nonempty_text(mapping.get("impact")) or ""
        mitigation = preserve_markdown(mapping.get("mitigation") or "")
        if not any([scenario, impact, mitigation]):
            continue
        views.append(
            FailureModeView(
                scenario=scenario,
                impact=impact,
                mitigation=mitigation,
                detection=_nonempty_text(mapping.get("detection")),
                recovery=_nonempty_text(mapping.get("recovery")),
            )
        )
    return tuple(views)


def _failure_modes_as_cards(modes: tuple[FailureModeView, ...]) -> bool:
    for mode in modes:
        if "\n" in mode.mitigation or "|" in mode.mitigation:
            return True
        if len(mode.mitigation) > _FAILURE_CARD_MITIGATION_LENGTH:
            return True
    return False


def _operational_rows(adr: Any) -> tuple[LabeledValue, ...]:
    raw = field_get(adr, "operational_requirements")
    mapping = _as_mapping(raw)
    if not mapping:
        return ()
    rows: list[LabeledValue] = []
    seen: set[str] = set()
    for key in KNOWN_OPERATIONAL_KEYS:
        if key not in mapping:
            continue
        formatted = _format_nested_value(mapping.get(key))
        if formatted:
            rows.append(LabeledValue(OPERATIONAL_LABELS[key], formatted))
            seen.add(key)
    extra_keys = sorted(key for key in mapping if key not in seen)
    for key in extra_keys:
        formatted = _format_nested_value(mapping.get(key))
        if formatted:
            from .physical_component_projection import humanize_key

            rows.append(LabeledValue(humanize_key(str(key)), formatted))
    return tuple(rows)


def _deployment_rows(adr: Any) -> tuple[LabeledValue, ...]:
    raw = field_get(adr, "deployment_model")
    mapping = _as_mapping(raw)
    if not mapping:
        return ()
    rows: list[LabeledValue] = []
    seen: set[str] = set()
    for key in KNOWN_DEPLOYMENT_KEYS:
        if key not in mapping:
            continue
        formatted = _format_nested_value(mapping.get(key))
        if formatted:
            rows.append(LabeledValue(DEPLOYMENT_LABELS[key], formatted))
            seen.add(key)
    extra_keys = sorted(key for key in mapping if key not in seen)
    for key in extra_keys:
        formatted = _format_nested_value(mapping.get(key))
        if formatted:
            from .physical_component_projection import humanize_key

            rows.append(LabeledValue(humanize_key(str(key)), formatted))
    return tuple(rows)


def _system_identity(adr: Any) -> SystemIdentityView | None:
    system = field_get(adr, "system")
    if system is None:
        return None
    alias_id = _nonempty_text(field_get(system, "alias_id")) or ""
    name = _nonempty_text(field_get(system, "name"))
    heading = f"{alias_id} — {name}" if alias_id and name else (name or alias_id)
    if not heading:
        return None
    return SystemIdentityView(alias_id=alias_id, name=name, heading=heading)


@implements_adr("ADR-L-0007")
def build_physical_system_projection(
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
) -> PhysicalSystemProjection:
    """Extract a disposable ADR-PS presentation model from authored + compiled state."""
    relationship_list = list(relationships)

    def format_ref(ref_id: str) -> str:
        return _format_ref(
            ref_id,
            resolve_present_ref=resolve_present_ref,
            format_present_ref=format_present_ref,
            entities=entities,
            adr_models_by_id=adr_models_by_id,
        )

    identity = list(
        _identity_rows(
            adr,
            adr_type=adr_type,
            status=status,
            alias_id=alias_id,
            format_ref=format_ref,
        )
    )
    system = _system_identity(adr)
    if system is not None:
        inserted: list[LabeledValue] = []
        for row in identity:
            inserted.append(row)
            if row.label == "Alias":
                inserted.append(LabeledValue("System", system.heading))
        identity = inserted

    members, by_handle = _membership_views(
        adr,
        entities=entities,
        relationships=relationship_list,
        adr_models_by_id=adr_models_by_id,
        format_ref=format_ref,
    )
    for member in members:
        owner = _owning_adr_id(
            member.component_ref,
            relationships=relationship_list,
            entity=entities.get(member.component_ref) if hasattr(entities, "get") else None,
        )
        if owner:
            resolve_present_ref(owner)

    rel_views = _relationship_views(adr, by_handle)
    boundaries = _boundary_views(adr)
    integration = _integration_views(adr, by_handle)
    flows = _data_flow_views(adr, by_handle)
    scalability = _scalability_view(adr)
    failures = _failure_mode_views(adr)
    operational = _operational_rows(adr)
    deployment = _deployment_rows(adr)
    gaps = tuple(
        _gap_view(gap, index)
        for index, gap in enumerate(_as_items(field_get(adr, "gaps")), start=1)
        if _as_mapping(gap) or (isinstance(gap, str) and str(gap).strip())
    )
    logical_authority = tuple(
        format_ref(item)
        for item in field_get(adr, "implements_logical") or []
        if isinstance(item, str)
    )
    external_deps = _join_unique(
        dep for boundary in boundaries for dep in boundary.external_dependencies
    )
    exposed = _join_unique(
        item for boundary in boundaries for item in boundary.exposed_interfaces
    )
    verbs = _join_unique(rel.verb for rel in rel_views)
    handle_index = tuple(
        LabeledValue(member.local_handle, member.heading)
        for member in members
        if member.local_handle
    )
    change_safety = SystemChangeSafetyView(
        logical_contracts=logical_authority,
        constituent_components=tuple(member.heading for member in members),
        internal_relationships=tuple(
            f"{rel.from_heading} {rel.human_phrase} {rel.to_heading}" for rel in rel_views
        ),
        external_dependencies=external_deps,
        exposed_interfaces=exposed,
        operational_requirements=operational,
        failure_mode_index=tuple(
            f"{mode.scenario} — {mode.impact}" if mode.impact else mode.scenario for mode in failures
        ),
        known_gaps=tuple(gap.heading for gap in gaps),
    )
    position = ArchitecturePositionView(
        note=ARCHITECTURE_POSITION_NOTE,
        system_heading=system.heading if system else "",
        component_count=len(members),
        boundary_count=len(boundaries),
        relationship_count=len(rel_views),
        external_dependency_count=len(external_deps),
        logical_authority=logical_authority,
        exposed_surfaces=exposed,
        topology_verbs=verbs,
    )
    related = [
        format_ref(item) for item in field_get(adr, "related_adrs") or [] if isinstance(item, str)
    ]
    impact_rows: list[LabeledValue] = []
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

    return PhysicalSystemProjection(
        identity_rows=tuple(identity),
        architecture_position=position,
        topology_handle_note=TOPOLOGY_HANDLE_NOTE if members else None,
        system=system,
        components=members,
        topology_graphs=_topology_graphs(
            members,
            rel_views,
            entities=entities,
            adr_models_by_id=adr_models_by_id,
        ),
        relationships=rel_views,
        handle_index=handle_index,
        boundaries=boundaries,
        change_safety=change_safety,
        integration_patterns=integration,
        data_flows=flows,
        scalability=scalability,
        failure_modes=failures,
        failure_modes_as_cards=_failure_modes_as_cards(failures),
        operational_requirements=operational,
        deployment_rows=deployment,
        technology_stack=_technology_stack(adr),
        architecture_impact_rows=tuple(impact_rows),
        gaps=gaps,
        related_adrs=tuple(related),
    )
