"""Deterministic additive identity helpers owned by ADR Kit."""

from __future__ import annotations

import os
import re
import struct
import time
from collections.abc import Mapping
from hashlib import sha256
from typing import Any
import json

import rfc8785

from .decorators import implements, implements_adr

# ---------------------------------------------------------------------------
# v1.0 / v1.1  —  assertion identity (unchanged)
# ---------------------------------------------------------------------------


def derive_assertion_id(
    relationship_type: str,
    from_entity_id: str,
    to_entity_id: str,
    canonical_source_ref: str,
    source_pointer: str | None = None,
) -> str:
    """Return the source-sensitive assertion identity locked by ADR-L-0018."""
    payload = [
        relationship_type,
        from_entity_id,
        to_entity_id,
        canonical_source_ref,
        source_pointer or "",
    ]
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"asrt-{sha256(canonical.encode('utf-8')).hexdigest()}"


# ---------------------------------------------------------------------------
# v1.3  —  UUIDv7  (RFC 9562)
# ---------------------------------------------------------------------------

UUIDV7_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


@implements_adr("ADR-L-0019")
@implements("019fee89-e617-7b55-931f-d0126c67c176")
def validate_uuidv7(value: str) -> str:
    """Validate *value* as a lowercase RFC 9562 UUIDv7 and return it."""
    if not isinstance(value, str) or not UUIDV7_PATTERN.match(value):
        raise ValueError(f"Not a valid lowercase UUIDv7: {value!r}")
    return value


@implements_adr("ADR-L-0019")
@implements("019fee89-e617-7b55-931f-d0126c67c176")
def parse_uuidv7(value: str) -> str:
    """Alias for :func:`validate_uuidv7`."""
    return validate_uuidv7(value)


@implements_adr("ADR-L-0019")
@implements("019fee89-e617-7b55-931f-d0126c67c176")
def mint_uuidv7(
    *,
    timestamp_ms: int | None = None,
    rand_bytes: bytes | None = None,
) -> str:
    """Mint an RFC 9562 UUIDv7 with injectable clock/random.

    Parameters
    ----------
    timestamp_ms:
        Unix epoch milliseconds.  Defaults to ``time.time_ns() // 1_000_000``.
    rand_bytes:
        Exactly 10 random bytes for rand_a (12 bits) + rand_b (62 bits).
        Defaults to ``os.urandom(10)``.
    """
    if timestamp_ms is None:
        timestamp_ms = time.time_ns() // 1_000_000
    if rand_bytes is None:
        rand_bytes = os.urandom(10)
    if len(rand_bytes) != 10:
        raise ValueError("rand_bytes must be exactly 10 bytes")

    ts_bytes = struct.pack(">Q", timestamp_ms)[-6:]

    rand_a = (rand_bytes[0] << 4) | (rand_bytes[1] >> 4)
    rand_a_hi = (rand_a >> 8) & 0x0F
    rand_a_lo = rand_a & 0xFF

    ver_rand_a = bytes([0x70 | rand_a_hi, rand_a_lo])

    var_byte = 0x80 | (((rand_bytes[1] & 0x0F) << 2) | (rand_bytes[2] >> 6))
    rest = bytes([var_byte, (rand_bytes[2] & 0x3F) | (rand_bytes[3] & 0x3F)]) + rand_bytes[4:]

    raw = ts_bytes + ver_rand_a + rest
    hexstr = raw.hex()
    return f"{hexstr[0:8]}-{hexstr[8:12]}-{hexstr[12:16]}" f"-{hexstr[16:20]}-{hexstr[20:32]}"


@implements_adr("ADR-L-0019")
def uuidv7_created_at(uuid_str: str) -> str:
    """Decode the UUIDv7 48-bit timestamp to RFC 3339 UTC with ms precision."""
    validate_uuidv7(uuid_str)
    hex_no_dash = uuid_str.replace("-", "")
    ts_ms = int(hex_no_dash[:12], 16)
    from datetime import datetime, timezone

    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts_ms % 1000:03d}Z"


# ---------------------------------------------------------------------------
# v1.3  —  alias conventions
# ---------------------------------------------------------------------------

ALIAS_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

RESERVED_GENERIC_ALIAS_NAMES: frozenset[str] = frozenset(
    {
        "decision",
        "system",
        "repository",
        "identity",
        "entity",
        "component",
        "capability",
        "invariant",
        "boundary",
        "contract",
        "interface",
        "adr",
    }
)

_ENTITY_TYPE_SEGMENTS: dict[str, str] = {
    "logical": "logical",
    "physical-system": "physical-system",
    "physical-component": "physical-component",
    "physical": "physical",
    "decision": "decision",
    "capability": "capability",
    "invariant": "invariant",
    "boundary": "boundary",
    "contract": "contract",
    "component": "component",
    "interface": "interface",
}


@implements_adr("ADR-L-0019")
def validate_alias_name(
    name: str,
    *,
    entity_type: str | None = None,
) -> str:
    """Validate *name* as a v1.3 alias_name and return it.

    Rejects UUID-shaped values, reserved generics, and exact entity-type
    repetition when *entity_type* is provided.  Never normalizes silently.
    """
    if not isinstance(name, str):
        raise ValueError("alias_name must be a string")
    if len(name) < 3 or len(name) > 96:
        raise ValueError(f"alias_name must be 3–96 characters, got {len(name)}")
    if not ALIAS_NAME_PATTERN.match(name):
        raise ValueError(f"alias_name must match {ALIAS_NAME_PATTERN.pattern}: {name!r}")
    if UUIDV7_PATTERN.match(name):
        raise ValueError("alias_name must not be UUID-shaped")
    hex_only = name.replace("-", "")
    if len(hex_only) == 32 and all(c in "0123456789abcdef" for c in hex_only):
        raise ValueError("alias_name must not be UUID-shaped")
    if name in RESERVED_GENERIC_ALIAS_NAMES:
        raise ValueError(f"alias_name {name!r} is a reserved generic name")

    if entity_type is not None:
        normalized_type = _ENTITY_TYPE_SEGMENTS.get(entity_type.lower(), entity_type.lower())
        if name == normalized_type:
            raise ValueError(
                f"alias_name {name!r} is an exact repetition of " f"entity_type {entity_type!r}"
            )
    return name


# ---------------------------------------------------------------------------
# v1.3  —  derived identity surfaces
# ---------------------------------------------------------------------------


@implements_adr("ADR-L-0019")
def derive_alias_ref(alias_id: str, alias_name: str) -> str:
    """Derive the human-recognition alias reference from alias_id and alias_name."""
    return f"{alias_id}:{alias_name}"


@implements_adr("ADR-L-0019")
def derive_entity_uri(architecture_namespace: str, uuid: str) -> str:
    """Derive the canonical entity URI from architecture namespace and UUID."""
    validate_uuidv7(uuid)
    return f"adr://{architecture_namespace}/entities/{uuid}"


@implements_adr("ADR-L-0019")
def entity_fingerprint(record: Mapping[str, Any]) -> str:
    """Compute entity fingerprint: RFC 8785 JCS then SHA-256."""
    canonical_bytes: bytes = rfc8785.dumps(dict(record))
    digest = sha256(canonical_bytes).hexdigest()
    return f"sha256:{digest}"


# ---------------------------------------------------------------------------
# v1.3  —  relationship / assertion identity
# ---------------------------------------------------------------------------


@implements_adr("ADR-L-0019")
def derive_relationship_id_v13(
    relationship_type: str,
    source_uuid: str,
    target_uuid: str,
) -> str:
    """Derive v1.3 relationship_id from type and UUID endpoints."""
    validate_uuidv7(source_uuid)
    validate_uuidv7(target_uuid)
    return f"{relationship_type}:{source_uuid}:{target_uuid}"


@implements_adr("ADR-L-0019")
def derive_assertion_id_v13(
    relationship_type: str,
    source_uuid: str,
    target_uuid: str,
    source_owner_uuid: str,
    source_pointer: str | None = None,
) -> str:
    """Derive v1.3 assertion_id from UUID endpoints and owner."""
    validate_uuidv7(source_uuid)
    validate_uuidv7(target_uuid)
    validate_uuidv7(source_owner_uuid)
    payload = [
        relationship_type,
        source_uuid,
        target_uuid,
        source_owner_uuid,
        source_pointer or "",
    ]
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"asrt-{sha256(canonical.encode('utf-8')).hexdigest()}"
