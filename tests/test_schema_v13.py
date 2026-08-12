"""Schema v1.3 identity-envelope validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from adr_kit.api import capabilities
from adr_kit.parser import ADRParser, ADRSchemaValidationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def test_valid_v13_logical_fixture_parses() -> None:
    parser = ADRParser()
    data = parser.parse_yaml(FIXTURES / "v1_3" / "logical-minimal.yaml")
    schema_name = parser._authoring_schema_name(data, "logical")
    assert schema_name == "logical_v1_3"
    parser.validate_against_schema(data, schema_name)


def test_valid_v13_physical_system_fixture_parses() -> None:
    parser = ADRParser()
    data = parser.parse_yaml(FIXTURES / "v1_3" / "physical-system-with-system.yaml")
    schema_name = parser._authoring_schema_name(data, "physical_system")
    assert schema_name == "physical_system_v1_3"
    parser.validate_against_schema(data, schema_name)


def test_v13_logical_missing_alias_id_fails(tmp_path: Path) -> None:
    source = (FIXTURES / "v1_3" / "logical-minimal.yaml").read_text(encoding="utf-8")
    path = tmp_path / "missing-alias-id.yaml"
    path.write_text(source.replace("alias_id: ADR-L-9990\n", ""), encoding="utf-8")
    parser = ADRParser()
    data = parser.parse_yaml(path)
    with pytest.raises(ADRSchemaValidationError, match="alias_id"):
        parser.validate_against_schema(data, parser._authoring_schema_name(data, "logical"))


def test_v13_logical_missing_alias_name_fails(tmp_path: Path) -> None:
    source = (FIXTURES / "v1_3" / "logical-minimal.yaml").read_text(encoding="utf-8")
    path = tmp_path / "missing-alias-name.yaml"
    path.write_text(
        source.replace("alias_name: minimal-v13-logical\n", ""),
        encoding="utf-8",
    )
    parser = ADRParser()
    data = parser.parse_yaml(path)
    with pytest.raises(ADRSchemaValidationError, match="alias_name"):
        parser.validate_against_schema(data, parser._authoring_schema_name(data, "logical"))


def test_v13_logical_non_uuid_id_fails(tmp_path: Path) -> None:
    source = (FIXTURES / "v1_3" / "logical-minimal.yaml").read_text(encoding="utf-8")
    path = tmp_path / "non-uuid-id.yaml"
    path.write_text(
        source.replace(
            'id: "019109a0-b1c2-7def-8a00-112233445566"',
            'id: "ADR-L-9990"',
        ),
        encoding="utf-8",
    )
    parser = ADRParser()
    data = parser.parse_yaml(path)
    with pytest.raises(ADRSchemaValidationError):
        parser.validate_against_schema(data, parser._authoring_schema_name(data, "logical"))


def test_v13_physical_system_missing_system_object_fails(
    tmp_path: Path,
) -> None:
    source = (FIXTURES / "v1_3" / "physical-system-with-system.yaml").read_text(encoding="utf-8")
    lines = source.split("\n")
    filtered = [
        line
        for line in lines
        if not line.startswith("system:")
        and not line.startswith('  id: "019109a0-d5e6')
        and not line.startswith("  alias_id: SYS-")
        and not line.startswith("  alias_name: test-system")
    ]
    path = tmp_path / "no-system.yaml"
    path.write_text("\n".join(filtered), encoding="utf-8")
    parser = ADRParser()
    data = parser.parse_yaml(path)
    with pytest.raises(ADRSchemaValidationError, match="system"):
        parser.validate_against_schema(data, parser._authoring_schema_name(data, "physical_system"))


def test_v13_decision_missing_identity_envelope_fails(
    tmp_path: Path,
) -> None:
    source = (FIXTURES / "v1_3" / "logical-minimal.yaml").read_text(encoding="utf-8")
    path = tmp_path / "decision-no-identity.yaml"
    bad = source.replace("    alias_id: DEC-9990\n    alias_name: test-decision-one\n", "")
    path.write_text(bad, encoding="utf-8")
    parser = ADRParser()
    data = parser.parse_yaml(path)
    with pytest.raises(ADRSchemaValidationError):
        parser.validate_against_schema(data, parser._authoring_schema_name(data, "logical"))


def test_capability_manifest_includes_v13() -> None:
    manifest = capabilities()
    assert "1.3" in manifest.supported_adr_schema_versions
    assert "1.3" in manifest.provisional_adr_schema_versions


def test_parser_v13_dir_exists() -> None:
    parser = ADRParser()
    assert parser.schema_v13_dir.name == "v1_3"
    assert (parser.schema_v13_dir / "types.schema.json").is_file()
