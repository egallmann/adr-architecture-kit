"""Tests for Physical-System ADR YAML generation."""

import shutil
import uuid
from pathlib import Path

from click.testing import CliRunner

from src.adr_kit.cli.main import cli
from src.adr_kit.generators import PhysicalSystemADRGenerator
from src.adr_kit.parser import ADRParser
from src.adr_kit.validators import ADRValidator


def test_render_yaml_from_minimal_fixture():
    """Generator renders stable YAML for required Physical-System fields."""
    parser = ADRParser()
    generator = PhysicalSystemADRGenerator(parser=parser)
    fixture_path = Path("tests/fixtures/valid/physical-system-minimal.yaml")

    adr = parser.parse_physical_system_adr(fixture_path)
    yaml_text = generator.render_yaml(adr)

    assert "technology_stack:" in yaml_text
    assert "system_boundaries:" in yaml_text
    assert "component_topology:" in yaml_text
    assert "failure_modes:" in yaml_text


def _make_workspace_temp_dir() -> Path:
    temp_dir = Path("tests") / ".tmp" / str(uuid.uuid4())
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def test_save_generated_physical_system_to_arbitrary_path():
    """Generator can write a valid Physical-System ADR outside adrs/physical-system."""
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    generator = PhysicalSystemADRGenerator(parser=parser, validator=validator)
    fixture_path = Path("tests/fixtures/valid/physical-system-minimal.yaml")
    temp_dir = _make_workspace_temp_dir()
    output_path = temp_dir / "documentation" / "adr" / "physical" / "generated.yaml"

    try:
        adr = generator.create_adr_from_file(fixture_path)
        generator.save_adr(adr, output_path)

        parsed = parser.parse_physical_system_adr(output_path)
        result = validator.validate_file(output_path)

        assert output_path.exists()
        assert parsed.id == "ADR-PS-0001"
        assert result.valid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_generate_physical_system_cli_round_trip():
    """CLI generates a parseable and valid Physical-System ADR file."""
    runner = CliRunner()
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    fixture_path = Path("tests/fixtures/valid/physical-system-minimal.yaml")
    temp_dir = _make_workspace_temp_dir()
    output_path = temp_dir / "physical-system-cli.yaml"

    try:
        result = runner.invoke(
            cli,
            [
                "generate-physical-system",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code == 0, result.output

        parsed = parser.parse_physical_system_adr(output_path)
        validation = validator.validate_file(output_path)

        assert parsed.id == "ADR-PS-0001"
        assert validation.valid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
