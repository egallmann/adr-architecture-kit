from __future__ import annotations

from pathlib import Path

import yaml

from adr_kit.federation.workspace_attribution import build_workspace_attribution_federation


def _write_evidence(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.2",
                "type": "implementation_attribution_evidence",
                "records": records,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_manifest(path: Path, adrs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "type": "manifest",
                "adrs": adrs,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_homonym_produces_separate_qualified_rows_and_group(tmp_path: Path) -> None:
    workspace_root = tmp_path / "ws"
    state_dir = tmp_path / ".ste-workspace"

    repo_a = workspace_root / "repo-a"
    repo_b = workspace_root / "repo-b"
    repo_a.mkdir(parents=True)
    repo_b.mkdir(parents=True)

    _write_manifest(
        repo_a / "adrs" / "manifest.yaml",
        [{"id": "ADR-L-0013", "title": "Repository Boundary", "status": "accepted"}],
    )
    _write_manifest(
        repo_b / "adrs" / "manifest.yaml",
        [{"id": "ADR-L-0013", "title": "Path Portability", "status": "accepted"}],
    )

    _write_evidence(
        state_dir / "state" / "repo-a" / "attribution" / "implementation-attribution-evidence.yaml",
        [
            {
                "implementation_entity_id": "function:a:one:1",
                "implementation_entity_type": "function",
                "attributed_adrs": ["ADR-L-0013"],
                "enforced_invariants": [],
                "provenance": {"source_file": "a.py", "extractor": "t", "commit": None},
            },
            {
                "implementation_entity_id": "function:a:two:2",
                "implementation_entity_type": "function",
                "attributed_adrs": ["ADR-L-0013"],
                "enforced_invariants": [],
                "provenance": {"source_file": "a.py", "extractor": "t", "commit": None},
            },
        ],
    )
    _write_evidence(
        state_dir / "state" / "repo-b" / "attribution" / "implementation-attribution-evidence.yaml",
        [
            {
                "implementation_entity_id": "function:b:one:1",
                "implementation_entity_type": "function",
                "attributed_adrs": ["ADR-L-0013"],
                "enforced_invariants": [],
                "provenance": {"source_file": "b.ts", "extractor": "t", "commit": None},
            },
        ],
    )

    doc = build_workspace_attribution_federation(
        workspace_root=workspace_root,
        state_dir=state_dir,
        repos=[
            ("repo-a", repo_a),
            ("repo-b", repo_b),
        ],
    )

    assert doc["type"] == "workspace_attribution_federation"
    qualified = {row["qualified_id"]: row for row in doc["qualified_adrs"]}
    assert set(qualified) == {"repo-a:ADR-L-0013", "repo-b:ADR-L-0013"}
    assert qualified["repo-a:ADR-L-0013"]["embodiment_count"] == 2
    assert qualified["repo-b:ADR-L-0013"]["embodiment_count"] == 1
    assert qualified["repo-a:ADR-L-0013"]["title"] == "Repository Boundary"
    assert qualified["repo-b:ADR-L-0013"]["title"] == "Path Portability"

    homonyms = {g["bare_id"]: g for g in doc["homonym_groups"]}
    assert "ADR-L-0013" in homonyms
    assert set(homonyms["ADR-L-0013"]["qualified_ids"]) == {
        "repo-a:ADR-L-0013",
        "repo-b:ADR-L-0013",
    }
    assert homonyms["ADR-L-0013"]["collision_kind"] == "independent_decisions"


def test_embodiment_not_summed_across_corpora(tmp_path: Path) -> None:
    workspace_root = tmp_path / "ws"
    state_dir = tmp_path / ".ste-workspace"
    repo_a = workspace_root / "repo-a"
    repo_b = workspace_root / "repo-b"
    repo_a.mkdir(parents=True)
    repo_b.mkdir(parents=True)

    for repo in (repo_a, repo_b):
        _write_manifest(
            repo / "adrs" / "manifest.yaml",
            [{"id": "ADR-L-0004", "title": f"Title {repo.name}", "status": "accepted"}],
        )

    for repo_name, repo_path, count in (
        ("repo-a", repo_a, 3),
        ("repo-b", repo_b, 1),
    ):
        records = [
            {
                "implementation_entity_id": f"function:{repo_name}:{i}:1",
                "implementation_entity_type": "function",
                "attributed_adrs": ["ADR-L-0004"],
                "enforced_invariants": [],
                "provenance": {"source_file": "x", "extractor": "t", "commit": None},
            }
            for i in range(count)
        ]
        _write_evidence(
            state_dir / "state" / repo_name / "attribution" / "implementation-attribution-evidence.yaml",
            records,
        )

    doc = build_workspace_attribution_federation(
        workspace_root=workspace_root,
        state_dir=state_dir,
        repos=[("repo-a", repo_a), ("repo-b", repo_b)],
    )
    counts = {r["qualified_id"]: r["embodiment_count"] for r in doc["qualified_adrs"]}
    assert len(counts) == 2
    assert counts["repo-a:ADR-L-0004"] == 3
    assert counts["repo-b:ADR-L-0004"] == 1
    assert "ADR-L-0004" not in counts
