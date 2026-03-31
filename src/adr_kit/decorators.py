"""No-op architecture intent decorators for implementation attribution."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar


Decorated = TypeVar("Decorated")


def implements_adr(*adr_ids: str) -> Callable[[Decorated], Decorated]:
    """Attach ADR implementation attribution metadata to a function or class."""

    normalized = _normalize_ids(adr_ids, label="ADR")

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
