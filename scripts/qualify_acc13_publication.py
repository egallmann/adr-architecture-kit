"""ACC 1.3 publication qualification; no construction or interpretation execution."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from scripts.generate_semantic_contract_assets import digest
from scripts.qualify_ai13_publication import pointer, qualify_publication, registry_for

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "authoring-construction/1.3/"
AI = "architecture-interpretation/1.3/"
AI_SCF = "scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167"
NM_SCF = "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7"
ACC12_SCF = "scf:v1:sha256:8da499420e996c446cbc416dc7db9b4bbb2692ea5039f14461f668aaa48b9e0c"
CONTEXT_KEY = "context/declaring_adr_lifecycle#"
NAMES = (
    "schema",
    "rules",
    "compatibility",
    "composition-bindings",
    "composition-bindings.schema",
    "ledger.schema",
    "conformance",
    "conformance.schema",
)


def read(root: Path, path: str) -> Any:
    return json.loads((root / path).read_text(encoding="utf-8"))


def predecessor(root: Path, name: str) -> Any:
    return read(
        root,
        "contracts/authoring-construction/v1.2/"
        + ("schema.json" if name == "schema" else "resources/" + name + ".json"),
    )


def selected(root: Path, name: str) -> Any:
    return read(root, "contracts/architecture-interpretation/v1.3/resources/" + name + ".json")


def retarget(value: Any) -> Any:
    """Prospective version clauses only. ADC, Authoring and historical refs stay exact."""
    if isinstance(value, list):
        return [retarget(v) for v in value]
    if isinstance(value, dict):
        result = {retarget(k): retarget(v) for k, v in value.items()}
        if str(value.get("resource_kind", "")).startswith("authoring-construction"):
            result["resource_version"] = "1.3"
        return result
    if isinstance(value, str):
        for old, new in (
            ("authoring-construction/1.2/", PREFIX),
            ("architecture-interpretation/1.2/", AI),
            ("normalized-model/2.4/", "normalized-model/2.5/"),
            ("1.7-to-2.4", "1.7-to-2.5"),
            ("Architecture Interpretation 1.2", "Architecture Interpretation 1.3"),
            ("Normalized Model 2.4", "Normalized Model 2.5"),
            ("AI 1.2", "AI 1.3"),
            ("AI-1.2", "AI-1.3"),
            ("ACC 1.2", "ACC 1.3"),
            ("ACC_1.2", "ACC_1.3"),
            ("Authoring Construction Contract 1.2", "Authoring Construction Contract 1.3"),
            (
                "exact_architecture_interpretation_authority_is_1.2",
                "exact_architecture_interpretation_authority_is_1.3",
            ),
            ("normalized_model_2.4", "normalized_model_2.5"),
            ("ai12", "ai13"),
            ("nm24", "nm25"),
            ("acc12", "acc13"),
            (
                "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a",
                AI_SCF,
            ),
        ):
            value = value.replace(old, new)
    return value


def binding(root: Path) -> dict[str, Any]:
    table = retarget(predecessor(root, "composition-bindings"))
    table["semanticDependencies"].append(AI + "lifecycle-ownership")
    row = table["rows"][0]
    row["ai_authority"]["content_digest"] = digest(selected(root, "field-dispositions-1.7-to-2.5"))
    owners = [
        r
        for r in selected(root, "lifecycle-ownership")["rows"]
        if r["declaring_adr_semantic_type"] == row["parent_semantic_type"]
        and r["parent_semantic_type"] == row["parent_semantic_type"]
        and r["child_semantic_type"] == row["child_semantic_type"]
        and r["source_instance_pattern"] == row["parent_pointer"] + "/*"
    ]
    if len(owners) != 1:
        raise ValueError("composition ownership selector is not unique")
    row["ai_ownership_authority"] = {
        "family": "architecture-interpretation",
        "version": "1.3",
        "semantic_contract_fingerprint": AI_SCF,
        "canonical_resource_key": AI + "lifecycle-ownership",
        "content_digest": digest(selected(root, "lifecycle-ownership")),
        "rule_id": owners[0]["rule_id"],
    }
    return cast(dict[str, Any], table)


def ledger(root: Path) -> dict[str, Any]:
    """One inherited first-class value; contextual facts never replay that value."""
    value = read(root, "contracts/authoring-construction/v1.1/resources/ledger.schema.json")
    value["$id"] = (
        "https://adr-kit.dev/semantic-contract/resources/" + PREFIX + "ledger.schema.json"
    )
    value["title"] = "ACC 1.3 whole-result semantic ledger"
    value["properties"]["ledger_version"]["const"] = "authoring-construction-semantic-ledger/1.3"
    value["semanticDependencies"] = [
        AI + "contextual-facts",
        AI + "lifecycle-provenance.schema",
        AI + "lifecycle-ownership",
        "normalized-model/2.5/schema/normalized-entity.schema",
    ]
    defs = value["$defs"]
    defs["identity"]["properties"]["identity_kind"]["enum"][-1] = "ai13_semantic_tuple"
    carrier = selected(root, "lifecycle-provenance.schema")
    semantic_fields = [
        "declaring_adr_id",
        "declaring_adr_semantic_type",
        "status_semantic_field_key",
        "ownership_rule",
    ]
    context: dict[str, Any] = {
        "type": "object",
        "required": semantic_fields,
        "properties": {k: copy.deepcopy(carrier["properties"][k]) for k in semantic_fields},
        "additionalProperties": False,
    }
    context["properties"]["ownership_rule"] = {
        "type": "object",
        "required": ["rule_id"],
        "additionalProperties": False,
        "properties": {"rule_id": carrier["properties"]["ownership_rule"]["properties"]["rule_id"]},
    }
    defs["contextual_lifecycle_fact"] = context
    defs["field"]["allOf"] = [
        {
            "if": {
                "properties": {"semantic_field_key": {"const": CONTEXT_KEY}},
                "required": ["semantic_field_key"],
            },
            "then": {"properties": {"value": {"$ref": "#/$defs/contextual_lifecycle_fact"}}},
        }
    ]
    contextual = {
        "properties": {"semantic_field_key": {"const": CONTEXT_KEY}},
        "required": ["semantic_field_key"],
    }
    unit = defs["semantic_unit"]
    unit["properties"]["lifecycle_stage"] = {
        "enum": sorted(
            selected(root, "rules")["lifecycle_authority"]["authored_to_normalized"].values()
        )
    }
    canonical_identity = {
        "properties": {
            "identity_kind": {"const": "canonical_uuidv7"},
            "components": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": carrier["properties"]["declaring_adr_id"],
            },
        }
    }
    authored_status = {
        "properties": {
            "semantic_field_key": {
                "enum": [
                    t + "#/status"
                    for t in ("adr/logical", "adr/physical-system", "adr/physical-component")
                ]
            }
        },
        "required": ["semantic_field_key"],
    }
    inherited = {
        "required": ["lifecycle_stage"],
        "properties": {
            "semantic_type": {
                "enum": sorted(
                    {
                        r["child_semantic_type"]
                        for r in selected(root, "lifecycle-ownership")["rows"]
                    }
                )
            },
            "identity": canonical_identity,
            "fields": {
                "contains": contextual,
                "minContains": 1,
                "maxContains": 1,
                "not": {"contains": authored_status},
            },
        },
    }
    shared_rows = [
        r
        for r in selected(root, "lifecycle-ownership")["rows"]
        if r["shared_system_descriptor"]
        == "reuse_existing_semantic_unit_if_same_canonical_identity"
    ]
    if len(shared_rows) != 1:
        raise ValueError("shared descriptor rule must be uniquely qualified")
    shared = shared_rows[0]
    shared_context = {
        "properties": {
            "semantic_field_key": {"const": CONTEXT_KEY},
            "value": {
                "properties": {
                    "declaring_adr_semantic_type": {"const": shared["declaring_adr_semantic_type"]},
                    "status_semantic_field_key": {"const": shared["status_semantic_field_key"]},
                    "ownership_rule": {"properties": {"rule_id": {"const": shared["rule_id"]}}},
                }
            },
        },
        "required": ["semantic_field_key", "value"],
    }
    shared_value = {
        "properties": {
            "semantic_field_key": {"const": shared["status_semantic_field_key"]},
            "value": unit["properties"]["lifecycle_stage"],
        },
        "required": ["semantic_field_key", "value"],
    }
    reused = {
        "not": {"required": ["lifecycle_stage"]},
        "properties": {
            "identity": canonical_identity,
            "semantic_type": {
                "enum": [shared["declaring_adr_semantic_type"], shared["child_semantic_type"]]
            },
            "fields": {
                "allOf": [
                    {"contains": contextual, "minContains": 1, "maxContains": 1},
                    {"contains": shared_context, "minContains": 1, "maxContains": 1},
                    {"contains": shared_value, "minContains": 1, "maxContains": 1},
                ]
            },
        },
    }
    unit["allOf"] = [
        {
            "if": {"properties": {"fields": {"contains": contextual}}, "required": ["fields"]},
            "then": {"oneOf": [inherited, reused]},
        },
        {"if": {"required": ["lifecycle_stage"]}, "then": inherited},
    ]
    return cast(dict[str, Any], value)


def exact_closure(
    root: Path, family: str, version: str, fingerprint: bool = False
) -> dict[str, Any]:
    definition = read(root, f"contracts/semantic-contract/v1.0/definitions/{family}-{version}.json")
    members = [
        {"canonical_resource_key": e["canonicalResourceKey"], "content_digest": e["contentDigest"]}
        for e in definition["resourceManifest"]
    ]
    value: dict[str, Any] = {
        "type": "object",
        "required": ["family", "version", "resources"],
        "properties": {
            "family": {"const": family},
            "version": {"const": version},
            "resources": {
                "type": "array",
                "minItems": len(members),
                "maxItems": len(members),
                "uniqueItems": True,
                "items": {"enum": members},
            },
        },
        "additionalProperties": False,
    }
    if fingerprint:
        value["required"].append("semantic_contract_fingerprint")
        value["properties"]["semantic_contract_fingerprint"] = {
            "const": definition["semanticContractFingerprint"]
        }
    return value


def schema(root: Path) -> dict[str, Any]:
    value = retarget(predecessor(root, "schema"))
    old = read(root, "contracts/authoring-construction/v1.1/schema.json")["$defs"]
    defs = value["$defs"]
    defs["resource_manifest_entry"] = copy.deepcopy(old["resource_manifest_entry"])
    defs["resource_manifest_entry"]["properties"]["role"]["enum"].append(
        "normalized-model-conformance"
    )
    for name in ("acc13_qualification", "authoring_request", "contract_document", "result_base"):
        prop = {
            "contract_document": "semanticContractVersion",
            "acc13_qualification": "version",
        }.get(name, "contract_version")
        defs[name]["properties"][prop] = {"const": "1.3"}
    defs["exact_ai13_closure"] = exact_closure(root, "architecture-interpretation", "1.3")
    defs["exact_nm25_closure"] = exact_closure(root, "normalized-model", "2.5", True)
    defs["normalized_result"] = retarget(old["normalized_result"])
    ai = copy.deepcopy(defs["composition_authority"]["properties"]["architecture_interpretation"])
    ai["properties"]["version"] = {"const": "1.3"}
    defs["architecture_interpretation_qualification"] = ai
    defs["exact_basis"]["properties"]["architecture_interpretation"] = {
        "$ref": "#/$defs/architecture_interpretation_qualification"
    }
    defs["exact_basis"]["properties"]["normalized_model"] = {"$ref": "#/$defs/exact_nm25_closure"}
    defs["exact_authoring17_closure"] = {
        "type": "object",
        "required": ["family", "version", "resources"],
        "properties": {
            "family": {"const": "authoring"},
            "version": {"const": "1.7"},
            "resources": {
                "type": "array",
                "minItems": 6,
                "maxItems": 6,
                "uniqueItems": True,
                "items": {
                    "enum": [
                        {
                            "canonical_resource_key": e["canonicalResourceKey"],
                            "content_digest": e["contentDigest"],
                        }
                        for e in read(
                            root,
                            "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.3.json",
                        )["resourceManifest"]
                        if e["canonicalResourceKey"].startswith("authoring/1.7/schema/")
                    ]
                },
            },
        },
        "additionalProperties": False,
    }
    defs["exact_basis"]["properties"]["authoring"] = {"$ref": "#/$defs/exact_authoring17_closure"}
    for name in ("composition_authority",):
        defs[name]["properties"]["architecture_interpretation"] = copy.deepcopy(ai)
    cq = defs["construction_qualification"]["properties"]
    cq["authority"]["properties"]["architecture_interpretation"] = copy.deepcopy(ai)
    cq["interpretation"]["properties"]["architecture_interpretation_fingerprint"] = {
        "const": AI_SCF
    }
    for name in ("expected_ledger", "observed_ledger"):
        cq[name] = {"$ref": "ledger.schema.json"}
    cq["comparison"]["properties"]["algorithm"] = {
        "const": PREFIX + "complete-semantic-ledger-equality"
    }
    return cast(dict[str, Any], value)


def successor_resources(root: Path = ROOT) -> dict[str, Any]:
    table = binding(root)
    table_schema = retarget(predecessor(root, "composition-bindings.schema"))
    table_schema["properties"]["resource_version"] = {"const": "1.3"}
    table_schema["properties"]["semanticDependencies"] = {"const": table["semanticDependencies"]}
    row_schema = table_schema["properties"]["rows"]["items"]
    row_schema["required"].append("ai_ownership_authority")
    row_schema["properties"]["ai_ownership_authority"] = {
        "const": table["rows"][0]["ai_ownership_authority"]
    }
    rules = retarget(predecessor(root, "rules"))
    rules["authority"]["architecture_interpretation"]["version"] = "1.3"
    rules["authority"]["normalized_model"].update(version="2.5", fingerprint=NM_SCF)
    rules["normalized_result"]["contract"]["version"] = "2.5"
    rules["compatibility"]["historical_contract"] = "authoring-construction/1.2"
    rules["ledger"]["schema"] = PREFIX + "ledger.schema"
    rules["equivalence"]["algorithm_id"] = PREFIX + "complete-semantic-ledger-equality"
    rules["semanticDependencies"] = sorted(
        set(
            rules["semanticDependencies"]
            + [
                PREFIX + "ledger.schema",
                AI + "contextual-facts",
                AI + "lifecycle-ownership",
                AI + "lifecycle-provenance.schema",
            ]
            + [
                e["canonicalResourceKey"]
                for e in read(
                    root,
                    "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.3.json",
                )["resourceManifest"]
            ]
        )
    )
    rules["ledger"]["contextual_semantics"] = {
        "authority": AI + "contextual-facts",
        "semantic_field_key": CONTEXT_KEY,
        "carrier": "/metadata/ai_lifecycle_provenance",
        "carrier_schema": AI + "lifecycle-provenance.schema",
        "identity": "canonical_child_UUIDv7",
        "value_projection": selected(root, "contextual-facts")["facts"][0][
            "semantic_equality_fields"
        ],
        "inherited_first_class_value": "semantic_unit.lifecycle_stage_or_existing_qualified_authored_status_once_only",
        "authored_ADR_status": "existing_stable_authored_status_field_key_no_duplicate_lifecycle_slot",
        "context_value_contains_lifecycle": False,
        "independent_verification": "verify_owner_status_source_rule_meaning_and_complete_carrier_against_sealed_basis_and_exact_AI_closure",
        "qualification_not_semantic_value": "source_authority_and_resource_digests_independently_required_not_owner_identity_or_equivalence",
        "missing_additional_changed_or_ambiguous_context": "semantic_mismatch",
    }
    rules["ledger"]["contextual_semantics"]["shared_descriptor"] = {
        "authority": AI + "lifecycle-ownership",
        "rule": "reuse_existing_semantic_unit_if_same_canonical_identity",
        "required_proof": "independently_qualify_shared_canonical_identity_and_governed_existing_unit_type_from_sealed_sources",
        "value": "reuse_the_existing_qualified_authored_status_field_without_another_lifecycle_slot_or_unit",
        "schema_admission": "does_not_select_unit_type_or_prove_identity_coincidence",
    }
    rules["lifecycle"] = {
        "authority": AI + "lifecycle-ownership",
        "source": "exact_qualified_declaring_ADR_literal_status",
        "root_mapping": selected(root, "rules")["lifecycle_authority"]["authored_to_normalized"],
        "active_is_accepted": False,
        "default": "forbidden",
        "independent_approval_or_deployment": False,
        "standalone_representation": "native_authoring_fragment_and_minimal_root_preserved",
        "missing_qualified_lifecycle_provenance": "Unavailable",
        "synthetic_owner_or_ADR": False,
        "excluded": selected(root, "lifecycle-ownership")["rules"]["excluded"],
    }
    rules["composition"]["binding_authority"]["content_digest"] = digest(table)
    rules["composition"]["schema_authority"]["content_digest"] = digest(table_schema)
    rules["composition"][
        "declaring_lifecycle_ownership"
    ] = "selected_binding_and_independently_verified_AI_ownership_rule_and_sealed_containment_only; request_intent_is_not_proof"
    rules["ledger"]["aggregation"][
        "standalone_fragments"
    ] += "; complete interpretation requires independently qualified lifecycle facts; otherwise Unavailable"
    rules["qualification_evidence"]["required_for_constructed"].append(
        "independently qualified complete literal lifecycle, contextual facts and carrier evidence under exact AI 1.3"
    )
    rules["outcomes"]["Constructed"]["requires"].append(
        "complete_literal_lifecycle_and_contextual_semantic_accounting"
    )
    compatibility = retarget(predecessor(root, "compatibility"))
    # Historical dependency identities must not be prospectively retargeted.
    compatibility["semanticDependencies"] = predecessor(root, "compatibility")[
        "semanticDependencies"
    ] + [
        "authoring-construction/1.2/schema",
        "authoring-construction/1.2/rules",
        "authoring-construction/1.2/compatibility",
        "authoring-construction/1.2/conformance",
    ]
    compatibility["historical_definitions"] = predecessor(root, "compatibility")[
        "historical_definitions"
    ] + [
        {
            "family": "authoring-construction",
            "version": "1.2",
            "fingerprint": ACC12_SCF,
            "resources_mutated": False,
        }
    ]
    compatibility["ledger_schema"] = PREFIX + "ledger.schema"
    compatibility["carry_forward"] = [
        "ACC 1.2 orchestration, identity, composition, ordering, preservation, minimal roots, complete equality and diagnostic semantics; only ADR-L-0037 successor clauses refine authority, lifecycle and contextual coverage"
    ]
    compatibility["successor_changes"] = [
        "exact ACC 1.3/AI 1.3/NM 2.5 selection",
        "qualified literal lifecycle and contextual equality",
        "conditional complete standalone interpretation",
        "one requalified composition binding, no new containment",
    ]
    compatibility["historical_conformance"] = (
        "C01-C42, ACC11-01-26 and ACC12-01-41 unchanged; no successor runtime execution claim"
    )
    conformance_schema = retarget(predecessor(root, "conformance.schema"))
    conformance_schema["properties"]["resource_version"] = {"const": "1.3"}
    case = conformance_schema["properties"]["cases"]["items"]
    case["properties"]["case_id"]["pattern"] = "^ACC13-[0-9]{3}$"
    case["properties"]["requalified_from"] = {"type": "string", "pattern": "^ACC12-[0-9]{2}$"}
    case["properties"]["review"] = {"type": "string", "minLength": 1}
    return {
        "schema": schema(root),
        "rules": rules,
        "compatibility": compatibility,
        "composition-bindings": table,
        "composition-bindings.schema": table_schema,
        "ledger.schema": ledger(root),
        "conformance.schema": conformance_schema,
    }


def qualify(root: Path = ROOT) -> dict[str, Any]:
    from adr_kit.semantic_contract import (
        validate_semantic_resource_closure,
        verify_semantic_contract,
    )

    report = qualify_publication(root)
    expected = successor_resources(root)
    raw = {
        name: read(
            root,
            "contracts/authoring-construction/v1.3/"
            + ("schema.json" if name == "schema" else "resources/" + name + ".json"),
        )
        for name in NAMES
    }
    for name, value in expected.items():
        if raw[name] != value:
            raise ValueError("unqualified successor publication delta: " + name)
    for family, version, fingerprint in [
        ("architecture-interpretation", "1.3", AI_SCF),
        ("normalized-model", "2.5", NM_SCF),
        ("authoring-construction", "1.2", ACC12_SCF),
    ]:
        definition = read(
            root, f"contracts/semantic-contract/v1.0/definitions/{family}-{version}.json"
        )
        if definition["semanticContractFingerprint"] != fingerprint:
            raise ValueError("wrong selected fingerprint: " + family)
        bundle = [
            {
                "canonicalResourceKey": e["canonicalResourceKey"],
                "content": canonical_resource(root, e["canonicalResourceKey"]),
            }
            for e in definition["resourceManifest"]
        ]
        if (
            not verify_semantic_contract(definition).success
            or not validate_semantic_resource_closure(definition, bundle).closure_valid
        ):
            raise ValueError("unverified exact authority closure: " + family)
        # Publication consults canonical schema/catalog files. Qualify those
        # exact bytes as well as the flattened closure supplied to Rust.
        for entry in definition["resourceManifest"]:
            key = entry["canonicalResourceKey"]
            peer: Path | None = None
            if key.startswith(AI):
                peer = (
                    root
                    / "contracts/architecture-interpretation/v1.3/resources"
                    / (key.removeprefix(AI) + ".json")
                )
            elif key.startswith("authoring/1.7/schema/"):
                peer = root / "schema/authoring/v1.7" / (key.split("/")[-1] + ".json")
            elif key.startswith("normalized-model/2.5/schema/"):
                peer = root / "schema/normalized-model/v2.5" / (key.split("/")[-1] + ".json")
            elif key.startswith("authoring-construction/"):
                _, version_name, resource_name = key.split("/")
                relative = (
                    resource_name + ".json"
                    if resource_name in {"contract", "schema"}
                    else "resources/" + resource_name + ".json"
                )
                peer = root / "contracts/authoring-construction" / ("v" + version_name) / relative
            if (
                peer is not None
                and digest(json.loads(peer.read_text(encoding="utf-8"))) != entry["contentDigest"]
            ):
                raise ValueError(
                    "consulted authority bytes disagree with verified manifest: " + key
                )
    row = raw["composition-bindings"]["rows"][0]
    disposition = [
        f
        for t in selected(root, "field-dispositions-1.7-to-2.5")["semantic_types"]
        for f in t["field_dispositions"]
        if f["semantic_field_key"] == row["semantic_field_key"]
    ]
    if len(disposition) != 1 or any(
        disposition[0][k] != v for k, v in row["required_ai_disposition"].items()
    ):
        raise ValueError("AI membership disposition disagreement")
    adc = read(root, "contracts/authoring-domain/v1.1/contract.json")
    if row["adc_authority"]["content_digest"] != digest(adc):
        raise ValueError("ADC qualification disagreement")
    for role in ("parent", "child"):
        kind, name = row[role + "_semantic_type"].split("/")
        types = [t for t in adc["types"] if t["key"] == {"kind": kind, "name": name}]
        if len(types) != 1 or row["required_adc_policy"][role] != {
            k: types[0][k] for k in row["adc_policies_consulted"]
        }:
            raise ValueError("ADC policy disagreement")
        resource = row[role + "_schema"]
        source = read(
            root,
            "schema/authoring/v1.7/" + resource["canonical_resource_key"].split("/")[-1] + ".json",
        )
        if digest(source) != resource["content_digest"]:
            raise ValueError("Authoring schema qualification disagreement")
        pointer(source, resource["schema_pointer"])
    documents = [value for value in raw.values() if "$schema" in value]
    registry = registry_for(documents)
    for value in documents:
        Draft202012Validator.check_schema(value)
    for name in ("composition-bindings", "conformance"):
        Draft202012Validator(raw[name + ".schema"], registry=registry).validate(raw[name])
    cases = raw["conformance"]["cases"]
    if [c["case_id"] for c in cases] != [f"ACC13-{i:03d}" for i in range(1, len(cases) + 1)]:
        raise ValueError("nonunique or unordered successor conformance namespace")
    if [c.get("requalified_from") for c in cases[:41]] != [f"ACC12-{i:02d}" for i in range(1, 42)]:
        raise ValueError("missing individual predecessor-case review")
    return {
        "composition_bindings": 1,
        "ownership_selectors": report["ownership_selectors"],
        "enum_domain_proofs": len(report["enum_domain_proofs"]),
        "conformance_cases": len(cases),
        "runtime_execution": False,
    }


def canonical_resource(root: Path, key: str) -> Any:
    if key == AI + "contract":
        return read(
            root,
            "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.3.json",
        )
    directory = root / "contracts/semantic-contract/v1.0/resources"
    path = directory / (key.replace("/", "-") + ".json")
    if not path.is_file() and len(key.split("/")) == 3:
        family, _, name = key.split("/")
        path = directory / (family + "-" + name + ".json")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(json.dumps(qualify(), indent=2))
