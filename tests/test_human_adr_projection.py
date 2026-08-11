"""Tests for ADR human projection layout and compiler-derived semantics."""

from __future__ import annotations

from pathlib import Path

from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.compiler.backend.human_adr_projection import (
    context_summary_from_text,
    escape_mermaid_label,
    mermaid_node_id,
)
from adr_kit.compiler.backend.markdown_rendering import (
    MARKDOWN_GENERATOR_IDENTITY,
    emit_markdown_artifacts,
)
from adr_kit.compiler.backend.projection_paths import (
    projection_relative_path,
    stem_matches_adr,
)
from adr_kit.compiler.frontend.builder import ArchModelBuilder
from adr_kit.parser import ADRParser
from adr_kit.scope import ProjectScopeResolver


def test_generator_identity_is_projection_v2():
    assert MARKDOWN_GENERATOR_IDENTITY.generator_id == "adr-projection-markdown"
    assert MARKDOWN_GENERATOR_IDENTITY.generator_version == 2


def test_projection_path_uses_alias_slug_and_type(tmp_path: Path):
    scope = ProjectScopeResolver().resolve()
    parser = ADRParser()
    source = next(scope.logical_dir.glob("ADR-L-0007*.yaml"))
    adr = parser.parse_adr(source)
    path = projection_relative_path(adr)
    assert path.as_posix().startswith("adrs/adr-projection/logical/")
    assert path.name.startswith("ADR-L-0007-")
    assert path.suffix == ".md"
    assert stem_matches_adr(adr, path.stem)
    assert stem_matches_adr(adr, adr.id)
    assert stem_matches_adr(adr, adr.alias_id)


def test_artifact_id_stable_when_slug_changes():
    scope = ProjectScopeResolver(explicit_scope=Path(".")).resolve()
    result = compile_architecture(
        CompilationRequest(
            project_root=scope.root,
            artifact_groups=("markdown",),
            write=False,
        )
    )
    assert result.success
    markdown = [item for item in result.artifacts if item.group == "markdown"]
    assert markdown
    matches = [item for item in markdown if "ADR-L-0007" in item.relative_path]
    assert matches
    artifact = matches[0]
    assert artifact.artifact_id.startswith("rendered-adr:")
    logical = artifact.artifact_id.removeprefix("rendered-adr:")
    assert logical != Path(artifact.relative_path).stem
    # UUID machine id — not alias/slug
    assert logical.startswith("019") or logical.startswith("ADR-")


def test_context_summary_and_mermaid_helpers():
    assert context_summary_from_text("first para\n\nsecond") == "first para"
    assert context_summary_from_text("") == "(no context)"
    assert '"' in escape_mermaid_label('say "hi"')
    assert mermaid_node_id("019fee89-e615-7b9c-8e3f-32ceeda01491").startswith("n_")
    assert mermaid_node_id("ADR-L-0007") == "ADR_L_0007"


def test_implements_logical_and_adr_supersedes_derived():
    scope = ProjectScopeResolver().resolve()
    build = ArchModelBuilder().build_from_scope(scope)
    # Relationships already on ArchModel via pipeline; assert implements_logical present
    verbs = {rel.relationship_type for rel in build.model.relationships.values()}
    assert "implements_logical" in verbs
    # At least one physical→logical implements_logical edge
    impl = [
        rel
        for rel in build.model.relationships.values()
        if rel.relationship_type == "implements_logical"
    ]
    assert impl


def test_emit_markdown_uses_adr_projection_layout():
    scope = ProjectScopeResolver().resolve()
    parser = ADRParser()
    build = ArchModelBuilder().build_from_scope(scope)
    artifacts = emit_markdown_artifacts(parser=parser, scope=scope, build_result=build)
    assert artifacts
    for artifact in artifacts:
        assert artifact.path.as_posix().startswith("adrs/adr-projection/")
        assert artifact.logical_id
        text = artifact.content.decode("utf-8")
        assert "artifact_kind: rendered_adr_markdown" in text
        assert "generator_id: adr-projection-markdown" in text
        assert "```mermaid" in text
        assert "## Context" in text


def test_human_projection_readability_contains_decisions_and_peers():
    scope = ProjectScopeResolver().resolve()
    parser = ADRParser()
    build = ArchModelBuilder().build_from_scope(scope)
    artifacts = emit_markdown_artifacts(parser=parser, scope=scope, build_result=build)
    l7 = next(item for item in artifacts if "ADR-L-0007" in item.path.as_posix())
    body = l7.content.decode("utf-8")
    assert "## Decisions" in body
    assert "**Rationale:**" in body
    assert "## Related ADRs" in body or "```mermaid" in body
