"""Immutable AI 1.5 publication evidence, never source-instance execution."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from adr_kit.semantic_contract import (
    get_semantic_contract,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from scripts import qualify_ai15_publication as publication
from scripts.generate_semantic_contract_assets import definition, digest, discovered_dependencies

ROOT = Path(__file__).resolve().parents[1]
P = publication.PREFIX
B = publication.BASE
SCF = get_semantic_contract("architecture-interpretation", "1.5").semantic_contract_fingerprint


def resource(name: str) -> Any:
    return json.loads(
        (
            ROOT / "contracts/architecture-interpretation/v1.5/resources" / (name + ".json")
        ).read_text(encoding="utf-8")
    )


@pytest.fixture
def snapshot(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    original = publication.read
    values = {P + n: resource(n) for n in publication.NAMES}
    values[P + "contract"] = original(ROOT, P + "contract")

    def read(root: Path, key: str) -> Any:
        return values[key] if key in values else original(root, key)

    monkeypatch.setattr(publication, "read", read)
    return values


def selected_entry(values: dict[str, Any], destination: str = "/uri") -> dict[str, Any]:
    return next(
        e
        for e in values[P + publication.CATALOG]["types"][0]["outputs"]
        if e["destination"] == destination
    )


def test_independent_authority_and_derived_accounting() -> None:
    result = publication.qualify(ROOT)
    assert result == {
        "semantic_types": 27,
        "output_branches": 6,
        "output_accounting": {"QUALIFIED": 240, "BLOCKED": 215},
        "transitions": {"/alias_ref": 18, "/created_at": 18, "/uri": 18},
        "literal_string_copy_rules": 26,
        "active_blocker_categories": 11,
        "conformance_cases": 132,
        "instance_applicability": "Unknown",
        "complete_interpretation": "Unavailable",
        "runtime_execution": False,
    }
    contract = get_semantic_contract("architecture-interpretation", "1.5")
    assert contract.semantic_contract_fingerprint == SCF
    assert len(contract.resource_manifest) == 69
    assert contract.to_wire()["frozenNormativeConformanceResources"] == [P + "conformance"]
    assert verify_semantic_contract(contract).success
    bundle = [
        {
            "canonicalResourceKey": m.canonical_resource_key,
            "content": load_semantic_resource(m.canonical_resource_key),
        }
        for m in contract.resource_manifest
    ]
    assert validate_semantic_resource_closure(contract, bundle).closure_valid
    assert validate_semantic_resource_closure(contract, list(reversed(bundle))).closure_valid


TYPES = [t["semantic_type"] for t in resource(publication.CATALOG)["types"]]


@pytest.mark.parametrize("semantic_type", TYPES)
def test_every_inherited_declaration_and_type_is_preserved(semantic_type: str) -> None:
    previous = load_semantic_resource(B + publication.CATALOG)
    old = next(t for t in previous["types"] if t["semantic_type"] == semantic_type)
    current = next(
        t for t in resource(publication.CATALOG)["types"] if t["semantic_type"] == semantic_type
    )
    assert {k: v for k, v in current.items() if k != "outputs"} == {
        k: v for k, v in old.items() if k != "outputs"
    }
    eligible = old["output_branch"] in {"regular", "normative-proposition"}
    originals = {e["destination"]: e for e in old["outputs"]}
    assert len(current["outputs"]) == len(originals)
    for entry in current["outputs"]:
        before = originals[entry["destination"]]
        if eligible and entry["destination"] in publication.CODES:
            assert before["status"] == "BLOCKED" and entry["status"] == "QUALIFIED"
            assert before["blocked"]["code"] == publication.CODES[entry["destination"]]
            assert entry["classification"] == "representation_only"
            assert entry["producer"]["kind"] == publication.OPERATIONS[entry["destination"]]
            for key in set(before) - {"status", "classification", "semantic_equality", "blocked"}:
                assert entry[key] == before[key]
        else:
            assert entry == before
    # Actual inherited local operation identity is explicit, not an AI 1.5 rename.
    assert (
        resource(publication.CATALOG)["inherited_output_authority"]["local_rule_bindings"][
            "literal_string_copy"
        ]["canonical_resource_key"]
        == B + publication.CATALOG
    )


@pytest.mark.parametrize(
    "fault",
    [
        "unsupported_kind",
        "wrong_operation",
        "wrong_input_type",
        "wrong_manifest_role",
        "wrong_source_selector",
        "wrong_destination_branch",
        "missing_producer",
        "competing_producer",
        "qualified_without_authority",
        "forged_lineage",
        "inherited_identity",
        "missing_schema_edge",
        "missing_conformance_rule_edge",
        "wrong_dependency",
        "URI_normalize",
        "missing_provider",
        "timestamp_precision",
        "timestamp_boundary",
        "wrong_failure",
        "semantic_owner",
        "lost_authored_field",
        "missing_nested",
        "missing_conditional",
        "conditional_inapplicable",
        "forged_custom",
        "shared_identity",
        "relationship_branch",
        "open_schema",
        "schema_vocabulary",
        "schema_cardinality",
        "broken_reference",
        "wrong_dialect",
        "wrong_context_SCF",
        "namespace_substitution",
        "false_execution",
        "false_complete",
        "missing_inherited_case",
        "wrong_oracle_outcome",
        "changed_oracle_assertion",
        "missing_boundary",
        "missing_remaining_blocker",
        "wrong_rule_selection",
        "wrong_definition_SCF",
        "wrong_definition_version",
    ],
)
def test_independent_negative_mutations_fail_closed(snapshot: dict[str, Any], fault: str) -> None:
    c = snapshot[P + publication.CATALOG]
    recipes = snapshot[P + publication.RECIPES]
    rule = recipes["recipes"][1]
    entry = selected_entry(snapshot)
    if fault == "unsupported_kind":
        entry["producer"]["kind"] = "fallback"
    elif fault == "wrong_operation":
        rule["specification"]["operation"] = "normalize_URL"
    elif fault == "wrong_input_type":
        rule["input_contract"][0]["type"] = "integer"
    elif fault == "wrong_manifest_role":
        snapshot[P + "contract"]["resourceManifest"][0]["role"] = "interpretation-rule"
    elif fault == "wrong_source_selector":
        entry["producer"]["inputs"][1]["schema_pointer"] = "/properties/title"
    elif fault == "wrong_destination_branch":
        c["types"][0]["output_branch"] = "canonical-relationship"
    elif fault == "missing_producer":
        entry.pop("producer")
    elif fault == "competing_producer":
        c["types"][0]["outputs"].append(copy.deepcopy(entry))
    elif fault == "qualified_without_authority":
        blocked = next(e for e in c["types"][0]["outputs"] if e["status"] == "BLOCKED")
        blocked.update(status="QUALIFIED", producer=copy.deepcopy(entry["producer"]))
        blocked.pop("blocked")
    elif fault == "forged_lineage":
        rule["lineage"]["decision_id"] = "00000000-0000-7000-8000-000000000000"
    elif fault == "inherited_identity":
        c["inherited_output_authority"]["local_rule_bindings"]["literal_string_copy"][
            "canonical_resource_key"
        ] = (P + publication.CATALOG)
    elif fault == "missing_schema_edge":
        recipes["semanticDependencies"].remove(P + publication.RECIPES + ".schema")
    elif fault == "missing_conformance_rule_edge":
        snapshot[P + "conformance"]["semanticDependencies"].remove(P + publication.RECIPES)
    elif fault == "wrong_dependency":
        c["semanticDependencies"].append("architecture-interpretation/99.99/rules")
    elif fault == "URI_normalize":
        rule["specification"]["namespace_encoding"] = "URL_normalization"
    elif fault == "missing_provider":
        recipes["context_authority"].pop("qualification")
    elif fault == "timestamp_precision":
        recipes["recipes"][2]["specification"]["fraction_digits"] = 6
    elif fault == "timestamp_boundary":
        recipes["recipes"][2]["specification"]["maximum_timestamp_ms"] = (1 << 48) - 1
    elif fault == "wrong_failure":
        rule["failure_policy"]["missing_or_ambiguous_provider"] = "Unresolved"
    elif fault == "semantic_owner":
        entry["classification"] = "semantic"
    elif fault == "lost_authored_field":
        c["types"][0]["outputs"] = [
            e
            for e in c["types"][0]["outputs"]
            if e["destination"] != "/metadata/semantic_extensions/{semantic_field_key}"
        ]
    elif fault == "missing_nested":
        nested = next(e for t in c["types"] for e in t["outputs"] if e["required_subdestinations"])
        nested["required_subdestinations"].pop()
    elif fault == "missing_conditional":
        c["branches"][0]["requirements"].pop()
    elif fault == "conditional_inapplicable":
        entry["applicability"]["evaluation"] = "inapplicable_without_instance"
    elif fault == "forged_custom":
        next(t for t in c["types"] if t["semantic_type"] == "entity/extension")[
            "context_dependencies"
        ] = []
    elif fault == "shared_identity":
        next(t for t in c["types"] if t["semantic_type"] == "entity/system")[
            "identity_policy"
        ] = "new_identity_per_occurrence"
    elif fault == "relationship_branch":
        next(t for t in c["types"] if t["semantic_type"] == "relationship/extension")[
            "outputs"
        ].append(copy.deepcopy(entry))
    elif fault == "open_schema":
        snapshot[P + publication.CATALOG + ".schema"]["additionalProperties"] = True
    elif fault == "schema_vocabulary":
        snapshot[P + publication.CATALOG + ".schema"]["$defs"]["identity_producer"]["properties"][
            "kind"
        ]["enum"].append("fallback")
    elif fault == "schema_cardinality":
        snapshot[P + publication.CATALOG + ".schema"]["$defs"]["identity_producer"].pop("allOf")
    elif fault == "broken_reference":
        snapshot[P + publication.CATALOG + ".schema"]["properties"]["operation"][
            "$ref"
        ] = "../../outside.schema.json"
    elif fault == "wrong_dialect":
        snapshot[P + publication.RECIPES + ".schema"]["$schema"] = "https://invalid.test/dialect"
    elif fault == "wrong_context_SCF":
        recipes["context_authority"]["semantic_contract_fingerprint"] = publication.AI14_SCF
    elif fault == "namespace_substitution":
        entry["producer"]["inputs"][0]["schema_pointer"] = "/scope_root_form"
    elif fault == "false_execution":
        snapshot[P + "rules"]["public_boundary"]["enabled_by_publication"] = True
    elif fault == "false_complete":
        snapshot[P + "rules"]["public_boundary"]["complete_interpretation"] = "Complete"
    elif fault == "missing_inherited_case":
        snapshot[P + "conformance"]["inherited_cases"].pop()
    elif fault == "wrong_oracle_outcome":
        next(
            x
            for x in snapshot[P + "conformance"]["cases"]
            if x["fixture"].get("mutation") == "missing_provider"
        )["expected"] = "unavailable_wrong"
    elif fault == "changed_oracle_assertion":
        snapshot[P + "conformance"]["cases"][0][
            "assertion"
        ] = "Count proves complete interpretation"
    elif fault == "missing_boundary":
        next(
            x
            for x in snapshot[P + "conformance"]["cases"]
            if x["category"] == "timestamp_unavailable"
        )["fixture"]["timestamp_ms"] = 0
    elif fault == "missing_remaining_blocker":
        c["blockers"].pop("fingerprint_preimage")
    elif fault == "wrong_rule_selection":
        snapshot[P + "rules"]["inherits"]["semantic_contract_fingerprint"] = publication.NM25_SCF
    elif fault == "wrong_definition_SCF":
        snapshot[P + "contract"]["semanticContractFingerprint"] = "scf:v1:sha256:" + "0" * 64
    elif fault == "wrong_definition_version":
        snapshot[P + "contract"]["semanticContractVersion"] = "1.4"
    with pytest.raises(publication.PublicationError):
        publication.qualify(ROOT)


def test_recomputed_valid_closure_cannot_authorize_an_invalid_recipe(
    snapshot: dict[str, Any],
) -> None:
    # Mutate both data and companion to agree, retaining all counts and shape.
    snapshot[P + publication.RECIPES]["recipes"][1]["specification"]["fallback"] = True
    snapshot[P + publication.RECIPES + ".schema"]["properties"]["recipes"]["items"]["oneOf"][1][
        "properties"
    ]["specification"]["const"]["fallback"] = True

    def refresh(node: Any) -> None:
        if isinstance(node, dict):
            key = node.get("canonical_resource_key")
            if isinstance(key, str) and key in snapshot and "content_digest" in node:
                node["content_digest"] = digest(snapshot[key])
            for v in node.values():
                refresh(v)
        elif isinstance(node, list):
            for v in node:
                refresh(v)

    for _ in range(4):
        for key in [P + n for n in publication.NAMES]:
            refresh(snapshot[key])
    original = snapshot[P + "contract"]
    manifest = []
    for member in original["resourceManifest"]:
        key = member["canonicalResourceKey"]
        content = publication.read(ROOT, key)
        manifest.append(
            {
                **member,
                "contentDigest": digest(content),
                "dependencies": [
                    {
                        "canonicalResourceKey": dep,
                        "contentDigest": digest(publication.read(ROOT, dep)),
                    }
                    for dep in sorted(discovered_dependencies(key, content))
                ],
            }
        )
    forged = definition("architecture-interpretation", manifest, [P + "conformance"], version="1.5")
    snapshot[P + "contract"] = forged
    assert forged["semanticContractFingerprint"] != SCF
    assert verify_semantic_contract(forged).success
    bundle = [
        {
            "canonicalResourceKey": m["canonicalResourceKey"],
            "content": publication.read(ROOT, m["canonicalResourceKey"]),
        }
        for m in manifest
    ]
    assert validate_semantic_resource_closure(forged, bundle).closure_valid
    with pytest.raises(
        publication.PublicationError, match="unauthorized_recipe_operation_or_encoding"
    ):
        publication.qualify(ROOT)


def test_current_candidate_mirrors_match_canonical_inputs() -> None:
    # Current candidate bytes are qualified per revision, not frozen by a
    # previous development merge. Released distributions have separate artifact
    # verification in test_release_authority_enforcement.
    for name in publication.NAMES:
        expected = (
            ROOT / "contracts/architecture-interpretation/v1.5/resources" / (name + ".json")
        ).read_bytes()
        filename = "architecture-interpretation-1.5-" + name + ".json"
        assert (
            ROOT / "contracts/semantic-contract/v1.0/resources" / filename
        ).read_bytes() == expected
        assert (
            ROOT / "src/adr_kit/semantic_contract/v1_0/resources" / filename
        ).read_bytes() == expected


def test_deterministic_version_isolated_generation() -> None:
    before = {
        p: p.read_bytes()
        for directory in ("contracts", "src/adr_kit/semantic_contract")
        for p in (ROOT / directory).rglob("*.json")
    }
    result = subprocess.run(
        [sys.executable, "scripts/generate_semantic_contract_assets.py", "--publish-ai15-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert {p: (ROOT / p).read_bytes() for p in before} == before


def test_exact_discovery_rejects_missing_versions_keys_and_resources() -> None:
    assert load_semantic_resource(P + "contract")["semanticContractFingerprint"] == SCF
    assert (
        load_semantic_resource("normalized-model/2.5/contract")["semanticContractFingerprint"]
        == publication.NM25_SCF
    )
    with pytest.raises(LookupError):
        get_semantic_contract("architecture-interpretation", "99.99")
    for key in (
        P + "missing",
        P + "../1.4/rules",
        P + "required/output",
        "architecture-interpretation/99.99/rules",
    ):
        with pytest.raises(LookupError):
            load_semantic_resource(key)
    contract = get_semantic_contract("architecture-interpretation", "1.5")
    bundle = [
        {
            "canonicalResourceKey": m.canonical_resource_key,
            "content": load_semantic_resource(m.canonical_resource_key),
        }
        for m in contract.resource_manifest
    ]
    assert not validate_semantic_resource_closure(contract, bundle[:-1]).closure_valid
    corrupted = copy.deepcopy(bundle)
    corrupted[0]["content"] = {"tampered": True}
    assert not validate_semantic_resource_closure(contract, corrupted).closure_valid
    extra = [
        *bundle,
        {"canonicalResourceKey": "architecture-interpretation/99.99/rules", "content": {}},
    ]
    assert not validate_semantic_resource_closure(contract, extra).closure_valid


def test_exact_installed_wheel_discovery(tmp_path: Path) -> None:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path))
    wheels = tmp_path / "wheels"
    built = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheels), str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    wheel = next(wheels.glob("*.whl"))
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
import pathlib,sys
sys.path.insert(0,sys.argv[1])
import adr_kit
from adr_kit.semantic_contract import get_semantic_contract,load_semantic_resource,validate_semantic_resource_closure
assert pathlib.Path(adr_kit.__file__).is_relative_to(sys.argv[1])
c=get_semantic_contract('architecture-interpretation','1.5')
assert c.semantic_contract_fingerprint==sys.argv[2]
assert len(c.resource_manifest)==69
assert validate_semantic_resource_closure(c,[{'canonicalResourceKey':e.canonical_resource_key,'content':load_semantic_resource(e.canonical_resource_key)} for e in c.resource_manifest]).closure_valid
"""
    checked = subprocess.run(
        [sys.executable, "-I", "-c", code, str(installed), SCF],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
