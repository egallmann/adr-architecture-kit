"""Authority checks for the retained, non-current architecture-materialization successor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import (
    load_semantic_resource,
    validate_semantic_contract_profile,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC = ROOT / "contracts" / "semantic-contract" / "v1.0"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_successor_profile_has_exact_locked_tuple_and_current_profile_is_separate() -> None:
    profile = _read(SEMANTIC / "profiles" / "architecture-materialization-1.1.json")
    schema = _read(SEMANTIC / "semantic-contract-profile.schema.json")
    assert not list(Draft202012Validator(schema).iter_errors(profile))
    assert profile["profileId"] == "architecture-materialization@1.1"
    assert {
        (item["semanticContractFamily"], item["semanticContractVersion"])
        for item in profile["participatingFamilies"]
    } == {
        ("architecture-interpretation", "1.1"),
        ("normalized-model", "2.4"),
        ("normative-semantics", "1.0"),
    }
    assert _read(SEMANTIC / "profiles" / "architecture-materialization-1.0.json")["profileId"] == (
        "architecture-materialization@1.0"
    )


def test_successor_is_retained_and_executable_without_becoming_current() -> None:
    set_path = (
        SEMANTIC
        / "sets"
        / "scs-v1-sha256-2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020.json"
    )
    retained_set = _read(set_path)
    assert {member["semanticContractVersion"] for member in retained_set["members"]} == {
        "1.1",
        "2.4",
        "1.0",
    }
    qualifications = _read(SEMANTIC / "qualifications" / "architecture-materialization-1.1.json")
    materialization = next(
        item for item in qualifications if item["operation"] == "materialize_architecture"
    )
    assert materialization["installedExecutionSupport"] is True
    assert materialization["newUsePolicy"] == "permitted"
    assert materialization["direction"] == "forward"
    assert all(
        item["installedExecutionSupport"] is False and item["newUsePolicy"] == "prohibited"
        for item in qualifications
        if item["operation"] != "materialize_architecture"
    )
    catalog = _read(SEMANTIC / "catalog" / "semantic-contract-catalog-1.0.json")
    successor_catalog = next(
        item
        for item in catalog["entries"]
        if item["semanticContractSetId"] == retained_set["semanticContractSetId"]
    )
    assert successor_catalog["catalogued"] is True
    assert successor_catalog["lifecycle"] == "active"
    current = _read(SEMANTIC / "current" / "semantic-contract-current-1.0.json")
    assert current["profileId"] == "architecture-materialization@1.0"


def test_successor_definitions_verify_against_sealed_resource_mirrors() -> None:
    for name in ("architecture-interpretation-1.1.json", "normalized-model-2.4.json"):
        definition = _read(SEMANTIC / "definitions" / name)
        assert verify_semantic_contract(definition).success
        resources = [
            {
                "canonicalResourceKey": entry["canonicalResourceKey"],
                "content": load_semantic_resource(entry["canonicalResourceKey"]),
            }
            for entry in definition["resourceManifest"]
        ]
        from adr_kit.semantic_contract import validate_semantic_resource_closure

        assert validate_semantic_resource_closure(definition, resources).success


def test_successor_profile_is_accepted_by_semantic_core_without_becoming_current() -> None:
    profile = _read(SEMANTIC / "profiles" / "architecture-materialization-1.1.json")
    assert validate_semantic_contract_profile(profile).success
