"""Phase 2 contracts for additive ADR authoring schema v1.2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from adr_kit.api import capabilities
from adr_kit.parser import ADRParseError, ADRParser, ADRSchemaValidationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def test_v1_0_inventory_digests_match_current_canonical_bytes() -> None:
    """Per-release fingerprint: inventory sha256 must match current canonical bytes."""
    inventory = json.loads(
        (ROOT / "tests" / "fixtures" / "schema-contract-inventory.json").read_text(encoding="utf-8")
    )
    for record in inventory["records"]:
        canonical_path = record.get("canonical_path", "")
        if not canonical_path.startswith("schema/v1.0/"):
            continue
        path = ROOT / canonical_path
        assert path.is_file(), canonical_path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == record["sha256"], canonical_path


def test_v1_0_stable_compatibility_line_accepts_legacy_and_split_physical_ids(
    tmp_path: Path,
) -> None:
    """INV-0077: previously valid v1.0 docs remain valid; physical slots accept P|PS|PC."""
    parser = ADRParser()
    logical = parser.parse_logical_adr(FIXTURES / "valid" / "logical-minimal.yaml")
    assert logical.schema_version == "1.0"

    types = json.loads((ROOT / "schema" / "v1.0" / "types.schema.json").read_text(encoding="utf-8"))
    assert types["definitions"]["adr_id_physical"]["pattern"] == r"^ADR-P-\d{4}$"
    assert "adr_id_physical_any" in types["definitions"]
    assert types["definitions"]["adr_id_physical_any"]["pattern"] == r"^ADR-P(S|C)?-\d{4}$"

    for physical_id in ("ADR-P-0001", "ADR-PS-0001", "ADR-PC-0001"):
        data = {
            "schema_version": "1.0",
            "type": "manifest",
            "generated_date": "2026-09-05T00:00:00Z",
            "generated_from": "adrs/**/*.yaml",
            "adrs": [],
            "gaps_summary": {"total": 0, "blocking": 0, "by_adr": {}},
            "statistics": {"total_adrs": 0, "logical_adrs": 0, "physical_adrs": 0},
            "by_technology": {"python": [physical_id]},
        }
        path = tmp_path / f"manifest-{physical_id}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        parser.parse_manifest(path)

    bad = {
        "schema_version": "1.0",
        "type": "manifest",
        "generated_date": "2026-09-05T00:00:00Z",
        "generated_from": "adrs/**/*.yaml",
        "adrs": [],
        "gaps_summary": {"total": 0, "blocking": 0, "by_adr": {}},
        "statistics": {"total_adrs": 0, "logical_adrs": 0, "physical_adrs": 0},
        "by_technology": {"python": ["ADR-L-0001"]},
    }
    bad_path = tmp_path / "manifest-bad.yaml"
    bad_path.write_text(yaml.safe_dump(bad, sort_keys=False), encoding="utf-8")
    with pytest.raises(ADRSchemaValidationError):
        parser.parse_manifest(bad_path)


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
    # Current golden corpus is model 2.2 after the v1.5 authoring / topology cutover.
    assert registry.schema_version == "2.2"
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

    assert manifest.supported_adr_schema_versions == ("1.0", "1.1", "1.2", "1.3", "1.4", "1.5")
    assert manifest.stable_adr_schema_versions == ("1.0",)
    assert manifest.provisional_adr_schema_versions == ("1.1", "1.2", "1.3", "1.4", "1.5")


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
