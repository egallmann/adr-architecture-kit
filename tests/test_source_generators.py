"""Tests for ADR source YAML generators beyond Physical-System ADRs."""

import shutil
import uuid
from pathlib import Path

import yaml
from click.testing import CliRunner

from src.adr_kit.cli.main import cli
from src.adr_kit.generators import LogicalADRGenerator, PhysicalComponentADRGenerator, ScaffoldGenerator
from src.adr_kit.parser import ADRParser
from src.adr_kit.validators import ADRValidator


def _make_workspace_temp_dir() -> Path:
    temp_dir = Path("tests") / ".tmp" / str(uuid.uuid4())
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def test_render_yaml_from_minimal_logical_fixture():
    """Generator renders stable YAML for required Logical ADR fields."""
    parser = ADRParser()
    generator = LogicalADRGenerator(parser=parser)
    fixture_path = Path("tests/fixtures/valid/logical-minimal.yaml")

    adr = parser.parse_logical_adr(fixture_path)
    yaml_text = generator.render_yaml(adr)

    assert "context:" in yaml_text
    assert "decisions:" in yaml_text
    assert "authors:" in yaml_text


def test_generate_logical_cli_round_trip():
    """CLI generates a parseable and valid Logical ADR file."""
    runner = CliRunner()
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    fixture_path = Path("tests/fixtures/valid/logical-minimal.yaml")
    temp_dir = _make_workspace_temp_dir()
    output_path = temp_dir / "logical-cli.yaml"

    try:
        result = runner.invoke(
            cli,
            [
                "generate-logical",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code == 0, result.output

        parsed = parser.parse_logical_adr(output_path)
        validation = validator.validate_file(output_path)

        assert parsed.id == "ADR-L-9999"
        assert validation.valid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_generate_logical_cli_can_show_input_schema():
    """CLI can print the structured input schema without requiring input/output paths."""
    runner = CliRunner()

    result = runner.invoke(cli, ["generate-logical", "--show-input-schema"])

    assert result.exit_code == 0, result.output
    assert "properties:" in result.output
    assert "decisions:" in result.output


def test_generate_vision_cli_round_trip():
    """CLI generates a parseable and valid Vision ADR file."""
    runner = CliRunner()
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    fixture_path = Path("tests/fixtures/valid/logical-minimal.yaml")
    temp_dir = _make_workspace_temp_dir()
    input_path = temp_dir / "vision-input.yaml"
    output_path = temp_dir / "vision-cli.yaml"

    try:
        data = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
        data["id"] = "ADR-V-9999"
        data["title"] = "Minimal Valid Vision ADR"
        data["vision_category"] = True
        data.pop("decisions", None)
        input_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        result = runner.invoke(
            cli,
            [
                "generate-vision",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code == 0, result.output

        parsed = parser.parse_logical_adr(output_path)
        validation = validator.validate_file(output_path)

        assert parsed.id == "ADR-V-9999"
        assert parsed.vision_category is True
        assert validation.valid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_generate_physical_component_cli_round_trip():
    """CLI generates a parseable and valid Physical-Component ADR file."""
    runner = CliRunner()
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    fixture_path = Path("tests/fixtures/valid/physical-component-minimal.yaml")
    temp_dir = _make_workspace_temp_dir()
    output_path = temp_dir / "physical-component-cli.yaml"

    try:
        result = runner.invoke(
            cli,
            [
                "generate-physical-component",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code == 0, result.output

        parsed = parser.parse_physical_component_adr(output_path)
        validation = validator.validate_file(output_path)

        assert parsed.id == "ADR-PC-0001"
        assert validation.valid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_generate_physical_system_cli_can_show_input_schema():
    """CLI can print the physical-system input schema without generation paths."""
    runner = CliRunner()

    result = runner.invoke(cli, ["generate-physical-system", "--show-input-schema"])

    assert result.exit_code == 0, result.output
    assert "technology_stack:" in result.output
    assert "system_boundaries:" in result.output


def test_generate_logical_cli_structural_mode_preserves_empty_sections():
    """CLI can generate draft logical ADRs with explicit empty sections intact."""
    runner = CliRunner()
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    temp_dir = _make_workspace_temp_dir()
    input_path = temp_dir / "draft-logical-input.yaml"
    output_path = temp_dir / "draft-logical-output.yaml"

    try:
        input_path.write_text(
            "\n".join(
                [
                    'schema_version: "1.0"',
                    "adr_type: logical",
                    "id: ADR-L-9994",
                    'title: "Draft Logical ADR"',
                    "status: proposed",
                    'created_date: "2026-03-13"',
                    "authors: [adr-architecture-kit]",
                    "domains: [drafting]",
                    "context: |",
                    "  Draft context pending fuller pin-down.",
                    "decisions: []",
                    "gaps: []",
                ]
            ),
            encoding="utf-8",
        )

        result = runner.invoke(
            cli,
            [
                "generate-logical",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--validation-mode",
                "structural",
                "--preserve-empty-sections",
            ],
        )

        assert result.exit_code == 0, result.output
        rendered = output_path.read_text(encoding="utf-8")
        assert "decisions: []" in rendered
        assert "gaps: []" in rendered

        validation = validator.validate_file(output_path, mode="structural")
        assert validation.valid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_generator_exposes_input_json_schema():
    """Programmatic schema exposure should match the model-backed input contract."""
    schema = LogicalADRGenerator.input_json_schema()

    assert "properties" in schema
    assert "decisions" in schema["properties"]


def test_scaffold_generator_emits_forward_authoring_scaffold():
    """Scaffold generator emits deterministic structured inputs for supported ADR types."""
    generator = ScaffoldGenerator()
    logical = generator.scaffold("logical", adr_id="ADR-L-1234", title="Example")
    physical_component_yaml = generator.scaffold_yaml("physical-component", adr_id="ADR-PC-0009")

    assert logical["id"] == "ADR-L-1234"
    assert logical["title"] == "Example"
    assert logical["decisions"][0]["id"] == "DEC-0001"
    assert "ADR-PC-0009" in physical_component_yaml


def test_scaffold_cli_writes_yaml(tmp_path: Path):
    """CLI scaffold command writes deterministic scaffold YAML."""
    runner = CliRunner()
    output_path = tmp_path / "scaffold.yaml"

    result = runner.invoke(
        cli,
        [
            "scaffold",
            "--type",
            "logical",
            "--id",
            "ADR-L-0099",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    rendered = output_path.read_text(encoding="utf-8")
    assert 'id: ADR-L-0099' in rendered
    assert 'decisions:' in rendered
