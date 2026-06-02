from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from adr_kit.models import ImplementationAttributionEvidence


def _load_manifest_titles(manifest_path: Path) -> dict[str, str]:
    if not manifest_path.is_file():
        return {}
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    titles: dict[str, str] = {}
    for entry in data.get("adrs") or []:
        if isinstance(entry, dict) and entry.get("id"):
            titles[str(entry["id"])] = str(entry.get("title") or entry["id"])
    return titles


def _load_evidence(evidence_path: Path) -> ImplementationAttributionEvidence | None:
    if not evidence_path.is_file():
        return None
    data = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
    return ImplementationAttributionEvidence.model_validate(data)


def build_workspace_attribution_federation(
    *,
    workspace_root: Path,
    state_dir: Path,
    repos: list[tuple[str, Path]],
) -> dict[str, Any]:
    """
    Build derived workspace attribution federation from per-repo evidence files.

    ``repos`` is a list of (workspace_repo_key, absolute_repo_root) pairs.
    """
    embodiment_by_qualified: dict[str, int] = defaultdict(int)
    meta_by_qualified: dict[str, dict[str, Any]] = {}
    bare_to_qualified: dict[str, set[str]] = defaultdict(set)

    for repo_key, repo_root in repos:
        evidence_path = (
            state_dir
            / "state"
            / repo_key
            / "attribution"
            / "implementation-attribution-evidence.yaml"
        )
        evidence = _load_evidence(evidence_path)
        titles = _load_manifest_titles(repo_root / "adrs" / "manifest.yaml")

        if evidence is None:
            continue

        for record in evidence.records:
            for bare_id in record.attributed_adrs:
                qualified_id = f"{repo_key}:{bare_id}"
                embodiment_by_qualified[qualified_id] += 1
                bare_to_qualified[bare_id].add(qualified_id)
                if qualified_id not in meta_by_qualified:
                    meta_by_qualified[qualified_id] = {
                        "qualified_id": qualified_id,
                        "bare_id": bare_id,
                        "corpus_scope": repo_key,
                        "title": titles.get(bare_id, bare_id),
                        "homonym_group": bare_id,
                        "records_from": [repo_key],
                    }

    qualified_adrs = sorted(
        [
            {
                **meta_by_qualified[qid],
                "embodiment_count": embodiment_by_qualified[qid],
            }
            for qid in meta_by_qualified
        ],
        key=lambda row: row["qualified_id"],
    )

    homonym_groups = [
        {
            "bare_id": bare_id,
            "qualified_ids": sorted(qualified_ids),
            "collision_kind": "independent_decisions",
        }
        for bare_id, qualified_ids in sorted(bare_to_qualified.items())
        if len(qualified_ids) >= 2
    ]

    return {
        "schema_version": "1.0",
        "type": "workspace_attribution_federation",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "qualified_adrs": qualified_adrs,
        "homonym_groups": homonym_groups,
    }


def resolve_workspace_repos(workspace_root: Path) -> tuple[Path, list[tuple[str, Path]]]:
    """Resolve state directory and repo list from workspace.yaml under workspace_root or its parent."""
    root = workspace_root.resolve()
    manifest_file: Path | None = None
    for candidate in (root, root.parent):
        for name in ("workspace.yaml", "workspace.yml"):
            path = candidate / name
            if path.is_file():
                manifest_file = path
                root = candidate
                break
        if manifest_file is not None:
            break
    if manifest_file is None:
        raise FileNotFoundError(
            f"No workspace.yaml found under {workspace_root} or its parent",
        )

    data = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid workspace manifest: {manifest_file}")

    output_dir = str(data.get("output_dir") or ".ste-workspace/").strip()
    state_dir = (root / output_dir).resolve()

    repos: list[tuple[str, Path]] = []
    for entry in data.get("repos") or []:
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("path"):
            continue
        repo_key = str(entry["name"])
        repo_path = (root / str(entry["path"])).resolve()
        repos.append((repo_key, repo_path))
    if not repos:
        raise ValueError(f"workspace manifest has no repos: {manifest_file}")
    return state_dir, repos


def write_workspace_attribution_federation(
    output_path: Path,
    *,
    workspace_root: Path,
    state_dir: Path,
    repos: list[tuple[str, Path]],
) -> Path:
    doc = build_workspace_attribution_federation(
        workspace_root=workspace_root,
        state_dir=state_dir,
        repos=repos,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return output_path
