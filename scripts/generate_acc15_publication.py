"""Isolated ACC 1.5 authority producer. No construction or recipe execution."""

from __future__ import annotations

import copy
import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from scripts.generate_semantic_contract_assets import (
    definition,
    digest,
    discovered_dependencies,
    write_json,
)
from scripts.qualify_acc13_publication import exact_closure
from scripts.qualify_acc14_publication import read as historical_read
from scripts.qualify_ai13_publication import pointer

ROOT = Path(__file__).resolve().parents[1]
P = "authoring-construction/1.5/"
B = "authoring-construction/1.4/"
AI = "architecture-interpretation/1.5/"
CAT = AI + "required-output-derivations"
REC = AI + "identity-representation-recipes"
LEDGER = "authoring-construction/1.3/ledger.schema"
NAMES = (
    "schema",
    "rules",
    "compatibility",
    "composition-bindings",
    "composition-bindings.schema",
    "conformance",
    "conformance.schema",
)
CHECKS = (
    "source_and_identity",
    "applicability_and_context",
    "inputs_and_types",
    "exact_operation",
    "complete_output",
)
_snapshot: ContextVar[dict[str, Any] | None] = ContextVar("acc15_producer_inputs", default=None)
_digests: ContextVar[dict[str, str] | None] = ContextVar("acc15_producer_digests", default=None)


def read(root: Path, key: str) -> Any:
    cache = _snapshot.get()
    if cache is not None and key in cache:
        return cache[key]
    if key.startswith(P) and key != P + "contract":
        name = key.removeprefix(P)
        path = (
            root
            / "contracts/authoring-construction/v1.5"
            / ("schema.json" if name == "schema" else "resources/" + name + ".json")
        )
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = historical_read(root, key)
    if cache is not None:
        cache[key] = value
    return value


def q(root: Path, key: str, selector: str = "") -> dict[str, str]:
    value = read(root, key)
    pointer(value, selector)
    hashes = _digests.get()
    if hashes is None:
        content_digest = digest(value)
    else:
        if key not in hashes:
            hashes[key] = digest(value)
        content_digest = hashes[key]
    return {
        "canonical_resource_key": key,
        "content_digest": content_digest,
        "schema_pointer": selector,
    }


def closed(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def ai_qualification(root: Path) -> dict[str, Any]:
    return closed(
        {
            "family": {"const": "architecture-interpretation"},
            "version": {"const": "1.5"},
            "semantic_contract_fingerprint": {
                "const": read(root, AI + "contract")["semanticContractFingerprint"]
            },
            "authority_closure": {"$ref": "#/$defs/exact_ai15_closure"},
        }
    )


def resolved_rule(catalog: dict[str, Any], output: dict[str, Any]) -> dict[str, str]:
    producer = output["producer"]
    rule = producer["rule"]
    if rule == {"local_rule": "literal_string_copy"}:
        # A published local rule stays qualified by its actual inherited owner.
        return copy.deepcopy(
            catalog["inherited_output_authority"]["local_rule_bindings"][producer["kind"]]
        )
    return copy.deepcopy(rule)


def output_schema(root: Path) -> dict[str, Any]:
    catalog = read(root, CAT)
    units = []
    for i, row in enumerate(catalog["types"]):
        alternatives = []
        for j, output in enumerate(row["outputs"]):
            if output["status"] != "QUALIFIED":
                continue
            alternatives.append(
                closed(
                    {
                        "destination": {"const": output["destination"]},
                        "producer_kind": {"const": output["producer"]["kind"]},
                        "producer_rule_id": {"const": output["producer"]["rule_id"]},
                        "producer_rule": {"const": resolved_rule(catalog, output)},
                        "producer_definition": {"const": q(root, CAT, f"/types/{i}/outputs/{j}")},
                        "verification": closed(
                            {
                                key: {
                                    "enum": ["verified", "invalid", "unavailable", "not_evaluated"]
                                }
                                for key in CHECKS
                            }
                        ),
                    }
                )
            )
        units.append(
            closed(
                {
                    "semantic_type": {"const": row["semantic_type"]},
                    "identity": {"$ref": "../1.3/ledger.schema.json#/$defs/identity"},
                    "output_branch": {"const": row["output_branch"]},
                    "source_schema": {"const": row["source_schema"]},
                    "destinations": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {"oneOf": alternatives} if alternatives else False,
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
                }
            )
        )
    result = closed(
        {
            "architecture_interpretation": ai_qualification(root),
            "catalog": {"const": q(root, CAT)},
            "catalog_schema": {"const": q(root, CAT + ".schema")},
            "recipe_authority": {"const": q(root, REC)},
            "recipe_schema": {"const": q(root, REC + ".schema")},
            "inherited_output_authority": {"const": catalog["inherited_output_authority"]},
            "status": {"enum": ["complete", "blocked", "invalid", "not_evaluated"]},
            "units": {"type": "array", "items": {"oneOf": units}},
            "all_required_destinations_accounted": {"type": "boolean"},
            "representation_verification": {
                "enum": ["valid", "invalid", "unavailable", "not_evaluated"]
            },
        }
    )
    result["allOf"] = [
        {
            "if": {"properties": {"status": {"const": "complete"}}, "required": ["status"]},
            "then": {
                "properties": {
                    "all_required_destinations_accounted": {"const": True},
                    "representation_verification": {"const": "valid"},
                    "units": {
                        "items": {
                            "properties": {
                                "all_applicable_accounted": {"const": True},
                                "blocked_destinations": {"maxItems": 0},
                                "competing_destinations": {"maxItems": 0},
                                "destinations": {
                                    "items": {
                                        "properties": {
                                            "verification": {
                                                "properties": {
                                                    k: {"const": "verified"} for k in CHECKS
                                                }
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    },
                }
            },
        }
    ]
    return result


def bindings(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    table = copy.deepcopy(read(root, B + "composition-bindings"))
    table["resource_version"] = "1.5"
    table["semanticDependencies"] = [
        P + "composition-bindings.schema" if k == B + "composition-bindings.schema" else k
        for k in table["semanticDependencies"]
    ]
    schema = copy.deepcopy(read(root, B + "composition-bindings.schema"))
    schema["$id"] = (
        "https://adr-kit.dev/semantic-contract/resources/" + P + "composition-bindings.schema.json"
    )
    schema["title"] = "ACC 1.5 composition binding table"
    schema["properties"]["resource_version"] = {"const": "1.5"}
    schema["properties"]["semanticDependencies"] = {
        "const": copy.deepcopy(table["semanticDependencies"])
    }
    schema["semanticDependencies"] = sorted(
        set(table["semanticDependencies"]) - {P + "composition-bindings.schema"}
    )
    return table, schema


def schema(root: Path, table: dict[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = copy.deepcopy(read(root, B + "schema"))
    value["$id"] = "https://adr-kit.dev/semantic-contract/resources/" + P + "schema.json"
    value["title"] = "Authoring Construction Contract 1.5"
    value["semanticDependencies"] = sorted(
        set(value["semanticDependencies"])
        | {
            AI + "contract",
            CAT,
            CAT + ".schema",
            REC,
            REC + ".schema",
            LEDGER,
            B + "schema",
            P + "composition-bindings",
            P + "composition-bindings.schema",
        }
        | {e["canonicalResourceKey"] for e in read(root, AI + "contract")["resourceManifest"]}
    )
    defs = value["$defs"]
    defs["acc15_qualification"] = defs.pop("acc14_qualification")
    defs["acc15_qualification"]["properties"]["version"] = {"const": "1.5"}
    defs["exact_basis"]["properties"]["acc"] = {"$ref": "#/$defs/acc15_qualification"}
    defs.pop("exact_ai14_closure")
    defs["exact_ai15_closure"] = exact_closure(root, "architecture-interpretation", "1.5")
    defs["architecture_interpretation_qualification"] = ai_qualification(root)
    for name, field in (
        ("authoring_request", "contract_version"),
        ("result_base", "contract_version"),
        ("contract_document", "semanticContractVersion"),
    ):
        defs[name]["properties"][field] = {"const": "1.5"}
    authority = defs["composition_authority"]["properties"]
    authority["architecture_interpretation"] = ai_qualification(root)
    authority["acc"] = {"$ref": "#/$defs/acc15_qualification"}
    defs["composition_binding_qualification"]["properties"]["canonical_resource_key"] = {
        "const": P + "composition-bindings"
    }
    defs["composition_binding_qualification"]["properties"]["content_digest"] = {
        "const": digest(table)
    }
    defs["composition_record"]["properties"]["integrity"]["properties"][
        "composition_binding_resource_key"
    ] = {"const": P + "composition-bindings"}
    cq = defs["construction_qualification"]["properties"]
    cq["authority"] = copy.deepcopy(defs["composition_authority"])
    cq["interpretation"]["properties"]["architecture_interpretation_fingerprint"] = {
        "const": read(root, AI + "contract")["semanticContractFingerprint"]
    }
    cq["comparison"]["properties"]["algorithm"] = {"const": P + "complete-semantic-ledger-equality"}
    defs["required_output_qualification"] = output_schema(root)
    return value


def rules(root: Path, table: dict[str, Any], companion: dict[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = copy.deepcopy(read(root, B + "rules"))
    value["resource_version"] = "1.5"
    value["compatibility"]["historical_contract"] = "authoring-construction/1.4"
    value["compatibility"]["successor_definitions"][
        0
    ] = "exact_architecture_interpretation_authority_is_1.5"
    value["authority"]["architecture_interpretation"].update(
        version="1.5",
        fingerprint=read(root, AI + "contract")["semanticContractFingerprint"],
        closure_source=AI + "contract",
    )
    value["authority"][
        "inherited_rule_qualification"
    ] = "enclosing_AI_1.5_and_actual_AI_1.3_and_AI_1.4_rule_family_version_SCF_key_digest_and_rule_id_are_independently_verified; never_rewrite_inherited_qualifications"
    value["ledger"]["expected_side"][
        "field_meaning_source"
    ] = "actual qualified AI 1.3 dispositions inherited through exact AI 1.5; required-output authority and identity representations are separately qualified"
    value["ledger"]["observed_side"]["source_chain"][3] = "exact Architecture Interpretation 1.5"
    value["ledger"]["observed_side"]["source_chain"][
        5
    ] = "actual inherited AI 1.3 semantic projection qualified through AI 1.5"
    value["equivalence"]["algorithm_id"] = P + "complete-semantic-ledger-equality"
    value["equivalence"][
        "first_class_and_extension_duplicate"
    ] = "Rejected_unless_exact_AI_1.5_type_scoped_representation_derivation_independently_verified; no_second_semantic_value_and_original_destination_retained"
    rep = value["equivalence"]["representation_outputs"]
    rep.update(
        authority=AI + "rules",
        catalog=CAT,
        semantic_owner="none_for_verified_representation_only_producers_including_inherited_labels_and_three_identity_recipes",
    )
    catalog = read(root, CAT)
    required = value["required_output"]
    required.update(
        catalog=q(root, CAT),
        schema=q(root, CAT + ".schema"),
        recipe_authority=q(root, REC),
        recipe_schema=q(root, REC + ".schema"),
        inherited_output_authority=catalog["inherited_output_authority"],
        policy=catalog["coverage"],
        BLOCKED_register=catalog["blockers"],
    )
    outputs = [e for t in catalog["types"] for e in t["outputs"]]
    required["catalog_counts"] = {
        "semantic_types": len(catalog["types"]),
        "output_branches": len(catalog["branches"]),
        "qualified_producer_definitions": sum(e["status"] == "QUALIFIED" for e in outputs),
        "BLOCKED_destination_entries": sum(e["status"] == "BLOCKED" for e in outputs),
        "literal_copy_label_rules": sum(
            e.get("producer", {}).get("kind") == "literal_string_copy" for e in outputs
        ),
        "identity_representation_definitions": sum(
            e.get("producer", {}).get("kind")
            in {r["specification"]["operation"] for r in read(root, REC)["recipes"]}
            for e in outputs
        ),
    }
    required["identity_recipe_operations"] = [
        r["specification"]["operation"] for r in read(root, REC)["recipes"]
    ]
    required["actual_rule_resolution"] = (
        "qualified_catalog_definition_and_actual_rule; local_literal_string_copy_resolves_through_AI_1.5_inherited_output_authority_to_actual_AI_1.4_not_AI_1.5"
    )
    required["instance_applicability"] = (
        "Unknown_until_independently_evaluated_from_exact_source_identity_branch_and_context"
    )
    required["schema_valid_is_instance_proof"] = False
    required["recipe_failure_policy"] = {
        "missing_ambiguous_provider_or_instance_qualification": "Unavailable",
        "valid_uuid_timestamp_beyond_selected_four_digit_year_representation": "Unavailable",
        "independently_malformed_noncanonical_or_conflicting_identity": "Rejected",
        "synthetic_alias_namespace_owner_time_or_reminted_identity": "Rejected",
        "unresolved": "only_actually_established_governed_dependency",
    }
    requirements = value["qualification_evidence"]["required_for_constructed"]
    requirements[-2] = (
        "all applicable AI 1.5 required-output destinations independently qualified with no BLOCKED or competing producer"
    )
    requirements.append(
        "each selected identity recipe independently verified against original sealed source aliases established UUID and exact qualified provider context; no asserted namespace receipt or changed digest substitutes"
    )
    value["composition"]["binding_authority"] = {
        "canonical_resource_key": P + "composition-bindings",
        "content_digest": digest(table),
    }
    value["composition"]["schema_authority"] = {
        "canonical_resource_key": P + "composition-bindings.schema",
        "content_digest": digest(companion),
    }
    value["composition"]["selection_sequence"][0] = "verify_complete_exact_ACC_1.5_closure"
    value["composition"][
        "record_qualification"
    ] = "exact enclosing ACC 1.5 / AI 1.5 closures and actual inherited AI 1.3 rule qualifications; same verified binding/ADC/Authoring/NM/CEC basis"
    value["semanticDependencies"] = sorted(
        set(value["semanticDependencies"])
        | {
            AI + "contract",
            AI + "rules",
            CAT,
            CAT + ".schema",
            REC,
            REC + ".schema",
            B + "rules",
            P + "composition-bindings",
            P + "composition-bindings.schema",
            LEDGER,
        }
        | {e["canonicalResourceKey"] for e in read(root, AI + "contract")["resourceManifest"]}
    )
    return value


def compatibility(root: Path) -> dict[str, Any]:
    predecessor = read(root, B + "contract")
    return {
        "resource_kind": "authoring-construction-compatibility",
        "resource_version": "1.5",
        "semanticDependencies": sorted(
            {B + "contract", B + "compatibility", AI + "contract", CAT, REC, LEDGER}
            | {e["canonicalResourceKey"] for e in predecessor["resourceManifest"]}
        ),
        "historical_definitions": [
            {
                "family": "authoring-construction",
                "version": "1.4",
                "fingerprint": predecessor["semanticContractFingerprint"],
                "resources_mutated": False,
            }
        ],
        "carry_forward": "all ACC 1.4 construction identity references roots composition lifecycle contextual ownership NM 2.5 ledgers equality diagnostics and outcome meaning retained",
        "successor_changes": [
            "exact enclosing AI 1.5 definition and complete resource closure",
            "three AI-owned representation recipes admitted only as qualified definitions with independently verified instance prerequisites",
            "exact producer-definition and actual governing-rule qualification",
        ],
        "ledger_schema": LEDGER,
        "cross_version_evidence": "never_promote_by_version_or_fingerprint_rewriting",
        "current_selection_change": False,
        "runtime_execution": False,
        "historical_conformance": "all historical ACC 1.0 through 1.4 authority/conformance and acceptance semantics remain immutable",
    }


def conformance(root: Path) -> dict[str, Any]:
    old = read(root, B + "conformance")["cases"]
    inherited = []
    for i, case in enumerate(old):
        state = case["fixture"]["input"]
        if state.get("code") in {"alias_ref_recipe", "uri_recipe", "created_at_encoding"}:
            review = "historical_BLOCKED_only; exact_AI_1.5_recipes_qualify_successor_definitions_not_old_receipts_or_instance_values"
        elif "label_rule" in state:
            review = "actual_AI_1.4_literal_copy_authority_preserved; enclosing_AI_1.5_selection_does_not_relabel_local_rules"
        elif "enclosing_AI" in state or case.get("review_class") == "successor_selection":
            review = "historical_enclosing_selection_preserved; independently_select_ACC_1.5_AI_1.5_and_NM_2.5_for_successor_claims"
        else:
            review = "preserve_historical_assertions_under_actual_authority; successor_output_and_instance_prerequisites_are_additional_not_substitutes"
        inherited.append(
            {
                "case_id": case["case_id"],
                "qualification": q(root, B + "conformance", f"/cases/{i}"),
                "preserved_assertions": copy.deepcopy(case["assertions"]),
                "scope": "historical_authority_only_not_executed_successor_request",
                "review": review,
            }
        )
    cases: list[dict[str, Any]] = []

    def add(category: str, claim: str, state: dict[str, Any], assertions: dict[str, Any]) -> None:
        cases.append(
            {
                "case_id": f"ACC15-{len(cases)+1:03d}",
                "category": category,
                "claim": claim,
                "fixture": {"kind": "authority_reference", "input": state},
                "assertions": [
                    {"path": k, "operator": "equals", "expected": v} for k, v in assertions.items()
                ],
                "runtime_coverage": "authority_only_not_implemented",
            }
        )

    catalog = read(root, CAT)
    for i, row in enumerate(catalog["types"]):
        add(
            "type_branch",
            "Qualify the exact source/output branch and every conditional/nested destination; type membership grants no root or instance output.",
            {
                "qualification": q(root, CAT, f"/types/{i}"),
                "semantic_type": row["semantic_type"],
                "output_branch": row["output_branch"],
            },
            {
                "root_permission_granted": False,
                "instance_applicability": "Unknown",
                "complete_branch_constraints_required": True,
            },
        )
        for j, output in enumerate(row["outputs"]):
            state = {
                "qualification": q(root, CAT, f"/types/{i}/outputs/{j}"),
                "semantic_type": row["semantic_type"],
                "output_branch": row["output_branch"],
                "destination": output["destination"],
            }
            if output["status"] == "BLOCKED":
                state.update(blocked_code=output["blocked"]["code"], applicability="Unknown")
                add(
                    "blocked_destination",
                    "A statically BLOCKED destination is not a producer; when independently applicable its missing prerequisite prevents complete materialization.",
                    state,
                    {
                        "producer": False,
                        "outcome_if_applicable": "Unavailable",
                        "instance_applicability": "Unknown",
                        "complete_materialization": False,
                    },
                )
            else:
                producer = output["producer"]
                state.update(
                    producer_kind=producer["kind"], producer_rule=resolved_rule(catalog, output)
                )
                category = (
                    "identity_recipe_definition"
                    if producer["kind"]
                    in {r["specification"]["operation"] for r in read(root, REC)["recipes"]}
                    else (
                        "literal_label_definition"
                        if producer["kind"] == "literal_string_copy"
                        else "inherited_producer_definition"
                    )
                )
                add(
                    category,
                    "The exact producer definition and actual rule are qualified; all five independent checks and original semantic preservation remain necessary for an instance.",
                    state,
                    {
                        "qualified_definition": True,
                        "instance_output_established": False,
                        "verification_checks": list(CHECKS),
                        "original_semantics_preserved_once": True,
                        "second_semantic_owner": False,
                    },
                )
        if row["output_branch"] not in {"regular", "normative-proposition"}:
            add(
                "recipe_exclusion",
                "Entity-envelope identity recipes do not create relationship envelopes, proposition-owned values or owner-local roots.",
                {
                    "qualification": q(root, CAT, f"/types/{i}"),
                    "semantic_type": row["semantic_type"],
                    "output_branch": row["output_branch"],
                },
                {"identity_entity_recipes_apply": False, "synthetic_entity_created": False},
            )
    for i, recipe in enumerate(read(root, REC)["recipes"]):
        add(
            "recipe_authority",
            "Select the actual AI 1.5 operation and complete source/identity/provider/range constraints; publication does not execute a recipe.",
            {
                "qualification": q(root, REC, f"/recipes/{i}"),
                "producer_kind": recipe["specification"]["operation"],
            },
            {"recipe_owned_by_AI": True, "runtime_enabled": False, "representation_only": True},
        )
    add(
        "selection",
        "Independently qualify the exact AI 1.5 definition and complete immutable closure; inherited resource identities are not enclosing interpretation substitutes.",
        {"qualification": q(root, AI + "contract")},
        {
            "family": "architecture-interpretation",
            "version": "1.5",
            "SCF": read(root, AI + "contract")["semanticContractFingerprint"],
            "resource_count": len(read(root, AI + "contract")["resourceManifest"]),
        },
    )
    add(
        "selection",
        "Require the actual complete schema-valid NM 2.5 result, not a local partial model or schema-valid assertion alone.",
        {"qualification": q(root, "normalized-model/2.5/contract")},
        {
            "version": "2.5",
            "SCF": read(root, "normalized-model/2.5/contract")["semanticContractFingerprint"],
            "complete_actual_model_required": True,
        },
    )
    unavailable = [
        "wrong_ACC_version",
        "wrong_ACC_SCF",
        "wrong_AI_SCF",
        "AI14_as_enclosing_AI15",
        "missing_AI_closure_member",
        "wrong_NM_authority",
        "wrong_recipe_resource_or_digest",
        "rewritten_AI13_as_AI15_rule",
        "missing_provider",
        "ambiguous_provider",
        "unrepresentable_created_at",
        "missing_source_context_evidence",
        "missing_required_destination",
        "missing_execution_capability",
        "incorrect_binding_schema_digest",
        "inconsistent_binding_manifest_edge",
        "recomputed_unauthorized_SCF",
    ]
    rejected = [
        "wrong_recipe_operation",
        "wrong_producer_identity",
        "wrong_source_selector",
        "wrong_destination_branch",
        "BLOCKED_as_QUALIFIED",
        "omitted_producer_alternative",
        "competing_producers",
        "forged_instance_applicability",
        "forged_independently_verified_result",
        "changed_authorized_representation",
        "invalid_timestamp_representation",
        "malformed_noncanonical_UUIDv7",
        "wrong_namespace_or_UUID_source",
        "missing_alias_inputs",
        "invented_identity_or_context",
        "altered_source_ownership",
        "lost_original_semantic_value",
        "partial_output_claiming_complete",
        "invalid_verification_status",
        "omitted_verification_check",
        "incomplete_expected_ledger",
        "incomplete_observed_ledger",
        "dropped_ledger_equality",
        "changed_composition_binding",
        "malformed_companion_schema",
        "representation_as_second_semantic_value",
    ]
    for fault in unavailable + rejected:
        add(
            "negative_qualification",
            "Independent authority and instance qualification must reject the fault atomically; flags, schemas, digests, replay copies and counts cannot substitute for proof.",
            {"fault": fault},
            {
                "outcome": "Unavailable" if fault in unavailable else "Rejected",
                "qualifies": False,
                "partial_success": False,
                "independent_diagnostics_retained": True,
            },
        )
    for obligation, expected in {
        "single_existing_binding_only": True,
        "actual_AI13_ownership_disposition_qualification_preserved": True,
        "complete_sealed_source_and_identity_accounting_required": True,
        "literal_lifecycle_and_declaring_context_preserved": True,
        "independent_complete_expected_and_observed_ledgers_required": True,
        "representation_verification_is_ledger_equality": False,
        "ledger_equality_is_representation_verification": False,
        "schema_validity_is_instance_proof": False,
        "resource_permutation_changes_authority": False,
        "historical_immutable_bytes_changed": False,
        "current_selection_changed_by_publication": False,
        "public_execution_capability_enabled_by_publication": False,
        "Constructed_proven_by_publication": False,
        "complete_interpretation": "Unavailable",
        "instance_applicability": "Unknown",
        "outcome_precedence": ["Rejected", "Unavailable", "Unresolved", "Constructed"],
    }.items():
        add(
            "construction_obligation",
            "Preserve complete independent construction qualification and the authority-only publication boundary.",
            {"obligation": obligation},
            {obligation: expected},
        )
    return {
        "resource_kind": "authoring-construction-conformance",
        "resource_version": "1.5",
        "conformance_level": "frozen_authority",
        "authority_only": True,
        "runtime_execution_coverage": False,
        "semanticDependencies": sorted(
            {B + "conformance", AI + "contract", CAT, REC, LEDGER, "normalized-model/2.5/contract"}
            | {P + n for n in NAMES if n != "conformance"}
        ),
        "inherited_cases": inherited,
        "cases": cases,
    }


def conformance_schema() -> dict[str, Any]:
    qualification = {
        "$ref": "../../architecture-interpretation/1.4/required-output-derivations.schema.json#/properties/field_dispositions"
    }
    assertion = {
        "$ref": "../1.4/conformance.schema.json#/properties/cases/items/properties/assertions"
    }
    fixture_input = closed(
        {
            "qualification": qualification,
            "semantic_type": {"type": "string"},
            "output_branch": {"type": "string"},
            "destination": {"type": "string"},
            "producer_kind": {"type": "string"},
            "producer_rule": qualification,
            "blocked_code": {"type": "string"},
            "applicability": {"const": "Unknown"},
            "fault": {"type": "string"},
            "obligation": {"type": "string"},
        }
    )
    fixture_input.pop("required")
    case = closed(
        {
            "case_id": {"type": "string", "pattern": "^ACC15-[0-9]{3}$"},
            "category": {
                "enum": [
                    "type_branch",
                    "blocked_destination",
                    "identity_recipe_definition",
                    "literal_label_definition",
                    "inherited_producer_definition",
                    "recipe_exclusion",
                    "recipe_authority",
                    "selection",
                    "negative_qualification",
                    "construction_obligation",
                ]
            },
            "claim": {"type": "string", "minLength": 1},
            "fixture": closed({"kind": {"const": "authority_reference"}, "input": fixture_input}),
            "assertions": assertion,
            "runtime_coverage": {"const": "authority_only_not_implemented"},
        }
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://adr-kit.dev/semantic-contract/resources/" + P + "conformance.schema.json",
        "semanticDependencies": sorted(
            [
                B + "conformance.schema",
                "architecture-interpretation/1.4/required-output-derivations.schema",
            ]
        ),
        **closed(
            {
                "resource_kind": {"const": "authoring-construction-conformance"},
                "resource_version": {"const": "1.5"},
                "conformance_level": {"const": "frozen_authority"},
                "authority_only": {"const": True},
                "runtime_execution_coverage": {"const": False},
                "semanticDependencies": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1},
                },
                "inherited_cases": {
                    "type": "array",
                    "minItems": 1,
                    "items": closed(
                        {
                            "case_id": {"type": "string", "pattern": "^ACC14-[0-9]{3}$"},
                            "qualification": qualification,
                            "preserved_assertions": assertion,
                            "scope": {
                                "const": "historical_authority_only_not_executed_successor_request"
                            },
                            "review": {"type": "string", "minLength": 1},
                        }
                    ),
                },
                "cases": {"type": "array", "minItems": 1, "items": case},
            }
        ),
    }


def publish(root: Path = ROOT) -> None:
    snapshot_token, digest_token = _snapshot.set({}), _digests.set({})
    try:
        _publish(root)
    finally:
        _snapshot.reset(snapshot_token)
        _digests.reset(digest_token)


def _publish(root: Path) -> None:
    from scripts.qualify_acc15_publication import qualify

    source = root / "contracts/authoring-construction/v1.5"
    table, companion = bindings(root)
    values = {
        P + "composition-bindings": table,
        P + "composition-bindings.schema": companion,
        P + "schema": schema(root, table),
        P + "rules": rules(root, table, companion),
        P + "compatibility": compatibility(root),
        P + "conformance": conformance(root),
        P + "conformance.schema": conformance_schema(),
    }
    for key, value in values.items():
        name = key.removeprefix(P)
        write_json(
            source / ("schema.json" if name == "schema" else "resources/" + name + ".json"), value
        )
    qualify(root, published=False)
    contents: dict[str, Any] = {}
    pending = set(values)
    while pending:
        key = min(pending)
        pending.remove(key)
        contents[key] = values[key] if key in values else read(root, key)
        pending.update(discovered_dependencies(key, contents[key]) - contents.keys())
    roles = {B + "contract": "normative-definition", AI + "contract": "normative-definition"}
    for authority in (B + "contract", AI + "contract"):
        for m in read(root, authority)["resourceManifest"]:
            if m["canonicalResourceKey"] in roles and roles[m["canonicalResourceKey"]] != m["role"]:
                raise ValueError("conflicting_inherited_manifest_role")
            roles[m["canonicalResourceKey"]] = m["role"]
    manifest = []
    for key in sorted(contents):
        name = key.removeprefix(P)
        role = (
            (
                "interpretation-conformance"
                if name == "conformance"
                else (
                    "source-contract-schema"
                    if name == "schema" or name.endswith(".schema")
                    else (
                        "normative-definition" if name == "compatibility" else "interpretation-rule"
                    )
                )
            )
            if key in values
            else roles[key]
        )
        manifest.append(
            {
                "canonicalResourceKey": key,
                "contentDigest": digest(contents[key]),
                "role": role,
                "dependencies": [
                    {"canonicalResourceKey": dep, "contentDigest": digest(contents[dep])}
                    for dep in sorted(discovered_dependencies(key, contents[key]))
                ],
            }
        )
    result = definition("authoring-construction", manifest, [P + "conformance"], version="1.5")
    from adr_kit.semantic_contract import (
        verify_semantic_contract,
        validate_semantic_resource_closure,
    )

    if (
        not verify_semantic_contract(result).success
        or not validate_semantic_resource_closure(
            result, [{"canonicalResourceKey": k, "content": v} for k, v in contents.items()]
        ).closure_valid
    ):
        raise ValueError("ACC_1_5_closure_failed_before_distribution")
    for name in NAMES:
        data = (
            source / ("schema.json" if name == "schema" else "resources/" + name + ".json")
        ).read_bytes()
        for folder in (
            "contracts/semantic-contract/v1.0/resources",
            "src/adr_kit/semantic_contract/v1_0/resources",
        ):
            (root / folder / ("authoring-construction-1.5-" + name + ".json")).write_bytes(data)
    for path in (
        source / "contract.json",
        root / "contracts/semantic-contract/v1.0/definitions/authoring-construction-1.5.json",
        root / "src/adr_kit/semantic_contract/v1_0/definitions/authoring-construction-1.5.json",
        root / "src/adr_kit/semantic_contract/v1_0/authoring-construction-1.5.json",
    ):
        write_json(path, result)
    print(
        json.dumps(
            {
                "SCF": result["semanticContractFingerprint"],
                "resources": len(manifest),
                **qualify(root),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    publish()
