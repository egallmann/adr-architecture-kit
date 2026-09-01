"""Editorial regression tests for Projection v3 human rendering."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.compiler.backend.markdown_rendering import emit_markdown_artifacts
from adr_kit.compiler.frontend.builder import ArchModelBuilder
from adr_kit.parser import ADRParser
from adr_kit.scope import ProjectScopeResolver

ROOT = Path(__file__).resolve().parents[1]
PC_FIXTURE = ROOT / "tests" / "fixtures" / "adr-pc-human-projection"
PS_FIXTURE = ROOT / "tests" / "fixtures" / "adr-ps-human-projection"
PRODUCTION_RENDERER_PATHS = (
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "human_adr_projection.py",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "physical_component_projection.py",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "physical_system_projection.py",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "projection_editorial.py",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical-component-v3.md.jinja2",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical-system-v3.md.jinja2",
)


def _body(artifacts, folder: str, alias: str) -> str:
    match = next(
        item
        for item in artifacts
        if folder in item.path.as_posix() and alias in item.path.as_posix()
    )
    return match.content.decode("utf-8").split("-->", 1)[-1]


def _compile(workspace: Path):
    parser = ADRParser()
    scope = ProjectScopeResolver(explicit_scope=workspace).resolve()
    build = ArchModelBuilder().build_from_scope(scope)
    return emit_markdown_artifacts(parser=parser, scope=scope, build_result=build)


def test_no_duplicate_raw_inventory_for_pc_fixture(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PC_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-component", "ADR-PC-9001")
    assert "### Component Relationships" in content
    assert "### Semantic architecture inventory" not in content


def test_no_peer_context_duplication_for_pc_fixture(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PC_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-component", "ADR-PC-9001")
    assert "**Peer context:**" not in content
    assert "PURPOSE_PEER" not in content or "Peer Component" in content


def test_simple_ps_topology_omits_one_node_graph(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PS_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-system", "ADR-PS-9102")
    assert "### System Topology" not in content
    assert "COMP-9107 — Optional Widget" in content


def test_nontrivial_ps_topology_retains_graph_and_table(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PS_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-system", "ADR-PS-9101")
    assert "### System Topology" in content
    assert "### Component Interactions" in content
    for verb in ("depends_on", "calls", "publishes_to", "subscribes_to", "reads_from", "writes_to"):
        assert f'|"{verb}"|' in content


def test_simple_pc_internal_structure_uses_table_not_star_graph(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PC_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-component", "ADR-PC-9002")
    internal = content.split("## Internal Structure", 1)[1]
    assert "| Kind | Entity |" in internal
    assert "```mermaid" not in internal.split("## Neighbor Relationships", 1)[0]


def test_nontrivial_pc_internal_structure_retains_graph(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PC_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-component", "ADR-PC-9001")
    internal = content.split("## Internal Structure", 1)[1].split("## Architecture Neighborhood", 1)[0]
    assert "```mermaid" in internal


def test_change_safety_has_no_nested_bullets(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PC_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-component", "ADR-PC-9001")
    change = content.split("## Change Safety", 1)[1].split("## Context", 1)[0]
    assert "- - " not in change
    assert "**Verification**" in change


def test_decision_heading_not_duplicated(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PC_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-component", "ADR-PC-9001")
    block = content.split("### IMPL-9001 — Choose a deterministic alpha runtime", 1)[1]
    assert "**Decision:**" not in block.split("**Rationale:**", 1)[0]


def test_markdown_list_fidelity_in_interface_spec(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PC_FIXTURE, workspace)
    artifacts = _compile(workspace)
    content = _body(artifacts, "physical-component", "ADR-PC-9001")
    spec = content.split("### IFACE-9001 — CLI", 1)[1].split("### IFACE-9002", 1)[0]
    assert "- adr alpha\n" in spec
    assert "- adr beta\n" in spec


def test_production_renderer_has_no_current_corpus_special_cases() -> None:
    banned = (
        "ADR-PC-0001",
        "ADR-PC-0008",
        "ADR-PS-0001",
        "ADR-PS-0002",
        "COMP-0012",
        "SYS-0002",
        "Compiler Pipeline and Driver",
        "ADR Kit Authoring Compiler and Validation System",
    )
    for path in PRODUCTION_RENDERER_PATHS:
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} contains corpus special case {token}"


def test_kit_corpus_pc_ps_editorial_expectations() -> None:
    result = compile_architecture(
        CompilationRequest(project_root=ROOT, artifact_groups=("markdown",), write=False)
    )
    assert result.success, result.diagnostics

    def corpus(alias: str, folder: str) -> str:
        match = next(
            item
            for item in result.artifacts
            if folder in item.relative_path.replace("\\", "/") and alias in item.relative_path
        )
        return match.content.decode("utf-8").split("-->", 1)[-1]

    pc3 = corpus("ADR-PC-0003", "physical-component")
    assert "## Architecture at a Glance" in pc3
    assert "## Change Safety" in pc3
    assert "### Semantic architecture inventory" not in pc3
    assert "**Peer context:**" not in pc3
    assert "`COMP-0012 -[:depends_on]-> COMP-0011`" in pc3
    assert "Must Remain True" not in pc3

    ps1 = corpus("ADR-PS-0001", "physical-system")
    assert "### System Topology" not in ps1
    assert "## Architecture at a Glance" in ps1
    assert "Topology handles are local authoring labels" not in ps1.split("## Context", 1)[0]

    ps2 = corpus("ADR-PS-0002", "physical-system")
    assert "### System Topology" in ps2
    assert "### Component Interactions" in ps2
    assert "**Peer context:**" not in ps2
    assert re.search(r"ADR-PC-000[2345].*Peer context", ps2) is None


def test_second_generation_is_byte_identical(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(PC_FIXTURE, workspace)
    first = _compile(workspace)
    second = _compile(workspace)
    assert _body(first, "physical-component", "ADR-PC-9001") == _body(
        second, "physical-component", "ADR-PC-9001"
    )
