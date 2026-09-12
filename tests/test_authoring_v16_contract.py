"""Authoring v1.6 NormativeProposition contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, RefResolver
from pydantic import ValidationError

from adr_kit.models.v1_6 import NormativePropositionV16
from adr_kit.models.project_metadata import ProjectInfo
from adr_kit.parser import ADRParser

ROOT = Path(__file__).resolve().parents[1]
AUTHORING_V16 = ROOT / "schema" / "authoring" / "v1.6"
UUID = "019109a0-b1c2-7def-8a00-112233445566"


def _np(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": UUID,
        "alias_id": "NP-0001",
        "alias_name": "explicit-contract",
        "statement": "The contract MUST remain explicit.",
        "normative_force": "MUST",
        "scope": "global",
    }
    value.update(overrides)
    return value


def _logical_document() -> dict[str, object]:
    return {
        "schema_version": "1.6",
        "adr_type": "logical",
        "id": "019109a0-b1c2-7def-8a00-112233445566",
        "alias_id": "ADR-L-0001",
        "alias_name": "normative-authority",
        "title": "Normative authority",
        "status": "proposed",
        "created_date": "2026-08-28",
        "authors": ["test.author"],
        "context": "A bounded context.",
        "decisions": [
            {
                "id": "019109a0-b1c2-7def-8a00-112233445567",
                "alias_id": "DEC-0001",
                "alias_name": "explicit-contract",
                "summary": "Use an explicit contract.",
                "rationale": "It is reviewable.",
            }
        ],
        "normative_propositions": [_np()],
    }


def test_authoring_v16_np_is_parent_agnostic_and_parser_selects_successor() -> None:
    parser = ADRParser()
    assert parser._authoring_schema_name(_logical_document(), "logical") == "logical_v1_6"
    parser.validate_against_schema(_logical_document(), "logical_v1_6")
    proposition = NormativePropositionV16.model_validate(_np())
    assert proposition.normative_force == "MUST"


@pytest.mark.parametrize("parent", ["logical", "physical-system", "physical-component"])
def test_authoring_v16_schema_accepts_np_in_each_declaring_parent(parent: str) -> None:
    document = _logical_document()
    document["adr_type"] = parent
    if parent == "physical-system":
        document.update(
            {
                "alias_id": "ADR-PS-0001",
                "implements_logical": [UUID],
                "technology_stack": [
                    {
                        "category": "language",
                        "name": "Python",
                        "version": "3.12",
                        "rationale": "test",
                    }
                ],
                "system": {"id": UUID, "alias_id": "SYS-0001", "alias_name": "test-system"},
            }
        )
        schema_name = "physical_system"
    elif parent == "physical-component":
        document.update(
            {
                "alias_id": "ADR-PC-0001",
                "implements_logical": [UUID],
                "technology_stack": [
                    {
                        "category": "language",
                        "name": "Python",
                        "version": "3.12",
                        "rationale": "test",
                    }
                ],
                "implements_system": [UUID],
                "component_specifications": [
                    {
                        "id": UUID,
                        "alias_id": "COMP-0001",
                        "alias_name": "test-component",
                        "name": "Test component",
                        "type": "worker",
                        "responsibilities": "Does test work.",
                        "generation_context": {
                            "purpose": "Testing",
                            "key_responsibilities": ["test"],
                        },
                        "interfaces": [
                            {
                                "id": UUID,
                                "alias_id": "IFACE-0001",
                                "alias_name": "test-interface",
                                "type": "CLI",
                                "specification": "A test interface.",
                            }
                        ],
                    }
                ],
            }
        )
        schema_name = "physical_component"
    else:
        schema_name = "logical"
    parser = ADRParser()
    parser.validate_against_schema(document, f"{schema_name}_v1_6")


@pytest.mark.parametrize(
    "invalid",
    [
        {"normative_force": "MAY", "polarity": "positive"},
        {"normative_force": "UNKNOWN"},
        {"scope": None},
        {"lifecycle_stage": "active"},
    ],
)
def test_authoring_v16_np_rejects_inference_or_independent_lifecycle(
    invalid: dict[str, object],
) -> None:
    value = _np(**invalid)
    with pytest.raises(ValidationError):
        NormativePropositionV16.model_validate(value)

    schema = json.loads((AUTHORING_V16 / "adr-common.schema.json").read_text(encoding="utf-8"))
    types = json.loads((AUTHORING_V16 / "types.schema.json").read_text(encoding="utf-8"))
    store = {schema["$id"]: schema, types["$id"]: types}
    resolver = RefResolver((AUTHORING_V16 / "adr-common.schema.json").as_uri(), schema, store=store)
    errors = list(
        Draft7Validator(
            schema["definitions"]["normative_proposition"], resolver=resolver
        ).iter_errors(value)
    )
    assert errors


def test_specification_project_type_is_shared_model_value() -> None:
    assert (
        ProjectInfo(name="ste-spec", description="A specification", type="specification").type
        == "specification"
    )
    with pytest.raises(ValidationError):
        ProjectInfo(name="ste-spec", description="A specification", type="not-a-project-type")
