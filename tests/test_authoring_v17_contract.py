"""Authoring v1.7 schema loading and installed-package parity."""

from __future__ import annotations

import hashlib
from pathlib import Path

from adr_kit.models.v1_7 import LogicalADRv17
from adr_kit.parser.yaml_parser import ADRParser
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
