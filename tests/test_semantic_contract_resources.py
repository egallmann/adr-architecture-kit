"""Semantic-contract resources must remain byte-identical across package mirrors."""

from __future__ import annotations

import filecmp
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_semantic_contract_definitions_and_resources_match_python_bundle() -> None:
    canonical = ROOT / "contracts" / "semantic-contract" / "v1.0"
    bundled = ROOT / "src" / "adr_kit" / "semantic_contract" / "v1_0"
    for relative in (
        "semantic-contract-version.schema.json",
        "resource-manifest-entry.schema.json",
        "definitions/normative-semantics.json",
        "definitions/architecture-interpretation.json",
        "resources/normative-semantics-definition.json",
        "resources/normative-semantics-conformance.json",
        "resources/architecture-interpretation-rules.json",
        "resources/architecture-interpretation-conformance.json",
    ):
        source = canonical / relative
        if relative.startswith("definitions/"):
            mirror = bundled / Path(relative).name
        elif relative.startswith("resources/"):
            mirror = bundled / "resources" / Path(relative).name
        else:
            mirror = bundled / Path(relative).name
        assert source.is_file()
        assert mirror.is_file()
        assert filecmp.cmp(source, mirror, shallow=False), relative
