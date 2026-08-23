"""Validation primitives for namespaced consumer semantic extensions.

The compiler owns the envelope and structural grammar.  It deliberately does
not interpret the meaning of a consumer's qualified type or property values.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

ARCHITECTURE_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
EXTENSION_TYPE_RE = re.compile(
    r"^(?P<namespace>[A-Za-z0-9][A-Za-z0-9._-]*):(?P<local>[a-z][a-z0-9_]{1,63})$"
)
PROPERTY_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ALIAS_PREFIX_RE = re.compile(r"^[A-Z][A-Z0-9]{0,15}$")

CORE_ENTITY_TYPES = frozenset(
    {
        "adr",
        "system",
        "component",
        "decision",
        "capability",
        "invariant",
        "boundary",
        "contract",
        "constraint",
        "nfr",
        "gap",
        "interface",
        "integration",
        "implementation_decision",
    }
)
CORE_RELATIONSHIP_TYPES = frozenset(
    {
        "declared_in",
        "references",
        "related_to",
        "enforces",
        "enabled_by",
        "enables",
        "governs",
        "implemented_by",
        "embodied_in",
        "implements_logical",
        "supersedes",
        "superseded_by",
        "refines",
        "provides_interface",
        "composed_of",
        "binds_substrate",
        "binds_rule",
        "expects_evidence",
    }
)
CORE_ALIAS_PREFIXES = frozenset(
    {
        "ADR",
        "BOUND",
        "CAP",
        "COMP",
        "CONTRACT",
        "DEC",
        "GAP",
        "IFACE",
        "IMPL",
        "INV",
        "NFR",
        "REL",
        "SYS",
    }
)


class ExtensionValidationError(ValueError):
    """Raised when an extension violates the structural or semantic grammar."""


def validate_architecture_namespace(namespace: str) -> str:
    if not isinstance(namespace, str) or not ARCHITECTURE_NAMESPACE_RE.fullmatch(namespace):
        raise ExtensionValidationError(f"Invalid architecture namespace: {namespace!r}")
    return namespace


def validate_extension_type(
    value: str,
    *,
    architecture_namespace: str | None = None,
    kind: str = "entity",
) -> str:
    match = EXTENSION_TYPE_RE.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ExtensionValidationError(
            f"{kind} type must be namespace-qualified as '<architecture_namespace>:<local_type>'"
        )
    namespace = match.group("namespace")
    local = match.group("local")
    if architecture_namespace is not None and namespace != architecture_namespace:
        raise ExtensionValidationError(
            f"{kind} type namespace {namespace!r} does not match "
            f"architecture namespace {architecture_namespace!r}"
        )
    reserved = CORE_ENTITY_TYPES if kind == "entity" else CORE_RELATIONSHIP_TYPES
    if local in reserved:
        raise ExtensionValidationError(f"Extension {kind} type shadows reserved core type: {local}")
    return value


def validate_property_map(properties: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(properties, Mapping):
        raise ExtensionValidationError("Extension properties must be an object")
    checked: dict[str, Any] = {}
    for key, value in properties.items():
        if not isinstance(key, str) or PROPERTY_KEY_RE.fullmatch(key) is None:
            raise ExtensionValidationError(f"Invalid extension property key: {key!r}")
        if isinstance(value, bool) or isinstance(value, (str, int, float)):
            checked[key] = value
            continue
        if isinstance(value, list) and all(isinstance(item, (str, int, float, bool)) for item in value):
            checked[key] = list(value)
            continue
        raise ExtensionValidationError(
            f"Extension property {key!r} must be a scalar or a list of scalars"
        )
    return checked


def validate_rationale(rationale: str) -> str:
    if not isinstance(rationale, str) or not rationale.strip():
        raise ExtensionValidationError("Extension rationale must be a non-empty string")
    return rationale


def validate_alias_registration(
    *,
    semantic_type: str,
    alias_id: str,
    architecture_namespace: str | None = None,
    registrations: Mapping[str, str] | None = None,
    reserved_prefixes: Sequence[str] = (),
) -> str:
    """Validate one consumer-owned type-to-prefix registration.

    ``registrations`` is supplied by the consumer corpus.  ADR-Kit validates
    it but never stores it as a central registry.
    """

    validate_extension_type(semantic_type, architecture_namespace=architecture_namespace)
    match = re.fullmatch(r"(?P<prefix>[A-Z][A-Z0-9]{0,15})-\d{4}", alias_id)
    if match is None:
        raise ExtensionValidationError("Extension alias_id must match <PREFIX>-NNNN")
    prefix = match.group("prefix")
    reserved = set(CORE_ALIAS_PREFIXES) | set(reserved_prefixes)
    if prefix in reserved:
        raise ExtensionValidationError(f"Alias prefix {prefix!r} is reserved")
    if registrations is not None:
        prior = registrations.get(semantic_type)
        if prior is not None and prior != prefix:
            raise ExtensionValidationError(
                f"Semantic type {semantic_type!r} is registered to both {prior!r} and {prefix!r}"
            )
        for other_type, other_prefix in registrations.items():
            if other_type != semantic_type and other_prefix == prefix:
                raise ExtensionValidationError(
                    f"Alias prefix {prefix!r} is already registered in this consumer scope"
                )
    return prefix


def is_extension_type(value: str, *, kind: str = "entity") -> bool:
    try:
        validate_extension_type(value, kind=kind)
    except ExtensionValidationError:
        return False
    return True
