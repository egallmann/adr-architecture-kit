"""Contract-family-aware packaged schema inventory.

Authoring v1.5 lives under ``adr_kit.schema.authoring.v1_5``. Evidence
attribution v1.5 remains ``adr_kit.schema.v1_5``. Do not discover authoring
versions by scanning ``adr_kit.schema/v*``.
"""

from __future__ import annotations

# Explicit authoring-family package map. 1.1 is discovery/governance, not ADR YAML.
AUTHORING_SCHEMA_PACKAGES: dict[str, str] = {
    "1.0": "adr_kit.schema.v1_0",
    "1.2": "adr_kit.schema.v1_2",
    "1.3": "adr_kit.schema.v1_3",
    "1.4": "adr_kit.schema.v1_4",
    "1.5": "adr_kit.schema.authoring.v1_5",
}

EVIDENCE_ATTRIBUTION_SCHEMA_PACKAGES: dict[str, str] = {
    "1.5": "adr_kit.schema.v1_5",
    "1.6": "adr_kit.schema.v1_6",
}


def packaged_authoring_schema_versions() -> tuple[str, ...]:
    """Return ADR authoring schema versions present as packaged families."""

    return tuple(AUTHORING_SCHEMA_PACKAGES.keys())
