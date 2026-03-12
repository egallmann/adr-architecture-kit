"""Shared integrity header and hashing primitives."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .artifacts import ArtifactKind

INTEGRITY_SCHEMA_VERSION = 1
GENERATED_MARKER = "deterministic_projection_v1"
HASH_ALGORITHM = "sha256"
HEADER_FIELD_ORDER = [
    "integrity_schema_version",
    "generated",
    "artifact_kind",
    "generator_id",
    "generator_version",
    "hash_algorithm",
    "source_hash",
    "rendered_hash",
]


@dataclass(frozen=True)
class GeneratorIdentity:
    """Logical projection generator identity."""

    generator_id: str
    generator_version: int


class IntegrityHeaderError(ValueError):
    """Raised when an integrity header is absent or malformed."""


@dataclass(frozen=True)
class HashInput:
    """A deterministic labeled input for source hashing."""

    label: str
    content: bytes


def _normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/")


def _ordered_header_lines(header_fields: dict[str, str]) -> list[str]:
    if set(header_fields.keys()) != set(HEADER_FIELD_ORDER):
        raise IntegrityHeaderError("Header fields do not match required schema")
    return [f"{field}: {header_fields[field]}" for field in HEADER_FIELD_ORDER]


def build_markdown_header(header_fields: dict[str, str]) -> str:
    """Build a deterministic markdown integrity header."""
    lines = _ordered_header_lines(header_fields)
    content = "\n".join(lines)
    return f"<!--\n{content}\n-->\n\n"


def build_yaml_header(header_fields: dict[str, str]) -> str:
    """Build a deterministic YAML integrity header."""
    lines = _ordered_header_lines(header_fields)
    return "".join(f"# {line}\n" for line in lines) + "\n"


def parse_integrity_header(text: str, artifact_kind_hint: ArtifactKind | None = None) -> dict[str, str]:
    """Parse and validate a deterministic integrity header."""
    if text.startswith("<!--\n"):
        closing = text.find("\n-->\n")
        if closing == -1:
            raise IntegrityHeaderError("Markdown header is not properly closed")
        raw_lines = text[len("<!--\n"):closing].splitlines()
    else:
        raw_lines: list[str] = []
        for line in text.splitlines():
            if not line.startswith("# "):
                break
            raw_lines.append(line[2:])
        if not raw_lines:
            raise IntegrityHeaderError("YAML header not found")

    if len(raw_lines) != len(HEADER_FIELD_ORDER):
        raise IntegrityHeaderError("Unexpected number of header fields")

    parsed: dict[str, str] = {}
    expected_index = 0
    for line in raw_lines:
        if ": " not in line:
            raise IntegrityHeaderError("Malformed header line")
        key, value = line.split(": ", 1)
        if key != HEADER_FIELD_ORDER[expected_index]:
            raise IntegrityHeaderError("Header field order is invalid")
        if key in parsed:
            raise IntegrityHeaderError("Duplicate header field")
        parsed[key] = value
        expected_index += 1

    if parsed["integrity_schema_version"] != str(INTEGRITY_SCHEMA_VERSION):
        raise IntegrityHeaderError("Unsupported integrity schema version")
    if parsed["generated"] != GENERATED_MARKER:
        raise IntegrityHeaderError("Invalid generated marker")
    if parsed["hash_algorithm"] != HASH_ALGORITHM:
        raise IntegrityHeaderError("Unsupported hash algorithm")
    if artifact_kind_hint and parsed["artifact_kind"] != artifact_kind_hint.value:
        raise IntegrityHeaderError("Artifact kind mismatch")
    if parsed["artifact_kind"] not in {kind.value for kind in ArtifactKind}:
        raise IntegrityHeaderError("Unsupported artifact kind")
    if not parsed["generator_version"].isdigit():
        raise IntegrityHeaderError("Generator version must be an integer")

    return parsed


def extract_body_without_header(text: str) -> str:
    """Extract artifact body excluding the integrity header."""
    if text.startswith("<!--\n"):
        closing = text.find("\n-->\n")
        if closing == -1:
            raise IntegrityHeaderError("Markdown header is not properly closed")
        body_start = closing + len("\n-->\n")
        if text[body_start:body_start + 1] == "\n":
            body_start += 1
        return text[body_start:]

    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines) and lines[index].startswith("# "):
        index += 1
    if index < len(lines) and lines[index] == "\n":
        index += 1
    return "".join(lines[index:])


def compute_rendered_hash(body: str) -> str:
    """Hash rendered body content excluding integrity header."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def compute_source_hash(
    scope_root: Path,
    inputs: Iterable[Path | HashInput],
    generator_identity: GeneratorIdentity,
) -> str:
    """Hash canonical inputs plus generator identity/version."""
    scope_root = Path(scope_root).resolve()
    normalized_inputs: list[tuple[str, bytes]] = []
    for item in inputs:
        if isinstance(item, HashInput):
            normalized_inputs.append((_normalize_rel_path(item.label), item.content))
            continue

        candidate = Path(item)
        if not candidate.exists() or not candidate.is_file() or candidate.is_symlink():
            continue
        resolved = candidate.resolve()
        try:
            label = _normalize_rel_path(str(resolved.relative_to(scope_root)))
        except ValueError:
            label = _normalize_rel_path(f"__generator__/{resolved.name}")
        normalized_inputs.append((label, resolved.read_bytes()))

    normalized_inputs.sort(key=lambda item: item[0])

    digest = hashlib.sha256()
    digest.update(f"generator_id:{generator_identity.generator_id}\n".encode("utf-8"))
    digest.update(f"generator_version:{generator_identity.generator_version}\n".encode("utf-8"))
    for rel_path, content in normalized_inputs:
        digest.update(f"path:{rel_path}\n".encode("utf-8"))
        digest.update(content)
        digest.update(b"\n")
    return digest.hexdigest()
