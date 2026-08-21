"""No-op architecture intent decorators for implementation attribution.

Legacy alias decorators set ``__implements_adrs__`` / ``__enforces_invariants__``.
They do not resolve aliases, load architecture state, or synthesize UUID claims.

UUID decorators compose ``__architecture_attribution_claims__`` with
``confidence: declared`` after local UUIDv7 validation only.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from ._uuidv7 import UUIDV7_PATTERN

Decorated = TypeVar("Decorated")

CANONICAL_CLAIMS_ATTR = "__architecture_attribution_claims__"
_RELATIONSHIP_ORDER = {"implements": 0, "enforces": 1, "embodies": 2}


def implements_adr(*adr_ids: str) -> Callable[[Decorated], Decorated]:
    """Attach ADR implementation attribution metadata to a function or class."""

    normalized = _normalize_ids(adr_ids, label="ADR")

    def decorator(target: Decorated) -> Decorated:
        setattr(target, "__implements_adrs__", normalized)
        return target

    return decorator


def implements_adrs(adr_ids: Sequence[str]) -> Callable[[Decorated], Decorated]:
    """Like :func:`implements_adr`, but takes a single iterable (e.g. a list literal).

    Use this when you want RECON to see ``@implements_adrs([...])`` in source, matching
    TypeScript call style.
    """

    if isinstance(adr_ids, str):
        raise TypeError("implements_adrs expects a sequence of strings, not a single str")
    normalized = _normalize_ids(tuple(adr_ids), label="ADR")

    def decorator(target: Decorated) -> Decorated:
        setattr(target, "__implements_adrs__", normalized)
        return target

    return decorator


def enforces_invariant(*invariant_ids: str) -> Callable[[Decorated], Decorated]:
    """Attach invariant-enforcement attribution metadata to a function or class."""

    normalized = _normalize_ids(invariant_ids, label="invariant")

    def decorator(target: Decorated) -> Decorated:
        setattr(target, "__enforces_invariants__", normalized)
        return target

    return decorator


def enforces_invariants(invariant_ids: Sequence[str]) -> Callable[[Decorated], Decorated]:
    """Like :func:`enforces_invariant`, but takes a single iterable."""

    if isinstance(invariant_ids, str):
        raise TypeError("enforces_invariants expects a sequence of strings, not a single str")
    normalized = _normalize_ids(tuple(invariant_ids), label="invariant")

    def decorator(target: Decorated) -> Decorated:
        setattr(target, "__enforces_invariants__", normalized)
        return target

    return decorator


def implements(*target_entity_ids: str) -> Callable[[Decorated], Decorated]:
    """Attach UUID ``implements`` claims with ``confidence: declared``."""

    return _uuid_claim_decorator("implements", target_entity_ids)


def implements_uuids(target_entity_ids: Sequence[str]) -> Callable[[Decorated], Decorated]:
    """Sequence form of :func:`implements` for list-literal extractor parity."""

    if isinstance(target_entity_ids, str):
        raise TypeError("implements_uuids expects a sequence of strings, not a single str")
    return _uuid_claim_decorator("implements", tuple(target_entity_ids))


def enforces(*target_entity_ids: str) -> Callable[[Decorated], Decorated]:
    """Attach UUID ``enforces`` claims with ``confidence: declared``."""

    return _uuid_claim_decorator("enforces", target_entity_ids)


def enforces_uuids(target_entity_ids: Sequence[str]) -> Callable[[Decorated], Decorated]:
    """Sequence form of :func:`enforces` for list-literal extractor parity."""

    if isinstance(target_entity_ids, str):
        raise TypeError("enforces_uuids expects a sequence of strings, not a single str")
    return _uuid_claim_decorator("enforces", tuple(target_entity_ids))


def embodies(*target_entity_ids: str) -> Callable[[Decorated], Decorated]:
    """Attach UUID ``embodies`` claims with ``confidence: declared``."""

    return _uuid_claim_decorator("embodies", target_entity_ids)


def embodies_uuids(target_entity_ids: Sequence[str]) -> Callable[[Decorated], Decorated]:
    """Sequence form of :func:`embodies` for list-literal extractor parity."""

    if isinstance(target_entity_ids, str):
        raise TypeError("embodies_uuids expects a sequence of strings, not a single str")
    return _uuid_claim_decorator("embodies", tuple(target_entity_ids))


def _uuid_claim_decorator(
    relationship: str,
    target_entity_ids: tuple[str, ...],
) -> Callable[[Decorated], Decorated]:
    normalized = _normalize_uuids(target_entity_ids, label=relationship)
    attr = CANONICAL_CLAIMS_ATTR

    def decorator(target: Decorated) -> Decorated:
        existing = getattr(target, attr, ())
        composed = list(existing) if isinstance(existing, (list, tuple)) else []
        existing_pairs = {
            (claim.get("relationship"), claim.get("target_entity_id"))
            for claim in composed
            if isinstance(claim, dict)
        }
        incoming_pairs = {(relationship, target_entity_id) for target_entity_id in normalized}
        duplicates = sorted(existing_pairs & incoming_pairs)
        if duplicates:
            duplicate_relationship, duplicate_target = duplicates[0]
            raise ValueError(
                "duplicate architecture attribution claim: "
                f"({duplicate_relationship}, {duplicate_target})"
            )
        for target_entity_id in normalized:
            composed.append(
                {
                    "relationship": relationship,
                    "target_entity_id": target_entity_id,
                    "confidence": "declared",
                }
            )
        composed.sort(
            key=lambda claim: (
                _RELATIONSHIP_ORDER.get(str(claim.get("relationship")), 99),
                str(claim.get("target_entity_id", "")),
            )
        )
        setattr(target, attr, tuple(composed))
        return target

    return decorator


def _normalize_uuids(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    if not values:
        raise ValueError(f"{label} decorator requires at least one identifier")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"{label} decorator identifiers must be strings")
        item = value.strip()
        if not item:
            raise ValueError(f"{label} decorator identifiers must not be empty")
        if not UUIDV7_PATTERN.match(item):
            raise ValueError(f"Not a valid lowercase UUIDv7: {item!r}")
        uuid = item
        if uuid in seen:
            raise ValueError(f"{label} decorator identifiers must be unique after normalization")
        seen.add(uuid)
        normalized.append(uuid)
    return tuple(normalized)


def _normalize_ids(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    if not values:
        raise ValueError(f"{label} decorator requires at least one identifier")

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"{label} decorator identifiers must be strings")
        item = value.strip()
        if not item:
            raise ValueError(f"{label} decorator identifiers must not be empty")
        if item in seen:
            raise ValueError(f"{label} decorator identifiers must be unique after normalization")
        seen.add(item)
        normalized.append(item)

    return tuple(normalized)
