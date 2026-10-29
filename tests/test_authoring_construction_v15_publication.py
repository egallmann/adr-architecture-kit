"""ACC 1.5 authority/schema oracles; no runtime construction is exercised."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import (
    get_semantic_contract,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from scripts import qualify_acc15_publication as publication
from scripts.generate_semantic_contract_assets import definition, digest, discovered_dependencies
from tests.test_authoring_construction_v13_publication import request as historical_request

ROOT = Path(__file__).resolve().parents[1]
P = publication.PREFIX
SCF = get_semantic_contract("authoring-construction", "1.5").semantic_contract_fingerprint


def resource(name: str) -> Any:
    return json.loads(
        (
            ROOT
            / "contracts/authoring-construction/v1.5"
            / ("schema.json" if name == "schema" else "resources/" + name + ".json")
        ).read_text(encoding="utf-8")
    )


@lru_cache
def bundle() -> list[dict[str, Any]]:
    return [
        {
            "canonicalResourceKey": m.canonical_resource_key,
            "content": load_semantic_resource(m.canonical_resource_key),
        }
        for m in get_semantic_contract("authoring-construction", "1.5").resource_manifest
    ]


@lru_cache
def validator(fragment: str) -> Draft202012Validator:
    raw = {n: resource(n) for n in publication.NAMES}
    views, registry = publication.sealed_schemas(
        ROOT, raw, {e["canonicalResourceKey"] for e in bundle()}
    )
    return Draft202012Validator(
        {"$ref": views[P + "schema"]["$id"] + "#/$defs/" + fragment}, registry=registry
    )


def request() -> dict[str, Any]:
    # A new successor schema fixture, not a runtime predecessor adapter.
    value = historical_request()
    value["contract_version"] = "1.5"
    value["basis"]["acc"].update(version="1.5", semantic_contract_fingerprint=SCF)
    ai = get_semantic_contract("architecture-interpretation", "1.5")
    value["basis"]["architecture_interpretation"] = {
        "family": "architecture-interpretation",
        "version": "1.5",
        "semantic_contract_fingerprint": publication.selected_ai_fingerprint(ROOT),
        "authority_closure": {
            "family": "architecture-interpretation",
            "version": "1.5",
            "resources": [
                {
                    "canonical_resource_key": m.canonical_resource_key,
                    "content_digest": m.content_digest,
                }
                for m in ai.resource_manifest
            ],
        },
    }
    return value


CATALOG = load_semantic_resource(publication.CATALOG)
ELIGIBLE = [
    t["semantic_type"]
    for t in CATALOG["types"]
    if t["output_branch"] in {"regular", "normative-proposition"}
]


def evidence(semantic_type: str = "adr/logical", destination: str = "/alias_ref") -> dict[str, Any]:
    i, row = next(
        (i, r) for i, r in enumerate(CATALOG["types"]) if r["semantic_type"] == semantic_type
    )
    j, output = next(
        (j, e) for j, e in enumerate(row["outputs"]) if e["destination"] == destination
    )
    producer = output["producer"]
    rule = producer["rule"]
    if rule == {"local_rule": "literal_string_copy"}:
        rule = CATALOG["inherited_output_authority"]["local_rule_bindings"]["literal_string_copy"]
    return {
        "architecture_interpretation": request()["basis"]["architecture_interpretation"],
        "catalog": publication.qualification(ROOT, publication.CATALOG),
        "catalog_schema": publication.qualification(ROOT, publication.CATALOG + ".schema"),
        "recipe_authority": publication.qualification(ROOT, publication.RECIPES),
        "recipe_schema": publication.qualification(ROOT, publication.RECIPES + ".schema"),
        "inherited_output_authority": copy.deepcopy(CATALOG["inherited_output_authority"]),
        "status": "blocked",
        "all_required_destinations_accounted": False,
        "representation_verification": "unavailable",
        "units": [
            {
                "semantic_type": semantic_type,
                "identity": {
                    "identity_kind": "canonical_uuidv7",
                    "components": ["01900000-0000-7000-8000-000000000001"],
                },
                "output_branch": row["output_branch"],
                "source_schema": copy.deepcopy(row["source_schema"]),
                "destinations": [
                    {
                        "destination": destination,
                        "producer_kind": producer["kind"],
                        "producer_rule_id": producer["rule_id"],
                        "producer_rule": copy.deepcopy(rule),
                        "producer_definition": publication.qualification(
                            ROOT, publication.CATALOG, f"/types/{i}/outputs/{j}"
                        ),
                        "verification": {k: "verified" for k in publication.CHECKS},
                    }
                ],
                "blocked_destinations": [
                    e["destination"] for e in row["outputs"] if e["status"] == "BLOCKED"
                ],
                "competing_destinations": [],
                "all_applicable_accounted": False,
            }
        ],
    }


def test_exact_authority_and_independently_derived_inventory() -> None:
    result = publication.qualify(ROOT)
    assert {
        k: result[k]
        for k in (
            "semantic_types",
            "output_branches",
            "qualified_producer_definitions",
            "BLOCKED_definitions",
            "literal_copy_label_rules",
            "identity_recipe_transitions",
            "active_blocker_categories",
        )
    } == {
        "semantic_types": 27,
        "output_branches": 6,
        "qualified_producer_definitions": 240,
        "BLOCKED_definitions": 215,
        "literal_copy_label_rules": 26,
        "identity_recipe_transitions": 54,
        "active_blocker_categories": 11,
    }
    assert result["inherited_conformance_cases"] == 263 and result["new_conformance_cases"] == 555
    assert (
        result["instance_applicability"] == "Unknown"
        and result["complete_interpretation"] == "Unavailable"
        and result["runtime_execution"] is False
    )
    c = get_semantic_contract("authoring-construction", "1.5")
    assert c.semantic_contract_fingerprint == SCF
    assert c.to_wire()["frozenNormativeConformanceResources"] == [P + "conformance"]
    assert verify_semantic_contract(c).success
    assert validate_semantic_resource_closure(c, bundle()).closure_valid
    assert validate_semantic_resource_closure(c, list(reversed(bundle()))).closure_valid
    keys = {e.canonical_resource_key for e in c.resource_manifest}
    assert {
        e.canonical_resource_key
        for e in get_semantic_contract("architecture-interpretation", "1.5").resource_manifest
    } <= keys
    assert keys == publication.dependency_closure(
        ROOT,
        {P + n: resource(n) for n in publication.NAMES},
        lambda root, key: load_semantic_resource(key),
    )
    assert {k for k in keys if k.startswith(P)} == {P + n for n in publication.NAMES}
    assert publication.LEDGER in keys
    for m in c.to_wire()["resourceManifest"]:
        assert {d["canonicalResourceKey"] for d in m["dependencies"]} == discovered_dependencies(
            m["canonicalResourceKey"], load_semantic_resource(m["canonicalResourceKey"])
        )


@pytest.mark.parametrize("semantic_type", ELIGIBLE)
@pytest.mark.parametrize("destination", ["/alias_ref", "/uri", "/created_at"])
def test_all_54_actual_recipe_definition_alternatives(semantic_type: str, destination: str) -> None:
    value = evidence(semantic_type, destination)
    validator("required_output_qualification").validate(value)
    assert value["status"] == "blocked"  # Schema fixtures are not instance evidence.
    assert (
        value["units"][0]["destinations"][0]["producer_rule"]["canonical_resource_key"]
        == publication.RECIPES
    )
    if semantic_type == "entity/normative_proposition":
        assert all(
            e["destination"] != "/lifecycle_stage"
            for e in next(t for t in CATALOG["types"] if t["semantic_type"] == semantic_type)[
                "outputs"
            ]
        )


def test_actual_inherited_producers_labels_and_binding_rules_remain_qualified() -> None:
    prior = load_semantic_resource("architecture-interpretation/1.4/required-output-derivations")
    previous = {
        (t["semantic_type"], e["destination"]): e for t in prior["types"] for e in t["outputs"]
    }
    inherited_count = 0
    for row in CATALOG["types"]:
        for output in row["outputs"]:
            old = previous[(row["semantic_type"], output["destination"])]
            if old["status"] == "QUALIFIED":
                assert output == old
                inherited_count += 1
    assert inherited_count == 186
    label = evidence("adr/logical", "/summary")["units"][0]["destinations"][0]
    assert label["producer_kind"] == "literal_string_copy"
    assert (
        label["producer_rule"]
        == CATALOG["inherited_output_authority"]["local_rule_bindings"]["literal_string_copy"]
    )
    assert (
        label["producer_rule"]["canonical_resource_key"]
        == "architecture-interpretation/1.4/required-output-derivations"
    )
    table = resource("composition-bindings")
    assert (
        table["rows"] == load_semantic_resource(publication.BASE + "composition-bindings")["rows"]
    )
    q = table["rows"][0]["ai_ownership_authority"]
    assert q["version"] == "1.3" and q["rule_id"] == "declaring-lifecycle.adr-logical.decisions"
    schema_key = P + "composition-bindings.schema"
    assert [
        k for k in table["semanticDependencies"] if k.endswith("composition-bindings.schema")
    ] == [schema_key]
    manifest = get_semantic_contract("authoring-construction", "1.5").to_wire()["resourceManifest"]
    edge = next(m for m in manifest if m["canonicalResourceKey"] == P + "composition-bindings")[
        "dependencies"
    ]
    assert {
        "canonicalResourceKey": schema_key,
        "contentDigest": digest(resource("composition-bindings.schema")),
    } in edge


@pytest.mark.parametrize(
    "fault",
    [
        "ACC_version",
        "malformed_ACC_SCF",
        "AI14",
        "AI_SCF",
        "AI_missing",
        "NM24",
        "NM_SCF",
        "NM_missing",
    ],
)
def test_exact_request_schema_qualifications(fault: str) -> None:
    value = request()
    check = validator("authoring_request")
    check.validate(value)
    ai = value["basis"]["architecture_interpretation"]
    nm = value["basis"]["normalized_model"]
    if fault == "ACC_version":
        value["contract_version"] = "1.4"
    elif fault == "malformed_ACC_SCF":
        value["basis"]["acc"]["semantic_contract_fingerprint"] = "invented"
    elif fault == "AI14":
        ai.update(
            version="1.4",
            semantic_contract_fingerprint="scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7",
        )
    elif fault == "AI_SCF":
        ai["semantic_contract_fingerprint"] = publication.ACC14_SCF
    elif fault == "AI_missing":
        ai["authority_closure"]["resources"].pop()
    elif fault == "NM24":
        nm["version"] = "2.4"
    elif fault == "NM_SCF":
        nm["semantic_contract_fingerprint"] = publication.selected_ai_fingerprint(ROOT)
    else:
        nm["resources"].pop()
    assert not check.is_valid(value)


def test_resource_permutation_is_not_instance_semantics_or_partial_NM_success() -> None:
    value = request()
    value["basis"]["architecture_interpretation"]["authority_closure"]["resources"].reverse()
    value["basis"]["normalized_model"]["resources"].reverse()
    validator("authoring_request").validate(value)
    assert not validator("normalized_result").is_valid(
        {
            "normalized_contract": value["basis"]["normalized_model"],
            "semantic_digest": "sha256:" + "0" * 64,
            "model": {"schema_version": "2.5", "entities": []},
        }
    )


@pytest.mark.parametrize(
    "fault", ["missing", "bad_selector", "escape", "remote", "historical_bad_fragment"]
)
def test_selected_schema_references_fail_closed_without_ambient_resolution(fault: str) -> None:
    raw = {n: resource(n) for n in publication.NAMES}
    refs = {
        "missing": "../../normalized-model/2.5/schema/missing.schema.json",
        "bad_selector": "../../normalized-model/2.5/schema/normalized-entity.schema.json#/absent",
        "escape": "../../../outside.schema.json",
        "remote": "https://example.invalid/schema.json",
        "historical_bad_fragment": "../../normalized-model/2.3/schema/relationship-record.schema.json",
    }
    raw["schema"]["$defs"]["non_empty"] = {"$ref": refs[fault]}
    with pytest.raises(ValueError):
        publication.sealed_schemas(ROOT, raw, {e["canonicalResourceKey"] for e in bundle()})


def test_only_selected_schema_fragments_are_interpreted_not_all_historical_members() -> None:
    raw = {n: resource(n) for n in publication.NAMES}
    allowed = {e["canonicalResourceKey"] for e in bundle()}
    historical = "normalized-model/2.3/schema/relationship-record.schema"
    assert historical in allowed
    views, _ = publication.sealed_schemas(ROOT, raw, allowed)
    assert historical not in views
    assert "normalized-model/2.5/schema/normalized-entity.schema" in views


@pytest.mark.parametrize("check", publication.CHECKS)
@pytest.mark.parametrize("state", ["verified", "invalid", "unavailable", "not_evaluated"])
def test_independently_evaluated_four_state_checks(check: str, state: str) -> None:
    value = evidence()
    value["units"][0]["destinations"][0]["verification"][check] = state
    validator("required_output_qualification").validate(value)
    value.update(
        status="complete",
        all_required_destinations_accounted=True,
        representation_verification="valid",
    )
    value["units"][0].update(all_applicable_accounted=True, blocked_destinations=[])
    assert validator("required_output_qualification").is_valid(value) == (state == "verified")


@pytest.mark.parametrize(
    "fault",
    [
        "missing_check",
        "boolean_check",
        "unknown_check",
        "wrong_operation",
        "wrong_rule_id",
        "wrong_rule_digest",
        "wrong_definition",
        "wrong_source",
        "wrong_branch",
        "blocked_complete",
        "competing",
        "missing_recipe",
        "fake_local_owner",
    ],
)
def test_output_schema_rejects_inconsistent_or_incomplete_evidence(fault: str) -> None:
    value = evidence()
    unit = value["units"][0]
    dest = unit["destinations"][0]
    if fault == "missing_check":
        dest["verification"].pop("source_and_identity")
    elif fault == "boolean_check":
        dest["verification"]["complete_output"] = True
    elif fault == "unknown_check":
        dest["verification"]["complete_output"] = "trusted"
    elif fault == "wrong_operation":
        dest["producer_kind"] = "normalize_alias"
    elif fault == "wrong_rule_id":
        dest["producer_rule_id"] = "invented"
    elif fault == "wrong_rule_digest":
        dest["producer_rule"]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "wrong_definition":
        dest["producer_definition"]["schema_pointer"] = "/types/0/outputs/0"
    elif fault == "wrong_source":
        unit["source_schema"]["schema_pointer"] = "/properties/other"
    elif fault == "wrong_branch":
        unit["output_branch"] = "canonical-relationship"
    elif fault == "blocked_complete":
        value["status"] = "complete"
    elif fault == "competing":
        unit["destinations"].append(copy.deepcopy(dest))
    elif fault == "missing_recipe":
        value.pop("recipe_authority")
    else:
        value["inherited_output_authority"]["local_rule_bindings"]["literal_string_copy"][
            "canonical_resource_key"
        ] = publication.CATALOG
    assert not validator("required_output_qualification").is_valid(value)


def test_schema_consistent_flags_do_not_create_instance_or_construction_proof() -> None:
    fragment = evidence()
    fragment.update(
        status="complete",
        all_required_destinations_accounted=True,
        representation_verification="valid",
    )
    fragment["units"][0].update(all_applicable_accounted=True, blocked_destinations=[])
    # Shape validation cannot establish whether the asserted checks occurred.
    validator("required_output_qualification").validate(fragment)
    rules = resource("rules")
    assert rules["required_output"]["schema_valid_is_instance_proof"] is False
    assert rules["required_output"]["definition_is_instance_proof"] is False
    assert "caller_flags" in rules["required_output"]["independent_replay"]
    assert (
        rules["equivalence"]["representation_outputs"]["representation_proof_is_equality"] is False
    )
    assert (
        rules["equivalence"]["representation_outputs"]["equality_is_representation_proof"] is False
    )
    assert rules["outcomes"]["precedence"] == [
        "Rejected",
        "Unavailable",
        "Unresolved",
        "Constructed",
    ]
    defs = resource("schema")["$defs"]
    assert defs["construction_qualification"]["properties"]["expected_ledger"] == {
        "$ref": "../1.3/ledger.schema.json"
    }
    assert defs["construction_qualification"]["properties"]["observed_ledger"] == {
        "$ref": "../1.3/ledger.schema.json"
    }
    assert rules["publication_posture"]["execution_capability_advertised"] is False
    report = publication.qualify(ROOT)
    assert (
        report["complete_interpretation"] == "Unavailable"
        and report["instance_applicability"] == "Unknown"
    )


@pytest.fixture
def snapshot(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    original = publication.read
    values = {P + n: resource(n) for n in publication.NAMES}
    for key in (
        P + "contract",
        publication.AI + "contract",
        publication.CATALOG,
        publication.RECIPES,
    ):
        values[key] = copy.deepcopy(original(ROOT, key))
    monkeypatch.setattr(
        publication, "read", lambda root, key: values[key] if key in values else original(root, key)
    )
    return values


def alternative(values: dict[str, Any]) -> dict[str, Any]:
    units = values[P + "schema"]["$defs"]["required_output_qualification"]["properties"]["units"][
        "items"
    ]["oneOf"]
    return next(
        a
        for a in units[0]["properties"]["destinations"]["items"]["oneOf"]
        if a["properties"]["destination"] == {"const": "/alias_ref"}
    )


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_AI_SCF",
        "incomplete_AI_closure",
        "AI14_enclosing",
        "AI13_relabelled",
        "wrong_operation",
        "wrong_rule_id",
        "wrong_rule_digest",
        "wrong_definition_selector",
        "wrong_source",
        "wrong_destination",
        "BLOCKED_qualified",
        "omitted_alternative",
        "competing_alternative",
        "forged_applicability",
        "flags_are_proof",
        "caller_replay_is_proof",
        "URI_normalization",
        "invalid_timestamp_policy",
        "lost_original_semantics",
        "missing_check",
        "boolean_verification",
        "incomplete_expected_ledger",
        "incomplete_observed_ledger",
        "dropped_equality",
        "changed_binding",
        "malformed_companion",
        "predecessor_schema_edge",
        "missing_schema_edge",
        "wrong_schema_digest",
        "wrong_manifest_edge",
        "missing_conformance_case",
        "duplicate_conformance_case",
        "altered_historical_assertion",
        "historical_case_missing",
        "forged_conformance_success",
        "open_conformance_schema",
        "bad_required_schema_ref",
        "missing_selected_schema",
        "invalid_schema_dialect",
        "wrong_ACC_version",
        "wrong_ACC_SCF",
        "extra_manifest_resource",
        "wrong_manifest_role",
    ],
)
def test_independent_publication_mutations(snapshot: dict[str, Any], fault: str) -> None:
    props = alternative(snapshot)["properties"]
    rules = snapshot[P + "rules"]
    schema = snapshot[P + "schema"]["$defs"]
    if fault == "wrong_AI_SCF":
        snapshot[publication.AI + "contract"]["semanticContractFingerprint"] = publication.ACC14_SCF
    elif fault == "incomplete_AI_closure":
        snapshot[publication.AI + "contract"]["resourceManifest"].pop()
    elif fault == "AI14_enclosing":
        schema["architecture_interpretation_qualification"]["properties"]["version"] = {
            "const": "1.4"
        }
    elif fault == "AI13_relabelled":
        snapshot[P + "composition-bindings"]["rows"][0]["ai_ownership_authority"]["version"] = "1.5"
    elif fault == "wrong_operation":
        props["producer_kind"]["const"] = "normalize_alias"
    elif fault == "wrong_rule_id":
        props["producer_rule_id"]["const"] = "invented"
    elif fault == "wrong_rule_digest":
        props["producer_rule"]["const"]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "wrong_definition_selector":
        props["producer_definition"]["const"]["schema_pointer"] = "/types/0/outputs/0"
    elif fault == "wrong_source":
        schema["required_output_qualification"]["properties"]["units"]["items"]["oneOf"][0][
            "properties"
        ]["source_schema"]["const"]["schema_pointer"] = "/properties/wrong"
    elif fault == "wrong_destination":
        props["destination"]["const"] = "/entity_fingerprint"
    elif fault in {"BLOCKED_qualified", "omitted_alternative", "competing_alternative"}:
        choices = schema["required_output_qualification"]["properties"]["units"]["items"]["oneOf"][
            0
        ]["properties"]["destinations"]["items"]["oneOf"]
        if fault == "BLOCKED_qualified":
            fake = copy.deepcopy(choices[0])
            fake["properties"]["destination"] = {"const": "/entity_fingerprint"}
            choices.append(fake)
        elif fault == "omitted_alternative":
            choices.pop()
        else:
            choices.append(copy.deepcopy(choices[0]))
    elif fault == "forged_applicability":
        rules["required_output"]["instance_applicability"] = "proven"
    elif fault == "flags_are_proof":
        rules["required_output"]["schema_valid_is_instance_proof"] = True
    elif fault == "caller_replay_is_proof":
        rules["required_output"]["independent_replay"] = "trust_caller_flags"
    elif fault == "URI_normalization":
        rules["required_output"]["identity_recipe_operations"][1] = "normalize_URL"
    elif fault == "invalid_timestamp_policy":
        rules["required_output"]["recipe_failure_policy"][
            "valid_uuid_timestamp_beyond_selected_four_digit_year_representation"
        ] = "Rejected"
    elif fault == "lost_original_semantics":
        rules["equivalence"]["representation_outputs"][
            "lost_extension_is_mismatch_even_if_label_intact"
        ] = False
    elif fault == "missing_check":
        props["verification"]["required"].remove("source_and_identity")
    elif fault == "boolean_verification":
        props["verification"]["properties"]["complete_output"] = {"type": "boolean"}
    elif fault.startswith("incomplete_"):
        key = "expected_ledger" if fault == "incomplete_expected_ledger" else "observed_ledger"
        schema["construction_qualification"]["properties"][key] = {"type": "object"}
    elif fault == "dropped_equality":
        schema["construction_qualification"]["properties"]["comparison"]["required"].remove(
            "all_observed_accounted"
        )
    elif fault == "changed_binding":
        snapshot[P + "composition-bindings"]["rows"][0]["parent_property"] = "other"
    elif fault == "malformed_companion":
        snapshot[P + "composition-bindings.schema"]["additionalProperties"] = True
    elif fault == "predecessor_schema_edge":
        deps = snapshot[P + "composition-bindings"]["semanticDependencies"]
        deps[deps.index(P + "composition-bindings.schema")] = (
            publication.BASE + "composition-bindings.schema"
        )
    elif fault == "missing_schema_edge":
        snapshot[P + "composition-bindings"]["semanticDependencies"].remove(
            P + "composition-bindings.schema"
        )
    elif fault == "wrong_schema_digest":
        rules["composition"]["schema_authority"]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "wrong_manifest_edge":
        member = next(
            m
            for m in snapshot[P + "contract"]["resourceManifest"]
            if m["canonicalResourceKey"] == P + "composition-bindings"
        )
        edge = next(
            e
            for e in member["dependencies"]
            if e["canonicalResourceKey"] == P + "composition-bindings.schema"
        )
        edge["contentDigest"] = "sha256:" + "0" * 64
    elif fault == "missing_conformance_case":
        snapshot[P + "conformance"]["cases"].pop()
    elif fault == "duplicate_conformance_case":
        snapshot[P + "conformance"]["cases"].append(
            copy.deepcopy(snapshot[P + "conformance"]["cases"][-1])
        )
    elif fault == "altered_historical_assertion":
        snapshot[P + "conformance"]["inherited_cases"][0]["preserved_assertions"] = []
    elif fault == "historical_case_missing":
        snapshot[P + "conformance"]["inherited_cases"].pop()
    elif fault == "forged_conformance_success":
        c = next(
            c
            for c in snapshot[P + "conformance"]["cases"]
            if c["fixture"]["input"].get("fault") == "forged_independently_verified_result"
        )
        c["assertions"][0]["expected"] = "Constructed"
    elif fault == "open_conformance_schema":
        snapshot[P + "conformance.schema"]["additionalProperties"] = True
    elif fault == "bad_required_schema_ref":
        schema["normalized_result"]["properties"]["model"][
            "$ref"
        ] = "../../normalized-model/2.5/schema/normalized-entity.schema.json#/missing"
    elif fault == "missing_selected_schema":
        schema["normalized_result"]["properties"]["model"][
            "$ref"
        ] = "../../normalized-model/2.5/schema/absent.schema.json"
    elif fault == "invalid_schema_dialect":
        snapshot[P + "conformance.schema"]["$schema"] = "https://invalid.test/dialect"
    elif fault == "wrong_ACC_version":
        snapshot[P + "contract"]["semanticContractVersion"] = "1.4"
    elif fault == "wrong_ACC_SCF":
        snapshot[P + "contract"]["semanticContractFingerprint"] = publication.ACC14_SCF
    elif fault == "extra_manifest_resource":
        snapshot[P + "contract"]["resourceManifest"].append(
            copy.deepcopy(snapshot[P + "contract"]["resourceManifest"][0])
        )
    else:
        snapshot[P + "contract"]["resourceManifest"][0]["role"] = "normative-definition"
    with pytest.raises(publication.PublicationError):
        publication.qualify(ROOT)


@pytest.mark.parametrize("fault", ["producer_kind", "predecessor_schema"])
def test_valid_recomputed_SCF_and_closure_cannot_authorize_a_bad_rule(
    snapshot: dict[str, Any], fault: str
) -> None:
    if fault == "producer_kind":
        alternative(snapshot)["properties"]["producer_kind"] = {"const": "literal_entity_uri"}
    else:
        table = snapshot[P + "composition-bindings"]
        table["semanticDependencies"] = [
            (
                publication.BASE + "composition-bindings.schema"
                if k == P + "composition-bindings.schema"
                else k
            )
            for k in table["semanticDependencies"]
        ]
        snapshot[P + "composition-bindings.schema"]["properties"]["semanticDependencies"] = {
            "const": table["semanticDependencies"]
        }
        snapshot[P + "schema"]["$defs"]["composition_binding_qualification"]["properties"][
            "content_digest"
        ] = {"const": digest(table)}
        rules = snapshot[P + "rules"]["composition"]
        rules["binding_authority"]["content_digest"] = digest(table)
        rules["schema_authority"]["content_digest"] = digest(
            snapshot[P + "composition-bindings.schema"]
        )
    original = snapshot[P + "contract"]["resourceManifest"]
    historical = get_semantic_contract("authoring-construction", "1.4").to_wire()[
        "resourceManifest"
    ]
    roles = {m["canonicalResourceKey"]: m["role"] for m in [*historical, *original]}
    # An attacker must actually supply the substituted schema and its closure.
    # It is no longer implicitly present through a predecessor manifest import.
    selected = publication.dependency_closure(
        ROOT,
        {
            m["canonicalResourceKey"]: publication.read(ROOT, m["canonicalResourceKey"])
            for m in original
        },
        publication.read,
    )
    manifest = []
    for key in sorted(selected):
        value = publication.read(ROOT, key)
        manifest.append(
            {
                "canonicalResourceKey": key,
                "role": roles[key],
                "contentDigest": digest(value),
                "dependencies": [
                    {"canonicalResourceKey": k, "contentDigest": digest(publication.read(ROOT, k))}
                    for k in sorted(discovered_dependencies(key, value))
                ],
            }
        )
    forged = definition("authoring-construction", manifest, [P + "conformance"], version="1.5")
    snapshot[P + "contract"] = forged
    assert forged["semanticContractFingerprint"] != SCF
    assert verify_semantic_contract(forged).success
    supplied = [
        {
            "canonicalResourceKey": m["canonicalResourceKey"],
            "content": publication.read(ROOT, m["canonicalResourceKey"]),
        }
        for m in manifest
    ]
    assert validate_semantic_resource_closure(forged, supplied).closure_valid
    with pytest.raises(
        publication.PublicationError,
        match="composition_schema_dependency|unqualified_producer_source_destination_kind_or_rule",
    ):
        publication.qualify(ROOT)


def test_frozen_cases_individually_preserve_all_historical_assertions() -> None:
    c = resource("conformance")
    old = load_semantic_resource(publication.BASE + "conformance")["cases"]
    assert len(c["inherited_cases"]) == len(old) == 263
    for i, (ref, original) in enumerate(zip(c["inherited_cases"], old, strict=True)):
        assert ref["case_id"] == original["case_id"]
        assert ref["qualification"] == publication.qualification(
            ROOT, publication.BASE + "conformance", f"/cases/{i}"
        )
        assert ref["preserved_assertions"] == original["assertions"]
        assert ref["scope"] == "historical_authority_only_not_executed_successor_request"
    categories = Counter(case["category"] for case in c["cases"])
    assert (
        categories["identity_recipe_definition"] == 54
        and categories["blocked_destination"] == 215
        and categories["literal_label_definition"] == 26
    )
    assert categories["recipe_exclusion"] == 9
    assert len(c["cases"]) == 555
    assert [case["case_id"] for case in c["cases"]] == [
        f"ACC15-{i:03d}" for i in range(1, len(c["cases"]) + 1)
    ]
    assert all(case["runtime_coverage"] == "authority_only_not_implemented" for case in c["cases"])


def test_current_candidate_mirrors_match_canonical_inputs() -> None:
    # Promotion, not a development snapshot, establishes compatibility freezes.
    # Released artifact preservation is independently tested by the actual
    # wheel/npm inventory admission suite.
    canonical = ROOT / "contracts/authoring-construction/v1.5"
    for name in publication.NAMES:
        data = (
            canonical / ("schema.json" if name == "schema" else "resources/" + name + ".json")
        ).read_bytes()
        assert SCF.encode() not in data
        for folder in (
            "contracts/semantic-contract/v1.0/resources",
            "src/adr_kit/semantic_contract/v1_0/resources",
        ):
            assert (
                ROOT / folder / ("authoring-construction-1.5-" + name + ".json")
            ).read_bytes() == data
    for path in (
        "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.5.json",
        "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.5.json",
        "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.5.json",
    ):
        assert (ROOT / path).read_bytes() == (canonical / "contract.json").read_bytes()


def test_deterministic_successor_only_generation() -> None:
    before = {
        p: p.read_bytes()
        for directory in ("contracts", "src/adr_kit/semantic_contract")
        for p in (ROOT / directory).rglob("*.json")
    }
    run = subprocess.run(
        [sys.executable, "scripts/generate_semantic_contract_assets.py", "--publish-acc15-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert {p: (ROOT / p).read_bytes() for p in before} == before


def test_exact_discovery_and_closure_corruption_rejection() -> None:
    assert load_semantic_resource(P + "contract")["semanticContractFingerprint"] == SCF
    assert (
        load_semantic_resource(publication.BASE + "contract")["semanticContractFingerprint"]
        == publication.ACC14_SCF
    )
    assert load_semantic_resource(publication.AI + "contract")[
        "semanticContractFingerprint"
    ] == publication.selected_ai_fingerprint(ROOT)
    # Invalid syntax cannot become a legitimate later selected version.
    with pytest.raises(LookupError):
        get_semantic_contract("authoring-construction", "missing-version")
    for key in (P + "missing", P + "../1.4/rules", P + "composition/bindings"):
        with pytest.raises(LookupError):
            load_semantic_resource(key)
    contract = get_semantic_contract("authoring-construction", "1.5")
    assert not validate_semantic_resource_closure(contract, bundle()[:-1]).closure_valid
    changed = copy.deepcopy(bundle())
    changed[0]["content"] = {"tampered": True}
    assert not validate_semantic_resource_closure(contract, changed).closure_valid
    assert not validate_semantic_resource_closure(
        contract,
        [
            *bundle(),
            {"canonicalResourceKey": "authoring-construction/99.99/unknown", "content": {}},
        ],
    ).closure_valid


def test_independent_installed_wheel_discovery(tmp_path: Path) -> None:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path))
    built = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(tmp_path / "wheels"),
            str(ROOT),
        ],
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    wheel = next((tmp_path / "wheels").glob("*.whl"))
    installed = tmp_path / "installed"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(installed),
            str(wheel),
        ],
        check=True,
        capture_output=True,
    )
    code = """
import sys,pathlib
sys.path.insert(0,sys.argv[1])
import adr_kit
from adr_kit.semantic_contract import get_semantic_contract,load_semantic_resource,validate_semantic_resource_closure
assert pathlib.Path(adr_kit.__file__).is_relative_to(sys.argv[1])
c=get_semantic_contract('authoring-construction','1.5')
assert c.semantic_contract_fingerprint==sys.argv[2]
assert validate_semantic_resource_closure(c,[{'canonicalResourceKey':m.canonical_resource_key,'content':load_semantic_resource(m.canonical_resource_key)} for m in c.resource_manifest]).closure_valid
assert load_semantic_resource('authoring-construction/1.5/rules')['required_output']['schema_valid_is_instance_proof'] is False
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(installed), SCF],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
