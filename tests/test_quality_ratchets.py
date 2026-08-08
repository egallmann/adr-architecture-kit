"""Phase 0 no-regression quality ratchet contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PHASE1_FILES = (
    "src/adr_kit/_version.py",
    "src/adr_kit/api/__init__.py",
    "src/adr_kit/api/_contracts.py",
    "src/adr_kit/api/_errors.py",
    "src/adr_kit/api/_operations.py",
    "src/adr_kit/repository/_normalized_bundle.py",
    "scripts/test_sdk_consumer.py",
    "tests/test_public_sdk_contract.py",
    "tests/test_public_sdk_operations.py",
    "tests/test_cli_application_delegation.py",
    "tests/test_version_authority.py",
)


def test_committed_quality_baselines_reject_new_findings() -> None:
    script = ROOT / "scripts" / "check_quality_ratchets.py"
    assert script.is_file(), "missing Phase 0 quality-ratchet runner"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_phase1_files_are_explicit_zero_debt_targets() -> None:
    source = (ROOT / "scripts" / "check_quality_ratchets.py").read_text(encoding="utf-8")

    assert "PHASE1_FILES" in source
    for relative_path in PHASE1_FILES:
        assert f'"{relative_path}"' in source
