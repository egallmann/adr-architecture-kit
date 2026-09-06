"""Tests for the generated SYSTEM-OVERVIEW artifact."""

import re
from pathlib import Path

from adr_kit.compiler.pipeline import run_frontend_pipeline
from adr_kit.generators import SystemOverviewGenerator
from adr_kit.integrity.core import parse_integrity_header
from adr_kit.scope import ProjectScopeResolver
from adr_kit.validators import SystemOverviewValidator


def _current_overview_generator() -> SystemOverviewGenerator:
    scope = ProjectScopeResolver(explicit_scope=Path.cwd()).resolve()
    frontend = run_frontend_pipeline(scope=scope)
    return SystemOverviewGenerator(scope=scope, build_result=frontend)


def test_system_overview_generator_renders_required_sections():
    body = _current_overview_generator().render()

    assert body.startswith("<!--\n")
    assert "document_type: system-overview" in body
    assert "authority_order:" in body
    assert "-->\n\n# SYSTEM-OVERVIEW" in body
    assert "---\n" not in body
    assert "last_updated:" not in body
    assert "# SYSTEM-OVERVIEW" in body
    assert "## Start Here" in body
    assert "## One-Line Orientation" in body
    assert "`adr generate-system-overview`" in body
    assert "`adr validate-system-overview`" in body
    assert "## First Discovery Order" not in body
    assert "documentation-state toolkit" not in body


def test_system_overview_validator_accepts_generated_file(tmp_path):
    output = tmp_path / "SYSTEM-OVERVIEW.md"
    generator = _current_overview_generator()
    generator.save(output)
    header = parse_integrity_header(output.read_text(encoding="utf-8"))

    result = SystemOverviewValidator(generator=generator).validate_file(output)

    assert header["artifact_kind"] == "system_overview"
    assert header["generator_version"] == "2"
    assert result.is_valid
    assert result.errors == []


def test_system_overview_validator_detects_stale_file(tmp_path):
    output = tmp_path / "SYSTEM-OVERVIEW.md"
    output.write_text("# SYSTEM-OVERVIEW\nstale\n", encoding="utf-8")

    result = SystemOverviewValidator(
        generator=SystemOverviewGenerator(repo_root=Path.cwd())
    ).validate_file(output)

    assert not result.is_valid
    assert any("stale or manually edited" in error for error in result.errors)


def test_repo_system_overview_matches_generator():
    repo_file = Path("SYSTEM-OVERVIEW.md")
    generator = _current_overview_generator()
    result = SystemOverviewValidator(generator=generator).validate_file(repo_file)

    assert result.is_valid, result.errors


def test_system_overview_markdown_links_open_files_not_directories():
    generator = _current_overview_generator()
    body = generator.render()
    repo = Path.cwd()
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", body)
    assert "schema/README.md" in targets
    assert "AUTHORING-SYSTEM.md" in targets
    assert "adrs/" not in targets
    assert "schema/" not in targets
    for target in targets:
        if "://" in target:
            continue
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        resolved = repo / path_part
        assert resolved.is_file(), f"overview link is not an openable file: {target}"


def test_directory_href_rewrites_to_readme_when_present(tmp_path: Path):
    generator = SystemOverviewGenerator(repo_root=tmp_path)
    (tmp_path / "schema").mkdir()
    (tmp_path / "schema" / "README.md").write_text("# schema\n", encoding="utf-8")
    (tmp_path / "adrs").mkdir()

    assert generator._openable_repo_file_target("schema/") == "schema/README.md"
    assert generator._openable_repo_file_target("adrs/") is None
    assert generator._openable_repo_file_target("docs/public-sdk.md") == "docs/public-sdk.md"
