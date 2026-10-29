"""Independent ACC 1.5 publication audit, never construction/materialization.

No successor producer builders are imported. Exact frozen authorities establish
the inherited meaning; every permitted successor edit is separately checked.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from contextvars import ContextVar
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import UnknownDialect

from scripts.generate_semantic_contract_assets import (
    digest,
    discovered_dependencies,
    relative_resource_key,
)
from scripts.qualify_acc14_publication import read as historical_read
from scripts.qualify_ai13_publication import PublicationError, pointer
from scripts.qualify_ai15_publication import qualify as qualify_ai15
from scripts.candidate_contract_assets import canonical_resource

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "authoring-construction/1.5/"
BASE = "authoring-construction/1.4/"
AI = "architecture-interpretation/1.5/"
CATALOG = AI + "required-output-derivations"
RECIPES = AI + "identity-representation-recipes"
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
ACC14_SCF = "scf:v1:sha256:19e267c5c77477a594414168bde9f733b1b9e547c06fc6836ad09392a248ea6d"
NM_SCF = "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7"
_snapshot: ContextVar[dict[str, Any] | None] = ContextVar("acc15_snapshot", default=None)
_digests: ContextVar[dict[str, str] | None] = ContextVar("acc15_snapshot_digests", default=None)


def selected_ai_fingerprint(root: Path = ROOT) -> str:
    """Expected current source selection; qualification below establishes trust."""
    return str(canonical_resource(root, AI + "contract")["semanticContractFingerprint"])


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PublicationError(code)


def read(root: Path, key: str) -> Any:
    cache = _snapshot.get()
    if cache is not None and key in cache:
        return cache[key]
    if key.startswith(PREFIX) and key != PREFIX + "contract":
        name = key.removeprefix(PREFIX)
        value = json.loads(
            (
                root
                / "contracts/authoring-construction/v1.5"
                / ("schema.json" if name == "schema" else "resources/" + name + ".json")
            ).read_text(encoding="utf-8")
        )
    else:
        value = historical_read(root, key)
    if cache is not None:
        cache[key] = value
    return value


def qualification(root: Path, key: str, selector: str = "") -> dict[str, str]:
    content = read(root, key)
    pointer(content, selector)
    hashes = _digests.get()
    if hashes is None:
        content_digest = digest(content)
    else:
        if key not in hashes:
            hashes[key] = digest(content)
        content_digest = hashes[key]
    return {
        "canonical_resource_key": key,
        "content_digest": content_digest,
        "schema_pointer": selector,
    }


def same_except(new: dict[str, Any], old: dict[str, Any], *keys: str) -> None:
    require(new.keys() == old.keys(), "undeclared_schema_or_policy_field")
    require(
        {k: v for k, v in new.items() if k not in keys}
        == {k: v for k, v in old.items() if k not in keys},
        "inherited_semantics_changed",
    )


def qualified_history(root: Path) -> dict[str, Any]:
    # The unchanged AI 1.5 independent audit proves the actual 54-transition
    # delta and source/branch/recipe semantics, not just aggregate totals.
    report = qualify_ai15(root)
    require(
        read(root, AI + "contract") == canonical_resource(root, AI + "contract"),
        "inconsistent_current_AI_definition",
    )
    from adr_kit.semantic_contract import (
        verify_semantic_contract,
        validate_semantic_resource_closure,
    )

    pins = (
        (AI + "contract", selected_ai_fingerprint(root)),
        (BASE + "contract", ACC14_SCF),
        ("normalized-model/2.5/contract", NM_SCF),
        (
            "architecture-interpretation/1.4/contract",
            "scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7",
        ),
        (
            "architecture-interpretation/1.3/contract",
            "scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167",
        ),
        (
            "authoring-construction/1.3/contract",
            "scf:v1:sha256:5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49",
        ),
    )
    for key, expected in pins:
        contract = read(root, key)
        require(
            contract["semanticContractFingerprint"] == expected
            and verify_semantic_contract(contract).success is True,
            "unqualified_exact_authority_fingerprint",
        )
        bundle = [
            {
                "canonicalResourceKey": e["canonicalResourceKey"],
                "content": read(root, e["canonicalResourceKey"]),
            }
            for e in contract["resourceManifest"]
        ]
        require(
            validate_semantic_resource_closure(contract, bundle).closure_valid is True,
            "unqualified_historical_resource_closure",
        )
    return report


def ai_schema(root: Path, value: dict[str, Any]) -> None:
    old = read(root, BASE + "schema")["$defs"]["architecture_interpretation_qualification"]
    same_except(value, old, "properties")
    props = value["properties"]
    same_except(
        props, old["properties"], "version", "semantic_contract_fingerprint", "authority_closure"
    )
    require(
        props["version"] == {"const": "1.5"}
        and props["semantic_contract_fingerprint"] == {"const": selected_ai_fingerprint(root)}
        and props["authority_closure"] == {"$ref": "#/$defs/exact_ai15_closure"},
        "wrong_enclosing_AI_selection",
    )


def resolved_authority(
    root: Path, catalog: dict[str, Any], entry: dict[str, Any]
) -> dict[str, str]:
    rule = entry["producer"]["rule"]
    if rule == {"local_rule": "literal_string_copy"}:
        require(entry["producer"]["kind"] == "literal_string_copy", "unknown_local_producer_rule")
        rule = catalog["inherited_output_authority"]["local_rule_bindings"]["literal_string_copy"]
        require(
            rule["canonical_resource_key"]
            == "architecture-interpretation/1.4/required-output-derivations",
            "inherited_label_rule_relabelled",
        )
    require(
        rule == qualification(root, rule["canonical_resource_key"], rule["schema_pointer"]),
        "unqualified_actual_producer_rule",
    )
    return cast(dict[str, str], rule)


def qualify_output_schema(root: Path, value: dict[str, Any]) -> dict[str, int]:
    catalog = read(root, CATALOG)
    require(
        set(value) == {"type", "additionalProperties", "required", "properties", "allOf"}
        and value["type"] == "object"
        and value["additionalProperties"] is False,
        "open_required_output_evidence",
    )
    props = value["properties"]
    expected_keys = {
        "architecture_interpretation",
        "catalog",
        "catalog_schema",
        "recipe_authority",
        "recipe_schema",
        "inherited_output_authority",
        "status",
        "units",
        "all_required_destinations_accounted",
        "representation_verification",
    }
    require(
        set(props) == expected_keys
        and set(value["required"]) == expected_keys
        and len(value["required"]) == len(expected_keys),
        "missing_output_authority_qualification",
    )
    ai_schema(root, props["architecture_interpretation"])
    for prop, key in (
        ("catalog", CATALOG),
        ("catalog_schema", CATALOG + ".schema"),
        ("recipe_authority", RECIPES),
        ("recipe_schema", RECIPES + ".schema"),
    ):
        require(
            props[prop] == {"const": qualification(root, key)},
            "wrong_output_catalog_or_recipe_authority",
        )
    require(
        props["inherited_output_authority"] == {"const": catalog["inherited_output_authority"]},
        "missing_actual_inherited_output_authority",
    )
    previous = read(root, BASE + "schema")["$defs"]["required_output_qualification"]
    for key in ("status", "all_required_destinations_accounted", "representation_verification"):
        require(props[key] == previous["properties"][key], "weakened_output_completion_status")
    require(value["allOf"] == previous["allOf"], "weakened_independent_complete_output_checks")
    require(
        set(props["units"]) == {"type", "items"}
        and props["units"]["type"] == "array"
        and set(props["units"]["items"]) == {"oneOf"},
        "invalid_unit_branch_schema",
    )
    units = props["units"]["items"]["oneOf"]
    require(len(units) == len(catalog["types"]), "missing_or_competing_unit_branch")
    indexed = {u["properties"]["semantic_type"]["const"]: u for u in units}
    require(
        len(indexed) == len(units)
        and set(indexed) == {t["semantic_type"] for t in catalog["types"]},
        "wrong_unit_semantic_type",
    )
    count: Counter[str] = Counter()
    old_units = {
        u["properties"]["semantic_type"]["const"]: u
        for u in previous["properties"]["units"]["items"]["oneOf"]
    }
    for i, row in enumerate(catalog["types"]):
        unit = indexed[row["semantic_type"]]
        up = unit["properties"]
        old = old_units[row["semantic_type"]]
        require(
            set(unit) == set(old)
            and unit["type"] == "object"
            and unit["additionalProperties"] is False,
            "open_unit_evidence",
        )
        require(
            set(up) == set(old["properties"]) | {"source_schema"}
            and set(unit["required"]) == set(up)
            and len(unit["required"]) == len(up),
            "missing_unit_source_qualification",
        )
        for key in old["properties"].keys() - {"destinations"}:
            require(up[key] == old["properties"][key], "changed_unit_identity_branch_or_accounting")
        require(
            up["source_schema"] == {"const": row["source_schema"]}, "wrong_source_schema_selector"
        )
        expected = {
            e["destination"]: (j, e)
            for j, e in enumerate(row["outputs"])
            if e["status"] == "QUALIFIED"
        }
        destinations = up["destinations"]
        require(
            set(destinations) == {"type", "uniqueItems", "items"}
            and destinations["type"] == "array"
            and destinations["uniqueItems"] is True,
            "missing_duplicate_destination_guard",
        )
        if not expected:
            require(destinations["items"] is False, "invented_nonselected_output_producer")
            continue
        require(set(destinations["items"]) == {"oneOf"}, "invalid_producer_alternatives")
        alternatives = destinations["items"]["oneOf"]
        actual = {a["properties"]["destination"]["const"]: a for a in alternatives}
        require(
            len(actual) == len(alternatives) and set(actual) == set(expected),
            "missing_or_competing_producer_alternative",
        )
        for destination, (j, entry) in expected.items():
            alt = actual[destination]
            require(
                set(alt) == {"type", "additionalProperties", "required", "properties"}
                and alt["type"] == "object"
                and alt["additionalProperties"] is False,
                "open_producer_evidence",
            )
            ap = alt["properties"]
            fields = {
                "destination",
                "producer_kind",
                "producer_rule_id",
                "producer_rule",
                "producer_definition",
                "verification",
            }
            require(
                set(ap) == fields
                and set(alt["required"]) == fields
                and len(alt["required"]) == len(fields),
                "missing_actual_producer_definition_or_rule",
            )
            for field, expected_value in {
                "destination": destination,
                "producer_kind": entry["producer"]["kind"],
                "producer_rule_id": entry["producer"]["rule_id"],
                "producer_rule": resolved_authority(root, catalog, entry),
                "producer_definition": qualification(root, CATALOG, f"/types/{i}/outputs/{j}"),
            }.items():
                require(
                    ap[field] == {"const": expected_value},
                    "unqualified_producer_source_destination_kind_or_rule",
                )
            checks = ap["verification"]
            require(
                set(checks) == {"type", "additionalProperties", "required", "properties"}
                and checks["type"] == "object"
                and checks["additionalProperties"] is False
                and set(checks["required"]) == set(CHECKS)
                and len(checks["required"]) == len(CHECKS),
                "missing_independent_verification_check",
            )
            require(
                checks["properties"]
                == {
                    k: {"enum": ["verified", "invalid", "unavailable", "not_evaluated"]}
                    for k in CHECKS
                },
                "invalid_verification_states_or_boolean_shortcut",
            )
            count[entry["producer"]["kind"]] += 1
    return dict(count)


def qualify_schema(root: Path, raw: dict[str, Any]) -> dict[str, int]:
    new = raw["schema"]
    old = read(root, BASE + "schema")
    same_except(new, old, "$id", "title", "$defs", "semanticDependencies")
    require(
        new["$id"] == "https://adr-kit.dev/semantic-contract/resources/" + PREFIX + "schema.json"
        and new["title"] == "Authoring Construction Contract 1.5",
        "wrong_successor_schema_identity",
    )
    defs, previous = new["$defs"], old["$defs"]
    removed = {"acc14_qualification", "exact_ai14_closure"}
    require(
        set(defs) == (set(previous) - removed) | {"acc15_qualification", "exact_ai15_closure"},
        "undeclared_schema_definition_change",
    )
    changed = {
        "architecture_interpretation_qualification",
        "exact_basis",
        "authoring_request",
        "result_base",
        "contract_document",
        "composition_binding_qualification",
        "composition_authority",
        "composition_record",
        "construction_qualification",
        "required_output_qualification",
    }
    for key in set(previous) - removed - changed:
        require(defs[key] == previous[key], "historical_schema_obligation_changed_" + key)
    ai_schema(root, defs["architecture_interpretation_qualification"])
    for key, prior, field, value in (
        ("acc15_qualification", "acc14_qualification", "version", {"const": "1.5"}),
        ("exact_basis", "exact_basis", "acc", {"$ref": "#/$defs/acc15_qualification"}),
        ("authoring_request", "authoring_request", "contract_version", {"const": "1.5"}),
        ("result_base", "result_base", "contract_version", {"const": "1.5"}),
        ("contract_document", "contract_document", "semanticContractVersion", {"const": "1.5"}),
    ):
        same_except(defs[key], previous[prior], "properties")
        same_except(defs[key]["properties"], previous[prior]["properties"], field)
        require(defs[key]["properties"][field] == value, "wrong_ACC_request_or_result_selection")
    closure = defs["exact_ai15_closure"]
    base_closure = previous["exact_ai14_closure"]
    same_except(closure, base_closure, "properties")
    cp = closure["properties"]
    same_except(cp, base_closure["properties"], "version", "resources")
    require(cp["version"] == {"const": "1.5"}, "wrong_AI_closure_version")
    members = [
        {"canonical_resource_key": e["canonicalResourceKey"], "content_digest": e["contentDigest"]}
        for e in read(root, AI + "contract")["resourceManifest"]
    ]
    require(
        cp["resources"]
        == {
            "type": "array",
            "minItems": len(members),
            "maxItems": len(members),
            "uniqueItems": True,
            "items": {"enum": members},
        },
        "incomplete_exact_AI_1_5_schema_closure",
    )
    authority = defs["composition_authority"]
    same_except(authority, previous["composition_authority"], "properties")
    same_except(
        authority["properties"],
        previous["composition_authority"]["properties"],
        "architecture_interpretation",
        "acc",
    )
    require(
        authority["properties"]["architecture_interpretation"]
        == defs["architecture_interpretation_qualification"]
        and authority["properties"]["acc"] == {"$ref": "#/$defs/acc15_qualification"},
        "wrong_composition_enclosing_authority",
    )
    binding = defs["composition_binding_qualification"]
    same_except(binding, previous["composition_binding_qualification"], "properties")
    same_except(
        binding["properties"],
        previous["composition_binding_qualification"]["properties"],
        "canonical_resource_key",
        "content_digest",
    )
    require(
        binding["properties"]["canonical_resource_key"]
        == {"const": PREFIX + "composition-bindings"}
        and binding["properties"]["content_digest"]
        == {"const": digest(raw["composition-bindings"])},
        "wrong_exact_binding_qualification",
    )
    old_record = copy.deepcopy(previous["composition_record"])
    old_record["properties"]["integrity"]["properties"]["composition_binding_resource_key"] = {
        "const": PREFIX + "composition-bindings"
    }
    require(
        defs["composition_record"] == old_record,
        "composition_meaning_or_preservation_proof_changed",
    )
    cq = defs["construction_qualification"]
    same_except(cq, previous["construction_qualification"], "properties")
    cqprops = cq["properties"]
    prior = previous["construction_qualification"]["properties"]
    same_except(cqprops, prior, "authority", "interpretation", "comparison")
    require(cqprops["authority"] == authority, "construction_authority_inconsistent")
    for name, field, expected in (
        (
            "interpretation",
            "architecture_interpretation_fingerprint",
            selected_ai_fingerprint(root),
        ),
        ("comparison", "algorithm", PREFIX + "complete-semantic-ledger-equality"),
    ):
        same_except(cqprops[name], prior[name], "properties")
        same_except(cqprops[name]["properties"], prior[name]["properties"], field)
        require(
            cqprops[name]["properties"][field] == {"const": expected},
            "weakened_interpretation_or_ledger_qualification",
        )
    # Other construction_result / normalized_result / ledger definitions were
    # compared unchanged above, including all independent Constructed gates.
    return qualify_output_schema(root, defs["required_output_qualification"])


def qualify_binding(
    root: Path, raw: dict[str, Any], manifest: list[dict[str, Any]] | None = None
) -> None:
    table, companion = raw["composition-bindings"], raw["composition-bindings.schema"]
    old = read(root, BASE + "composition-bindings")
    same_except(table, old, "resource_version", "semanticDependencies")
    require(
        table["resource_version"] == "1.5" and len(table["rows"]) == 1,
        "invalid_binding_table_version_or_cardinality",
    )
    expected_deps = [
        PREFIX + "composition-bindings.schema" if k == BASE + "composition-bindings.schema" else k
        for k in old["semanticDependencies"]
    ]
    require(table["semanticDependencies"] == expected_deps, "composition_schema_dependency")
    key = PREFIX + "composition-bindings.schema"
    prior = read(root, BASE + "composition-bindings.schema")
    require(
        set(companion) == set(prior) | {"semanticDependencies"},
        "unqualified_companion_schema_fields",
    )
    compare = {k: v for k, v in companion.items() if k != "semanticDependencies"}
    same_except(compare, prior, "$id", "title", "properties")
    require(
        companion["$id"] == "https://adr-kit.dev/semantic-contract/resources/" + key + ".json"
        and companion["title"] == "ACC 1.5 composition binding table",
        "wrong_companion_schema_identity",
    )
    same_except(
        companion["properties"], prior["properties"], "resource_version", "semanticDependencies"
    )
    require(
        companion["properties"]["resource_version"] == {"const": "1.5"}
        and companion["properties"]["semanticDependencies"] == {"const": expected_deps},
        "composition_schema_version_or_closed_dependencies",
    )
    require(
        companion["semanticDependencies"] == sorted(set(expected_deps) - {key}),
        "missing_companion_inherited_authority_dependencies",
    )
    require(
        raw["rules"]["composition"]["schema_authority"]
        == {"canonical_resource_key": key, "content_digest": digest(companion)},
        "composition_schema_authority_digest",
    )
    require(
        raw["rules"]["composition"]["binding_authority"]
        == {
            "canonical_resource_key": PREFIX + "composition-bindings",
            "content_digest": digest(table),
        },
        "composition_table_authority_digest",
    )
    # The row itself was compared to immutable ACC 1.4 in same_except. Its
    # actual AI 1.3, ADC and Authoring qualifiers are independently dereferenced.
    row = table["rows"][0]
    for name in (
        "ai_authority",
        "adc_authority",
        "parent_schema",
        "child_schema",
        "ai_ownership_authority",
    ):
        ref = row[name]
        value = read(root, ref["canonical_resource_key"])
        require(ref["content_digest"] == digest(value), "inherited_binding_resource_digest")
        if "schema_pointer" in ref:
            pointer(value, ref["schema_pointer"])
    ownership = row["ai_ownership_authority"]
    require(
        ownership["family"] == "architecture-interpretation"
        and ownership["version"] == "1.3"
        and ownership["semantic_contract_fingerprint"]
        == read(root, "architecture-interpretation/1.3/contract")["semanticContractFingerprint"],
        "fabricated_successor_ownership_rule",
    )
    if manifest is not None:
        matching = [
            m for m in manifest if m["canonicalResourceKey"] == PREFIX + "composition-bindings"
        ]
        require(len(matching) == 1, "missing_binding_manifest_member")
        schema_edges = [
            d
            for d in matching[0]["dependencies"]
            if d["canonicalResourceKey"].startswith("authoring-construction/")
            and d["canonicalResourceKey"].endswith("/composition-bindings.schema")
        ]
        require(
            schema_edges == [{"canonicalResourceKey": key, "contentDigest": digest(companion)}],
            "composition_schema_manifest_edge",
        )


def qualify_rules(root: Path, raw: dict[str, Any]) -> None:
    value, old = raw["rules"], read(root, BASE + "rules")
    changed = (
        "resource_version",
        "compatibility",
        "authority",
        "ledger",
        "equivalence",
        "required_output",
        "qualification_evidence",
        "composition",
        "semanticDependencies",
    )
    same_except(value, old, *changed)
    require(value["resource_version"] == "1.5", "wrong_rules_version")
    same_except(
        value["compatibility"], old["compatibility"], "historical_contract", "successor_definitions"
    )
    require(
        value["compatibility"]["historical_contract"] == "authoring-construction/1.4"
        and value["compatibility"]["successor_definitions"]
        == [
            "exact_architecture_interpretation_authority_is_1.5",
            *old["compatibility"]["successor_definitions"][1:],
        ],
        "wrong_successor_compatibility_scope",
    )
    a, previous = value["authority"], old["authority"]
    same_except(a, previous, "architecture_interpretation", "inherited_rule_qualification")
    ai = a["architecture_interpretation"]
    same_except(
        ai, previous["architecture_interpretation"], "version", "fingerprint", "closure_source"
    )
    require(
        ai["version"] == "1.5"
        and ai["fingerprint"] == selected_ai_fingerprint(root)
        and ai["closure_source"] == AI + "contract",
        "wrong_exact_enclosing_AI_authority",
    )
    require(
        a["inherited_rule_qualification"]
        == "enclosing_AI_1.5_and_actual_AI_1.3_and_AI_1.4_rule_family_version_SCF_key_digest_and_rule_id_are_independently_verified; never_rewrite_inherited_qualifications",
        "inherited_rule_qualification_weakened",
    )
    ledger = copy.deepcopy(old["ledger"])
    ledger["expected_side"][
        "field_meaning_source"
    ] = "actual qualified AI 1.3 dispositions inherited through exact AI 1.5; required-output authority and identity representations are separately qualified"
    ledger["observed_side"]["source_chain"][3] = "exact Architecture Interpretation 1.5"
    ledger["observed_side"]["source_chain"][
        5
    ] = "actual inherited AI 1.3 semantic projection qualified through AI 1.5"
    require(value["ledger"] == ledger, "independent_ledger_semantics_weakened")
    eq = value["equivalence"]
    same_except(
        eq,
        old["equivalence"],
        "algorithm_id",
        "first_class_and_extension_duplicate",
        "representation_outputs",
    )
    require(
        eq["algorithm_id"] == PREFIX + "complete-semantic-ledger-equality"
        and eq["first_class_and_extension_duplicate"]
        == "Rejected_unless_exact_AI_1.5_type_scoped_representation_derivation_independently_verified; no_second_semantic_value_and_original_destination_retained",
        "semantic_ownership_or_equality_weakened",
    )
    rep = eq["representation_outputs"]
    same_except(
        rep, old["equivalence"]["representation_outputs"], "authority", "catalog", "semantic_owner"
    )
    require(
        rep["authority"] == AI + "rules"
        and rep["catalog"] == CATALOG
        and rep["semantic_owner"]
        == "none_for_verified_representation_only_producers_including_inherited_labels_and_three_identity_recipes",
        "representation_semantic_owner_invented",
    )
    catalog = read(root, CATALOG)
    outputs = [e for t in catalog["types"] for e in t["outputs"]]
    kinds = [r["specification"]["operation"] for r in read(root, RECIPES)["recipes"]]
    counts = {
        "semantic_types": len(catalog["types"]),
        "output_branches": len(catalog["branches"]),
        "qualified_producer_definitions": sum(e["status"] == "QUALIFIED" for e in outputs),
        "BLOCKED_destination_entries": sum(e["status"] == "BLOCKED" for e in outputs),
        "literal_copy_label_rules": sum(
            e.get("producer", {}).get("kind") == "literal_string_copy" for e in outputs
        ),
        "identity_representation_definitions": sum(
            e.get("producer", {}).get("kind") in kinds for e in outputs
        ),
    }
    required, prior = value["required_output"], old["required_output"]
    additions = {
        "recipe_authority",
        "recipe_schema",
        "inherited_output_authority",
        "identity_recipe_operations",
        "actual_rule_resolution",
        "instance_applicability",
        "schema_valid_is_instance_proof",
        "recipe_failure_policy",
    }
    require(set(required) == set(prior) | additions, "undeclared_required_output_policy")
    for key in set(prior) - {"catalog", "schema", "policy", "catalog_counts", "BLOCKED_register"}:
        require(required[key] == prior[key], "independent_output_proof_weakened_" + key)
    for key, target in (
        ("catalog", CATALOG),
        ("schema", CATALOG + ".schema"),
        ("recipe_authority", RECIPES),
        ("recipe_schema", RECIPES + ".schema"),
    ):
        require(
            required[key] == qualification(root, target), "unqualified_required_output_resource"
        )
    require(
        required["policy"] == catalog["coverage"]
        and required["catalog_counts"] == counts
        and required["BLOCKED_register"] == catalog["blockers"],
        "false_required_output_accounting",
    )
    require(
        required["inherited_output_authority"] == catalog["inherited_output_authority"]
        and required["identity_recipe_operations"] == kinds,
        "wrong_actual_producer_vocabulary",
    )
    require(
        required["actual_rule_resolution"]
        == "qualified_catalog_definition_and_actual_rule; local_literal_string_copy_resolves_through_AI_1.5_inherited_output_authority_to_actual_AI_1.4_not_AI_1.5",
        "invented_local_rule_owner",
    )
    require(
        required["instance_applicability"]
        == "Unknown_until_independently_evaluated_from_exact_source_identity_branch_and_context"
        and required["schema_valid_is_instance_proof"] is False,
        "forged_instance_completion_from_publication",
    )
    require(
        required["recipe_failure_policy"]
        == {
            "missing_ambiguous_provider_or_instance_qualification": "Unavailable",
            "valid_uuid_timestamp_beyond_selected_four_digit_year_representation": "Unavailable",
            "independently_malformed_noncanonical_or_conflicting_identity": "Rejected",
            "synthetic_alias_namespace_owner_time_or_reminted_identity": "Rejected",
            "unresolved": "only_actually_established_governed_dependency",
        },
        "wrong_recipe_failure_classification",
    )
    evidence = copy.deepcopy(old["qualification_evidence"])
    evidence["required_for_constructed"][
        -2
    ] = "all applicable AI 1.5 required-output destinations independently qualified with no BLOCKED or competing producer"
    evidence["required_for_constructed"].append(
        "each selected identity recipe independently verified against original sealed source aliases established UUID and exact qualified provider context; no asserted namespace receipt or changed digest substitutes"
    )
    require(
        value["qualification_evidence"] == evidence,
        "incomplete_independent_construction_qualification",
    )
    composition = value["composition"]
    previous_comp = old["composition"]
    same_except(
        composition,
        previous_comp,
        "binding_authority",
        "schema_authority",
        "selection_sequence",
        "record_qualification",
    )
    require(
        composition["selection_sequence"]
        == ["verify_complete_exact_ACC_1.5_closure", *previous_comp["selection_sequence"][1:]]
        and composition["record_qualification"]
        == "exact enclosing ACC 1.5 / AI 1.5 closures and actual inherited AI 1.3 rule qualifications; same verified binding/ADC/Authoring/NM/CEC basis",
        "changed_composition_or_rule_identity",
    )


def qualify_compatibility(root: Path, value: dict[str, Any]) -> None:
    require(
        set(value)
        == {
            "resource_kind",
            "resource_version",
            "semanticDependencies",
            "historical_definitions",
            "carry_forward",
            "successor_changes",
            "ledger_schema",
            "cross_version_evidence",
            "current_selection_change",
            "runtime_execution",
            "historical_conformance",
        },
        "undeclared_compatibility_authority",
    )
    require(
        value["resource_kind"] == "authoring-construction-compatibility"
        and value["resource_version"] == "1.5",
        "wrong_compatibility_identity",
    )
    require(
        value["historical_definitions"]
        == [
            {
                "family": "authoring-construction",
                "version": "1.4",
                "fingerprint": ACC14_SCF,
                "resources_mutated": False,
            }
        ],
        "historical_authority_rebound",
    )
    require(
        value["carry_forward"]
        == "all ACC 1.4 construction identity references roots composition lifecycle contextual ownership NM 2.5 ledgers equality diagnostics and outcome meaning retained"
        and value["successor_changes"]
        == [
            "exact enclosing AI 1.5 definition and complete resource closure",
            "three AI-owned representation recipes admitted only as qualified definitions with independently verified instance prerequisites",
            "exact producer-definition and actual governing-rule qualification",
        ],
        "unapproved_semantic_delta",
    )
    require(
        value["ledger_schema"] == LEDGER
        and value["cross_version_evidence"] == "never_promote_by_version_or_fingerprint_rewriting"
        and value["current_selection_change"] is False
        and value["runtime_execution"] is False
        and value["historical_conformance"]
        == "all historical ACC 1.0 through 1.4 authority/conformance and acceptance semantics remain immutable",
        "compatibility_or_public_boundary_weakened",
    )


def qualify_conformance(root: Path, value: dict[str, Any]) -> Counter[str]:
    require(
        set(value)
        == {
            "resource_kind",
            "resource_version",
            "conformance_level",
            "authority_only",
            "runtime_execution_coverage",
            "semanticDependencies",
            "inherited_cases",
            "cases",
        },
        "undeclared_conformance_scope",
    )
    require(
        value["resource_kind"] == "authoring-construction-conformance"
        and value["resource_version"] == "1.5"
        and value["conformance_level"] == "frozen_authority"
        and value["authority_only"] is True
        and value["runtime_execution_coverage"] is False,
        "conformance_claims_execution",
    )
    historical = read(root, BASE + "conformance")["cases"]
    require(len(value["inherited_cases"]) == len(historical), "missing_historical_case_reference")
    for i, (case, old) in enumerate(zip(value["inherited_cases"], historical, strict=True)):
        require(
            set(case) == {"case_id", "qualification", "preserved_assertions", "scope", "review"}
            and case["case_id"] == old["case_id"]
            and case["qualification"] == qualification(root, BASE + "conformance", f"/cases/{i}")
            and case["preserved_assertions"] == old["assertions"]
            and case["scope"] == "historical_authority_only_not_executed_successor_request",
            "historical_case_relabelled_or_assertion_changed",
        )
        state = old["fixture"]["input"]
        if state.get("code") in {"alias_ref_recipe", "uri_recipe", "created_at_encoding"}:
            expected = "historical_BLOCKED_only; exact_AI_1.5_recipes_qualify_successor_definitions_not_old_receipts_or_instance_values"
        elif "label_rule" in state:
            expected = "actual_AI_1.4_literal_copy_authority_preserved; enclosing_AI_1.5_selection_does_not_relabel_local_rules"
        elif "enclosing_AI" in state or old.get("review_class") == "successor_selection":
            expected = "historical_enclosing_selection_preserved; independently_select_ACC_1.5_AI_1.5_and_NM_2.5_for_successor_claims"
        else:
            expected = "preserve_historical_assertions_under_actual_authority; successor_output_and_instance_prerequisites_are_additional_not_substitutes"
        require(case["review"] == expected, "missing_individual_historical_scope_review")
    unavailable = {
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
    }
    rejected = {
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
    }
    obligations = {
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
    }
    catalog = read(root, CATALOG)
    recipe_kinds = {r["specification"]["operation"] for r in read(root, RECIPES)["recipes"]}
    expected_refs: dict[str, tuple[str, dict[str, Any], dict[str, Any]]] = {}
    for i, row in enumerate(catalog["types"]):
        for j, output in enumerate(row["outputs"]):
            key = f"/types/{i}/outputs/{j}"
            if output["status"] == "BLOCKED":
                category = "blocked_destination"
            else:
                kind = output["producer"]["kind"]
                category = (
                    "identity_recipe_definition"
                    if kind in recipe_kinds
                    else (
                        "literal_label_definition"
                        if kind == "literal_string_copy"
                        else "inherited_producer_definition"
                    )
                )
            expected_refs[key] = (category, row, output)
    seen: set[tuple[str, str]] = set()
    counters: Counter[str] = Counter()
    claims = {
        "type_branch": "Qualify the exact source/output branch and every conditional/nested destination; type membership grants no root or instance output.",
        "blocked_destination": "A statically BLOCKED destination is not a producer; when independently applicable its missing prerequisite prevents complete materialization.",
        "producer": "The exact producer definition and actual rule are qualified; all five independent checks and original semantic preservation remain necessary for an instance.",
        "recipe_exclusion": "Entity-envelope identity recipes do not create relationship envelopes, proposition-owned values or owner-local roots.",
        "recipe_authority": "Select the actual AI 1.5 operation and complete source/identity/provider/range constraints; publication does not execute a recipe.",
        "negative_qualification": "Independent authority and instance qualification must reject the fault atomically; flags, schemas, digests, replay copies and counts cannot substitute for proof.",
        "construction_obligation": "Preserve complete independent construction qualification and the authority-only publication boundary.",
    }
    for i, case in enumerate(value["cases"], 1):
        require(
            case["case_id"] == f"ACC15-{i:03d}"
            and case["runtime_coverage"] == "authority_only_not_implemented"
            and case["fixture"]["kind"] == "authority_reference",
            "invalid_or_runtime_conformance_identity",
        )
        category, state = case["category"], case["fixture"]["input"]
        assertions: dict[str, Any]
        if category in {
            "identity_recipe_definition",
            "literal_label_definition",
            "inherited_producer_definition",
            "blocked_destination",
        }:
            selector = state["qualification"]["schema_pointer"]
            require(selector in expected_refs, "fabricated_destination_conformance")
            expected_category, row, output = expected_refs[selector]
            require(category == expected_category, "BLOCKED_or_producer_conformance_reclassified")
            expected_state: dict[str, Any] = {
                "qualification": qualification(root, CATALOG, selector),
                "semantic_type": row["semantic_type"],
                "output_branch": row["output_branch"],
                "destination": output["destination"],
            }
            if category == "blocked_destination":
                expected_state.update(
                    blocked_code=output["blocked"]["code"], applicability="Unknown"
                )
                assertions = {
                    "producer": False,
                    "outcome_if_applicable": "Unavailable",
                    "instance_applicability": "Unknown",
                    "complete_materialization": False,
                }
                claim = claims[category]
            else:
                expected_state.update(
                    producer_kind=output["producer"]["kind"],
                    producer_rule=resolved_authority(root, catalog, output),
                )
                assertions = {
                    "qualified_definition": True,
                    "instance_output_established": False,
                    "verification_checks": list(CHECKS),
                    "original_semantics_preserved_once": True,
                    "second_semantic_owner": False,
                }
                claim = claims["producer"]
            require(state == expected_state, "wrong_producer_conformance_qualification")
            identity = (category, selector)
        elif category in {"type_branch", "recipe_exclusion"}:
            selector = state["qualification"]["schema_pointer"]
            row = pointer(catalog, selector)
            require(any(row is r for r in catalog["types"]), "wrong_type_conformance_selector")
            require(
                state
                == {
                    "qualification": qualification(root, CATALOG, selector),
                    "semantic_type": row["semantic_type"],
                    "output_branch": row["output_branch"],
                },
                "wrong_branch_conformance_qualification",
            )
            if category == "type_branch":
                assertions = {
                    "root_permission_granted": False,
                    "instance_applicability": "Unknown",
                    "complete_branch_constraints_required": True,
                }
            else:
                require(
                    row["output_branch"] not in {"regular", "normative-proposition"},
                    "incorrect_recipe_exclusion",
                )
                assertions = {
                    "identity_entity_recipes_apply": False,
                    "synthetic_entity_created": False,
                }
            claim, identity = claims[category], (category, selector)
        elif category == "recipe_authority":
            selector = state["qualification"]["schema_pointer"]
            recipe = pointer(read(root, RECIPES), selector)
            require(
                state
                == {
                    "qualification": qualification(root, RECIPES, selector),
                    "producer_kind": recipe["specification"]["operation"],
                }
                and recipe["specification"]["operation"] in recipe_kinds,
                "wrong_recipe_conformance_identity",
            )
            claim, identity = claims[category], (category, selector)
            assertions = {
                "recipe_owned_by_AI": True,
                "runtime_enabled": False,
                "representation_only": True,
            }
        elif category == "selection":
            target = state["qualification"]["canonical_resource_key"]
            require(
                target in {AI + "contract", "normalized-model/2.5/contract"}
                and state == {"qualification": qualification(root, target)},
                "wrong_selection_conformance",
            )
            if target == AI + "contract":
                assertions = {
                    "family": "architecture-interpretation",
                    "version": "1.5",
                    "SCF": selected_ai_fingerprint(root),
                    "resource_count": len(read(root, target)["resourceManifest"]),
                }
                claim = "Independently qualify the exact AI 1.5 definition and complete immutable closure; inherited resource identities are not enclosing interpretation substitutes."
            else:
                assertions = {
                    "version": "2.5",
                    "SCF": NM_SCF,
                    "complete_actual_model_required": True,
                }
                claim = "Require the actual complete schema-valid NM 2.5 result, not a local partial model or schema-valid assertion alone."
            identity = (category, target)
        elif category == "negative_qualification":
            fault = state["fault"]
            require(
                set(state) == {"fault"} and fault in unavailable | rejected,
                "unknown_negative_conformance_obligation",
            )
            assertions = {
                "outcome": "Unavailable" if fault in unavailable else "Rejected",
                "qualifies": False,
                "partial_success": False,
                "independent_diagnostics_retained": True,
            }
            claim, identity = claims[category], (category, fault)
        else:
            require(
                category == "construction_obligation"
                and set(state) == {"obligation"}
                and state["obligation"] in obligations,
                "unknown_construction_conformance_obligation",
            )
            name = state["obligation"]
            assertions = {name: obligations[name]}
            claim, identity = claims[category], (category, name)
        require(identity not in seen, "duplicate_conformance_assertion")
        seen.add(identity)
        require(
            case["claim"] == claim
            and case["assertions"]
            == [{"path": k, "operator": "equals", "expected": v} for k, v in assertions.items()],
            "changed_conformance_meaning_or_outcome",
        )
        counters[category] += 1
    wanted = {(category, selector) for selector, (category, _, _) in expected_refs.items()}
    wanted |= {("type_branch", f"/types/{i}") for i in range(len(catalog["types"]))}
    wanted |= {
        ("recipe_exclusion", f"/types/{i}")
        for i, row in enumerate(catalog["types"])
        if row["output_branch"] not in {"regular", "normative-proposition"}
    }
    wanted |= {("recipe_authority", f"/recipes/{i}") for i in range(len(recipe_kinds))}
    wanted |= {("selection", key) for key in (AI + "contract", "normalized-model/2.5/contract")}
    wanted |= {("negative_qualification", fault) for fault in unavailable | rejected}
    wanted |= {("construction_obligation", name) for name in obligations}
    require(seen == wanted, "incomplete_independent_conformance_coverage")
    return counters


def sealed_schemas(
    root: Path, raw: dict[str, Any], allowed: set[str]
) -> tuple[dict[str, Any], Registry[Any]]:
    documents = {key: read(root, key) for key in allowed if key not in {PREFIX + n for n in NAMES}}
    documents.update({PREFIX + n: v for n, v in raw.items()})
    schemas = {
        k: v
        for k, v in documents.items()
        if isinstance(v, dict)
        and "$schema" in v
        and (k.endswith("/schema") or k.endswith(".schema") or "/schema/" in k)
    }
    reachable: set[str] = set()
    visited: set[tuple[str, str]] = set()

    def selected(key: str, selector: str) -> None:
        if (key, selector) in visited:
            return
        require(key in schemas, "missing_sealed_schema_reference")
        require(
            schemas[key]["$schema"]
            in {
                "http://json-schema.org/draft-07/schema#",
                "https://json-schema.org/draft/2020-12/schema",
            },
            "unsupported_sealed_schema_dialect",
        )
        visited.add((key, selector))
        reachable.add(key)
        try:
            node = pointer(schemas[key], selector)
        except PublicationError as error:
            raise PublicationError(
                f"unresolved_sealed_schema_selector: {key}#{selector}"
            ) from error
        references(node, key)

    def references(node: Any, key: str) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                target = relative_resource_key(key, ref) or key
                selected(target, ref.split("#", 1)[1] if "#" in ref else "")
            for value in node.values():
                references(value, key)
        elif isinstance(node, list):
            for value in node:
                references(value, key)

    # Qualify every own schema and every transitively selected fragment.
    # Historical schema members are still integrity-qualified by their exact
    # immutable closures, not retroactively reinterpreted as NM 2.5 branches.
    for name in ("schema", "composition-bindings.schema", "conformance.schema"):
        selected(PREFIX + name, "")

    def view(node: Any, key: str) -> Any:
        if isinstance(node, list):
            return [view(v, key) for v in node]
        if not isinstance(node, dict):
            return node
        result = {k: view(v, key) for k, v in node.items() if k != "$id"}
        if "$ref" in node:
            reference = node["$ref"]
            target = relative_resource_key(key, reference) or key
            require(target in schemas, "missing_sealed_schema_reference")
            selector = reference.split("#", 1)[1] if "#" in reference else ""
            # Selected selectors were checked above. A reachable document may
            # also contain unused historical definitions; do not follow them.
            result["$ref"] = (
                "https://sealed.adr-kit.invalid/" + target + ("#" + selector if selector else "")
            )
        return result

    views = {}
    for key in sorted(reachable):
        value = schemas[key]
        transformed = view(value, key)
        transformed.pop(
            "semanticDependencies", None
        )  # Root annotation only; instance property retained.
        transformed["$id"] = "https://sealed.adr-kit.invalid/" + key
        views[key] = transformed
    registry: Registry[Any] = Registry().with_resources(
        (v["$id"], Resource.from_contents(v)) for v in views.values()
    )
    return views, registry


def qualify_conformance_schema(value: dict[str, Any]) -> None:
    require(
        set(value)
        == {
            "$schema",
            "$id",
            "semanticDependencies",
            "type",
            "additionalProperties",
            "required",
            "properties",
        }
        and value["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        and value["$id"]
        == "https://adr-kit.dev/semantic-contract/resources/" + PREFIX + "conformance.schema.json",
        "invalid_closed_conformance_schema",
    )

    def closed(node: dict[str, Any], keys: set[str]) -> None:
        require(
            set(node) == {"type", "additionalProperties", "required", "properties"}
            and node["type"] == "object"
            and node["additionalProperties"] is False
            and set(node["required"]) == keys
            and len(node["required"]) == len(keys)
            and set(node["properties"]) == keys,
            "open_or_incomplete_conformance_shape",
        )

    closed(
        {k: v for k, v in value.items() if k not in {"$schema", "$id", "semanticDependencies"}},
        {
            "resource_kind",
            "resource_version",
            "conformance_level",
            "authority_only",
            "runtime_execution_coverage",
            "semanticDependencies",
            "inherited_cases",
            "cases",
        },
    )
    props = value["properties"]
    for key, expected in {
        "resource_kind": "authoring-construction-conformance",
        "resource_version": "1.5",
        "conformance_level": "frozen_authority",
        "authority_only": True,
        "runtime_execution_coverage": False,
    }.items():
        require(
            props[key] == {"const": expected}, "wrong_conformance_version_or_execution_boundary"
        )
    require(
        props["semanticDependencies"]
        == {"type": "array", "uniqueItems": True, "items": {"type": "string", "minLength": 1}},
        "unqualified_conformance_dependencies",
    )
    for collection in ("cases", "inherited_cases"):
        require(
            set(props[collection]) == {"type", "minItems", "items"}
            and props[collection]["type"] == "array"
            and props[collection]["minItems"] == 1,
            "incomplete_conformance_case_collection",
        )
    case = props["cases"]["items"]
    closed(case, {"case_id", "category", "claim", "fixture", "assertions", "runtime_coverage"})
    cp = case["properties"]
    require(
        cp["case_id"] == {"type": "string", "pattern": "^ACC15-[0-9]{3}$"}
        and cp["runtime_coverage"] == {"const": "authority_only_not_implemented"}
        and cp["claim"] == {"type": "string", "minLength": 1},
        "invalid_conformance_case_identity",
    )
    require(
        cp["category"]
        == {
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
        "unknown_conformance_category",
    )
    assertion = {
        "$ref": "../1.4/conformance.schema.json#/properties/cases/items/properties/assertions"
    }
    reference = {
        "$ref": "../../architecture-interpretation/1.4/required-output-derivations.schema.json#/properties/field_dispositions"
    }
    require(cp["assertions"] == assertion, "weakened_assertion_schema")
    closed(cp["fixture"], {"kind", "input"})
    require(
        cp["fixture"]["properties"]["kind"] == {"const": "authority_reference"},
        "false_runtime_fixture",
    )
    inp = cp["fixture"]["properties"]["input"]
    expected_inputs = {
        "qualification": reference,
        "semantic_type": {"type": "string"},
        "output_branch": {"type": "string"},
        "destination": {"type": "string"},
        "producer_kind": {"type": "string"},
        "producer_rule": reference,
        "blocked_code": {"type": "string"},
        "applicability": {"const": "Unknown"},
        "fault": {"type": "string"},
        "obligation": {"type": "string"},
    }
    require(
        inp == {"type": "object", "additionalProperties": False, "properties": expected_inputs},
        "open_conformance_fixture_input",
    )
    inherited = props["inherited_cases"]["items"]
    closed(inherited, {"case_id", "qualification", "preserved_assertions", "scope", "review"})
    require(
        inherited["properties"]
        == {
            "case_id": {"type": "string", "pattern": "^ACC14-[0-9]{3}$"},
            "qualification": reference,
            "preserved_assertions": assertion,
            "scope": {"const": "historical_authority_only_not_executed_successor_request"},
            "review": {"type": "string", "minLength": 1},
        },
        "historical_case_impersonation_schema",
    )


def qualify(
    root: Path = ROOT,
    *,
    published: bool = True,
    candidate_definition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Proposed metadata receives the same complete independent qualification.
    token = _snapshot.set(
        {PREFIX + "contract": copy.deepcopy(candidate_definition)}
        if candidate_definition is not None
        else {}
    )
    digest_token = _digests.set({})
    try:
        return _qualify(root, published=published)
    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        OSError,
        SchemaError,
        ValidationError,
        UnknownDialect,
        Unresolvable,
    ) as error:
        if isinstance(error, PublicationError):
            raise
        raise PublicationError("incomplete_or_invalid_ACC_1_5_authority: " + str(error)) from error
    finally:
        _snapshot.reset(token)
        _digests.reset(digest_token)


def _qualify(root: Path, *, published: bool) -> dict[str, Any]:
    ai_report = qualified_history(root)
    raw = {n: read(root, PREFIX + n) for n in NAMES}
    require(
        all(
            raw[n].get("resource_version") == "1.5"
            for n in ("rules", "compatibility", "composition-bindings", "conformance")
        ),
        "wrong_successor_resource_version",
    )
    predecessors = (read(root, BASE + "contract"), read(root, AI + "contract"))
    inherited_keys = {
        e["canonicalResourceKey"] for d in predecessors for e in d["resourceManifest"]
    } | {BASE + "contract", AI + "contract"}
    own = {PREFIX + n for n in NAMES}
    allowed = inherited_keys | own
    for name, value in raw.items():
        require(
            PREFIX + "contract" not in discovered_dependencies(PREFIX + name, value),
            "self_referential_ACC_SCF",
        )
        require(
            discovered_dependencies(PREFIX + name, value) <= allowed,
            "unselected_or_missing_dependency",
        )
    qualify_binding(root, raw)
    producer_counts = qualify_schema(root, raw)
    qualify_rules(root, raw)
    qualify_compatibility(root, raw["compatibility"])
    qualify_conformance_schema(raw["conformance.schema"])
    cases = qualify_conformance(root, raw["conformance"])
    old_rules = read(root, BASE + "rules")
    ai_keys = {e["canonicalResourceKey"] for e in read(root, AI + "contract")["resourceManifest"]}
    base_keys = {
        e["canonicalResourceKey"] for e in read(root, BASE + "contract")["resourceManifest"]
    }
    expected_deps = {
        "schema": set(read(root, BASE + "schema")["semanticDependencies"])
        | ai_keys
        | {
            AI + "contract",
            CATALOG,
            CATALOG + ".schema",
            RECIPES,
            RECIPES + ".schema",
            LEDGER,
            BASE + "schema",
            PREFIX + "composition-bindings",
            PREFIX + "composition-bindings.schema",
        },
        "rules": set(old_rules["semanticDependencies"])
        | ai_keys
        | {
            AI + "contract",
            AI + "rules",
            CATALOG,
            CATALOG + ".schema",
            RECIPES,
            RECIPES + ".schema",
            BASE + "rules",
            PREFIX + "composition-bindings",
            PREFIX + "composition-bindings.schema",
            LEDGER,
        },
        "compatibility": base_keys
        | {BASE + "contract", BASE + "compatibility", AI + "contract", CATALOG, RECIPES, LEDGER},
        "conformance": {
            BASE + "conformance",
            AI + "contract",
            CATALOG,
            RECIPES,
            LEDGER,
            "normalized-model/2.5/contract",
        }
        | (own - {PREFIX + "conformance"}),
        "conformance.schema": {
            BASE + "conformance.schema",
            "architecture-interpretation/1.4/required-output-derivations.schema",
        },
    }
    for name, expected in expected_deps.items():
        require(
            raw[name]["semanticDependencies"] == sorted(expected),
            "incorrect_authoritative_dependency_edges_" + name,
        )
    views, registry = sealed_schemas(root, raw, allowed)
    for name in ("schema", "composition-bindings.schema", "conformance.schema"):
        Draft202012Validator.check_schema(raw[name])
    for name in ("composition-bindings", "conformance"):
        Draft202012Validator(views[PREFIX + name + ".schema"], registry=registry).validate(
            raw[name]
        )
    if published:
        from adr_kit.semantic_contract import (
            verify_semantic_contract,
            validate_semantic_resource_closure,
        )

        contract = read(root, PREFIX + "contract")
        require(
            contract["semanticContractFamily"] == "authoring-construction"
            and contract["semanticContractVersion"] == "1.5"
            and contract["fingerprintScheme"] == "scf:v1:sha256"
            and contract["frozenNormativeConformanceResources"] == [PREFIX + "conformance"],
            "wrong_ACC_1_5_identity_or_frozen_conformance",
        )
        manifest = contract["resourceManifest"]
        require(
            len(manifest) == len(allowed)
            and {m["canonicalResourceKey"] for m in manifest} == allowed
            and [m["canonicalResourceKey"] for m in manifest] == sorted(allowed),
            "incomplete_extra_or_duplicate_ACC_closure",
        )
        require(
            contract["semanticContractFingerprint"] not in json.dumps(raw),
            "enclosing_SCF_embedded_in_own_resources",
        )
        roles = {BASE + "contract": "normative-definition", AI + "contract": "normative-definition"}
        for d in predecessors:
            for m in d["resourceManifest"]:
                require(
                    m["canonicalResourceKey"] not in roles
                    or roles[m["canonicalResourceKey"]] == m["role"],
                    "conflicting_historical_resource_roles",
                )
                roles[m["canonicalResourceKey"]] = m["role"]
        for n in NAMES:
            roles[PREFIX + n] = (
                "interpretation-conformance"
                if n == "conformance"
                else (
                    "source-contract-schema"
                    if n == "schema" or n.endswith(".schema")
                    else "normative-definition" if n == "compatibility" else "interpretation-rule"
                )
            )
        for m in manifest:
            key = m["canonicalResourceKey"]
            content = read(root, key)
            require(
                m["contentDigest"] == digest(content) and m["role"] == roles[key],
                "resource_digest_or_role_mismatch",
            )
            require(
                m["dependencies"]
                == [
                    {"canonicalResourceKey": dep, "contentDigest": digest(read(root, dep))}
                    for dep in sorted(discovered_dependencies(key, content))
                ],
                "inconsistent_manifest_dependency_edge",
            )
        qualify_binding(root, raw, manifest)
        bundle = [
            {
                "canonicalResourceKey": m["canonicalResourceKey"],
                "content": read(root, m["canonicalResourceKey"]),
            }
            for m in manifest
        ]
        require(
            verify_semantic_contract(contract).success is True
            and validate_semantic_resource_closure(contract, bundle).closure_valid is True,
            "invalid_ACC_1_5_fingerprint_or_closure",
        )
    require(
        sum(producer_counts.values()) == ai_report["output_accounting"]["QUALIFIED"],
        "producer_alternatives_do_not_cover_catalog",
    )
    return {
        "semantic_types": ai_report["semantic_types"],
        "output_branches": ai_report["output_branches"],
        "qualified_producer_definitions": sum(producer_counts.values()),
        "BLOCKED_definitions": ai_report["output_accounting"]["BLOCKED"],
        "literal_copy_label_rules": ai_report["literal_string_copy_rules"],
        "identity_recipe_transitions": sum(ai_report["transitions"].values()),
        "active_blocker_categories": ai_report["active_blocker_categories"],
        "producer_kinds": producer_counts,
        "inherited_conformance_cases": len(raw["conformance"]["inherited_cases"]),
        "new_conformance_cases": len(raw["conformance"]["cases"]),
        "conformance_categories": dict(cases),
        "instance_applicability": "Unknown",
        "complete_interpretation": "Unavailable",
        "runtime_execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(qualify(), indent=2))
