"""RED/GREEN: invariant-alias-history validation + allocator occupancy (R4/R7)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from adr_kit.promotion.allocation import allocate_child_ids
from adr_kit.promotion.invariant_alias_history import (
    load_validated_historical_aliases,
    validate_invariant_alias_history,
)


def _write_history(tmp_path: Path, doc: dict) -> Path:
    migrations = tmp_path / "adrs" / "migrations"
    migrations.mkdir(parents=True, exist_ok=True)
    path = migrations / "invariant-alias-history.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    (tmp_path / "PROJECT.yaml").write_text(
        "project:\n  name: t\nownership:\n  team: t\n"
        "architecture_documentation:\n  architecture_namespace: test.ns\n",
        encoding="utf-8",
    )
    (tmp_path / "adrs" / "logical").mkdir(parents=True, exist_ok=True)
    return path


def _valid_doc() -> dict:
    return {
        "schema_version": "1.0",
        "type": "invariant_alias_history",
        "entries": [
            {
                "historical_alias": "INV-0002",
                "disposition": "moved_to",
                "canonical_alias": "INV-0095",
                "retired_surface": "standalone_file",
            },
            {
                "historical_alias": "INV-0008",
                "disposition": "merged_into",
                "canonical_alias": "INV-0061",
                "retired_surface": "standalone_file",
                "permanently_consumed": True,
            },
        ],
        "enrichment_log": [],
    }


def test_valid_alias_history_loads():
    doc = _valid_doc()
    validate_invariant_alias_history(doc)
    aliases = load_validated_historical_aliases(doc)
    assert aliases == {"INV-0002", "INV-0008"}


def test_malformed_alias_history_fails():
    with pytest.raises(ValueError):
        validate_invariant_alias_history({"type": "invariant_alias_history"})


def test_unknown_disposition_fails():
    doc = _valid_doc()
    doc["entries"][0]["disposition"] = "retired_somehow"
    with pytest.raises(ValueError, match="disposition"):
        validate_invariant_alias_history(doc)


def test_duplicate_historical_alias_fails():
    doc = _valid_doc()
    doc["entries"].append(
        {
            "historical_alias": "INV-0002",
            "disposition": "duplicate_of",
            "canonical_alias": "INV-0002",
        }
    )
    with pytest.raises(ValueError, match="historical_alias"):
        validate_invariant_alias_history(doc)


def test_invalid_inv_alias_syntax_fails():
    doc = _valid_doc()
    doc["entries"][0]["historical_alias"] = "INV-2"
    with pytest.raises(ValueError, match="INV-"):
        validate_invariant_alias_history(doc)


def test_missing_canonical_alias_fails():
    doc = _valid_doc()
    del doc["entries"][0]["canonical_alias"]
    with pytest.raises(ValueError, match="canonical_alias"):
        validate_invariant_alias_history(doc)


def test_allocator_occupies_historical_alias_moved_to(tmp_path: Path):
    _write_history(tmp_path, _valid_doc())
    _, invs = allocate_child_ids(tmp_path, dec_count=0, inv_count=1)
    assert invs[0] != "INV-0002"
    assert invs[0] != "INV-0008"


def test_allocator_occupies_regardless_of_permanently_consumed(tmp_path: Path):
    doc = {
        "schema_version": "1.0",
        "type": "invariant_alias_history",
        "entries": [
            {
                "historical_alias": "INV-0042",
                "disposition": "duplicate_of",
                "canonical_alias": "INV-0042",
            },
            {
                "historical_alias": "INV-0043",
                "disposition": "merged_into",
                "canonical_alias": "INV-0059",
                "permanently_consumed": False,
            },
        ],
        "enrichment_log": [{"noise": True}],
    }
    _write_history(tmp_path, doc)
    _, invs = allocate_child_ids(tmp_path, dec_count=0, inv_count=1)
    assert invs[0] not in {"INV-0042", "INV-0043"}


def test_enrichment_fields_do_not_change_occupancy(tmp_path: Path):
    base = _valid_doc()
    _write_history(tmp_path, base)
    _, first = allocate_child_ids(tmp_path, dec_count=0, inv_count=1)

    base["enrichment_log"] = [{"classification": "PRESERVE_AS_HISTORY_ONLY"}]
    base["entries"][0]["note"] = "changed"
    _write_history(tmp_path, base)
    _, second = allocate_child_ids(tmp_path, dec_count=0, inv_count=1)
    assert first == second
