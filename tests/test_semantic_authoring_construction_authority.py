"""Protect the accepted ADR-L-0029 authority boundary."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = (
    ROOT
    / "adrs"
    / "logical"
    / "ADR-L-0029-semantic-authoring-construction-and-candidate-authority.yaml"
)

DECISION_ALIASES = {
    "DEC-0128",
    "DEC-0129",
    "DEC-0184",
    "DEC-0185",
    "DEC-0186",
    "DEC-0187",
    "DEC-0188",
    "DEC-0189",
    "DEC-0190",
    "DEC-0191",
    "DEC-0192",
    "DEC-0193",
    "DEC-0194",
    "DEC-0195",
    "DEC-0196",
    "DEC-0197",
}

INVARIANT_ALIASES = {
    *(f"INV-{number:04d}" for number in range(113, 128)),
    "INV-0165",
    "INV-0166",
    "INV-0167",
    "INV-0168",
}

SUCCESSOR_CONTRACTS = (
    "ADC 1.1",
    "Custom Entity Contract 1.0",
    "Authoring Construction Contract 1.0",
    "authoring 1.7",
    "normalized-model 2.4",
    "architecture-interpretation 1.1",
    "semantic-core 1.2",
    "architecture-authoring@1.0",
)


def test_adr_l_0029_is_accepted_and_uses_the_supported_representation() -> None:
    document = yaml.safe_load(ADR_PATH.read_text(encoding="utf-8"))

    assert document["alias_id"] == "ADR-L-0029"
    assert document["status"] == "accepted"
    assert document["schema_version"] == "1.5"
    assert {item["alias_id"] for item in document["decisions"]} == DECISION_ALIASES
    assert {item["alias_id"] for item in document["invariants"]} == INVARIANT_ALIASES
    assert "normative_propositions" not in document


def test_adr_l_0029_authorizes_successors_without_advertising_implementation() -> None:
    text = ADR_PATH.read_text(encoding="utf-8")

    for successor in SUCCESSOR_CONTRACTS:
        assert successor in text
    assert "None is implemented, advertised, or released" in text
    assert "No successor contract directory or resource" in text
