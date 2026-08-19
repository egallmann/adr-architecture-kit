from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL_ROOT = ROOT / "docs" / "design-journal"
ALLOWLIST = {
    "docs/design-journal/README.md",
    "docs/design-journal/2026-phase-1-public-sdk.md",
    "docs/design-journal/2026-phase-2-schema-v12.md",
    "docs/design-journal/2026-production-hardening.md",
}


def _tracked_journal_paths() -> set[str]:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT}", "ls-files", "docs/design-journal"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def test_only_grandfathered_explanatory_journals_are_tracked() -> None:
    assert _tracked_journal_paths() <= ALLOWLIST


def test_active_design_journal_working_state_is_ignored() -> None:
    ignore_probe = JOURNAL_ROOT / "2026-active-working-state.md"
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT}", "check-ignore", "--no-index", str(ignore_probe)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "docs/design-journal/*" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_authority_boundary_does_not_require_local_journal_files() -> None:
    tracked = _tracked_journal_paths()
    assert "docs/design-journal/2026-universal-uuidv7-entity-identity.md" not in tracked
    assert (
        "docs/design-journal/2026-universal-uuidv7-alias-collision-disposition.yaml" not in tracked
    )
    assert "docs/design-journal/2026-universal-uuidv7-human-gates.md" not in tracked
