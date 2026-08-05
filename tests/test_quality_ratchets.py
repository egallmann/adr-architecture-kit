"""Phase 0 no-regression quality ratchet contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
