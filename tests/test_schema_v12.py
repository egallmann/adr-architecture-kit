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
    "adr-common.schema.json": "cf9e6460ce53ef2ae8a566dbc383f881bcc0d8f4ac1c5ee8a0d10f0009c5c35d",
    "adr-logical.schema.json": "c49d5cebbbd83ed3faa2524ab3af8291606eeaaa9450610efa12e9e392b92c71",
    "adr-physical-base.schema.json": "89105a66cec6eddba617192258e44917d0c02956ad8778ac7c6f603e7717d6f5",
    "adr-physical-component.schema.json": "f2c922a781aaed64459e661c3bd91f2952288f78ec3b0e089a13f5522390d2c1",
    "adr-physical-system.schema.json": "93c2ddb3fcae2a7f3a9f3b7d876ea4cb1b1fb09e659e0de7ad12ca526be7044e",
    "adr-physical.schema.json": "44c461b49a48483fb1555c53e62544e838ae0eba17608ec3dbf4ccb6ece10470",
    "invariant.schema.json": "5e61818ece9eee3169ab51c24b8ad599a01fd220d336fd4cab4ca64b40a630a1",
    "manifest.schema.json": "15e02c4053e7d6d7f415e70feab703bc7a37cd02c69c1f6203beccb061da32a2",
    "project-metadata.schema.json": "882a883abe9ccb3267c6d61c1081138145a6e0d26898bc42d1a8d181e4e0764a",
    "types.schema.json": "fae298fafd55e0c1bd0eb2233380086f7f85710d83809a7876d1da1f2a736bca",
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
    assert parser.schema_v13_dir.name == "v1_3"
    assert (parser.schema_v12_dir / "adr-logical.schema.json").is_file()
    assert (parser.schema_v12_dir / "adr-physical-system.schema.json").is_file()
    assert (parser.schema_v13_dir / "adr-logical.schema.json").is_file()
    assert (parser.schema_v13_dir / "adr-physical-system.schema.json").is_file()


def test_v1_0_fixture_still_parses_and_v1_1_artifact_stays_loadable() -> None:
    parser = ADRParser()

    logical = parser.parse_logical_adr(FIXTURES / "valid" / "logical-minimal.yaml")
    registry = parser.parse_normalized_entity_registry(
        ROOT / "tests" / "golden" / "expected" / "entity_registry.yaml"
    )

    assert logical.schema_version == "1.0"
    # Current golden corpus is model 2.0 after the v1.3 identity migration.
    assert registry.schema_version == "2.0"
    # Legacy 1.1 registry parsing remains available for migration consumers.
    legacy = parser.parse_normalized_entity_registry_from_data(
        "\n".join(
            [
                "schema_version: '1.1'",
                "type: normalized_entity_registry",
                "entities: []",
            ]
        )
    )
    assert legacy.schema_version == "1.1"


def test_capability_manifest_reports_v1_2_as_provisional_without_promoting_v1_1() -> None:
    manifest = capabilities()

    assert manifest.supported_adr_schema_versions == ("1.0", "1.1", "1.2", "1.3")
    assert manifest.stable_adr_schema_versions == ("1.0",)
    assert manifest.provisional_adr_schema_versions == ("1.1", "1.2", "1.3")


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


@pytest.mark.parametrize("version", ["1.1", "2.0"])
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


def test_v1_3_minimal_without_identity_fails(tmp_path: Path) -> None:
    """A v1.0-shaped fixture relabeled to 1.3 must fail schema validation."""
    source = (FIXTURES / "valid" / "logical-minimal.yaml").read_text(encoding="utf-8")
    path = tmp_path / "v13-missing-identity.yaml"
    path.write_text(
        source.replace('schema_version: "1.0"', 'schema_version: "1.3"'), encoding="utf-8"
    )

    with pytest.raises(ADRSchemaValidationError):
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
