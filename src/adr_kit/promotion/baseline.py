"""Path-scoped authority baseline equivalence for promotion concurrency."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

AUTHORITY_PATHSPECS = ("adrs", "ROADMAP.md")


def _run_git(project_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git command failed")
    return completed.stdout


def list_authority_paths(project_root: Path) -> list[Path]:
    root = project_root.resolve()
    paths: list[Path] = []
    roadmap = root / "ROADMAP.md"
    if roadmap.exists():
        paths.append(roadmap)
    adrs = root / "adrs"
    if adrs.is_dir():
        for path in sorted(adrs.rglob("*")):
            if path.is_file():
                paths.append(path)
    return paths


def authority_content_fingerprint(project_root: Path) -> str:
    digest = hashlib.sha256()
    root = project_root.resolve()
    for path in list_authority_paths(root):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def authority_tree_at_commit(project_root: Path, commit: str) -> dict[str, str]:
    """Map repo-relative authority paths to blob hashes at a commit."""

    mapping: dict[str, str] = {}
    for pathspec in AUTHORITY_PATHSPECS:
        output = _run_git(
            project_root,
            "ls-tree",
            "-r",
            commit,
            "--",
            pathspec,
        )
        for line in output.splitlines():
            # mode type hash\tpath
            meta, _, path = line.partition("\t")
            if not path:
                continue
            parts = meta.split()
            if len(parts) < 3:
                continue
            mapping[path.replace("\\", "/")] = parts[2]
    return mapping


def working_tree_authority_blobs(project_root: Path) -> dict[str, str]:
    root = project_root.resolve()
    mapping: dict[str, str] = {}
    for path in list_authority_paths(root):
        relative = path.relative_to(root).as_posix()
        mapping[relative] = hashlib.sha1(
            b"blob %d\0" % path.stat().st_size + path.read_bytes()
        ).hexdigest()
    return mapping


def path_scoped_baseline_equivalent(
    project_root: Path,
    *,
    baseline_kind: str,
    baseline_value: str,
) -> tuple[bool, str]:
    """Return (equivalent, detail) comparing governed authority to baseline."""

    if baseline_kind != "git_commit":
        return False, f"unsupported baseline kind {baseline_kind}"
    try:
        baseline_blobs = authority_tree_at_commit(project_root, baseline_value)
    except Exception as exc:  # noqa: BLE001
        return False, f"baseline commit unavailable: {exc}"

    # Dirty / untracked governed paths invalidate
    try:
        status = _run_git(
            project_root,
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *AUTHORITY_PATHSPECS,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"git status failed: {exc}"
    if status.strip():
        return False, "governed authority working tree dirty or untracked"

    try:
        head_blobs = authority_tree_at_commit(project_root, "HEAD")
    except Exception as exc:  # noqa: BLE001
        return False, f"HEAD tree unavailable: {exc}"

    if baseline_blobs != head_blobs:
        return False, "authority tree differs from baseline commit"
    return True, "authority scope matches baseline"
