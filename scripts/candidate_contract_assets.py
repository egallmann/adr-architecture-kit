"""Assemble current candidate commitments from maintained canonical inputs.

This utility does not author rules, reconstruct predecessors, select capabilities,
or establish semantic correctness. Callers independently qualify semantics before
writing the already closure-verified definition and deterministic package mirrors.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.generate_semantic_contract_assets import (
    definition,
    digest,
    discovered_dependencies,
    write_json,
)


def _load(path: Path) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate canonical JSON member: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def canonical_resource(root: Path, key: str) -> Any:
    parts = key.split("/")
    if (
        len(parts) < 3
        or re.fullmatch(r"[a-z][a-z0-9-]*", parts[0]) is None
        or re.fullmatch(r"[0-9]+\.[0-9]+", parts[1]) is None
        or any(
            p in {"", ".", ".."} or re.fullmatch(r"[A-Za-z0-9_.-]+", p) is None for p in parts[2:]
        )
    ):
        raise ValueError(f"invalid canonical resource key: {key}")
    family, version = parts[:2]
    name = "/".join(parts[2:])
    base = root / "contracts" / family / f"v{version}"
    if name == "contract":
        paths = [
            base / "contract.json",
            root / "contracts/semantic-contract/v1.0/definitions" / f"{family}-{version}.json",
        ]
    elif parts[2] == "schema" and len(parts) == 4:
        paths = [root / "schema" / family / f"v{version}" / f"{parts[3]}.json"]
    else:
        paths = [base / ("schema.json" if name == "schema" else f"resources/{name}.json")]
    # Exact canonical immutable dependency resources remain valid inputs. This is
    # not a predecessor-version or packaged-resource fallback.
    flat = root / "contracts/semantic-contract/v1.0/resources"
    paths.append(flat / (key.replace("/", "-") + ".json"))
    for path in paths:
        if path.is_file():
            return _load(path)
    if len(parts) == 3:
        legacy = flat / f"{family}-{name}.json"
        if legacy.is_file():
            value = _load(legacy)
            # Released versionless filenames identify their exact version in
            # their content. They must never satisfy a different requested key.
            if (value.get("semanticContractFamily"), value.get("semanticContractVersion")) == (
                family,
                version,
            ):
                return value
    raise ValueError(f"missing exact canonical resource: {key}")


def assemble(root: Path, family: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if family not in {"architecture-interpretation", "authoring-construction"}:
        raise ValueError("unsupported current candidate")
    prefix = f"{family}/1.5/"
    source = root / "contracts" / family / "v1.5"
    draft = _load(source / "contract.json")
    if (draft["semanticContractFamily"], draft["semanticContractVersion"]) != (family, "1.5"):
        raise ValueError("wrong candidate source identity")
    # Manifest roles are authored authority, not guessed from names. Digests,
    # dependency edges and the enclosing SCF are derived from actual references.
    roles = {m["canonicalResourceKey"]: m["role"] for m in draft["resourceManifest"]}
    if len(roles) != len(draft["resourceManifest"]):
        raise ValueError("duplicate authored resource role")
    own = {prefix + p.stem: _load(p) for p in sorted((source / "resources").glob("*.json"))}
    if (source / "schema.json").is_file():
        own[prefix + "schema"] = _load(source / "schema.json")
    if not own or draft["frozenNormativeConformanceResources"] != [prefix + "conformance"]:
        raise ValueError("missing or ambiguous candidate conformance selection")
    contents: dict[str, Any] = {}
    pending = set(own)
    while pending:
        key = min(pending)
        pending.remove(key)
        if key == prefix + "contract":
            raise ValueError("self-referential candidate closure")
        if key not in roles:
            raise ValueError(f"missing authored resource role: {key}")
        contents[key] = own[key] if key in own else canonical_resource(root, key)
        pending.update(discovered_dependencies(key, contents[key]) - contents.keys())
    manifest = [
        {
            "canonicalResourceKey": key,
            "contentDigest": digest(value),
            "role": roles[key],
            "dependencies": [
                {"canonicalResourceKey": dep, "contentDigest": digest(contents[dep])}
                for dep in sorted(discovered_dependencies(key, value))
            ],
        }
        for key, value in sorted(contents.items())
    ]
    result = definition(family, manifest, [prefix + "conformance"], version="1.5")
    from adr_kit.semantic_contract import (
        validate_semantic_resource_closure,
        verify_semantic_contract,
    )

    closure = validate_semantic_resource_closure(
        result, [{"canonicalResourceKey": k, "content": v} for k, v in contents.items()]
    )
    if (
        not verify_semantic_contract(result).success
        or not closure.success
        or not closure.closure_valid
    ):
        raise ValueError("candidate closure qualification failed")
    return result, contents


def distribute(root: Path, family: str, result: dict[str, Any], contents: dict[str, Any]) -> None:
    """Write derived views only after independent semantic qualification succeeds."""
    prefix = f"{family}/1.5/"
    for key, value in sorted(contents.items()):
        if not key.startswith(prefix):
            continue
        filename = key.replace("/", "-") + ".json"
        source = root / "contracts" / family / "v1.5"
        name = key.removeprefix(prefix)
        data = (
            source / ("schema.json" if name == "schema" else f"resources/{name}.json")
        ).read_bytes()
        for directory in (
            root / "contracts/semantic-contract/v1.0/resources",
            root / "src/adr_kit/semantic_contract/v1_0/resources",
        ):
            (directory / filename).write_bytes(data)
    for path in (
        root / "contracts" / family / "v1.5/contract.json",
        root / "contracts/semantic-contract/v1.0/definitions" / f"{family}-1.5.json",
        root / "src/adr_kit/semantic_contract/v1_0/definitions" / f"{family}-1.5.json",
        root / "src/adr_kit/semantic_contract/v1_0" / f"{family}-1.5.json",
    ):
        write_json(path, result)
