from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from adr_kit.schema.kernel_contract import generate_kernel_schema_documents


REPO_ROOT = Path(__file__).resolve().parents[1]
KERNEL_SCHEMA_DIR = REPO_ROOT / "schema" / "kernel"
INDEX_DIR = REPO_ROOT / "adrs" / "index"


def _load_committed_schema(filename: str) -> dict:
    return json.loads((KERNEL_SCHEMA_DIR / filename).read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_kernel_contract_schemas_match_generated_models() -> None:
    generated = generate_kernel_schema_documents()
    committed = {
        filename: _load_committed_schema(filename)
        for filename in sorted(generated)
    }
    assert committed == generated


def test_current_contract_payloads_validate_against_committed_kernel_schemas() -> None:
    payloads = {
        "architecture-index.schema.json": _load_yaml(INDEX_DIR / "architecture-index.yaml"),
        "entity-registry.schema.json": _load_yaml(INDEX_DIR / "entity-registry.yaml"),
        "relationship-registry.schema.json": _load_yaml(INDEX_DIR / "relationship-registry.yaml"),
        "unresolved-registry.schema.json": _load_yaml(INDEX_DIR / "unresolved-registry.yaml"),
    }

    for filename, payload in payloads.items():
        jsonschema.validate(instance=payload, schema=_load_committed_schema(filename))
