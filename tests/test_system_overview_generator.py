"""Tests for the generated SYSTEM-OVERVIEW artifact."""

from pathlib import Path

from adr_kit.generators import SystemOverviewGenerator
from adr_kit.integrity.core import parse_integrity_header
from adr_kit.validators import SystemOverviewValidator


def test_system_overview_generator_renders_required_sections():
    body = SystemOverviewGenerator(repo_root=Path.cwd()).render()

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
    generator = SystemOverviewGenerator(repo_root=Path.cwd())
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

    result = SystemOverviewValidator(
        generator=SystemOverviewGenerator(repo_root=Path.cwd())
    ).validate_file(repo_file)

    assert result.is_valid, result.errors
