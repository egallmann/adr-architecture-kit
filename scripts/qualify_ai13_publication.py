"""Publication-only qualification of AI 1.3 catalogs; no source interpretation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin

from jsonschema import Draft7Validator, Draft202012Validator
from referencing import Registry, Resource

from scripts.generate_semantic_contract_assets import digest

ROOT = Path(__file__).resolve().parents[1]
AI = "architecture-interpretation/1.3/"
NM_SCF = "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7"
BUILTINS = frozenset(
    "boundary capability component contract data_flow decision evidence_expectation gap "
    "implementation_decision interface invariant system system_boundary".split()
)
ROOT_TYPES = ("logical", "physical-system", "physical-component")
RESOURCE_NAMES = (
    "source-mapping-1.7-to-2.5",
    "field-dispositions-1.7-to-2.5",
    "field-dispositions.schema",
    "detached-context",
    "rules",
    "conformance.schema",
    "conformance",
    "lifecycle-ownership",
    "lifecycle-ownership.schema",
    "lifecycle-provenance.schema",
    "contextual-facts",
    "contextual-facts.schema",
)


def retarget_ai12(value: Any) -> Any:
    """Version qualification changes only; used to guard inherited authority."""
    if isinstance(value, list):
        return [retarget_ai12(child) for child in value]
    if isinstance(value, dict):
        result = {key: retarget_ai12(child) for key, child in value.items()}
        if (
            value.get("contract_family") == "normalized-model"
            and value.get("contract_version") == "2.4"
        ):
            result["contract_version"] = "2.5"
        if (
            value.get("contract_family") == "architecture-interpretation"
            and value.get("contract_version") == "1.2"
        ):
            result["contract_version"] = "1.3"
        return result
    if isinstance(value, str):
        for old, new in (
            ("architecture-interpretation/1.2", "architecture-interpretation/1.3"),
            ("architecture-interpretation@1.2", "architecture-interpretation@1.3"),
            ("Architecture Interpretation 1.2", "Architecture Interpretation 1.3"),
            ("Interpretation 1.2", "Interpretation 1.3"),
            ("AI 1.2 and NM 2.4", "AI 1.3 and NM 2.5"),
            ("/v1.2/", "/v1.3/"),
            ("normalized-model/2.4", "normalized-model/2.5"),
            ("normalized-model@2.4", "normalized-model@2.5"),
            ("Normalized Model 2.4", "Normalized Model 2.5"),
            ("1.7-to-2.4", "1.7-to-2.5"),
        ):
            value = value.replace(old, new)
        for name in ("source-decoding-1.7", "legacy-compatibility"):
            value = value.replace(AI + name, "architecture-interpretation/1.2/" + name)
    return value


class PublicationError(ValueError):
    """A successor publication prerequisite could not be established."""


def read(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def pointer(document: Any, selector: str) -> Any:
    if selector and not selector.startswith("/"):
        raise PublicationError("invalid_schema_selector")
    try:
        for token in selector.split("/")[1:] if selector else []:
            token = token.replace("~1", "/").replace("~0", "~")
            document = document[int(token)] if isinstance(document, list) else document[token]
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise PublicationError("unresolved_schema_selector") from exc
    return document


def source_documents(root: Path) -> dict[str, Any]:
    return {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in (root / "schema/authoring/v1.7").glob("*.json")
    }


def source_qualification(documents: dict[str, Any], name: str, selector: str) -> dict[str, Any]:
    pointer(documents[name], selector)
    return {
        "canonical_resource_key": "authoring/1.7/schema/" + name.removesuffix(".json"),
        "content_digest": digest(documents[name]),
        "schema_pointer": selector,
    }


def derive_ownership_rows(root: Path) -> list[dict[str, Any]]:
    """Enumerate definition occurrences, not runtime owners or canonical identities."""
    documents = source_documents(root)
    rows: list[dict[str, Any]] = []

    def visit(
        node: Any,
        filename: str,
        selector: str,
        instance: str,
        declaring: str,
        parent: str,
        root_filename: str,
        parent_schema: dict[str, Any],
        chain: list[dict[str, Any]],
        seen: frozenset[tuple[str, str]],
    ) -> None:
        if not isinstance(node, dict):
            return
        if any(key in node for key in ("anyOf", "oneOf", "if", "then", "else")):
            raise PublicationError("conditional_source_ownership_requires_qualification")
        if "$ref" in node:
            reference = node["$ref"]
            if not isinstance(reference, str) or ":" in reference or reference.startswith("/"):
                raise PublicationError("unsealed_source_reference")
            location, fragment = urldefrag(reference)
            target_file = location or filename
            if target_file not in documents:
                raise PublicationError("missing_source_schema")
            if (target_file, fragment) in seen:
                raise PublicationError("recursive_source_ownership")
            target = pointer(documents[target_file], fragment)
            name = fragment.removeprefix("/definitions/")
            next_chain = chain
            if target_file == "adr-common.schema.json" and name in BUILTINS:
                child_schema = source_qualification(documents, target_file, fragment)
                next_chain = [*chain, source_qualification(documents, filename, selector)]
                rule_id = (
                    "declaring-lifecycle."
                    + declaring.replace("/", "-")
                    + "."
                    + (instance.strip("/").replace("/*", "").replace("/", "."))
                )
                rows.append(
                    {
                        "rule_id": rule_id,
                        "declaring_adr_semantic_type": declaring,
                        "parent_semantic_type": parent,
                        "child_semantic_type": "entity/" + name,
                        "source_schema": source_qualification(documents, root_filename, ""),
                        "parent_schema": parent_schema,
                        "child_schema": child_schema,
                        "ownership_schema_path": next_chain,
                        "source_instance_pattern": instance,
                        "declaring_adr_identity_selector": "/id",
                        "parent_identity_selector": "/id",
                        "child_identity_selector": "/id",
                        "status_semantic_field_key": declaring + "#/status",
                        "status_source_authority": {
                            "family": "authoring",
                            "version": "1.7",
                            **source_qualification(documents, root_filename, "/properties/status"),
                        },
                        "governing_rule": "literal_declaring_adr_status",
                        "value_destination": "/lifecycle_stage",
                        "canonical_identity": "preserve_established_uuidv7",
                        "shared_system_descriptor": (
                            "reuse_existing_semantic_unit_if_same_canonical_identity"
                            if name == "system"
                            else "not_applicable"
                        ),
                    }
                )
                parent, parent_schema = "entity/" + name, child_schema
            visit(
                target,
                target_file,
                fragment,
                instance,
                declaring,
                parent,
                root_filename,
                parent_schema,
                next_chain,
                seen | {(target_file, fragment)},
            )
            return
        for key, value in node.get("properties", {}).items():
            escaped = key.replace("~", "~0").replace("/", "~1")
            visit(
                value,
                filename,
                selector + "/properties/" + escaped,
                instance + "/" + escaped,
                declaring,
                parent,
                root_filename,
                parent_schema,
                chain,
                seen,
            )
        if isinstance(node.get("items"), dict):
            visit(
                node["items"],
                filename,
                selector + "/items",
                instance + "/*",
                declaring,
                parent,
                root_filename,
                parent_schema,
                chain,
                seen,
            )
        for index, value in enumerate(node.get("allOf", [])):
            visit(
                value,
                filename,
                selector + "/allOf/" + str(index),
                instance,
                declaring,
                parent,
                root_filename,
                parent_schema,
                chain,
                seen,
            )

    for kind in ROOT_TYPES:
        filename = "adr-" + kind + ".schema.json"
        root_schema = source_qualification(documents, filename, "")
        visit(
            documents[filename],
            filename,
            "",
            "",
            "adr/" + kind,
            "adr/" + kind,
            filename,
            root_schema,
            [],
            frozenset(),
        )
    rows.sort(key=lambda row: row["rule_id"])
    if len(rows) != len({row["rule_id"] for row in rows}):
        raise PublicationError("duplicate_ownership_selector")
    if {row["child_semantic_type"] for row in rows} != {"entity/" + n for n in BUILTINS}:
        raise PublicationError("incomplete_builtin_selector_coverage")
    return rows


def registry_for(documents: list[dict[str, Any]]) -> Registry[Any]:
    # Registry's default retriever fails with NoSuchResource; no network/ambient lookup.
    return Registry().with_resources(
        (document["$id"], Resource.from_contents(document)) for document in documents
    )


def _resolve(reference: str, base: str, store: dict[str, Any]) -> tuple[Any, str]:
    uri, fragment = urldefrag(urljoin(base, reference))
    if uri not in store:
        raise PublicationError("unresolved_sealed_schema_reference")
    return pointer(store[uri], fragment), uri


def _property_constraints(
    node: dict[str, Any],
    field: str,
    base: str,
    store: dict[str, Any],
    seen: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if "$ref" in node:
        target, uri = _resolve(node["$ref"], base, store)
        identity = urljoin(base, node["$ref"])
        if identity in seen:
            raise PublicationError("recursive_field_domain")
        return _property_constraints(target, field, uri, store, seen | {identity})
    if field in node.get("properties", {}):
        value = node["properties"][field]
        result.append(_absolute_references(value, base))
    for value in node.get("allOf", []):
        result.extend(_property_constraints(value, field, base, store, seen))
    # A conditional object constraint may depend on unprovided sibling values.
    # Prove independence or fail; never guess a branch from a partial instance.
    for key in ("oneOf", "anyOf", "not", "if", "then", "else", "dependencies"):
        if key in node and _mentions_field(node[key], field, base, store, seen):
            raise PublicationError("ambiguous_field_domain_branch")
    return result


def _absolute_references(value: Any, base: str) -> Any:
    if isinstance(value, list):
        return [_absolute_references(child, base) for child in value]
    if isinstance(value, dict):
        return {
            key: urljoin(base, child) if key == "$ref" else _absolute_references(child, base)
            for key, child in value.items()
        }
    return value


def _mentions_field(
    value: Any, field: str, base: str, store: dict[str, Any], seen: frozenset[str]
) -> bool:
    if isinstance(value, dict):
        if "$ref" in value:
            identity = urljoin(base, value["$ref"])
            if identity in seen:
                raise PublicationError("recursive_field_domain")
            target, uri = _resolve(value["$ref"], base, store)
            if _mentions_field(target, field, uri, store, seen | {identity}):
                return True
        if field in value.get("properties", {}) or field in value.get("required", []):
            return True
        return any(_mentions_field(child, field, base, store, seen) for child in value.values())
    if isinstance(value, list):
        return any(_mentions_field(child, field, base, store, seen) for child in value)
    return False


def _finite_candidates(
    node: Any,
    base: str,
    store: dict[str, Any],
    seen: frozenset[str] = frozenset(),
) -> set[str]:
    if not isinstance(node, dict):
        raise PublicationError("unsupported_field_domain_schema")
    supported = {
        "$ref",
        "type",
        "enum",
        "const",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "if",
        "then",
        "else",
        "title",
        "description",
        "$comment",
        "default",
        "examples",
    }
    if set(node) - supported:
        raise PublicationError("unsupported_field_domain_keyword")
    if "$ref" in node:
        identity = urljoin(base, node["$ref"])
        if identity in seen:
            raise PublicationError("recursive_field_domain")
        target, uri = _resolve(node["$ref"], base, store)
        return _finite_candidates(target, uri, store, seen | {identity})
    values = list(node.get("enum", []))
    if "const" in node:
        values.append(node["const"])
    if any(not isinstance(value, str) for value in values):
        raise PublicationError("non_string_lifecycle_domain")
    found = set(values)
    for key in ("allOf", "anyOf", "oneOf"):
        for child in node.get(key, []):
            child_values = _finite_candidates(child, base, store, seen)
            if key != "allOf" and not child_values:
                raise PublicationError("unbounded_field_domain_branch")
            found.update(child_values)
    for key in ("not", "if", "then", "else"):
        if key in node:
            _finite_candidates(node[key], base, store, seen)
    return found


def prove_enum_inclusion(
    source_document: dict[str, Any],
    destination_document: dict[str, Any],
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prove finite schema-domain inclusion, never convert lifecycle values."""
    store = {document["$id"]: document for document in documents}
    registry = registry_for(documents)
    constraints = _property_constraints(source_document, "status", source_document["$id"], store)
    if not constraints:
        raise PublicationError("missing_source_status_selector")
    source = {"allOf": constraints}
    candidates = _finite_candidates(source, source_document["$id"], store)
    if not candidates:
        raise PublicationError("unestablished_finite_source_domain")
    source_validator = Draft7Validator(source, registry=registry)
    # Validate every intersection constraint, including inherited allOf members.
    validators = [Draft7Validator(constraint, registry=registry) for constraint in constraints]
    domain = sorted(
        value
        for value in candidates
        if source_validator.is_valid(value)
        and all(validator.is_valid(value) for validator in validators)
    )
    if not domain:
        raise PublicationError("conflicting_source_domain_constraints")
    branches = destination_document.get("oneOf", [])
    selected = [
        (index, branch)
        for index, branch in enumerate(branches)
        if "lifecycle_stage" in branch.get("properties", {})
    ]
    if len(selected) != 1:
        raise PublicationError("ambiguous_destination_branch")
    index, branch = selected[0]
    target_constraints = _property_constraints(
        branch,
        "lifecycle_stage",
        destination_document["$id"],
        store,
        frozenset({"selected_branch"}),
    )
    target = {"allOf": target_constraints}
    _finite_candidates(target, destination_document["$id"], store)
    target_validator = Draft7Validator(target, registry=registry)
    if any(not target_validator.is_valid(value) for value in domain):
        raise PublicationError("source_value_outside_destination_domain")
    return {
        "source_domain": domain,
        "destination_selector": f"/oneOf/{index}/properties/lifecycle_stage",
        "unchanged_values_accepted": True,
    }


def qualify_publication(root: Path = ROOT) -> dict[str, Any]:
    raw = {
        name: read(root, f"contracts/architecture-interpretation/v1.3/resources/{name}.json")
        for name in RESOURCE_NAMES
    }
    documents = source_documents(root)
    nm = read(root, "schema/normalized-model/v2.5/normalized-entity.schema.json")
    nm_definition = read(
        root, "contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json"
    )
    if nm_definition["semanticContractFingerprint"] != NM_SCF:
        raise PublicationError("wrong_normalized_authority")
    for name in (
        "source-mapping-1.7-to-2.5",
        "field-dispositions-1.7-to-2.5",
        "field-dispositions.schema",
        "detached-context",
    ):
        predecessor = read(
            root,
            "contracts/architecture-interpretation/v1.2/resources/"
            + name.replace("to-2.5", "to-2.4")
            + ".json",
        )
        if raw[name] != retarget_ai12(predecessor):
            raise PublicationError("unapproved_inherited_semantic_delta: " + name)
    old_rules = retarget_ai12(
        read(root, "contracts/architecture-interpretation/v1.2/resources/rules.json")
    )
    new_rules = raw["rules"]
    for key, value in old_rules.items():
        if key not in {"semanticDependencies", "aggregation"} and new_rules.get(key) != value:
            raise PublicationError("unapproved_inherited_rule_delta: " + key)
    for key, value in old_rules["aggregation"].items():
        if key != "standalone_fragments" and new_rules["aggregation"].get(key) != value:
            raise PublicationError("unapproved_aggregation_delta")
    domain = documents["types.schema.json"]["definitions"]["status"]["enum"]
    if new_rules["lifecycle_authority"]["authored_to_normalized"] != {
        value: value for value in domain
    }:
        raise PublicationError("non_literal_lifecycle_mapping")
    destination = {
        "canonical_resource_key": "normalized-model/2.5/schema/normalized-entity.schema",
        "content_digest": digest(nm),
        "schema_pointer": "/oneOf/0/properties/lifecycle_stage",
    }
    if raw["lifecycle-ownership"]["destination_schema"] != destination:
        raise PublicationError("wrong_lifecycle_destination_qualification")
    if new_rules["lifecycle_authority"]["destination_schema"] != destination:
        raise PublicationError("wrong_root_lifecycle_destination")
    if new_rules["lifecycle_authority"]["source_status_schema"] != source_qualification(
        documents, "types.schema.json", "/definitions/status"
    ):
        raise PublicationError("wrong_root_status_source_authority")
    if new_rules["lifecycle_authority"]["output_qualification"] != {
        "family": "normalized-model",
        "version": "2.5",
        "semantic_contract_fingerprint": NM_SCF,
    }:
        raise PublicationError("wrong_root_output_authority")
    facts = raw["contextual-facts"]["facts"]
    if len(facts) != 1 or facts[0]["semantic_field_key"] != "context/declaring_adr_lifecycle#":
        raise PublicationError("missing_or_additional_contextual_fact")
    fact = facts[0]
    if (
        fact["semantic_identity"] != "normalized_child_canonical_UUIDv7"
        or fact["normalized_carrier"] != "/metadata/ai_lifecycle_provenance"
        or fact["carrier_schema"] != AI + "lifecycle-provenance.schema"
        or fact["first_class_value_destination"] != "/lifecycle_stage"
        or fact["semantic_equality_fields"]
        != [
            "declaring_adr_id",
            "declaring_adr_semantic_type",
            "status_semantic_field_key",
            "ownership_rule.rule_id",
        ]
    ):
        raise PublicationError("wrong_contextual_semantic_binding")
    carrier = raw["lifecycle-provenance.schema"]
    carrier_fields = {
        "declaring_adr_id",
        "declaring_adr_semantic_type",
        "status_semantic_field_key",
        "status_source_authority",
        "ownership_rule",
        "value_destination",
    }
    if (
        set(carrier["properties"]) != carrier_fields
        or set(carrier["required"]) != carrier_fields
        or carrier.get("additionalProperties") is not False
    ):
        raise PublicationError("incomplete_or_open_lifecycle_carrier")
    if carrier["properties"]["ownership_rule"]["properties"]["semantic_contract_fingerprint"] != {
        "type": "string",
        "pattern": "^scf:v1:sha256:[0-9a-f]{64}$",
    }:
        raise PublicationError("self_bound_or_unqualified_ownership_authority")
    schema_documents = [value for value in raw.values() if "$schema" in value]
    registry = registry_for([*schema_documents, *documents.values(), nm])
    store = {document["$id"]: document for document in [*schema_documents, *documents.values(), nm]}

    def check_references(value: Any, base: str) -> None:
        if isinstance(value, dict):
            if "$ref" in value:
                _resolve(value["$ref"], base, store)
            for child in value.values():
                check_references(child, base)
        elif isinstance(value, list):
            for child in value:
                check_references(child, base)

    for document in schema_documents:
        Draft202012Validator.check_schema(document)
        check_references(document, document["$id"])
    for name in ("lifecycle-ownership", "contextual-facts", "conformance"):
        errors = list(
            Draft202012Validator(raw[name + ".schema"], registry=registry).iter_errors(raw[name])
        )
        if errors:
            raise PublicationError("invalid_" + name + ": " + errors[0].message)
    errors = list(
        Draft202012Validator(raw["field-dispositions.schema"], registry=registry).iter_errors(
            raw["field-dispositions-1.7-to-2.5"]
        )
    )
    if errors:
        raise PublicationError("invalid_field_dispositions: " + errors[0].message)
    expected = derive_ownership_rows(root)
    actual = sorted(raw["lifecycle-ownership"]["rows"], key=lambda row: row["rule_id"])
    if sorted(actual, key=lambda row: row["rule_id"]) != expected:
        raise PublicationError("ownership_catalog_disagrees_with_exact_source_schema")
    proofs = []
    for kind in ROOT_TYPES:
        proof = prove_enum_inclusion(
            documents[f"adr-{kind}.schema.json"], nm, [*documents.values(), nm]
        )
        proofs.append({"semantic_type": "adr/" + kind, **proof})
    for row in actual:
        kind = row["declaring_adr_semantic_type"].split("/")[1]
        proof = prove_enum_inclusion(
            documents[f"adr-{kind}.schema.json"], nm, [*documents.values(), nm]
        )
        proofs.append(
            {"rule_id": row["rule_id"], "semantic_type": row["child_semantic_type"], **proof}
        )
    return {
        "ownership_selectors": len(actual),
        "built_in_types": len(BUILTINS),
        "enum_domain_proofs": proofs,
        "runtime_interpretation": False,
    }


if __name__ == "__main__":
    print(json.dumps(qualify_publication(), indent=2))
