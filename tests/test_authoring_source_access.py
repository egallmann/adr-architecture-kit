"""Regression tests for authoring source-access fields not carried by v1.5 models."""

from __future__ import annotations

from pathlib import Path

from adr_kit.compiler.frontend.authoring_source_access import (
    CAPABILITY_SOURCE_ONLY_FIELDS,
    capability_fields_dropped_by_parse,
    index_raw_capabilities,
    load_authoring_yaml,
)
from adr_kit.compiler.frontend.adr_access import field_get
from adr_kit.parser import ADRParser

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ADR = ROOT / "adrs" / "logical" / "ADR-L-0002-multi-scope-adr-architecture.yaml"
PROJECTION = (
    ROOT
    / "adrs"
    / "adr-projection"
    / "logical"
    / "ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md"
)


def test_capability_acceptance_criteria_is_not_authorized_on_v1_5_model() -> None:
    parser = ADRParser()
    adr = parser.parse_logical_adr(CORPUS_ADR)
    raw = load_authoring_yaml(CORPUS_ADR)
    raw_by_key = index_raw_capabilities(raw)
    capabilities = list(field_get(adr, "capabilities") or [])
    assert capabilities
    dropped = capability_fields_dropped_by_parse(capabilities[0], raw_by_key=raw_by_key)
    assert "acceptance_criteria" in dropped
    assert "acceptance_criteria" in CAPABILITY_SOURCE_ONLY_FIELDS
    assert not field_get(capabilities[0], "acceptance_criteria")


def test_capability_acceptance_criteria_renders_from_authoring_source() -> None:
    assert PROJECTION.is_file(), "projection corpus must exist before this test"
    body = PROJECTION.read_text(encoding="utf-8").split("-->", 1)[-1]
    assert "**Acceptance criteria**" in body
    assert "Detects workspace root when run from any subdirectory" in body


def test_coverage_registry_classifies_capability_acceptance_criteria() -> None:
    from adr_kit.compiler.backend.coverage_registry import disposition_for

    assert (
        disposition_for(adr_type="logical", pointer="/capabilities/acceptance_criteria")
        == "RENDER_DETAIL"
    )
