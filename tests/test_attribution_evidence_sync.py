"""Sync tests for RECON-derived implementation attribution evidence."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
ATTRIBUTION_PATH = (
    WORKSPACE_ROOT
    / ".ste-workspace"
    / "state"
    / "adr-architecture-kit"
    / "attribution"
    / "implementation-attribution-evidence.yaml"
)


def _attribution_file_exists() -> bool:
    return ATTRIBUTION_PATH.is_file()


def _record_adr_ids(record: dict) -> list[str]:
    return list(record.get("attributed_adrs") or [])


@pytest.mark.skipif(not _attribution_file_exists(), reason="workspace RECON evidence not present")
def test_populates_records_after_workspace_recon() -> None:
    doc = yaml.safe_load(ATTRIBUTION_PATH.read_text(encoding="utf-8"))
    records = doc.get("records") or []

    if not records:
        pytest.skip("evidence file empty — run recon:workspace from ste-runtime first")

    assert doc.get("type") == "implementation_attribution_evidence"
    assert len(records) > 0

    all_adr_ids = [adr for record in records for adr in _record_adr_ids(record)]
    assert "ADR-L-0001" in all_adr_ids
    assert "ADR-L-0004" in all_adr_ids
    assert "ADR-L-0013" in all_adr_ids
    assert "ADR-L-0009" in all_adr_ids

    entity_ids = [record.get("implementation_entity_id", "") for record in records]
    assert any("ADRParser" in eid for eid in entity_ids)
    assert any("ArchitectureCompiler" in eid for eid in entity_ids)
    assert any(
        "validate_implementation_attribution_evidence" in eid for eid in entity_ids
    )

    assert any("ADR-L-0004" in _record_adr_ids(r) for r in records)

    manifest = (REPO_ROOT / "adrs" / "manifest.yaml").read_text(encoding="utf-8")
    for record in records[:5]:
        for adr_id in _record_adr_ids(record):
            assert adr_id in manifest
        source_file = (record.get("provenance") or {}).get("source_file")
        if source_file:
            assert (REPO_ROOT / source_file).is_file()
        if record.get("confidence"):
            assert record["confidence"] == "declared"
