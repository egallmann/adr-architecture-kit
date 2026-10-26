"""Version-isolated AI 1.5 asset producer. Never execute source interpretation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.generate_semantic_contract_assets import (
    definition,
    digest,
    discovered_dependencies,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
P = "architecture-interpretation/1.5/"
B = "architecture-interpretation/1.4/"
NAMES = (
    "rules",
    "required-output-derivations",
    "required-output-derivations.schema",
    "identity-representation-recipes",
    "identity-representation-recipes.schema",
    "conformance",
    "conformance.schema",
)
NM = "normalized-model/2.5/contract"
CONTEXT = "architecture-interpretation/1.3/detached-context"


def read(root: Path, key: str) -> Any:
    if key.endswith("/contract"):
        f, v, _ = key.split("/")
        path = root / (
            f"contracts/semantic-contract/v1.0/definitions/{f}-{v}.json"
            if f in {"architecture-interpretation", "authoring-construction", "normalized-model"}
            else f"contracts/{f}/v{v}/contract.json"
        )
    elif key.startswith(P):
        path = (
            root
            / "contracts/architecture-interpretation/v1.5/resources"
            / (key.removeprefix(P) + ".json")
        )
    else:
        path = (
            root / "contracts/semantic-contract/v1.0/resources" / (key.replace("/", "-") + ".json")
        )
        if not path.exists() and len(key.split("/")) == 3:
            f, _, name = key.split("/")
            path = path.with_name(f"{f}-{name}.json")
    return json.loads(path.read_text(encoding="utf-8"))


def q(root: Path, key: str, pointer: str = "") -> dict[str, str]:
    return {
        "canonical_resource_key": key,
        "content_digest": digest(read(root, key)),
        "schema_pointer": pointer,
    }


def schema_id(name: str) -> str:
    return (
        "https://adr-kit.ste.systems/contracts/architecture-interpretation/v1.5/resources/"
        + name
        + ".json"
    )


def closed(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties) if required is None else required,
        "properties": properties,
    }


def inherited_ref(pointer: str) -> dict[str, str]:
    return {"$ref": "../1.4/required-output-derivations.schema.json#" + pointer}


def qualification_schema() -> dict[str, str]:
    return inherited_ref("/properties/field_dispositions")


def recipes(root: Path) -> dict[str, Any]:
    adr = yaml.safe_load(
        next((root / "adrs/logical").glob("ADR-L-0039-*.yaml")).read_text(encoding="utf-8")
    )
    if adr["status"] not in {"accepted", "superseded", "deprecated"} or not adr.get(
        "governance", {}
    ).get("approved_by"):
        raise ValueError("ADR-L-0039 accepted lineage required")
    old = read(root, B + "required-output-derivations")
    types = [
        t["semantic_type"]
        for t in old["types"]
        if t["output_branch"] in {"regular", "normative-proposition"}
    ]
    historical = yaml.safe_load(
        next((root / "adrs/logical").glob("ADR-L-0019-*.yaml")).read_text(encoding="utf-8")
    )
    historical_ids = {d["alias_id"]: d["id"] for d in historical["decisions"]}
    items = []
    roles = [
        [
            {
                "role": "authored_alias_id",
                "type": "string",
                "source_property": "alias_id",
                "presence": "required_authored",
            },
            {
                "role": "authored_alias_name",
                "type": "string",
                "source_property": "alias_name",
                "presence": "required_authored",
            },
        ],
        [
            {
                "role": "qualified_architecture_namespace",
                "type": "string",
                "context_property": "architecture_namespace",
                "presence": "independently_qualified_context",
            },
            {
                "role": "established_uuidv7",
                "type": "string",
                "source_property": "id",
                "presence": "established_once_source_bound_lowercase_uuidv7",
            },
        ],
        [
            {
                "role": "established_uuidv7",
                "type": "string",
                "source_property": "id",
                "presence": "established_once_source_bound_lowercase_uuidv7",
            }
        ],
    ]
    for i, short in enumerate(("alias-ref", "entity-uri", "uuidv7-created-at")):
        d = adr["decisions"][i + 1]
        spec = yaml.safe_load(d["rationale"].split("```yaml\n")[1].split("```", 1)[0])
        inv = adr["invariants"][i + 1]
        inherited = (
            ("DEC-0093",) if i == 0 else ("DEC-0098", "DEC-0107") if i == 1 else ("DEC-0099",)
        )
        items.append(
            {
                "id": "identity-representation." + short,
                "specification": spec,
                "input_contract": roles[i],
                "classification": "representation_only",
                "independent_semantic_owner": False,
                "original_semantics": "preserve_original_authored_aliases_canonical_identity_and_qualified_context_once",
                "lineage": {
                    "adr_id": adr["id"],
                    "decision_id": d["id"],
                    "decision_alias": d["alias_id"],
                    "invariant_id": inv["id"],
                    "invariant_alias": inv["alias_id"],
                    "inherited_decisions": [
                        {"alias": alias, "id": historical_ids[alias]} for alias in inherited
                    ],
                },
                "verification": [
                    "independently_verified_sealed_source_basis",
                    "original_request_and_established_identity_commitment_where_applicable",
                    "exact_selected_source_and_destination_schema",
                    "qualified_provider_context_where_required",
                    "independent_complete_string_reconstruction",
                    "complete_selected_NM_branch_validation",
                    "semantic_equality_is_independent_not_a_replay_or_digest_comparison",
                ],
                "failure_policy": {
                    "independently_invalid_source_or_canonical_identity": "Rejected",
                    "conflicting_canonical_identity_or_producer": "Rejected",
                    "missing_authority_or_instance_evidence": "Unavailable",
                    "missing_or_ambiguous_provider": "Unavailable",
                    "valid_uuid_timestamp_outside_selected_representation": "Unavailable",
                    "unresolved": "only_independently_established_governed_dependency",
                },
            }
        )
    return {
        "resource": P + "identity-representation-recipes",
        "semanticDependencies": sorted(
            {
                P + "identity-representation-recipes.schema",
                CONTEXT,
                NM,
                *[t["source_schema"]["canonical_resource_key"] for t in old["types"]],
                "normalized-model/2.5/schema/normalized-entity.schema",
            }
        ),
        "source_contract": "authoring@1.7",
        "destination_authority": {
            "definition": q(root, NM),
            "semantic_contract_fingerprint": read(root, NM)["semanticContractFingerprint"],
        },
        "applicability": {
            "semantic_types": types,
            "output_branches": ["regular", "normative-proposition"],
            "instance_applicability": "Unknown",
            "catalog_membership_grants_root_or_owner": False,
            "custom_CEC_selection": "independently_required_not_registry_invention",
            "shared_identity": "unique_unit_and_producer_before_applicability",
            "normative_proposition_lifecycle": "prohibited",
        },
        "context_authority": {
            "qualification": q(root, CONTEXT),
            "governing_family": "architecture-interpretation",
            "governing_version": "1.3",
            "semantic_contract_fingerprint": read(root, "architecture-interpretation/1.3/contract")[
                "semanticContractFingerprint"
            ],
            "namespace_selector": "/architecture_namespace",
            "provider_kind_selector": "/provider_kind",
            "verification": "independently_rederive_selected_context_from_exact_sealed_basis_no_asserted_namespace_or_locator_substitution",
        },
        "recipes": items,
        "scope": {
            "authority_only": True,
            "instance_values_produced": False,
            "complete_interpretation": "Unavailable",
            "runtime_capability_enabled": False,
        },
    }


def recipe_schema(value: dict[str, Any]) -> dict[str, Any]:
    # Closed versioned policy constraints. Qualification objects remain explicit
    # typed selectors; independent qualification rechecks their selected contents.
    props = {
        k: {"const": v}
        for k, v in value.items()
        if k
        not in {"semanticDependencies", "destination_authority", "context_authority", "recipes"}
    }
    props["semanticDependencies"] = {
        "type": "array",
        "items": {"type": "string"},
        "uniqueItems": True,
    }
    props["destination_authority"] = closed(
        {
            "definition": qualification_schema(),
            "semantic_contract_fingerprint": {
                "type": "string",
                "pattern": "^scf:v1:sha256:[0-9a-f]{64}$",
            },
        }
    )
    props["context_authority"] = closed(
        {
            k: qualification_schema() if k == "qualification" else {"const": v}
            for k, v in value["context_authority"].items()
        }
    )
    props["recipes"] = {
        "type": "array",
        "minItems": 3,
        "maxItems": 3,
        "items": {
            "oneOf": [
                closed({k: {"const": v} for k, v in item.items()}) for item in value["recipes"]
            ]
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_id("identity-representation-recipes.schema"),
        **closed(props),
        "semanticDependencies": [B + "required-output-derivations.schema"],
    }


def catalog_schema(root: Path, recipe_data: dict[str, Any]) -> dict[str, Any]:
    old = read(root, B + "required-output-derivations.schema")
    old_props = old["properties"]
    props: dict[str, Any] = {
        k: inherited_ref("/properties/" + k)
        for k in old_props
        if k not in {"resource", "semanticDependencies", "blockers", "types"}
    }
    props.update(
        {
            "resource": {"const": P + "required-output-derivations"},
            "semanticDependencies": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
            "blockers": {
                "const": {
                    k: v
                    for k, v in read(root, B + "required-output-derivations")["blockers"].items()
                    if k not in {"alias_ref_recipe", "uri_recipe", "created_at_encoding"}
                }
            },
            "identity_representation_recipes": qualification_schema(),
            "inherited_output_authority": closed(
                {
                    "catalog": qualification_schema(),
                    "semantic_contract_fingerprint": {
                        "const": read(root, B + "contract")["semanticContractFingerprint"]
                    },
                    "local_rule_bindings": closed({"literal_string_copy": qualification_schema()}),
                }
            ),
        }
    )
    row_pointer = "/properties/types/items"
    entry_pointer = row_pointer + "/properties/outputs/items"
    row = old_props["types"]["items"]
    props["types"] = {
        "type": "array",
        "items": closed(
            {
                k: (
                    inherited_ref(row_pointer + "/properties/" + k)
                    if k != "outputs"
                    else {
                        "type": "array",
                        "items": {
                            "oneOf": [
                                inherited_ref(entry_pointer),
                                {"$ref": "#/$defs/identity_output"},
                            ]
                        },
                    }
                )
                for k in row["properties"]
            },
            row["required"],
        ),
    }
    producer = closed(
        {
            "kind": {"enum": [r["specification"]["operation"] for r in recipe_data["recipes"]]},
            "rule_id": {"enum": [r["id"] for r in recipe_data["recipes"]]},
            "rule": qualification_schema(),
            "inputs": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": qualification_schema(),
            },
            "source_field": {"const": ""},
        }
    )
    producer["allOf"] = [
        {
            "if": {"properties": {"kind": {"const": r["specification"]["operation"]}}},
            "then": {
                "properties": {
                    "rule_id": {"const": r["id"]},
                    "inputs": {
                        "minItems": len(r["input_contract"]),
                        "maxItems": len(r["input_contract"]),
                    },
                }
            },
        }
        for r in recipe_data["recipes"]
    ]
    entry = old_props["types"]["items"]["properties"]["outputs"]["items"]
    identity_props = {
        k: inherited_ref(entry_pointer + "/properties/" + k) for k in entry["required"]
    }
    identity_props.update(
        {
            "status": {"const": "QUALIFIED"},
            "classification": {"const": "representation_only"},
            "semantic_equality": {"const": "original_inputs_once_not_generated_representation"},
            "producer": {"$ref": "#/$defs/identity_producer"},
        }
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_id("required-output-derivations.schema"),
        **closed(props),
        "$defs": {"identity_output": closed(identity_props), "identity_producer": producer},
        "semanticDependencies": [B + "required-output-derivations.schema"],
    }


def catalog(root: Path, recipe_data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = copy.deepcopy(read(root, B + "required-output-derivations"))
    result["resource"] = P + "required-output-derivations"
    result["semanticDependencies"] = sorted(
        set(result["semanticDependencies"]) - {B + "required-output-derivations.schema"}
        | {
            P + "required-output-derivations.schema",
            P + "identity-representation-recipes",
            CONTEXT,
            B + "required-output-derivations",
        }
    )
    result["identity_representation_recipes"] = q(root, P + "identity-representation-recipes")
    result["inherited_output_authority"] = {
        "catalog": q(root, B + "required-output-derivations"),
        "semantic_contract_fingerprint": read(root, B + "contract")["semanticContractFingerprint"],
        "local_rule_bindings": {
            "literal_string_copy": q(root, B + "required-output-derivations", "/operation")
        },
    }
    for code in ("alias_ref_recipe", "uri_recipe", "created_at_encoding"):
        result["blockers"].pop(code)
    by_destination = {
        r["specification"]["destination"]: (i, r) for i, r in enumerate(recipe_data["recipes"])
    }
    for row in result["types"]:
        if row["output_branch"] not in {"regular", "normative-proposition"}:
            continue
        for entry in row["outputs"]:
            if entry["destination"] not in by_destination:
                continue
            i, recipe = by_destination[entry["destination"]]
            inputs = []
            for role in recipe["input_contract"]:
                if "source_property" in role:
                    source = row["source_schema"]
                    inputs.append(
                        q(
                            root,
                            source["canonical_resource_key"],
                            source["schema_pointer"] + "/properties/" + role["source_property"],
                        )
                    )
                else:
                    inputs.append(q(root, CONTEXT, "/" + role["context_property"]))
            entry.pop("blocked")
            entry.update(
                status="QUALIFIED",
                classification="representation_only",
                semantic_equality="original_inputs_once_not_generated_representation",
                producer={
                    "kind": recipe["specification"]["operation"],
                    "rule_id": recipe["id"],
                    "rule": q(root, P + "identity-representation-recipes", f"/recipes/{i}"),
                    "inputs": inputs,
                    "source_field": "",
                },
            )
    return result


def rules(root: Path) -> dict[str, Any]:
    inherited = read(root, B + "contract")
    return {
        "resource": P + "rules",
        "semanticDependencies": sorted(
            {
                *[m["canonicalResourceKey"] for m in inherited["resourceManifest"]],
                B + "contract",
                NM,
                P + "required-output-derivations",
                P + "identity-representation-recipes",
            }
        ),
        "inherits": {
            "definition": q(root, B + "contract"),
            "semantic_contract_fingerprint": inherited["semanticContractFingerprint"],
            "overrides": [
                "identity_representation_required_output_definitions",
                "representation_only_identity_recipes",
            ],
        },
        "destination_authority": {
            "definition": q(root, NM),
            "semantic_contract_fingerprint": read(root, NM)["semanticContractFingerprint"],
        },
        "required_output_catalog": q(root, P + "required-output-derivations"),
        "recipe_authority": q(root, P + "identity-representation-recipes"),
        "required_output_coverage": read(root, B + "required-output-derivations")["coverage"],
        "inherited_authority": "actual_AI_1_3_and_AI_1_4_resource_keys_digests_SCFs_and_rule_identities_retained_no_version_rewriting",
        "representation_verification": "independent_complete_reconstruction_from_sealed_source_established_identity_exact_rule_and_context_not_asserted_flags_or_replay",
        "semantic_equality": "original_semantic_values_identity_context_order_and_multiplicity_once_not_generated_representation_ownership",
        "instance_applicability": "Unknown",
        "outcome_precedence": ["Rejected", "Unavailable", "Unresolved"],
        "public_boundary": {
            "enabled_by_publication": False,
            "runtime_execution_coverage": False,
            "complete_interpretation": "Unavailable",
            "semantic_equivalent": False,
            "Constructed": False,
            "publication_changes_current_selection": False,
        },
    }


def conformance(root: Path, recipe_data: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def case(category: str, ty: str, assertion: str, expected: str, **fixture: Any) -> None:
        cases.append(
            {
                "id": f"AI15-{len(cases)+1:03}",
                "category": category,
                "semantic_type": ty,
                "assertion": assertion,
                "expected": expected,
                "fixture": fixture,
                "coverage": "authority_only_not_runtime_execution",
            }
        )

    for row in data["types"]:
        if row["output_branch"] not in {"regular", "normative-proposition"}:
            case(
                "excluded_branch",
                row["semantic_type"],
                "Entity identity representation recipes do not create an entity envelope or independent root for this branch.",
                "excludes",
                given=["exact_selected_branch", "no_entity_envelope"],
                source_schema=row["source_schema"],
            )
            continue
        for entry in row["outputs"]:
            if entry.get("producer", {}).get("kind") not in {
                r["specification"]["operation"] for r in recipe_data["recipes"]
            }:
                continue
            case(
                "definition_qualification",
                row["semantic_type"],
                "Exact recipe definition qualifies only static authority; all source, identity, branch and contextual instance prerequisites remain independently required.",
                "conforms",
                destination=entry["destination"],
                operation=entry["producer"]["kind"],
                source_schema=row["source_schema"],
                destination_schema=entry["destination_schema"],
                given=[
                    "instance_applicability_Unknown",
                    "no_instance_value",
                    "one_producer_definition",
                    "original_semantics_preserved_once",
                ],
            )
    # Fixed oracle values, not invocation of the historical converter or a new interpreter.
    for timestamp, output in (
        (0, "1970-01-01T00:00:00.000Z"),
        (1, "1970-01-01T00:00:00.001Z"),
        (999, "1970-01-01T00:00:00.999Z"),
        (1000, "1970-01-01T00:00:01.000Z"),
        (86400000, "1970-01-02T00:00:00.000Z"),
        (951782400000, "2000-02-29T00:00:00.000Z"),
        (1609459200000, "2021-01-01T00:00:00.000Z"),
        (253402300799999, "9999-12-31T23:59:59.999Z"),
    ):
        case(
            "timestamp_oracle",
            "catalog",
            "An established canonical UUIDv7's timestamp verifies this exact four-digit RFC3339 millisecond representation; this fixture is not qualified instance evidence.",
            "conforms",
            timestamp_ms=timestamp,
            expected_output=output,
            given=["established_source_bound_uuidv7", "integer_time_no_clock"],
        )
    for timestamp in (253402300800000, 281474976710655):
        case(
            "timestamp_unavailable",
            "catalog",
            "A valid canonical UUIDv7 remains valid but cannot qualify the selected representation; do not truncate, remint or manufacture a string.",
            "unavailable",
            timestamp_ms=timestamp,
            given=["valid_canonical_uuidv7", "no_identity_mutation"],
        )
    for alias_id, alias_name, output in (
        ("DEC-0001", "first-decision", "DEC-0001:first-decision"),
        ("ADR-L-0001", "logical-root", "ADR-L-0001:logical-root"),
    ):
        case(
            "alias_oracle",
            "catalog",
            "Qualified authored aliases retain exact contents; the derived recognition string owns no second semantic value.",
            "conforms",
            input_values=[alias_id, alias_name],
            expected_output=output,
            given=["exact_qualified_authored_aliases", "no_normalization_or_lookup_authority"],
        )
    identifier = "00000000-0000-7000-8000-000000000001"
    for namespace in ("urn:adr-kit:detached-candidate:v1", "provider-a", "provider-b"):
        case(
            "uri_oracle",
            "catalog",
            "Given independently qualified provider context and identity, the resolver string is literal and opaque; fixtures do not create provider authority.",
            "conforms",
            input_values=[namespace, identifier],
            expected_output=f"adr://{namespace}/entities/{identifier}",
            given=["independently_qualified_provider_context", "established_source_bound_uuidv7"],
        )
    faults = {
        "alias_input": [
            "missing_alias",
            "wrong_alias_type",
            "authored_alias_ref_authority",
            "alias_case_folding",
            "alias_trimming",
            "alias_as_foreign_key",
        ],
        "namespace": [
            "missing_provider",
            "ambiguous_provider",
            "namespace_mismatch",
            "scope_root_substitution",
            "source_ref_substitution",
            "path_substitution",
            "URL_normalization",
            "percent_encoding",
            "Unicode_normalization",
            "wrong_inherited_context_rule",
        ],
        "identity": [
            "malformed_uuid",
            "uppercase_uuid",
            "wrong_uuid_version",
            "duplicate_canonical_identity",
            "duplicate_producer",
            "identity_reminting",
            "request_position_as_identity",
        ],
        "timestamp": [
            "wrong_fraction_precision",
            "clock_fallback",
            "authored_date_fallback",
            "Git_time_fallback",
            "float_rounding",
            "expanded_year",
            "wrong_timestamp_failure",
        ],
        "qualification": [
            "wrong_rule",
            "wrong_version",
            "wrong_SCF",
            "wrong_digest",
            "missing_source_evidence",
            "missing_context_evidence",
            "forged_receipt",
            "recomputed_unauthorized_SCF",
            "missing_nested_output",
            "missing_conditional_output",
            "competing_producer",
            "lost_authored_field",
            "second_semantic_owner",
        ],
    }
    for category, names in faults.items():
        for name in names:
            expected = (
                "unavailable"
                if name
                in {
                    "missing_provider",
                    "ambiguous_provider",
                    "missing_source_evidence",
                    "missing_context_evidence",
                }
                else "rejects"
            )
            case(
                category,
                "catalog",
                "Independently qualify exact authority, applicability, source/identity/context and complete representation. Known violations are Rejected; missing evidence is Unavailable; no fabricated Unresolved.",
                expected,
                mutation=name,
                given=["retain_independent_diagnostics", "no_partial_instance_result"],
            )
    for name in (
        "same_uuid_different_providers",
        "custom_CEC_selection_not_closure_only",
        "shared_system_unique_producer",
        "normative_proposition_lifecycle_freedom",
        "native_standalone_no_synthetic_owner",
        "resource_and_source_permutations",
        "original_186_producers_and_26_labels",
        "remaining_215_BLOCKED",
        "representation_verification_not_semantic_equality",
        "complete_interpretation_Unavailable",
        "historical_integrity_and_future_selection",
    ):
        case(
            "preservation",
            "catalog",
            "Preserve governed semantic identity, branch and proof distinctions without new roots, owners or public execution capability.",
            "preserves",
            mutation=name,
            given=[
                "authority_conformance_only",
                "instance_applicability_Unknown",
                "no_Constructed",
            ],
        )
    inherited_cases = read(root, B + "conformance")["cases"]
    return {
        "resource": P + "conformance",
        "semanticDependencies": sorted(
            {
                B + "conformance",
                P + "conformance.schema",
                P + "rules",
                P + "required-output-derivations",
                P + "identity-representation-recipes",
                *[t["source_schema"]["canonical_resource_key"] for t in data["types"]],
                "normalized-model/2.5/schema/normalized-entity.schema",
            }
        ),
        "authority_only": True,
        "runtime_execution_coverage": False,
        "inherited_conformance": q(root, B + "conformance"),
        "inherited_cases": [
            {
                "id": c["id"],
                "qualification": q(root, B + "conformance", f"/cases/{i}"),
                "scope": (
                    "historical_publication_snapshot_not_successor_absence_requirement"
                    if c["id"] == "AI14-085"
                    else "unchanged_semantic_obligation_under_actual_inherited_authority"
                ),
            }
            for i, c in enumerate(inherited_cases)
        ],
        "cases": cases,
    }


def conformance_schema() -> dict[str, Any]:
    fixture = closed(
        {
            "given": {"type": "array", "items": {"type": "string"}},
            "destination": {"enum": ["/alias_ref", "/uri", "/created_at"]},
            "operation": {
                "enum": [
                    "literal_alias_join",
                    "literal_entity_uri",
                    "uuidv7_unix_milliseconds_to_rfc3339_utc",
                ]
            },
            "source_schema": qualification_schema(),
            "destination_schema": qualification_schema(),
            "timestamp_ms": {"type": "integer", "minimum": 0, "maximum": 281474976710655},
            "expected_output": {"type": "string"},
            "input_values": {
                "type": "array",
                "items": {"type": ["string", "integer", "boolean", "null"]},
            },
            "mutation": {"type": "string"},
        },
        ["given"],
    )
    case = closed(
        {
            "id": {"type": "string", "pattern": "^AI15-[0-9]{3}$"},
            "category": {"type": "string", "minLength": 1},
            "semantic_type": {"type": "string", "minLength": 1},
            "assertion": {"type": "string", "minLength": 1},
            "expected": {"enum": ["conforms", "excludes", "unavailable", "rejects", "preserves"]},
            "fixture": fixture,
            "coverage": {"const": "authority_only_not_runtime_execution"},
        }
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_id("conformance.schema"),
        **closed(
            {
                "resource": {"const": P + "conformance"},
                "semanticDependencies": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {"type": "string"},
                },
                "authority_only": {"const": True},
                "runtime_execution_coverage": {"const": False},
                "inherited_conformance": qualification_schema(),
                "inherited_cases": {
                    "type": "array",
                    "items": closed(
                        {
                            "id": {"type": "string", "pattern": "^AI14-[0-9]{3}$"},
                            "qualification": qualification_schema(),
                            "scope": {
                                "enum": [
                                    "historical_publication_snapshot_not_successor_absence_requirement",
                                    "unchanged_semantic_obligation_under_actual_inherited_authority",
                                ]
                            },
                        }
                    ),
                },
                "cases": {"type": "array", "minItems": 1, "items": case},
            }
        ),
        "semanticDependencies": [B + "required-output-derivations.schema"],
    }


def publish(root: Path = ROOT) -> None:
    from scripts.qualify_ai15_publication import qualify

    source = root / "contracts/architecture-interpretation/v1.5"
    values = {}

    def put(name: str, value: Any) -> None:
        values[P + name] = value
        write_json(source / "resources" / (name + ".json"), value)

    recipe_data = recipes(root)
    put("identity-representation-recipes.schema", recipe_schema(recipe_data))
    put("identity-representation-recipes", recipe_data)
    put("required-output-derivations.schema", catalog_schema(root, recipe_data))
    data = catalog(root, recipe_data)
    put("required-output-derivations", data)
    put("rules", rules(root))
    put("conformance.schema", conformance_schema())
    put("conformance", conformance(root, recipe_data, data))
    qualify(root, published=False)
    contents = {}
    pending = set(values)
    while pending:
        key = min(pending)
        pending.remove(key)
        contents[key] = values[key] if key in values else read(root, key)
        pending.update(discovered_dependencies(key, contents[key]) - contents.keys())
    roles = {
        m["canonicalResourceKey"]: m["role"] for m in read(root, B + "contract")["resourceManifest"]
    }
    roles.update({B + "contract": "normative-definition", NM: "normative-definition"})
    manifest = []
    for key in sorted(contents):
        name = key.removeprefix(P)
        role = (
            (
                "interpretation-conformance"
                if name == "conformance"
                else "source-contract-schema" if name.endswith(".schema") else "interpretation-rule"
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
    result = definition("architecture-interpretation", manifest, [P + "conformance"], version="1.5")
    from adr_kit.semantic_contract import (
        verify_semantic_contract,
        validate_semantic_resource_closure,
    )

    bundle = [{"canonicalResourceKey": key, "content": value} for key, value in contents.items()]
    if (
        not verify_semantic_contract(result).success
        or not validate_semantic_resource_closure(result, bundle).closure_valid
    ):
        raise ValueError("AI 1.5 exact closure failed before distribution")
    for name in NAMES:
        filename = "architecture-interpretation-1.5-" + name + ".json"
        for directory in (
            root / "contracts/semantic-contract/v1.0/resources",
            root / "src/adr_kit/semantic_contract/v1_0/resources",
        ):
            (directory / filename).write_bytes(
                (source / "resources" / (name + ".json")).read_bytes()
            )
    for path in (
        source / "contract.json",
        root / "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.5.json",
        root
        / "src/adr_kit/semantic_contract/v1_0/definitions/architecture-interpretation-1.5.json",
        root / "src/adr_kit/semantic_contract/v1_0/architecture-interpretation-1.5.json",
    ):
        write_json(path, result)
    print(json.dumps(qualify(root), indent=2))


if __name__ == "__main__":
    publish()
