"""Assemble current candidate commitments from maintained canonical inputs.

This utility does not author rules, reconstruct predecessors, select capabilities,
or establish semantic correctness. Callers independently qualify semantics before
writing the already closure-verified definition and deterministic package mirrors.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
from functools import lru_cache
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
    current_candidate = (family, version) in {
        ("architecture-interpretation", "1.5"),
        ("authoring-construction", "1.5"),
        ("normalized-model", "2.5"),
    }
    if name == "contract":
        paths = [
            base / "contract.json",
            root / "contracts/semantic-contract/v1.0/definitions" / f"{family}-{version}.json",
        ]
    elif parts[2] == "schema" and len(parts) == 4:
        paths = [root / "schema" / family / f"v{version}" / f"{parts[3]}.json"]
    elif key == "normalized-model/2.5/conformance":
        # NM's maintained conformance input already lives here; unlike an AI/ACC
        # flattened mirror this file is not generated from another current input.
        paths = [
            root
            / "contracts/semantic-contract/v1.0/resources/normalized-model-2.5-conformance.json"
        ]
    else:
        paths = [base / ("schema.json" if name == "schema" else f"resources/{name}.json")]
    # Exact canonical immutable dependency resources remain valid inputs. This is
    # not a predecessor-version or packaged-resource fallback.
    flat = root / "contracts/semantic-contract/v1.0/resources"
    if not current_candidate:
        paths.append(flat / (key.replace("/", "-") + ".json"))
    for path in paths:
        if path.is_file():
            return _load(path)
    if not current_candidate and len(parts) == 3:
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


# Historical evidence is read at its recorded Git revision, never resolved through
# the current candidate's same-version paths or package mirrors.
HISTORICAL_REVISION = "6ddc8c2b6d66531ff3ecefb0bba7b15616ac4f0c"


@lru_cache(maxsize=4)
def _historical_files(root: Path, revision: str) -> dict[str, bytes]:
    raw = subprocess.check_output(
        ["git", "archive", revision, "contracts/semantic-contract/v1.0"], cwd=root
    )
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith(".json"):
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("missing historical archive payload: " + member.name)
                files[member.name] = stream.read()
    return files


def historical_resource(root: Path, key: str) -> Any:
    files = _historical_files(root.resolve(), HISTORICAL_REVISION)
    family, version, name = key.split("/", 2)
    base = "contracts/semantic-contract/v1.0/"
    paths = ([base + f"definitions/{family}-{version}.json"] if name == "contract" else []) + [
        base + "resources/" + key.replace("/", "-") + ".json"
    ]
    paths.append(base + f"resources/{family}-{name}.json")
    path = next((p for p in paths if p in files), None)
    if path is None:
        raise ValueError("missing recorded historical resource: " + key)
    return json.loads(files[path])


def dependency_closure(root: Path, roots: dict[str, Any], reader: Any) -> set[str]:
    """Follow actual declared/ref edges; a definition is not a manifest import."""
    pending = set(roots)
    selected: set[str] = set()
    while pending:
        key = min(pending)
        pending.remove(key)
        if key in selected:
            continue
        selected.add(key)
        value = roots[key] if key in roots else reader(root, key)
        pending.update(discovered_dependencies(key, value) - selected)
    return selected


def direct_references(key: str, value: Any, known: set[str]) -> set[str]:
    """Explicit resource selectors, with only closed historical evidence excluded.

    Callers independently verify those exact evidence records. All schema $refs
    remain operative, including refs selecting historical validation fragments.
    """
    historical_fields = {
        "architecture-interpretation/1.5/rules": {"inherits"},
        "architecture-interpretation/1.5/conformance": {"inherited_conformance", "inherited_cases"},
        "authoring-construction/1.5/conformance": {"inherited_cases"},
        "authoring-construction/1.5/compatibility": {"historical_definitions"},
    }
    operative = {
        k: v
        for k, v in value.items()
        if k not in historical_fields.get(key, set()) | {"semanticDependencies"}
    }
    found = discovered_dependencies(key, operative)

    def visit(node: Any, path: tuple[str, ...] = ()) -> None:
        # This schema constraint checks the conformance resource's *name*, not
        # its contents. The definition independently selects that resource and
        # conformance consumes the schema, so reversing the audit edge here
        # would create a false schema/conformance dependency cycle.
        if key == "authoring-construction/1.5/schema" and path == (
            "$defs",
            "contract_document",
            "properties",
            "frozenNormativeConformanceResources",
            "const",
        ):
            return
        if isinstance(node, str) and node in known:
            found.add(node)
        elif isinstance(node, dict):
            for k, v in node.items():
                visit(v, (*path, k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                visit(v, (*path, str(i)))

    visit(operative)
    if key + ".schema" in known:
        found.add(key + ".schema")
    # The conformance audit reads these governing policies independently of the
    # example fixture payloads; they are real dependencies, not history imports.
    if key == "architecture-interpretation/1.5/conformance":
        found.update(
            "architecture-interpretation/1.5/" + n
            for n in ("rules", "required-output-derivations", "identity-representation-recipes")
        )
    elif key == "authoring-construction/1.5/conformance":
        found.update(
            "authoring-construction/1.5/" + n
            for n in (
                "rules",
                "schema",
                "compatibility",
                "composition-bindings",
                "composition-bindings.schema",
            )
        )
        found.add("authoring-construction/1.3/ledger.schema")
    return found - {key}
