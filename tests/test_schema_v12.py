"""Phase 2 contracts for additive ADR authoring schema v1.2."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from adr_kit.api import capabilities
from adr_kit.parser import ADRParseError, ADRParser, ADRSchemaValidationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
V1_0_SHA256 = {
    "adr-common.schema.json": "a46a80d7a39d815d74d7c458d84c3fe7fe272a751c3b5cb5f274baf1502361e2",
    "adr-logical.schema.json": "ca1a1c50dd165a9f1112f2fcacdd865ea4e5852f4ed691013bbc1203b1dc7294",
    "adr-physical-base.schema.json": "e478799e0a7dd9efaf55a6e58dd4878928848339c381ed68358fe4ff941cc60f",
    "adr-physical-component.schema.json": "5087147cc171f0500eba04e603c5d197015e554eda7b21e753a614a1df488c4e",
    "adr-physical-system.schema.json": "5b17763bb6c368d3d0e393ac779c2dad04298600b419446ed7a86420afb517a3",
    "adr-physical.schema.json": "d5fcc7306ab39869591d0399c03eec0f5db06d700cb59cd7b6edab4444b88568",
    "invariant.schema.json": "20943722590da6e061508f077492f7b37b031e1a121c5317f920f3b3ff6a22a8",
    "manifest.schema.json": "1b75633af94fe312791f94740eeccebf8e79de8930808302dd47641ffa9cf719",
    "project-metadata.schema.json": "ffd244960f40863f001105891e355c04f1a68610643dfda078931281b37b457e",
    "types.schema.json": "e3838f9932c76d6794b76e191faaeb85a57c8d89bc4d01bb47fdf13b18f3b8da",
}


def test_v1_0_schema_bytes_remain_frozen() -> None:
    actual = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "schema" / "v1.0").glob("*.json"))
    }
    assert actual == V1_0_SHA256


def test_parser_discovers_all_schema_lines_from_package_resources() -> None:
    parser = ADRParser()

    assert parser.schema_dir.name == "v1_0"
    assert parser.schema_v11_dir.name == "v1_1"
    assert parser.schema_v12_dir.name == "v1_2"
    assert (parser.schema_v12_dir / "adr-logical.schema.json").is_file()
    assert (parser.schema_v12_dir / "adr-physical-system.schema.json").is_file()


def test_v1_0_fixture_still_parses_and_v1_1_artifact_stays_loadable() -> None:
    parser = ADRParser()

    logical = parser.parse_logical_adr(FIXTURES / "valid" / "logical-minimal.yaml")
    registry = parser.parse_normalized_entity_registry(
        ROOT / "tests" / "golden" / "expected" / "entity_registry.yaml"
    )

    assert logical.schema_version == "1.0"
    assert registry.schema_version == "1.1"


def test_capability_manifest_reports_v1_2_as_provisional_without_promoting_v1_1() -> None:
    manifest = capabilities()

    assert manifest.supported_adr_schema_versions == ("1.0", "1.1", "1.2")
    assert manifest.stable_adr_schema_versions == ("1.0",)
    assert manifest.provisional_adr_schema_versions == ("1.1", "1.2")


def test_valid_v1_2_logical_and_topology_fixtures_parse() -> None:
    parser = ADRParser()

    logical = parser.parse_logical_adr(FIXTURES / "v1_2" / "logical-bindings.yaml")
    physical_system = parser.parse_physical_system_adr(
        FIXTURES / "v1_2" / "physical-system-topology.yaml"
    )

    assert logical.schema_version == "1.2"
    assert logical.substrate_bindings[0].artifact_id == "SUBSTRATE-0001"
    assert logical.rule_bindings[0].affected_entities[1].qualified_id == (
        "provider-architecture:CAP-0042"
    )
    assert logical.evidence_expectations[0].expectation_id == "EVID-9801"
    assert physical_system.component_topology is not None
    assert physical_system.component_topology.components[0].id == "TOPO-0001"


@pytest.mark.parametrize("version", ["1.1", "1.3", "2.0"])
def test_authoring_version_dispatch_rejects_non_authoring_lines(
    tmp_path: Path, version: str
) -> None:
    source = (FIXTURES / "valid" / "logical-minimal.yaml").read_text(encoding="utf-8")
    path = tmp_path / "unsupported.yaml"
    path.write_text(
        source.replace('schema_version: "1.0"', f'schema_version: "{version}"'), encoding="utf-8"
    )

    with pytest.raises(ADRParseError, match=f"Unsupported ADR schema_version '{version}'"):
        ADRParser().parse_logical_adr(path)


def test_v1_2_invalid_fingerprint_fails_semantic_parsing(tmp_path: Path) -> None:
    source = (FIXTURES / "v1_2" / "logical-bindings.yaml").read_text(encoding="utf-8")
    path = tmp_path / "invalid-fingerprint.yaml"
    path.write_text(
        source.replace(
            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "not-a-fingerprint",
        ),
        encoding="utf-8",
    )

    with pytest.raises((ADRParseError, ADRSchemaValidationError), match="fingerprint"):
        ADRParser().parse_logical_adr(path)


def test_v1_2_implicit_cross_repository_reference_fails(tmp_path: Path) -> None:
    source = (FIXTURES / "v1_2" / "logical-bindings.yaml").read_text(encoding="utf-8")
    path = tmp_path / "implicit-cross-repo.yaml"
    path.write_text(
        source.replace("  - DEC-9801\n  - namespace:", "  - provider:CAP-0042\n  - namespace:"),
        encoding="utf-8",
    )

    with pytest.raises((ADRParseError, ADRSchemaValidationError), match="not valid under any"):
        ADRParser().parse_logical_adr(path)


def test_v1_0_does_not_silently_accept_v1_2_binding_fields(tmp_path: Path) -> None:
    source = (FIXTURES / "v1_2" / "logical-bindings.yaml").read_text(encoding="utf-8")
    path = tmp_path / "misversioned-bindings.yaml"
    path.write_text(
        source.replace("schema_version: '1.2'", "schema_version: '1.0'"), encoding="utf-8"
    )

    with pytest.raises(ADRParseError, match="require ADR schema_version 1.2"):
        ADRParser().parse_logical_adr(path)


def test_duplicate_binding_identity_fails_semantic_parsing(tmp_path: Path) -> None:
    source = (FIXTURES / "v1_2" / "logical-bindings.yaml").read_text(encoding="utf-8")
    binding = """\
- external_namespace: ste-substrate
  artifact_id: SUBSTRATE-0001
  kind: context_domain
  version: 1.0.0
  fingerprint: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  role: required_context
  selected_by: DEC-9801
"""
    path = tmp_path / "duplicate-binding.yaml"
    path.write_text(
        source.replace("rule_bindings:\n", binding + "rule_bindings:\n"), encoding="utf-8"
    )

    with pytest.raises(ADRParseError, match="duplicate substrate binding identity"):
        ADRParser().parse_logical_adr(path)


def test_rule_disposition_requirements_fail_closed(tmp_path: Path) -> None:
    source = (FIXTURES / "v1_2" / "logical-bindings.yaml").read_text(encoding="utf-8")
    path = tmp_path / "missing-rationale.yaml"
    path.write_text(
        source.replace(
            "  rationale: The local decision narrows the provider rule without redefining it.\n",
            "",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ADRSchemaValidationError, match="rationale.*required property"):
        ADRParser().parse_logical_adr(path)
