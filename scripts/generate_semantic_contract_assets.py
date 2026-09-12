"""Generate the committed semantic-contract definitions and mirrors.

The canonical resources live under ``contracts``.  This script only assembles
content-addressed manifests and package mirrors; it does not define semantic
rules.  Fingerprints are calculated with the repository's RFC 8785 dependency
so the generated known-answer values use the same canonical JSON contract as
the public Python tooling.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, cast

import rfc8785

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "contracts" / "semantic-contract" / "v1.0"
RESOURCES = CANONICAL / "resources"
BUNDLED = ROOT / "src" / "adr_kit" / "semantic_contract" / "v1_0"


def scs_id(members: list[dict[str, str]]) -> str:
    composition: dict[str, Any] = {
        "scheme": "adr-kit.semantic-contract-set/v1",
        "contracts": sorted(members, key=lambda item: item["semanticContractFamily"]),
    }
    return "scs:v1:sha256:" + hashlib.sha256(rfc8785.dumps(composition)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def relative_resource_key(key: str, reference: str) -> str | None:
    location = reference.split("#", 1)[0]
    if not location:
        return None
    if location.startswith(("//", "/")) or "://" in reference or reference.startswith("urn:"):
        raise ValueError(f"remote or absolute $ref is not allowed: {key}: {reference}")
    parts = list(PurePosixPath(key).parts[:-1])
    for part in PurePosixPath(location).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError(f"$ref escapes canonical resource namespace: {key}: {reference}")
            parts.pop()
        else:
            parts.append(part)
    if not parts:
        raise ValueError(f"$ref resolves to an empty resource key: {key}: {reference}")
    if parts[-1].endswith(".json"):
        parts[-1] = parts[-1][:-5]
    return "/".join(parts)


def discovered_dependencies(key: str, value: Any) -> set[str]:
    found: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                reference = node["$ref"]
                if not isinstance(reference, str):
                    raise ValueError(f"$ref must be a string: {key}")
                target = relative_resource_key(key, reference)
                if target is not None:
                    found.add(target)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    explicit = value.get("semanticDependencies", []) if isinstance(value, dict) else []
    if not isinstance(explicit, list) or not all(isinstance(item, str) for item in explicit):
        raise ValueError(f"semanticDependencies must be a string list: {key}")
    found.update(explicit)
    return found


def resource(key: str, filename: str, role: str) -> dict[str, Any]:
    value = read_json(RESOURCES / filename)
    dependencies = sorted(discovered_dependencies(key, value))
    return {
        "canonicalResourceKey": key,
        "contentDigest": digest(value),
        "role": role,
        "dependencies": [
            {"canonicalResourceKey": dep, "contentDigest": manifest_digest(dep)}
            for dep in dependencies
        ],
    }


RESOURCE_DIGESTS: dict[str, str] = {}


def manifest_digest(key: str) -> str:
    if key not in RESOURCE_DIGESTS:
        filename = key.replace("/", "-") + ".json"
        parts = key.split("/")
        if not (RESOURCES / filename).is_file() and len(parts) == 3:
            filename = f"{parts[0]}-{parts[2]}.json"
        if not (RESOURCES / filename).is_file():
            raise FileNotFoundError(f"No canonical resource file for {key}")
        RESOURCE_DIGESTS[key] = digest(read_json(RESOURCES / filename))
    return RESOURCE_DIGESTS[key]


def resource_value(key: str) -> Any:
    filename = key.replace("/", "-") + ".json"
    parts = key.split("/")
    path = RESOURCES / filename
    if not path.is_file() and len(parts) == 3:
        path = RESOURCES / f"{parts[0]}-{parts[2]}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No canonical resource file for {key}")
    return read_json(path)


def definition(family: str, manifest: list[dict[str, Any]], frozen: list[str]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "semanticContractFamily": family,
        "semanticContractVersion": "1.0" if family != "normalized-model" else "2.3",
        "fingerprintScheme": "scf:v1:sha256",
        "resourceManifest": sorted(manifest, key=lambda item: item["canonicalResourceKey"]),
        "frozenNormativeConformanceResources": sorted(frozen),
    }
    preimage: dict[str, Any] = {"scheme": "adr-kit.semantic-contract/v1", "definition": value}
    value["semanticContractFingerprint"] = (
        "scf:v1:sha256:" + hashlib.sha256(rfc8785.dumps(preimage)).hexdigest()
    )
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep generated fingerprints and mirrors byte-stable across Windows and
    # Unix; newline translation must not become an accidental artifact change.
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    normalized_schema_files = [
        "normalized-architecture-model.schema",
        "normalized-entity-registry.schema",
        "normalized-entity.schema",
        "relationship-record.schema",
        "relationship-registry.schema",
        "unresolved-registry.schema",
    ]
    normalized_keys = [f"normalized-model/2.3/schema/{name}" for name in normalized_schema_files]
    normalized_schema_manifest = [
        resource(key, key.replace("/", "-") + ".json", "normalized-model-schema")
        for key in normalized_keys
    ]
    normalized_manifest = list(normalized_schema_manifest)
    normalized_conformance_key = "normalized-model/2.3/conformance"
    normalized_manifest.append(
        resource(
            normalized_conformance_key,
            normalized_conformance_key.replace("/", "-") + ".json",
            "normalized-model-conformance",
        )
    )

    normative_keys = [
        "normative-semantics/1.0/definition",
        "normative-semantics/1.0/conformance",
    ]
    normative_manifest = [
        resource(normative_keys[0], "normative-semantics-definition.json", "normative-definition"),
        resource(
            normative_keys[1],
            "normative-semantics-conformance.json",
            "normative-conformance",
        ),
    ]

    source_manifest: list[dict[str, Any]] = []
    for version in ("1.5", "1.6"):
        for name in (
            "adr-common.schema",
            "adr-logical.schema",
            "adr-physical-base.schema",
            "adr-physical-component.schema",
            "adr-physical-system.schema",
            "types.schema",
        ):
            key = f"authoring/{version}/schema/{name}"
            source_manifest.append(
                resource(key, key.replace("/", "-") + ".json", "source-contract-schema")
            )

    architecture_keys = [
        "architecture-interpretation/1.0/rules",
        "architecture-interpretation/1.0/conformance",
    ]
    architecture_manifest = [
        resource(
            architecture_keys[0],
            "architecture-interpretation-rules.json",
            "interpretation-rule",
        ),
        resource(
            architecture_keys[1],
            "architecture-interpretation-conformance.json",
            "interpretation-conformance",
        ),
        *source_manifest,
        *normalized_schema_manifest,
        resource(
            "architecture-interpretation/1.0/source-decoding-1.5",
            "architecture-interpretation-source-decoding-1.5.json",
            "source-contract-mapping",
        ),
        resource(
            "architecture-interpretation/1.0/source-decoding-1.6",
            "architecture-interpretation-source-decoding-1.6.json",
            "source-contract-mapping",
        ),
        resource(
            "architecture-interpretation/1.0/source-mapping-1.5-to-2.3",
            "architecture-interpretation-source-mapping-1.5-to-2.3.json",
            "source-contract-mapping",
        ),
        resource(
            "architecture-interpretation/1.0/source-mapping-1.6-to-2.3",
            "architecture-interpretation-source-mapping-1.6-to-2.3.json",
            "source-contract-mapping",
        ),
    ]

    definitions = {
        "normalized-model.json": definition(
            "normalized-model", normalized_manifest, [normalized_conformance_key]
        ),
        "normative-semantics.json": definition(
            "normative-semantics", normative_manifest, [normative_keys[1]]
        ),
        "architecture-interpretation.json": definition(
            "architecture-interpretation", architecture_manifest, [architecture_keys[1]]
        ),
    }
    for name, value in definitions.items():
        write_json(CANONICAL / "definitions" / name, value)
        write_json(BUNDLED / name, value)

    for path in CANONICAL.glob("*.schema.json"):
        target = BUNDLED / path.name
        target.write_bytes(path.read_bytes())
    for path in RESOURCES.glob("*.json"):
        target = BUNDLED / "resources" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())

    # Governance artifacts are generated from the exact definitions written above.
    # The profile and policy files are projections around immutable identities;
    # they never participate in an SCF or SCS preimage.
    members = [
        {
            "semanticContractFamily": value["semanticContractFamily"],
            "semanticContractVersion": value["semanticContractVersion"],
            "semanticContractFingerprint": value["semanticContractFingerprint"],
        }
        for value in definitions.values()
    ]
    members.sort(key=lambda item: item["semanticContractFamily"])
    set_id = scs_id(members)
    profile = {
        "profileFamily": "architecture-materialization",
        "profileVersion": "1.0",
        "profileId": "architecture-materialization@1.0",
        "participatingFamilies": [
            {
                "semanticContractFamily": "architecture-interpretation",
                "semanticContractVersion": "1.0",
                "cardinality": 1,
            },
            {
                "semanticContractFamily": "normalized-model",
                "semanticContractVersion": "2.3",
                "cardinality": 1,
            },
            {
                "semanticContractFamily": "normative-semantics",
                "semanticContractVersion": "1.0",
                "cardinality": 1,
            },
        ],
        "operations": [
            "validate_profile",
            "qualify_tuple",
            "assemble_set",
            "validate_corpus",
            "resolve_current",
            "resolve_semantic_contract_set",
            "materialize_architecture",
        ],
        "selectionPurposes": ["architecture-materialization"],
    }
    set_artifact = {
        "scsScheme": "scs:v1:sha256",
        "semanticContractSetId": set_id,
        "members": members,
    }
    qualifications = []
    policy_entries = []
    for operation in profile["operations"]:
        qualification_id = f"qualification:architecture-materialization@1.0:{operation}"
        qualifications.append(
            {
                "qualificationRecordId": qualification_id,
                "qualificationSchemaVersion": "1.0",
                "operation": operation,
                "direction": "none",
                "profileId": profile["profileId"],
                "semanticContractSetId": set_id,
                "members": members,
                "outcome": "qualified",
                "installedExecutionSupport": True,
                "newUsePolicy": "permitted",
                "historicalInterpretationSupport": True,
                "qualificationRevision": "qualification:v1:1",
                "reasonCode": "architecture-materialization-qualified",
            }
        )
        policy_entries.append(
            {
                "semanticContractSetId": set_id,
                "operation": operation,
                "direction": "none",
                "newUsePolicy": "permitted",
                "installedExecutionSupport": True,
                "historicalInterpretationSupport": True,
            }
        )
    catalog = {
        "catalogSchemaVersion": "1.0",
        "catalogRevision": "catalog:v1:1",
        "entries": [
            {
                "semanticContractSetId": set_id,
                "catalogued": True,
                "lifecycle": "active",
                "historicalAddressable": True,
            }
        ],
    }
    policy = {
        "policySchemaVersion": "1.0",
        "policyRevision": "policy:v1:1",
        "entries": policy_entries,
    }
    current = {
        "currentSelectionSchemaVersion": "1.0",
        "currentSelectionRevision": "current:v1:1",
        "profileId": profile["profileId"],
        "operation": "resolve_current",
        "direction": "none",
        "semanticContractSetId": set_id,
        "qualificationRecordId": "qualification:architecture-materialization@1.0:resolve_current",
        "catalogRevision": catalog["catalogRevision"],
        "policyRevision": policy["policyRevision"],
    }
    generated: dict[str, Any] = {
        "profiles/architecture-materialization-1.0.json": profile,
        f"sets/{set_id.replace(':', '-')}.json": set_artifact,
        "qualifications/architecture-materialization-1.0.json": qualifications,
        "catalog/semantic-contract-catalog-1.0.json": catalog,
        "policy/semantic-contract-policy-1.0.json": policy,
        "current/semantic-contract-current-1.0.json": current,
    }
    for relative, value in generated.items():
        write_json(CANONICAL / relative, value)
        write_json(BUNDLED / relative, value)

    bundles = []
    for value in definitions.values():
        bundles.append(
            {
                "definition": value,
                "resources": [
                    {
                        "canonicalResourceKey": entry["canonicalResourceKey"],
                        "content": resource_value(entry["canonicalResourceKey"]),
                    }
                    for entry in value["resourceManifest"]
                ],
            }
        )

    def requalified_bundle(
        family: str,
        version: str,
        resource_mutations: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a valid retained definition that is intentionally unselected.

        These bundles are adversarial corpus inputs.  They are fully qualified
        and closure-valid, but their family/version/SCF identity is absent from
        the admitted SCS, which proves that retained history cannot become an
        implicit execution source.
        """
        original = copy.deepcopy(
            next(item for item in bundles if item["definition"]["semanticContractFamily"] == family)
        )
        definition_value = original["definition"]
        definition_value["semanticContractVersion"] = version
        for key, content in (resource_mutations or {}).items():
            for entry in definition_value["resourceManifest"]:
                if entry["canonicalResourceKey"] == key:
                    entry["contentDigest"] = digest(content)
                for dependency in entry.get("dependencies", []):
                    if dependency["canonicalResourceKey"] == key:
                        dependency["contentDigest"] = digest(content)
            for resource_entry in original["resources"]:
                if resource_entry["canonicalResourceKey"] == key:
                    resource_entry["content"] = copy.deepcopy(content)
        definition_value.pop("semanticContractFingerprint", None)
        preimage: dict[str, Any] = {
            "scheme": "adr-kit.semantic-contract/v1",
            "definition": definition_value,
        }
        definition_value["semanticContractFingerprint"] = (
            "scf:v1:sha256:" + hashlib.sha256(rfc8785.dumps(preimage)).hexdigest()
        )
        return original

    physical_component_schema_key = "authoring/1.6/schema/adr-physical-component.schema"
    permissive_component_schema = resource_value(physical_component_schema_key)
    # The actual name property is on the top-level component specification;
    # retain this explicit path so the adversarial mutation remains obvious.
    permissive_component_schema["properties"] = copy.deepcopy(
        permissive_component_schema["properties"]
    )
    permissive_component_schema["properties"]["component_specifications"] = copy.deepcopy(
        permissive_component_schema["properties"]["component_specifications"]
    )
    permissive_component_schema["properties"]["component_specifications"]["items"] = copy.deepcopy(
        permissive_component_schema["properties"]["component_specifications"]["items"]
    )
    permissive_component_schema["properties"]["component_specifications"]["items"]["properties"] = (
        copy.deepcopy(
            permissive_component_schema["properties"]["component_specifications"]["items"][
                "properties"
            ]
        )
    )
    permissive_component_schema["properties"]["component_specifications"]["items"]["properties"][
        "name"
    ] = {"type": ["string", "number"]}
    strict_component_schema = copy.deepcopy(permissive_component_schema)
    strict_component_schema["properties"]["component_specifications"]["items"]["properties"][
        "name"
    ] = {
        "type": "string",
        "minLength": 1000,
    }
    unselected_architecture_permissive = requalified_bundle(
        "architecture-interpretation",
        "9.9",
        {physical_component_schema_key: permissive_component_schema},
    )
    unselected_architecture_strict = requalified_bundle(
        "architecture-interpretation",
        "9.8",
        {physical_component_schema_key: strict_component_schema},
    )
    normalized_schema_key = "normalized-model/2.3/schema/normalized-architecture-model.schema"
    unselected_normalized_strict_schema = copy.deepcopy(resource_value(normalized_schema_key))
    unselected_normalized_strict_schema["required"] = sorted(
        set(unselected_normalized_strict_schema.get("required", [])) | {"unselectedSentinel"}
    )
    unselected_normalized = requalified_bundle(
        "normalized-model", "9.9", {normalized_schema_key: unselected_normalized_strict_schema}
    )
    conflicting_normalized_schema = copy.deepcopy(resource_value(normalized_schema_key))
    conflicting_normalized_schema["description"] = (
        "Adversarial bytes: the selected architecture import disagrees with the owner."
    )
    conflicting_architecture = requalified_bundle(
        "architecture-interpretation", "1.0", {normalized_schema_key: conflicting_normalized_schema}
    )
    conflicting_definitions = [
        item
        for item in bundles
        if item["definition"]["semanticContractFamily"] != "architecture-interpretation"
    ] + [conflicting_architecture]
    conflicting_members = [
        {
            "semanticContractFamily": item["definition"]["semanticContractFamily"],
            "semanticContractVersion": item["definition"]["semanticContractVersion"],
            "semanticContractFingerprint": item["definition"]["semanticContractFingerprint"],
        }
        for item in conflicting_definitions
    ]
    conflicting_members.sort(key=lambda item: item["semanticContractFamily"])
    conflicting_set_id = scs_id(conflicting_members)
    conflicting_set = {
        "scsScheme": "scs:v1:sha256",
        "semanticContractSetId": conflicting_set_id,
        "members": conflicting_members,
    }
    conflicting_qualifications = copy.deepcopy(qualifications)
    for qualification in conflicting_qualifications:
        qualification["semanticContractSetId"] = conflicting_set_id
        qualification["members"] = copy.deepcopy(conflicting_members)
    conflicting_catalog = copy.deepcopy(catalog)
    conflicting_catalog["entries"][0]["semanticContractSetId"] = conflicting_set_id
    conflicting_policy = copy.deepcopy(policy)
    for policy_entry in conflicting_policy["entries"]:
        policy_entry["semanticContractSetId"] = conflicting_set_id
    by_operation = {item["operation"]: item for item in qualifications}
    common: dict[str, Any] = {
        "profile": profile,
        "definitions": bundles,
        "catalog": catalog,
        "policy": policy,
    }
    _compatibility_vector_cases: list[dict[str, Any]] = [
        {
            "name": "valid_architecture_materialization_profile",
            "request": {
                "core_contract_version": "1.0",
                "operation": "validate_semantic_contract_profile",
                "profile": profile,
            },
            "expected": {"success": True},
        },
        {
            "name": "profile_rejects_missing_participating_family",
            "request": {
                "core_contract_version": "1.0",
                "operation": "validate_semantic_contract_profile",
                "profile": {
                    **profile,
                    "participatingFamilies": profile["participatingFamilies"][:2],
                },
            },
            "expected": {
                "success": False,
                "diagnostic_codes": ["semantic_contract.profile_family_mismatch"],
            },
        },
        {
            "name": "exact_whole_tuple_qualification_succeeds",
            "request": {
                "core_contract_version": "1.0",
                "operation": "validate_semantic_contract_qualification",
                "profile": profile,
                "members": members,
                "targetOperation": "qualify_tuple",
                "direction": "none",
                "qualification": by_operation["qualify_tuple"],
            },
            "expected": {"success": True},
        },
        {
            "name": "qualification_rejects_wrong_scs_id",
            "request": {
                "core_contract_version": "1.0",
                "operation": "validate_semantic_contract_qualification",
                "profile": profile,
                "members": members,
                "targetOperation": "qualify_tuple",
                "direction": "none",
                "qualification": {
                    **by_operation["qualify_tuple"],
                    "semanticContractSetId": "scs:v1:sha256:" + "0" * 64,
                },
            },
            "expected": {
                "success": False,
                "diagnostic_codes": ["semantic_contract.qualification_set_mismatch"],
            },
        },
        {
            "name": "assembly_is_deterministic_no_op_for_retained_set",
            "request": {
                "core_contract_version": "1.0",
                "operation": "assemble_semantic_contract_set",
                "targetOperation": "assemble_set",
                "direction": "none",
                "requestedMembers": members,
                "qualification": by_operation["assemble_set"],
                "retainedSets": [set_artifact],
                "retainedQualifications": qualifications,
                **common,
            },
            "expected": {"success": True, "noOp": True, "semanticContractSetId": set_id},
        },
        {
            "name": "assembly_rejects_missing_whole_tuple_qualification",
            "request": {
                "core_contract_version": "1.0",
                "operation": "assemble_semantic_contract_set",
                "targetOperation": "assemble_set",
                "direction": "none",
                "requestedMembers": members,
                "qualification": by_operation["assemble_set"],
                "retainedSets": [],
                "retainedQualifications": [],
                **common,
            },
            "expected": {
                "success": False,
                "diagnostic_codes": ["semantic_contract.missing_whole_tuple_qualification"],
            },
        },
        {
            "name": "complete_retained_corpus_validates",
            "request": {
                "core_contract_version": "1.0",
                "operation": "validate_semantic_contract_corpus",
                "sets": [set_artifact],
                "qualifications": qualifications,
                **common,
            },
            "expected": {"success": True},
        },
        {
            "name": "corpus_rejects_duplicate_stored_composition",
            "request": {
                "core_contract_version": "1.0",
                "operation": "validate_semantic_contract_corpus",
                "sets": [set_artifact, set_artifact],
                "qualifications": qualifications,
                **common,
            },
            "expected": {
                "success": False,
                "diagnostic_codes": ["semantic_contract.duplicate_stored_composition"],
            },
        },
        {
            "name": "current_pointer_resolves_to_exact_set",
            "request": {
                "core_contract_version": "1.0",
                "operation": "resolve_current_semantic_contract_set",
                "targetOperation": "resolve_current",
                "direction": "none",
                "current": current,
                "sets": [set_artifact],
                "qualifications": qualifications,
                **common,
            },
            "expected": {"success": True, "resolved": {"semanticContractSetId": set_id}},
        },
        {
            "name": "current_pointer_missing_set_fails_closed",
            "request": {
                "core_contract_version": "1.0",
                "operation": "resolve_current_semantic_contract_set",
                "targetOperation": "resolve_current",
                "direction": "none",
                "current": {**current, "semanticContractSetId": "scs:v1:sha256:" + "0" * 64},
                "sets": [],
                "qualifications": [],
                **common,
            },
            "expected": {
                "success": False,
                "diagnostic_codes": ["semantic_contract.invalid_current_selection"],
            },
        },
    ]
    # v1.1 materialization vectors are executable requests, not an inventory
    # of planned cases.  They are generated from the retained SCS and its
    # governed authoring resource manifest so every host harness consumes the
    # same authority evidence.
    source_resources = {
        entry["canonicalResourceKey"]: entry["contentDigest"]
        for entry in definitions["architecture-interpretation.json"]["resourceManifest"]
    }

    def binding(version: str, adr_type: str) -> dict[str, Any]:
        top_level = {
            "logical": "adr-logical.schema",
            "physical-system": "adr-physical-system.schema",
            "physical-component": "adr-physical-component.schema",
        }[adr_type]
        names = ["adr-common.schema", "types.schema", top_level]
        if adr_type.startswith("physical-"):
            names.append("adr-physical-base.schema")
        keys = sorted(f"authoring/{version}/schema/{name}" for name in names)
        closure = [
            {"canonicalResourceKey": key, "contentDigest": source_resources[key]} for key in keys
        ]
        schema_resource = next(
            item for item in closure if item["canonicalResourceKey"].endswith(top_level)
        )
        return {
            "family": "authoring",
            "version": version,
            "schemaResource": schema_resource,
            "resourceClosure": closure,
        }

    def document(adr_type: str, version: str, identity: str, alias: str) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": version,
            "adr_type": adr_type,
            "id": identity,
            "alias_id": alias,
            "alias_name": "boundary-record",
            "title": "A governed architecture boundary",
            "status": "accepted",
            "created_date": "2026-01-01",
            "authors": ["architecture-team"],
            "context": "The boundary needs an explicit semantic authority.",
            "decisions": [
                {
                    "id": "01940000-0000-7000-8000-000000000002",
                    "alias_id": "DEC-0001",
                    "alias_name": "choose-authority",
                    "summary": "Use the governed boundary.",
                }
            ],
            "invariants": [
                {
                    "id": "01940000-0000-7000-8000-000000000003",
                    "alias_id": "INV-0001",
                    "alias_name": "retain-evidence",
                }
            ],
            "normative_propositions": [
                {
                    "id": "01940000-0000-7000-8000-000000000004",
                    "alias_id": "NP-0001",
                    "alias_name": "retain-evidence",
                    "statement": "The canonical boundary MUST retain source evidence.",
                    "normative_force": "MUST",
                    "scope": "semantic-core",
                }
            ],
            "extension_entities": [
                {
                    "id": "01940000-0000-7000-8000-000000000005",
                    "alias_id": "EXT-0001",
                    "alias_name": "boundary-extension",
                    "entity_type": "acme:boundary",
                    "properties": {"risk_level": "low"},
                    "rationale": "The extension carries bounded evidence.",
                }
            ],
            "extension_relationships": [
                {
                    "id": "01940000-0000-7000-8000-000000000006",
                    "alias_id": "REL-0001",
                    "alias_name": "boundary-relates",
                    "relationship_type": "acme:relates_to",
                    "from_entity_id": identity,
                    "to_entity_id": "01940000-0000-7000-8000-000000000005",
                    "properties": {"kind": "evidence"},
                    "rationale": "The relationship is explicitly authored.",
                }
            ],
        }
        if adr_type == "physical-system":
            value.update(
                {
                    "implements_logical": [identity],
                    "technology_stack": ["WASM"],
                    "system": {
                        "id": "01940000-0000-7000-8000-000000000007",
                        "alias_id": "SYS-0001",
                        "alias_name": "boundary-system",
                    },
                }
            )
        elif adr_type == "physical-component":
            value.update(
                {
                    "implements_logical": [identity],
                    "technology_stack": ["WASM"],
                    "implements_system": ["01940000-0000-7000-8000-000000000007"],
                    "component_specifications": [
                        {
                            "id": "01940000-0000-7000-8000-000000000008",
                            "alias_id": "COMP-0001",
                            "alias_name": "boundary-component",
                            "name": "Boundary component",
                            "type": "service",
                            "responsibilities": "Executes the bounded semantic operation.",
                            "generation_context": {
                                "purpose": "Preserve the semantic boundary.",
                                "key_responsibilities": ["retain evidence"],
                            },
                        }
                    ],
                }
            )
            value.pop("decisions")
            value.pop("invariants")
            value.pop("normative_propositions")
        return value

    def artifact(
        source_ref: str, value: dict[str, Any], version: str, adr_type: str, digest_suffix: str
    ) -> dict[str, Any]:
        content_digest = "sha256:" + digest_suffix * 64
        return {
            "sourceRef": source_ref,
            "artifactPath": f"architecture/{source_ref}.yaml",
            "contentDigest": content_digest,
            "sourceContract": binding(version, adr_type),
            "document": value,
        }

    def materialization_request(
        artifacts: list[dict[str, Any]] | None,
        source_basis: Any = None,
        definitions_override: list[dict[str, Any]] | None = None,
        set_override: dict[str, Any] | None = None,
        qualifications_override: list[dict[str, Any]] | None = None,
        catalog_override: dict[str, Any] | None = None,
        policy_override: dict[str, Any] | None = None,
        semantic_contract_set_id_override: str | None = None,
    ) -> dict[str, Any]:
        request = {
            "core_contract_version": "1.1",
            "operation": "materialize_architecture",
            "materializationContractVersion": "1.0",
            "semanticContractSetId": semantic_contract_set_id_override or set_id,
            "authorityProvider": {"kind": "fixture-provider", "architectureNamespace": "example"},
            "providerProvenance": {
                "semanticCoreContractVersion": "1.1",
                "packageVersion": "0.10.1",
                "hostBinding": "fixture-harness",
            },
            **copy.deepcopy(common),
        }
        if source_basis is None and artifacts is not None:
            request["sourceBasis"] = {
                "sealed": True,
                "providerSourceIdentity": "fixture-provider:example",
                "sourceRevision": "revision-1",
                "artifacts": artifacts,
            }
        else:
            request["sourceBasis"] = source_basis
        if definitions_override is not None:
            request["definitions"] = copy.deepcopy(definitions_override)
        request["sets"] = [set_override or set_artifact]
        request["qualifications"] = qualifications_override or qualifications
        request["catalog"] = catalog_override or catalog
        request["policy"] = policy_override or policy
        return request

    def exact_resolution_request(
        *,
        set_id_override: str | None = None,
        sets_override: list[dict[str, Any]] | None = None,
        qualifications_override: list[dict[str, Any]] | None = None,
        definitions_override: list[dict[str, Any]] | None = None,
        include_current: bool = False,
    ) -> dict[str, Any]:
        request = {
            "core_contract_version": "1.1",
            "operation": "resolve_semantic_contract_set",
            "semanticContractSetId": set_id_override or set_id,
            "profile": profile,
            "targetOperation": "materialize_architecture",
            "direction": "none",
            "useMode": "new",
            "sets": sets_override if sets_override is not None else [set_artifact],
            "qualifications": (
                qualifications_override if qualifications_override is not None else qualifications
            ),
            "catalog": catalog,
            "policy": policy,
            # Exact resolution consumes the retained immutable definition
            # bundles, including each bundle's resource closure.  Supplying
            # only the definition payload would test a malformed transport
            # shape instead of the resolver's exact-set behavior.
            "definitions": definitions_override if definitions_override is not None else bundles,
        }
        if include_current:
            # This is intentionally a raw-core metamorphic request.  The
            # validated v1.1 protocol rejects undeclared transport fields, but
            # the canonical resolver itself must remain independent of any
            # current-pointer input if a host accidentally supplies one.
            request["current"] = {"semanticContractSetId": "scs:v1:sha256:" + "0" * 64}
        return request

    logical = document("logical", "1.6", "01940000-0000-7000-8000-000000000001", "ADR-L-0001")
    physical_system = document(
        "physical-system", "1.6", "01940000-0000-7000-8000-000000000011", "ADR-PS-0001"
    )
    physical_component = document(
        "physical-component", "1.6", "01940000-0000-7000-8000-000000000021", "ADR-PC-0001"
    )
    logical_15 = document("logical", "1.5", "01940000-0000-7000-8000-000000000031", "ADR-L-0002")
    logical_15.pop("normative_propositions")

    # Keep the compact fixtures useful for negative tests, and maintain a
    # separate fully populated physical pair for projection and coverage
    # assertions.  The topology handle is deliberately not a canonical
    # identity; its component_ref points at the independently emitted
    # component specification identity.
    physical_system_rich = copy.deepcopy(physical_system)
    physical_system_rich.update(
        {
            "system_boundaries": [
                {
                    "id": "SYSBOUND-0001",
                    "name": "semantic boundary",
                    "description": "The system boundary is retained as source evidence.",
                    "external_dependencies": ["external-provider"],
                    "exposed_interfaces": ["IFACE-0001"],
                }
            ],
            "component_topology": {
                "components": [
                    {
                        "id": "TOPO-BOUNDARY",
                        "component_ref": "01940000-0000-7000-8000-000000000028",
                        "purpose": "Executes the boundary operation.",
                    }
                ],
                "relationships": [],
            },
            "integration_patterns": [
                {
                    "pattern_name": "request-response",
                    "application": "The boundary uses a request-response interaction.",
                    "components_affected": ["TOPO-BOUNDARY"],
                    "rationale": "The interaction is explicit source meaning.",
                }
            ],
            "data_flows": [
                {
                    "id": "FLOW-0001",
                    "name": "boundary request",
                    "description": "A request crosses the boundary.",
                    "path": ["TOPO-BOUNDARY"],
                    "data_type": "JSON",
                    "volume": "low",
                    "latency_requirements": "bounded",
                }
            ],
            "references_components": [],
            "scalability_strategy": {
                "horizontal_scaling": "Add equivalent boundary workers.",
                "vertical_scaling": "Increase worker capacity.",
                "bottlenecks": ["worker capacity"],
                "capacity_planning": "Measure boundary demand.",
            },
            "failure_modes": [
                {
                    "scenario": "provider unavailable",
                    "impact": "medium",
                    "mitigation": "Retry with bounded backoff.",
                    "detection": "Health checks",
                    "recovery": "Restore provider connectivity",
                }
            ],
        }
    )
    physical_component_rich = copy.deepcopy(physical_component)
    # This standalone fixture uses its own canonical root as the logical
    # endpoint so the combined projection can prove endpoint admission without
    # adding an unrelated logical fixture to the expected entity set.
    physical_component_rich["implements_logical"] = [physical_component["id"]]
    physical_component_rich["component_specifications"][0].update(
        {
            "id": "01940000-0000-7000-8000-000000000028",
            "interfaces": [
                {
                    "id": "01940000-0000-7000-8000-000000000029",
                    "alias_id": "IFACE-0001",
                    "alias_name": "boundary-interface",
                    "type": "REST",
                    "specification": "The boundary interface accepts a governed request.",
                }
            ],
        }
    )
    physical_component_rich["implements_system"] = [physical_system["system"]["id"]]
    physical_component_rich["extension_entities"][0].update(
        {"id": "01940000-0000-7000-8000-000000000025", "alias_id": "EXT-0002"}
    )
    physical_component_rich["extension_relationships"][0].update(
        {
            "id": "01940000-0000-7000-8000-000000000026",
            "alias_id": "REL-0002",
            "from_entity_id": physical_component_rich["id"],
            "to_entity_id": physical_component_rich["extension_entities"][0]["id"],
        }
    )
    physical_component_unresolved = copy.deepcopy(physical_component_rich)
    physical_component_unresolved["implements_logical"] = ["01940000-0000-7000-8000-000000000099"]

    # v1.5 has the same physical top-level families but does not express
    # normative propositions.  Distinct identities keep the parity cases from
    # becoming duplicate-definition cases when combined with v1.6 fixtures.
    physical_system_15 = document(
        "physical-system", "1.5", "01940000-0000-7000-8000-000000000041", "ADR-PS-0002"
    )
    physical_system_15.pop("normative_propositions")
    physical_component_15 = document(
        "physical-component", "1.5", "01940000-0000-7000-8000-000000000051", "ADR-PC-0002"
    )
    logical_artifact = artifact("logical-16", logical, "1.6", "logical", "1")
    cases: list[dict[str, Any]] = []

    def add(
        name: str,
        request: dict[str, Any],
        expected: dict[str, Any],
        execution_boundary: str | None = None,
    ) -> None:
        counts = expected.get("diagnostic_code_counts", {})
        if counts:
            expected["diagnostic_codes"] = [
                code for code, count in counts.items() for _ in range(count)
            ]
        else:
            expected["diagnostic_codes"] = []
        case: dict[str, Any] = {"name": name, "request": request, "expected": expected}
        if execution_boundary is not None:
            case["executionBoundary"] = execution_boundary
        cases.append(case)

    success: dict[str, Any] = {
        "success": True,
        "outcome": "Materialized",
        "diagnostic_code_counts": {},
        "assertions": {
            "normalized_schema_version": "2.3",
            "no_runtime_identity": True,
            "semantic_contract_set_id": set_id,
        },
    }
    add(
        "logical_16_materializes_with_np_and_extensions",
        materialization_request([logical_artifact]),
        success
        | {
            "assertions": {
                **success["assertions"],
                "source_contract_versions": ["1.6"],
                "normalized_entity_type": "normative_proposition",
            }
        },
    )
    add(
        "physical_system_16_materializes",
        materialization_request(
            [artifact("physical-system-16", physical_system, "1.6", "physical-system", "2")]
        ),
        success | {"assertions": {**success["assertions"], "source_contract_versions": ["1.6"]}},
    )
    add(
        "physical_component_16_materializes",
        materialization_request(
            [
                artifact(
                    "physical-component-16", physical_component, "1.6", "physical-component", "3"
                )
            ]
        ),
        success | {"assertions": {**success["assertions"], "source_contract_versions": ["1.6"]}},
    )
    add(
        "logical_15_materializes_without_inferred_np",
        materialization_request([artifact("logical-15", logical_15, "1.5", "logical", "4")]),
        success
        | {
            "assertions": {
                **success["assertions"],
                "source_contract_versions": ["1.5"],
                "limitation_capability": "normative_proposition",
            }
        },
    )
    invalids: list[tuple[str, str, str | None]] = [
        ("missing_id", "id", None),
        ("invalid_alias_id", "alias_id", "INVALID"),
        ("missing_title", "title", None),
        ("invalid_status", "status", "unknown"),
        ("invalid_created_date", "created_date", "2026/01/01"),
        ("missing_authors", "authors", None),
        ("missing_logical_context", "context", None),
        ("missing_logical_decisions", "decisions", None),
    ]
    for suffix, field, invalid_value in invalids:
        invalid_document = copy.deepcopy(logical)
        if invalid_value is None:
            invalid_document.pop(field, None)
        else:
            invalid_document[field] = invalid_value
        add(
            f"rejects_{suffix}",
            materialization_request(
                [artifact(f"invalid-{suffix}", invalid_document, "1.6", "logical", "5")]
            ),
            {
                "success": False,
                "outcome": "Rejected",
                "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
            },
        )
    physical_invalids: list[tuple[str, str, dict[str, Any]]] = [
        ("missing_physical_implementation", "physical-system", {"implements_logical": []}),
        ("missing_system_identity", "physical-system", {"system": None}),
        ("missing_component_specification", "physical-component", {"component_specifications": []}),
        ("missing_component_implementation", "physical-component", {"implements_system": []}),
    ]
    for suffix, adr_type, source in physical_invalids:
        invalid_physical_document: dict[str, Any] = copy.deepcopy(
            physical_system if adr_type == "physical-system" else physical_component
        )
        invalid_physical_document.update(source)
        add(
            f"rejects_{suffix}",
            materialization_request(
                [artifact(f"invalid-{suffix}", invalid_physical_document, "1.6", adr_type, "6")]
            ),
            {
                "success": False,
                "outcome": "Rejected",
                "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
            },
        )

    invalid_component_name = copy.deepcopy(physical_component)
    invalid_component_name["component_specifications"][0]["name"] = 42
    add(
        "rejects_component_name_wrong_type",
        materialization_request(
            [
                artifact(
                    "invalid-component-name",
                    invalid_component_name,
                    "1.6",
                    "physical-component",
                    "a",
                )
            ]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_component_alias = copy.deepcopy(physical_component)
    invalid_component_alias["component_specifications"][0]["alias_id"] = "BAD-9999"
    add(
        "rejects_component_alias_outside_comp_pattern",
        materialization_request(
            [
                artifact(
                    "invalid-component-alias",
                    invalid_component_alias,
                    "1.6",
                    "physical-component",
                    "b",
                )
            ]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_interface_alias = copy.deepcopy(physical_component_rich)
    invalid_interface_alias["component_specifications"][0]["interfaces"][0]["alias_id"] = "BAD-9999"
    add(
        "rejects_interface_alias_outside_iface_pattern",
        materialization_request(
            [
                artifact(
                    "invalid-interface-alias",
                    invalid_interface_alias,
                    "1.6",
                    "physical-component",
                    "c",
                )
            ]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_component_topology = copy.deepcopy(physical_component)
    invalid_component_topology["component_topology"] = {}
    add(
        "rejects_component_topology_on_physical_component",
        materialization_request(
            [
                artifact(
                    "invalid-component-topology",
                    invalid_component_topology,
                    "1.6",
                    "physical-component",
                    "d",
                )
            ]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_generation_context = copy.deepcopy(physical_component)
    invalid_generation_context["component_specifications"][0]["generation_context"][
        "key_responsibilities"
    ] = []
    add(
        "rejects_invalid_nested_generation_context",
        materialization_request(
            [
                artifact(
                    "invalid-generation-context",
                    invalid_generation_context,
                    "1.6",
                    "physical-component",
                    "e",
                )
            ]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_topology = copy.deepcopy(physical_system_rich)
    invalid_topology["component_topology"]["components"][0]["component_ref"] = "not-a-uuid"
    add(
        "rejects_invalid_physical_system_topology",
        materialization_request(
            [artifact("invalid-physical-topology", invalid_topology, "1.6", "physical-system", "f")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_boundary = copy.deepcopy(physical_system_rich)
    invalid_boundary["system_boundaries"][0]["description"] = 42
    add(
        "rejects_invalid_system_boundary_structure",
        materialization_request(
            [artifact("invalid-system-boundary", invalid_boundary, "1.6", "physical-system", "a")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_flow = copy.deepcopy(physical_system_rich)
    invalid_flow["data_flows"][0]["path"] = [42]
    add(
        "rejects_invalid_data_flow_structure",
        materialization_request(
            [artifact("invalid-data-flow", invalid_flow, "1.6", "physical-system", "b")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_integration = copy.deepcopy(physical_system_rich)
    invalid_integration["integration_patterns"][0]["components_affected"] = ["bad-handle"]
    add(
        "rejects_invalid_integration_pattern_structure",
        materialization_request(
            [artifact("invalid-integration", invalid_integration, "1.6", "physical-system", "c")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_failure_mode = copy.deepcopy(physical_system_rich)
    invalid_failure_mode["failure_modes"][0]["impact"] = "critical"
    add(
        "rejects_invalid_failure_mode_structure",
        materialization_request(
            [artifact("invalid-failure-mode", invalid_failure_mode, "1.6", "physical-system", "d")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_np_alias = copy.deepcopy(logical)
    invalid_np_alias["normative_propositions"][0]["alias_id"] = "BAD-0001"
    add(
        "rejects_invalid_np_alias_once",
        materialization_request(
            [artifact("invalid-np-alias", invalid_np_alias, "1.6", "logical", "e")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )

    invalid_relationship_endpoint = copy.deepcopy(logical)
    invalid_relationship_endpoint["extension_relationships"][0][
        "to_entity_id"
    ] = "01940000-0000-7000-8000-000000000099"
    add(
        "relationship_with_non_admitted_endpoint_is_not_canonical",
        materialization_request(
            [
                artifact(
                    "invalid-relationship-endpoint",
                    invalid_relationship_endpoint,
                    "1.6",
                    "logical",
                    "f",
                )
            ]
        ),
        success
        | {"assertions": {**success["assertions"], "unresolved_count": 1, "relationship_count": 0}},
    )
    invalid_np = copy.deepcopy(logical)
    invalid_np["normative_propositions"][0]["normative_force"] = "MAYBE"
    add(
        "rejects_invalid_normative_force",
        materialization_request(
            [artifact("invalid-normative-force", invalid_np, "1.6", "logical", "7")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_15 = copy.deepcopy(logical_15)
    invalid_15["normative_propositions"] = copy.deepcopy(logical["normative_propositions"])
    add(
        "rejects_normative_proposition_in_15",
        materialization_request([artifact("invalid-15-np", invalid_15, "1.5", "logical", "8")]),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_binding = copy.deepcopy(logical_artifact)
    invalid_binding["sourceContract"]["schemaResource"]["contentDigest"] = "sha256:" + "0" * 64
    add(
        "rejects_unqualified_source_schema_digest",
        materialization_request([invalid_binding]),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {
                "semantic_contract.source_contract_closure_mismatch": 1,
                "semantic_contract.source_contract_resource_unqualified": 1,
                "semantic_contract.source_contract_schema_unqualified": 1,
            },
        },
    )
    mismatched_document = copy.deepcopy(logical_artifact)
    mismatched_document["document"]["schema_version"] = "1.5"
    add(
        "rejects_artifact_contract_version_mismatch",
        materialization_request([mismatched_document]),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.artifact_contract_mismatch": 1},
        },
    )
    related_a = copy.deepcopy(logical)
    related_b = copy.deepcopy(logical)
    related_b["id"] = "01940000-0000-7000-8000-000000000041"
    related_b["alias_id"] = "ADR-L-0003"
    related_b["related_adrs"] = [logical["id"]]
    related_b["decisions"][0].update(
        {"id": "01940000-0000-7000-8000-000000000042", "alias_id": "DEC-0002"}
    )
    related_b["invariants"][0].update(
        {"id": "01940000-0000-7000-8000-000000000043", "alias_id": "INV-0002"}
    )
    related_b["normative_propositions"][0].update(
        {"id": "01940000-0000-7000-8000-000000000044", "alias_id": "NP-0002"}
    )
    related_b["extension_entities"][0].update(
        {"id": "01940000-0000-7000-8000-000000000045", "alias_id": "EXT-0002"}
    )
    related_b["extension_relationships"][0].update(
        {
            "id": "01940000-0000-7000-8000-000000000046",
            "alias_id": "REL-0002",
            "from_entity_id": related_b["id"],
            "to_entity_id": related_b["extension_entities"][0]["id"],
        }
    )
    logical_15_closure = copy.deepcopy(logical_15)
    logical_15_closure["id"] = "01940000-0000-7000-8000-000000000051"
    logical_15_closure["alias_id"] = "ADR-L-0004"
    logical_15_closure["decisions"][0].update(
        {"id": "01940000-0000-7000-8000-000000000052", "alias_id": "DEC-0003"}
    )
    logical_15_closure["invariants"][0].update(
        {"id": "01940000-0000-7000-8000-000000000053", "alias_id": "INV-0003"}
    )
    logical_15_closure["extension_entities"][0].update(
        {"id": "01940000-0000-7000-8000-000000000054", "alias_id": "EXT-0003"}
    )
    logical_15_closure["extension_relationships"][0].update(
        {
            "id": "01940000-0000-7000-8000-000000000055",
            "alias_id": "REL-0003",
            "from_entity_id": logical_15_closure["id"],
            "to_entity_id": logical_15_closure["extension_entities"][0]["id"],
        }
    )
    ordered = [
        artifact("related-a", related_a, "1.6", "logical", "9"),
        artifact("related-b", related_b, "1.6", "logical", "a"),
    ]
    reversed_request = materialization_request(list(reversed(ordered)))
    add(
        "artifact_order_is_semantically_invariant",
        materialization_request(ordered),
        {
            "success": True,
            "outcome": "Materialized",
            "diagnostic_code_counts": {},
            "pairedRequest": reversed_request,
            "assertions": {
                "same_normalized_model_as_pair": True,
                "same_source_contract_closure_as_pair": True,
            },
        },
    )
    add(
        "unavailable_source_basis_is_protocol_valid",
        materialization_request(None, None),
        {
            "success": False,
            "outcome": "Unavailable",
            "diagnostic_code_counts": {"semantic_contract.source_basis_unavailable": 1},
        },
    )
    invalid_extension = copy.deepcopy(logical)
    invalid_extension["extension_entities"][0].pop("rationale")
    add(
        "invalid_extension_entity_is_rejected",
        materialization_request(
            [artifact("invalid-extension", invalid_extension, "1.6", "logical", "b")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    invalid_relationship = copy.deepcopy(logical)
    invalid_relationship["extension_relationships"][0].pop("rationale")
    add(
        "invalid_extension_relationship_is_rejected",
        materialization_request(
            [artifact("invalid-relationship", invalid_relationship, "1.6", "logical", "c")]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    add(
        "legacy_identity_requires_qualification",
        materialization_request(
            [
                artifact(
                    "legacy-identity",
                    {**copy.deepcopy(logical), "id": "legacy-root"},
                    "1.6",
                    "logical",
                    "d",
                )
            ]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    add(
        "normalized_output_retains_unresolved_reference",
        materialization_request(
            [
                artifact(
                    "unresolved-reference",
                    {
                        **copy.deepcopy(logical),
                        "related_adrs": ["01940000-0000-7000-8000-000000000099"],
                    },
                    "1.6",
                    "logical",
                    "e",
                )
            ]
        ),
        {
            "success": True,
            "outcome": "Materialized",
            "diagnostic_code_counts": {},
            "assertions": {"unresolved_count": 1, "normalized_schema_version": "2.3"},
        },
    )
    add(
        "source_contract_closure_is_exact_and_sorted",
        materialization_request(
            [
                logical_artifact,
                artifact("logical-15-closure", logical_15_closure, "1.5", "logical", "f"),
            ]
        ),
        {
            "success": True,
            "outcome": "Materialized",
            "diagnostic_code_counts": {},
            "assertions": {
                "source_contract_versions": ["1.5", "1.6"],
                "closure_resource_keys_are_sorted": True,
            },
        },
    )
    add(
        "diagnostics_are_not_duplicated",
        materialization_request([invalid_binding]),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {
                "semantic_contract.source_contract_closure_mismatch": 1,
                "semantic_contract.source_contract_resource_unqualified": 1,
                "semantic_contract.source_contract_schema_unqualified": 1,
            },
        },
    )
    add(
        "source_contract_binding_rejects_wrong_top_level_schema",
        materialization_request(
            [
                copy.deepcopy(logical_artifact)
                | {"sourceContract": binding("1.6", "physical-system")}
            ]
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {
                "semantic_contract.source_contract_closure_mismatch": 1,
                "semantic_contract.source_contract_schema_mismatch": 1,
            },
        },
    )

    # Retained definitions are deliberately adversarial here.  Every added
    # bundle is independently valid, but its exact member is absent from the
    # admitted SCS.  Materialization must therefore remain byte-for-byte
    # anchored to the selected v1.0/2.3/1.0 member bundles.
    retained_permissive = bundles + [unselected_architecture_permissive]
    retained_strict = bundles + [unselected_architecture_strict]
    invalid_component_with_permissive = copy.deepcopy(physical_component)
    invalid_component_with_permissive["component_specifications"][0]["name"] = 42
    add(
        "unselected_architecture_cannot_weaken_source_validation",
        materialization_request(
            [
                artifact(
                    "unselected-weakening",
                    invalid_component_with_permissive,
                    "1.6",
                    "physical-component",
                    "1",
                )
            ],
            definitions_override=retained_permissive,
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.invalid_source_document": 1},
        },
    )
    add(
        "unselected_architecture_cannot_strengthen_source_validation",
        materialization_request(
            [
                artifact(
                    "unselected-strengthening", physical_component, "1.6", "physical-component", "2"
                )
            ],
            definitions_override=retained_strict,
        ),
        success,
    )
    unselected_binding_artifact = artifact(
        "unselected-binding", physical_component, "1.6", "physical-component", "3"
    )
    unselected_component_digest = next(
        entry["contentDigest"]
        for entry in unselected_architecture_permissive["definition"]["resourceManifest"]
        if entry["canonicalResourceKey"] == physical_component_schema_key
    )
    unselected_binding_artifact["sourceContract"]["schemaResource"][
        "contentDigest"
    ] = unselected_component_digest
    for closure_entry in unselected_binding_artifact["sourceContract"]["resourceClosure"]:
        if closure_entry["canonicalResourceKey"] == physical_component_schema_key:
            closure_entry["contentDigest"] = unselected_component_digest
    add(
        "artifact_binding_to_unselected_schema_digest_is_rejected",
        materialization_request(
            [unselected_binding_artifact], definitions_override=retained_permissive
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {
                "semantic_contract.source_contract_closure_mismatch": 1,
                "semantic_contract.source_contract_resource_unqualified": 1,
                "semantic_contract.source_contract_schema_unqualified": 1,
            },
        },
    )
    base_materialization = materialization_request([copy.deepcopy(logical_artifact)])
    retained_unselected_normalized = bundles + [unselected_normalized]
    unrelated_retained = materialization_request(
        [copy.deepcopy(logical_artifact)], definitions_override=retained_unselected_normalized
    )
    add(
        "unselected_normalized_definition_does_not_change_result",
        base_materialization,
        {
            "success": True,
            "outcome": "Materialized",
            "diagnostic_code_counts": {},
            "pairedRequest": unrelated_retained,
            "pairedAssertions": {
                "same_normalized_model": True,
                "same_source_contract_closure": True,
                "same_authority_state_fingerprint": True,
            },
        },
    )
    retained_order_pair = materialization_request(
        [artifact("definition-order", physical_component, "1.6", "physical-component", "4")],
        definitions_override=list(reversed(retained_permissive)),
    )
    add(
        "retained_definition_order_is_invariant",
        materialization_request(
            [artifact("definition-order", physical_component, "1.6", "physical-component", "4")],
            definitions_override=retained_permissive,
        ),
        {
            "success": True,
            "outcome": "Materialized",
            "diagnostic_code_counts": {},
            "pairedRequest": retained_order_pair,
            "pairedAssertions": {
                "same_normalized_model": True,
                "same_source_contract_closure": True,
                "same_authority_state_fingerprint": True,
            },
        },
    )
    wrong_scf_set = copy.deepcopy(set_artifact)
    wrong_scf_set["members"][0]["semanticContractFingerprint"] = "scf:v1:sha256:" + "0" * 64
    add(
        "selected_member_with_wrong_scf_is_rejected",
        exact_resolution_request(sets_override=[wrong_scf_set]),
        {
            "success": False,
            "diagnostic_code_counts": {
                "semantic_contract.qualification_members_mismatch": 7,
                "semantic_contract.missing_whole_tuple_qualification": 1,
                "semantic_contract.member_fingerprint_mismatch": 2,
                "semantic_contract.scs_id_mismatch": 2,
            },
        },
    )
    missing_architecture_resource = copy.deepcopy(bundles)
    missing_architecture_bundle = next(
        item
        for item in missing_architecture_resource
        if item["definition"]["semanticContractFamily"] == "architecture-interpretation"
    )
    missing_architecture_bundle["resources"] = [
        item
        for item in missing_architecture_bundle["resources"]
        if item["canonicalResourceKey"] != physical_component_schema_key
    ]
    add(
        "missing_selected_member_resource_content_is_rejected",
        exact_resolution_request(definitions_override=missing_architecture_resource),
        {
            "success": False,
            "diagnostic_code_counts": {"semantic_contract.integrity_failure": 2},
        },
    )
    add(
        "selected_cross_member_resource_conflict_is_rejected",
        materialization_request(
            [artifact("selected-resource-conflict", logical, "1.6", "logical", "5")],
            definitions_override=conflicting_definitions,
            set_override=conflicting_set,
            qualifications_override=conflicting_qualifications,
            catalog_override=conflicting_catalog,
            policy_override=conflicting_policy,
            semantic_contract_set_id_override=conflicting_set_id,
        ),
        {
            "success": False,
            "outcome": "Rejected",
            "diagnostic_code_counts": {"semantic_contract.selected_resource_conflict": 1},
        },
    )

    add(
        "physical_system_15_materializes",
        materialization_request(
            [artifact("physical-system-15", physical_system_15, "1.5", "physical-system", "5")]
        ),
        success | {"assertions": {**success["assertions"], "source_contract_versions": ["1.5"]}},
    )
    add(
        "physical_component_15_materializes",
        materialization_request(
            [
                artifact(
                    "physical-component-15", physical_component_15, "1.5", "physical-component", "6"
                )
            ]
        ),
        success | {"assertions": {**success["assertions"], "source_contract_versions": ["1.5"]}},
    )
    add(
        "physical_identity_projection_and_source_coverage",
        materialization_request(
            [
                artifact(
                    "physical-system-rich", physical_system_rich, "1.6", "physical-system", "7"
                ),
                artifact(
                    "physical-component-rich",
                    physical_component_rich,
                    "1.6",
                    "physical-component",
                    "8",
                ),
            ]
        ),
        success
        | {
            "assertions": {
                **success["assertions"],
                "entity_ids": [
                    "01940000-0000-7000-8000-000000000007",
                    "01940000-0000-7000-8000-000000000011",
                    "01940000-0000-7000-8000-000000000021",
                    "01940000-0000-7000-8000-000000000028",
                    "01940000-0000-7000-8000-000000000029",
                ],
                "relationship_type_counts": {
                    "acme:relates_to": 2,
                    "composed_of": 1,
                    "implements": 3,
                },
                "source_coverage_fields": [
                    "component_specifications",
                    "component_topology",
                    "data_flows",
                    "failure_modes",
                    "integration_patterns",
                    "implements_logical",
                    "implements_system",
                    "scalability_strategy",
                    "system",
                    "system_boundaries",
                    "technology_stack",
                ],
            }
        },
    )
    add(
        "physical_component_implementation_becomes_unresolved",
        materialization_request(
            [
                artifact(
                    "physical-component-unresolved",
                    physical_component_unresolved,
                    "1.6",
                    "physical-component",
                    "9",
                )
            ]
        ),
        success
        | {
            "assertions": {
                **success["assertions"],
                # Both implementation references are intentionally outside
                # the admitted entity set in this standalone fixture.  The
                # projection must preserve each as unresolved evidence rather
                # than manufacturing an endpoint or dropping the relation.
                "unresolved_count": 2,
                "relationship_type_counts": {"acme:relates_to": 1},
            }
        },
    )

    add(
        "exact_retained_set_resolution_succeeds",
        exact_resolution_request(),
        {
            "success": True,
            "diagnostic_code_counts": {},
            "resolved": {"semanticContractSetId": set_id},
        },
    )
    add(
        "exact_resolution_ignores_current_pointer",
        exact_resolution_request(include_current=True),
        {
            "success": True,
            "diagnostic_code_counts": {},
            "resolved": {"semanticContractSetId": set_id},
        },
        execution_boundary="raw-core",
    )
    add(
        "unknown_exact_set_is_rejected",
        exact_resolution_request(set_id_override="scs:v1:sha256:" + "0" * 64),
        {
            "success": False,
            "diagnostic_code_counts": {"semantic_contract.exact_set_not_retained": 1},
        },
    )
    tampered_set = copy.deepcopy(set_artifact)
    tampered_members = cast(list[dict[str, Any]], tampered_set["members"])
    tampered_members[0]["semanticContractVersion"] = "9.9"
    add(
        "tampered_exact_set_is_rejected",
        exact_resolution_request(sets_override=[tampered_set]),
        {
            "success": False,
            "diagnostic_code_counts": {
                "semantic_contract.profile_family_mismatch": 1,
                "semantic_contract.qualification_members_mismatch": 7,
                "semantic_contract.missing_whole_tuple_qualification": 1,
                "semantic_contract.missing_definition": 2,
                "semantic_contract.scs_id_mismatch": 2,
            },
        },
    )
    missing_materialization_qualification = [
        item for item in qualifications if item["operation"] != "materialize_architecture"
    ]
    add(
        "missing_whole_set_materialization_qualification_is_rejected",
        exact_resolution_request(qualifications_override=missing_materialization_qualification),
        {
            "success": False,
            "diagnostic_code_counts": {"semantic_contract.missing_whole_tuple_qualification": 1},
        },
    )

    base_materialization = materialization_request([copy.deepcopy(logical_artifact)])
    source_revision_pair = copy.deepcopy(base_materialization)
    source_revision_pair["sourceBasis"]["sourceRevision"] = "revision-2"
    add(
        "source_revision_only_preserves_authority_state_fingerprint",
        base_materialization,
        {
            "success": True,
            "outcome": "Materialized",
            "diagnostic_code_counts": {},
            "pairedRequest": source_revision_pair,
            "pairedAssertions": {
                "same_authority_state_fingerprint": True,
                "same_normalized_model": True,
                "same_source_contract_closure": True,
            },
        },
    )
    semantic_pair = copy.deepcopy(base_materialization)
    semantic_pair["sourceBasis"]["artifacts"][0]["document"]["decisions"][0][
        "summary"
    ] = "A different governed decision."
    add(
        "semantic_change_changes_authority_state_fingerprint",
        base_materialization,
        {
            "success": True,
            "outcome": "Materialized",
            "diagnostic_code_counts": {},
            "pairedRequest": semantic_pair,
            "pairedAssertions": {
                "different_authority_state_fingerprint": True,
                "same_source_contract_closure": True,
            },
        },
    )
    provider_pair = copy.deepcopy(base_materialization)
    provider_pair["authorityProvider"]["architectureNamespace"] = "other"
    add(
        "provider_qualification_change_changes_authority_state_fingerprint",
        base_materialization,
        {
            "success": True,
            "outcome": "Materialized",
            "diagnostic_code_counts": {},
            "pairedRequest": provider_pair,
            "pairedAssertions": {
                "different_authority_state_fingerprint": True,
                "same_source_contract_closure": True,
            },
        },
    )

    # These tuples are the executable diagnostic contract.  Codes alone do
    # not prove deterministic diagnostics: the semantic core must preserve
    # message, path, severity, order, and multiplicity across all hosts.
    diagnostic_details: dict[str, list[tuple[str, str, str, str]]] = {
        "rejects_missing_id": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: required property 'id' is missing",
                "sourceBasis.artifacts[0].document.id",
                "error",
            )
        ],
        "rejects_invalid_alias_id": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: string does not match pattern ^ADR-(L|V|PS|PC)-[0-9]{4}$",
                "sourceBasis.artifacts[0].document.alias_id",
                "error",
            )
        ],
        "rejects_missing_title": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: required property 'title' is missing",
                "sourceBasis.artifacts[0].document.title",
                "error",
            )
        ],
        "rejects_invalid_status": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: value is outside the governed enum",
                "sourceBasis.artifacts[0].document.status",
                "error",
            )
        ],
        "rejects_invalid_created_date": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: string does not match pattern ^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
                "sourceBasis.artifacts[0].document.created_date",
                "error",
            )
        ],
        "rejects_missing_authors": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: required property 'authors' is missing",
                "sourceBasis.artifacts[0].document.authors",
                "error",
            )
        ],
        "rejects_missing_logical_context": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: required property 'context' is missing",
                "sourceBasis.artifacts[0].document.context",
                "error",
            )
        ],
        "rejects_missing_logical_decisions": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: required property 'decisions' is missing",
                "sourceBasis.artifacts[0].document.decisions",
                "error",
            )
        ],
        "rejects_missing_physical_implementation": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: array must contain at least 1 item(s)",
                "sourceBasis.artifacts[0].document.implements_logical",
                "error",
            )
        ],
        "rejects_missing_system_identity": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: expected type object",
                "sourceBasis.artifacts[0].document.system",
                "error",
            )
        ],
        "rejects_missing_component_specification": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: array must contain at least 1 item(s)",
                "sourceBasis.artifacts[0].document.component_specifications",
                "error",
            )
        ],
        "rejects_missing_component_implementation": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: array must contain at least 1 item(s)",
                "sourceBasis.artifacts[0].document.implements_system",
                "error",
            )
        ],
        "rejects_component_name_wrong_type": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: expected type string",
                "sourceBasis.artifacts[0].document.component_specifications[0].name",
                "error",
            )
        ],
        "rejects_component_alias_outside_comp_pattern": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: string does not match pattern ^COMP-[0-9]{4}$",
                "sourceBasis.artifacts[0].document.component_specifications[0].alias_id",
                "error",
            )
        ],
        "rejects_interface_alias_outside_iface_pattern": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: string does not match pattern ^IFACE-[0-9]{4}$",
                "sourceBasis.artifacts[0].document.component_specifications[0].interfaces[0].alias_id",
                "error",
            )
        ],
        "rejects_component_topology_on_physical_component": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: value matches a prohibited schema",
                "sourceBasis.artifacts[0].document",
                "error",
            )
        ],
        "rejects_invalid_nested_generation_context": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: array must contain at least 1 item(s)",
                "sourceBasis.artifacts[0].document.component_specifications[0].generation_context.key_responsibilities",
                "error",
            )
        ],
        "rejects_invalid_physical_system_topology": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: string does not match pattern ^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                "sourceBasis.artifacts[0].document.component_topology.components[0].component_ref",
                "error",
            )
        ],
        "rejects_invalid_system_boundary_structure": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: expected type string",
                "sourceBasis.artifacts[0].document.system_boundaries[0].description",
                "error",
            )
        ],
        "rejects_invalid_data_flow_structure": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: expected type string",
                "sourceBasis.artifacts[0].document.data_flows[0].path[0]",
                "error",
            )
        ],
        "rejects_invalid_integration_pattern_structure": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: string does not match pattern ^TOPO-[A-Z0-9][A-Z0-9-]*$",
                "sourceBasis.artifacts[0].document.integration_patterns[0].components_affected[0]",
                "error",
            )
        ],
        "rejects_invalid_failure_mode_structure": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: value is outside the governed enum",
                "sourceBasis.artifacts[0].document.failure_modes[0].impact",
                "error",
            )
        ],
        "rejects_invalid_np_alias_once": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: string does not match pattern ^NP-[0-9]{4}$",
                "sourceBasis.artifacts[0].document.normative_propositions[0].alias_id",
                "error",
            )
        ],
        "rejects_invalid_normative_force": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: value is outside the governed enum",
                "sourceBasis.artifacts[0].document.normative_propositions[0].normative_force",
                "error",
            )
        ],
        "rejects_normative_proposition_in_15": [
            (
                "semantic_contract.invalid_source_document",
                "authoring 1.5 cannot declare normative_propositions",
                "sourceBasis.artifacts[0].document.normative_propositions",
                "error",
            )
        ],
        "rejects_unqualified_source_schema_digest": [
            (
                "semantic_contract.source_contract_closure_mismatch",
                "source contract closure does not exactly match the applicable authoring schema imports",
                "sourceBasis.artifacts[0].sourceContract.resourceClosure",
                "error",
            ),
            (
                "semantic_contract.source_contract_resource_unqualified",
                "source contract resource is not part of the exact resolved semantic basis with the selected member digest",
                "sourceBasis.artifacts[0].sourceContract.resourceClosure[1]",
                "error",
            ),
            (
                "semantic_contract.source_contract_schema_unqualified",
                "top-level schema resource is not part of the exact resolved semantic basis with the selected member digest",
                "sourceBasis.artifacts[0].sourceContract.schemaResource",
                "error",
            ),
        ],
        "rejects_artifact_contract_version_mismatch": [
            (
                "semantic_contract.artifact_contract_mismatch",
                "document schema_version does not match its artifact-level source-contract binding",
                "sourceBasis.artifacts[0].document.schema_version",
                "error",
            )
        ],
        "unavailable_source_basis_is_protocol_valid": [
            (
                "semantic_contract.source_basis_unavailable",
                "the sealed source basis is unavailable",
                "sourceBasis",
                "error",
            )
        ],
        "invalid_extension_entity_is_rejected": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: required property 'rationale' is missing",
                "sourceBasis.artifacts[0].document.extension_entities[0].rationale",
                "error",
            )
        ],
        "invalid_extension_relationship_is_rejected": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: required property 'rationale' is missing",
                "sourceBasis.artifacts[0].document.extension_relationships[0].rationale",
                "error",
            )
        ],
        "legacy_identity_requires_qualification": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: string does not match pattern ^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                "sourceBasis.artifacts[0].document.id",
                "error",
            )
        ],
        "source_contract_binding_rejects_wrong_top_level_schema": [
            (
                "semantic_contract.source_contract_closure_mismatch",
                "source contract closure does not exactly match the applicable authoring schema imports",
                "sourceBasis.artifacts[0].sourceContract.resourceClosure",
                "error",
            ),
            (
                "semantic_contract.source_contract_schema_mismatch",
                "schemaResource is not the exact top-level authoring schema for adr_type",
                "sourceBasis.artifacts[0].sourceContract.schemaResource.canonicalResourceKey",
                "error",
            ),
        ],
        "unknown_exact_set_is_rejected": [
            (
                "semantic_contract.exact_set_not_retained",
                "the explicitly requested SCS is not present in the retained corpus",
                "semanticContractSetId",
                "error",
            )
        ],
        "tampered_exact_set_is_rejected": [
            (
                "semantic_contract.profile_family_mismatch",
                "requested tuple must contain exactly one member from every participating family",
                "members",
                "error",
            ),
            *[
                (
                    "semantic_contract.qualification_members_mismatch",
                    "qualification members do not exactly match the SCS composition",
                    "qualification.members",
                    "error",
                )
            ]
            * 7,
            (
                "semantic_contract.missing_whole_tuple_qualification",
                "the exact retained SCS is not qualified as a whole for the requested operation and use mode",
                "qualifications",
                "error",
            ),
            (
                "semantic_contract.missing_definition",
                "SCS member has no retained immutable definition",
                "sets.members",
                "error",
            ),
            (
                "semantic_contract.scs_id_mismatch",
                "SCS ID does not match the canonical composition",
                "sets.semanticContractSetId",
                "error",
            ),
            (
                "semantic_contract.scs_id_mismatch",
                "SCS ID does not match the canonical composition",
                "sets.semanticContractSetId",
                "error",
            ),
            (
                "semantic_contract.missing_definition",
                "SCS member has no retained immutable definition",
                "sets[0].members",
                "error",
            ),
        ],
        "missing_whole_set_materialization_qualification_is_rejected": [
            (
                "semantic_contract.missing_whole_tuple_qualification",
                "the exact retained SCS is not qualified as a whole for the requested operation and use mode",
                "qualifications",
                "error",
            ),
        ],
        "diagnostics_are_not_duplicated": [
            (
                "semantic_contract.source_contract_closure_mismatch",
                "source contract closure does not exactly match the applicable authoring schema imports",
                "sourceBasis.artifacts[0].sourceContract.resourceClosure",
                "error",
            ),
            (
                "semantic_contract.source_contract_resource_unqualified",
                "source contract resource is not part of the exact resolved semantic basis with the selected member digest",
                "sourceBasis.artifacts[0].sourceContract.resourceClosure[1]",
                "error",
            ),
            (
                "semantic_contract.source_contract_schema_unqualified",
                "top-level schema resource is not part of the exact resolved semantic basis with the selected member digest",
                "sourceBasis.artifacts[0].sourceContract.schemaResource",
                "error",
            ),
        ],
        "unselected_architecture_cannot_weaken_source_validation": [
            (
                "semantic_contract.invalid_source_document",
                "schema validation failed: expected type string",
                "sourceBasis.artifacts[0].document.component_specifications[0].name",
                "error",
            ),
        ],
        "artifact_binding_to_unselected_schema_digest_is_rejected": [
            (
                "semantic_contract.source_contract_closure_mismatch",
                "source contract closure does not exactly match the applicable authoring schema imports",
                "sourceBasis.artifacts[0].sourceContract.resourceClosure",
                "error",
            ),
            (
                "semantic_contract.source_contract_resource_unqualified",
                "source contract resource is not part of the exact resolved semantic basis with the selected member digest",
                "sourceBasis.artifacts[0].sourceContract.resourceClosure[2]",
                "error",
            ),
            (
                "semantic_contract.source_contract_schema_unqualified",
                "top-level schema resource is not part of the exact resolved semantic basis with the selected member digest",
                "sourceBasis.artifacts[0].sourceContract.schemaResource",
                "error",
            ),
        ],
        "selected_member_with_wrong_scf_is_rejected": [
            *[
                (
                    "semantic_contract.qualification_members_mismatch",
                    "qualification members do not exactly match the SCS composition",
                    "qualification.members",
                    "error",
                )
            ]
            * 7,
            (
                "semantic_contract.missing_whole_tuple_qualification",
                "the exact retained SCS is not qualified as a whole for the requested operation and use mode",
                "qualifications",
                "error",
            ),
            *[
                (
                    "semantic_contract.member_fingerprint_mismatch",
                    "SCS member fingerprint does not match the retained immutable definition",
                    "sets.members",
                    "error",
                )
            ]
            * 2,
            *[
                (
                    "semantic_contract.scs_id_mismatch",
                    "SCS ID does not match the canonical composition",
                    "sets.semanticContractSetId",
                    "error",
                )
            ]
            * 2,
        ],
        "missing_selected_member_resource_content_is_rejected": [
            *[
                (
                    "semantic_contract.integrity_failure",
                    "definition resource closure is incomplete or invalid",
                    "definitions[2].resources",
                    "error",
                )
            ]
            * 2,
        ],
        "selected_cross_member_resource_conflict_is_rejected": [
            (
                "semantic_contract.selected_resource_conflict",
                "selected resource normalized-model/2.3/schema/normalized-architecture-model.schema has conflicting identity or canonical bytes across exact SCS members",
                "definitions.normalized-model.resourceManifest",
                "error",
            )
        ],
    }
    for case in cases:
        expected = case["expected"]
        details = diagnostic_details.get(case["name"], [])
        if not expected["success"]:
            assert details, f"missing exact diagnostic tuple fixture for {case['name']}"
        expected["diagnostic_codes"] = [item[0] for item in details]
        expected["diagnostic_messages"] = [item[1] for item in details]
        expected["diagnostic_paths"] = [item[2] for item in details]
        expected["diagnostic_severities"] = [item[3] for item in details]

    assert len(cases) >= 50
    forbidden_vector_terms = ("slice", "phase", "wave", "tranche")
    assert not any(
        any(term in case["name"].lower() for term in forbidden_vector_terms) for case in cases
    )
    write_json(
        ROOT
        / "contracts"
        / "semantic-core"
        / "v1.1"
        / "vectors"
        / "architecture-materialization.json",
        {"vectorContractVersion": "1.1", "cases": cases},
    )
    # The v1.0 governance vector is a compatibility fixture.  It is retained
    # byte-for-byte while the v1.1 profile/qualification additions are covered
    # by the dedicated semantic-core v1.1 vectors.


if __name__ == "__main__":
    main()
