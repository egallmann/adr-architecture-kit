"""Disposable human ADR projection context built from compiler semantics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...decorators import implements_adr
from ...integrity import HashInput
from ...scope import ProjectScope
from ..frontend.adr_access import field_get, presentation_id
from ..ir.rel_graph import IRRelationship
from ..pipeline import FrontendBuildResult
from .coverage_registry import assert_current_authoring_coverage
from .neighbor_paths import (
    GOVERNANCE,
    LIFECYCLE_ASSOCIATION,
    select_neighbor_paths,
)
from .projection_paths import (
    human_label_for_adr,
    projection_relative_path,
)

_MERMAID_UNSAFE = re.compile(r'["\\]')
_NODE_SAFE = re.compile(r"[^A-Za-z0-9_]")


@dataclass(frozen=True)
class PresentRef:
    """Resolved or unresolved human reference for projection links."""

    display: str
    link: str | None
    unresolved: bool


@dataclass(frozen=True)
class PeerRelationship:
    """One compiled relationship connecting the ego set to a peer ADR."""

    verb: str
    direction_token: str
    other_endpoint_id: str
    label: str
    from_display: str
    to_display: str
    canonical_path: str


@dataclass
class PeerCard:
    """Human peer card for one related ADR."""

    peer_id: str
    alias_id: str
    title: str
    relationships: list[PeerRelationship]
    context_summary: str
    link: str | None
    use_table: bool


@dataclass(frozen=True)
class NeighborhoodRow:
    verb: str
    from_label: str
    to_label: str
    from_id: str
    to_id: str


@dataclass(frozen=True)
class InternalEntityRow:
    entity_id: str
    alias: str
    entity_type: str
    name: str


@dataclass
class HumanAdrProjectionContext:
    """Disposable human projection model for one ADR."""

    subject: Any
    subject_id: str
    alias_id: str
    title: str
    adr_type: str
    status: str
    peer_cards: list[PeerCard]
    graphs: list[str]
    context: str
    present_refs: dict[str, PresentRef]
    render_dependencies: list[Path | HashInput]
    source_path: Path
    projection_path: Path
    neighborhood_inventory: list[NeighborhoodRow]
    internal_entities: list[InternalEntityRow]
    internal_graph: str | None
    use_internal_structure_table: bool
    primary_architecture_graph: str | None
    show_semantic_inventory: bool
    lifecycle_rows: list[str]
    governance_rows: list[str]
    physical_component: Any | None = None
    physical_system: Any | None = None
    logical: Any | None = None


def context_summary_from_text(text: str | None) -> str:
    """First blank-line paragraph, else first 500 chars at a word boundary."""
    if not text or not str(text).strip():
        return "(no context)"
    normalized = str(text).replace("\r\n", "\n").strip()
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    if paragraphs:
        candidate = paragraphs[0]
    else:
        candidate = normalized
    if len(candidate) <= 500:
        return candidate
    truncated = candidate[:500]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated.rstrip() + "…"


def escape_mermaid_label(text: str) -> str:
    """Escape Mermaid-sensitive characters in display labels."""
    return _MERMAID_UNSAFE.sub(lambda match: "\\" + match.group(0), text)


def mermaid_node_id(entity_id: str) -> str:
    """Stable machine-safe Mermaid node id independent of display labels."""
    cleaned = _NODE_SAFE.sub("_", entity_id)
    if not cleaned:
        cleaned = "node"
    if cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned


def _status_value(adr: Any) -> str:
    status = field_get(adr, "status")
    if hasattr(status, "value"):
        return str(status.value)
    return str(status or "")


def _adr_type_value(adr: Any) -> str:
    adr_type = field_get(adr, "adr_type")
    if hasattr(adr_type, "value"):
        return str(adr_type.value)
    return str(adr_type or "")


def _module_hash_input(path: Path) -> HashInput:
    return HashInput(f"__generator__/modules/{path.name}", path.resolve().read_bytes())


def _relative_markdown_link(from_path: Path, to_path: Path) -> str:
    import os

    return Path(os.path.relpath(Path(to_path), Path(from_path).parent)).as_posix()


@implements_adr("ADR-L-0007")
def build_human_adr_projection_context(
    *,
    adr: Any,
    source_path: Path,
    scope: ProjectScope,
    build_result: FrontendBuildResult,
    template_dir: Path,
    template_name: str,
) -> HumanAdrProjectionContext:
    """Assemble a disposable human projection context from compiler semantics."""
    subject_id = str(field_get(adr, "id"))
    alias_id = str(field_get(adr, "alias_id") or subject_id)
    title = str(field_get(adr, "title") or "")
    projection_path = projection_relative_path(adr)

    assert_current_authoring_coverage(adr)

    entities = build_result.model.entities
    relationships = build_result.model.relationships.values()
    entity_types = {entity.id: entity.entity_type for entity in entities.values()}

    adr_models_by_id: dict[str, Any] = {}
    adr_paths_by_id: dict[str, Path] = {}
    for path_str, artifact in sorted(build_result.model.corpus.artifacts.items()):
        artifact_id = field_get(artifact, "id")
        if not isinstance(artifact_id, str) or not artifact_id:
            continue
        if field_get(artifact, "adr_type") is None:
            continue
        path = Path(path_str)
        if not path.is_absolute():
            path = (scope.root / path).resolve()
        else:
            path = path.resolve()
        adr_models_by_id[artifact_id] = artifact
        adr_paths_by_id[artifact_id] = path
        alias = field_get(artifact, "alias_id")
        if isinstance(alias, str) and alias:
            adr_models_by_id.setdefault(alias, artifact)
            adr_paths_by_id.setdefault(alias, path)

    neighbor_paths = select_neighbor_paths(
        subject_id=subject_id,
        relationships=list(relationships),
        entity_types=entity_types,
    )

    peer_rel_map: dict[str, list[PeerRelationship]] = {}
    peer_path_map: dict[str, list[Any]] = {}
    neighborhood_inventory: list[NeighborhoodRow] = []
    path_relationships: list[IRRelationship] = []
    inventory_keys: set[tuple[str, str, str]] = set()
    for path in neighbor_paths:
        path_relationships.append(path.relationship)
        from_entity = entities.get(path.from_id)
        to_entity = entities.get(path.to_id)
        from_label = presentation_id(from_entity) if from_entity else path.from_id
        to_label = presentation_id(to_entity) if to_entity else path.to_id
        from_display = _endpoint_heading(
            path.from_id, entities=entities, adr_models_by_id=adr_models_by_id
        )
        to_display = _endpoint_heading(
            path.to_id, entities=entities, adr_models_by_id=adr_models_by_id
        )
        canonical_path = f"{from_label} -[:{path.semantic_verb}]-> {to_label}"
        inventory_key = (path.semantic_verb, path.from_id, path.to_id)
        if inventory_key not in inventory_keys:
            inventory_keys.add(inventory_key)
            neighborhood_inventory.append(
                NeighborhoodRow(
                    verb=path.semantic_verb,
                    from_label=from_label,
                    to_label=to_label,
                    from_id=path.from_id,
                    to_id=path.to_id,
                )
            )
        peer_rel_map.setdefault(path.peer_adr_id, []).append(
            PeerRelationship(
                verb=path.semantic_verb,
                direction_token="semantic",
                other_endpoint_id=path.to_id,
                label=canonical_path,
                from_display=from_display,
                to_display=to_display,
                canonical_path=canonical_path,
            )
        )
        peer_path_map.setdefault(path.peer_adr_id, []).append(path)
    neighborhood_inventory.sort(key=lambda row: (row.verb, row.from_id, row.to_id))

    adr_type_early = _adr_type_value(adr)
    if adr_type_early == "physical-system":
        from .projection_editorial import (
            is_internal_ps_member_peer,
            ps_member_component_refs,
            ps_member_owner_ids,
        )

        member_refs = ps_member_component_refs(adr)
        member_owners = ps_member_owner_ids(member_refs, relationships)
        peer_rel_map = {
            peer_id: rels
            for peer_id, rels in peer_rel_map.items()
            if not is_internal_ps_member_peer(
                peer_id=peer_id,
                member_refs=member_refs,
                member_owners=member_owners,
                paths_for_peer=peer_path_map.get(peer_id, []),
            )
        }

    peer_cards: list[PeerCard] = []
    for peer_id, rels in peer_rel_map.items():
        peer_model = adr_models_by_id.get(peer_id)
        peer_entity = entities.get(peer_id)
        peer_alias = ""
        peer_title = ""
        if peer_model is not None:
            peer_alias = str(field_get(peer_model, "alias_id") or peer_id)
            peer_title = str(field_get(peer_model, "title") or "")
            summary = context_summary_from_text(field_get(peer_model, "context"))
        else:
            peer_alias = presentation_id(peer_entity) if peer_entity else peer_id
            peer_title = peer_entity.name if peer_entity else peer_id
            summary = context_summary_from_text(peer_entity.summary if peer_entity else None)
        unique_rels = {
            (item.verb, item.direction_token, item.other_endpoint_id): item for item in rels
        }
        sorted_rels = sorted(
            unique_rels.values(),
            key=lambda item: (item.verb, item.direction_token, item.other_endpoint_id),
        )
        link = None
        if peer_model is not None:
            link = _relative_markdown_link(projection_path, projection_relative_path(peer_model))
        peer_cards.append(
            PeerCard(
                peer_id=peer_id,
                alias_id=peer_alias,
                title=peer_title,
                relationships=sorted_rels,
                context_summary=summary,
                link=link,
                use_table=len(sorted_rels) == 1,
            )
        )
    peer_cards.sort(key=lambda card: (card.alias_id or "", card.peer_id))

    present_refs: dict[str, PresentRef] = {}

    def resolve_present_ref(ref_id: str) -> PresentRef:
        if ref_id in present_refs:
            return present_refs[ref_id]
        model = adr_models_by_id.get(ref_id)
        entity = entities.get(ref_id)
        if model is not None:
            display = human_label_for_adr(model)
            link = _relative_markdown_link(projection_path, projection_relative_path(model))
            present_refs[ref_id] = PresentRef(display=display, link=link, unresolved=False)
            return present_refs[ref_id]
        if entity is not None and entity.entity_type == "adr":
            display = presentation_id(entity)
            present_refs[ref_id] = PresentRef(display=display, link=None, unresolved=True)
            return present_refs[ref_id]
        if entity is not None:
            display = presentation_id(entity)
            present_refs[ref_id] = PresentRef(display=display, link=None, unresolved=False)
            return present_refs[ref_id]
        present_refs[ref_id] = PresentRef(display=ref_id, link=None, unresolved=True)
        return present_refs[ref_id]

    # Seed refs for peer cards and common subject relation fields.
    for card in peer_cards:
        resolve_present_ref(card.peer_id)
    for key in ("related_adrs", "implements_logical", "implements_system", "supersedes"):
        for ref in field_get(adr, key) or []:
            if isinstance(ref, str):
                resolve_present_ref(ref)
    superseded_by = field_get(adr, "superseded_by")
    if isinstance(superseded_by, str) and superseded_by:
        resolve_present_ref(superseded_by)
    for component in field_get(adr, "component_specifications") or []:
        for cap_id in field_get(component, "implements_capabilities") or []:
            if isinstance(cap_id, str) and cap_id:
                resolve_present_ref(cap_id)

    adr_type = _adr_type_value(adr)
    physical_component = None
    physical_system = None
    logical = None
    if adr_type == "physical-component":
        from .physical_component_projection import build_physical_component_projection

        physical_component = build_physical_component_projection(
            adr=adr,
            subject_id=subject_id,
            alias_id=alias_id,
            adr_type=adr_type,
            status=_status_value(adr),
            entities=entities,
            relationships=list(relationships),
            adr_models_by_id=adr_models_by_id,
            resolve_present_ref=resolve_present_ref,
            format_present_ref=format_present_ref,
        )
    elif adr_type == "physical-system":
        from .physical_system_projection import build_physical_system_projection

        physical_system = build_physical_system_projection(
            adr=adr,
            subject_id=subject_id,
            alias_id=alias_id,
            adr_type=adr_type,
            status=_status_value(adr),
            entities=entities,
            relationships=list(relationships),
            adr_models_by_id=adr_models_by_id,
            resolve_present_ref=resolve_present_ref,
            format_present_ref=format_present_ref,
        )
    elif adr_type == "logical":
        from .logical_projection import build_logical_projection

        logical = build_logical_projection(
            adr=adr,
            subject_id=subject_id,
            alias_id=alias_id,
            adr_type=adr_type,
            status=_status_value(adr),
            entities=entities,
            relationships=list(relationships),
            adr_models_by_id=adr_models_by_id,
            resolve_present_ref=resolve_present_ref,
            format_present_ref=format_present_ref,
            peer_cards=peer_cards,
            source_path=source_path,
        )
        for card in peer_cards:
            card.context_summary = ""

    ego = _ego_ids(subject_id, adr) if adr_type == "physical-component" else {subject_id}
    has_human_relationship_inventory = False
    if physical_component is not None:
        has_human_relationship_inventory = bool(
            physical_component.architecture_position.relationship_groups
        )
    elif logical is not None:
        has_human_relationship_inventory = logical.has_human_relationship_inventory

    graphs = _build_mermaid_graphs(
        one_hop=path_relationships,
        relationships=list(relationships),
        entities=entities,
        entity_types=entity_types,
        adr_models_by_id=adr_models_by_id,
        subject_id=subject_id,
        ego_ids=ego,
        has_human_relationship_inventory=has_human_relationship_inventory,
        adr_type=adr_type,
    )

    primary_architecture_graph = None
    if adr_type == "physical-component":
        primary_architecture_graph = _build_pc_primary_architecture_graph(
            ego=ego,
            subject_id=subject_id,
            relationships=list(relationships),
            entities=entities,
            adr_models_by_id=adr_models_by_id,
        )

    internal_entities = [
        InternalEntityRow(
            entity_id=entity.id,
            alias=presentation_id(entity),
            entity_type=entity.entity_type,
            name=_inventory_name(entity.id, entities=entities, adr_models_by_id=adr_models_by_id),
        )
        for entity in entities.values()
        if any(
            rel.relationship_type == "declared_in"
            and rel.from_entity_id == entity.id
            and rel.to_entity_id == subject_id
            for rel in relationships
        )
    ]
    internal_entities.sort(key=lambda row: (row.entity_type, row.alias, row.entity_id))
    use_internal_structure_table = False
    internal_graph = None
    if adr_type == "physical-component":
        owned_component_count = sum(
            1 for row in internal_entities if row.entity_type == "component"
        )
        owned = {row.entity_id for row in internal_entities}
        display_ids = owned | {subject_id}
        structure_edges = _unique_relationships(
            [
                rel
                for rel in relationships
                if rel.relationship_type in _PC_INTERNAL_VERBS
                and rel.from_entity_id in display_ids
                and rel.to_entity_id in display_ids
            ]
        )
        from .projection_editorial import should_render_pc_internal_graph

        if not should_render_pc_internal_graph(
            owned_component_count=owned_component_count,
            structure_edges=structure_edges,
        ):
            use_internal_structure_table = True
        else:
            internal_graph = _build_internal_structure_graph(
                subject_id=subject_id,
                adr_type=adr_type,
                internal_entities=internal_entities,
                relationships=list(relationships),
                entities=entities,
                adr_models_by_id=adr_models_by_id,
            )

    lifecycle_rows = [
        f"{presentation_id(entities.get(rel.from_entity_id) or rel.from_entity_id)} "
        f"-[:{rel.relationship_type}]-> "
        f"{presentation_id(entities.get(rel.to_entity_id) or rel.to_entity_id)}"
        for rel in relationships
        if rel.relationship_type in LIFECYCLE_ASSOCIATION
        and (rel.from_entity_id == subject_id or rel.to_entity_id == subject_id)
    ]
    governance_rows = [
        f"{presentation_id(entities.get(rel.from_entity_id) or rel.from_entity_id)} "
        f"-[:{rel.relationship_type}]-> "
        f"{presentation_id(entities.get(rel.to_entity_id) or rel.to_entity_id)}"
        for rel in relationships
        if rel.relationship_type in GOVERNANCE
        and (rel.from_entity_id == subject_id or rel.to_entity_id == subject_id)
    ]

    dependency_keys: dict[str, Path | HashInput] = {}
    source_resolved = Path(source_path).resolve()
    dependency_keys[str(source_resolved)] = source_resolved
    template_path = Path(template_dir) / template_name
    dependency_keys[f"__generator__/templates/{template_name}"] = HashInput(
        f"__generator__/templates/{template_name}",
        template_path.resolve().read_bytes(),
    )
    this_module = Path(__file__).resolve()
    paths_module = Path(__file__).resolve().parent / "projection_paths.py"
    neighbor_module = Path(__file__).resolve().parent / "neighbor_paths.py"
    coverage_module = Path(__file__).resolve().parent / "coverage_registry" / "__init__.py"
    pc_module = Path(__file__).resolve().parent / "physical_component_projection.py"
    ps_module = Path(__file__).resolve().parent / "physical_system_projection.py"
    logical_module = Path(__file__).resolve().parent / "logical_projection.py"
    editorial_module = Path(__file__).resolve().parent / "projection_editorial.py"
    dependency_keys[f"__generator__/modules/{this_module.name}"] = _module_hash_input(this_module)
    dependency_keys[f"__generator__/modules/{paths_module.name}"] = _module_hash_input(paths_module)
    dependency_keys[f"__generator__/modules/{neighbor_module.name}"] = _module_hash_input(neighbor_module)
    dependency_keys[f"__generator__/modules/{coverage_module.name}"] = _module_hash_input(coverage_module)
    dependency_keys[f"__generator__/modules/{pc_module.name}"] = _module_hash_input(pc_module)
    dependency_keys[f"__generator__/modules/{ps_module.name}"] = _module_hash_input(ps_module)
    dependency_keys[f"__generator__/modules/{logical_module.name}"] = _module_hash_input(
        logical_module
    )
    dependency_keys[f"__generator__/modules/{editorial_module.name}"] = _module_hash_input(
        editorial_module
    )

    inventory_payload = "\n".join(
        f"{row.verb}|{row.from_id}|{row.to_id}" for row in neighborhood_inventory
    ).encode("utf-8")
    dependency_keys["__generator__/neighborhood"] = HashInput(
        "__generator__/neighborhood",
        inventory_payload,
    )
    dependency_keys["__generator__/primary-architecture"] = HashInput(
        "__generator__/primary-architecture",
        (primary_architecture_graph or "").encode("utf-8"),
    )
    dependency_keys["__generator__/internal-structure"] = HashInput(
        "__generator__/internal-structure",
        (internal_graph or "").encode("utf-8"),
    )
    dependency_keys["__generator__/internal-structure-mode"] = HashInput(
        "__generator__/internal-structure-mode",
        str(use_internal_structure_table).encode("utf-8"),
    )
    system_topology = ""
    if physical_system is not None:
        system_topology = "\n".join(physical_system.topology_graphs)
    dependency_keys["__generator__/system-topology"] = HashInput(
        "__generator__/system-topology",
        system_topology.encode("utf-8"),
    )
    for card in peer_cards:
        peer_path = adr_paths_by_id.get(card.peer_id)
        if peer_path is not None:
            dependency_keys[str(peer_path)] = peer_path

    endpoint_ids = {
        endpoint
        for relationship in path_relationships
        for endpoint in (relationship.from_entity_id, relationship.to_entity_id)
    }
    for endpoint in endpoint_ids:
        if endpoint == subject_id:
            continue
        peer_path = adr_paths_by_id.get(endpoint)
        if peer_path is not None:
            dependency_keys[str(peer_path)] = peer_path

    render_dependencies = [dependency_keys[key] for key in sorted(dependency_keys)]

    show_semantic_inventory = not has_human_relationship_inventory
    if adr_type in {"physical-component", "physical-system", "logical"} and has_human_relationship_inventory:
        show_semantic_inventory = False

    return HumanAdrProjectionContext(
        subject=adr,
        subject_id=subject_id,
        alias_id=alias_id,
        title=title,
        adr_type=adr_type,
        status=_status_value(adr),
        peer_cards=peer_cards,
        graphs=graphs,
        context=str(field_get(adr, "context") or ""),
        present_refs=present_refs,
        render_dependencies=render_dependencies,
        source_path=source_resolved,
        projection_path=projection_path,
        neighborhood_inventory=neighborhood_inventory,
        internal_entities=internal_entities,
        internal_graph=internal_graph,
        use_internal_structure_table=use_internal_structure_table,
        primary_architecture_graph=primary_architecture_graph,
        show_semantic_inventory=show_semantic_inventory,
        lifecycle_rows=lifecycle_rows,
        governance_rows=governance_rows,
        physical_component=physical_component,
        physical_system=physical_system,
        logical=logical,
    )


def _endpoint_heading(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    from .physical_component_projection import human_endpoint_heading

    return human_endpoint_heading(
        entity_id, entities=entities, adr_models_by_id=adr_models_by_id
    )


def _inventory_name(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    from .physical_component_projection import human_inventory_name

    return human_inventory_name(
        entity_id, entities=entities, adr_models_by_id=adr_models_by_id
    )


def _entity_label(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    from .physical_component_projection import human_node_label

    return human_node_label(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)


_LOGICAL_INTERNAL_VERBS = frozenset(
    {
        "declared_in",
        "enables",
        "enabled_by",
        "enforces",
        "governs",
        "implemented_by",
        "refines",
    }
)
_PC_INTERNAL_VERBS = frozenset({"declared_in", "provides_interface"})
_LOGICAL_TYPE_ORDER = ("capability", "decision", "invariant", "constraint", "gap")
_PC_TYPE_ORDER = ("component", "interface", "implementation_decision")


def _build_internal_structure_graph(
    *,
    subject_id: str,
    adr_type: str,
    internal_entities: list[InternalEntityRow],
    relationships: list[IRRelationship],
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str | None:
    if not internal_entities:
        return None
    if adr_type == "physical-component":
        verbs = _PC_INTERNAL_VERBS
        type_rank = _PC_TYPE_ORDER
    else:
        verbs = _LOGICAL_INTERNAL_VERBS
        type_rank = _LOGICAL_TYPE_ORDER
    owned = {row.entity_id for row in internal_entities}
    display_ids = owned | {subject_id}
    structure_edges = _unique_relationships(
        [
            rel
            for rel in relationships
            if rel.relationship_type in verbs
            and rel.from_entity_id in display_ids
            and rel.to_entity_id in display_ids
        ]
    )
    grouped: dict[str, list[InternalEntityRow]] = {}
    for row in internal_entities:
        grouped.setdefault(row.entity_type, []).append(row)
    type_order = [item for item in type_rank if item in grouped]
    type_order.extend(sorted(key for key in grouped if key not in type_rank))

    lines = ["flowchart TB"]
    subject_node = mermaid_node_id(subject_id)
    subject_label = escape_mermaid_label(
        _entity_label(subject_id, entities=entities, adr_models_by_id=adr_models_by_id)
    )
    lines.append(f'  {subject_node}["{subject_label}"]')
    for entity_type in type_order:
        subgraph_id = mermaid_node_id(f"sg_{entity_type}")
        lines.append(f'  subgraph {subgraph_id}["{escape_mermaid_label(entity_type)}"]')
        for row in grouped[entity_type]:
            node = mermaid_node_id(row.entity_id)
            label = escape_mermaid_label(
                _entity_label(row.entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
            )
            lines.append(f'    {node}["{label}"]')
        lines.append("  end")
    for relationship in structure_edges:
        src = mermaid_node_id(relationship.from_entity_id)
        dst = mermaid_node_id(relationship.to_entity_id)
        verb = escape_mermaid_label(relationship.relationship_type)
        lines.append(f'  {src} -->|"{verb}"| {dst}')
    lines.append("")
    return "\n".join(lines)


def _unique_relationships(edges: list[IRRelationship]) -> list[IRRelationship]:
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


def _declared_in_bridges(
    *,
    endpoints: set[str],
    relationships: list[IRRelationship],
    entity_types: dict[str, str],
) -> list[IRRelationship]:
    non_adr_endpoints = {
        endpoint for endpoint in endpoints if entity_types.get(endpoint) != "adr"
    }
    bridges: list[IRRelationship] = []
    for relationship in relationships:
        if relationship.relationship_type != "declared_in":
            continue
        if entity_types.get(relationship.to_entity_id) != "adr":
            continue
        if relationship.from_entity_id in non_adr_endpoints:
            bridges.append(relationship)
    return _unique_relationships(bridges)


def _ego_ids(subject_id: str, adr: Any) -> set[str]:
    from .physical_component_projection import _as_items

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


def _build_pc_primary_architecture_graph(
    *,
    ego: set[str],
    subject_id: str,
    relationships: list[IRRelationship],
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str | None:
    from .projection_editorial import select_pc_primary_architecture_edges

    edges = select_pc_primary_architecture_edges(ego=ego, relationships=relationships)
    if not edges:
        return None
    owned_components = {
        entity_id
        for entity_id in ego
        if entities.get(entity_id) is not None
        and getattr(entities.get(entity_id), "entity_type", None) == "component"
    }
    if not owned_components and len(ego) <= 1:
        return None
    local_nodes = sorted(
        {
            endpoint
            for relationship in edges
            for endpoint in (relationship.from_entity_id, relationship.to_entity_id)
        }
    )
    lines = ["flowchart LR"]
    if owned_components:
        lines.append('  subgraph subject["Owned by this ADR"]')
        for entity_id in sorted(owned_components):
            if entity_id not in local_nodes:
                continue
            node = mermaid_node_id(entity_id)
            label = escape_mermaid_label(
                _entity_label(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
            )
            lines.append(f'    {node}["{label}"]')
        lines.append("  end")
    for entity_id in local_nodes:
        if entity_id in owned_components:
            continue
        node = mermaid_node_id(entity_id)
        label = escape_mermaid_label(
            _entity_label(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
        )
        lines.append(f'  {node}["{label}"]')
    for relationship in edges:
        src = mermaid_node_id(relationship.from_entity_id)
        dst = mermaid_node_id(relationship.to_entity_id)
        verb = escape_mermaid_label(relationship.relationship_type)
        lines.append(f'  {src} -->|"{verb}"| {dst}')
    lines.append("")
    return "\n".join(lines)


def _build_mermaid_graphs(
    *,
    one_hop: list[IRRelationship],
    relationships: list[IRRelationship],
    entities: Any,
    entity_types: dict[str, str],
    adr_models_by_id: dict[str, Any],
    subject_id: str,
    ego_ids: set[str],
    has_human_relationship_inventory: bool,
    adr_type: str,
) -> list[str]:
    from .projection_editorial import filter_neighborhood_graph_edges

    semantic_edges = filter_neighborhood_graph_edges(
        one_hop,
        subject_id=subject_id,
        ego_ids=ego_ids,
        has_human_relationship_inventory=has_human_relationship_inventory,
    )
    semantic_edges = _unique_relationships(semantic_edges)
    if not semantic_edges:
        return []

    def render_edge_group(edges: list[IRRelationship]) -> str:
        endpoints = {
            endpoint
            for relationship in edges
            for endpoint in (relationship.from_entity_id, relationship.to_entity_id)
        }
        display_edges = _unique_relationships(
            [
                *edges,
                *_declared_in_bridges(
                    endpoints=endpoints,
                    relationships=relationships,
                    entity_types=entity_types,
                ),
            ]
        )
        local_nodes = sorted(
            {
                endpoint
                for relationship in display_edges
                for endpoint in (relationship.from_entity_id, relationship.to_entity_id)
            }
        )
        lines = ["flowchart LR"]
        for entity_id in local_nodes:
            node = mermaid_node_id(entity_id)
            label = escape_mermaid_label(
                _entity_label(entity_id, entities=entities, adr_models_by_id=adr_models_by_id)
            )
            lines.append(f'  {node}["{label}"]')
        for relationship in display_edges:
            src = mermaid_node_id(relationship.from_entity_id)
            dst = mermaid_node_id(relationship.to_entity_id)
            verb = escape_mermaid_label(relationship.relationship_type)
            lines.append(f'  {src} -->|"{verb}"| {dst}')
        lines.append("")
        return "\n".join(lines)

    by_verb: dict[str, list[IRRelationship]] = {}
    for relationship in semantic_edges:
        by_verb.setdefault(relationship.relationship_type, []).append(relationship)

    graphs = [render_edge_group(by_verb[verb]) for verb in sorted(by_verb)]
    if adr_type in {"physical-component", "physical-system", "logical"}:
        return [graph for graph in graphs if graph.strip()]
    return graphs


def format_present_ref(ref: PresentRef) -> str:
    """Render a present_ref for markdown body text."""
    if ref.link and not ref.unresolved:
        return f"[{ref.display}]({ref.link})"
    if ref.unresolved:
        return f"{ref.display} (unresolved)"
    return ref.display
