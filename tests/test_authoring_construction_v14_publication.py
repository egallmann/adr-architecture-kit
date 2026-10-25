"""Immutable ACC 1.4 publication oracles, not construction execution tests."""

from __future__ import annotations

import copy
import hashlib
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from adr_kit.semantic_contract import (
    SemanticContractVersion,
    get_semantic_contract,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from scripts import qualify_acc14_publication as publication
from scripts.generate_semantic_contract_assets import discovered_dependencies
from tests.test_architecture_interpretation_v14_publication import (
    IMMUTABLE_SHA256,
    assert_immutable_publication,
)
from tests.test_authoring_construction_v13_publication import request as historical_request

ROOT = Path(__file__).resolve().parents[1]
PREFIX = publication.PREFIX
SCF = "scf:v1:sha256:98bbdf394aa53ce20e1ebbc3e9835eecae1b89e0cd9568f3abee4d983c20b9f5"
RESOURCE_COUNT = 108
IMMUTABLE_BYTES: dict[str, str] = {
    "contracts/authoring-construction/v1.3/contract.json": "fdb5d13e1e6d83da2aaadcd40211bcd33be9e550d178a85ad071b58ed99b6124",
    "contracts/authoring-construction/v1.3/resources/compatibility.json": "0b3b804485701d15129e5f2d066b4d7b742af310cb0591c8547c1f5f704adc79",
    "contracts/authoring-construction/v1.3/resources/composition-bindings.json": "13fd345692882869f2a9bfe26de1130bfc6d3913b3c4e3f85e1de8b0f5bcd843",
    "contracts/authoring-construction/v1.3/resources/composition-bindings.schema.json": "164a9b9342576fcf7c0c88a393e5ffaaa49c98872b68ac8d74fa13fa5280b4ea",
    "contracts/authoring-construction/v1.3/resources/conformance.json": "1e88e9107f22b9ffbad3efa1c3c23c87adb11413daf8aa13bc302d227bee3029",
    "contracts/authoring-construction/v1.3/resources/conformance.schema.json": "2d5cadf66d628585d6c6d45ea56815bb5efb2b4dc959d57100424c0f09837a12",
    "contracts/authoring-construction/v1.3/resources/ledger.schema.json": "2153ab360266d9f54796bdcf45e47b85b02d45c7ee6d0a6d27e514fd159b3efa",
    "contracts/authoring-construction/v1.3/resources/rules.json": "bce1c686b98b695c28827a753560be084d60ca0ea8a07a84c297d24eb8bb52d7",
    "contracts/authoring-construction/v1.3/schema.json": "c774668f24fc032d6c313141619c3d4a58c1a0fbd2f819ff45a0376db45d08db",
    "contracts/authoring-construction/v1.4/contract.json": "622246456a997a190b8a73a21fc900d5540a72f3c9732bf60739bd375b13d180",
    "contracts/authoring-construction/v1.4/resources/compatibility.json": "d1704ce5f4e2aded310ec1c185a2163d4b65c74ae5b3096b0af6225739f0ac78",
    "contracts/authoring-construction/v1.4/resources/composition-bindings.json": "aaa526f06d2e09a3c0588c32f634c69622b28de03f8e91bb2bbbd4483f3e5c7a",
    "contracts/authoring-construction/v1.4/resources/composition-bindings.schema.json": "2fdce81bee187492b75055b73f181bb0cc8dd574e72a933ebac6af28301d0690",
    "contracts/authoring-construction/v1.4/resources/conformance.json": "d88b6ffeb72ce1d920722ab8d94180d21f8f083505967ceffa2d6887e4d04897",
    "contracts/authoring-construction/v1.4/resources/conformance.schema.json": "5bae637f9e788de9209b6670a417f15eb5ae4526acc37308407f0c2ed024ee68",
    "contracts/authoring-construction/v1.4/resources/rules.json": "a1325c426d4b6a4db1f4cb16b45af04346bb6521a0eda5cbf8a540b27872f5d6",
    "contracts/authoring-construction/v1.4/schema.json": "82bea8e0904f2637e184dce8c1cb787300d997cea5307bbc1c51ba43e56f394d",
}


def immutable_bytes(root: Path) -> None:
    assert_immutable_publication(root)
    for relative, expected in IMMUTABLE_BYTES.items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative


def bundle() -> list[dict[str, Any]]:
    return [
        {
            "canonicalResourceKey": e.canonical_resource_key,
            "content": load_semantic_resource(e.canonical_resource_key),
        }
        for e in get_semantic_contract("authoring-construction", "1.4").resource_manifest
    ]


def validator(fragment: str) -> Draft202012Validator:
    schemas = {}
    for entry in bundle():
        value = entry["content"]
        if not isinstance(value, dict) or value.get("$schema") not in {
            "http://json-schema.org/draft-07/schema#",
            "https://json-schema.org/draft/2020-12/schema",
        }:
            continue
        resource = Resource.from_contents(value)
        if "$id" in value:
            schemas[value["$id"]] = resource
        schemas[
            "https://adr-kit.dev/semantic-contract/resources/"
            + entry["canonicalResourceKey"]
            + ".json"
        ] = resource
    registry: Registry[Any] = Registry().with_resources(schemas.items())
    schema = publication.read(ROOT, PREFIX + "schema")
    return Draft202012Validator({"$ref": schema["$id"] + "#/$defs/" + fragment}, registry=registry)


def request() -> dict[str, Any]:
    # Build a legitimate successor fixture, not a runtime predecessor adapter.
    value = historical_request()
    value["contract_version"] = "1.4"
    value["basis"]["acc"].update(version="1.4", semantic_contract_fingerprint=SCF)
    closure = publication.read(ROOT, PREFIX + "schema")["$defs"]["exact_ai14_closure"]
    value["basis"]["architecture_interpretation"] = {
        "family": "architecture-interpretation",
        "version": "1.4",
        "semantic_contract_fingerprint": publication.AI_SCF,
        "authority_closure": {
            "family": "architecture-interpretation",
            "version": "1.4",
            "resources": copy.deepcopy(closure["properties"]["resources"]["items"]["enum"]),
        },
    }
    return value


def output_evidence() -> dict[str, Any]:
    catalog = publication.read(ROOT, publication.CATALOG)
    row = next(r for r in catalog["types"] if r["semantic_type"] == "adr/logical")
    output = next(o for o in row["outputs"] if o["destination"] == "/summary")
    return {
        "architecture_interpretation": request()["basis"]["architecture_interpretation"],
        "catalog": publication.qualification(ROOT, publication.CATALOG),
        "status": "blocked",
        "all_required_destinations_accounted": False,
        "representation_verification": "unavailable",
        "units": [
            {
                "semantic_type": row["semantic_type"],
                "output_branch": row["output_branch"],
                "identity": {
                    "identity_kind": "canonical_uuidv7",
                    "components": ["01900000-0000-7000-8000-000000000001"],
                },
                "destinations": [
                    {
                        "destination": output["destination"],
                        "producer_rule_id": output["producer"]["rule_id"],
                        "producer_rule": output["producer"]["rule"],
                        "verification": {
                            k: "verified"
                            for k in (
                                "source_and_identity",
                                "applicability_and_context",
                                "inputs_and_types",
                                "exact_operation",
                                "complete_output",
                            )
                        },
                    }
                ],
                "blocked_destinations": ["/alias_ref"],
                "competing_destinations": [],
                "all_applicable_accounted": False,
            }
        ],
    }


def test_exact_definition_closure_dependencies_and_mirrors() -> None:
    contract = get_semantic_contract("authoring-construction", "1.4")
    wire = contract.to_wire()
    assert wire["semanticContractFingerprint"] == SCF
    assert len(contract.resource_manifest) == RESOURCE_COUNT
    assert wire["frozenNormativeConformanceResources"] == [PREFIX + "conformance"]
    assert verify_semantic_contract(contract).success
    assert validate_semantic_resource_closure(contract, bundle()).closure_valid
    keys = {e.canonical_resource_key for e in contract.resource_manifest}
    for family, version in (
        ("architecture-interpretation", "1.4"),
        ("normalized-model", "2.5"),
        ("authoring-construction", "1.3"),
    ):
        assert {
            e.canonical_resource_key
            for e in get_semantic_contract(family, version).resource_manifest
        } <= keys
    for entry in wire["resourceManifest"]:
        assert {
            d["canonicalResourceKey"] for d in entry["dependencies"]
        } == discovered_dependencies(
            entry["canonicalResourceKey"], load_semantic_resource(entry["canonicalResourceKey"])
        )
    canonical = ROOT / "contracts/authoring-construction/v1.4"
    for name in publication.NAMES:
        data = (
            canonical / ("schema.json" if name == "schema" else f"resources/{name}.json")
        ).read_bytes()
        assert SCF.encode() not in data
        for directory in (
            "contracts/semantic-contract/v1.0/resources",
            "src/adr_kit/semantic_contract/v1_0/resources",
        ):
            assert (
                ROOT / directory / ("authoring-construction-1.4-" + name + ".json")
            ).read_bytes() == data
    for relative in (
        "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.4.json",
        "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.4.json",
        "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.4.json",
    ):
        assert (ROOT / relative).read_bytes() == (canonical / "contract.json").read_bytes()
    for key in (
        PREFIX + "missing",
        PREFIX + "../1.3/rules",
        PREFIX + "composition/bindings",
        "authoring-construction/99.99/rules",
    ):
        with pytest.raises(LookupError):
            load_semantic_resource(key)
    with pytest.raises(LookupError):
        get_semantic_contract("authoring-construction", "99.99")
    assert (
        load_semantic_resource(publication.AI + "contract")
        == get_semantic_contract("architecture-interpretation", "1.4").to_wire()
    )
    assert (
        load_semantic_resource(publication.BASE + "contract")
        == get_semantic_contract("authoring-construction", "1.3").to_wire()
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "extra",
        "content",
        "digest",
        "dependency",
        "fingerprint",
        "wrong_ACC",
        "wrong_AI",
        "wrong_NM",
    ],
)
def test_independent_closure_and_fingerprint_mutations(fault: str) -> None:
    wire = get_semantic_contract("authoring-construction", "1.4").to_wire()
    supplied = bundle()
    if fault == "missing":
        supplied.pop()
    elif fault == "extra":
        supplied.append({"canonicalResourceKey": PREFIX + "unqualified", "content": {}})
    elif fault == "content":
        supplied[-1]["content"]["mutated"] = True
    elif fault == "digest":
        wire["resourceManifest"][-1]["contentDigest"] = "sha256:" + "0" * 64
    elif fault == "dependency":
        wire["resourceManifest"][-1]["dependencies"] = [
            {"canonicalResourceKey": PREFIX + "rules", "contentDigest": "sha256:" + "0" * 64}
        ]
    elif fault == "fingerprint":
        wire["semanticContractFingerprint"] = "scf:v1:sha256:" + "0" * 64
    elif fault == "wrong_ACC":
        wire["semanticContractVersion"] = "1.3"
    else:
        key = (
            publication.AI + "contract"
            if fault == "wrong_AI"
            else "normalized-model/2.5/schema/normalized-entity.schema"
        )
        selected = next(e for e in supplied if e["canonicalResourceKey"] == key)
        selected["content"] = (
            get_semantic_contract("architecture-interpretation", "1.3").to_wire()
            if fault == "wrong_AI"
            else load_semantic_resource("normalized-model/2.4/schema/normalized-entity.schema")
        )
    assert not validate_semantic_resource_closure(
        SemanticContractVersion.from_wire(wire), supplied
    ).closure_valid


def test_closed_publication_qualifier_and_actual_inherited_authority() -> None:
    report = publication.qualify()
    assert report["composition_bindings"] == 1
    assert report["inherited_cases_reviewed"] == 159
    assert report["conformance_cases"] == 263
    assert report["output_accounting"] == {"QUALIFIED": 186, "BLOCKED": 269}
    table = publication.read(ROOT, PREFIX + "composition-bindings")
    assert (
        table["rows"] == publication.read(ROOT, publication.BASE + "composition-bindings")["rows"]
    )
    row = table["rows"][0]
    assert row["ai_ownership_authority"]["version"] == "1.3"
    assert (
        row["ai_ownership_authority"]["canonical_resource_key"]
        == publication.INHERITED_AI + "lifecycle-ownership"
    )
    assert row["ai_ownership_authority"]["rule_id"] == "declaring-lifecycle.adr-logical.decisions"
    assert report["complete_interpretation"] == "Unavailable"
    assert report["runtime_execution"] is False
    # Schema bytes/identity stay historical. Representation verification adds
    # no independently owned semantic value or invented ledger shape.
    assert publication.read(ROOT, PREFIX + "rules")["ledger"]["schema"] == publication.LEDGER
    assert not (
        ROOT / "contracts/authoring-construction/v1.4/resources/ledger.schema.json"
    ).exists()


@pytest.mark.parametrize(
    "fault",
    [
        "ACC_version",
        "AI_version",
        "AI_fingerprint",
        "AI_closure",
        "NM_version",
        "NM_fingerprint",
        "NM_closure",
    ],
)
def test_exact_request_schema_selection(fault: str) -> None:
    value = request()
    check = validator("authoring_request")
    check.validate(value)
    if fault == "ACC_version":
        value["contract_version"] = "1.3"
    elif fault.startswith("AI_"):
        q = value["basis"]["architecture_interpretation"]
        if fault == "AI_version":
            q["version"] = "1.3"
        elif fault == "AI_fingerprint":
            q["semantic_contract_fingerprint"] = publication.ACC13_SCF
        else:
            q["authority_closure"]["resources"].pop()
    else:
        q = value["basis"]["normalized_model"]
        if fault == "NM_version":
            q["version"] = "2.4"
        elif fault == "NM_fingerprint":
            q["semantic_contract_fingerprint"] = publication.AI_SCF
        else:
            q["resources"].pop()
    assert not check.is_valid(value)


def test_request_resource_permutations_and_complete_NM_shape() -> None:
    value = request()
    check = validator("authoring_request")
    check.validate(value)
    value["basis"]["architecture_interpretation"]["authority_closure"]["resources"].reverse()
    value["basis"]["normalized_model"]["resources"].reverse()
    value["request"]["fragments"].reverse()
    check.validate(value)
    assert not validator("normalized_result").is_valid(
        {
            "normalized_contract": value["basis"]["normalized_model"],
            "semantic_digest": "sha256:" + "0" * 64,
            "model": {"schema_version": "2.5", "entities": []},
        }
    )


@pytest.mark.parametrize(
    "fault",
    [
        "blocked_complete",
        "competing",
        "missing_check",
        "unverified",
        "changed_producer",
        "wrong_rule_digest",
        "wrong_catalog",
        "blocked_as_producer",
        "wrong_branch",
        "wrong_type",
    ],
)
def test_required_output_evidence_fails_closed(fault: str) -> None:
    value = output_evidence()
    check = validator("required_output_qualification")
    check.validate(value)
    unit = value["units"][0]
    output = unit["destinations"][0]
    if fault == "blocked_complete":
        value["status"] = "complete"
    elif fault == "competing":
        unit["destinations"].append(copy.deepcopy(output))
    elif fault == "missing_check":
        output["verification"].pop("source_and_identity")
    elif fault == "unverified":
        value.update(
            status="complete",
            all_required_destinations_accounted=True,
            representation_verification="valid",
        )
        unit.update(blocked_destinations=[], all_applicable_accounted=True)
        output["verification"]["exact_operation"] = "unavailable"
    elif fault == "changed_producer":
        output["producer_rule_id"] = "invented"
    elif fault == "wrong_rule_digest":
        output["producer_rule"]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "wrong_catalog":
        value["catalog"]["canonical_resource_key"] = publication.INHERITED_AI + "rules"
    elif fault == "blocked_as_producer":
        output["destination"] = "/alias_ref"
    elif fault == "wrong_branch":
        unit["output_branch"] = "canonical-relationship"
    else:
        unit["semantic_type"] = "entity/unknown"
    assert not check.is_valid(value)


def test_Constructed_requires_independent_output_proof_not_flags_or_schema_alone() -> None:
    schema = publication.read(ROOT, PREFIX + "schema")["$defs"]
    assert "required_output" in schema["construction_qualification"]["required"]
    condition = schema["construction_result"]["allOf"][2]["then"]["properties"][
        "construction_qualification"
    ]["properties"]
    assert condition["required_output"]["properties"]["status"] == {"const": "complete"}
    rules = publication.read(ROOT, PREFIX + "rules")
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
    assert rules["publication_posture"]["execution_capability_advertised"] is False


def test_all_cases_reviewed_by_exact_identity_without_fabricated_successor_rules() -> None:
    cases = publication.read(ROOT, PREFIX + "conformance")["cases"]
    previous = publication.read(ROOT, publication.BASE + "conformance")["cases"]
    assert [c["case_id"] for c in cases] == [f"ACC14-{i:03}" for i in range(1, 264)]
    assert [c["requalified_from"] for c in cases[:159]] == [c["case_id"] for c in previous]
    for index, (old, case) in enumerate(zip(previous, cases)):
        selected = case["fixture"]["input"]["inherited_case"]
        assert selected == publication.qualification(
            ROOT, publication.BASE + "conformance", f"/cases/{index}"
        )
        assert case["review"] == publication.review_case(old)[1]
        assert case["fixture"]["input"]["inherited_fixture_is_successor_request"] is False
        if index != 121:
            assert case["assertions"] == old["assertions"]
    assert all(c["runtime_coverage"] == "authority_only_not_implemented" for c in cases)
    categories = Counter(c.get("review_class") for c in cases[159:])
    assert categories["required_output_refinement"] == 53
    assert categories["BLOCKED"] == 14


@pytest.fixture
def snapshot(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    keys = {e["canonicalResourceKey"] for e in bundle()} | {
        publication.AI + "contract",
        publication.BASE + "contract",
        "normalized-model/2.5/contract",
    }
    data = {key: publication.read(ROOT, key) for key in keys}
    monkeypatch.setattr(publication, "read", lambda root, key: copy.deepcopy(data[key]))
    return data


@pytest.mark.parametrize(
    "fault",
    [
        "AI_SCF",
        "missing",
        "catalog",
        "binding_rule",
        "binding_SCF",
        "duplicate_binding",
        "prepared_inventory",
        "blocked_policy",
        "representation_equality",
        "missing_output_gate",
        "weakened_Constructed",
        "wrong_schema_ref",
        "wrong_dialect",
        "omitted_case",
        "forged_case",
        "semantic_loss",
    ],
)
def test_independent_publication_mutations(snapshot: dict[str, Any], fault: str) -> None:
    if fault == "AI_SCF":
        snapshot[publication.AI + "contract"]["semanticContractFingerprint"] = publication.ACC13_SCF
    elif fault == "missing":
        snapshot.pop(publication.INHERITED_AI + "lifecycle-ownership")
    elif fault == "catalog":
        snapshot[publication.CATALOG]["types"][0]["outputs"][0]["status"] = "BLOCKED"
    elif fault == "binding_rule":
        snapshot[PREFIX + "composition-bindings"]["rows"][0]["ai_ownership_authority"][
            "version"
        ] = "1.4"
    elif fault == "binding_SCF":
        snapshot[PREFIX + "composition-bindings"]["rows"][0]["ai_ownership_authority"][
            "semantic_contract_fingerprint"
        ] = publication.AI_SCF
    elif fault == "duplicate_binding":
        snapshot[PREFIX + "composition-bindings"]["rows"] *= 2
    elif fault == "prepared_inventory":
        snapshot[PREFIX + "composition-bindings"]["rows"][0]["child_object"] = "ADC_input_contract"
    elif fault == "blocked_policy":
        snapshot[PREFIX + "rules"]["required_output"]["BLOCKED_is_producer"] = True
    elif fault == "representation_equality":
        snapshot[PREFIX + "rules"]["equivalence"]["representation_outputs"][
            "representation_proof_is_equality"
        ] = True
    elif fault == "missing_output_gate":
        snapshot[PREFIX + "schema"]["$defs"]["construction_qualification"]["required"].remove(
            "required_output"
        )
    elif fault == "weakened_Constructed":
        snapshot[PREFIX + "schema"]["$defs"]["construction_result"]["allOf"][2]["then"][
            "properties"
        ]["construction_qualification"]["properties"].pop("required_output")
    elif fault == "wrong_schema_ref":
        snapshot[PREFIX + "schema"]["$defs"]["normalized_result"]["properties"]["model"][
            "$ref"
        ] = "../../normalized-model/2.4/schema/normalized-architecture-model.schema.json"
    elif fault == "wrong_dialect":
        snapshot[PREFIX + "schema"]["$schema"] = "urn:unknown-dialect"
    elif fault == "omitted_case":
        snapshot[PREFIX + "conformance"]["cases"].pop(0)
    elif fault == "forged_case":
        snapshot[PREFIX + "conformance"]["cases"][0][
            "review"
        ] = "no independent output proof required"
    else:
        snapshot[publication.INHERITED_AI + "field-dispositions-1.7-to-2.5"]["semantic_types"].pop()
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        publication.qualify()


def test_historical_integrity_and_deterministic_generation() -> None:
    immutable_bytes(ROOT)

    def files() -> dict[str, bytes]:
        paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
        paths += [
            str(p.relative_to(ROOT)).replace("\\", "/")
            for p in (ROOT / "contracts/authoring-construction/v1.4").rglob("*.json")
        ]
        return {p: (ROOT / p).read_bytes() for p in paths if p and (ROOT / p).is_file()}

    before = files()
    for _ in range(2):
        subprocess.run(
            [
                sys.executable,
                "scripts/generate_semantic_contract_assets.py",
                "--publish-acc14-only",
            ],
            cwd=ROOT,
            check=True,
        )
        assert files() == before
        immutable_bytes(ROOT)


def test_future_publications_and_explicit_selection_do_not_invalidate_integrity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path))
    # This is a test-only unrelated file; it publishes no successor authority.
    for relative in IMMUTABLE_SHA256 | IMMUTABLE_BYTES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    (tmp_path / "contracts/authoring-construction/v1.5").mkdir(parents=True)
    (tmp_path / "contracts/authoring-construction/v1.5/contract.json").write_text(
        "{}", encoding="utf-8"
    )
    from adr_kit import semantic_contract

    selected = get_semantic_contract("authoring-construction", "1.4")
    monkeypatch.setattr(semantic_contract, "list_semantic_contracts", lambda: (selected,))
    test_exact_definition_closure_dependencies_and_mirrors()
    immutable_bytes(tmp_path)
    assert (tmp_path / "contracts/authoring-construction/v1.5/contract.json").is_file()
    # An unrelated successor is allowed, a historical byte mutation still fails.
    historical = (
        tmp_path
        / "contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.3-rules.json"
    )
    historical.write_bytes(historical.read_bytes() + b"\n")
    with pytest.raises(AssertionError, match="architecture-interpretation-1.3"):
        immutable_bytes(tmp_path)


def test_installed_wheel_exact_discovery(tmp_path: Path) -> None:
    if os.name == "nt" and not str(tmp_path).startswith("\\\\?\\"):
        tmp_path = Path("\\\\?\\" + str(tmp_path))
    wheels = tmp_path / "wheels"
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheels), str(ROOT)],
        check=True,
        capture_output=True,
    )
    target = tmp_path / "installed"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(target),
            str(next(wheels.glob("*.whl"))),
        ],
        check=True,
        capture_output=True,
    )
    code = (
        "from adr_kit.semantic_contract import *; c=get_semantic_contract('authoring-construction','1.4'); assert c.to_wire()['semanticContractFingerprint']=="
        + repr(SCF)
        + "; assert len(c.resource_manifest)=="
        + str(RESOURCE_COUNT)
        + "; assert validate_semantic_resource_closure(c,[{'canonicalResourceKey':e.canonical_resource_key,'content':load_semantic_resource(e.canonical_resource_key)} for e in c.resource_manifest]).closure_valid"
    )
    env = dict(os.environ, PYTHONPATH=str(target))
    subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=env, check=True, capture_output=True
    )
