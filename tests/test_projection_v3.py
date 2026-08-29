"""Coverage registry and Projection v3 canaries."""

from __future__ import annotations

from pathlib import Path

from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.cli.main import generate_system_overview
from adr_kit.compiler.backend.coverage_registry import (
    DISPOSITIONS,
    collect_schema_field_pointers,
    disposition_for,
)
from adr_kit.compiler.backend.neighbor_paths import (
    LIFECYCLE_ASSOCIATION,
    SEMANTIC_ARCHITECTURE,
    STRUCTURAL_BRIDGES,
    select_neighbor_paths,
)
from adr_kit.compiler.ir.rel_graph import IRRelationship

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_VERBS = ("depends_on", "calls", "publishes_to", "subscribes_to", "reads_from", "writes_to")


def _artifact_text(artifacts, *, folder: str, alias: str) -> str:
    match = next(
        item
        for item in artifacts
        if folder in item.relative_path.replace("\\", "/") and alias in item.relative_path
    )
    return match.content.decode("utf-8")


def test_coverage_registry_covers_authoring_v15_schema_fields() -> None:
    for adr_type in ("logical", "physical-system", "physical-component"):
        pointers = collect_schema_field_pointers(adr_type)
        assert pointers
        for pointer in pointers:
            disposition = disposition_for(adr_type=adr_type, pointer=pointer)
            assert disposition in DISPOSITIONS
            assert disposition != "UNCLASSIFIED"
    assert disposition_for(adr_type="physical-component", pointer="/component_topology") == (
        "UNSUPPORTED_OR_STALE"
    )
    assert disposition_for(adr_type="logical", pointer="/domains") == "RENDER_DETAIL"
    assert disposition_for(adr_type="logical", pointer="/notes") == "RENDER_DETAIL"
    assert "provides_interface" in SEMANTIC_ARCHITECTURE
    assert "provides_interface" not in STRUCTURAL_BRIDGES
    for verb in ("binds_substrate", "binds_rule", "expects_evidence"):
        assert verb not in SEMANTIC_ARCHITECTURE
        assert verb not in STRUCTURAL_BRIDGES
    for verb in LIFECYCLE_ASSOCIATION:
        assert verb not in SEMANTIC_ARCHITECTURE


def test_neighbor_path_uses_incoming_semantic_edge_and_not_lifecycle() -> None:
    adr_a = "aaaaaaaa-aaaa-7aaa-8aaa-aaaaaaaaaaaa"
    adr_b = "bbbbbbbb-bbbb-7bbb-8bbb-bbbbbbbbbbbb"
    comp_x = "11111111-1111-7111-8111-111111111111"
    comp_y = "22222222-2222-7222-8222-222222222222"
    relationships = [
        IRRelationship(
            relationship_type="declared_in",
            from_entity_id=comp_x,
            to_entity_id=adr_a,
            canonical_source_ref=adr_a,
        ),
        IRRelationship(
            relationship_type="declared_in",
            from_entity_id=comp_y,
            to_entity_id=adr_b,
            canonical_source_ref=adr_b,
        ),
        IRRelationship(
            relationship_type="depends_on",
            from_entity_id=comp_y,
            to_entity_id=comp_x,
            canonical_source_ref=adr_b,
        ),
        IRRelationship(
            relationship_type="supersedes",
            from_entity_id=adr_b,
            to_entity_id=adr_a,
            canonical_source_ref=adr_b,
        ),
    ]
    entity_types = {
        adr_a: "adr",
        adr_b: "adr",
        comp_x: "component",
        comp_y: "component",
    }
    paths = select_neighbor_paths(
        subject_id=adr_a,
        relationships=relationships,
        entity_types=entity_types,
    )
    assert len(paths) == 1
    assert paths[0].peer_adr_id == adr_b
    assert paths[0].semantic_verb == "depends_on"
    assert paths[0].from_id == comp_y
    assert paths[0].to_id == comp_x


def test_neighbor_path_adr_to_adr_implements_logical_does_not_union_topology() -> None:
    logical = "aaaaaaaa-aaaa-7aaa-8aaa-aaaaaaaaaaaa"
    physical = "bbbbbbbb-bbbb-7bbb-8bbb-bbbbbbbbbbbb"
    peer_pc = "cccccccc-cccc-7ccc-8ccc-cccccccccccc"
    system = "33333333-3333-7333-8333-333333333333"
    member = "44444444-4444-7444-8444-444444444444"
    relationships = [
        IRRelationship(
            relationship_type="declared_in",
            from_entity_id=system,
            to_entity_id=physical,
            canonical_source_ref=physical,
        ),
        IRRelationship(
            relationship_type="declared_in",
            from_entity_id=member,
            to_entity_id=peer_pc,
            canonical_source_ref=peer_pc,
        ),
        IRRelationship(
            relationship_type="composed_of",
            from_entity_id=system,
            to_entity_id=member,
            canonical_source_ref=physical,
        ),
        IRRelationship(
            relationship_type="implements_logical",
            from_entity_id=physical,
            to_entity_id=logical,
            canonical_source_ref=physical,
        ),
    ]
    entity_types = {
        logical: "adr",
        physical: "adr",
        peer_pc: "adr",
        system: "system",
        member: "component",
    }
    paths = select_neighbor_paths(
        subject_id=logical,
        relationships=relationships,
        entity_types=entity_types,
    )
    assert [path.peer_adr_id for path in paths] == [physical]
    assert paths[0].semantic_verb == "implements_logical"
    assert paths[0].from_id == physical
    assert paths[0].to_id == logical


def test_generate_system_overview_cli_is_targeted_not_recursive() -> None:
    names = {param.name for param in generate_system_overview.params}
    assert "scope" in names
    assert "recursive" not in names


def test_projection_v3_canaries_for_kit_corpus() -> None:
    result = compile_architecture(
        CompilationRequest(project_root=ROOT, artifact_groups=("markdown",), write=False)
    )
    assert result.success, result.diagnostics
    paths = {item.relative_path.replace("\\", "/") for item in result.artifacts}
    assert any(path.endswith("SYSTEM-OVERVIEW.md") or path == "SYSTEM-OVERVIEW.md" for path in paths)
    overview = next(item for item in result.artifacts if item.artifact_id == "system-overview")
    assert overview.group == "markdown"

    ps1 = _artifact_text(result.artifacts, folder="physical-system", alias="ADR-PS-0001")
    assert "COMP-0010" in ps1
    assert "TOPO-0001" in ps1
    assert "Canonical ADR artifacts" in ps1
    assert "Semantic architecture inventory" in ps1
    for verb in TOPOLOGY_VERBS:
        assert f"`{verb}`:" not in ps1
    assert "ADR-P-" not in ps1 or "retired" in ps1.lower()

    ps2 = _artifact_text(result.artifacts, folder="physical-system", alias="ADR-PS-0002")
    assert "COMP-0011" in ps2
    assert "COMP-0012" in ps2
    assert "COMP-0013" in ps2
    assert "COMP-0014" in ps2
    assert "`depends_on`: COMP-0012 → COMP-0011" in ps2
    assert "`depends_on`: COMP-0013 → COMP-0012" in ps2
    assert "`depends_on`: COMP-0014 → COMP-0012" in ps2
    assert "ADR-PS-0002 depends_on ADR-" not in ps2

    pc3 = _artifact_text(result.artifacts, folder="physical-component", alias="ADR-PC-0003")
    assert "`depends_on`: COMP-0012 → COMP-0011" in pc3
    assert "COMP-0013" in pc3
    assert "COMP-0014" in pc3
    assert "ADR-PC-0003 depends_on ADR-" not in pc3

    pc4 = _artifact_text(result.artifacts, folder="physical-component", alias="ADR-PC-0004")
    assert "`depends_on`: COMP-0013 → COMP-0012" in pc4
    assert "ADR-PC-0003" in pc4
    assert "ADR-PC-0004 depends_on ADR-PC-0003" not in pc4

    pc5 = _artifact_text(result.artifacts, folder="physical-component", alias="ADR-PC-0005")
    assert "`depends_on`: COMP-0014 → COMP-0012" in pc5

    l13 = _artifact_text(result.artifacts, folder="logical", alias="ADR-L-0013")
    assert "`implements_logical`" in l13
    assert "binds_substrate" not in l13.split("## Governance")[0]
    assert l13.count("`implements_logical`: ADR-PS-0002 → ADR-L-0013") == 1
    implemented_by_graph = l13.split("```mermaid")[1].split("```")[0]
    assert "ADR-L-0013" in implemented_by_graph
    assert '|"declared_in"|' in implemented_by_graph
    assert '|"implemented_by"|' in implemented_by_graph

    l1 = _artifact_text(result.artifacts, folder="logical", alias="ADR-L-0001")
    assert l1.count("`implements_logical`: ADR-PS-0002 → ADR-L-0001") == 1
    assert "peer ADR-PC-0002" not in l1

    ps1_blocks = [block.split("```", 1)[0] for block in ps1.split("```mermaid")[1:]]
    impl_by = next(block for block in ps1_blocks if '|"implemented_by"|' in block)
    impl_logical = next(block for block in ps1_blocks if '|"implements_logical"|' in block)
    provides = next(block for block in ps1_blocks if '|"provides_interface"|' in block)
    assert '["ADR-PS-0001"]' not in impl_by
    assert '["ADR-PS-0001"]' not in provides
    assert "ADR-PS-0001" in impl_logical

    l3 = _artifact_text(result.artifacts, folder="logical", alias="ADR-L-0003")
    assert "```mermaid" not in l3.split("## Internal Structure")[0]
    assert "No grammatical peer neighborhood" in l3
    l8 = _artifact_text(result.artifacts, folder="logical", alias="ADR-L-0008")
    internal = l8.split("## Internal Structure", 1)[1]
    assert "```mermaid" in internal
    assert "CAP-0015" in internal
    assert "DEC-0013" in internal
    assert '|"declared_in"|' in internal

    pc1 = _artifact_text(result.artifacts, folder="physical-component", alias="ADR-PC-0001")
    pc1_internal = pc1.split("## Internal Structure", 1)[1]
    assert "```mermaid" in pc1_internal
    assert "COMP-0010" in pc1_internal
    assert "IFACE-0011" in pc1_internal
    assert '|"provides_interface"|' in pc1_internal
    assert '|"declared_in"|' in pc1_internal
    assert "depends_on" not in pc1_internal.split("## Technology Stack")[0]

    ps1_internal = ps1.split("## Internal Structure", 1)[1] if "## Internal Structure" in ps1 else ""
    assert "```mermaid" not in ps1_internal

    assert any("ADR-L-0025" in item.relative_path for item in result.artifacts)
    assert any("ADR-PC-0008" in item.relative_path for item in result.artifacts)
    assert not any("/physical/ADR-P-" in item.relative_path.replace("\\", "/") for item in result.artifacts)
    projection_markdown = [
        item
        for item in result.artifacts
        if "adr-projection" in item.relative_path.replace("\\", "/")
        and item.relative_path.replace("\\", "/").endswith(".md")
    ]
    assert projection_markdown
    assert all("generator_version: 3" in item.content.decode("utf-8") for item in projection_markdown)
