"""Independent AI 1.5 publication qualification, never instance materialization.

The producer is deliberately not imported. Actual frozen AI 1.4 is qualified
as itself; every unchanged declaration is compared individually. New definitions
are checked against accepted lineage, exact source schemas and their own rules.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator, Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.jsonschema import UnknownDialect

from scripts.generate_semantic_contract_assets import (
    digest,
    discovered_dependencies,
    relative_resource_key,
)
from scripts.qualify_ai13_publication import PublicationError, pointer
from scripts import qualify_ai14_publication as historical

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "architecture-interpretation/1.5/"
BASE = "architecture-interpretation/1.4/"
CATALOG = "required-output-derivations"
RECIPES = "identity-representation-recipes"
NAMES = (
    "rules",
    CATALOG,
    CATALOG + ".schema",
    RECIPES,
    RECIPES + ".schema",
    "conformance",
    "conformance.schema",
)
NM = "normalized-model/2.5/contract"
CONTEXT = "architecture-interpretation/1.3/detached-context"
AI14_SCF = "scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7"
NM25_SCF = "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7"
CODES = {
    "/alias_ref": "alias_ref_recipe",
    "/uri": "uri_recipe",
    "/created_at": "created_at_encoding",
}
OPERATIONS = {
    "/alias_ref": "literal_alias_join",
    "/uri": "literal_entity_uri",
    "/created_at": "uuidv7_unix_milliseconds_to_rfc3339_utc",
}
RULE_IDS = [
    "identity-representation.alias-ref",
    "identity-representation.entity-uri",
    "identity-representation.uuidv7-created-at",
]
_snapshot: ContextVar[dict[tuple[Path, str], Any] | None] = ContextVar(
    "ai15_publication_snapshot", default=None
)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PublicationError(code)


def read(root: Path, key: str) -> Any:
    cache = _snapshot.get()
    if cache is not None and (root, key) in cache:
        return cache[root, key]
    if key.endswith("/contract"):
        family, version, _ = key.split("/")
        path = root / (
            f"contracts/semantic-contract/v1.0/definitions/{family}-{version}.json"
            if family
            in {"architecture-interpretation", "authoring-construction", "normalized-model"}
            else f"contracts/{family}/v{version}/contract.json"
        )
    elif key.startswith(PREFIX):
        path = (
            root
            / "contracts/architecture-interpretation/v1.5/resources"
            / (key.removeprefix(PREFIX) + ".json")
        )
    else:
        path = (
            root / "contracts/semantic-contract/v1.0/resources" / (key.replace("/", "-") + ".json")
        )
        if not path.is_file() and len(key.split("/")) == 3:
            family, _, name = key.split("/")
            path = path.with_name(f"{family}-{name}.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if cache is not None:
        cache[root, key] = value
    return value


def qualification(root: Path, key: str, selector: str = "") -> dict[str, str]:
    value = read(root, key)
    pointer(value, selector)
    return {
        "canonical_resource_key": key,
        "content_digest": digest(value),
        "schema_pointer": selector,
    }


def qualified_references(root: Path, value: Any, allowed: set[str]) -> set[str]:
    found: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if {"canonical_resource_key", "content_digest", "schema_pointer"} <= node.keys():
                key = node["canonical_resource_key"]
                require(key in allowed, "unselected_resource_has_no_authority")
                require(
                    node == qualification(root, key, node["schema_pointer"]),
                    "resource_or_selector_qualification_mismatch",
                )
                found.add(key)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return found


def exact_history(root: Path) -> dict[str, Any]:
    from adr_kit.semantic_contract import (
        verify_semantic_contract,
        validate_semantic_resource_closure,
    )

    result = historical.qualify(root)
    ai = read(root, BASE + "contract")
    require(ai["semanticContractFingerprint"] == AI14_SCF, "wrong_inherited_AI_selection")
    for d, expected in ((ai, AI14_SCF), (read(root, NM), NM25_SCF)):
        require(
            d["semanticContractFingerprint"] == expected and verify_semantic_contract(d).success,
            "unqualified_exact_definition",
        )
        bundle = [
            {
                "canonicalResourceKey": e["canonicalResourceKey"],
                "content": read(root, e["canonicalResourceKey"]),
            }
            for e in d["resourceManifest"]
        ]
        require(
            validate_semantic_resource_closure(d, bundle).closure_valid is True,
            "unqualified_exact_closure",
        )
    return result


def schema_registry(root: Path, raw: dict[str, Any]) -> tuple[dict[str, Any], Registry[Any]]:
    """Canonical-key references, evaluated only over sealed supplied documents.

    Resource keys are not filesystem/$id URL paths. The shared key resolver
    selects each target first. Only evaluation views get internal absolute IDs;
    immutable schema bytes and their published $ids are not rewritten.
    """
    documents = {BASE + CATALOG + ".schema": read(root, BASE + CATALOG + ".schema")}
    documents.update({PREFIX + n: v for n, v in raw.items() if n.endswith(".schema")})

    def uri(key: str) -> str:
        return "https://sealed.adr-kit.invalid/" + key

    def view(node: Any, key: str) -> Any:
        if isinstance(node, list):
            return [view(child, key) for child in node]
        if not isinstance(node, dict):
            return node
        result = {k: view(v, key) for k, v in node.items()}
        if "$ref" in node:
            reference = node["$ref"]
            target = relative_resource_key(key, reference) or key
            require(target in documents, "unsealed_companion_reference")
            fragment = reference.partition("#")[2]
            pointer(documents[target], fragment)
            result["$ref"] = uri(target) + "#" + fragment
        return result

    views = {}
    for key, doc in documents.items():
        transformed = view(doc, key)
        transformed.pop("semanticDependencies", None)
        transformed["$id"] = uri(key)
        views[key] = transformed
    return views, Registry().with_resources(
        (uri(k), Resource.from_contents(v)) for k, v in views.items()
    )


def closed_schema(schema: Any) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            require(schema.get("additionalProperties") is False, "open_successor_schema")
        # const/enum payloads are data, not schema syntax.
        for key, child in schema.items():
            if key not in {"const", "enum", "semanticDependencies"}:
                closed_schema(child)
    elif isinstance(schema, list):
        for child in schema:
            closed_schema(child)


def qualify_schemas(root: Path, raw: dict[str, Any]) -> dict[str, Draft202012Validator]:
    views, registry = schema_registry(root, raw)
    validators = {}
    for name in (CATALOG, RECIPES, "conformance"):
        companion = raw[name + ".schema"]
        require(
            companion.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
            "wrong_schema_dialect",
        )
        require(
            companion.get("$id")
            == "https://adr-kit.ste.systems/contracts/architecture-interpretation/v1.5/resources/"
            + name
            + ".schema.json",
            "wrong_companion_identity",
        )
        require(
            companion.get("semanticDependencies") == [BASE + CATALOG + ".schema"],
            "incorrect_companion_dependency",
        )
        closed_schema(companion)
        Draft202012Validator.check_schema(companion)
        validator = Draft202012Validator(views[PREFIX + name + ".schema"], registry=registry)
        errors = list(validator.iter_errors(raw[name]))
        require(not errors, "invalid_" + name + (": " + errors[0].message if errors else ""))
        # Every root property is mandatory, with no extra authority/receipt channel.
        for prop in raw[name]:
            mutated = copy.deepcopy(raw[name])
            mutated.pop(prop)
            require(not validator.is_valid(mutated), "weakened_required_companion_property")
        extra = copy.deepcopy(raw[name])
        extra["forged_authority"] = True
        require(not validator.is_valid(extra), "weakened_closed_companion")
        validators[name] = validator
    # Independently require the schema's genuine vocabulary extension. A schema
    # accepting today's example after losing its constraints is not sufficient.
    old_schema = read(root, BASE + CATALOG + ".schema")
    schema = raw[CATALOG + ".schema"]
    require(
        set(schema["required"])
        == set(old_schema["required"])
        | {"identity_representation_recipes", "inherited_output_authority"},
        "missing_successor_schema_requirement",
    )

    def reference(pointer: str) -> dict[str, str]:
        return {"$ref": "../1.4/required-output-derivations.schema.json#" + pointer}

    for key in old_schema["properties"].keys() - {
        "resource",
        "semanticDependencies",
        "blockers",
        "types",
    }:
        require(
            schema["properties"][key] == reference("/properties/" + key),
            "historical_schema_fragment_rewritten",
        )
    row_pointer = "/properties/types/items"
    entry_pointer = row_pointer + "/properties/outputs/items"
    row_schema = schema["properties"]["types"]["items"]
    old_row = old_schema["properties"]["types"]["items"]
    require(
        row_schema["required"] == old_row["required"]
        and row_schema["properties"].keys() == old_row["properties"].keys(),
        "weakened_type_schema",
    )
    for key in old_row["properties"].keys() - {"outputs"}:
        require(
            row_schema["properties"][key] == reference(row_pointer + "/properties/" + key),
            "historical_type_schema_reinterpreted",
        )
    require(
        row_schema["properties"]["outputs"]["items"]
        == {"oneOf": [reference(entry_pointer), {"$ref": "#/$defs/identity_output"}]},
        "unsupported_or_overlapping_producer_schema",
    )
    producer = schema["$defs"]["identity_producer"]
    require(
        set(producer["required"]) == {"kind", "rule_id", "rule", "inputs", "source_field"}
        and producer["properties"].keys() == set(producer["required"]),
        "open_or_missing_recipe_producer_schema",
    )
    require(
        producer["properties"]["kind"] == {"enum": list(OPERATIONS.values())}
        and producer["properties"]["rule_id"] == {"enum": RULE_IDS}
        and producer["properties"]["source_field"] == {"const": ""},
        "unauthorized_producer_vocabulary",
    )
    require(
        producer["properties"]["rule"] == reference("/properties/field_dispositions")
        and producer["properties"]["inputs"]
        == {
            "type": "array",
            "minItems": 1,
            "maxItems": 2,
            "items": reference("/properties/field_dispositions"),
        },
        "weakened_qualified_input_schema",
    )
    require(
        producer["allOf"]
        == [
            {
                "if": {"properties": {"kind": {"const": op}}},
                "then": {
                    "properties": {
                        "rule_id": {"const": RULE_IDS[i]},
                        "inputs": {"minItems": 2 if i < 2 else 1, "maxItems": 2 if i < 2 else 1},
                    }
                },
            }
            for i, op in enumerate(OPERATIONS.values())
        ],
        "missing_operation_input_cardinality_constraint",
    )
    identity = schema["$defs"]["identity_output"]
    old_entry = old_row["properties"]["outputs"]["items"]
    require(
        set(identity["required"]) == set(old_entry["required"]) | {"producer"}
        and identity["properties"].keys() == set(identity["required"]),
        "missing_recipe_output_constraint",
    )
    for key in set(old_entry["required"]) - {"status", "classification", "semantic_equality"}:
        require(
            identity["properties"][key] == reference(entry_pointer + "/properties/" + key),
            "historical_output_constraint_rewritten",
        )
    require(
        identity["properties"]["status"] == {"const": "QUALIFIED"}
        and identity["properties"]["classification"] == {"const": "representation_only"}
        and identity["properties"]["semantic_equality"]
        == {"const": "original_inputs_once_not_generated_representation"}
        and identity["properties"]["producer"] == {"$ref": "#/$defs/identity_producer"},
        "weakened_recipe_ownership_schema",
    )
    recipe_shape = raw[RECIPES + ".schema"]["properties"]["recipes"]
    require(
        recipe_shape["minItems"] == recipe_shape["maxItems"] == 3
        and len(recipe_shape["items"]["oneOf"]) == 3,
        "missing_or_ambiguous_recipe_schema",
    )
    for shape, recipe in zip(recipe_shape["items"]["oneOf"], raw[RECIPES]["recipes"], strict=True):
        require(
            set(shape["required"]) == set(recipe)
            and shape["properties"] == {k: {"const": v} for k, v in recipe.items()},
            "recipe_schema_not_closed_over_selected_policy",
        )
    return validators


def accepted_lineage(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    # Publication/governance input only. Runtime discovery never reads ADR prose.
    adr = yaml.safe_load(
        next((root / "adrs/logical").glob("ADR-L-0039-*.yaml")).read_text(encoding="utf-8")
    )
    require(
        adr["id"] == "01a17432-c52f-74c0-8485-97832c7671ed"
        and bool(adr.get("governance", {}).get("approved_by")),
        "unqualified_accepted_recipe_lineage",
    )
    historical_adr = yaml.safe_load(
        next((root / "adrs/logical").glob("ADR-L-0019-*.yaml")).read_text(encoding="utf-8")
    )
    return adr, {d["alias_id"]: d["id"] for d in historical_adr["decisions"]}


def qualify_recipes(root: Path, value: dict[str, Any], old: dict[str, Any]) -> None:
    adr, inherited = accepted_lineage(root)
    types = [
        t["semantic_type"]
        for t in old["types"]
        if t["output_branch"] in {"regular", "normative-proposition"}
    ]
    require(value["source_contract"] == "authoring@1.7", "wrong_source_authority")
    require(
        value["destination_authority"]
        == {"definition": qualification(root, NM), "semantic_contract_fingerprint": NM25_SCF},
        "wrong_destination_authority",
    )
    require(
        value["applicability"]
        == {
            "semantic_types": types,
            "output_branches": ["regular", "normative-proposition"],
            "instance_applicability": "Unknown",
            "catalog_membership_grants_root_or_owner": False,
            "custom_CEC_selection": "independently_required_not_registry_invention",
            "shared_identity": "unique_unit_and_producer_before_applicability",
            "normative_proposition_lifecycle": "prohibited",
        },
        "wrong_recipe_branch_or_instance_applicability",
    )
    ai13 = read(root, "architecture-interpretation/1.3/contract")
    require(
        value["context_authority"]
        == {
            "qualification": qualification(root, CONTEXT),
            "governing_family": "architecture-interpretation",
            "governing_version": "1.3",
            "semantic_contract_fingerprint": ai13["semanticContractFingerprint"],
            "namespace_selector": "/architecture_namespace",
            "provider_kind_selector": "/provider_kind",
            "verification": "independently_rederive_selected_context_from_exact_sealed_basis_no_asserted_namespace_or_locator_substitution",
        },
        "unqualified_or_rewritten_provider_context",
    )
    require(
        value["scope"]
        == {
            "authority_only": True,
            "instance_values_produced": False,
            "complete_interpretation": "Unavailable",
            "runtime_capability_enabled": False,
        },
        "publication_not_instance_execution",
    )
    require([r["id"] for r in value["recipes"]] == RULE_IDS, "missing_duplicate_or_unknown_recipe")
    for i, recipe in enumerate(value["recipes"]):
        decision = adr["decisions"][i + 1]
        invariant = adr["invariants"][i + 1]
        spec = yaml.safe_load(decision["rationale"].split("```yaml\n")[1].split("```", 1)[0])
        destination = list(OPERATIONS)[i]
        require(
            spec["destination"] == destination and spec["operation"] == OPERATIONS[destination],
            "unexpected_accepted_operation",
        )
        require(recipe["specification"] == spec, "unauthorized_recipe_operation_or_encoding")
        if i == 0:
            roles = [
                ("authored_alias_id", "alias_id", "required_authored"),
                ("authored_alias_name", "alias_name", "required_authored"),
            ]
        elif i == 1:
            roles = [
                (
                    "qualified_architecture_namespace",
                    "architecture_namespace",
                    "independently_qualified_context",
                ),
                ("established_uuidv7", "id", "established_once_source_bound_lowercase_uuidv7"),
            ]
        else:
            roles = [("established_uuidv7", "id", "established_once_source_bound_lowercase_uuidv7")]
        expected_inputs = [
            {
                "role": role,
                "type": "string",
                (
                    "context_property"
                    if role == "qualified_architecture_namespace"
                    else "source_property"
                ): prop,
                "presence": presence,
            }
            for role, prop, presence in roles
        ]
        require(recipe["input_contract"] == expected_inputs, "wrong_recipe_input_type_or_selector")
        aliases = ["DEC-0093"] if i == 0 else ["DEC-0098", "DEC-0107"] if i == 1 else ["DEC-0099"]
        require(
            recipe["lineage"]
            == {
                "adr_id": adr["id"],
                "decision_id": decision["id"],
                "decision_alias": decision["alias_id"],
                "invariant_id": invariant["id"],
                "invariant_alias": invariant["alias_id"],
                "inherited_decisions": [{"alias": a, "id": inherited[a]} for a in aliases],
            },
            "forged_recipe_lineage",
        )
        require(
            recipe["classification"] == "representation_only"
            and recipe["independent_semantic_owner"] is False
            and recipe["original_semantics"]
            == "preserve_original_authored_aliases_canonical_identity_and_qualified_context_once",
            "second_semantic_owner",
        )
        require(
            recipe["verification"]
            == [
                "independently_verified_sealed_source_basis",
                "original_request_and_established_identity_commitment_where_applicable",
                "exact_selected_source_and_destination_schema",
                "qualified_provider_context_where_required",
                "independent_complete_string_reconstruction",
                "complete_selected_NM_branch_validation",
                "semantic_equality_is_independent_not_a_replay_or_digest_comparison",
            ],
            "missing_independent_representation_or_semantic_proof",
        )
        require(
            recipe["failure_policy"]
            == {
                "independently_invalid_source_or_canonical_identity": "Rejected",
                "conflicting_canonical_identity_or_producer": "Rejected",
                "missing_authority_or_instance_evidence": "Unavailable",
                "missing_or_ambiguous_provider": "Unavailable",
                "valid_uuid_timestamp_outside_selected_representation": "Unavailable",
                "unresolved": "only_independently_established_governed_dependency",
            },
            "wrong_failure_classification",
        )


def qualify_catalog(
    root: Path, new: dict[str, Any], old: dict[str, Any], recipes: dict[str, Any]
) -> dict[str, int]:
    require(
        new.keys()
        == old.keys() | {"identity_representation_recipes", "inherited_output_authority"},
        "unknown_catalog_authority",
    )
    require(
        new["inherited_output_authority"]
        == {
            "catalog": qualification(root, BASE + CATALOG),
            "semantic_contract_fingerprint": AI14_SCF,
            "local_rule_bindings": {
                "literal_string_copy": qualification(root, BASE + CATALOG, "/operation")
            },
        },
        "inherited_local_rule_identity_rewritten",
    )
    for key in old.keys() - {"resource", "semanticDependencies", "blockers", "types"}:
        require(new[key] == old[key], "changed_inherited_catalog_" + key)
    expected_blockers = {
        code: reason for code, reason in old["blockers"].items() if code not in CODES.values()
    }
    require(new["blockers"] == expected_blockers, "missing_or_reinterpreted_remaining_blocker")
    require(
        new["identity_representation_recipes"] == qualification(root, PREFIX + RECIPES),
        "unqualified_recipe_selection",
    )
    expected = {t["semantic_type"]: t for t in old["types"]}
    require(
        Counter(t["semantic_type"] for t in new["types"]) == Counter({t: 1 for t in expected}),
        "missing_duplicate_or_unknown_type",
    )
    branches = {b["branch_id"]: b for b in old["branches"]}
    sources = historical.sealed_schemas(root)
    registry = Registry().with_resources((k, Resource.from_contents(v)) for k, v in sources.items())
    transitions: Counter[str] = Counter()
    for row in new["types"]:
        ty = row["semantic_type"]
        previous = expected[ty]
        require(
            {k: v for k, v in row.items() if k != "outputs"}
            == {k: v for k, v in previous.items() if k != "outputs"},
            "changed_type_branch_source_identity_or_context",
        )
        entries = {e["destination"]: e for e in row["outputs"]}
        before = {e["destination"]: e for e in previous["outputs"]}
        require(
            len(entries) == len(row["outputs"]) and entries.keys() == before.keys(),
            "missing_competing_or_extra_destination",
        )
        branch = branches[row["output_branch"]]
        selected_branch = pointer(
            read(root, branch["schema"]["canonical_resource_key"]),
            branch["schema"]["schema_pointer"],
        )
        eligible = row["output_branch"] in {"regular", "normative-proposition"}
        if eligible:
            require(
                set(CODES) <= {"/" + field for field in selected_branch["required"]},
                "recipe_destination_not_required_by_branch",
            )
        source = row["source_schema"]
        document = read(root, source["canonical_resource_key"])
        shape = pointer(document, source["schema_pointer"])
        for destination, entry in entries.items():
            old_entry = before[destination]
            if not eligible or destination not in CODES:
                require(entry == old_entry, "inherited_declaration_or_semantic_field_changed")
                continue
            require(
                old_entry["status"] == "BLOCKED"
                and old_entry["blocked"]["code"] == CODES[destination],
                "unauthorized_transition",
            )
            unchanged = set(old_entry) - {
                "status",
                "classification",
                "semantic_equality",
                "blocked",
            }
            require(
                set(entry)
                == unchanged | {"status", "classification", "semantic_equality", "producer"},
                "invalid_recipe_entry_shape",
            )
            for key in unchanged:
                require(
                    entry[key] == old_entry[key],
                    "changed_destination_constraints_or_instance_prerequisites",
                )
            require(
                entry["status"] == "QUALIFIED"
                and entry["classification"] == "representation_only"
                and entry["semantic_equality"]
                == "original_inputs_once_not_generated_representation",
                "BLOCKED_promoted_without_recipe_authority",
            )
            i = list(OPERATIONS).index(destination)
            recipe = recipes["recipes"][i]
            producer = entry["producer"]
            inputs = []
            for role in recipe["input_contract"]:
                if "context_property" in role:
                    field = role["context_property"]
                    value = read(root, CONTEXT)[field]
                    require(
                        isinstance(value, str) and bool(value),
                        "invalid_selected_provider_namespace",
                    )
                    inputs.append(qualification(root, CONTEXT, "/" + field))
                else:
                    field = role["source_property"]
                    require(
                        field in shape["required"] and field in shape["properties"],
                        "recipe_input_not_required_source",
                    )
                    selector = source["schema_pointer"] + "/properties/" + field
                    inputs.append(qualification(root, source["canonical_resource_key"], selector))
                    validator = Draft7Validator(
                        {"$ref": document["$id"] + "#" + selector}, registry=registry
                    )
                    nonstrings: tuple[Any, ...] = (None, False, 1, [], {})
                    require(
                        not any(validator.is_valid(v) for v in nonstrings),
                        "recipe_input_not_string",
                    )
                    if field == "id":
                        require(
                            validator.is_valid("00000000-0000-7000-8000-000000000001")
                            and not validator.is_valid("00000000-0000-4000-8000-000000000001")
                            and not validator.is_valid("00000000-0000-7000-A000-000000000001"),
                            "wrong_canonical_identity_schema",
                        )
            require(
                producer
                == {
                    "kind": OPERATIONS[destination],
                    "rule_id": RULE_IDS[i],
                    "rule": qualification(root, PREFIX + RECIPES, f"/recipes/{i}"),
                    "inputs": inputs,
                    "source_field": "",
                },
                "wrong_recipe_producer_kind_rule_or_inputs",
            )
            transitions[destination] += 1
    # Independently cross-check the accepted audit, not merely a fixed count.
    adr, _ = accepted_lineage(root)
    audit = yaml.safe_load(
        adr["decisions"][4]["rationale"].split("```yaml\n")[1].split("```", 1)[0]
    )
    affected = {t["semantic_type"] for t in audit if t["affected_destinations"]}
    require(
        affected
        == {
            t["semantic_type"]
            for t in new["types"]
            if t["output_branch"] in {"regular", "normative-proposition"}
        },
        "accepted_type_scope_disagreement",
    )
    return dict(transitions)


def qualify_oracles(root: Path, value: dict[str, Any], catalog: dict[str, Any]) -> None:
    require(
        value["authority_only"] is True and value["runtime_execution_coverage"] is False,
        "conformance_is_not_execution",
    )
    previous = read(root, BASE + "conformance")
    require(
        value["inherited_conformance"] == qualification(root, BASE + "conformance"),
        "wrong_inherited_conformance",
    )
    expected_review = [
        {
            "id": c["id"],
            "qualification": qualification(root, BASE + "conformance", f"/cases/{i}"),
            "scope": (
                "historical_publication_snapshot_not_successor_absence_requirement"
                if c["id"] == "AI14-085"
                else "unchanged_semantic_obligation_under_actual_inherited_authority"
            ),
        }
        for i, c in enumerate(previous["cases"])
    ]
    require(value["inherited_cases"] == expected_review, "historical_case_relabel_or_scope_loss")
    cases = value["cases"]
    require(
        [c["id"] for c in cases] == [f"AI15-{i+1:03}" for i in range(len(cases))],
        "missing_duplicate_conformance_identity",
    )
    require(
        all(c["coverage"] == "authority_only_not_runtime_execution" for c in cases),
        "false_runtime_coverage",
    )
    actual = {
        (c["semantic_type"], c["fixture"].get("destination"))
        for c in cases
        if c["category"] == "definition_qualification"
    }
    expected = {
        (t["semantic_type"], path)
        for t in catalog["types"]
        if t["output_branch"] in {"regular", "normative-proposition"}
        for path in CODES
    }
    require(
        actual == expected
        and sum(c["category"] == "definition_qualification" for c in cases) == len(expected),
        "incomplete_recipe_type_oracle",
    )
    require(
        {c["semantic_type"] for c in cases if c["category"] == "excluded_branch"}
        == {
            t["semantic_type"]
            for t in catalog["types"]
            if t["output_branch"] not in {"regular", "normative-proposition"}
        },
        "missing_excluded_branch_oracle",
    )
    for c in cases:
        f = c["fixture"]
        category = c["category"]
        assertions = {
            "definition_qualification": "Exact recipe definition qualifies only static authority; all source, identity, branch and contextual instance prerequisites remain independently required.",
            "excluded_branch": "Entity identity representation recipes do not create an entity envelope or independent root for this branch.",
            "timestamp_oracle": "An established canonical UUIDv7's timestamp verifies this exact four-digit RFC3339 millisecond representation; this fixture is not qualified instance evidence.",
            "timestamp_unavailable": "A valid canonical UUIDv7 remains valid but cannot qualify the selected representation; do not truncate, remint or manufacture a string.",
            "alias_oracle": "Qualified authored aliases retain exact contents; the derived recognition string owns no second semantic value.",
            "uri_oracle": "Given independently qualified provider context and identity, the resolver string is literal and opaque; fixtures do not create provider authority.",
            "preservation": "Preserve governed semantic identity, branch and proof distinctions without new roots, owners or public execution capability.",
        }
        fault_categories = {"alias_input", "namespace", "identity", "timestamp", "qualification"}
        fault_assertion = "Independently qualify exact authority, applicability, source/identity/context and complete representation. Known violations are Rejected; missing evidence is Unavailable; no fabricated Unresolved."
        require(
            category in assertions or category in fault_categories, "unknown_conformance_category"
        )
        require(
            c["assertion"]
            == (fault_assertion if category in fault_categories else assertions[category]),
            "changed_normative_conformance_assertion",
        )
        givens = {
            "definition_qualification": [
                "instance_applicability_Unknown",
                "no_instance_value",
                "one_producer_definition",
                "original_semantics_preserved_once",
            ],
            "excluded_branch": ["exact_selected_branch", "no_entity_envelope"],
            "timestamp_oracle": ["established_source_bound_uuidv7", "integer_time_no_clock"],
            "timestamp_unavailable": ["valid_canonical_uuidv7", "no_identity_mutation"],
            "alias_oracle": [
                "exact_qualified_authored_aliases",
                "no_normalization_or_lookup_authority",
            ],
            "uri_oracle": [
                "independently_qualified_provider_context",
                "established_source_bound_uuidv7",
            ],
            "preservation": [
                "authority_conformance_only",
                "instance_applicability_Unknown",
                "no_Constructed",
            ],
        }
        require(
            f["given"]
            == (
                ["retain_independent_diagnostics", "no_partial_instance_result"]
                if category in fault_categories
                else givens[category]
            ),
            "missing_or_forged_oracle_prerequisite",
        )
        if category in fault_categories:
            require(
                c["expected"]
                == (
                    "unavailable"
                    if f["mutation"]
                    in {
                        "missing_provider",
                        "ambiguous_provider",
                        "missing_source_evidence",
                        "missing_context_evidence",
                    }
                    else "rejects"
                ),
                "wrong_negative_oracle_outcome",
            )
        if category in {"excluded_branch", "preservation"}:
            require(
                c["expected"] == ("excludes" if category == "excluded_branch" else "preserves"),
                "wrong_preservation_oracle",
            )
        if c["category"] == "definition_qualification":
            t = next(t for t in catalog["types"] if t["semantic_type"] == c["semantic_type"])
            e = next(e for e in t["outputs"] if e["destination"] == f["destination"])
            require(
                f["source_schema"] == t["source_schema"]
                and f["destination_schema"] == e["destination_schema"]
                and f["operation"] == e["producer"]["kind"]
                and c["expected"] == "conforms",
                "forged_definition_oracle",
            )
        elif c["category"] == "timestamp_oracle":
            # Inverse verification of frozen examples, not conversion of a source instance.
            stamp = datetime.strptime(f["expected_output"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=timezone.utc
            )
            delta = stamp - datetime(1970, 1, 1, tzinfo=timezone.utc)
            milliseconds = (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000
            require(
                milliseconds == f["timestamp_ms"]
                and len(f["expected_output"]) == 24
                and c["expected"] == "conforms",
                "incorrect_frozen_timestamp_example",
            )
        elif c["category"] == "timestamp_unavailable":
            require(
                253402300799999 < f["timestamp_ms"] <= (1 << 48) - 1
                and c["expected"] == "unavailable",
                "wrong_timestamp_representability_oracle",
            )
        elif c["category"] == "alias_oracle":
            require(
                f["expected_output"] == ":".join(f["input_values"]) and c["expected"] == "conforms",
                "changed_alias_oracle",
            )
        elif c["category"] == "uri_oracle":
            require(
                f["expected_output"]
                == "adr://" + f["input_values"][0] + "/entities/" + f["input_values"][1]
                and "independently_qualified_provider_context" in f["given"],
                "changed_uri_or_missing_qualification_oracle",
            )
    required_mutations = {
        "missing_alias",
        "wrong_alias_type",
        "authored_alias_ref_authority",
        "alias_case_folding",
        "alias_trimming",
        "alias_as_foreign_key",
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
        "malformed_uuid",
        "uppercase_uuid",
        "wrong_uuid_version",
        "duplicate_canonical_identity",
        "duplicate_producer",
        "identity_reminting",
        "request_position_as_identity",
        "wrong_fraction_precision",
        "clock_fallback",
        "authored_date_fallback",
        "Git_time_fallback",
        "float_rounding",
        "expanded_year",
        "wrong_timestamp_failure",
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
    }
    found = [c["fixture"]["mutation"] for c in cases if "mutation" in c["fixture"]]
    require(
        set(found) == required_mutations and len(found) == len(set(found)),
        "missing_duplicate_or_unknown_negative_obligation",
    )
    require(
        {c["fixture"]["timestamp_ms"] for c in cases if c["category"] == "timestamp_oracle"}
        == {0, 1, 999, 1000, 86400000, 951782400000, 1609459200000, 253402300799999},
        "missing_timestamp_boundary",
    )
    require(
        {c["fixture"]["timestamp_ms"] for c in cases if c["category"] == "timestamp_unavailable"}
        == {253402300800000, 281474976710655},
        "missing_unrepresentable_timestamp_boundary",
    )
    uri_cases = [c for c in cases if c["category"] == "uri_oracle"]
    require(
        {c["fixture"]["input_values"][0] for c in uri_cases}
        == {"urn:adr-kit:detached-candidate:v1", "provider-a", "provider-b"},
        "missing_provider_or_detached_oracle",
    )
    require(
        len({c["fixture"]["expected_output"] for c in uri_cases}) == len(uri_cases),
        "provider_collision_oracle",
    )


def qualify(
    root: Path = ROOT,
    *,
    published: bool = True,
    candidate_definition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Validate proposed derived metadata before any distribution files are written.
    token = _snapshot.set(
        {(root, PREFIX + "contract"): copy.deepcopy(candidate_definition)}
        if candidate_definition is not None
        else {}
    )
    try:
        return _qualify(root, published=published)
    except (
        KeyError,
        TypeError,
        IndexError,
        ValueError,
        OSError,
        SchemaError,
        UnknownDialect,
    ) as error:
        if isinstance(error, PublicationError):
            raise
        raise PublicationError(
            "incomplete_or_invalid_successor_authority: " + str(error)
        ) from error
    finally:
        _snapshot.reset(token)


def _qualify(root: Path, *, published: bool) -> dict[str, Any]:
    exact_history(root)
    old = read(root, BASE + CATALOG)
    raw = {name: read(root, PREFIX + name) for name in NAMES}
    allowed = (
        {e["canonicalResourceKey"] for e in read(root, BASE + "contract")["resourceManifest"]}
        | {BASE + "contract", NM}
        | {PREFIX + n for n in NAMES}
    )
    for name, value in raw.items():
        if not name.endswith(".schema"):
            require(value.get("resource") == PREFIX + name, "wrong_successor_resource_identity")
        require(set(value.get("semanticDependencies", [])) <= allowed, "unselected_dependency")
        found = qualified_references(root, value, allowed)
        require(
            found <= set(value.get("semanticDependencies", [])),
            "missing_qualified_resource_dependency",
        )
        require(
            discovered_dependencies(PREFIX + name, value) <= allowed, "unsealed_schema_dependency"
        )
    qualify_schemas(root, raw)
    qualify_recipes(root, raw[RECIPES], old)
    transitions = qualify_catalog(root, raw[CATALOG], old, raw[RECIPES])
    qualify_oracles(root, raw["conformance"], raw[CATALOG])
    rules = raw["rules"]
    require(
        set(rules)
        == {
            "resource",
            "semanticDependencies",
            "inherits",
            "destination_authority",
            "required_output_catalog",
            "recipe_authority",
            "required_output_coverage",
            "inherited_authority",
            "representation_verification",
            "semantic_equality",
            "instance_applicability",
            "outcome_precedence",
            "public_boundary",
        },
        "unknown_successor_rule_authority",
    )
    require(
        rules["inherited_authority"]
        == "actual_AI_1_3_and_AI_1_4_resource_keys_digests_SCFs_and_rule_identities_retained_no_version_rewriting"
        and rules["representation_verification"]
        == "independent_complete_reconstruction_from_sealed_source_established_identity_exact_rule_and_context_not_asserted_flags_or_replay"
        and rules["semantic_equality"]
        == "original_semantic_values_identity_context_order_and_multiplicity_once_not_generated_representation_ownership",
        "weakened_inherited_or_independent_proof_rule",
    )
    require(
        rules["inherits"]
        == {
            "definition": qualification(root, BASE + "contract"),
            "semantic_contract_fingerprint": AI14_SCF,
            "overrides": [
                "identity_representation_required_output_definitions",
                "representation_only_identity_recipes",
            ],
        },
        "unapproved_inherited_semantic_delta",
    )
    require(
        rules["destination_authority"]
        == {"definition": qualification(root, NM), "semantic_contract_fingerprint": NM25_SCF}
        and rules["required_output_catalog"] == qualification(root, PREFIX + CATALOG)
        and rules["recipe_authority"] == qualification(root, PREFIX + RECIPES),
        "unqualified_successor_selection",
    )
    require(
        rules["required_output_coverage"] == old["coverage"]
        and rules["instance_applicability"] == "Unknown"
        and rules["outcome_precedence"] == ["Rejected", "Unavailable", "Unresolved"],
        "changed_coverage_or_status_distinction",
    )
    require(
        rules["public_boundary"]
        == {
            "enabled_by_publication": False,
            "runtime_execution_coverage": False,
            "complete_interpretation": "Unavailable",
            "semantic_equivalent": False,
            "Constructed": False,
            "publication_changes_current_selection": False,
        },
        "publication_enables_execution",
    )
    expected_dependencies = {
        e["canonicalResourceKey"] for e in read(root, BASE + "contract")["resourceManifest"]
    } | {BASE + "contract", NM, PREFIX + CATALOG, PREFIX + RECIPES}
    require(
        set(rules["semanticDependencies"]) == expected_dependencies,
        "incomplete_inherited_closure_declaration",
    )
    require(
        set(raw[CATALOG]["semanticDependencies"])
        == (set(old["semanticDependencies"]) - {BASE + CATALOG + ".schema"})
        | {PREFIX + CATALOG + ".schema", PREFIX + RECIPES, CONTEXT, BASE + CATALOG},
        "wrong_catalog_dependency_edge",
    )
    source_keys = {t["source_schema"]["canonical_resource_key"] for t in old["types"]}
    require(
        set(raw[RECIPES]["semanticDependencies"])
        == source_keys
        | {
            PREFIX + RECIPES + ".schema",
            CONTEXT,
            NM,
            "normalized-model/2.5/schema/normalized-entity.schema",
        },
        "wrong_recipe_schema_or_authority_dependency",
    )
    require(
        set(raw["conformance"]["semanticDependencies"])
        == source_keys
        | {
            BASE + "conformance",
            PREFIX + "conformance.schema",
            PREFIX + "rules",
            PREFIX + CATALOG,
            PREFIX + RECIPES,
            "normalized-model/2.5/schema/normalized-entity.schema",
        },
        "wrong_conformance_dependency",
    )
    if published:
        from adr_kit.semantic_contract import (
            verify_semantic_contract,
            validate_semantic_resource_closure,
        )

        definition = read(root, PREFIX + "contract")
        require(
            definition["semanticContractFamily"] == "architecture-interpretation"
            and definition["semanticContractVersion"] == "1.5"
            and definition["fingerprintScheme"] == "scf:v1:sha256",
            "wrong_exact_contract_identity",
        )
        require(
            definition["frozenNormativeConformanceResources"] == [PREFIX + "conformance"],
            "wrong_frozen_conformance",
        )
        manifest = definition["resourceManifest"]
        roles = {
            entry["canonicalResourceKey"]: entry["role"]
            for entry in read(root, BASE + "contract")["resourceManifest"]
        }
        roles.update({BASE + "contract": "normative-definition", NM: "normative-definition"})
        roles.update(
            {
                PREFIX
                + name: (
                    "source-contract-schema"
                    if name.endswith(".schema")
                    else (
                        "interpretation-conformance"
                        if name == "conformance"
                        else "interpretation-rule"
                    )
                )
                for name in NAMES
            }
        )
        require(
            len(manifest) == len(allowed)
            and {m["canonicalResourceKey"] for m in manifest} == allowed,
            "incomplete_extra_or_duplicate_closure",
        )
        for m in manifest:
            key = m["canonicalResourceKey"]
            require(m["role"] == roles[key], "incorrect_manifest_resource_role")
            content = read(root, key)
            require(m["contentDigest"] == digest(content), "changed_resource_digest")
            expected_deps = [
                {"canonicalResourceKey": dep, "contentDigest": digest(read(root, dep))}
                for dep in sorted(discovered_dependencies(key, content))
            ]
            require(m["dependencies"] == expected_deps, "inconsistent_manifest_dependency_edge")
        bundle = [
            {
                "canonicalResourceKey": m["canonicalResourceKey"],
                "content": read(root, m["canonicalResourceKey"]),
            }
            for m in manifest
        ]
        require(
            verify_semantic_contract(definition).success is True
            and validate_semantic_resource_closure(definition, bundle).closure_valid is True,
            "invalid_SCF_or_resource_closure",
        )
    counts = Counter(e["status"] for t in raw[CATALOG]["types"] for e in t["outputs"])
    return {
        "semantic_types": len(raw[CATALOG]["types"]),
        "output_branches": len(raw[CATALOG]["branches"]),
        "output_accounting": dict(counts),
        "transitions": transitions,
        "literal_string_copy_rules": sum(
            e.get("producer", {}).get("kind") == "literal_string_copy"
            for t in raw[CATALOG]["types"]
            for e in t["outputs"]
        ),
        "active_blocker_categories": len(raw[CATALOG]["blockers"]),
        "conformance_cases": len(raw["conformance"]["cases"]),
        "instance_applicability": "Unknown",
        "complete_interpretation": "Unavailable",
        "runtime_execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(qualify(), indent=2))
