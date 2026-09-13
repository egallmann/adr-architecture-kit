"""Executable guard for capability-based durable repository naming."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_repository_naming", ROOT / "scripts" / "check_repository_naming.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_delivery_stage_path_variants_are_rejected() -> None:
    paths = (
        "core/semantic-contract-slice-c.rs",
        "tests/phase_2_contracts.py",
        "docs/hsg-14-notes.md",
        "fixtures/tranche15.yaml",
        "benchmarks/wave_3.py",
    )
    violations = MODULE.path_violations(paths)
    assert len(violations) == len(paths)


def test_domain_and_provenance_paths_are_accepted() -> None:
    paths = (
        "core/src/semantic_contract_set.rs",
        "contracts/semantic-core/v1.0/vectors/semantic-contract-set-governance.json",
        "adrs/ADR-L-0028-semantic-contracts.yaml",
        "contracts/semantic-core/v1.0/definitions/normalized-model-2.3.json",
    )
    assert MODULE.path_violations(paths) == []


def test_local_adr_kit_state_is_rejected_when_tracked() -> None:
    violations = MODULE.path_violations((".adr-kit/promotion/prepared.json",))
    assert len(violations) == 1
    assert "ignored and untracked" in violations[0]


def test_active_identifiers_are_rejected_but_historical_prose_is_ignored(tmp_path: Path) -> None:
    active = tmp_path / "contracts" / "active.py"
    active.parent.mkdir()
    active.write_text("REASON_CODE = 'slice-c-qualified'\n", encoding="utf-8")
    historical = tmp_path / "historical.md"
    historical.write_text("The old Slice C decision was retained.\n", encoding="utf-8")
    assert MODULE.content_violations(tmp_path, ("contracts/active.py",))
    assert MODULE.content_violations(tmp_path, ("historical.md",)) == []


def test_broad_generated_directory_prefixes_do_not_hide_active_violations(tmp_path: Path) -> None:
    active = tmp_path / "tests" / "golden" / "expected" / "active.py"
    active.parent.mkdir(parents=True)
    active.write_text("name = 'wave_3'\n", encoding="utf-8")
    assert MODULE.content_violations(tmp_path, ("tests/golden/expected/active.py",))


def test_tracked_repository_naming_passes() -> None:
    assert MODULE.find_violations(ROOT) == []
