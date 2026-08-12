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
from .projection_paths import (
    human_label_for_adr,
    projection_relative_path,
)

_MERMAID_UNSAFE = re.compile(r'["\\]')
_NODE_SAFE = re.compile(r"[^A-Za-z0-9_]")
_MAX_GRAPH_NODES = 40


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


@dataclass
class PeerCard:
    """Human peer card for one related ADR."""

    peer_id: str
    alias_id: str
    title: str
    relationships: list[PeerRelationship]
    context_summary: str
    link: str | None


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

    entities = build_result.model.entities
    relationships = build_result.model.relationships.values()

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

    ego_ids = {subject_id}
    for relationship in relationships:
        if (
            relationship.relationship_type == "declared_in"
            and relationship.to_entity_id == subject_id
        ):
            ego_ids.add(relationship.from_entity_id)

    one_hop: list[IRRelationship] = []
    for relationship in relationships:
        if relationship.from_entity_id in ego_ids or relationship.to_entity_id in ego_ids:
            one_hop.append(relationship)

    peer_rel_map: dict[str, list[PeerRelationship]] = {}
    for relationship in one_hop:
        for endpoint in (relationship.from_entity_id, relationship.to_entity_id):
            if endpoint in ego_ids:
                continue
            entity = entities.get(endpoint)
            if entity is None or entity.entity_type != "adr":
                continue
            direction = "out" if relationship.from_entity_id in ego_ids else "in"
            if direction == "out":
                label = f"this ADR -[:{relationship.relationship_type}]-> {presentation_id(entity)}"
            else:
                label = f"{presentation_id(entity)} -[:{relationship.relationship_type}]-> this ADR"
            peer_rel_map.setdefault(endpoint, []).append(
                PeerRelationship(
                    verb=relationship.relationship_type,
                    direction_token=direction,
                    other_endpoint_id=endpoint,
                    label=label,
                )
            )

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

    graphs = _build_mermaid_graphs(
        one_hop=one_hop,
        entities=entities,
        adr_models_by_id=adr_models_by_id,
        subject_id=subject_id,
    )

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
    dependency_keys[f"__generator__/modules/{this_module.name}"] = _module_hash_input(this_module)
    dependency_keys[f"__generator__/modules/{paths_module.name}"] = _module_hash_input(paths_module)

    for card in peer_cards:
        peer_path = adr_paths_by_id.get(card.peer_id)
        if peer_path is not None:
            dependency_keys[str(peer_path)] = peer_path

    endpoint_ids = {
        endpoint
        for relationship in one_hop
        for endpoint in (relationship.from_entity_id, relationship.to_entity_id)
    }
    for endpoint in endpoint_ids:
        if endpoint == subject_id:
            continue
        peer_path = adr_paths_by_id.get(endpoint)
        if peer_path is not None:
            dependency_keys[str(peer_path)] = peer_path

    render_dependencies = [dependency_keys[key] for key in sorted(dependency_keys)]

    return HumanAdrProjectionContext(
        subject=adr,
        subject_id=subject_id,
        alias_id=alias_id,
        title=title,
        adr_type=_adr_type_value(adr),
        status=_status_value(adr),
        peer_cards=peer_cards,
        graphs=graphs,
        context=str(field_get(adr, "context") or ""),
        present_refs=present_refs,
        render_dependencies=render_dependencies,
        source_path=source_resolved,
        projection_path=projection_path,
    )


def _entity_label(
    entity_id: str,
    *,
    entities: Any,
    adr_models_by_id: dict[str, Any],
) -> str:
    model = adr_models_by_id.get(entity_id)
    if model is not None:
        return human_label_for_adr(model)
    entity = entities.get(entity_id)
    if entity is not None:
        alias = entity.metadata.get("alias_id") if isinstance(entity.metadata, dict) else None
        if isinstance(alias, str) and alias:
            return alias
        return presentation_id(entity)
    if len(entity_id) > 12:
        return entity_id[:8]
    return entity_id


def _build_mermaid_graphs(
    *,
    one_hop: list[IRRelationship],
    entities: Any,
    adr_models_by_id: dict[str, Any],
    subject_id: str,
) -> list[str]:
    if not one_hop:
        subject_node = mermaid_node_id(subject_id)
        subject_label = escape_mermaid_label(
            _entity_label(subject_id, entities=entities, adr_models_by_id=adr_models_by_id)
        )
        return [f'flowchart LR\n  {subject_node}["{subject_label}"]\n']

    sorted_edges = sorted(
        one_hop,
        key=lambda item: (
            item.relationship_type,
            item.from_entity_id,
            item.to_entity_id,
            item.relationship_id,
        ),
    )
    node_ids = sorted(
        {
            endpoint
            for relationship in sorted_edges
            for endpoint in (relationship.from_entity_id, relationship.to_entity_id)
        }
    )

    def render_edge_group(edges: list[IRRelationship]) -> str:
        local_nodes = sorted(
            {
                endpoint
                for relationship in edges
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
        for relationship in edges:
            src = mermaid_node_id(relationship.from_entity_id)
            dst = mermaid_node_id(relationship.to_entity_id)
            verb = escape_mermaid_label(relationship.relationship_type)
            lines.append(f'  {src} -->|"{verb}"| {dst}')
        lines.append("")
        return "\n".join(lines)

    if len(node_ids) <= _MAX_GRAPH_NODES:
        return [render_edge_group(sorted_edges)]

    by_verb: dict[str, list[IRRelationship]] = {}
    for relationship in sorted_edges:
        by_verb.setdefault(relationship.relationship_type, []).append(relationship)

    graphs: list[str] = []
    for verb in sorted(by_verb):
        edges = by_verb[verb]
        verb_nodes = {
            endpoint
            for relationship in edges
            for endpoint in (relationship.from_entity_id, relationship.to_entity_id)
        }
        if len(verb_nodes) <= _MAX_GRAPH_NODES:
            graphs.append(render_edge_group(edges))
            continue
        # Chunk by sorted edges while never omitting.
        chunk: list[IRRelationship] = []
        chunk_nodes: set[str] = set()
        for relationship in edges:
            endpoints = {relationship.from_entity_id, relationship.to_entity_id}
            projected = chunk_nodes | endpoints
            if chunk and len(projected) > _MAX_GRAPH_NODES:
                graphs.append(render_edge_group(chunk))
                chunk = []
                chunk_nodes = set()
            chunk.append(relationship)
            chunk_nodes |= endpoints
        if chunk:
            graphs.append(render_edge_group(chunk))
    return graphs


def format_present_ref(ref: PresentRef) -> str:
    """Render a present_ref for markdown body text."""
    if ref.link and not ref.unresolved:
        return f"[{ref.display}]({ref.link})"
    if ref.unresolved:
        return f"{ref.display} (unresolved)"
    return ref.display
