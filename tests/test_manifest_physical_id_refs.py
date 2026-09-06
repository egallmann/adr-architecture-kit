"""Regression: manifest:1.0 physical-only slots accept ADR-P|PS|PC, reject others."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from adr_kit.parser import ADRParser, ADRSchemaValidationError

ROOT = Path(__file__).resolve().parents[1]


def _base_manifest(**overlays: object) -> dict:
    data: dict = {
        "schema_version": "1.0",
        "type": "manifest",
        "generated_date": "2026-09-05T00:00:00Z",
        "generated_from": "adrs/**/*.yaml",
        "adrs": [],
        "gaps_summary": {"total": 0, "blocking": 0, "by_adr": {}},
        "statistics": {
            "total_adrs": 0,
            "logical_adrs": 0,
            "physical_adrs": 0,
        },
    }
    data.update(overlays)
    return data


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _accepts(tmp_path: Path, physical_id: str) -> None:
    parser = ADRParser()
    for overlays in (
        {"by_technology": {"python": [physical_id]}},
        {"logical_to_physical_map": {"ADR-L-0001": [physical_id]}},
        {
            "invariants": [
                {
                    "id": "INV-9999",
                    "statement": "fixture invariant",
                    "defined_in": "ADR-L-0001",
                    "enforced_by": [physical_id],
                    "enforcement_level": "must",
                }
            ]
        },
    ):
        path = _write_manifest(tmp_path, _base_manifest(**overlays))
        parser.parse_manifest(path)


def _rejects(tmp_path: Path, physical_id: str) -> None:
    parser = ADRParser()
    for overlays in (
        {"by_technology": {"python": [physical_id]}},
        {"logical_to_physical_map": {"ADR-L-0001": [physical_id]}},
        {
            "invariants": [
                {
                    "id": "INV-9999",
                    "statement": "fixture invariant",
                    "defined_in": "ADR-L-0001",
                    "enforced_by": [physical_id],
                    "enforcement_level": "must",
                }
            ]
        },
    ):
        path = _write_manifest(tmp_path, _base_manifest(**overlays))
        with pytest.raises(ADRSchemaValidationError):
            parser.parse_manifest(path)


@pytest.mark.parametrize("physical_id", ["ADR-PS-0001"])
def test_a_physical_system_accepted_in_physical_only_slots(
    tmp_path: Path, physical_id: str
) -> None:
    _accepts(tmp_path, physical_id)


@pytest.mark.parametrize("physical_id", ["ADR-PC-0001"])
def test_b_physical_component_accepted_in_physical_only_slots(
    tmp_path: Path, physical_id: str
) -> None:
    _accepts(tmp_path, physical_id)


@pytest.mark.parametrize("physical_id", ["ADR-P-0001"])
def test_c_legacy_physical_accepted_in_physical_only_slots(
    tmp_path: Path, physical_id: str
) -> None:
    _accepts(tmp_path, physical_id)


@pytest.mark.parametrize(
    "bad_id",
    [
        "ADR-L-0001",
        "ADR-V-0001",
        "ADR-D-0001",
        "ADR-P-1",
        "ADR-PS-1",
        "ADR-PC-ABCD",
        "ADR-PX-0001",
        "not-an-adr",
    ],
)
def test_d_non_physical_and_malformed_rejected_in_physical_only_slots(
    tmp_path: Path, bad_id: str
) -> None:
    _rejects(tmp_path, bad_id)


def test_e_dogfood_repo_manifest_validates() -> None:
    parser = ADRParser()
    parser.parse_manifest(ROOT / "adrs" / "manifest.yaml")
