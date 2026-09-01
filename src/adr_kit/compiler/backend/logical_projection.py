"""Disposable ADR-L human-projection view model.

Not a public SDK contract. Field X exists -> view field Y -> template section Z.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from ...decorators import implements_adr
from ..frontend.adr_access import field_get, presentation_id
from ..ir.rel_graph import IRRelationship
from .human_adr_projection import escape_mermaid_label, mermaid_node_id
from .physical_component_projection import (
    AlternativeRow,
    GapView,
    LabeledValue,
    _as_items,
    _as_mapping,
    _format_nested_value,
    _format_ref,
    _gap_view,
    _heading_includes_summary,
    _identity_rows,
    _join_unique,
    _nonempty_text,
    _string_list,
    humanize_key,
    looks_like_uuid,
    preserve_markdown,
)

_LOGICAL_TRACEABILITY_VERBS = frozenset(
    {
        "enforces",
        "enables",
        "enabled_by",
        "governs",
        "refines",
        "supersedes",
        "implemented_by",
    }
)
_PEER_PHRASES: dict[tuple[str, str], str] = {
    ("implements_logical", "incoming"): "implements this logical authority",
    ("implements_logical", "outgoing"): "implements logical authority",
    ("references", "incoming"): "references this logical authority",
    ("references", "outgoing"): "references",
    ("related_to", "incoming"): "relates to this logical authority",
    ("related_to", "outgoing"): "relates to",
    ("supersedes", "incoming"): "is superseded by this logical authority",
    ("supersedes", "outgoing"): "supersedes",
    ("superseded_by", "incoming"): "is superseded by",
    ("superseded_by", "outgoing"): "superseded by",
}


@dataclass(frozen=True)
class LogicalGlanceRow:
    label: str
    value: str


@dataclass(frozen=True)
class DecisionIndexRow:
    alias_id: str
    choice: str
    traceability: str | None


@dataclass(frozen=True)
class TraceabilityItem:
    category: str
    target: str


@dataclass(frozen=True)
class ConsequencesView:
    positive: tuple[str, ...]
    negative: tuple[str, ...]


@dataclass(frozen=True)
class LogicalDecisionView:
    alias_id: str
    heading: str
    summary: str
    show_summary_body: bool
    rationale: str
    alternatives: tuple[AlternativeRow, ...]
    consequences: ConsequencesView
    traceability: tuple[TraceabilityItem, ...]


@dataclass(frozen=True)
class CapabilityView:
    alias_id: str
    name: str
    heading: str
    description: str
    acceptance_criteria: tuple[str, ...]
    implemented_by: tuple[str, ...]
    enabled_by: tuple[str, ...]


@dataclass(frozen=True)
class ArchitecturalBoundaryView:
    alias_id: str
    name: str
    heading: str
    description: str
    rationale: str


@dataclass(frozen=True)
class InteractionContractView:
    alias_id: str
    heading: str
    parties: tuple[str, ...]
    protocol: str
    guarantees: str


@dataclass(frozen=True)
class InvariantIndexRow:
    alias_id: str
    requirement: str
    enforcement: str
    verification: str


@dataclass(frozen=True)
class InvariantView:
    alias_id: str
    heading: str
    statement: str
    scope: str
    enforcement_level: str
    enforcement_mechanism: str
    verification_method: str
    rationale: str
    declaration_mode: str | None
    upheld_by: tuple[str, ...]
    policy_reference: str | None
    compliance_frameworks: tuple[str, ...]
    exceptions: tuple[str, ...]
    supersedes: tuple[str, ...]


@dataclass(frozen=True)
class NonFunctionalRequirementView:
    alias_id: str
    category: str
    requirement: str
    acceptance_criteria: str
    extra_rows: tuple[LabeledValue, ...]


@dataclass(frozen=True)
class ConstraintView:
    alias_id: str
    constraint_type: str | None
    heading: str
    description: str
    rationale: str | None


@dataclass(frozen=True)
class CapabilityRealizationRow:
    capability_display: str
    component_display: str
    canonical_path: str


@dataclass(frozen=True)
class PhysicalRealizationView:
    systems: tuple[str, ...]
    components: tuple[str, ...]
    capability_realizations: tuple[CapabilityRealizationRow, ...]
    graph: str | None


@dataclass(frozen=True)
class CompressedPeerView:
    alias_id: str
    title: str
    relationship_phrase: str
    canonical_path: str
    link: str | None
    use_table: bool
    paths: tuple[str, ...]


@dataclass(frozen=True)
class LifecycleCategoryView:
    heading: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class GovernanceSectionView:
    heading: str
    rows: tuple[LabeledValue, ...]


@dataclass(frozen=True)
class ExtensionEntityView:
    namespace: str
    entity_id: str
    fields: tuple[LabeledValue, ...]


@dataclass(frozen=True)
class ExtensionRelationshipView:
    namespace: str
    verb: str
    from_display: str
    to_display: str
    canonical_path: str


@dataclass
class LogicalProjection:
    """Type-specific disposable presentation model for one ADR-L."""

    identity_rows: tuple[LabeledValue, ...]
    glance_rows: tuple[LogicalGlanceRow, ...]
    context: str
    decision_index: tuple[DecisionIndexRow, ...]
    decisions: tuple[LogicalDecisionView, ...]
    capabilities: tuple[CapabilityView, ...]
    boundaries: tuple[ArchitecturalBoundaryView, ...]
    interaction_contracts: tuple[InteractionContractView, ...]
    invariant_index: tuple[InvariantIndexRow, ...]
    invariants: tuple[InvariantView, ...]
    non_functional_requirements: tuple[NonFunctionalRequirementView, ...]
    constraints: tuple[ConstraintView, ...]
    decision_traceability_graph: str | None
    capability_realization_graph: str | None
    physical_realization: PhysicalRealizationView | None
    governance_sections: tuple[GovernanceSectionView, ...]
    lifecycle_categories: tuple[LifecycleCategoryView, ...]
    compressed_peers: tuple[CompressedPeerView, ...]
    extension_entities: tuple[ExtensionEntityView, ...]
    extension_relationships: tuple[ExtensionRelationshipView, ...]
    gaps: tuple[GapView, ...]
    notes: str | None
    tags: tuple[str, ...]
    has_human_relationship_inventory: bool = False


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _decision_consequences(raw: Any) -> ConsequencesView:
    positive: list[str] = []
    negative: list[str] = []
    if raw is None:
        return ConsequencesView(positive=(), negative=())
    if isinstance(raw, list):
        positive.extend(_string_list(raw))
        return ConsequencesView(positive=tuple(positive), negative=())
    cons_map = _as_mapping(raw)
    positive.extend(_string_list(cons_map.get("positive")))
    negative.extend(_string_list(cons_map.get("negative")))
    for key, value in cons_map.items():
        if key in {"positive", "negative"}:
            continue
        formatted = _format_nested_value(value)
        if formatted:
            positive.append(f"{humanize_key(str(key))}: {formatted}")
    return ConsequencesView(positive=tuple(positive), negative=tuple(negative))


def _traceability_items(
    decision: Any,
    *,
    format_ref: Callable[[str], str],
) -> tuple[TraceabilityItem, ...]:
    items: list[TraceabilityItem] = []
    mapping = {
        "Enforces": field_get(decision, "enforces_invariants") or [],
        "Enables": field_get(decision, "enables_capabilities") or [],
        "Governs": field_get(decision, "governs_components") or [],
        "Refines": field_get(decision, "refines") or [],
        "Supersedes": field_get(decision, "supersedes") or [],
        "Related invariants": field_get(decision, "related_invariants") or [],
    }
    for category, refs in mapping.items():
        for ref in _as_items(refs):
            ref_id = _text(ref)
            if not ref_id:
                continue
            items.append(TraceabilityItem(category=category, target=format_ref(ref_id)))
    return tuple(items)


def _traceability_summary(items: tuple[TraceabilityItem, ...]) -> str | None:
    if not items:
        return None
    grouped: dict[str, list[str]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append(item.target)
    parts = []
    for category in sorted(grouped):
        targets = grouped[category]
        if category in {"Enforces", "Enables", "Governs", "Refines", "Supersedes"}:
            parts.append(f"{category} {', '.join(targets)}")
        elif category == "Related invariants":
            parts.append(f"Related {', '.join(targets)}")
    return "; ".join(parts) if parts else None


def _logical_decision_view(
    decision: Any,
    *,
    format_ref: Callable[[str], str],
) -> LogicalDecisionView | None:
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
            alternatives.append(AlternativeRow(name=name or "", rejected_because=rejected or ""))
    traceability = _traceability_items(decision, format_ref=format_ref)
    show_summary_body = bool(summary) and not _heading_includes_summary(heading, summary, alias_id)
    return LogicalDecisionView(
        alias_id=alias_id,
        heading=heading,
        summary=summary,
        show_summary_body=show_summary_body,
        rationale=preserve_markdown(field_get(decision, "rationale") or ""),
        alternatives=tuple(alternatives),
        consequences=_decision_consequences(field_get(decision, "consequences")),
        traceability=traceability,
    )


def _capability_view(
    capability: Any,
    *,
    format_ref: Callable[[str], str],
) -> CapabilityView:
    alias_id = _nonempty_text(field_get(capability, "alias_id")) or _text(
        field_get(capability, "id") or "capability"
    )
    if looks_like_uuid(alias_id):
        alias_id = _nonempty_text(field_get(capability, "name")) or alias_id
    name = _nonempty_text(field_get(capability, "name")) or alias_id
    heading = f"{alias_id} — {name}" if alias_id and name and alias_id != name else (name or alias_id)
    acceptance = _string_list(field_get(capability, "acceptance_criteria"))
    implemented_by = tuple(
        format_ref(item)
        for item in field_get(capability, "implemented_by_components") or []
        if isinstance(item, str)
    )
    enabled_by = tuple(
        format_ref(item)
        for item in field_get(capability, "enabled_by_decisions") or []
        if isinstance(item, str)
    )
    return CapabilityView(
        alias_id=alias_id,
        name=name,
        heading=heading,
        description=preserve_markdown(field_get(capability, "description") or ""),
        acceptance_criteria=tuple(acceptance),
        implemented_by=implemented_by,
        enabled_by=enabled_by,
    )


def _boundary_view(boundary: Any) -> ArchitecturalBoundaryView:
    alias_id = _nonempty_text(field_get(boundary, "alias_id")) or _text(
        field_get(boundary, "id") or "boundary"
    )
    name = _nonempty_text(field_get(boundary, "name")) or alias_id
    heading = f"{alias_id} — {name}" if alias_id and name else (name or alias_id)
    return ArchitecturalBoundaryView(
        alias_id=alias_id,
        name=name,
        heading=heading,
        description=preserve_markdown(field_get(boundary, "description") or ""),
        rationale=preserve_markdown(field_get(boundary, "rationale") or ""),
    )


def _contract_view(contract: Any) -> InteractionContractView:
    alias_id = _nonempty_text(field_get(contract, "alias_id")) or _text(
        field_get(contract, "id") or "contract"
    )
    parties = tuple(_string_list(field_get(contract, "parties")))
    return InteractionContractView(
        alias_id=alias_id,
        heading=alias_id,
        parties=parties,
        protocol=_nonempty_text(field_get(contract, "protocol")) or "",
        guarantees=preserve_markdown(field_get(contract, "guarantees") or ""),
    )


def _invariant_view(
    invariant: Any,
    *,
    format_ref: Callable[[str], str],
) -> InvariantView:
    alias_id = _nonempty_text(field_get(invariant, "alias_id")) or _text(
        field_get(invariant, "id") or "invariant"
    )
    enforcement_level = _text(field_get(invariant, "enforcement_level"))
    enforcement_mechanism = _nonempty_text(field_get(invariant, "enforcement_mechanism")) or ""
    verification_method = _nonempty_text(field_get(invariant, "verification_method")) or ""
    statement = preserve_markdown(field_get(invariant, "statement") or "")
    enforcement_display = (
        f"{enforcement_level.upper()} / {enforcement_mechanism}"
        if enforcement_level and enforcement_mechanism
        else enforcement_level or enforcement_mechanism
    )
    return InvariantView(
        alias_id=alias_id,
        heading=alias_id,
        statement=statement,
        scope=_nonempty_text(field_get(invariant, "scope")) or "",
        enforcement_level=enforcement_level,
        enforcement_mechanism=enforcement_mechanism,
        verification_method=verification_method,
        rationale=preserve_markdown(field_get(invariant, "rationale") or ""),
        declaration_mode=_nonempty_text(field_get(invariant, "declaration_mode")),
        upheld_by=tuple(
            format_ref(item)
            for item in field_get(invariant, "upheld_by_decisions") or []
            if isinstance(item, str)
        ),
        policy_reference=_nonempty_text(field_get(invariant, "policy_reference")),
        compliance_frameworks=tuple(_string_list(field_get(invariant, "compliance_frameworks"))),
        exceptions=tuple(_string_list(field_get(invariant, "exceptions"))),
        supersedes=tuple(
            format_ref(item)
            for item in field_get(invariant, "supersedes") or []
            if isinstance(item, str)
        ),
    )


def _invariant_index_row(invariant: InvariantView) -> InvariantIndexRow:
    enforcement = (
        f"{invariant.enforcement_level.upper()} / {invariant.enforcement_mechanism}"
        if invariant.enforcement_level and invariant.enforcement_mechanism
        else invariant.enforcement_level or invariant.enforcement_mechanism or "—"
    )
    verification = invariant.verification_method or "—"
    requirement = invariant.statement.replace("\n", " ").strip()
    if len(requirement) > 120:
        requirement = requirement[:117].rsplit(" ", 1)[0] + "…"
    return InvariantIndexRow(
        alias_id=invariant.alias_id,
        requirement=requirement or "—",
        enforcement=enforcement,
        verification=verification,
    )


def _nfr_view(item: Any, index: int) -> NonFunctionalRequirementView | None:
    mapping = _as_mapping(item) if not isinstance(item, str) else {}
    if isinstance(item, str):
        text = preserve_markdown(item)
        if not text:
            return None
        return NonFunctionalRequirementView(
            alias_id=f"NFR-{index:04d}",
            category="",
            requirement=text,
            acceptance_criteria="",
            extra_rows=(),
        )
    alias = _nonempty_text(mapping.get("alias_id")) or _nonempty_text(mapping.get("id"))
    if alias and looks_like_uuid(alias):
        alias = None
    alias_id = alias or f"NFR-{index:04d}"
    requirement = preserve_markdown(mapping.get("requirement") or mapping.get("description") or "")
    if not requirement and not mapping:
        return None
    extra: list[LabeledValue] = []
    reserved = {"id", "alias_id", "category", "requirement", "description", "acceptance_criteria"}
    for key in sorted(mapping):
        if key in reserved:
            continue
        formatted = _format_nested_value(mapping.get(key))
        if formatted:
            extra.append(LabeledValue(humanize_key(str(key)), formatted))
    return NonFunctionalRequirementView(
        alias_id=alias_id,
        category=_nonempty_text(mapping.get("category")) or "",
        requirement=requirement,
        acceptance_criteria=preserve_markdown(mapping.get("acceptance_criteria") or ""),
        extra_rows=tuple(extra),
    )


def _constraint_view(item: Any, index: int) -> ConstraintView | None:
    mapping = _as_mapping(item) if not isinstance(item, str) else {}
    if isinstance(item, str):
        text = preserve_markdown(item)
        if not text:
            return None
        return ConstraintView(
            alias_id=f"CONST-{index:04d}",
            constraint_type=None,
            heading=f"CONST-{index:04d}",
            description=text,
            rationale=None,
        )
    alias = _nonempty_text(mapping.get("alias_id")) or _nonempty_text(mapping.get("id"))
    if alias and looks_like_uuid(alias):
        alias = None
    alias_id = alias or f"CONST-{index:04d}"
    constraint_type = _nonempty_text(mapping.get("type"))
    description = preserve_markdown(mapping.get("description") or "")
    rationale = _nonempty_text(mapping.get("rationale"))
    if not description and not rationale:
        return None
    heading = f"{alias_id} — {constraint_type}" if constraint_type else alias_id
    return ConstraintView(
        alias_id=alias_id,
        constraint_type=constraint_type,
        heading=heading,
        description=description,
        rationale=rationale,
    )


def _entity_label(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
    format_ref: Callable[[str], str],
) -> str:
    return format_ref(entity_id)


def _unique_relationships(edges: Iterable[IRRelationship]) -> list[IRRelationship]:
    unique: dict[tuple[str, str, str], IRRelationship] = {}
    for relationship in edges:
        key = (
            relationship.relationship_type,
            relationship.from_entity_id,
            relationship.to_entity_id,
        )
        unique.setdefault(key, relationship)
    return sorted(
        unique.values(),
        key=lambda item: (
            item.relationship_type,
            item.from_entity_id,
            item.to_entity_id,
            item.relationship_id,
        ),
    )


def _build_semantic_graph(
    *,
    edges: list[IRRelationship],
    entities: Any,
    adr_models_by_id: dict[str, Any],
    format_ref: Callable[[str], str],
    title: str | None = None,
) -> str | None:
    semantic = [
        rel for rel in edges if rel.relationship_type in _LOGICAL_TRACEABILITY_VERBS
    ]
    semantic = _unique_relationships(semantic)
    if not semantic:
        return None
    local_nodes = sorted(
        {
            endpoint
            for relationship in semantic
            for endpoint in (relationship.from_entity_id, relationship.to_entity_id)
        }
    )
    lines = ["flowchart LR"]
    if title:
        lines.append(f'  %% {title}')
    for entity_id in local_nodes:
        node = mermaid_node_id(entity_id)
        label = escape_mermaid_label(
            _entity_label(
                entity_id,
                entities=entities,
                adr_models_by_id=adr_models_by_id,
                format_ref=format_ref,
            )
        )
        lines.append(f'  {node}["{label}"]')
    for relationship in semantic:
        src = mermaid_node_id(relationship.from_entity_id)
        dst = mermaid_node_id(relationship.to_entity_id)
        verb = escape_mermaid_label(relationship.relationship_type)
        lines.append(f'  {src} -->|"{verb}"| {dst}')
    lines.append("")
    return "\n".join(lines)


def _physical_realization(
    *,
    subject_id: str,
    adr: Any,
    relationships: list[IRRelationship],
    entities: Any,
    adr_models_by_id: dict[str, Any],
    format_ref: Callable[[str], str],
) -> PhysicalRealizationView | None:
    systems: list[str] = []
    components: list[str] = []
    capability_ids = {
        _text(field_get(cap, "id"))
        for cap in _as_items(field_get(adr, "capabilities"))
        if field_get(cap, "id")
    }
    for rel in relationships:
        if rel.relationship_type != "implements_logical" or rel.to_entity_id != subject_id:
            continue
        peer = adr_models_by_id.get(rel.from_entity_id)
        if peer is None:
            continue
        adr_type = _text(field_get(peer, "adr_type"))
        display = format_ref(rel.from_entity_id)
        if adr_type == "physical-system":
            systems.append(display)
        elif adr_type == "physical-component":
            components.append(display)
    capability_realizations: list[CapabilityRealizationRow] = []
    for rel in relationships:
        if rel.relationship_type != "implemented_by":
            continue
        if rel.from_entity_id not in capability_ids:
            continue
        capability_realizations.append(
            CapabilityRealizationRow(
                capability_display=format_ref(rel.from_entity_id),
                component_display=format_ref(rel.to_entity_id),
                canonical_path=(
                    f"{presentation_id(entities.get(rel.from_entity_id) or rel.from_entity_id)} "
                    f"-[:implemented_by]-> "
                    f"{presentation_id(entities.get(rel.to_entity_id) or rel.to_entity_id)}"
                ),
            )
        )
    for capability in _as_items(field_get(adr, "capabilities")):
        cap_id = _text(field_get(capability, "id"))
        cap_display = format_ref(cap_id) if cap_id else ""
        for component_id in field_get(capability, "implemented_by_components") or []:
            if not isinstance(component_id, str):
                continue
            path = f"{cap_display} → {format_ref(component_id)}"
            if any(row.canonical_path.endswith(path) for row in capability_realizations):
                continue
            capability_realizations.append(
                CapabilityRealizationRow(
                    capability_display=cap_display,
                    component_display=format_ref(component_id),
                    canonical_path=path,
                )
            )
    systems = _join_unique(systems)
    components = _join_unique(components)
    capability_realizations = tuple(
        sorted(capability_realizations, key=lambda row: (row.capability_display, row.component_display))
    )
    if not systems and not components and not capability_realizations:
        return None
    graph = None
    if len(capability_realizations) > 1:
        edges = [
            rel
            for rel in relationships
            if rel.relationship_type == "implemented_by" and rel.from_entity_id in capability_ids
        ]
        graph = _build_semantic_graph(
            edges=edges,
            entities=entities,
            adr_models_by_id=adr_models_by_id,
            format_ref=format_ref,
            title="Capability realization",
        )
    return PhysicalRealizationView(
        systems=systems,
        components=components,
        capability_realizations=capability_realizations,
        graph=graph,
    )


def _governance_sections(adr: Any, *, format_ref: Callable[[str], str]) -> tuple[GovernanceSectionView, ...]:
    sections: list[GovernanceSectionView] = []
    ownership = field_get(adr, "ownership")
    if ownership is not None:
        rows: list[LabeledValue] = []
        mapping = _as_mapping(ownership)
        for key in sorted(mapping):
            formatted = _format_nested_value(mapping.get(key))
            if formatted:
                rows.append(LabeledValue(humanize_key(str(key)), formatted))
        if rows:
            sections.append(GovernanceSectionView(heading="Ownership", rows=tuple(rows)))
    governance = field_get(adr, "governance")
    if governance is not None:
        rows = []
        mapping = _as_mapping(governance)
        for key in sorted(mapping):
            formatted = _format_nested_value(mapping.get(key))
            if formatted:
                rows.append(LabeledValue(humanize_key(str(key)), formatted))
        if rows:
            sections.append(GovernanceSectionView(heading="Governance", rows=tuple(rows)))
    for heading, field_name in (
        ("Substrate bindings", "substrate_bindings"),
        ("Rule bindings", "rule_bindings"),
        ("Evidence expectations", "evidence_expectations"),
    ):
        rows = []
        for index, item in enumerate(_as_items(field_get(adr, field_name)), start=1):
            mapping = _as_mapping(item)
            if not mapping:
                continue
            parts = []
            for key in sorted(mapping):
                formatted = _format_nested_value(mapping.get(key))
                if formatted:
                    parts.append(f"{humanize_key(str(key))}: {formatted}")
            if parts:
                rows.append(LabeledValue(f"Item {index}", "; ".join(parts)))
        if rows:
            sections.append(GovernanceSectionView(heading=heading, rows=tuple(rows)))
    return tuple(sections)


def _lifecycle_categories(
    adr: Any,
    *,
    relationships: list[IRRelationship],
    subject_id: str,
    format_ref: Callable[[str], str],
) -> tuple[LifecycleCategoryView, ...]:
    categories: list[LifecycleCategoryView] = []
    supersedes = [
        format_ref(item) for item in field_get(adr, "supersedes") or [] if isinstance(item, str)
    ]
    if supersedes:
        categories.append(LifecycleCategoryView(heading="Supersedes", items=tuple(supersedes)))
    superseded_by = field_get(adr, "superseded_by")
    if isinstance(superseded_by, str) and superseded_by:
        categories.append(
            LifecycleCategoryView(heading="Superseded by", items=(format_ref(superseded_by),))
        )
    related = [
        format_ref(item) for item in field_get(adr, "related_adrs") or [] if isinstance(item, str)
    ]
    if related:
        categories.append(LifecycleCategoryView(heading="Related ADRs", items=tuple(related)))
    references: list[str] = []
    for rel in relationships:
        if rel.from_entity_id != subject_id and rel.to_entity_id != subject_id:
            continue
        if rel.relationship_type != "references":
            continue
        other = rel.to_entity_id if rel.from_entity_id == subject_id else rel.from_entity_id
        references.append(format_ref(other))
    references = list(_join_unique(references))
    if references:
        categories.append(LifecycleCategoryView(heading="References", items=tuple(references)))
    return tuple(categories)


def _peer_phrase(*, verb: str, canonical_path: str, subject_alias: str) -> str:
    if f"-> {subject_alias}" in canonical_path:
        direction = "incoming"
    elif canonical_path.startswith(f"{subject_alias} "):
        direction = "outgoing"
    else:
        direction = "incoming"
    phrase = _PEER_PHRASES.get((verb, direction))
    if phrase:
        return phrase
    return verb.replace("_", " ")


def _compressed_peers(
    *,
    subject_alias: str,
    peer_cards: Iterable[Any],
) -> tuple[CompressedPeerView, ...]:
    views: list[CompressedPeerView] = []
    for card in peer_cards:
        rels = list(getattr(card, "relationships", []) or [])
        if not rels:
            continue
        paths = tuple(rel.canonical_path for rel in rels)
        primary = rels[0]
        phrase = _peer_phrase(
            verb=primary.verb,
            canonical_path=primary.canonical_path,
            subject_alias=subject_alias,
        )
        views.append(
            CompressedPeerView(
                alias_id=getattr(card, "alias_id", ""),
                title=getattr(card, "title", ""),
                relationship_phrase=phrase,
                canonical_path=primary.canonical_path,
                link=getattr(card, "link", None),
                use_table=len(rels) == 1,
                paths=paths,
            )
        )
    return tuple(views)


def _extension_entities(adr: Any) -> tuple[ExtensionEntityView, ...]:
    views: list[ExtensionEntityView] = []
    for item in _as_items(field_get(adr, "extension_entities")):
        mapping = _as_mapping(item)
        if not mapping:
            continue
        entity_type = _nonempty_text(mapping.get("entity_type")) or "extension"
        namespace = entity_type.split(":", 1)[0] if ":" in entity_type else entity_type
        entity_id = _nonempty_text(mapping.get("alias_id")) or _nonempty_text(mapping.get("id")) or ""
        rows: list[LabeledValue] = []
        if entity_type:
            rows.append(LabeledValue("Entity type", entity_type))
        rationale = _nonempty_text(mapping.get("rationale"))
        if rationale:
            rows.append(LabeledValue("Rationale", rationale))
        properties = _as_mapping(mapping.get("properties"))
        for key in sorted(properties):
            formatted = _format_nested_value(properties.get(key))
            if formatted:
                rows.append(LabeledValue(humanize_key(str(key)), formatted))
        reserved = {"id", "alias_id", "alias_name", "entity_type", "properties", "rationale"}
        for key in sorted(mapping):
            if key in reserved:
                continue
            formatted = _format_nested_value(mapping.get(key))
            if formatted:
                rows.append(LabeledValue(humanize_key(str(key)), formatted))
        if entity_id or rows:
            views.append(
                ExtensionEntityView(namespace=namespace, entity_id=entity_id, fields=tuple(rows))
            )
    return tuple(views)


def _extension_relationships(adr: Any, *, format_ref: Callable[[str], str]) -> tuple[ExtensionRelationshipView, ...]:
    views: list[ExtensionRelationshipView] = []
    for item in _as_items(field_get(adr, "extension_relationships")):
        mapping = _as_mapping(item)
        if not mapping:
            continue
        relationship_type = _nonempty_text(mapping.get("relationship_type")) or ""
        namespace = relationship_type.split(":", 1)[0] if ":" in relationship_type else "extension"
        verb = relationship_type.split(":", 1)[-1] if relationship_type else ""
        from_id = _nonempty_text(mapping.get("from_entity_id")) or ""
        to_id = _nonempty_text(mapping.get("to_entity_id")) or ""
        from_display = format_ref(from_id) if from_id else ""
        to_display = format_ref(to_id) if to_id else ""
        if not relationship_type and not from_id and not to_id:
            continue
        views.append(
            ExtensionRelationshipView(
                namespace=namespace,
                verb=verb or relationship_type,
                from_display=from_display or from_id,
                to_display=to_display or to_id,
                canonical_path=(
                    f"{from_display or from_id} -[:{relationship_type}]-> {to_display or to_id}"
                    if relationship_type
                    else f"{from_display or from_id} → {to_display or to_id}"
                ),
            )
        )
    return tuple(views)


@implements_adr("ADR-L-0007")
def build_logical_projection(
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
    peer_cards: Iterable[Any],
) -> LogicalProjection:
    """Extract a disposable ADR-L presentation model from authored + compiled state."""
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
    decisions = tuple(
        view
        for decision in _as_items(field_get(adr, "decisions"))
        for view in [_logical_decision_view(decision, format_ref=format_ref)]
        if view is not None
    )
    capabilities = tuple(
        _capability_view(capability, format_ref=format_ref)
        for capability in _as_items(field_get(adr, "capabilities"))
    )
    boundaries = tuple(_boundary_view(boundary) for boundary in _as_items(field_get(adr, "architectural_boundaries")))
    contracts = tuple(
        _contract_view(contract) for contract in _as_items(field_get(adr, "interaction_contracts"))
    )
    invariants = tuple(
        _invariant_view(invariant, format_ref=format_ref)
        for invariant in _as_items(field_get(adr, "invariants"))
    )
    nfrs = tuple(
        view
        for index, item in enumerate(_as_items(field_get(adr, "non_functional_requirements")), start=1)
        for view in [_nfr_view(item, index)]
        if view is not None
    )
    constraints = tuple(
        view
        for index, item in enumerate(_as_items(field_get(adr, "constraints")), start=1)
        for view in [_constraint_view(item, index)]
        if view is not None
    )
    gaps = tuple(
        _gap_view(gap, index)
        for index, gap in enumerate(_as_items(field_get(adr, "gaps")), start=1)
        if _as_mapping(gap) or (isinstance(gap, str) and str(gap).strip())
    )
    decision_index: list[DecisionIndexRow] = []
    if len(decisions) > 1:
        for decision in decisions:
            decision_index.append(
                DecisionIndexRow(
                    alias_id=decision.alias_id,
                    choice=decision.summary.replace("\n", " ").strip() or decision.alias_id,
                    traceability=_traceability_summary(decision.traceability),
                )
            )
    glance_rows: list[LogicalGlanceRow] = [
        LogicalGlanceRow("Logical authority", alias_id),
        LogicalGlanceRow("Status", status),
    ]
    if decisions:
        glance_rows.append(LogicalGlanceRow("Decisions", str(len(decisions))))
    if capabilities:
        glance_rows.append(LogicalGlanceRow("Capabilities", str(len(capabilities))))
    if invariants:
        glance_rows.append(LogicalGlanceRow("Invariants", str(len(invariants))))
    if boundaries:
        glance_rows.append(LogicalGlanceRow("Boundaries", str(len(boundaries))))
    if contracts:
        glance_rows.append(LogicalGlanceRow("Interaction contracts", str(len(contracts))))
    if nfrs:
        glance_rows.append(LogicalGlanceRow("Non-functional requirements", str(len(nfrs))))
    physical = _physical_realization(
        subject_id=subject_id,
        adr=adr,
        relationships=relationship_list,
        entities=entities,
        adr_models_by_id=adr_models_by_id,
        format_ref=format_ref,
    )
    if physical is not None:
        realization_bits = []
        if physical.systems:
            realization_bits.extend(physical.systems)
        if physical.components:
            realization_bits.extend(physical.components)
        if realization_bits:
            glance_rows.append(
                LogicalGlanceRow("Physical realizations", ", ".join(realization_bits))
            )
    owned_ids = {subject_id}
    for entity in entities.values() if hasattr(entities, "values") else []:
        for rel in relationship_list:
            if rel.relationship_type == "declared_in" and rel.to_entity_id == subject_id:
                owned_ids.add(rel.from_entity_id)
    owned_edges = [
        rel
        for rel in relationship_list
        if rel.from_entity_id in owned_ids
        and rel.to_entity_id in owned_ids
        and rel.relationship_type != "declared_in"
    ]
    decision_traceability_graph = _build_semantic_graph(
        edges=owned_edges,
        entities=entities,
        adr_models_by_id=adr_models_by_id,
        format_ref=format_ref,
        title="Decision traceability",
    )
    capability_ids = {
        _text(field_get(cap, "id"))
        for cap in _as_items(field_get(adr, "capabilities"))
        if field_get(cap, "id")
    }
    cap_edges = [
        rel
        for rel in relationship_list
        if rel.relationship_type == "implemented_by" and rel.from_entity_id in capability_ids
    ]
    capability_realization_graph = None
    if len(capability_ids) > 1 and len(cap_edges) > 1:
        capability_realization_graph = _build_semantic_graph(
            edges=cap_edges,
            entities=entities,
            adr_models_by_id=adr_models_by_id,
            format_ref=format_ref,
            title="Capability realization",
        )
    compressed = _compressed_peers(subject_alias=alias_id, peer_cards=peer_cards)
    governance = _governance_sections(adr, format_ref=format_ref)
    lifecycle = _lifecycle_categories(
        adr,
        relationships=relationship_list,
        subject_id=subject_id,
        format_ref=format_ref,
    )
    has_inventory = bool(
        compressed
        or physical is not None
        or decision_traceability_graph
        or lifecycle
    )
    notes = _nonempty_text(field_get(adr, "notes"))
    tags = tuple(_string_list(field_get(adr, "tags")))
    return LogicalProjection(
        identity_rows=identity_rows,
        glance_rows=tuple(glance_rows),
        context=preserve_markdown(field_get(adr, "context") or ""),
        decision_index=tuple(decision_index),
        decisions=decisions,
        capabilities=capabilities,
        boundaries=boundaries,
        interaction_contracts=contracts,
        invariant_index=tuple(_invariant_index_row(inv) for inv in invariants),
        invariants=invariants,
        non_functional_requirements=nfrs,
        constraints=constraints,
        decision_traceability_graph=decision_traceability_graph,
        capability_realization_graph=capability_realization_graph,
        physical_realization=physical,
        governance_sections=governance,
        lifecycle_categories=lifecycle,
        compressed_peers=compressed,
        extension_entities=_extension_entities(adr),
        extension_relationships=_extension_relationships(adr, format_ref=format_ref),
        gaps=gaps,
        notes=notes,
        tags=tags,
        has_human_relationship_inventory=has_inventory,
    )
