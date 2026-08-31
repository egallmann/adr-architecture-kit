"""Generic ADR-PS human projection quality tests.

Production renderer must operate on adr_type and authored fields, never
ADR-PS-0001/0002 aliases. The synthetic fixture is the generic proof;
kit corpus documents are canaries only.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.compiler.backend.coverage_registry import (
    DISPOSITIONS,
    collect_schema_field_pointers,
    disposition_for,
)
from adr_kit.compiler.backend.markdown_rendering import (
    MARKDOWN_GENERATOR_IDENTITY,
    emit_markdown_artifacts,
)
from adr_kit.compiler.frontend.builder import ArchModelBuilder
from adr_kit.integrity.core import parse_integrity_header
from adr_kit.parser import ADRParser
from adr_kit.scope import ProjectScopeResolver

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "adr-ps-human-projection"
PRODUCTION_RENDERER_PATHS = (
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "human_adr_projection.py",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "physical_system_projection.py",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical-system-v3.md.jinja2",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "coverage_registry" / "__init__.py",
)
UUID_HYPHEN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
TOPOLOGY_VERBS = (
    "depends_on",
    "calls",
    "publishes_to",
    "subscribes_to",
    "reads_from",
    "writes_to",
)


def _copy_fixture(tmp_path: Path) -> Path:
    dest = tmp_path / "workspace"
    shutil.copytree(FIXTURE, dest)
    return dest


def _ps_body(artifacts, alias: str) -> str:
    match = next(
        item
        for item in artifacts
        if "physical-system" in item.path.as_posix() and alias in item.path.as_posix()
    )
    return match.content.decode("utf-8")


def _compile_fixture(workspace: Path):
    parser = ADRParser()
    scope = ProjectScopeResolver(explicit_scope=workspace).resolve()
    build = ArchModelBuilder().build_from_scope(scope)
    artifacts = emit_markdown_artifacts(parser=parser, scope=scope, build_result=build)
    return artifacts, scope, build


def test_coverage_registry_ps_identity_and_system_fields() -> None:
    pointers = collect_schema_field_pointers("physical-system")
    for pointer in pointers:
        disposition = disposition_for(adr_type="physical-system", pointer=pointer)
        assert disposition in DISPOSITIONS
        assert disposition != "UNCLASSIFIED"
    assert disposition_for(adr_type="physical-system", pointer="/schema_version") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-system", pointer="/created_date") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-system", pointer="/authors") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-system", pointer="/domains") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-system", pointer="/tags") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-system", pointer="/technologies") == (
        "INTENTIONALLY_NOT_RENDERED"
    )
    assert disposition_for(adr_type="physical-system", pointer="/component_topology") == (
        "PROJECTION_CONTROL_INPUT"
    )
    assert disposition_for(
        adr_type="physical-system", pointer="/component_topology/components/id"
    ) == "PROJECTION_CONTROL_INPUT"
    assert disposition_for(
        adr_type="physical-system", pointer="/component_topology/components/component_ref"
    ) == "RENDER_AS_RELATIONSHIP"
    assert disposition_for(
        adr_type="physical-system", pointer="/component_topology/components/purpose"
    ) == "RENDER_PRIMARY"
    assert disposition_for(
        adr_type="physical-system", pointer="/component_topology/relationships"
    ) == "RENDER_AS_RELATIONSHIP"
    assert disposition_for(adr_type="physical-system", pointer="/data_flows") == "RENDER_DETAIL"
    assert disposition_for(adr_type="physical-system", pointer="/data_flows/path") == "RENDER_DETAIL"
    assert disposition_for(adr_type="physical-system", pointer="/integration_patterns") == (
        "RENDER_DETAIL"
    )
    assert disposition_for(adr_type="physical-system", pointer="/references_components") == (
        "UNSUPPORTED_OR_STALE"
    )
    assert disposition_for(adr_type="physical-system", pointer="/operational_requirements") == (
        "RENDER_DETAIL"
    )
    assert disposition_for(adr_type="physical-system", pointer="/system/id") == "GOVERNANCE_METADATA"
    assert disposition_for(adr_type="physical-system", pointer="/system/name") == "RENDER_PRIMARY"


def test_production_renderer_has_no_current_corpus_special_cases() -> None:
    banned = (
        "ADR-PS-0001",
        "ADR-PS-0002",
        "SYS-0001",
        "SYS-0002",
        "COMP-0010",
        "COMP-0011",
        "COMP-0012",
        "COMP-0013",
        "COMP-0014",
        "ADR Kit Authoring Compiler and Validation System",
        "ADR Architecture Kit Discovery and Indexing System",
    )
    for path in PRODUCTION_RENDERER_PATHS:
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} contains corpus special case {token}"


def test_maximal_fixture_generic_projection_contract(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    body = _ps_body(artifacts, "ADR-PS-9101")
    content = body.split("-->", 1)[-1]

    sentinels = [
        "SYS-9101",
        "Maximal Physical System",
        "COMP-9101",
        "Alpha Service",
        "COMP-9102",
        "Beta Queue",
        "COMP-9103",
        "Gamma Cache",
        "COMP-9104",
        "Delta Worker",
        "COMP-9105",
        "Epsilon Database",
        "COMP-9106",
        "Zeta Gateway",
        "PURPOSE_ALPHA",
        "PURPOSE_BETA",
        "PURPOSE_GAMMA",
        "PURPOSE_DELTA",
        "PURPOSE_EPSILON",
        "PURPOSE_ZETA",
        "ADR-PC-9101",
        "ADR-PC-9102",
        "SYSBOUND-9101",
        "SYSBOUND-9102",
        "BOUNDARY_DESC_PRIMARY",
        "BOUNDARY_DESC_SECONDARY",
        "EXT_DEP_ALPHA",
        "EXT_DEP_BETA",
        "EXT_DEP_GAMMA",
        "EXPOSED_IFACE_ALPHA",
        "EXPOSED_IFACE_BETA",
        "EXPOSED_IFACE_GAMMA",
        "PATTERN_GATEWAY",
        "APPLICATION_TEXT",
        "RATIONALE_TEXT",
        "FLOW-9101",
        "FLOW_DESC_ALPHA",
        "DATA_TYPE_ALPHA",
        "VOLUME_ALPHA",
        "LATENCY_P95",
        "HORIZONTAL_SCALE",
        "VERTICAL_SCALE",
        "BOTTLENECK_DB",
        "BOTTLENECK_QUEUE",
        "CAPACITY_PLAN",
        "FAIL_SCENARIO_QUEUE",
        "FAIL_SCENARIO_DB",
        "FAIL_MITIGATION_QUEUE",
        "Second paragraph remains in the projection.",
        "FAIL_DETECTION_QUEUE",
        "FAIL_RECOVERY_QUEUE",
        "FAIL_MITIGATION_DB",
        "FAIL_DETECTION_DB",
        "FAIL_RECOVERY_DB",
        "MONITORING_SENTINEL",
        "LOGGING_SENTINEL",
        "BACKUP_SENTINEL",
        "EXTRA_OPS_SENTINEL",
        "ORCHESTRATION_SENTINEL",
        "DEPLOY_SCALE_SENTINEL",
        "GAP_QUESTION",
        "TAG_SENTINEL",
        "DOMAIN_SENTINEL",
        "authoring v1.5",
        "PROTOCOL_HTTP",
        "PROTOCOL_SQL",
        "REL_DESC_CALLS",
        "REL_DESC_DEPENDS",
        "does not perform runtime extraction, MCP, or LLM responsibilities.",
    ]
    missing = [item for item in sentinels if item not in content]
    assert missing == []

    assert "## Architecture Position" in content
    assert "## Before You Change This System" in content
    assert "### System Components" in content
    assert "### System Topology" in content
    assert "### Component Interactions" in content
    assert "## System Boundaries" in content
    assert "## Integration Patterns" in content
    assert "## Data Flows" in content
    assert "## Scalability" in content
    assert "## Failure Modes" in content
    assert "## Operational Requirements" in content
    assert "## Technology Stack" in content
    assert "## Known Gaps" in content
    assert "Physical-system membership is `composed_of`" not in content

    assert "COMP-9101 — Alpha Service" in content
    assert "service" in content
    assert "[ADR-PC-9101]" in content or "ADR-PC-9101" in content
    assert "019209b0-c2d3-7e00-8000-000000000031" not in content

    topology = content.split("### System Topology", 1)[1].split("### Component Interactions", 1)[0]
    assert "COMP-9101<br/>Alpha Service" in topology
    assert "TOPO-9101" not in topology
    for verb in TOPOLOGY_VERBS:
        assert f'|"{verb}"|' in topology

    interactions = content.split("### Component Interactions", 1)[1].split("## System Boundaries", 1)[0]
    assert "calls (`calls`)" in interactions
    assert "publishes to (`publishes_to`)" in interactions
    assert "subscribes to (`subscribes_to`)" in interactions
    assert "reads from (`reads_from`)" in interactions
    assert "writes to (`writes_to`)" in interactions
    assert "depends on (`depends_on`)" in interactions
    assert "| Alpha Service | calls" not in interactions or "COMP-9101 — Alpha Service" in interactions
    assert "COMP-9101 — Alpha Service" in interactions
    assert "COMP-9102 — Beta Queue" in interactions

    flow = content.split("## Data Flows", 1)[1].split("## Scalability", 1)[0]
    assert "COMP-9101 — Alpha Service" in flow
    assert "COMP-9102 — Beta Queue" in flow
    assert "COMP-9104 — Delta Worker" in flow
    assert "    ->" in flow
    assert "`calls`" not in flow or "calls (`calls`)" not in flow.split("**Path**", 1)[-1]
    path_block = flow.split("**Path**", 1)[-1]
    assert "depends_on" not in path_block
    assert "calls" not in path_block
    assert "publishes_to" not in path_block

    assert content.count("EXT_DEP_BETA") >= 1
    change_safety = content.split("## Before You Change This System", 1)[1].split("## Integration", 1)[0]
    assert change_safety.count("EXT_DEP_BETA") == 1

    hyphen_uuids = UUID_HYPHEN.findall(content)
    assert hyphen_uuids == [], f"human body leaked UUIDs: {hyphen_uuids}"


def test_optional_system_omits_empty_sections(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    body = _ps_body(artifacts, "ADR-PS-9102")
    content = body.split("-->", 1)[-1]
    assert "## Integration Patterns" not in content
    assert "## Data Flows" not in content
    assert "## Scalability" not in content
    assert "## Failure Modes" not in content
    assert "## Operational Requirements" not in content
    assert "## Known Gaps" not in content
    assert "## Deployment" not in content
    assert "### Component Interactions" not in content
    assert "{}" not in content
    assert "COMP-9107 — Optional Widget" in content
    assert "PURPOSE_OPTIONAL" in content
    assert "EXPOSED_IFACE_OPTIONAL" in content
    assert "EXT_DEP_OPTIONAL" in content
    topology = content.split("### System Topology", 1)[1].split("## System Boundaries", 1)[0]
    assert "COMP-9107" in topology
    assert '|"' not in topology
    assert "TOPO-9107" not in topology.split("```mermaid", 1)[1].split("```", 1)[0]


def test_render_is_byte_deterministic(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    first, _, _ = _compile_fixture(workspace)
    second, _, _ = _compile_fixture(workspace)
    first_body = _ps_body(first, "ADR-PS-9101")
    second_body = _ps_body(second, "ADR-PS-9101")
    assert first_body == second_body
    assert "generator_version: 3" in first_body
    assert MARKDOWN_GENERATOR_IDENTITY.generator_version == 3


def test_changing_rendered_field_changes_source_hash(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    before_artifacts, _, _ = _compile_fixture(workspace)
    before = _ps_body(before_artifacts, "ADR-PS-9101")
    before_header = parse_integrity_header(before)

    source = next((workspace / "adrs" / "physical-system").glob("ADR-PS-9101*.yaml"))
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["component_topology"]["components"][0]["purpose"] = "PURPOSE_MUTATED"
    source.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    after_artifacts, _, _ = _compile_fixture(workspace)
    after = _ps_body(after_artifacts, "ADR-PS-9101")
    after_header = parse_integrity_header(after)
    assert "PURPOSE_MUTATED" in after
    assert before_header["source_hash"] != after_header["source_hash"]


def test_kit_corpus_ps_canaries_expose_authored_fields() -> None:
    result = compile_architecture(
        CompilationRequest(project_root=ROOT, artifact_groups=("markdown",), write=False)
    )
    assert result.success, result.diagnostics

    def text(alias: str) -> str:
        match = next(
            item
            for item in result.artifacts
            if "physical-system" in item.relative_path.replace("\\", "/")
            and alias in item.relative_path
        )
        return match.content.decode("utf-8")

    ps1 = text("ADR-PS-0001")
    assert "SYS-0001" in ps1
    assert "COMP-0010" in ps1
    assert "Entity Registry Generator and Query Surface" in ps1
    assert "019fee89-e617-76d8-a333-e21361cd6602" not in ps1.split("-->", 1)[-1]
    assert "Compile, emit, and query derived discovery artifacts" in ps1
    assert "Canonical ADR artifacts" in ps1
    assert "Standalone invariant artifacts" in ps1
    assert "adr compile" in ps1
    assert "adr generate-architecture-index" in ps1
    assert "ADR-PC-0001" in ps1
    assert "Physical-system membership is `composed_of`" not in ps1

    ps2 = text("ADR-PS-0002")
    assert "SYS-0002" in ps2
    assert "COMP-0011" in ps2
    assert "COMP-0012" in ps2
    assert "COMP-0013" in ps2
    assert "COMP-0014" in ps2
    assert "Schema and Contract Validation Surface" in ps2
    assert "Compiler Pipeline and Driver" in ps2
    assert "Repository Boundary Component" in ps2
    assert "Generated Artifact Integrity Validation" in ps2
    assert "Validates canonical ADR structure and contract expectations" in ps2
    assert "ADR-PC-0002" in ps2
    assert "ADR-PC-0003" in ps2
    assert "ADR-PC-0004" in ps2
    assert "ADR-PC-0005" in ps2
    assert "depends on (`depends_on`)" in ps2
    assert "COMP-0012 — Compiler Pipeline and Driver" in ps2
    assert "adr compile" in ps2
    assert "adr_kit.api" in ps2
    assert "Deterministic validation and compilation output" in ps2
    assert "CLI-visible diagnostic logging" in ps2
    topology = ps2.split("### System Topology", 1)[1].split("### Component Interactions", 1)[0]
    assert '|"depends_on"|' in topology
    assert "TOPO-0001" not in topology
    assert "TOPO-0002" not in topology
