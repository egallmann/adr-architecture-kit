"""Read candidate authority from canonical contracts for repository qualification."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from adr_kit.semantic_contract import (
    SemanticContractVersion,
    get_semantic_contract as get_bundled_semantic_contract,
    load_semantic_resource as load_bundled_semantic_resource,
)
from scripts.candidate_contract_assets import canonical_resource

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def candidate_identities() -> frozenset[tuple[str, str]]:
    lifecycle = json.loads(
        (ROOT / "adrs/migrations/semantic-contract-lifecycle-classification.json").read_text(
            encoding="utf-8"
        )
    )
    released = {(item["family"], item["version"]) for item in lifecycle["released_contracts"]}
    definitions = ROOT / "contracts/semantic-contract/v1.0/definitions"
    return frozenset(
        (value["semanticContractFamily"], value["semanticContractVersion"])
        for path in definitions.glob("*.json")
        if (value := json.loads(path.read_text(encoding="utf-8")))
        and (value["semanticContractFamily"], value["semanticContractVersion"]) not in released
    )


def get_semantic_contract_for_qualification(family: str, version: str) -> SemanticContractVersion:
    if (family, version) not in candidate_identities():
        return get_bundled_semantic_contract(family, version)
    return SemanticContractVersion.from_wire(
        canonical_resource(ROOT, f"{family}/{version}/contract")
    )


def load_semantic_resource_for_qualification(key: str) -> Any:
    parts = key.split("/")
    if len(parts) >= 2 and tuple(parts[:2]) in candidate_identities():
        try:
            return canonical_resource(ROOT, key)
        except ValueError as exc:
            raise LookupError(str(exc)) from exc
    return load_bundled_semantic_resource(key)
