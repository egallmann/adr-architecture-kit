from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.adr_kit.compiler.driver import _FixedDateTime
from src.adr_kit.compiler.backend.manifest_rendering import (
    MANIFEST_GENERATOR_IDENTITY,
    build_manifest_integrity_header,
    render_manifest_for_scope,
)
from src.adr_kit.compiler.backend.markdown_rendering import (
    MARKDOWN_GENERATOR_IDENTITY,
    build_markdown_integrity_header,
    render_existing_markdown_artifact,
)
from src.adr_kit.generators.manifest_generator import ManifestGenerator
from src.adr_kit.generators.views.markdown import MarkdownGenerator
from src.adr_kit.parser import ADRParser
from src.adr_kit.scope import ProjectScopeResolver


def test_compiler_manifest_renderer_matches_generator_body_and_inputs():
    scope = ProjectScopeResolver().resolve()
    parser = ADRParser()

    with patch("src.adr_kit.generators.manifest_generator.datetime", _FixedDateTime), patch(
        "src.adr_kit.compiler.backend.manifest_rendering.datetime",
        _FixedDateTime,
    ):
        body, source_inputs = render_manifest_for_scope(parser=parser, scope=scope)
        generator_body, generator_inputs = ManifestGenerator(parser=parser).render_for_scope(scope)

    assert body == generator_body
    assert source_inputs == generator_inputs


def test_compiler_manifest_renderer_matches_generator_header():
    scope = ProjectScopeResolver().resolve()
    parser = ADRParser()
    with patch("src.adr_kit.generators.manifest_generator.datetime", _FixedDateTime), patch(
        "src.adr_kit.compiler.backend.manifest_rendering.datetime",
        _FixedDateTime,
    ):
        body, source_inputs = render_manifest_for_scope(parser=parser, scope=scope)

        header = build_manifest_integrity_header(scope, body, source_inputs)
        generator = ManifestGenerator(parser=parser)

        assert MANIFEST_GENERATOR_IDENTITY == generator.generator_identity
        assert header == generator.build_integrity_header(scope, body, source_inputs)


def test_compiler_markdown_renderer_matches_generator_body_and_inputs():
    scope = ProjectScopeResolver().resolve()
    parser = ADRParser()
    artifact_path = Path("adrs/rendered/ADR-L-0001.md")

    body, source_inputs = render_existing_markdown_artifact(
        artifact_path,
        scope=scope,
        parser=parser,
    )
    generator_body, generator_inputs = MarkdownGenerator().render_existing_artifact(artifact_path, scope)

    assert body == generator_body
    assert source_inputs == generator_inputs


def test_compiler_markdown_renderer_matches_generator_header():
    scope = ProjectScopeResolver().resolve()
    parser = ADRParser()
    artifact_path = Path("adrs/rendered/ADR-L-0001.md")
    body, source_inputs = render_existing_markdown_artifact(
        artifact_path,
        scope=scope,
        parser=parser,
    )

    header = build_markdown_integrity_header(scope, body, source_inputs)
    generator = MarkdownGenerator()

    assert MARKDOWN_GENERATOR_IDENTITY == generator.generator_identity
    assert header == generator.build_integrity_header(scope, body, source_inputs)
