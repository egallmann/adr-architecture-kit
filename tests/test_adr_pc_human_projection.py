"""Generic ADR-PC human projection quality tests.

Production renderer must operate on adr_type and authored fields, never
ADR-PC-0001..0008 aliases. The synthetic fixture is the generic proof;
kit corpus documents are canaries only.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.compiler.backend.coverage_registry import disposition_for
from adr_kit.compiler.backend.markdown_rendering import (
    MARKDOWN_GENERATOR_IDENTITY,
    emit_markdown_artifacts,
)
from adr_kit.compiler.frontend.builder import ArchModelBuilder
from adr_kit.integrity.core import parse_integrity_header
from adr_kit.parser import ADRParser
from adr_kit.scope import ProjectScopeResolver

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "adr-pc-human-projection"
PRODUCTION_RENDERER_PATHS = (
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "human_adr_projection.py",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "physical_component_projection.py",
    ROOT / "src" / "adr_kit" / "templates" / "adr-physical-component-v3.md.jinja2",
    ROOT / "src" / "adr_kit" / "compiler" / "backend" / "coverage_registry" / "__init__.py",
)
UUID_HYPHEN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _copy_fixture(tmp_path: Path) -> Path:
    dest = tmp_path / "workspace"
    shutil.copytree(FIXTURE, dest)
    return dest


def _pc_body(artifacts, alias: str) -> str:
    match = next(
        item
        for item in artifacts
        if "physical-component" in item.path.as_posix() and alias in item.path.as_posix()
    )
    return match.content.decode("utf-8")


def _compile_fixture(workspace: Path):
    parser = ADRParser()
    scope = ProjectScopeResolver(explicit_scope=workspace).resolve()
    build = ArchModelBuilder().build_from_scope(scope)
    artifacts = emit_markdown_artifacts(parser=parser, scope=scope, build_result=build)
    return artifacts, scope, build


def test_coverage_registry_pc_identity_and_contract_fields() -> None:
    assert disposition_for(adr_type="physical-component", pointer="/schema_version") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-component", pointer="/created_date") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-component", pointer="/authors") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-component", pointer="/domains") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-component", pointer="/tags") == "RENDER_PRIMARY"
    assert disposition_for(adr_type="physical-component", pointer="/technologies") == (
        "INTENTIONALLY_NOT_RENDERED"
    )
    assert disposition_for(adr_type="physical-component", pointer="/introduces_entities") == (
        "INTENTIONALLY_NOT_RENDERED"
    )
    assert (
        disposition_for(
            adr_type="physical-component",
            pointer="/component_specifications/generation_context/purpose",
        )
        == "RENDER_PRIMARY"
    )
    assert (
        disposition_for(
            adr_type="physical-component",
            pointer="/component_specifications/interfaces/specification",
        )
        == "RENDER_DETAIL"
    )
    assert (
        disposition_for(
            adr_type="physical-component",
            pointer="/implementation_decisions/rationale",
        )
        == "RENDER_DETAIL"
    )
    assert disposition_for(adr_type="physical-component", pointer="/migration_origin") == "RENDER_DETAIL"
    assert disposition_for(adr_type="physical-component", pointer="/component_topology") == (
        "UNSUPPORTED_OR_STALE"
    )


def test_production_renderer_has_no_current_corpus_special_cases() -> None:
    banned = (
        "ADR-PC-0001",
        "ADR-PC-0002",
        "ADR-PC-0003",
        "ADR-PC-0004",
        "ADR-PC-0005",
        "ADR-PC-0006",
        "ADR-PC-0007",
        "ADR-PC-0008",
        "Project Scope Resolution",
        "Compiler Pipeline and Driver",
        "Semantic Attribution Embodiment",
    )
    for path in PRODUCTION_RENDERER_PATHS:
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} contains corpus special case {token}"


def test_maximal_fixture_generic_projection_contract(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    body = _pc_body(artifacts, "ADR-PC-9001")
    content = body.split("-->", 1)[-1]

    sentinels = [
        "PURPOSE_ALPHA",
        "PURPOSE_BETA",
        "KEY_RESP_ALPHA",
        "KEY_RESP_BETA",
        "CONSTRAINT_ALPHA",
        "CONSTRAINT_BETA",
        "SUCCESS_ALPHA",
        "SUCCESS_BETA",
        "DESC_ALPHA",
        "RESPONSIBILITIES_ALPHA",
        "RESPONSIBILITIES_BETA",
        "ERROR_STRATEGY",
        "ERROR_STRATEGY_BETA",
        "METRIC_NAME",
        ">= 91%",
        "INTEGRATION_NESTED",
        "COMPONENT_TEST_ITEM",
        "DEP_PATHLIB",
        "MODULE_PATH_ALPHA",
        "SERVICE_ALPHA",
        "ENTRY_ALPHA",
        "TEST_PATH_ALPHA",
        "REPO_ALPHA",
        "MODULE_PATH_BETA",
        "RATIONALE_FULL_TEXT",
        "Second paragraph of rationale stays in the projection.",
        "ALT_NAME",
        "ALT_REJECTED",
        "CONSEQUENCE_ONE",
        "CONSEQUENCE_TWO",
        "RATIONALE_BETA",
        "GAP_QUESTION",
        "TAG_SENTINEL",
        "DOMAIN_SENTINEL",
        "COMP-8901",
        "COMP-9001",
        "IFACE-8901",
        "IMPL-8901",
        "authoring v1.5",
    ]
    missing = [item for item in sentinels if item not in content]
    assert missing == []

    assert content.count("### COMP-9001: Alpha Component") == 1
    assert content.count("### COMP-9002: Beta Component") == 1
    assert "## Architecture at a Glance" in content
    assert "## Change Safety" in content
    assert "### Before You Change This Component" not in content
    assert "## Component Contract" in content
    assert "## Interfaces" in content
    assert "### IMPL-9001 — Choose a deterministic alpha runtime" in content
    assert "## Engineering Contract" in content
    assert "## Implementation Map" in content
    assert "## Lineage / Migration" in content
    assert "## Known Gaps" in content
    assert "CAP-9001" in content
    assert "Fixture Capability" in content
    assert "- `component` COMP-9001 — Alpha Component\n" in content
    assert "- `interface` IFACE-9001 — CLI\n" in content

    spec_block = content.split("### IFACE-9001 — CLI", 1)[1].split("### IFACE-9002", 1)[0]
    assert "- adr alpha" in spec_block
    assert "- adr beta" in spec_block
    assert "- adr gamma" in spec_block
    assert "adr alpha - adr beta" not in spec_block

    assert "Depends on" in content
    assert "Depended on by" in content
    assert "Beta Component" in content
    assert "Peer Component" in content

    assert "COMP-9001<br/>Alpha Component" in content
    assert "IFACE-9001<br/>CLI" in content
    assert "ADR-PC-9001<br/>Maximal Physical Component" in content

    hyphen_uuids = UUID_HYPHEN.findall(content)
    assert hyphen_uuids == [], f"human body leaked UUIDs: {hyphen_uuids}"


def test_optional_peer_omits_empty_sections(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    artifacts, _scope, _build = _compile_fixture(workspace)
    body = _pc_body(artifacts, "ADR-PC-9002")
    content = body.split("-->", 1)[-1]
    assert "## Lineage / Migration" not in content
    assert "## Gaps" not in content
    assert "**Alternatives Considered:**" not in content
    assert "**Consequences:**" not in content
    assert "{}" not in content
    assert "**Description:**" not in content
    assert "Must Remain True" not in content


def test_render_is_byte_deterministic(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    first, _, _ = _compile_fixture(workspace)
    second, _, _ = _compile_fixture(workspace)
    first_body = _pc_body(first, "ADR-PC-9001")
    second_body = _pc_body(second, "ADR-PC-9001")
    assert first_body == second_body
    assert "generator_version: 3" in first_body
    assert MARKDOWN_GENERATOR_IDENTITY.generator_version == 3


def test_changing_rendered_field_changes_source_hash(tmp_path: Path) -> None:
    workspace = _copy_fixture(tmp_path)
    before_artifacts, _, _ = _compile_fixture(workspace)
    before = _pc_body(before_artifacts, "ADR-PC-9001")
    before_header = parse_integrity_header(before)

    source = next((workspace / "adrs" / "physical-component").glob("ADR-PC-9001*.yaml"))
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["component_specifications"][0]["generation_context"]["purpose"] = "PURPOSE_MUTATED"
    source.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    after_artifacts, _, _ = _compile_fixture(workspace)
    after = _pc_body(after_artifacts, "ADR-PC-9001")
    after_header = parse_integrity_header(after)
    assert "PURPOSE_MUTATED" in after
    assert before_header["source_hash"] != after_header["source_hash"]


def test_kit_corpus_pc_canaries_expose_authored_fields() -> None:
    result = compile_architecture(
        CompilationRequest(project_root=ROOT, artifact_groups=("markdown",), write=False)
    )
    assert result.success, result.diagnostics

    def text(alias: str) -> str:
        match = next(
            item
            for item in result.artifacts
            if "physical-component" in item.relative_path.replace("\\", "/")
            and alias in item.relative_path
        )
        return match.content.decode("utf-8")

    pc1 = text("ADR-PC-0001")
    assert "Generate and query the normalized entity registry" in pc1
    assert "Discovery outputs are derived and non-authoritative" in pc1
    assert "Fail closed on duplicate entity IDs" in pc1
    assert "entity_registry_generations_total" in pc1
    assert "src/adr_kit/compiler/driver.py" in pc1
    assert "tests/test_compiler_driver.py" in pc1
    assert "- adr compile" in pc1

    pc3 = text("ADR-PC-0003")
    assert "Pass ordering must stay compiler-owned and explicit" in pc3
    assert "Internal compiler types must not cross the supported public facade" in pc3
    assert "Keep compiler orchestration as a dedicated component" in pc3
    assert "tests/test_compiler_driver.py" in pc3
    assert "Depended on by" in pc3

    pc4 = text("ADR-PC-0004")
    assert "future Assembler" in pc4
    assert "ArchitectureRepository" in pc4
    assert "src/adr_kit/repository/architecture_repository.py" in pc4

    pc7 = text("ADR-PC-0007")
    assert "Must not load architecture state from legacy decorators" in pc7
    assert "1.0/1.2 callers of validate_implementation_attribution_evidence" in pc7
    assert "adr_kit.decorators" in pc7

    pc8 = text("ADR-PC-0008")
    assert "Python module implementing project scope detection" in pc8
    assert "pathlib.Path" in pc8
    assert "Named tuples" in pc8
    assert "Less readable, no default values" in pc8
    assert "Requires Python 3.7+" in pc8
    assert "COMP-0001" in pc8
    assert "COMP-0017" in pc8
    assert "## Lineage / Migration" in pc8
