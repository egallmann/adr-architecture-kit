"""Deterministic rendering helpers for Logical ADR -> Architecture IR fragments."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


def norm(value: str) -> str:
    """Apply the logical ADR IR profile string normalization rule."""

    return value.strip()


def lower_ascii(value: str) -> str:
    """Lowercase ASCII letters only after normalization."""

    normalized = norm(value)
    translated = []
    for char in normalized:
        codepoint = ord(char)
        if 65 <= codepoint <= 90:
            translated.append(chr(codepoint + 32))
        else:
            translated.append(char)
    return "".join(translated)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON using a deterministic canonical form for logical ADR IR inputs."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_prefixed_hex(value: Any) -> str:
    """Return the sha256-prefixed lowercase hex digest for canonical JSON bytes."""

    digest = hashlib.sha256(canonical_json_bytes(value)).hexdigest()
    return f"sha256:{digest}"


def sha256_hex(value: Any) -> str:
    """Return the lowercase hex digest for canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sort_ids_utf8(values: Iterable[str]) -> list[str]:
    """Sort strings by UTF-8 bytewise lexicographic order."""

    return sorted(values, key=lambda item: item.encode("utf-8"))


def sort_records_by_id(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort IR records by `id` using UTF-8 bytewise lexicographic order."""

    return sorted(records, key=lambda record: str(record["id"]).encode("utf-8"))
