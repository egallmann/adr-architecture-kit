"""Discover exact packaged authority; never promote or repair a package payload."""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile
import urllib.request
from urllib.parse import unquote, urlparse, urljoin
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, cast
import rfc8785

from scripts.check_semantic_contract_lifecycle_design import (
    canonical_bytes,
    digest,
    qualify_inventory,
    qualify_released_evidence,
    read_json,
    require,
)

ROOT = Path(__file__).resolve().parents[1]


def released_payloads(classification: dict[str, Any], root: Path) -> Iterator[bytes]:
    """Exact positive registry evidence, cached only under its verified SHA-256.

    Never infer release from a tag/tree/version, and never trust cached evidence
    without checking the accepted artifact digest again.
    """
    cache = root / ".tmp/released-authority-evidence"
    cache.mkdir(parents=True, exist_ok=True)
    for entry in classification["release_evidence"]:
        require(
            re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is not None,
            "invalid released evidence identity",
        )
        path = cache / entry["sha256"]
        if path.is_file():
            payload = path.read_bytes()
        else:
            registry = entry["registry"]
            require(
                registry.startswith(
                    (
                        "https://pypi.org/pypi/adr-architecture-kit/",
                        "https://registry.npmjs.org/@system-of-thought%2fadr-kit/",
                    )
                ),
                "unsupported release-evidence registry",
            )
            with urllib.request.urlopen(registry, timeout=60) as response:
                metadata = read_json(response.read(8 * 1024 * 1024))
            if entry["id"].startswith("pypi-"):
                matches = [
                    u
                    for u in metadata["urls"]
                    if u["filename"] == entry["artifact"]
                    and u["digests"]["sha256"] == entry["sha256"]
                ]
                require(len(matches) == 1, "ambiguous or changed released Python artifact")
                url = matches[0]["url"]
                require(
                    url.startswith("https://files.pythonhosted.org/"),
                    "untrusted PyPI artifact origin",
                )
            else:
                url = metadata["dist"]["tarball"]
                require(
                    url.startswith("https://registry.npmjs.org/@system-of-thought/adr-kit/-/"),
                    "untrusted npm artifact origin",
                )
            with urllib.request.urlopen(url, timeout=60) as response:
                payload = response.read(64 * 1024 * 1024 + 1)
            require(len(payload) <= 64 * 1024 * 1024, "released evidence size limit")
        require(
            hashlib.sha256(payload).hexdigest() == entry["sha256"],
            "released package evidence mutation",
        )
        if not path.exists():
            path.write_bytes(payload)
        yield payload


def json_identity(value: Any) -> str:
    """Comparison/cache key only; content addressing uses the shared Rust core."""
    return rfc8785.dumps(value).decode("utf-8")


def archive_members(data: bytes, wheel: bool) -> dict[str, bytes]:
    """Read bounded regular files, rejecting traversal, links and duplicate names."""
    result: dict[str, bytes] = {}
    total = 0
    if wheel:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = [(x.orig_filename, x.file_size, x.is_dir(), x) for x in archive.infolist()]
            for name, size, directory, item in entries:
                require((item.external_attr >> 16) & 0o170000 != 0o120000, "archive symlink")
                total += size
                require(total <= 512 * 1024 * 1024, "archive expansion limit")
                _member_name(name, result, directory)
                if not directory:
                    result[name] = archive.read(item)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive:
                total += member.size
                require(total <= 512 * 1024 * 1024, "archive expansion limit")
                require(member.isdir() or member.isfile(), "archive links or special members")
                _member_name(member.name, result, member.isdir())
                if member.isfile():
                    stream = archive.extractfile(member)
                    require(stream is not None, "unreadable archive member")
                    assert stream is not None
                    result[member.name] = stream.read()
    return result


def _member_name(name: str, seen: dict[str, bytes], directory: bool) -> None:
    path = PurePosixPath(name)
    require(
        not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and ":" not in name
        and str(path) == name.rstrip("/"),
        "unsafe archive member",
    )
    if not directory:
        require(name.casefold() not in {p.casefold() for p in seen}, "duplicate archive member")


def json_objects(text: str) -> Iterator[tuple[int, Any]]:
    """Discover complete JSON objects in generated JS and WASM string data."""
    decoder = json.JSONDecoder(object_pairs_hook=_unique)
    offset = 0
    while (start := text.find("{", offset)) >= 0:
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError, UnicodeError:
            offset = start + 1
            continue
        yield start, value
        offset = end


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON member")
        result[key] = value
    return result


def _uleb(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 35, 7):
        require(offset < len(data), "truncated WASM integer")
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ValueError("invalid WASM integer")


def wasm_data(data: bytes) -> Iterator[tuple[int, bytes]]:
    """Inspect the standard data section; do not execute an arbitrary package WASM."""
    require(data[:8] == b"\x00asm\x01\x00\x00\x00", "invalid WASM dialect")
    position = 8
    found = False
    while position < len(data):
        section = data[position]
        size, start = _uleb(data, position + 1)
        end = start + size
        require(end <= len(data), "truncated WASM section")
        if section == 11:
            require(not found, "duplicate WASM data section")
            found = True
            count, p = _uleb(data, start)
            for index in range(count):
                flags, p = _uleb(data, p)
                require(flags in (0, 1, 2), "unsupported WASM data segment")
                if flags == 2:
                    _, p = _uleb(data, p)
                if flags != 1:
                    require(data[p] == 0x41, "unsupported WASM data offset expression")
                    _, p = _uleb(data, p + 1)
                    require(data[p] == 0x0B, "invalid WASM data expression")
                    p += 1
                length, p = _uleb(data, p)
                require(p + length <= end, "truncated WASM data")
                yield index, data[p : p + length]
                p += length
            require(p == end, "unaccounted WASM data bytes")
        position = end
    require(found, "missing WASM authority data")


class AuthorityIndex:
    """Exact source-qualified meanings, including schema-only/embedded authorities."""

    def __init__(self, root: Path):
        from adr_kit.semantic_contract import (
            validate_semantic_resource_closure,
            verify_semantic_contract,
        )

        self.values: dict[str, list[tuple[str, str, str, str]]] = {}
        self.definitions: dict[tuple[str, str], dict[str, Any]] = {}
        self.required: dict[tuple[str, str], list[dict[str, str]]] = {}
        self.schema_dependencies: dict[str, set[str]] = {}
        self.control_values: set[str] = set()
        classification = read_json(
            (root / "adrs/migrations/semantic-contract-lifecycle-classification.json").read_bytes()
        )
        qualify_released_evidence(classification, root)
        self.released = {(r["family"], r["version"]) for r in classification["released_contracts"]}
        # Accepted positive release evidence also protects resource-qualified
        # authorities. Check their exact released source bytes, not a version
        # number or mere presence on a development branch.
        released_paths = {
            r["path"]
            for r in classification["released_schema_files"]
            + classification["embedded_resource_authorities"]
        }
        release_source = classification["release_evidence"][0]["source_commit"]
        retained_source = subprocess.check_output(
            ["git", "archive", "--format=tar", release_source, "contracts", "schema"], cwd=root
        )
        released_bytes: dict[str, bytes] = {}
        with tarfile.open(fileobj=io.BytesIO(retained_source), mode="r:") as archive:
            for item in archive:
                if item.isfile():
                    stream = archive.extractfile(item)
                    assert stream is not None
                    released_bytes[item.name] = stream.read()
        canonical = root / "contracts/semantic-contract/v1.0"
        definition_files = sorted((canonical / "definitions").glob("*.json"))
        definitions = [read_json(p.read_bytes()) for p in definition_files]
        definition_paths = {
            (d["semanticContractFamily"], d["semanticContractVersion"]): p.relative_to(
                root
            ).as_posix()
            for p, d in zip(definition_files, definitions, strict=True)
        }
        by_identity = {
            (d["semanticContractFamily"], d["semanticContractVersion"]): d for d in definitions
        }
        require(
            all(
                by_identity[d["semanticContractFamily"], d["semanticContractVersion"]] == d
                for d in definitions
            ),
            "conflicting source definitions",
        )
        for definition in by_identity.values():
            family, version = (
                definition["semanticContractFamily"],
                definition["semanticContractVersion"],
            )
            identity = family, version
            require(identity not in self.definitions, "duplicate source definition")
            resources = []
            for entry in definition["resourceManifest"]:
                key = entry["canonicalResourceKey"]
                resource_path = canonical / "resources" / (key.replace("/", "-") + ".json")
                if not resource_path.is_file() and len(key.split("/")) == 3:
                    f, _, name = key.split("/")
                    resource_path = canonical / "resources" / f"{f}-{name}.json"
                if resource_path.is_file():
                    value = read_json(resource_path.read_bytes())
                elif key.endswith("/contract") and tuple(key.split("/")[:2]) in by_identity:
                    value = by_identity[tuple(key.split("/")[:2])]
                elif key.startswith("authoring/1.7/schema/"):
                    value = read_json(
                        (
                            root / "schema/authoring/v1.7" / (key.split("/")[-1] + ".json")
                        ).read_bytes()
                    )
                else:
                    raise ValueError(f"missing canonical resource {key}")
                resources.append({"canonicalResourceKey": key, "content": value})
                self.add(value, family, version, key, entry["contentDigest"])
            verified = validate_semantic_resource_closure(definition, resources)
            require(
                verify_semantic_contract(definition).success
                and verified.success
                and verified.closure_valid is True,
                f"source closure {identity}",
            )
            self.definitions[identity] = definition
            self.required[identity] = [
                {"key": e["canonicalResourceKey"], "digest": e["contentDigest"]}
                for e in definition["resourceManifest"]
            ]
            self.add(
                definition,
                family,
                version,
                definition_paths[identity],
                digest(canonical_bytes(definition)),
            )
        # Canonical resources without an SCF (protocol, ADC, CEC and older schemas)
        # are still authority. They are never assigned an invented fingerprint.
        for directory in (root / "contracts", root / "schema"):
            for path in sorted(directory.rglob("*.json")):
                relative = path.relative_to(directory).as_posix()
                if "/vectors/" in relative:
                    # Adversarial protocol input fixtures are not selected authority.
                    continue
                value = read_json(path.read_bytes())
                # Catalog/policy/current/host-capability metadata is source-bound
                # package evidence, not semantic meaning promoted by mere presence.
                framework_member = relative.startswith(
                    "semantic-contract/v1.0/"
                ) and "/" in relative.removeprefix("semantic-contract/v1.0/")
                if (
                    directory.name == "contracts" and relative.startswith("compatibility/")
                ) or framework_member:
                    if json_identity(value) not in self.values:
                        self.control_values.add(json_identity(value))
                    continue
                match = re.match(r"([^/]+)/v(\d+\.\d+)/(.*)\.json$", relative)
                if match:
                    family, version, name = match.groups()
                    protected_protocol = family == "semantic-core" and version in {
                        "1.0",
                        "1.1",
                        "1.2",
                        "1.3",
                    }
                    protected_dependency = (family, version) in {
                        ("authoring-domain", "1.0"),
                        ("authoring-domain", "1.1"),
                        ("custom-entity", "1.0"),
                    }
                    source_path = path.relative_to(root).as_posix()
                    if source_path in released_paths or protected_protocol or protected_dependency:
                        require(
                            source_path in released_bytes
                            and path.read_bytes().replace(b"\r\n", b"\n")
                            == released_bytes[source_path].replace(b"\r\n", b"\n"),
                            f"released resource changed: {source_path}",
                        )
                        self.released.add((family, version))
                    value = read_json(path.read_bytes())
                    self._source_member(value, family, version, path.relative_to(root).as_posix())
                else:
                    legacy = re.match(r"v(\d+\.\d+)/(.*)\.json$", relative)
                    family, version, name = (
                        ("canonical-persistence", legacy[1], legacy[2])
                        if legacy
                        else ("host-compatibility", "1.0", relative[:-5])
                    )
                    value = read_json(path.read_bytes())
                    self._source_member(value, family, version, path.relative_to(root).as_posix())

        # Provider-local published rules have their own literal resource ID, not
        # an SCF or an invented dotted semantic-contract version.
        for path in sorted((root / "src/adr_kit/promotion/rules").glob("*.json")):
            value = read_json(path.read_bytes())
            require(
                set(value) == {"id", "description", "rules"}
                and isinstance(value["id"], str)
                and isinstance(value["description"], str)
                and isinstance(value["rules"], list)
                and all(isinstance(r, str) for r in value["rules"]),
                "unqualified provider-local rule document",
            )
            family, separator, version = value["id"].rpartition("/")
            require(bool(separator and family and version), "missing literal rule identity")
            self.add(value, family, version, value["id"], digest(canonical_bytes(value)))
        self._schema_graph(root)
        self._released_content(classification, root)
        self.observations: dict[tuple[str, str], list[tuple[str, str]]] = {}
        self.definition_keys = {
            identity: json_identity(d) for identity, d in self.definitions.items()
        }

        self.definition_values = {
            value: identity for identity, value in self.definition_keys.items()
        }

    def _released_content(self, classification: dict[str, Any], root: Path) -> None:
        """Qualify schema-only authority omitted by an SCF-only release list."""

        def declaration(value: Any) -> str | None:
            if not isinstance(value, dict):
                return None
            if "$id" in value:
                return json_identity(["$id", value["$id"]])
            if isinstance(value.get("id"), str) and value["id"].startswith("adr-kit."):
                return json_identity(["id", value["id"]])
            if "contract_id" in value and "contract_version" in value:
                return json_identity(["contract", value["contract_id"], value["contract_version"]])
            return None

        declarations: dict[str, set[str]] = {}
        for identity in self.values:
            value = json.loads(identity)
            declared = declaration(value)
            if declared is not None:
                declarations.setdefault(declared, set()).add(identity)
        self.released_digests: set[str] = set()
        self.released_values: dict[str, set[str]] = {}

        def visit(value: Any, required: set[str]) -> None:
            identity = json_identity(value)
            if identity in self.control_values:
                return
            if identity in self.values:
                required.add(identity)
                self.released_digests.update(entry[3] for entry in self.values[identity])
                if isinstance(value, dict) and "semanticContractFamily" in value:
                    self.released.add(
                        (value["semanticContractFamily"], value["semanticContractVersion"])
                    )
                return
            if isinstance(value, dict):
                declared = declaration(value)
                if declared is not None:
                    require(
                        identity in declarations.get(declared, set()),
                        f"changed or missing released resource: {declared}",
                    )
                for child in value.values():
                    visit(child, required)
            elif isinstance(value, list):
                for child in value:
                    visit(child, required)

        for payload in released_payloads(classification, root):
            wheel = payload[:2] == b"PK"
            required = self.released_values.setdefault("wheel" if wheel else "npm", set())
            for name, data in archive_members(payload, wheel).items():
                if name.endswith(".json"):
                    visit(read_json(data), required)
                elif name.endswith((".js", ".mjs")):
                    for _, value in json_objects(data.decode("utf-8")):
                        visit(value, required)
                elif name.endswith(".wasm"):
                    for _, raw in wasm_data(data):
                        for _, value in json_objects(raw.decode("utf-8", errors="surrogateescape")):
                            visit(value, required)

    def _source_member(self, value: Any, family: str, version: str, source_path: str) -> None:
        published = {
            (key, content_digest)
            for _, _, key, content_digest in self.values.get(json_identity(value), [])
            if key.startswith(f"{family}/{version}/")
        }
        if published:
            for key, content_digest in sorted(published):
                self.add(value, family, version, key, content_digest)
        else:
            # Schema-only/legacy authority has a qualified source path, not an
            # invented semantic-resource identity or an invented SCF.
            self.add(value, family, version, source_path, digest(canonical_bytes(value)))

    def _schema_graph(self, root: Path) -> None:
        """Resolve schema-only authority too, using only the sealed source tree.

        Visit schema keyword locations; examples/const/default are literal data,
        not a second ambient schema registry or executable reference authority.
        """
        from jsonschema.validators import validator_for
        from scripts.generate_semantic_contract_assets import relative_resource_key

        schemas: dict[Path, Any] = {}
        by_id: dict[str, Path] = {}
        for directory in (root / "schema", root / "contracts"):
            for path in sorted(directory.rglob("*.json")):
                if (
                    "/vectors/" in path.as_posix()
                    or "/semantic-contract/v1.0/resources/" in path.as_posix()
                ):
                    continue
                value = read_json(path.read_bytes())
                if not isinstance(value, dict) or not str(value.get("$schema", "")).startswith(
                    "http"
                ):
                    continue
                validator = validator_for(value, default=cast(Any, None))
                require(validator is not None, f"unsupported schema dialect: {path}")
                validator.check_schema(value)
                schemas[path.resolve()] = value
                if "$id" in value:
                    identifier = value["$id"].split("#", 1)[0]
                    if identifier in by_id:
                        require(
                            schemas[by_id[identifier]] == value,
                            f"conflicting schema identity {identifier}",
                        )
                    by_id[identifier] = path.resolve()

        def references(value: Any) -> Iterator[str]:
            if not isinstance(value, dict):
                return
            if "$ref" in value:
                yield value["$ref"]
            for keyword in (
                "properties",
                "patternProperties",
                "definitions",
                "$defs",
                "dependentSchemas",
            ):
                for child in value.get(keyword, {}).values():
                    yield from references(child)
            for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
                for child in value.get(keyword, []):
                    yield from references(child)
            for keyword in (
                "items",
                "additionalItems",
                "additionalProperties",
                "not",
                "if",
                "then",
                "else",
                "contains",
                "propertyNames",
                "unevaluatedProperties",
                "unevaluatedItems",
            ):
                child = value.get(keyword)
                for item in child if isinstance(child, list) else [child]:
                    yield from references(item)
            for child in value.get("dependencies", {}).values():
                yield from references(child)

        by_key: dict[str, Path] = {}
        primary: dict[Path, str] = {}
        manifest_keys = {e["key"] for entries in self.required.values() for e in entries}
        for path, value in schemas.items():
            for _, _, key, _ in self.values.get(json_identity(value), []):
                if key in manifest_keys:
                    by_key[key] = path
            relative = path.relative_to(root.resolve()).as_posix()
            match = re.match(r"contracts/([^/]+)/v(\d+\.\d+)/(?:resources/)?(.*)\.json$", relative)
            if match:
                key = f"{match[1]}/{match[2]}/{match[3]}"
                if key in manifest_keys:
                    primary[path] = key
            match = re.match(r"schema/([^/]+)/v(\d+\.\d+)/(.*)\.json$", relative)
            if match:
                key = f"{match[1]}/{match[2]}/schema/{match[3]}"
                if key in manifest_keys:
                    primary[path] = key

        for path, value in schemas.items():
            targets = self.schema_dependencies.setdefault(json_identity(value), set())
            for reference in references(value):
                location, _, fragment = reference.partition("#")
                if not location:
                    target = path
                elif path in primary and not urlparse(location).scheme:
                    resolved_key = relative_resource_key(primary[path], reference)
                    require(
                        resolved_key in by_key, f"unsealed canonical schema reference: {reference}"
                    )
                    assert resolved_key is not None
                    target = by_key[resolved_key]
                elif urlparse(location).scheme or urlparse(value.get("$id", "")).scheme in {
                    "http",
                    "https",
                }:
                    resolved = urljoin(value.get("$id", ""), location)
                    require(resolved in by_id, f"unsealed schema reference: {reference}")
                    target = by_id[resolved]
                else:
                    target = (path.parent / unquote(location)).resolve()
                require(
                    target.is_relative_to(root.resolve()) and target in schemas,
                    f"missing schema reference: {path}: {reference}",
                )
                # This is resource-closure admission, not a new interpretation of
                # historical fragment selectors or schema-instance conformance.
                # Exact source content, including its fragment, is independently
                # bound above; the existing contract suites own its semantics.
                targets.add(json_identity(schemas[target]))

    def add(self, value: Any, family: str, version: str, key: str, content_digest: str) -> None:
        entry = family, version, key, content_digest
        values = self.values.setdefault(json_identity(value), [])
        if entry not in values:
            values.append(entry)


def discover_inventory(bundle: Path, source: str, root: Path = ROOT) -> dict[str, Any]:
    require(re.fullmatch(r"[0-9a-f]{40}", source) is not None, "invalid source commit")
    payloads = package_payloads(bundle)
    index = AuthorityIndex(root)
    authorities: dict[tuple[str, str], dict[str, Any]] = {}
    wasm_hashes: set[str] = set()
    package_kinds: set[str] = set()
    definitions_seen: set[tuple[str, tuple[str, str]]] = set()
    contents_seen: dict[str, set[str]] = {}

    def record_key(value_key: str, artifact: str, locator: str, encoding: str) -> None:
        contents_seen.setdefault(artifact, set()).add(value_key)
        if value_key in index.definition_values:
            definitions_seen.add((artifact, index.definition_values[value_key]))
        for family, version, key, content_digest in index.values[value_key]:
            identity = family, version
            definition = index.definitions.get(identity)
            authority = authorities.setdefault(
                identity,
                {
                    "family": family,
                    "version": version,
                    "scf": definition["semanticContractFingerprint"] if definition else None,
                    "resources": {},
                    "placements": {},
                    "disposition": "released" if identity in index.released else "candidate",
                },
            )
            authority["resources"][key] = content_digest
            authority["placements"][locator, artifact] = {
                "artifact": artifact,
                "locator": locator,
                "digest": content_digest,
                "encoding": encoding,
            }

    def observations(data: bytes, kind: str, origin: str) -> list[tuple[str, str]]:
        # Decoding is pure and memoized only by exact bytes within an independently
        # qualified source index. Every placement, closure, commitment and live
        # human approval is still checked anew. Changed bytes never hit this cache.
        cache_key = kind, hashlib.sha256(data).hexdigest()
        if cache_key in index.observations:
            return index.observations[cache_key]
        result: list[tuple[str, str]] = []

        def visit(value: Any, locator: str) -> None:
            value_key = json_identity(value)
            if value_key in index.control_values:
                return
            if value_key in index.values:
                # The RFC lookup is not proof. Recompute actual content identity
                # with the shared semantic core before memoizing these exact bytes.
                actual_digest = digest(canonical_bytes(value))
                require(
                    all(entry[3] == actual_digest for entry in index.values[value_key]),
                    "packaged resource fails independent canonical digest verification",
                )
                result.append((locator, value_key))
                return
            if isinstance(value, dict):
                require(
                    not (
                        set(value)
                        & {
                            "semanticContractFamily",
                            "resource_version",
                            "contract_id",
                            "$schema",
                            "schema_version",
                            "contract_family",
                            "semantic_contract_family",
                            "semanticDependencies",
                        }
                    ),
                    f"unknown or changed packaged authority: {origin}{locator}",
                )
                for key, child in value.items():
                    visit(child, f"{locator}/{key}")
            elif isinstance(value, list):
                for i, child in enumerate(value):
                    visit(child, f"{locator}/{i}")

        if kind == "json":
            value = read_json(data)
            require(
                json_identity(value) in index.values
                or json_identity(value) in index.control_values,
                f"unknown or changed JSON authority: {origin}",
            )
            visit(value, "")
        elif kind == "wasm":
            for segment, raw in wasm_data(data):
                for offset, value in json_objects(raw.decode("utf-8", errors="surrogateescape")):
                    visit(value, f":data:{segment}:char:{offset}")
            require(bool(result), "WASM has no qualified authority")
        else:
            for offset, value in json_objects(data.decode("utf-8")):
                visit(value, f":char:{offset}")
        index.observations[cache_key] = result
        return result

    for artifact, payload in payloads.items():
        kind = (
            "wheel"
            if artifact.endswith(".whl")
            else "npm" if artifact.endswith(".tgz") else "sdist"
        )
        package_kinds.add(kind)
        found = 0
        wasm_count = 0
        for name, data in archive_members(payload, kind == "wheel").items():
            if name.endswith(".wasm"):
                require(
                    data == (root / "src/adr_kit/core/semantic-core.wasm").read_bytes(),
                    "WASM differs from qualified source artifact",
                )
                wasm_count += 1
                wasm_hashes.add(hashlib.sha256(data).hexdigest())
                decoded = observations(data, "wasm", name)
                found += len(decoded)
                for suffix, value_key in decoded:
                    record_key(value_key, artifact, name + suffix, "embedded-wasm")
            elif name.endswith(".json"):
                # Tests and documentation in an sdist are not executable/discoverable
                # authority. Runtime packages and canonical contract/schema directories are.
                if kind != "sdist" or any(
                    p in name.split("/")
                    for p in (
                        "adr_kit",
                        "generated",
                        "contracts",
                        "schema",
                        "schemas",
                        "semantic-contract",
                    )
                ):
                    if kind == "npm" and name == "package/package.json":
                        require(
                            read_json(data)
                            == read_json((root / "packages/node/package.json").read_bytes()),
                            "npm package metadata differs from qualified source",
                        )
                        continue
                    decoded = observations(data, "json", name)
                    found += len(decoded)
                    for suffix, value_key in decoded:
                        record_key(value_key, artifact, name + suffix, "json")
            elif name.endswith((".js", ".mjs")):
                decoded = observations(data, "js", name)
                found += len(decoded)
                for suffix, value_key in decoded:
                    record_key(value_key, artifact, name + suffix, "json")
        require(found > 0, f"package contains no qualified authority: {artifact}")
        require(wasm_count > 0, f"package missing embedded WASM: {artifact}")
    require(package_kinds == {"wheel", "sdist", "npm"}, "incomplete distribution cohort")
    require(len(wasm_hashes) == 1, "missing or inconsistent packaged WASM")
    for artifact, values in contents_seen.items():
        released_kind = "npm" if artifact.endswith(".tgz") else "wheel"
        require(
            index.released_values[released_kind] <= values,
            f"missing released packaged authority in {artifact}",
        )
    for artifact, identity in definitions_seen:
        for entry in index.required[identity]:
            require(
                any(
                    (identity[0], identity[1], entry["key"], entry["digest"]) in index.values[v]
                    for v in contents_seen[artifact]
                ),
                f"incomplete {artifact} closure: {entry['key']}",
            )
    for artifact, values in contents_seen.items():
        required_definitions = set()
        for value in values:
            require(
                index.schema_dependencies.get(value, set()) <= values,
                f"missing packaged schema-reference closure in {artifact}",
            )
            for family, version, _, _ in index.values[value]:
                identity = family, version
                if identity in index.definitions:
                    required_definitions.add(identity)
        for identity in required_definitions:
            require(
                index.definition_keys[identity] in values,
                f"missing packaged definition {identity} in {artifact}",
            )
    rows = []
    for identity, authority in sorted(authorities.items()):
        # A definition's entire resource closure must actually be packaged, not
        # merely present in the source tree used to interpret it.
        for entry in index.required.get(identity, []):
            require(
                authority["resources"].get(entry["key"]) == entry["digest"],
                f"missing packaged closure member {entry['key']}",
            )
        if authority["scf"] is None and all(
            d in index.released_digests for d in authority["resources"].values()
        ):
            authority["disposition"] = "released"
        authority["resources"] = [
            {"key": k, "digest": v} for k, v in sorted(authority["resources"].items())
        ]
        authority["placements"] = sorted(
            authority["placements"].values(), key=lambda p: (p["artifact"], p["locator"])
        )
        rows.append(authority)
    inventory = {
        "schema_version": "1.0",
        "kind": "packaged-semantic-authority-inventory",
        "source_commit": source,
        "artifacts": [
            {"name": k, "size": len(v), "digest": digest(v)} for k, v in sorted(payloads.items())
        ],
        "authorities": rows,
    }
    from scripts.release_authority_promotion import qualified_prior_promotions, enforce_promoted

    prior = qualified_prior_promotions(source, root)
    enforce_promoted(inventory, prior)
    promoted = {(a["family"], a["version"]) for p in prior for a in p["approved_authorities"]}
    for row in rows:
        if (row["family"], row["version"]) in promoted and row["disposition"] != "released":
            row["disposition"] = "independently_promoted"
    qualify_inventory(inventory, payloads)
    return inventory


def package_payloads(bundle: Path) -> dict[str, bytes]:
    files = sorted([*bundle.glob("python-dist/*"), *bundle.glob("node-dist/*")])
    require(
        len(files) == 3 and all(p.is_file() for p in files),
        "expected exactly three retained distributions",
    )
    require(
        sum(p.name.endswith(".whl") for p in files) == 1
        and sum(p.name.endswith(".tar.gz") for p in files) == 1
        and sum(p.name.endswith(".tgz") for p in files) == 1,
        "distribution kinds",
    )
    return {p.relative_to(bundle).as_posix(): p.read_bytes() for p in files}


def create_cohort(bundle: Path, source: str, root: Path = ROOT) -> dict[str, Any]:
    inventory = discover_inventory(bundle, source, root)
    inventory_bytes = canonical_bytes(inventory)
    manifest = {
        "source_commit": source,
        "artifacts": inventory["artifacts"],
        "inventory_digest": digest(inventory_bytes),
    }
    (bundle / "authority-inventory.json").write_bytes(inventory_bytes)
    (bundle / "authority-manifest.json").write_bytes(canonical_bytes(manifest))
    return inventory


def verify_cohort(bundle: Path, source: str, root: Path = ROOT) -> dict[str, Any]:
    inventory = discover_inventory(bundle, source, root)
    inventory_bytes = canonical_bytes(inventory)
    require(
        (bundle / "authority-inventory.json").read_bytes() == inventory_bytes,
        "inventory does not describe actual package cohort",
    )
    expected = {
        "source_commit": source,
        "artifacts": inventory["artifacts"],
        "inventory_digest": digest(inventory_bytes),
    }
    require(
        (bundle / "authority-manifest.json").read_bytes() == canonical_bytes(expected),
        "authority manifest mismatch",
    )
    return inventory
