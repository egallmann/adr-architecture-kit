"""Generate the committed Slice B semantic-contract definitions and mirrors.

The canonical resources live under ``contracts``.  This script only assembles
content-addressed manifests and package mirrors; it does not define semantic
rules.  Fingerprints are calculated with the repository's RFC 8785 dependency
so the generated known-answer values use the same canonical JSON contract as
the public Python tooling.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import rfc8785


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "contracts" / "semantic-contract" / "v1.0"
RESOURCES = CANONICAL / "resources"
BUNDLED = ROOT / "src" / "adr_kit" / "semantic_contract" / "v1_0"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def resource(key: str, filename: str, role: str, dependencies: list[str] | None = None) -> dict[str, Any]:
    value = read_json(RESOURCES / filename)
    return {
        "canonicalResourceKey": key,
        "contentDigest": digest(value),
        "role": role,
        "dependencies": [
            {"canonicalResourceKey": dep, "contentDigest": manifest_digest(dep)}
            for dep in dependencies or []
        ],
    }


RESOURCE_DIGESTS: dict[str, str] = {}


def manifest_digest(key: str) -> str:
    if key not in RESOURCE_DIGESTS:
        filename = key.replace("/", "-") + ".json"
        if not (RESOURCES / filename).is_file():
            filename = filename.replace("-1.0-", "-")
        RESOURCE_DIGESTS[key] = digest(read_json(RESOURCES / filename))
    return RESOURCE_DIGESTS[key]


def definition(family: str, manifest: list[dict[str, Any]], frozen: list[str]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "semanticContractFamily": family,
        "semanticContractVersion": "1.0" if family != "normalized-model" else "2.3",
        "fingerprintScheme": "scf:v1:sha256",
        "resourceManifest": sorted(manifest, key=lambda item: item["canonicalResourceKey"]),
        "frozenNormativeConformanceResources": sorted(frozen),
    }
    preimage = {"scheme": "adr-kit.semantic-contract/v1", "definition": value}
    value["semanticContractFingerprint"] = "scf:v1:sha256:" + hashlib.sha256(
        rfc8785.dumps(preimage)
    ).hexdigest()
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    # Prime the digest table before constructing dependency edges.
    for path in RESOURCES.glob("*.json"):
        key = path.stem.replace("-", "/", 2)
        if key not in RESOURCE_DIGESTS:
            RESOURCE_DIGESTS[key] = digest(read_json(path))

    normalized_schema_files = [
        "normalized-architecture-model.schema",
        "normalized-entity-registry.schema",
        "normalized-entity.schema",
        "relationship-record.schema",
        "relationship-registry.schema",
        "unresolved-registry.schema",
    ]
    normalized_keys = [f"normalized-model/2.3/schema/{name}" for name in normalized_schema_files]
    normalized_manifest = [
        resource(key, key.replace("/", "-") + ".json", "normalized-model-schema")
        for key in normalized_keys
    ]
    normalized_conformance_key = "normalized-model/2.3/conformance"
    normalized_manifest.append(
        resource(
            normalized_conformance_key,
            normalized_conformance_key.replace("/", "-") + ".json",
            "normalized-model-conformance",
            normalized_keys,
        )
    )

    normative_keys = [
        "normative-semantics/1.0/definition",
        "normative-semantics/1.0/conformance",
    ]
    normative_manifest = [
        resource(normative_keys[0], "normative-semantics-definition.json", "normative-definition"),
        resource(normative_keys[1], "normative-semantics-conformance.json", "normative-conformance", [normative_keys[0]]),
    ]

    source_keys: list[str] = []
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
            source_keys.append(key)
            source_manifest.append(resource(key, key.replace("/", "-") + ".json", "source-contract-schema"))

    architecture_keys = [
        "architecture-interpretation/1.0/rules",
        "architecture-interpretation/1.0/conformance",
    ]
    architecture_manifest = [
        resource(architecture_keys[0], "architecture-interpretation-rules.json", "interpretation-rule", source_keys),
        resource(architecture_keys[1], "architecture-interpretation-conformance.json", "interpretation-conformance", [architecture_keys[0]]),
        *source_manifest,
    ]

    definitions = {
        "normalized-model.json": definition("normalized-model", normalized_manifest, [normalized_conformance_key]),
        "normative-semantics.json": definition("normative-semantics", normative_manifest, [normative_keys[1]]),
        "architecture-interpretation.json": definition("architecture-interpretation", architecture_manifest, [architecture_keys[1]]),
    }
    for name, value in definitions.items():
        write_json(CANONICAL / "definitions" / name, value)
        write_json(BUNDLED / name, value)

    for path in (CANONICAL / "semantic-contract-version.schema.json", CANONICAL / "resource-manifest-entry.schema.json"):
        target = BUNDLED / path.name
        target.write_bytes(path.read_bytes())
    for path in RESOURCES.glob("*.json"):
        target = BUNDLED / "resources" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())


if __name__ == "__main__":
    main()
