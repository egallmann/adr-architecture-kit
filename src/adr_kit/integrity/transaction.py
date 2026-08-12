"""All-or-none multi-target authority commit with journaled recovery."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True, slots=True)
class PlannedWrite:
    relative_path: str
    absolute_path: Path
    content: bytes
    operation: str


class TransactionAborted(RuntimeError):
    """Raised when a fault injector or validation aborts the transaction."""


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def commit_all_or_none(
    project_root: Path,
    writes: list[PlannedWrite],
    *,
    validate_staged: Callable[[Path], None],
    fault: Callable[[str], None] | None = None,
    journal_root: Path | None = None,
    journal_kind: str = "authority-journal",
) -> None:
    """Stage → validate complete staged post-state → commit all or recover none.

    ``fault(phase)`` may raise to simulate failures. Phases:
    before_staging, during_staging, after_staging, before_commit,
    during_commit:<relative_path>, after_partial_commit
    """

    inject = fault or (lambda _phase: None)
    root = project_root.resolve()
    journal = journal_root or (root / ".adr-kit" / journal_kind / uuid.uuid4().hex)
    journal.mkdir(parents=True, exist_ok=False)
    staging = journal / "staging"
    backups = journal / "backups"
    staging.mkdir()
    backups.mkdir()

    try:
        inject("before_staging")
        staged_files: list[tuple[PlannedWrite, Path]] = []
        for item in writes:
            inject("during_staging")
            staged_path = staging / item.relative_path
            _write_bytes(staged_path, item.content)
            staged_files.append((item, staged_path))
        inject("after_staging")

        # Build complete staged post-state overlay directory
        overlay = journal / "post-state"
        if overlay.exists():
            shutil.rmtree(overlay)
        # Copy governed authority into overlay then apply staged writes
        overlay.mkdir()
        adrs_src = root / "adrs"
        if adrs_src.is_dir():
            shutil.copytree(adrs_src, overlay / "adrs")
        roadmap = root / "ROADMAP.md"
        if roadmap.is_file():
            shutil.copy2(roadmap, overlay / "ROADMAP.md")
        project_yaml = root / "PROJECT.yaml"
        if project_yaml.is_file():
            shutil.copy2(project_yaml, overlay / "PROJECT.yaml")
        for item, staged_path in staged_files:
            target = overlay / item.relative_path
            if item.operation == "create" and (root / item.relative_path).exists():
                raise TransactionAborted(f"create target exists: {item.relative_path}")
            _write_bytes(target, staged_path.read_bytes())

        validate_staged(overlay)
        inject("before_commit")

        # Record backups for existing targets
        manifest = []
        for item, staged_path in staged_files:
            original = root / item.relative_path
            backup_path = None
            if original.exists():
                backup_path = backups / item.relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, backup_path)
            manifest.append(
                {
                    "relative_path": item.relative_path,
                    "operation": item.operation,
                    "backup": (
                        None if backup_path is None else backup_path.relative_to(journal).as_posix()
                    ),
                    "staged": staged_path.relative_to(journal).as_posix(),
                }
            )
        (journal / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (journal / "state").write_text("committing", encoding="utf-8")

        temps: list[Path] = []
        replaced: list[PlannedWrite] = []
        try:
            for item, staged_path in staged_files:
                inject(f"during_commit:{item.relative_path}")
                fd, temp_name = tempfile.mkstemp(
                    prefix=f".{Path(item.relative_path).name}.",
                    dir=str(
                        item.absolute_path.parent if item.absolute_path.parent.exists() else root
                    ),
                )
                os.close(fd)
                temp_path = Path(temp_name)
                temps.append(temp_path)
                temp_path.write_bytes(staged_path.read_bytes())
                item.absolute_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_path, item.absolute_path)
                replaced.append(item)
                inject("after_partial_commit")
        except Exception:
            # Recover to pre-apply authority using backups / delete creates
            for item in reversed(replaced):
                backup = backups / item.relative_path
                if backup.exists():
                    item.absolute_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, item.absolute_path)
                elif item.operation == "create" and item.absolute_path.exists():
                    item.absolute_path.unlink()
            for temp_path in temps:
                if temp_path.exists():
                    temp_path.unlink()
            (journal / "state").write_text("recovered", encoding="utf-8")
            raise

        for temp_path in temps:
            if temp_path.exists():
                temp_path.unlink()
        (journal / "state").write_text("committed", encoding="utf-8")
    finally:
        # Keep journal on failure for diagnostics; remove on success
        state_file = journal / "state"
        if state_file.is_file() and state_file.read_text(encoding="utf-8").strip() == "committed":
            shutil.rmtree(journal, ignore_errors=True)


def recover_interrupted_commit(journal: Path, project_root: Path) -> None:
    """Restore authority from a committing journal if present."""

    state = (
        (journal / "state").read_text(encoding="utf-8").strip()
        if (journal / "state").exists()
        else ""
    )
    if state not in {"committing", "recovered"}:
        return
    manifest = json.loads((journal / "manifest.json").read_text(encoding="utf-8"))
    root = project_root.resolve()
    for item in reversed(manifest):
        absolute = root / item["relative_path"]
        backup_rel = item.get("backup")
        if backup_rel:
            shutil.copy2(journal / backup_rel, absolute)
        elif item.get("operation") == "create" and absolute.exists():
            absolute.unlink()
    (journal / "state").write_text("recovered", encoding="utf-8")
