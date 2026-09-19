"""Protect the accepted ADR-L-0031 non-recursive binding authority."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = (
    ROOT
    / "adrs"
    / "logical"
    / "ADR-L-0031-non-recursive-semantic-contract-conformance-binding.yaml"
)

DECISION_ALIASES = {f"DEC-{number:04d}" for number in range(240, 247)}
INVARIANT_ALIASES = {f"INV-{number:04d}" for number in range(240, 249)}


def _document() -> dict[str, object]:
    return yaml.safe_load(ADR_PATH.read_text(encoding="utf-8"))


def test_adr_l_0031_is_accepted_and_pins_non_recursive_binding_authority() -> None:
    document = _document()
    text = ADR_PATH.read_text(encoding="utf-8")

    assert document["alias_id"] == "ADR-L-0031"
    assert document["status"] == "accepted"
    assert document["schema_version"] == "1.5"
    assert {item["alias_id"] for item in document["decisions"]} == DECISION_ALIASES
    assert {item["alias_id"] for item in document["invariants"]} == INVARIANT_ALIASES
    assert {
        "01a083dd-22b5-726d-8e49-01851bde3ba5",
        "01a09938-a15b-75ed-8326-212e21bd3cfe",
        "01a09cf0-179e-71cc-b150-d4a79551b939",
    } <= set(document["related_adrs"])
    assert "$enclosing_scf" in text
    assert "scf:v1:sha256" in text
    assert "exact content-addressed resource closure" in text


def test_self_binding_is_verified_closed_derived_and_non_production() -> None:
    text = ADR_PATH.read_text(encoding="utf-8")

    for phrase in (
        "definition verifies against its declared SCF",
        "complete required resource closure verifies successfully",
        "exact manifest-qualified resource",
        "derived execution projection",
        "contract-declared locations",
        "MUST reject an unbound $enclosing_scf marker",
        "MUST change its exact resource digest",
        "MUST NOT create persistence",
    ):
        assert phrase in text

    assert not (ROOT / "contracts" / "semantic-core" / "v1.2").exists()
    assert not (ROOT / "contracts" / "architecture-authoring" / "v1.0").exists()


def test_self_binding_does_not_advertise_construction_capability() -> None:
    capabilities = json.loads(
        (ROOT / "src" / "adr_kit" / "compatibility" / "host-capabilities.json").read_text(
            encoding="utf-8"
        )
    )
    serialized = json.dumps(capabilities)
    assert "construct_authoring_set" not in serialized
    assert "validate_authoring" not in serialized
