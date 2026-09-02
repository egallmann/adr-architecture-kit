"""Production authoring v1.5 parser, models, and family-coexistence tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import Draft7Validator, RefResolver
from pydantic import ValidationError

from adr_kit.models.v1_4 import ExtensionRelationshipV14, PhysicalComponentADRv14
from adr_kit.models.v1_5 import (
    ExtensionRelationshipV15,
    PhysicalComponentADRv15,
    PhysicalSystemADRv15,
)
from adr_kit.parser import ADRParser, ADRParseError
from adr_kit.schema.family_inventory import (
    AUTHORING_SCHEMA_PACKAGES,
    EVIDENCE_ATTRIBUTION_SCHEMA_PACKAGES,
    packaged_authoring_schema_versions,
)

ROOT = Path(__file__).resolve().parents[1]
AUTHORING_V15 = ROOT / "schema" / "authoring" / "v1.5"
FIXTURES = ROOT / "tests" / "fixtures" / "authoring-v1.5-contract"
UUID_A = "018f4f20-0000-7000-8000-000000000001"
UUID_B = "018f4f20-0000-7000-8000-000000000002"
UUID_R = "018f4f20-0000-7000-8000-000000000003"

V15_SOURCES = (
    ("adrs/physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.yaml", PhysicalSystemADRv15),
    ("adrs/physical-system/ADR-PS-0002-adr-kit-compiler-and-validation-runtime.yaml", PhysicalSystemADRv15),
    ("adrs/physical-component/ADR-PC-0001-entity-registry-and-discovery-index.yaml", PhysicalComponentADRv15),
    ("adrs/physical-component/ADR-PC-0002-schema-and-contract-validation.yaml", PhysicalComponentADRv15),
    ("adrs/physical-component/ADR-PC-0003-compiler-pipeline-and-driver.yaml", PhysicalComponentADRv15),
    ("adrs/physical-component/ADR-PC-0008-project-scope-resolution.yaml", PhysicalComponentADRv15),
)


def _schema_store(schema_dir: Path) -> dict[str, dict]:
    import json

    store: dict[str, dict] = {}
    for schema_path in schema_dir.glob("*.schema.json"):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id")
        if schema_id:
            store[schema_id] = schema
    return store


def _json_schema_errors(schema_name: str, document: dict) -> list[str]:
    import json

    schema_path = AUTHORING_V15 / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resolver = RefResolver(schema_path.as_uri(), schema, store=_schema_store(AUTHORING_V15))
    return [error.message for error in Draft7Validator(schema, resolver=resolver).iter_errors(document)]


@pytest.mark.parametrize(("relpath", "model_type"), V15_SOURCES)
def test_production_v15_sources_parse(relpath: str, model_type: type) -> None:
    parsed = ADRParser().parse_adr(ROOT / relpath)
    assert isinstance(parsed, model_type)
    assert parsed.schema_version == "1.5"


def test_v14_namespaced_depends_on_remains_valid() -> None:
    relationship = ExtensionRelationshipV14(
        id=UUID_R,
        alias_id="WID-0001",
        alias_name="depends-on-extension",
        relationship_type="acme:depends_on",
        from_entity_id=UUID_A,
        to_entity_id=UUID_B,
        properties={},
        rationale="historical v1.4 extension local name",
    )
    assert relationship.relationship_type == "acme:depends_on"


def test_v15_namespaced_depends_on_is_reserved_core_collision() -> None:
    with pytest.raises(ValidationError, match="reserved core type"):
        ExtensionRelationshipV15(
            id=UUID_R,
            alias_id="WID-0001",
            alias_name="depends-on-extension",
            relationship_type="acme:depends_on",
            from_entity_id=UUID_A,
            to_entity_id=UUID_B,
            properties={},
            rationale="must collide after v1.5 reservation",
        )


def test_pc_component_topology_rejected_by_json_schema_and_pydantic() -> None:
    import yaml

    document = yaml.safe_load((FIXTURES / "invalid-pc-component-topology.yaml").read_text(encoding="utf-8"))
    assert _json_schema_errors("adr-physical-component.schema.json", document)
    with pytest.raises(ValidationError, match="component_topology"):
        PhysicalComponentADRv15.model_validate(document)


def test_unevaluated_properties_is_not_used_in_authoring_v15() -> None:
    for schema_path in AUTHORING_V15.glob("*.schema.json"):
        text = schema_path.read_text(encoding="utf-8")
        assert "unevaluatedProperties" not in text, schema_path


def test_evidence_v15_package_is_not_authoring() -> None:
    import importlib.resources

    evidence = importlib.resources.files("adr_kit.schema.v1_5")
    authoring = importlib.resources.files("adr_kit.schema.authoring.v1_5")
    assert (evidence / "implementation-attribution-evidence.schema.json").is_file()
    assert (authoring / "adr-logical.schema.json").is_file()
    assert not (evidence / "adr-logical.schema.json").is_file()
    assert not (authoring / "implementation-attribution-evidence.schema.json").is_file()
    assert AUTHORING_SCHEMA_PACKAGES["1.5"] == "adr_kit.schema.authoring.v1_5"
    assert EVIDENCE_ATTRIBUTION_SCHEMA_PACKAGES["1.5"] == "adr_kit.schema.v1_5"
    assert "1.5" in packaged_authoring_schema_versions()


def test_parser_still_loads_evidence_v15_from_schema_v15_dir() -> None:
    parser = ADRParser()
    assert parser.schema_v15_dir.name == "v1_5"
    assert parser.schema_authoring_v15_dir.name == "v1_5"
    assert "implementation_attribution_evidence_v1_5" in parser._schemas
    assert "logical_v1_5" in parser._schemas
    evidence_id = parser._schemas["implementation_attribution_evidence_v1_5"]["$id"]
    logical_id = parser._schemas["logical_v1_5"]["$id"]
    assert evidence_id != logical_id
    assert logical_id.endswith("authoring/v1.5/adr-logical.schema.json")
    assert evidence_id.endswith("implementation-attribution-evidence.schema.json")


def test_v14_physical_component_still_parses() -> None:
    # Frozen v1.4 path remains independent of authoring v1.5 package split.
    assert PhysicalComponentADRv14.model_fields["schema_version"].default == "1.4"


def test_unsupported_generic_physical_authoring_v15_fails_closed() -> None:
    parser = ADRParser()
    assert parser._authoring_schema_name({"schema_version": "1.5", "adr_type": "physical"}, "physical") == (
        "physical_v1_5"
    )
    with pytest.raises(ADRParseError, match="not found"):
        parser.validate_against_schema({"schema_version": "1.5"}, "physical_v1_5")
