"""Generic ADR-L human projection quality tests."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

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
FIXTURE = ROOT / "tests" / "fixtures" / "adr-l-human-projection"
PRODUCTION_RENDERER_PATHS = (
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "human_adr_projection.py",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "logical_projection.py",
    ROOT / "src" / "adr_kit" / "templates" / "adr-logical-v3.md.jinja2",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "coverage_registry" / "__init__.py",
)
UUID_HYPHEN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
HUMAN_RENDER_DISPOSITIONS = {
    "RENDER_PRIMARY",
    "RENDER_DETAIL",
    "RENDER_AS_RELATIONSHIP",
    "RENDER_SUMMARY_AND_DETAIL",
}


def _copy_fixture(tmp_path: Path) -> Path:
    dest = tmp_path / "workspace"
    shutil.copytree(FIXTURE, dest)
    return dest


def _logical_body(artifacts, alias: str) -> str:
    match = next(
        item
        for item in artifacts
        if "logical" in item.path.as_posix() and alias in item.path.as_posix()
    )
    return match.content.decode("utf-8")


def _compile_fixture(workspace: Path):
    parser = ADRParser()
    scope = ProjectScopeResolver(explicit_scope=workspace).resolve()
    build = ArchModelBuilder().build_from_scope(scope)
    artifacts = emit_markdown_artifacts(parser=parser, scope=scope, build_result=build)
    return artifacts, scope, build


def test_coverage_registry_logical_fields_classified() -> None:
    pointers = collect_schema_field_pointers("logical")
    for pointer in pointers:
        disposition = disposition_for(adr_type="logical", pointer=pointer)
        assert disposition in DISPOSITIONS
    assert disposition_for(adr_type="logical", pointer="/schema_version") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="logical", pointer="/decisions/consequences") == "RENDER_DETAIL"
    assert disposition_for(adr_type="logical", pointer="/architectural_boundaries/rationale") == (
        "RENDER_DETAIL"
    )
    assert disposition_for(adr_type="logical", pointer="/invariants/verification_method") == (
        "RENDER_DETAIL"
    )


def test_production_renderer_has_no_current_corpus_special_cases() -> None:
    banned = (
        "ADR-L-0001",
        "ADR-L-0013",
        "ADR-L-0025",
        "STE-Compliant Machine-Verifiable",
        "Architecture Repository Boundary",
        "Topology and Contract Succession",
    )
    for path in PRODUCTION_RENDERER_PATHS:
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} contains corpus special case {token}"


def test_maximal_fixture_generic_projection_contract(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    body = _logical_body(artifacts, "ADR-L-9001")
    content = body.split("-->", 1)[-1]

    sentinels = [
        "CONTEXT_SENTINEL",
        "Second paragraph of context stays in the projection losslessly.",
        "RATIONALE_ALPHA",
        "ALT_NAME_ALPHA",
        "ALT_REJECTED_ALPHA",
        "CONSEQUENCE_POSITIVE_ALPHA",
        "CONSEQUENCE_NEGATIVE_ALPHA",
        "CAP_DESC_ALPHA",
        "BOUND_DESC_ALPHA",
        "BOUND_RATIONALE_ALPHA",
        "GUARANTEE_ALPHA",
        "INV_STATEMENT_ALPHA",
        "INV_RATIONALE_ALPHA",
        "EXCEPTION_ALPHA",
        "NFR_REQUIREMENT_ALPHA",
        "NFR_ACCEPTANCE_ALPHA",
        "CONST_DESC_ALPHA",
        "CONST_RATIONALE_ALPHA",
        "GAP_QUESTION_ALPHA",
        "GAP_CONTEXT_ALPHA",
        "EXT_ENTITY_ALPHA",
        "NOTES_SENTINEL",
        "TAG_SENTINEL",
        "DOMAIN_SENTINEL",
        "authoring v1.5",
        "DEC-9001",
        "DEC-9002",
        "CAP-9001",
        "BOUND-9001",
        "CONTRACT-9001",
        "INV-9001",
        "ADR-PS-9001",
        "ADR-PC-9001",
        "COMP-9001",
    ]
    missing = [item for item in sentinels if item not in content]
    assert missing == []

    assert "## Architecture at a Glance" in content
    assert "## Context" in content
    context_pos = content.index("## Context")
    relationships_pos = content.index("## Architecture Relationships")
    assert context_pos < relationships_pos
    assert "## Architectural Decisions" in content
    assert "## Capabilities" in content
    assert "## Architectural Boundaries" in content
    assert "## Interaction Contracts" in content
    assert "## Invariants" in content
    assert "## Non-Functional Requirements" in content
    assert "## Constraints" in content
    assert "## Physical Realization" in content
    assert "## Known Gaps" in content
    assert "## Consumer Semantic Extensions" in content
    assert "## Architecture Neighborhood" not in content
    assert "## Internal Structure" not in content
    assert "### Semantic architecture inventory" not in content
    assert "Semantic architecture inventory" not in content
    assert "PEER_CONTEXT_SENTINEL" not in content
    assert "**Peer context:**" not in content

    decisions = content.split("## Architectural Decisions", 1)[1].split("## Capabilities", 1)[0]
    assert "Positive:" in decisions
    assert "Negative:" in decisions
    assert "| Alternative | Rejected because |" in decisions
    assert "| Decision | Choice | Traceability |" in decisions


def test_declared_in_only_logical_fixture_omits_ownership_star(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    content = _logical_body(artifacts, "ADR-L-9002").split("-->", 1)[-1]
    assert "## Internal Structure" not in content
    if "```mermaid" in content:
        assert "declared_in" not in content.split("```mermaid", 1)[1].split("```", 1)[0]


def test_decision_traceability_graph_renders_when_semantic_edges_exist(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    content = _logical_body(artifacts, "ADR-L-9001").split("-->", 1)[-1]
    trace = content.split("## Decision / Intent Traceability", 1)[1].split("## Physical Realization", 1)[0]
    assert "```mermaid" in trace
    assert "enforces" in trace or "enables" in trace


def test_no_uuid_leakage_in_fixture(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    content = _logical_body(artifacts, "ADR-L-9001").split("-->", 1)[-1]
    assert UUID_HYPHEN.search(content) is None


def test_optional_sections_absent_when_empty(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    content = _logical_body(artifacts, "ADR-L-9002").split("-->", 1)[-1]
    assert "None" not in content
    assert "## Known Gaps" not in content
    assert "## Physical Realization" not in content


def test_deterministic_second_generation(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    first = _compile_fixture(workspace)[0]
    second = _compile_fixture(workspace)[0]
    assert _logical_body(first, "ADR-L-9001") == _logical_body(second, "ADR-L-9001")


def test_source_hash_closure_present(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    body = _logical_body(artifacts, "ADR-L-9001")
    header = parse_integrity_header(body)
    assert header["generator_id"] == MARKDOWN_GENERATOR_IDENTITY.generator_id
    assert header["generator_version"] == str(MARKDOWN_GENERATOR_IDENTITY.generator_version)
    assert header["source_hash"]


def test_logical_field_coverage_paths_exercised(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    content = _logical_body(artifacts, "ADR-L-9001").split("-->", 1)[-1]
    pointers = collect_schema_field_pointers("logical")
    for pointer in pointers:
        disposition = disposition_for(adr_type="logical", pointer=pointer)
        if disposition not in HUMAN_RENDER_DISPOSITIONS:
            continue
        if pointer.startswith("/decisions"):
            assert "## Architectural Decisions" in content
        elif pointer.startswith("/capabilities"):
            assert "## Capabilities" in content
        elif pointer.startswith("/architectural_boundaries"):
            assert "## Architectural Boundaries" in content
        elif pointer.startswith("/interaction_contracts"):
            assert "## Interaction Contracts" in content
        elif pointer.startswith("/invariants"):
            assert "## Invariants" in content
        elif pointer.startswith("/non_functional_requirements"):
            assert "## Non-Functional Requirements" in content
        elif pointer.startswith("/constraints"):
            assert "## Constraints" in content
        elif pointer.startswith("/gaps"):
            assert "## Known Gaps" in content
        elif pointer.startswith("/extension_entities"):
            assert "## Consumer Semantic Extensions" in content
