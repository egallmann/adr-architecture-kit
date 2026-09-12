"""Generate the committed semantic-contract definitions and mirrors.

The canonical resources live under ``contracts``.  This script only assembles
content-addressed manifests and package mirrors; it does not define semantic
rules.  Fingerprints are calculated with the repository's RFC 8785 dependency
so the generated known-answer values use the same canonical JSON contract as
the public Python tooling.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

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
            {"semanticContractFamily": "architecture-interpretation", "semanticContractVersion": "1.0", "cardinality": 1},
            {"semanticContractFamily": "normalized-model", "semanticContractVersion": "2.3", "cardinality": 1},
            {"semanticContractFamily": "normative-semantics", "semanticContractVersion": "1.0", "cardinality": 1},
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
    policy = {"policySchemaVersion": "1.0", "policyRevision": "policy:v1:1", "entries": policy_entries}
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
                    {"canonicalResourceKey": entry["canonicalResourceKey"], "content": resource_value(entry["canonicalResourceKey"])}
                    for entry in value["resourceManifest"]
                ],
            }
        )
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
            "request": {"core_contract_version": "1.0", "operation": "validate_semantic_contract_profile", "profile": profile},
            "expected": {"success": True},
        },
        {
            "name": "profile_rejects_missing_participating_family",
            "request": {"core_contract_version": "1.0", "operation": "validate_semantic_contract_profile", "profile": {**profile, "participatingFamilies": profile["participatingFamilies"][:2]}},
            "expected": {"success": False, "diagnostic_codes": ["semantic_contract.profile_family_mismatch"]},
        },
        {
            "name": "exact_whole_tuple_qualification_succeeds",
            "request": {"core_contract_version": "1.0", "operation": "validate_semantic_contract_qualification", "profile": profile, "members": members, "targetOperation": "qualify_tuple", "direction": "none", "qualification": by_operation["qualify_tuple"]},
            "expected": {"success": True},
        },
        {
            "name": "qualification_rejects_wrong_scs_id",
            "request": {"core_contract_version": "1.0", "operation": "validate_semantic_contract_qualification", "profile": profile, "members": members, "targetOperation": "qualify_tuple", "direction": "none", "qualification": {**by_operation["qualify_tuple"], "semanticContractSetId": "scs:v1:sha256:" + "0" * 64}},
            "expected": {"success": False, "diagnostic_codes": ["semantic_contract.qualification_set_mismatch"]},
        },
        {
            "name": "assembly_is_deterministic_no_op_for_retained_set",
            "request": {"core_contract_version": "1.0", "operation": "assemble_semantic_contract_set", "targetOperation": "assemble_set", "direction": "none", "requestedMembers": members, "qualification": by_operation["assemble_set"], "retainedSets": [set_artifact], "retainedQualifications": qualifications, **common},
            "expected": {"success": True, "noOp": True, "semanticContractSetId": set_id},
        },
        {
            "name": "assembly_rejects_missing_whole_tuple_qualification",
            "request": {"core_contract_version": "1.0", "operation": "assemble_semantic_contract_set", "targetOperation": "assemble_set", "direction": "none", "requestedMembers": members, "qualification": by_operation["assemble_set"], "retainedSets": [], "retainedQualifications": [], **common},
            "expected": {"success": False, "diagnostic_codes": ["semantic_contract.missing_whole_tuple_qualification"]},
        },
        {
            "name": "complete_retained_corpus_validates",
            "request": {"core_contract_version": "1.0", "operation": "validate_semantic_contract_corpus", "sets": [set_artifact], "qualifications": qualifications, **common},
            "expected": {"success": True},
        },
        {
            "name": "corpus_rejects_duplicate_stored_composition",
            "request": {"core_contract_version": "1.0", "operation": "validate_semantic_contract_corpus", "sets": [set_artifact, set_artifact], "qualifications": qualifications, **common},
            "expected": {"success": False, "diagnostic_codes": ["semantic_contract.duplicate_stored_composition"]},
        },
        {
            "name": "current_pointer_resolves_to_exact_set",
            "request": {"core_contract_version": "1.0", "operation": "resolve_current_semantic_contract_set", "targetOperation": "resolve_current", "direction": "none", "current": current, "sets": [set_artifact], "qualifications": qualifications, **common},
            "expected": {"success": True, "resolved": {"semanticContractSetId": set_id}},
        },
        {
            "name": "current_pointer_missing_set_fails_closed",
            "request": {"core_contract_version": "1.0", "operation": "resolve_current_semantic_contract_set", "targetOperation": "resolve_current", "direction": "none", "current": {**current, "semanticContractSetId": "scs:v1:sha256:" + "0" * 64}, "sets": [], "qualifications": [], **common},
            "expected": {"success": False, "diagnostic_codes": ["semantic_contract.invalid_current_selection"]},
        },
    ]
    # The v1.0 governance vector is a compatibility fixture.  It is retained
    # byte-for-byte while the v1.1 profile/qualification additions are covered
    # by the dedicated semantic-core v1.1 vectors.


if __name__ == "__main__":
    main()
