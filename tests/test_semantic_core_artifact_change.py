"""Artifact guards require changed host bytes or a fresh unchanged-source proof."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import check_semantic_core_artifact_change as guard

pytestmark = pytest.mark.fast


@pytest.mark.parametrize("fault", [None, "compiled", "working", "committed", "empty", "build"])
def test_unchanged_artifact_proof_requires_fresh_build_and_both_exact_copies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    monkeypatch.setattr(guard, "ROOT", tmp_path)
    source = tmp_path / "core/target/wasm32-unknown-unknown/release/adr_kit_semantic_core.wasm"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"baseline")  # A stale matching build must not suffice.
    for relative in guard.ARTIFACTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"wrong" if fault == "working" else b"baseline")
    commands: list[list[str]] = []

    def run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        commands.append(command)
        assert kwargs["check"] is True
        assert kwargs["cwd"] == tmp_path
        if command[0] == "cargo":
            assert command[-1] == "--locked"
            if fault == "build":
                raise subprocess.CalledProcessError(1, command)
            source.write_bytes(
                b"" if fault == "empty" else b"new" if fault == "compiled" else b"baseline"
            )
            return SimpleNamespace(stdout=b"")
        assert command[:2] == ["git", "show"]
        assert command[2].removeprefix("HEAD:") in guard.ARTIFACTS
        return SimpleNamespace(stdout=b"wrong" if fault == "committed" else b"baseline")

    monkeypatch.setattr(guard.subprocess, "run", run)
    if fault is None:
        guard.verify_unchanged_artifacts()
        assert len(commands) == 3
    else:
        with pytest.raises((SystemExit, subprocess.CalledProcessError)):
            guard.verify_unchanged_artifacts()
    assert commands[0][0] == "cargo"


@pytest.mark.parametrize("artifacts", [set(), guard.ARTIFACTS, {next(iter(guard.ARTIFACTS))}])
def test_source_changes_require_both_updates_or_fresh_parity(
    monkeypatch: pytest.MonkeyPatch, artifacts: set[str]
) -> None:
    monkeypatch.setattr(
        guard, "changed_files", lambda: {"core/src/authoring_construction_v12.rs"} | artifacts
    )
    proofs: list[bool] = []
    monkeypatch.setattr(guard, "verify_unchanged_artifacts", lambda: proofs.append(True))
    if len(artifacts) == 1:
        with pytest.raises(SystemExit, match="both host copies"):
            guard.main()
        assert not proofs
    else:
        assert guard.main() == 0
        assert bool(proofs) == (not artifacts)
