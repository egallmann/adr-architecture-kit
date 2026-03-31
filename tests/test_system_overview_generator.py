"""Tests for the generated SYSTEM-OVERVIEW artifact."""

from pathlib import Path

from src.adr_kit.integrity.core import parse_integrity_header
from src.adr_kit.generators import SystemOverviewGenerator
from src.adr_kit.validators import SystemOverviewValidator


def test_system_overview_generator_renders_required_sections():
    body = SystemOverviewGenerator().render()

    assert body.startswith("<!--\n")
    assert "document_type: system-overview" in body
    assert "authority_order:" in body
    assert "-->\n\n# SYSTEM-OVERVIEW" in body
    assert "---\n" not in body
    assert "# SYSTEM-OVERVIEW" in body
    assert "## First Discovery Order" in body
    assert "`adr generate-system-overview`" in body
    assert "`adr validate-system-overview`" in body


def test_system_overview_validator_accepts_generated_file(tmp_path):
    output = tmp_path / "SYSTEM-OVERVIEW.md"
    generator = SystemOverviewGenerator()
    generator.save(output)
    header = parse_integrity_header(output.read_text(encoding="utf-8"))

    result = SystemOverviewValidator(generator=generator).validate_file(output)

    assert header["artifact_kind"] == "system_overview"
    assert result.is_valid
    assert result.errors == []


def test_system_overview_validator_detects_stale_file(tmp_path):
    output = tmp_path / "SYSTEM-OVERVIEW.md"
    output.write_text("# SYSTEM-OVERVIEW\nstale\n", encoding="utf-8")

    result = SystemOverviewValidator().validate_file(output)

    assert not result.is_valid
    assert any("stale or manually edited" in error for error in result.errors)


def test_repo_system_overview_matches_generator():
    repo_file = Path("SYSTEM-OVERVIEW.md")

    result = SystemOverviewValidator().validate_file(repo_file)

    assert result.is_valid, result.errors
