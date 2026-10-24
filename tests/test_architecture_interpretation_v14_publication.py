"""AI 1.4 authority qualification, never materialization execution conformance."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import (
    SemanticContractVersion,
    get_semantic_contract,
    list_semantic_contracts,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)
from scripts import qualify_ai14_publication as publication
from scripts.generate_semantic_contract_assets import discovered_dependencies

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "contracts/architecture-interpretation/v1.4"
PREFIX = publication.PREFIX
CATALOG = publication.CATALOG
BASELINE = "aac46c360f078ea2e11d46565649e64128209f80"
SCF = "scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7"


def resource(name: str) -> Any:
    return json.loads((CANONICAL / "resources" / (name + ".json")).read_text(encoding="utf-8"))


def matrix() -> list[dict[str, str]]:
    path = next((ROOT / "adrs/logical").glob("ADR-L-0038-*.yaml"))
    adr = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert adr["status"] == "accepted"
    text = next(row["rationale"] for row in adr["decisions"] if row["alias_id"] == "DEC-9011")
    return yaml.safe_load(text.split("```yaml\n")[1].split("```", 1)[0])


@pytest.fixture
def snapshot(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A fresh in-memory publication snapshot per mutation; no cached trust."""
    originals = publication.read
    values = {PREFIX + name: resource(name) for name in publication.NAMES}

    @lru_cache(maxsize=None)
    def read(root: Path, key: str) -> Any:
        return values[key] if key in values else originals(root, key)

    monkeypatch.setattr(publication, "read", read)
    return values


def test_independent_publication_qualification(snapshot: dict[str, Any]) -> None:
    assert publication.qualify(ROOT) == {
        "semantic_types": 27,
        "output_accounting": {"QUALIFIED": 186, "BLOCKED": 269},
        "complete_interpretation": "Unavailable",
        "runtime_execution": False,
    }


def test_all_types_and_label_selectors_match_accepted_authority() -> None:
    catalog = resource(CATALOG)
    types = {row["semantic_type"]: row for row in catalog["types"]}
    assert len(types) == 27
    oracle = {
        case["semantic_type"]: case["fixture"]
        for case in resource("conformance")["cases"]
        if case["category"] == "label_policy"
    }
    assert len(oracle) == 18
    for policy in matrix():
        row = types[policy["semantic_type"]]
        if policy["name"] == "not-applicable":
            assert not any(
                entry["destination"] in {"/name", "/summary"} for entry in row["outputs"]
            )
            continue
        for destination in ("name", "summary"):
            mode, field = policy[destination].split(":")
            assert oracle[row["semantic_type"]][destination] == {
                "mode": "authored" if mode == "A" else "representation",
                "source_field": field,
            }
            selected = next(
                entry for entry in row["outputs"] if entry["destination"] == "/" + destination
            )
            assert selected["status"] == "QUALIFIED"
            assert selected["producer"]["kind"] == (
                "field_placement" if mode == "A" else "literal_string_copy"
            )
            if mode == "R":
                assert selected["producer"]["source_field"] == field
                assert selected["classification"] == "representation_only"
    assert (
        Counter(
            row["producer"]["kind"]
            for ty in types.values()
            for row in ty["outputs"]
            if row["status"] == "QUALIFIED"
        )["literal_string_copy"]
        == 26
    )


@pytest.mark.parametrize("ty", [row["semantic_type"] for row in resource(CATALOG)["types"]])
def test_every_type_has_independent_branch_and_output_accounting(ty: str) -> None:
    catalog = resource(CATALOG)
    row = next(row for row in catalog["types"] if row["semantic_type"] == ty)
    assert row["root_permission"] == "catalog_membership_does_not_authorize_independent_root"
    paths = [entry["destination"] for entry in row["outputs"]]
    assert len(paths) == len(set(paths))
    for entry in row["outputs"]:
        if entry["status"] == "BLOCKED":
            assert "producer" not in entry
            assert entry["blocked"]["allows_complete_materialization"] is False
            assert entry["blocked"]["code"] in catalog["blockers"]
        else:
            assert "producer" in entry and "blocked" not in entry
    assert (
        len(
            [
                case
                for case in resource("conformance")["cases"]
                if case["semantic_type"] == ty and case["category"] == "output_coverage"
            ]
        )
        == 1
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing_type",
        "duplicate_type",
        "missing_required",
        "competing_producer",
        "wrong_source",
        "wrong_destination",
        "wrong_digest",
        "wrong_rule",
        "unknown_operation",
        "wrong_input",
        "changed_label",
        "missing_field_inventory",
        "semantic_as_ceremony",
        "missing_owner",
        "wrong_owner",
        "forged_producer",
        "wrong_branch",
        "missing_conditional",
        "broken_reference",
        "open_schema",
        "extra_proof",
        "unfrozen_conformance_id",
        "runtime_claim",
        "changed_inheritance",
        "missing_semantic_extensions",
        "blocked_known_identity",
        "wrong_destination_schema",
        "missing_nested_requirement",
        "wrong_applicability",
        "external_schema_ref",
        "invalid_schema_dialect",
    ],
)
def test_negative_publication_mutations_fail_closed(snapshot: dict[str, Any], fault: str) -> None:
    catalog = snapshot[PREFIX + CATALOG]
    first = catalog["types"][0]
    literal = next(
        entry
        for row in catalog["types"]
        for entry in row["outputs"]
        if entry.get("producer", {}).get("kind") == "literal_string_copy"
    )
    if fault == "missing_type":
        catalog["types"].pop()
    elif fault == "duplicate_type":
        catalog["types"][-1] = copy.deepcopy(first)
    elif fault == "missing_required":
        first["outputs"] = [entry for entry in first["outputs"] if entry["destination"] != "/id"]
    elif fault == "competing_producer":
        first["outputs"].append(copy.deepcopy(first["outputs"][0]))
    elif fault == "wrong_source":
        first["source_schema"]["schema_pointer"] = "/missing"
    elif fault == "wrong_destination":
        literal["destination"] = "/wrong"
    elif fault == "wrong_digest":
        literal["producer"]["inputs"][0]["content_digest"] = "sha256:" + "0" * 64
    elif fault == "wrong_rule":
        literal["producer"]["rule_id"] = "forged-rule"
    elif fault == "unknown_operation":
        literal["producer"]["rule"] = {"local_rule": "truncate"}
    elif fault == "wrong_input":
        literal["producer"]["inputs"][0]["schema_pointer"] = "/properties/id"
    elif fault == "changed_label":
        literal["producer"]["source_field"] = "title"
    elif fault == "missing_field_inventory":
        entry = next(
            entry
            for row in catalog["types"]
            for entry in row["outputs"]
            if entry.get("producer", {}).get("kind") == "field_inventory"
        )
        entry["producer"]["inputs"].pop()
    elif fault == "semantic_as_ceremony":
        entry = next(
            entry
            for entry in first["outputs"]
            if entry.get("producer", {}).get("kind") == "field_placement"
        )
        entry["classification"] = "representation_only"
    elif fault in {"missing_owner", "wrong_owner"}:
        entry = next(
            entry
            for row in catalog["types"]
            for entry in row["outputs"]
            if entry.get("producer", {}).get("kind") == "contextual_rule"
        )
        if fault == "missing_owner":
            entry["prerequisites"] = []
        else:
            entry["producer"]["inputs"] = [
                publication.qualification(
                    ROOT, publication.BASE + "lifecycle-ownership", "/rows/16"
                )
            ]
    elif fault == "forged_producer":
        first["outputs"][0]["producer"] = copy.deepcopy(literal["producer"])
    elif fault == "wrong_branch":
        first["output_branch"] = "normative-proposition"
    elif fault == "missing_conditional":
        catalog["branches"][0]["requirements"].pop()
    elif fault == "broken_reference":
        first["source_schema"]["canonical_resource_key"] = "authoring/1.7/schema/missing"
    elif fault == "open_schema":
        snapshot[PREFIX + CATALOG + ".schema"]["additionalProperties"] = True
    elif fault == "extra_proof":
        first["outputs"][0]["proof_is_true"] = True
    elif fault == "unfrozen_conformance_id":
        snapshot[PREFIX + "conformance"]["cases"][1]["id"] = "AI14-001"
    elif fault == "runtime_claim":
        snapshot[PREFIX + "rules"]["public_boundary"]["execution"] = "implemented"
    elif fault == "changed_inheritance":
        snapshot[PREFIX + "rules"]["inherits"]["semantic_contract_fingerprint"] = (
            "scf:v1:sha256:" + "0" * 64
        )
    elif fault == "missing_semantic_extensions":
        first["outputs"] = [
            entry
            for entry in first["outputs"]
            if "{semantic_field_key}" not in entry["destination"]
        ]
    elif fault == "blocked_known_identity":
        entry = next(entry for entry in first["outputs"] if entry["destination"] == "/id")
        entry.pop("producer")
        entry["status"] = "BLOCKED"
        entry["blocked"] = copy.deepcopy(
            next(item["blocked"] for item in first["outputs"] if item["status"] == "BLOCKED")
        )
    elif fault == "wrong_destination_schema":
        literal["destination_schema"] = publication.qualification(
            ROOT, "normalized-model/2.5/schema/normalized-entity.schema", "/oneOf/1/properties/name"
        )
    elif fault == "missing_nested_requirement":
        entry = next(
            entry
            for row in catalog["types"]
            for entry in row["outputs"]
            if entry["required_subdestinations"]
        )
        entry["required_subdestinations"].pop()
    elif fault == "wrong_applicability":
        literal["applicability"]["output_branch"] = "canonical-relationship"
    elif fault == "external_schema_ref":
        snapshot[PREFIX + CATALOG + ".schema"]["$ref"] = "https://unqualified.invalid/schema.json"
    elif fault == "invalid_schema_dialect":
        snapshot[PREFIX + CATALOG + ".schema"]["$schema"] = "https://unqualified.invalid/dialect"
    with pytest.raises((publication.PublicationError, FileNotFoundError)):
        publication.qualify(ROOT, history=False)


def test_exact_fingerprint_closure_dependencies_and_package_bytes() -> None:
    contract = get_semantic_contract("architecture-interpretation", "1.4")
    wire = contract.to_wire()
    assert wire["semanticContractFingerprint"] == SCF
    assert len(contract.resource_manifest) == 60
    assert wire["frozenNormativeConformanceResources"] == [PREFIX + "conformance"]
    assert verify_semantic_contract(contract).success
    bundle = [
        {
            "canonicalResourceKey": entry.canonical_resource_key,
            "content": load_semantic_resource(entry.canonical_resource_key),
        }
        for entry in contract.resource_manifest
    ]
    assert validate_semantic_resource_closure(contract, bundle).closure_valid
    for entry in wire["resourceManifest"]:
        selected = load_semantic_resource(entry["canonicalResourceKey"])
        assert {
            dependency["canonicalResourceKey"] for dependency in entry["dependencies"]
        } == discovered_dependencies(entry["canonicalResourceKey"], selected)
    for name in publication.NAMES:
        data = (CANONICAL / "resources" / (name + ".json")).read_bytes()
        assert SCF.encode() not in data
        for directory in (
            "contracts/semantic-contract/v1.0/resources",
            "src/adr_kit/semantic_contract/v1_0/resources",
        ):
            assert (
                ROOT / directory / ("architecture-interpretation-1.4-" + name + ".json")
            ).read_bytes() == data
    for path in (
        "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.4.json",
        "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.4.json",
        "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.4.json",
    ):
        assert (ROOT / path).read_bytes() == (CANONICAL / "contract.json").read_bytes()
    assert all(item.semantic_contract_version != "1.4" for item in list_semantic_contracts())
    for key in (
        PREFIX + "missing",
        PREFIX + "../1.3/rules",
        PREFIX + "required/output",
        "architecture-interpretation/99.99/rules",
    ):
        with pytest.raises(LookupError):
            load_semantic_resource(key)
    with pytest.raises(LookupError):
        get_semantic_contract("architecture-interpretation", "99.99")


@pytest.mark.parametrize("fault", ["missing", "modified", "extra", "fingerprint", "dependency"])
def test_closure_mutations(fault: str) -> None:
    contract = get_semantic_contract("architecture-interpretation", "1.4")
    wire = contract.to_wire()
    bundle = [
        {
            "canonicalResourceKey": entry.canonical_resource_key,
            "content": load_semantic_resource(entry.canonical_resource_key),
        }
        for entry in contract.resource_manifest
    ]
    if fault == "missing":
        bundle.pop()
    elif fault == "modified":
        bundle[0]["content"]["tampered"] = True
    elif fault == "extra":
        bundle.append(
            {"canonicalResourceKey": "architecture-interpretation/1.4/unqualified", "content": {}}
        )
    elif fault == "fingerprint":
        wire["semanticContractFingerprint"] = "scf:v1:sha256:" + "0" * 64
    elif fault == "dependency":
        wire["resourceManifest"][-1]["dependencies"] = [
            {"canonicalResourceKey": PREFIX + "rules", "contentDigest": "sha256:" + "0" * 64}
        ]
    assert not validate_semantic_resource_closure(
        SemanticContractVersion.from_wire(wire), bundle
    ).closure_valid


def test_deterministic_generation_and_historical_git_preservation() -> None:
    paths = [CANONICAL / "contract.json", *CANONICAL.glob("resources/*.json")]
    before = {path: path.read_bytes() for path in paths}
    for _ in range(2):
        subprocess.run(
            [sys.executable, "scripts/generate_semantic_contract_assets.py", "--publish-ai14-only"],
            cwd=ROOT,
            check=True,
        )
        assert {path: path.read_bytes() for path in paths} == before
    changed = subprocess.check_output(
        [
            "git",
            "diff",
            "--name-only",
            BASELINE,
            "--",
            "contracts",
            "schema",
            "core",
            "src/adr_kit/semantic_contract/v1_0",
            "src/adr_kit/schema",
            "packages/node/src/generated",
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert all(
        "architecture-interpretation-1.4" in path
        or path.startswith("contracts/architecture-interpretation/v1.4/")
        for path in changed
    ), changed
    publication.qualified_history(ROOT)


def test_frozen_oracle_and_blocker_register_are_honest() -> None:
    conf = resource("conformance")
    assert len(conf["cases"]) == 85
    assert conf["authority_only"] is True and conf["runtime_execution_coverage"] is False
    assert all(case["coverage"] == "authority_only_not_runtime_execution" for case in conf["cases"])
    catalog = resource(CATALOG)
    schema = resource(CATALOG + ".schema")
    assert not list(Draft202012Validator(schema).iter_errors(catalog))
    system = next(row for row in catalog["types"] if row["semantic_type"] == "entity/system")
    summary = next(row for row in system["outputs"] if row["destination"] == "/summary")
    assert summary["producer"]["source_field"] == "alias_name"
    assert "label_duplication_only_no_substantive_system_description" in summary["verification"]
    assert {
        "custom_lifecycle",
        "declaring_context",
        "fingerprint_preimage",
        "uri_recipe",
        "created_at_encoding",
        "relationship_envelope",
    }.issubset(catalog["blockers"])
    assert catalog["coverage"]["BLOCKED"] == "missing_prerequisite_not_a_producer_or_coverage"


def test_resource_delivery_permutations_do_not_change_qualification(
    snapshot: dict[str, Any],
) -> None:
    before = publication.qualify(ROOT, history=False)
    delivered = list(reversed(snapshot.items()))
    snapshot.clear()
    snapshot.update(delivered)
    assert publication.qualify(ROOT, history=False) == before
    contract = get_semantic_contract("architecture-interpretation", "1.4")
    bundle = [
        {
            "canonicalResourceKey": entry.canonical_resource_key,
            "content": load_semantic_resource(entry.canonical_resource_key),
        }
        for entry in reversed(contract.resource_manifest)
    ]
    assert validate_semantic_resource_closure(contract, bundle).closure_valid


def test_changed_catalog_bytes_cannot_reuse_an_old_resource_qualification(
    snapshot: dict[str, Any],
) -> None:
    snapshot[PREFIX + CATALOG]["types"].reverse()
    with pytest.raises(publication.PublicationError, match="qualification_mismatch"):
        publication.qualify(ROOT, history=False)


def test_exact_installed_wheel_discovery(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheels"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(wheel_dir),
            str(ROOT),
        ],
        check=True,
        capture_output=True,
    )
    wheel = next(wheel_dir.glob("*.whl"))
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
c=get_semantic_contract('architecture-interpretation','1.4')
assert c.to_wire()['semanticContractFingerprint']==sys.argv[2]
assert validate_semantic_resource_closure(c,[{'canonicalResourceKey':e.canonical_resource_key,'content':load_semantic_resource(e.canonical_resource_key)} for e in c.resource_manifest]).closure_valid
"""
    checked = subprocess.run(
        [sys.executable, "-I", "-c", code, str(installed), SCF],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.parametrize("value", ["", "a" * 10000, "Étiquette / exact\nJSON", "literal-alias"])
def test_published_literal_operation_has_no_coercion_or_fallback(value: str) -> None:
    operation = resource(CATALOG)["operation"]
    assert operation["input_count"] == 1 and operation["input_type"] == "string"
    assert operation["formatting"] is False and operation["fallback"] is False
    publication.verify_label_fixture(
        ROOT,
        "adr/logical",
        {"title": "A title", "context": value},
        {"/name": "A title", "/summary": value},
    )
    with pytest.raises(publication.PublicationError, match="changed_representation"):
        publication.verify_label_fixture(
            ROOT,
            "adr/logical",
            {"title": "A title", "context": value},
            {"/name": "A title", "/summary": value + "!"},
        )


@pytest.mark.parametrize(
    "ty",
    [
        row["semantic_type"]
        for row in resource(CATALOG)["types"]
        if row["output_branch"] in {"regular", "normative-proposition"}
    ],
)
def test_type_scoped_literal_fixture_verification(ty: str) -> None:
    policy = next(row for row in matrix() if row["semantic_type"] == ty)
    authored = {policy[key].split(":")[1]: "valid-label" for key in ("name", "summary")}
    outputs = {"/" + key: authored[policy[key].split(":")[1]] for key in ("name", "summary")}
    publication.verify_label_fixture(ROOT, ty, authored, outputs)
    for destination in ("/name", "/summary"):
        changed = {**outputs, destination: "forged-output"}
        with pytest.raises(publication.PublicationError):
            publication.verify_label_fixture(ROOT, ty, authored, changed)
    for value in (None, 17, {}, [], False):
        invalid = {**authored, policy["name"].split(":")[1]: value}
        with pytest.raises(publication.PublicationError):
            publication.verify_label_fixture(ROOT, ty, invalid, outputs)
    with pytest.raises(publication.PublicationError, match="missing_label_input"):
        publication.verify_label_fixture(ROOT, ty, {}, outputs)
