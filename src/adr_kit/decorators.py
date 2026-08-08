"""No-op architecture intent decorators for implementation attribution.

ste-runtime RECON's Python extractor (`ast_parser.py`) recognizes call-style
decorators named ``implements_adr``, ``implements_adrs``, ``enforces_invariant``,
and ``enforces_invariants`` on functions and classes. These helpers also set
``__implements_adrs__`` / ``__enforces_invariants__`` for runtime introspection.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar


Decorated = TypeVar("Decorated")


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
