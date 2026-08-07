"""Deterministic additive identity helpers owned by ADR Kit."""

from __future__ import annotations

from hashlib import sha256
import json


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
