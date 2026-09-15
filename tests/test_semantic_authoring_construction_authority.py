"""Protect the accepted ADR-L-0029 authority boundary."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = (
    ROOT
    / "adrs"
    / "logical"
    / "ADR-L-0029-semantic-authoring-construction-and-candidate-authority.yaml"
)
ADR_0030_PATH = (
    ROOT
    / "adrs"
    / "logical"
    / "ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.yaml"
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
    assert "01a09cf0-179e-71cc-b150-d4a79551b939" in document["related_adrs"]

    round_trip_rationale = next(
        item["rationale"] for item in document["decisions"] if item["alias_id"] == "DEC-0191"
    )
    assert "ADR-L-0030" in round_trip_rationale
    assert "Exact Source Basis" in round_trip_rationale
    assert "canonical Rust semantic execution" in round_trip_rationale


def test_adr_l_0029_authorizes_successors_without_advertising_implementation() -> None:
    text = ADR_PATH.read_text(encoding="utf-8")

    for successor in SUCCESSOR_CONTRACTS:
        assert successor in text
    assert "None is implemented, advertised, or released" in text
    assert "No successor contract directory or resource" in text


def test_adc11_is_the_only_authorized_successor_contract_resource() -> None:
    successor_paths = (
        ROOT / "contracts" / "custom-entity" / "v1.0",
        ROOT / "contracts" / "authoring-construction" / "v1.0",
        ROOT / "schema" / "authoring" / "v1.7",
        ROOT / "schema" / "v2.4",
        ROOT / "contracts" / "architecture-interpretation" / "v1.1",
        ROOT / "contracts" / "semantic-core" / "v1.2",
        ROOT / "contracts" / "architecture-authoring" / "v1.0",
    )
    assert (ROOT / "contracts" / "authoring-domain" / "v1.1").is_dir()
    assert not any(path.exists() for path in successor_paths)


def test_current_capability_and_execution_authority_remain_unchanged() -> None:
    capabilities = json.loads(
        (ROOT / "src" / "adr_kit" / "compatibility" / "host-capabilities.json").read_text(
            encoding="utf-8"
        )
    )
    assert capabilities["authoring_domain"]["capabilities"] == ["authoring.discovery"]
    assert capabilities["authoring_domain"]["operations"] == [
        "describe_contract",
        "list_types",
        "describe_type",
    ]

    adr_0030 = yaml.safe_load(ADR_0030_PATH.read_text(encoding="utf-8"))
    assert adr_0030["alias_id"] == "ADR-L-0030"
    assert adr_0030["status"] == "accepted"
    assert "Exact Source Basis" in adr_0030["decisions"][0]["summary"]
    assert "canonical Rust semantic" in ADR_0030_PATH.read_text(encoding="utf-8")
