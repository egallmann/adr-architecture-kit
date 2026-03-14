"""Kernel contract schema generation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adr_kit.models.architecture_discovery import (
    ArchitectureIndex,
    NormalizedEntityRegistry,
    RelationshipRegistry,
    UnresolvedRegistry,
)


KERNEL_SCHEMA_MODELS = {
    "architecture-index.schema.json": ArchitectureIndex,
    "entity-registry.schema.json": NormalizedEntityRegistry,
    "relationship-registry.schema.json": RelationshipRegistry,
    "unresolved-registry.schema.json": UnresolvedRegistry,
}


def normalize_json_data(value: Any) -> Any:
    """Recursively normalize JSON-like data for deterministic comparison."""
    if isinstance(value, dict):
        return {key: normalize_json_data(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [normalize_json_data(item) for item in value]
    return value


def generate_kernel_schema_documents() -> dict[str, dict[str, Any]]:
    """Generate normalized JSON Schema documents for kernel contract models."""
    return {
        filename: normalize_json_data(model.model_json_schema())
        for filename, model in KERNEL_SCHEMA_MODELS.items()
    }


def write_kernel_schema_documents(output_dir: Path) -> list[Path]:
    """Write normalized kernel contract schema documents to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, document in generate_kernel_schema_documents().items():
        path = output_dir / filename
        path.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written

