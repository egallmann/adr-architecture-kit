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


def test_adr_l_0029_authorizes_successors_and_keeps_ownership_in_rust() -> None:
    text = ADR_PATH.read_text(encoding="utf-8")

    for successor in SUCCESSOR_CONTRACTS:
        assert successor in text
    assert "No successor contract directory or resource" in text


def test_adc11_and_cec10_are_the_only_authorized_successor_contract_resources() -> None:
    absent_successor_paths = (ROOT / "contracts" / "architecture-authoring" / "v1.0",)
    assert (ROOT / "contracts" / "authoring-domain" / "v1.1").is_dir()
    assert (ROOT / "contracts" / "custom-entity" / "v1.0").is_dir()
    assert (ROOT / "contracts" / "authoring-construction" / "v1.0").is_dir()
    assert (ROOT / "schema" / "authoring" / "v1.7").is_dir()
    assert (ROOT / "schema" / "normalized-model" / "v2.4").is_dir()
    assert (ROOT / "contracts" / "architecture-interpretation" / "v1.1").is_dir()
    assert (ROOT / "contracts" / "semantic-core" / "v1.2" / "contract.json").is_file()
    assert not any(path.exists() for path in absent_successor_paths)


def test_protocol_exposure_keeps_semantics_in_rust_and_preserves_host_api_scope() -> None:
    from adr_kit.core import semantic_core_capabilities

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
    assert capabilities["peer_host_operations"][1:3] == [
        "validate_authoring",
        "construct_authoring_set",
    ]
    assert "validate_authoring" not in json.dumps(capabilities["authoring_domain"])
    assert "construct_authoring_set" not in json.dumps(capabilities["authoring_domain"])
    assert semantic_core_capabilities()["operations_by_version"]["1.2"] == (
        "validate_authoring",
        "construct_authoring_set",
    )

    rust = (ROOT / "core" / "src" / "lib.rs").read_text(encoding="utf-8")
    assert "authoring_construction::validate_authoring_request" in rust
    assert "authoring_construction_orchestration::construct_authoring_set" in rust
    for path in (
        ROOT / "src" / "adr_kit" / "core" / "semantic_core.py",
        ROOT / "packages" / "node" / "src" / "node" / "core.ts",
    ):
        text = path.read_text(encoding="utf-8")
        assert "def validate_authoring" not in text
        assert "def construct_authoring_set" not in text
        assert "function validateAuthoring" not in text
        assert "function constructAuthoringSet" not in text

    adr_0030 = yaml.safe_load(ADR_0030_PATH.read_text(encoding="utf-8"))
    assert adr_0030["alias_id"] == "ADR-L-0030"
    assert adr_0030["status"] == "accepted"
    assert "Exact Source Basis" in adr_0030["decisions"][0]["summary"]
    assert "canonical Rust semantic" in ADR_0030_PATH.read_text(encoding="utf-8")
