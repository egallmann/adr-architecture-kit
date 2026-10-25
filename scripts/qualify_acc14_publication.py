"""ACC 1.4 authority publication qualification; never execute construction."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urldefrag, urljoin

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from scripts.generate_semantic_contract_assets import digest, discovered_dependencies
from scripts.qualify_acc13_publication import exact_closure
from scripts.qualify_ai13_publication import pointer
from scripts.qualify_ai14_publication import qualify as qualify_ai14

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "authoring-construction/1.4/"
BASE = "authoring-construction/1.3/"
AI = "architecture-interpretation/1.4/"
INHERITED_AI = "architecture-interpretation/1.3/"
CATALOG = AI + "required-output-derivations"
LEDGER = BASE + "ledger.schema"
AI_SCF = "scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7"
NM_SCF = "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7"
ACC13_SCF = "scf:v1:sha256:5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49"
NAMES = (
    "schema",
    "rules",
    "compatibility",
    "composition-bindings",
    "composition-bindings.schema",
    "conformance",
    "conformance.schema",
)


def read(root: Path, key: str) -> Any:
    """Exact canonical paths, never mutable selection or predecessor fallback."""
    if key.endswith("/contract"):
        family, version, _ = key.split("/")
        if family in {"architecture-interpretation", "authoring-construction", "normalized-model"}:
            path = f"contracts/semantic-contract/v1.0/definitions/{family}-{version}.json"
        else:
            path = f"contracts/{family}/v{version}/contract.json"
    elif key.startswith((PREFIX, BASE)):
        family, version, name = key.split("/")
        path = f"contracts/{family}/v{version}/" + (
            "schema.json" if name == "schema" else f"resources/{name}.json"
        )
    else:
        path = "contracts/semantic-contract/v1.0/resources/" + key.replace("/", "-") + ".json"
        if not (root / path).is_file() and len(key.split("/")) == 3:
            family, _, name = key.split("/")
            path = f"contracts/semantic-contract/v1.0/resources/{family}-{name}.json"
    return json.loads((root / path).read_text(encoding="utf-8"))


def qualification(root: Path, key: str, selector: str = "") -> dict[str, str]:
    value = read(root, key)
    pointer(value, selector)
    return {
        "canonical_resource_key": key,
        "content_digest": digest(value),
        "schema_pointer": selector,
    }


def ai_qualification(root: Path) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["family", "version", "semantic_contract_fingerprint", "authority_closure"],
        "properties": {
            "family": {"const": "architecture-interpretation"},
            "version": {"const": "1.4"},
            "semantic_contract_fingerprint": {"const": AI_SCF},
            "authority_closure": {"$ref": "#/$defs/exact_ai14_closure"},
        },
    }


def output_schema(root: Path) -> dict[str, Any]:
    """Evidence shape only; assertions/counts never independently prove coverage."""
    catalog = read(root, CATALOG)
    catalog_qualification = qualification(root, CATALOG)
    verified = {"enum": ["verified", "invalid", "unavailable", "not_evaluated"]}
    checks = [
        "source_and_identity",
        "applicability_and_context",
        "inputs_and_types",
        "exact_operation",
        "complete_output",
    ]
    instance_branches = []
    for row in catalog["types"]:
        destinations = []
        for output in row["outputs"]:
            if output["status"] != "QUALIFIED":
                continue
            destinations.append(
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "destination",
                        "producer_rule_id",
                        "producer_rule",
                        "verification",
                    ],
                    "properties": {
                        "destination": {"const": output["destination"]},
                        "producer_rule_id": {"const": output["producer"]["rule_id"]},
                        "producer_rule": {"const": output["producer"]["rule"]},
                        "verification": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": checks,
                            "properties": {key: verified for key in checks},
                        },
                    },
                }
            )
        instance_branches.append(
            {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "semantic_type",
                    "identity",
                    "output_branch",
                    "destinations",
                    "blocked_destinations",
                    "competing_destinations",
                    "all_applicable_accounted",
                ],
                "properties": {
                    "semantic_type": {"const": row["semantic_type"]},
                    "identity": {"$ref": "../1.3/ledger.schema.json#/$defs/identity"},
                    "output_branch": {"const": row["output_branch"]},
                    "destinations": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {"oneOf": destinations} if destinations else False,
                    },
                    "blocked_destinations": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "competing_destinations": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "all_applicable_accounted": {"type": "boolean"},
                },
            }
        )
    complete_destination = {
        "properties": {
            "verification": {"properties": {key: {"const": "verified"} for key in checks}}
        }
    }
    complete_unit = {
        "properties": {
            "all_applicable_accounted": {"const": True},
            "blocked_destinations": {"maxItems": 0},
            "competing_destinations": {"maxItems": 0},
            "destinations": {"items": complete_destination},
        }
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "architecture_interpretation",
            "catalog",
            "status",
            "units",
            "all_required_destinations_accounted",
            "representation_verification",
        ],
        "properties": {
            "architecture_interpretation": ai_qualification(root),
            "catalog": {"const": catalog_qualification},
            "status": {"enum": ["complete", "blocked", "invalid", "not_evaluated"]},
            "units": {"type": "array", "items": {"oneOf": instance_branches}},
            "all_required_destinations_accounted": {"type": "boolean"},
            "representation_verification": {
                "enum": ["valid", "invalid", "unavailable", "not_evaluated"]
            },
        },
        "allOf": [
            {
                "if": {"properties": {"status": {"const": "complete"}}, "required": ["status"]},
                "then": {
                    "properties": {
                        "all_required_destinations_accounted": {"const": True},
                        "representation_verification": {"const": "valid"},
                        "units": {"items": complete_unit},
                    }
                },
            }
        ],
    }


def schema(root: Path) -> dict[str, Any]:
    value = read(root, BASE + "schema")
    value["$id"] = "https://adr-kit.dev/semantic-contract/resources/" + PREFIX + "schema.json"
    value["title"] = "Authoring Construction Contract 1.4"
    value["semanticDependencies"] = sorted(
        set(value.get("semanticDependencies", [])) | {AI + "contract", CATALOG, LEDGER}
    )
    defs = value["$defs"]
    # Closed, enumerated selection edits, not recursive version/SCF substitution.
    defs["acc14_qualification"] = defs.pop("acc13_qualification")
    defs["acc14_qualification"]["properties"]["version"] = {"const": "1.4"}
    defs["exact_basis"]["properties"]["acc"] = {"$ref": "#/$defs/acc14_qualification"}
    defs.pop("exact_ai13_closure")
    defs["exact_ai14_closure"] = exact_closure(root, "architecture-interpretation", "1.4")
    defs["architecture_interpretation_qualification"] = ai_qualification(root)
    for name, prop in (
        ("authoring_request", "contract_version"),
        ("result_base", "contract_version"),
        ("contract_document", "semanticContractVersion"),
    ):
        defs[name]["properties"][prop] = {"const": "1.4"}
    for name in ("composition_authority",):
        props = defs[name]["properties"]
        props["architecture_interpretation"] = ai_qualification(root)
        props["acc"] = {"$ref": "#/$defs/acc14_qualification"}
    binding = defs["composition_binding_qualification"]["properties"]["canonical_resource_key"]
    binding["const"] = PREFIX + "composition-bindings"
    defs["composition_record"]["properties"]["integrity"]["properties"][
        "composition_binding_resource_key"
    ] = {"const": PREFIX + "composition-bindings"}
    cq = defs["construction_qualification"]
    cq["properties"]["authority"] = copy.deepcopy(defs["composition_authority"])
    cq["properties"]["interpretation"]["properties"]["architecture_interpretation_fingerprint"] = {
        "const": AI_SCF
    }
    for name in ("expected_ledger", "observed_ledger"):
        cq["properties"][name] = {"$ref": "../1.3/ledger.schema.json"}
    cq["properties"]["comparison"]["properties"]["algorithm"] = {
        "const": PREFIX + "complete-semantic-ledger-equality"
    }
    defs["required_output_qualification"] = output_schema(root)
    cq["required"].append("required_output")
    cq["properties"]["required_output"] = {"$ref": "#/$defs/required_output_qualification"}
    # Complete construction requires a separately verified output proof, in
    # addition to inherited complete interpretation/schema/ledger obligations.
    condition = defs["construction_result"]["allOf"][2]["then"]["properties"][
        "construction_qualification"
    ]["properties"]
    condition["required_output"] = {"properties": {"status": {"const": "complete"}}}
    return cast(dict[str, Any], value)


def resources(root: Path) -> dict[str, Any]:
    table = read(root, BASE + "composition-bindings")
    table["resource_version"] = "1.4"
    # Every inherited row qualification stays byte-equivalent: notably the AI
    # disposition/ownership family/version/SCF, keys, digests and rule_id.
    table_schema = read(root, BASE + "composition-bindings.schema")
    table_schema["$id"] = (
        "https://adr-kit.dev/semantic-contract/resources/"
        + PREFIX
        + "composition-bindings.schema.json"
    )
    table_schema["title"] = "ACC 1.4 composition binding table"
    table_schema["properties"]["resource_version"] = {"const": "1.4"}
    rules = read(root, BASE + "rules")
    rules["resource_version"] = "1.4"
    rules["compatibility"]["historical_contract"] = "authoring-construction/1.3"
    rules["compatibility"]["successor_definitions"][
        0
    ] = "exact_architecture_interpretation_authority_is_1.4"
    rules["authority"]["architecture_interpretation"].update(
        version="1.4", fingerprint=AI_SCF, closure_source=AI + "contract"
    )
    rules["authority"][
        "inherited_rule_qualification"
    ] = "enclosing_AI_1.4_and_actual_AI_1.3_rule_family_version_SCF_key_digest_and_rule_id_are_independently_verified; never_rewrite_inherited_qualifications"
    rules["ledger"]["expected_side"][
        "field_meaning_source"
    ] = "actual qualified AI 1.3 dispositions inherited through exact AI 1.4; required-output authority is separately qualified"
    rules["ledger"]["observed_side"]["source_chain"][3] = "exact Architecture Interpretation 1.4"
    rules["ledger"]["observed_side"]["source_chain"][
        5
    ] = "actual inherited AI 1.3 semantic projection qualified through AI 1.4"
    rules["equivalence"]["algorithm_id"] = PREFIX + "complete-semantic-ledger-equality"
    rules["equivalence"][
        "first_class_and_extension_duplicate"
    ] = "Rejected_unless_exact_AI_1.4_type_scoped_representation_copy_independently_verified; no_second_semantic_value_and_original_destination_retained"
    rules["equivalence"]["representation_outputs"] = {
        "authority": AI + "rules",
        "catalog": CATALOG,
        "semantic_owner": "none_for_verified_literal_string_copy",
        "expected": "retain_original_authored_values_exactly_once_at_actual_inherited_AI_destinations",
        "observed": "independently_extract_all_original_semantic_values_from_complete_NM_2.5_and_verify_derived_outputs_separately",
        "classification": "exact_type_scoped_catalog_not_equal_strings_or_property_names",
        "representation_proof_is_equality": False,
        "equality_is_representation_proof": False,
        "lost_extension_is_mismatch_even_if_label_intact": True,
        "changed_label_is_violation_even_if_extension_intact": True,
    }
    rules["required_output"] = {
        "catalog": qualification(root, CATALOG),
        "schema": qualification(root, AI + "required-output-derivations.schema"),
        "policy": copy.deepcopy(read(root, CATALOG)["coverage"]),
        "catalog_counts": {
            "semantic_types": 27,
            "qualified_producer_definitions": 186,
            "BLOCKED_destination_entries": 269,
            "literal_copy_label_rules": 26,
        },
        "definition_is_instance_proof": False,
        "BLOCKED_is_producer": False,
        "complete_materialization": "every_applicable_required_destination_has_exactly_one_independently_qualified_producer_after_schema_branch_identity_and_context_resolution",
        "independent_replay": "reconstruct_all_claimed_outputs_from_original_sealed_sources_established_identities_and_exact_rule_inputs_types_and_operation; caller_flags_digests_counts_or_replay_copies_are_not_proof",
        "schema_validation": "validate_actual_complete_NM_2.5_result_in_addition_to_coverage_representation_and_ledger_proofs",
        "missing_prerequisite": "Unavailable",
        "established_violation": "Rejected",
        "unresolved": "only_actually_established_governed_dependency",
        "partial_complete_result": False,
        "BLOCKED_register": copy.deepcopy(read(root, CATALOG)["blockers"]),
    }
    rules["qualification_evidence"]["required_for_constructed"] += [
        "all applicable AI 1.4 required-output destinations independently qualified with no BLOCKED or competing producer",
        "independent complete representation reconstruction and verification separate from whole-ledger semantic equality",
    ]
    rules["outcomes"]["Constructed"]["requires"] += [
        "complete_required_output_coverage",
        "independent_representation_verification",
        "no_BLOCKED_construction_prerequisite",
    ]
    rules["composition"]["binding_authority"] = {
        "canonical_resource_key": PREFIX + "composition-bindings",
        "content_digest": digest(table),
    }
    rules["composition"]["schema_authority"] = {
        "canonical_resource_key": PREFIX + "composition-bindings.schema",
        "content_digest": digest(table_schema),
    }
    rules["composition"]["selection_sequence"][0] = "verify_complete_exact_ACC_1.4_closure"
    rules["composition"][
        "record_qualification"
    ] = "exact enclosing ACC 1.4 / AI 1.4 closures and actual inherited AI 1.3 rule qualifications; same verified binding/ADC/Authoring/NM/CEC basis"
    rules["semanticDependencies"] = sorted(
        set(rules["semanticDependencies"])
        | {
            AI + "contract",
            AI + "rules",
            CATALOG,
            AI + "required-output-derivations.schema",
            PREFIX + "composition-bindings",
            PREFIX + "composition-bindings.schema",
            LEDGER,
        }
        | {e["canonicalResourceKey"] for e in read(root, AI + "contract")["resourceManifest"]}
    )
    compatibility = {
        "resource_kind": "authoring-construction-compatibility",
        "resource_version": "1.4",
        "semanticDependencies": sorted(
            {BASE + "contract", BASE + "compatibility", AI + "contract", CATALOG, LEDGER}
            | {e["canonicalResourceKey"] for e in read(root, BASE + "contract")["resourceManifest"]}
        ),
        "historical_definitions": [
            {
                "family": "authoring-construction",
                "version": "1.3",
                "fingerprint": ACC13_SCF,
                "resources_mutated": False,
            }
        ],
        "carry_forward": "ACC 1.3 identity, artifacts, references, composition, minimal roots, contextual lifecycle, ledger shape, independent equality, outcomes and diagnostic policy unchanged except ADR-L-0038 refinements",
        "successor_changes": [
            "exact enclosing AI 1.4 selection with actual inherited AI 1.3 rule qualifications",
            "independent required-output and representation verification",
            "verified representation copies have no second semantic ownership",
        ],
        "ledger_schema": LEDGER,
        "cross_version_evidence": "never_promote_by_version_or_fingerprint_rewriting",
        "current_selection_change": False,
        "runtime_execution": False,
        "historical_conformance": "C01-C42, ACC11, ACC12 and ACC13 remain frozen with original acceptance semantics",
    }
    cs = read(root, BASE + "conformance.schema")
    cs["$id"] = (
        "https://adr-kit.dev/semantic-contract/resources/" + PREFIX + "conformance.schema.json"
    )
    cs["title"] = "ACC 1.4 frozen authority-only conformance"
    cs["properties"]["resource_version"] = {"const": "1.4"}
    case = cs["properties"]["cases"]["items"]
    case["properties"]["case_id"]["pattern"] = "^ACC14-[0-9]{3}$"
    case["properties"]["requalified_from"]["pattern"] = "^ACC13-[0-9]{3}$"
    case["properties"]["review_class"] = {
        "enum": ["inherited", "successor_selection", "required_output_refinement", "BLOCKED"]
    }
    return {
        "schema": schema(root),
        "rules": rules,
        "compatibility": compatibility,
        "composition-bindings": table,
        "composition-bindings.schema": table_schema,
        "conformance.schema": cs,
    }


def review_case(case: dict[str, Any]) -> tuple[str, str]:
    """Review semantic obligations, not mechanical fixture/version rewriting."""
    number = int(case["case_id"].split("-")[1])
    state = case["fixture"]["input"]
    if number <= 41:
        return (
            "successor_selection" if 27 <= number <= 37 else "inherited",
            case["review"]
            + " The binding resource/enclosing selection is ACC 1.4/AI 1.4; actual disposition and ownership rows remain AI 1.3. Preservation/root/endpoint assertions are not complete construction or required-output proof.",
        )
    if state.get("category") == "root_lifecycle":
        return (
            "inherited",
            f"Preserve {state['semantic_type']} literal {state['authored_status']} under the actual AI 1.3 lifecycle rule inherited by AI 1.4. A lifecycle assertion alone does not qualify required outputs.",
        )
    if state.get("category") == "ownership_selector":
        return (
            "inherited",
            f"Preserve {state['row']['rule_id']} and literal {state['declaring_status']}; the rule row/key/digest/SCF stays AI 1.3. Enclosing interpretation is independently AI 1.4, not a fabricated AI 1.4 ownership rule.",
        )
    fault = state["fault"]
    if fault in {"exact_successor_selection", "wrong_ai_version", "wrong_ai_scf"}:
        return (
            "successor_selection",
            {
                "exact_successor_selection": "Require enclosing AI 1.4 / exact 60-resource closure and unchanged NM 2.5; inherited AI 1.3 rules are separately qualified.",
                "wrong_ai_version": "Reject AI 1.3 as enclosing interpretation even though actual inherited AI 1.3 rule authority remains required.",
                "wrong_ai_scf": "Wrong enclosing AI 1.4 SCF is Unavailable; no rule qualification or predecessor SCF substitutes.",
            }[fault],
        )
    return (
        "inherited",
        f"Retain the independently established {fault} obligation: {case['claim']} Exact enclosing AI 1.4 output coverage is an additional prerequisite, never a replacement or partial-success path.",
    )


def conformance(root: Path) -> dict[str, Any]:
    previous = read(root, BASE + "conformance")
    previous_qualification = qualification(root, BASE + "conformance")
    catalog_qualification = qualification(root, CATALOG)
    cases: list[dict[str, Any]] = []

    def add(
        claim: str, state: dict[str, Any], assertions: list[dict[str, Any]], **extra: Any
    ) -> None:
        cases.append(
            {
                "case_id": f"ACC14-{len(cases)+1:03d}",
                "claim": claim,
                "fixture": {"kind": "authority_reference", "input": state},
                "assertions": assertions,
                "runtime_coverage": "authority_only_not_implemented",
                **extra,
            }
        )

    def assertion(path: str, expected: Any) -> dict[str, Any]:
        return {"path": path, "operator": "equals", "expected": expected}

    for index, old in enumerate(previous["cases"]):
        kind, review = review_case(old)
        add(
            old["claim"] if kind != "successor_selection" else review,
            {
                "inherited_case": {**previous_qualification, "schema_pointer": f"/cases/{index}"},
                "enclosing_AI": {
                    "family": "architecture-interpretation",
                    "version": "1.4",
                    "SCF": AI_SCF,
                },
                "NM_SCF": NM_SCF,
                "selected_binding": PREFIX + "composition-bindings",
                "inherited_fixture_is_successor_request": False,
            },
            (
                [assertion("enclosing_AI.version", "1.4"), assertion("enclosing_AI.SCF", AI_SCF)]
                if index == 121
                else copy.deepcopy(old["assertions"])
            ),
            requalified_from=old["case_id"],
            review_class=kind,
            review=review,
        )
    catalog = read(root, CATALOG)
    for index, row in enumerate(catalog["types"]):
        add(
            "Account for this exact type/branch; catalog membership is not root authority or complete execution.",
            {"type_accounting": {**catalog_qualification, "schema_pointer": f"/types/{index}"}},
            [
                assertion("semantic_type", row["semantic_type"]),
                assertion("output_branch", row["output_branch"]),
                assertion("BLOCKED_is_producer", False),
            ],
            review_class="required_output_refinement",
        )
    for index, row in enumerate(catalog["types"]):
        for offset, output in enumerate(row["outputs"]):
            if output.get("producer", {}).get("kind") != "literal_string_copy":
                continue
            add(
                "Verify literal representation copy independently; retain its original authored semantic destination once.",
                {
                    "label_rule": {
                        **catalog_qualification,
                        "schema_pointer": f"/types/{index}/outputs/{offset}",
                    },
                    "mutations": [
                        "changed_output",
                        "missing_input",
                        "fallback",
                        "truncation",
                        "missing_original_semantics",
                    ],
                },
                [
                    assertion("representation_equality_substitute", False),
                    assertion("second_semantic_owner", False),
                    assertion("mutations_accepted", False),
                ],
                review_class="required_output_refinement",
            )
    for code, description in catalog["blockers"].items():
        add(
            "Missing required authority prevents complete materialization and Constructed.",
            {"code": code, "missing_authority": description, "catalog": catalog_qualification},
            [
                assertion("outcome", "Unavailable"),
                assertion("producer", False),
                assertion("complete_materialization", False),
            ],
            review_class="BLOCKED",
        )
    for fault, expected in {
        "wrong_ACC_version": "Unavailable",
        "wrong_ACC_SCF": "Unavailable",
        "wrong_enclosing_AI_version": "Unavailable",
        "wrong_enclosing_AI_SCF": "Unavailable",
        "wrong_NM_version": "Unavailable",
        "wrong_NM_SCF": "Unavailable",
        "missing_resource": "Unavailable",
        "tampered_resource": "Unavailable",
        "wrong_resource_digest": "Unavailable",
        "fabricated_AI14_ownership_rule": "Unavailable",
        "rewritten_inherited_rule_SCF": "Unavailable",
        "forged_qualification_evidence": "Rejected",
        "BLOCKED_as_producer": "Rejected",
        "competing_producers": "Rejected",
        "incomplete_coverage": "Unavailable",
        "schema_valid_default_for_blocked": "Rejected",
        "changed_derived_label": "Rejected",
        "missing_semantic_extension_with_intact_label": "Rejected",
        "duplicate_semantic_ownership": "Rejected",
        "equal_fingerprint_not_ledger_equality": "Unavailable",
        "replay_copy_not_ledger_equality": "Unavailable",
        "canonical_as_compatibility_relationship": "Rejected",
        "unqualified_custom_registry": "Unavailable",
        "unqualified_owner_local_context": "Unavailable",
        "unresolved_governed_endpoint": "Unresolved",
        "missing_execution_capability": "Unavailable",
        "mixed_rejected_unavailable_unresolved": "Rejected",
        "mixed_unavailable_unresolved": "Unavailable",
    }.items():
        add(
            "Independently qualify successor selection, representation and original semantics; retain all independent diagnostics.",
            {"fault": fault, "catalog": catalog_qualification},
            [
                assertion("outcome", expected),
                assertion("partial_complete_result", False),
                assertion("independent_diagnostics_retained", True),
            ],
        )
    for obligation, value in {
        "single_binding_count": 1,
        "complete_NM_2_5_required": True,
        "source_resource_request_permutation_changes_semantics": False,
        "actual_inherited_rule_identity_preserved": True,
        "runtime_capability_enabled": False,
        "current_selection_changed_by_publication": False,
        "historical_authority_changed": False,
        "independent_complete_expected_observed_ledgers_required": True,
        "Constructed_proven_by_publication": False,
    }.items():
        add(
            "Publication preserves exact inherited authority and complete independent qualification boundaries.",
            {"obligation": obligation},
            [assertion(obligation, value)],
        )
    return {
        "resource_kind": "authoring-construction-conformance",
        "resource_version": "1.4",
        "conformance_level": "frozen_authority",
        "semanticDependencies": sorted(
            {BASE + "conformance", AI + "contract", CATALOG, LEDGER}
            | {PREFIX + n for n in NAMES if n != "conformance"}
        ),
        "cases": cases,
    }


def qualify(root: Path = ROOT) -> dict[str, Any]:
    """Independently qualify exact authority, reviewed delta, refs and schemas."""
    from adr_kit.semantic_contract import (
        validate_semantic_resource_closure,
        verify_semantic_contract,
    )

    ai_report = qualify_ai14(root)
    for family, version, scf in (
        ("architecture-interpretation", "1.4", AI_SCF),
        ("normalized-model", "2.5", NM_SCF),
        ("authoring-construction", "1.3", ACC13_SCF),
    ):
        definition = read(root, f"{family}/{version}/contract")
        if (
            definition["semanticContractFingerprint"] != scf
            or not verify_semantic_contract(definition).success
        ):
            raise ValueError("exact_authority_fingerprint: " + family)
        bundle = [
            {
                "canonicalResourceKey": e["canonicalResourceKey"],
                "content": read(root, e["canonicalResourceKey"]),
            }
            for e in definition["resourceManifest"]
        ]
        if not validate_semantic_resource_closure(definition, bundle).closure_valid:
            raise ValueError("exact_authority_closure: " + family)
    expected = resources(root)
    expected["conformance"] = conformance(root)
    raw = {name: read(root, PREFIX + name) for name in NAMES}
    for name, value in expected.items():
        if raw[name] != value:
            raise ValueError("unqualified_publication_delta: " + name)
    if raw["composition-bindings"]["rows"] != read(root, BASE + "composition-bindings")["rows"]:
        raise ValueError("inherited_binding_qualification_changed")
    documents = [v for v in raw.values() if "$schema" in v]
    # Use verified supplied resources only for reference closure; never network.
    schemas: dict[str, Any] = {}
    entries = {PREFIX + n: v for n, v in raw.items() if "$schema" in v}
    for entry in read(root, BASE + "contract")["resourceManifest"]:
        key = entry["canonicalResourceKey"]
        value = read(root, key)
        if (
            isinstance(value, dict)
            and "$id" in value
            and (key.endswith("schema") or "/schema/" in key)
        ):
            entries[key] = value
    for key, value in entries.items():
        # Both names refer only to the exact manifest-qualified supplied bytes.
        # Canonical resource refs are not network retrieval or schema substitution.
        for uri in (
            value["$id"],
            "https://adr-kit.dev/semantic-contract/resources/" + key + ".json",
        ):
            if uri in schemas and schemas[uri] != value:
                raise ValueError("ambiguous_schema_identity: " + uri)
            schemas[uri] = value
    registry = Registry().with_resources(
        (uri, Resource.from_contents(value)) for uri, value in schemas.items()
    )

    def references(node: Any, base: str) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                target, selector = urldefrag(urljoin(base, node["$ref"]))
                if target not in schemas:
                    raise ValueError("unresolved_sealed_schema_reference: " + target)
                pointer(schemas[target], selector)
            for value in node.values():
                references(value, base)
        elif isinstance(node, list):
            for value in node:
                references(value, base)

    for value in documents:
        Draft202012Validator.check_schema(value)
        references(value, value["$id"])
    for name in ("composition-bindings", "conformance"):
        Draft202012Validator(raw[name + ".schema"], registry=registry).validate(raw[name])
    own_keys = {PREFIX + n for n in NAMES}
    for key, value in ((PREFIX + n, v) for n, v in raw.items()):
        for dep in discovered_dependencies(key, value):
            if dep == PREFIX + "contract":
                raise ValueError("self_referential_ACC_fingerprint")
            if dep not in own_keys:
                read(root, dep)
    return {
        "composition_bindings": 1,
        "inherited_cases_reviewed": 159,
        "conformance_cases": len(raw["conformance"]["cases"]),
        **ai_report,
        "runtime_execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(qualify(), indent=2))
