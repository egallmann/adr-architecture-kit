"""Independently qualify AI 1.4 publication; never interpret source instances."""

from __future__ import annotations

import json
from collections import Counter
from contextvars import ContextVar
from pathlib import Path
from typing import Any, cast
from urllib.parse import urldefrag, urljoin

from jsonschema import Draft7Validator, Draft202012Validator
from referencing import Registry, Resource

from scripts.generate_semantic_contract_assets import digest
from scripts.qualify_ai13_publication import PublicationError, pointer

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "architecture-interpretation/1.4/"
BASE = "architecture-interpretation/1.3/"
NAMES = (
    "rules",
    "required-output-derivations",
    "required-output-derivations.schema",
    "conformance",
    "conformance.schema",
)
CATALOG = "required-output-derivations"
SCFS = {
    (
        "architecture-interpretation",
        "1.3",
    ): "scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167",
    (
        "authoring-construction",
        "1.3",
    ): "scf:v1:sha256:5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49",
    (
        "normalized-model",
        "2.5",
    ): "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7",
}
_snapshot: ContextVar[dict[tuple[Path, str], Any] | None] = ContextVar(
    "ai14_publication_snapshot", default=None
)
_digests: ContextVar[dict[tuple[Path, str], str] | None] = ContextVar(
    "ai14_publication_digests", default=None
)


def read(root: Path, key: str) -> Any:
    snapshot = _snapshot.get()
    if snapshot is not None and (root, key) in snapshot:
        return snapshot[(root, key)]
    if key.startswith(PREFIX):
        path = (
            root
            / "contracts/architecture-interpretation/v1.4/resources"
            / (key.removeprefix(PREFIX) + ".json")
        )
    elif key == BASE + "contract":
        path = (
            root
            / "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.3.json"
        )
    else:
        path = (
            root / "contracts/semantic-contract/v1.0/resources" / (key.replace("/", "-") + ".json")
        )
        if not path.is_file() and len(key.split("/")) == 3:
            family, _, name = key.split("/")
            path = path.with_name(f"{family}-{name}.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if snapshot is not None:
        snapshot[(root, key)] = value
    return value


def qualification(root: Path, key: str, selector: str = "") -> dict[str, str]:
    value = read(root, key)
    pointer(value, selector)
    cache = _digests.get()
    if cache is None:
        content_digest = digest(value)
    else:
        if (root, key) not in cache:
            cache[(root, key)] = digest(value)
        content_digest = cache[(root, key)]
    return {
        "canonical_resource_key": key,
        "content_digest": content_digest,
        "schema_pointer": selector,
    }


def resolve(root: Path, selected: dict[str, str]) -> Any:
    actual = qualification(root, selected["canonical_resource_key"], selected["schema_pointer"])
    if selected != actual:
        raise PublicationError("resource_or_selector_qualification_mismatch")
    return pointer(read(root, selected["canonical_resource_key"]), selected["schema_pointer"])


def expected_branch(mapping: dict[str, Any]) -> str:
    return {
        "normative_proposition": "normative-proposition",
        "canonical": "canonical-relationship",
        "compatibility": "compatibility-relationship",
        "component-reference": "owner-local-value",
        "normative_force": "proposition-owned-value",
    }.get(mapping["output"], "regular")


def destination_schema(root: Path, branch: dict[str, Any], destination: str) -> dict[str, str]:
    """Resolve a declared instance destination within its exact NM schema branch."""
    selected = branch["schema"]
    key, selector = selected["canonical_resource_key"], selected["schema_pointer"]
    node = resolve(root, selected)
    if branch["branch_id"] == "proposition-owned-value":
        return cast(dict[str, str], selected)
    if destination.startswith("/metadata/"):
        destination = "/metadata" if branch["branch_id"] != "owner-local-value" else ""
    for token in destination.split("/")[1:] if destination else []:
        while "$ref" in node:
            from scripts.generate_semantic_contract_assets import relative_resource_key

            reference = node["$ref"]
            key = relative_resource_key(key, reference) or key
            selector = urldefrag(reference)[1]
            node = pointer(read(root, key), selector)
        if token not in node.get("properties", {}):
            raise PublicationError("destination_not_in_selected_schema_branch")
        selector += "/properties/" + token.replace("~", "~0").replace("/", "~1")
        node = node["properties"][token]
    return qualification(root, key, selector)


def required_subdestinations(
    root: Path, selected: dict[str, str], destination: str
) -> list[dict[str, Any]]:
    """A complete typed parent producer owns nested required fields, once."""
    result = []

    def visit(key: str, selector: str, path: str, seen: frozenset[tuple[str, str]]) -> None:
        node = pointer(read(root, key), selector)
        if "$ref" in node:
            from scripts.generate_semantic_contract_assets import relative_resource_key

            target = relative_resource_key(key, node["$ref"]) or key
            fragment = urldefrag(node["$ref"])[1]
            if (target, fragment) in seen:
                raise PublicationError("recursive_output_value_schema")
            visit(target, fragment, path, seen | {(target, fragment)})
        for name in node.get("required", []):
            child = selector + "/properties/" + name.replace("~", "~0").replace("/", "~1")
            child_path = path + "/" + name
            result.append(
                {
                    "destination": child_path,
                    "schema": qualification(root, key, child),
                    "coverage": "same_complete_parent_value_no_second_producer",
                }
            )
            visit(key, child, child_path, seen)

    visit(selected["canonical_resource_key"], selected["schema_pointer"], destination, frozenset())
    return result


def schema_audit(root: Path, key: str, selector: str) -> list[dict[str, Any]]:
    """Inventory all required/conditional branches, including nested $ref targets.

    Conditions remain exact schema constraints. This is not a partial-instance
    branch guess or a source interpreter. A future materializer must evaluate
    these constraints against its complete independently established candidate.
    """
    result: list[dict[str, Any]] = []

    def visit(node: Any, resource: str, path: str, seen: frozenset[tuple[str, str]]) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                from scripts.generate_semantic_contract_assets import relative_resource_key

                reference = node["$ref"]
                target = relative_resource_key(resource, reference) or resource
                fragment = urldefrag(reference)[1]
                if (target, fragment) in seen:
                    raise PublicationError("recursive_schema_requirement")
                visit(
                    pointer(read(root, target), fragment),
                    target,
                    fragment,
                    seen | {(target, fragment)},
                )
            for keyword in (
                "required",
                "if",
                "then",
                "else",
                "not",
                "oneOf",
                "anyOf",
                "allOf",
                "dependencies",
                "dependentRequired",
            ):
                if keyword in node:
                    result.append(
                        {
                            "schema": qualification(root, resource, path + "/" + keyword),
                            "keyword": keyword,
                            "constraint": node[keyword],
                        }
                    )
            for name, value in node.items():
                if name != "$ref":
                    visit(
                        value,
                        resource,
                        path + "/" + name.replace("~", "~0").replace("/", "~1"),
                        seen,
                    )
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, resource, path + "/" + str(index), seen)

    visit(pointer(read(root, key), selector), key, selector, frozenset({(key, selector)}))
    unique = {json.dumps(row, sort_keys=True): row for row in result}
    return [unique[key] for key in sorted(unique)]


def qualified_history(root: Path) -> None:
    from adr_kit.semantic_contract import (
        SemanticContractVersion,
        validate_semantic_resource_closure,
        verify_semantic_contract,
    )

    for (family, version), scf in SCFS.items():
        definition = json.loads(
            (
                root / f"contracts/semantic-contract/v1.0/definitions/{family}-{version}.json"
            ).read_text(encoding="utf-8")
        )
        contract = SemanticContractVersion.from_wire(definition)
        if (
            definition["semanticContractFingerprint"] != scf
            or not verify_semantic_contract(contract).success
        ):
            raise PublicationError("historical_authority_unqualified")
        closure = [
            {
                "canonicalResourceKey": entry.canonical_resource_key,
                "content": read(root, entry.canonical_resource_key),
            }
            for entry in contract.resource_manifest
        ]
        if not validate_semantic_resource_closure(contract, closure).closure_valid:
            raise PublicationError("historical_resource_closure_unqualified")


def sealed_schemas(root: Path) -> dict[str, Any]:
    """Only manifest-qualified schema members may enter the reference registry."""
    result = {}
    for entry in read(root, BASE + "contract")["resourceManifest"]:
        key = entry["canonicalResourceKey"]
        if key.startswith("authoring/1.7/schema/"):
            canonical = root / "schema/authoring/v1.7" / (key.rsplit("/", 1)[1] + ".json")
        elif key.startswith("normalized-model/2.5/schema/"):
            canonical = root / "schema/normalized-model/v2.5" / (key.rsplit("/", 1)[1] + ".json")
        else:
            continue
        value = read(root, key)
        if (
            digest(value) != entry["contentDigest"]
            or json.loads(canonical.read_text(encoding="utf-8")) != value
        ):
            raise PublicationError("canonical_schema_not_manifest_qualified")
        if value["$id"] in result:
            raise PublicationError("ambiguous_schema_resource_identity")
        result[value["$id"]] = value
    if len(result) != 12:
        raise PublicationError("incomplete_authoring_or_normalized_schema_family")
    return result


def qualify(root: Path = ROOT, *, history: bool = True) -> dict[str, Any]:
    """Use a fresh immutable resource snapshot; never reuse trust across calls."""
    snapshot_token = _snapshot.set({})
    digest_token = _digests.set({})
    try:
        return _qualify(root, history=history)
    finally:
        _snapshot.reset(snapshot_token)
        _digests.reset(digest_token)


def _qualify(root: Path, *, history: bool) -> dict[str, Any]:
    if history:
        qualified_history(root)
    raw = {name: read(root, PREFIX + name) for name in NAMES}
    catalog = raw[CATALOG]
    allowed_resources = {
        entry["canonicalResourceKey"] for entry in read(root, BASE + "contract")["resourceManifest"]
    } | {
        BASE + "contract",
        "authoring-domain/1.1/contract",
        "authoring-domain/1.1/schema",
        *(PREFIX + name for name in NAMES),
    }

    def qualified_references(node: Any, found: set[str]) -> None:
        if isinstance(node, dict):
            if (
                isinstance(node.get("canonical_resource_key"), str)
                and "content_digest" in node
                and "schema_pointer" in node
            ):
                if node["canonical_resource_key"] not in allowed_resources:
                    raise PublicationError("unselected_resource_has_no_authority")
                resolve(root, node)
                found.add(node["canonical_resource_key"])
            for child in node.values():
                qualified_references(child, found)
        elif isinstance(node, list):
            for child in node:
                qualified_references(child, found)

    for value in raw.values():
        if not set(value.get("semanticDependencies", [])).issubset(allowed_resources):
            raise PublicationError("unselected_resource_has_no_authority")
    for value in raw.values():
        referenced: set[str] = set()
        qualified_references(value, referenced)
        if not referenced.issubset(value.get("semanticDependencies", [])):
            raise PublicationError("undeclared_qualified_resource_dependency")

    def closed_schema(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and node.get("additionalProperties") is not False:
                raise PublicationError("open_required_output_schema")
            for child in node.values():
                closed_schema(child)
        elif isinstance(node, list):
            for child in node:
                closed_schema(child)

    closed_schema(raw[CATALOG + ".schema"])
    # Never allow the schema library to retrieve an unsealed reference, even
    # while checking a mutated companion schema before publication.
    schema_store = {
        value["$id"]: value for value in raw.values() if isinstance(value, dict) and "$id" in value
    }

    def sealed_companion_refs(node: Any, base: str) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                location, fragment = urldefrag(urljoin(base, node["$ref"]))
                if location not in schema_store:
                    raise PublicationError("unsealed_companion_schema_reference")
                pointer(schema_store[location], fragment)
            for child in node.values():
                sealed_companion_refs(child, base)
        elif isinstance(node, list):
            for child in node:
                sealed_companion_refs(child, base)

    for name in (CATALOG, "conformance"):
        schema = raw[name + ".schema"]
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("$id")
            != "https://adr-kit.ste.systems/contracts/architecture-interpretation/v1.4/resources/"
            + name
            + ".schema.json"
        ):
            raise PublicationError("incorrect_companion_schema_identity")
        sealed_companion_refs(schema, schema["$id"])
        Draft202012Validator.check_schema(raw[name + ".schema"])
        errors = list(Draft202012Validator(raw[name + ".schema"]).iter_errors(raw[name]))
        if errors:
            raise PublicationError("invalid_" + name + ": " + errors[0].message)
    fields = read(root, BASE + "field-dispositions-1.7-to-2.5")
    types = {row["semantic_type"]: row for row in fields["semantic_types"]}
    rows = catalog["types"]
    if Counter(row["semantic_type"] for row in rows) != Counter({key: 1 for key in types}):
        raise PublicationError("missing_duplicate_or_unknown_type")
    if catalog["field_dispositions"] != qualification(root, BASE + "field-dispositions-1.7-to-2.5"):
        raise PublicationError("wrong_field_disposition_authority")
    # Verify the full sealed schema graph, including references hidden in branches.
    schemas = sealed_schemas(root)
    registry = Registry().with_resources(
        (key, Resource.from_contents(value)) for key, value in schemas.items()
    )

    def references(node: Any, base: str) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                location, fragment = urldefrag(urljoin(base, node["$ref"]))
                if location not in schemas:
                    raise PublicationError("unsealed_schema_reference")
                pointer(schemas[location], fragment)
            for value in node.values():
                references(value, base)
        elif isinstance(node, list):
            for value in node:
                references(value, base)

    for base, schema in schemas.items():
        Draft7Validator.check_schema(schema)
        references(schema, base)
    for branch in catalog["branches"]:
        resolve(root, branch["schema"])
        if branch["requirements"] != schema_audit(
            root, branch["schema"]["canonical_resource_key"], branch["schema"]["schema_pointer"]
        ):
            raise PublicationError("incomplete_branch_or_conditional_coverage")
    branches = {row["branch_id"]: row for row in catalog["branches"]}
    if len(branches) != 6 or len(branches) != len(catalog["branches"]):
        raise PublicationError("duplicate_output_branch")
    cases = raw["conformance"]["cases"]
    if [case["id"] for case in cases] != [f"AI14-{n:03}" for n in range(1, len(cases) + 1)]:
        raise PublicationError("duplicate_or_noncanonical_conformance_id")
    label_oracles = {
        case["semantic_type"]: case["fixture"]
        for case in cases
        if case["category"] == "label_policy"
    }
    if len(label_oracles) != 18:
        raise PublicationError("incomplete_label_policy_oracles")
    source_mapping = read(root, BASE + "source-mapping-1.7-to-2.5")
    ownership = read(root, BASE + "lifecycle-ownership")
    totals: Counter[str] = Counter()
    for row in rows:
        ty = row["semantic_type"]
        source = resolve(root, row["source_schema"])
        filename, _, selector = types[ty]["source_schema"].partition("#")
        expected_source = qualification(
            root, "authoring/1.7/schema/" + filename.removesuffix(".json"), selector
        )
        if row["source_schema"] != expected_source:
            raise PublicationError("wrong_source_branch")
        if row["identity_policy"] != types[ty]["identity_policy"]:
            raise PublicationError("unqualified_identity_policy")
        if row["output_branch"] != expected_branch(source_mapping["mappings"][ty]):
            raise PublicationError("incorrect_output_branch")
        branch = branches[row["output_branch"]]
        shape = resolve(root, branch["schema"])
        paths = [entry["destination"] for entry in row["outputs"]]
        if len(paths) != len(set(paths)):
            raise PublicationError("competing_destination_producers")
        expected_required = set(shape.get("required", []))
        if not {"/" + name for name in expected_required}.issubset(paths):
            raise PublicationError("missing_required_destination")
        # Input coverage remains an independent obligation. Optional semantic
        # fields and extension slots cannot disappear merely because NM does
        # not require their outer metadata container.
        for field in types[ty]["field_dispositions"]:
            if field["disposition"] not in {"canonical_field_placement", "direct_semantic_value"}:
                continue
            destination = fields["destination_catalog"][field["destination_ref"]]
            path = destination.get("path", destination.get("path_template"))
            entry = next((item for item in row["outputs"] if item["destination"] == path), None)
            if entry is None:
                raise PublicationError("missing_authored_semantic_destination")
            if (
                row["output_branch"] == "canonical-relationship"
                and destination["record"] == "normalized_entity"
            ):
                if (
                    entry["status"] != "BLOCKED"
                    or entry["blocked"]["code"] != "relationship_branch"
                ):
                    raise PublicationError("unqualified_relationship_identity_branch")
            elif entry["status"] != "QUALIFIED":
                raise PublicationError("known_field_producer_cannot_be_replaced_by_BLOCKED")
        # Every conditional required field is accounted even when inapplicable.
        for requirement in branch["requirements"]:
            if (
                requirement["keyword"] == "required"
                and "/then/required" in requirement["schema"]["schema_pointer"]
            ):
                if not {"/" + name for name in requirement["constraint"]}.issubset(paths):
                    raise PublicationError("missing_conditional_destination")
        for entry in row["outputs"]:
            totals[entry["status"]] += 1
            if entry["applicability"]["output_branch"] != row["output_branch"]:
                raise PublicationError("wrong_producer_applicability")
            selected_destination = destination_schema(root, branch, entry["destination"])
            if entry["destination_schema"] != selected_destination or entry[
                "required_subdestinations"
            ] != required_subdestinations(root, selected_destination, entry["destination"]):
                raise PublicationError("incomplete_or_wrong_destination_schema")
            for authority in entry["authorities"]:
                resolve(root, authority)
            if entry["status"] != "QUALIFIED":
                if "producer" in entry:
                    raise PublicationError("blocked_is_not_a_producer")
                continue
            producer = entry["producer"]
            for selected in producer["inputs"]:
                resolve(root, selected)
            if producer["kind"] == "literal_string_copy":
                if producer["rule"] != {"local_rule": "literal_string_copy"}:
                    raise PublicationError("unknown_output_derivation_operation")
            else:
                resolve(root, producer["rule"])
            if producer["kind"] == "literal_string_copy":
                target = entry["destination"].removeprefix("/")
                oracle = label_oracles.get(ty, {}).get(target)
                if (
                    oracle is None
                    or oracle["mode"] != "representation"
                    or producer["source_field"] != oracle["source_field"]
                ):
                    raise PublicationError("label_policy_disagreement")
                field = producer["source_field"]
                if producer["rule_id"] != "required-output." + ty.replace("/", ".") + "." + target:
                    raise PublicationError("incorrect_output_rule_identity")
                if field not in source.get("required", []) or producer["inputs"] != [
                    qualification(
                        root,
                        expected_source["canonical_resource_key"],
                        selector + "/properties/" + field,
                    )
                ]:
                    raise PublicationError("label_input_not_required")
                field_shape = source["properties"][field]
                validator = Draft7Validator(
                    {
                        "$ref": schemas_by_name(schemas, filename)["$id"]
                        + "#"
                        + selector
                        + "/properties/"
                        + field
                    },
                    registry=registry,
                )
                if field_shape.get("type") != "string" and "$ref" not in field_shape:
                    raise PublicationError("label_input_not_string")
                # A required string recipe must not accept another JSON type.
                nonstrings: tuple[Any, ...] = (None, False, 1, [], {})
                if any(validator.is_valid(item) for item in nonstrings):
                    raise PublicationError("label_input_not_string")
                if (
                    entry["classification"] != "representation_only"
                    or entry["semantic_equality"]
                    != "original_authored_input_once_not_generated_label"
                ):
                    raise PublicationError("representation_claims_new_semantic_ownership")
            elif producer["kind"] == "field_placement":
                if entry["classification"] != "semantic":
                    raise PublicationError("authored_semantic_value_reclassified")
                field = resolve(root, producer["rule"])
                if field not in types[ty]["field_dispositions"]:
                    raise PublicationError("foreign_field_producer")
                destination = fields["destination_catalog"][field["destination_ref"]]
                expected = destination.get("path", destination.get("path_template"))
                if entry["destination"] != expected:
                    raise PublicationError("incorrect_normalized_destination")
                field_filename, _, field_selector = field["schema_selector"].partition("#")
                if producer["inputs"] != [
                    qualification(
                        root,
                        "authoring/1.7/schema/" + field_filename.removesuffix(".json"),
                        field_selector,
                    )
                ]:
                    raise PublicationError("wrong_field_producer_input")
            elif producer["kind"] == "field_inventory":
                selected_type = resolve(root, producer["rule"])
                expected_fields = [
                    field
                    for field in types[ty]["field_dispositions"]
                    if fields["destination_catalog"][field["destination_ref"]].get("path_template")
                    == entry["destination"]
                ]
                if (
                    selected_type != types[ty]
                    or [resolve(root, item) for item in producer["inputs"]] != expected_fields
                ):
                    raise PublicationError("incomplete_or_forged_field_inventory")
                if entry["classification"] != "semantic":
                    raise PublicationError("authored_semantic_value_reclassified")
            elif producer["kind"] == "type_mapping":
                if (
                    resolve(root, producer["rule"]) != source_mapping["mappings"][ty]
                    or producer["inputs"] != [expected_source]
                    or entry["destination"] != "/entity_type"
                ):
                    raise PublicationError("unqualified_type_mapping")
            elif producer["kind"] == "schema_constant":
                selected = resolve(root, entry["destination_schema"])
                if (
                    entry["destination"] != "/record_kind"
                    or "const" not in selected
                    or producer["rule"] != entry["destination_schema"]
                    or producer["inputs"] != [expected_source]
                    or entry["classification"] != "representation_only"
                ):
                    raise PublicationError("unqualified_schema_envelope_constant")
            elif producer["kind"] == "mapping_constant":
                if (
                    ty != "entity/data_flow"
                    or entry["destination"] != "/path_semantics"
                    or producer["rule"]
                    != qualification(
                        root,
                        BASE + "source-mapping-1.7-to-2.5",
                        "/mappings/entity~1data_flow/path_semantics",
                    )
                    or resolve(root, producer["rule"])
                    != resolve(root, entry["destination_schema"])["const"]
                ):
                    raise PublicationError("unqualified_mapping_constant")
            elif producer["kind"] == "contextual_rule":
                expected_owners = [
                    item for item in ownership["rows"] if item["child_semantic_type"] == ty
                ]
                if (
                    entry["destination"]
                    not in {"/lifecycle_stage", "/metadata/ai_lifecycle_provenance"}
                    or resolve(root, producer["rule"]) != ownership
                    or [resolve(root, item) for item in producer["inputs"]] != expected_owners
                    or not expected_owners
                    or "declaring_context" not in entry["prerequisites"]
                    or "declaring_context" not in row["context_dependencies"]
                ):
                    raise PublicationError("unqualified_contextual_producer")
        if ty in label_oracles:
            for destination, oracle in label_oracles[ty].items():
                entry = next(
                    (item for item in row["outputs"] if item["destination"] == "/" + destination),
                    None,
                )
                if entry is None or entry["status"] != "QUALIFIED":
                    raise PublicationError("label_producer_missing")
                if oracle["mode"] == "authored":
                    producer = entry["producer"]
                    if (
                        producer["kind"] != "field_placement"
                        or resolve(root, producer["rule"])["semantic_field_key"]
                        != ty + "#/" + oracle["source_field"]
                    ):
                        raise PublicationError("authored_placement_replaced")
    if raw["rules"]["inherits"] != {
        "definition": qualification(root, BASE + "contract"),
        "semantic_contract_fingerprint": SCFS[("architecture-interpretation", "1.3")],
        "overrides": ["required_output_coverage", "verified_representation_duplication"],
    }:
        raise PublicationError("unapproved_inherited_semantic_delta")
    if raw["rules"]["refinements"] != [
        {
            "authority": qualification(root, BASE + "rules", "/semantic_extensions/duplication"),
            "successor_rule": "verified_representation_duplication",
            "scope": qualification(root, PREFIX + CATALOG, "/types"),
            "permitted_only": "literal_string_copy_representation_outputs",
            "child_payload_duplication": False,
            "independent_semantic_ownership": False,
        }
    ]:
        raise PublicationError("unapproved_semantic_duplication_refinement")
    if raw["rules"]["public_boundary"] != {
        "execution": "not_implemented",
        "advertised": False,
        "selected_by_current_semantic_contract_set": False,
        "Constructed": False,
    } or raw["rules"]["outcome_precedence"] != ["Rejected", "Unavailable", "Unresolved"]:
        raise PublicationError("publication_is_not_runtime_execution")
    return {
        "semantic_types": len(rows),
        "output_accounting": dict(totals),
        "complete_interpretation": "Unavailable",
        "runtime_execution": False,
    }


def schemas_by_name(schemas: dict[str, Any], filename: str) -> Any:
    matches = [
        value
        for key, value in schemas.items()
        if "/authoring/v1.7/" in key and key.endswith("/" + filename)
    ]
    if len(matches) != 1:
        raise PublicationError("ambiguous_source_schema")
    return matches[0]


def verify_label_fixture(
    root: Path, semantic_type: str, authored: dict[str, Any], outputs: dict[str, Any]
) -> None:
    """Check a publication oracle's proposed labels, without producing an entity.

    This verifier does not qualify sealed sources, contextual ownership, output
    envelopes or complete interpretation. It tests the literal-copy obligation
    using exact source-field schemas and independently supplied output values.
    """
    row = next(
        item
        for item in read(root, PREFIX + CATALOG)["types"]
        if item["semantic_type"] == semantic_type
    )
    documents = list(sealed_schemas(root).values())
    registry = Registry().with_resources(
        (item["$id"], Resource.from_contents(item)) for item in documents
    )
    for entry in row["outputs"]:
        if entry["destination"] not in {"/name", "/summary"}:
            continue
        producer = entry["producer"]
        if producer["kind"] == "literal_string_copy":
            source_field = producer["source_field"]
        else:
            source_field = resolve(root, producer["rule"])["semantic_field_key"].partition("#/")[2]
        if source_field not in authored:
            raise PublicationError("missing_label_input")
        selected = producer["inputs"][0]
        resolve(root, selected)
        document = read(root, selected["canonical_resource_key"])
        validator = Draft7Validator(
            {"$ref": document["$id"] + "#" + selected["schema_pointer"]}, registry=registry
        )
        value = authored[source_field]
        if not isinstance(value, str) or not validator.is_valid(value):
            raise PublicationError("invalid_label_input")
        if outputs.get(entry["destination"]) != value:
            raise PublicationError("changed_representation_label")


if __name__ == "__main__":
    print(json.dumps(qualify(), indent=2))
