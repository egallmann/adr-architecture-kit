"""Validated invariant-alias-history migration ledger (R4/R7)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_INV_ALIAS_RE = re.compile(r"^INV-\d{4}$")
_DISPOSITIONS = frozenset({"duplicate_of", "moved_to", "merged_into"})
_ALLOWED_ENTRY_KEYS = frozenset(
    {
        "historical_alias",
        "disposition",
        "canonical_alias",
        "retired_surface",
        "permanently_consumed",
        "conflict_provenance",
        "note",
    }
)
_ALLOWED_TOP_KEYS = frozenset({"schema_version", "type", "entries", "enrichment_log"})


def validate_invariant_alias_history(doc: Any) -> None:
    """Fail closed on malformed invariant-alias-history documents."""
    if not isinstance(doc, dict):
        raise ValueError("invariant_alias_history must be a mapping")

    unknown_top = set(doc.keys()) - _ALLOWED_TOP_KEYS
    if unknown_top:
        raise ValueError(f"unknown invariant_alias_history fields: {sorted(unknown_top)}")

    if "schema_version" not in doc:
        raise ValueError("invariant_alias_history missing schema_version")
    if doc.get("type") != "invariant_alias_history":
        raise ValueError("invariant_alias_history type must be 'invariant_alias_history'")
    if "status" in doc:
        raise ValueError("invariant_alias_history must not contain execution status")

    entries = doc.get("entries")
    if not isinstance(entries, list):
        raise ValueError("invariant_alias_history entries must be a list")

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"entries[{index}] must be a mapping")
        unknown = set(entry.keys()) - _ALLOWED_ENTRY_KEYS
        if unknown:
            raise ValueError(f"entries[{index}] unknown fields: {sorted(unknown)}")

        historical = entry.get("historical_alias")
        if not isinstance(historical, str) or not _INV_ALIAS_RE.match(historical):
            raise ValueError(f"entries[{index}] historical_alias must match INV-####")
        if historical in seen:
            raise ValueError(f"duplicate historical_alias: {historical}")
        seen.add(historical)

        disposition = entry.get("disposition")
        if disposition not in _DISPOSITIONS:
            raise ValueError(f"entries[{index}] unknown or missing disposition: {disposition!r}")

        canonical = entry.get("canonical_alias")
        if not isinstance(canonical, str) or not _INV_ALIAS_RE.match(canonical):
            raise ValueError(f"entries[{index}] canonical_alias required and must match INV-####")

        if "permanently_consumed" in entry and not isinstance(entry["permanently_consumed"], bool):
            raise ValueError(f"entries[{index}] permanently_consumed must be boolean")

    enrichment = doc.get("enrichment_log", [])
    if enrichment is not None and not isinstance(enrichment, list):
        raise ValueError("enrichment_log must be a list")


def load_validated_historical_aliases(doc: Any) -> set[str]:
    """Return allocation occupancy set: validated historical_alias values only (R7)."""
    validate_invariant_alias_history(doc)
    return {entry["historical_alias"] for entry in doc["entries"]}


def load_historical_aliases_from_project(project_root: Path) -> set[str]:
    """Load and validate alias-history if present; empty set if file absent."""
    path = project_root / "adrs" / "migrations" / "invariant-alias-history.yaml"
    if not path.is_file():
        return set()
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return load_validated_historical_aliases(doc)
