"""Authoring v1.7 schema loading and installed-package parity."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from adr_kit.models.v1_7 import LogicalADRv17
from adr_kit.parser.yaml_parser import ADRParser, ADRSchemaValidationError
from adr_kit.schema.family_inventory import AUTHORING_SCHEMA_PACKAGES

ROOT = Path(__file__).resolve().parents[1]
AUTHORING_V17 = ROOT / "schema" / "authoring" / "v1.7"
RESOURCE_NAMES = (
    "types.schema.json",
    "adr-common.schema.json",
    "adr-logical.schema.json",
    "adr-physical-base.schema.json",
    "adr-physical-system.schema.json",
    "adr-physical-component.schema.json",
)


def _logical_document() -> dict[str, object]:
    return {
        "schema_version": "1.7",
        "adr_type": "logical",
        "id": "01940000-0000-7000-8000-000000000001",
        "alias_id": "ADR-L-0001",
        "alias_name": "authoring-v17",
        "title": "Authoring v1.7 contract",
        "status": "accepted",
        "created_date": "2026-01-01",
        "authors": ["test"],
        "context": "A complete v1.7 logical document.",
        "decisions": [
            {
                "id": "01940000-0000-7000-8000-000000000002",
                "alias_id": "DEC-0001",
                "alias_name": "choose-v17",
                "summary": "Use authoring v1.7",
                "rationale": "The accepted ACC source contract requires it.",
                "alternatives_considered": [
                    {
                        "name": "Authoring v1.6",
                        "rejected_because": "The accepted source contract is v1.7.",
                    }
                ],
                "consequences": {
                    "positive": ["The source contract is explicit."],
                    "negative": ["Consumers must resolve the v1.7 schema family."],
                },
            }
        ],
    }


def _physical_component_document() -> dict[str, object]:
    return {
        "schema_version": "1.7",
        "adr_type": "physical-component",
        "id": "01940000-0000-7000-8000-000000000011",
        "alias_id": "ADR-PC-0001",
        "alias_name": "authoring-v17-component",
        "title": "Authoring v1.7 component",
        "status": "accepted",
        "created_date": "2026-01-01",
        "authors": ["test"],
        "implements_logical": ["01940000-0000-7000-8000-000000000001"],
        "implements_system": ["01940000-0000-7000-8000-000000000003"],
        "context": "A complete v1.7 physical component document.",
        "technology_stack": [
            {"category": "framework", "name": "Test", "version": "1", "rationale": "Test fixture."}
        ],
        "component_specifications": [
            {
                "id": "01940000-0000-7000-8000-000000000012",
                "alias_id": "COMP-0001",
                "alias_name": "test-component",
                "name": "Test component",
                "type": "service",
                "responsibilities": "Validates authoring v1.7.",
                "generation_context": {"purpose": "Test", "key_responsibilities": ["Validate"]},
                "interfaces": [
                    {
                        "id": "01940000-0000-7000-8000-000000000013",
                        "alias_id": "IFACE-0001",
                        "alias_name": "test-interface",
                        "type": "REST",
                        "specification": "Test interface.",
                    }
                ],
            }
        ],
        "implementation_decisions": [
            {
                "id": "01940000-0000-7000-8000-000000000014",
                "alias_id": "IMPL-0001",
                "alias_name": "choose-v17",
                "summary": "Use the v1.7 schema.",
                "rationale": "It is the accepted source contract.",
                "alternatives_considered": [
                    {
                        "name": "An older schema",
                        "rejected_because": "It lacks the accepted contract.",
                    }
                ],
            }
        ],
    }


def test_v17_is_explicitly_provisional_and_packaged() -> None:
    assert AUTHORING_SCHEMA_PACKAGES["1.7"] == "adr_kit.schema.authoring.v1_7"
    for name in RESOURCE_NAMES:
        canonical = AUTHORING_V17 / name
        mirror = ROOT / "src" / "adr_kit" / "schema" / "authoring" / "v1_7" / name
        assert canonical.read_bytes() == mirror.read_bytes()
        assert hashlib.sha256(canonical.read_bytes()).hexdigest()


def test_parser_loads_v17_from_the_packaged_schema_family() -> None:
    parser = ADRParser()
    document = _logical_document()
    assert parser._authoring_schema_name(document, "logical") == "logical_v1_7"
    parser.validate_against_schema(document, "logical_v1_7")
    parsed = LogicalADRv17(**document)
    assert parsed.schema_version == "1.7"
    assert parsed.id == document["id"]


def test_v17_schema_resolves_decision_and_implementation_refs() -> None:
    parser = ADRParser()
    logical = _logical_document()
    physical = _physical_component_document()

    parser.validate_against_schema(logical, "logical_v1_7")
    parser.validate_against_schema(physical, "physical_component_v1_7")

    malformed_logical = {
        **logical,
        "decisions": [{**logical["decisions"][0], "consequences": {"positive": [7]}}],
    }
    malformed_physical = {
        **physical,
        "implementation_decisions": [
            {
                **physical["implementation_decisions"][0],
                "alternatives_considered": [{"name": 7, "rejected_because": "bad"}],
            }
        ],
    }
    with pytest.raises(ADRSchemaValidationError):
        parser.validate_against_schema(malformed_logical, "logical_v1_7")
    with pytest.raises(ADRSchemaValidationError):
        parser.validate_against_schema(malformed_physical, "physical_component_v1_7")
