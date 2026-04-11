"""Repository schema generation helpers.

Generates Pydantic-derived JSON Schema documents for the repository-normalized
discovery models (architecture index, entity registry, relationship registry,
unresolved registry). These schemas are the kernel-compatibility subset — they
describe the shape of artifacts this repository produces, but they do not own
the normative cross-repo Architecture IR contract. That authority belongs to
ste-spec.
"""

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


REPOSITORY_SCHEMA_MODELS = {
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


def generate_repository_schema_documents() -> dict[str, dict[str, Any]]:
    """Generate normalized JSON Schema documents for repository discovery models."""
    return {
        filename: normalize_json_data(model.model_json_schema())
        for filename, model in REPOSITORY_SCHEMA_MODELS.items()
    }


def write_repository_schema_documents(output_dir: Path) -> list[Path]:
    """Write normalized repository schema documents to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, document in generate_repository_schema_documents().items():
        path = output_dir / filename
        path.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


# Pre-1.0 rename aliases: kernel_contract → repository_schema_generator.
# These aliases preserve compatibility with any code that imported from the old
# module path before the rename.
KERNEL_SCHEMA_MODELS = REPOSITORY_SCHEMA_MODELS
generate_kernel_schema_documents = generate_repository_schema_documents
write_kernel_schema_documents = write_repository_schema_documents
