"""Unchanged internal Rust must still prove exact source-built host parity."""

from pathlib import Path
import subprocess

import pytest

from scripts import check_semantic_core_artifact_change as guard

pytestmark = pytest.mark.fast


def setup_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    monkeypatch.setattr(guard, "ROOT", tmp_path)
    for path in [
        *guard.ARTIFACTS,
        "core/target/wasm32-unknown-unknown/release/adr_kit_semantic_core.wasm",
    ]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"same source-built bytes")
    calls = []
    monkeypatch.setattr(guard.subprocess, "run", lambda command, **kwargs: calls.append(command))
    monkeypatch.setattr(guard, "changed_files", lambda: {"core/src/internal.rs"})
    return calls


def test_unchanged_artifacts_require_a_fresh_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = setup_artifacts(tmp_path, monkeypatch)
    assert guard.main() == 0
    assert len(calls) == 1
    assert calls[0][0:2] == ["cargo", "build"]
    assert calls[0][-3:] == ["--target", "wasm32-unknown-unknown", "--release"]


@pytest.mark.parametrize("path", sorted(guard.ARTIFACTS))
def test_either_stale_host_copy_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    setup_artifacts(tmp_path, monkeypatch)
    (tmp_path / path).write_bytes(b"stale")
    with pytest.raises(SystemExit, match="bytes differ"):
        guard.main()


def test_failed_build_cannot_accept_stale_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup_artifacts(tmp_path, monkeypatch)

    def failed(*args: object, **kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, "cargo")

    monkeypatch.setattr(guard.subprocess, "run", failed)
    with pytest.raises(subprocess.CalledProcessError):
        guard.main()


def test_missing_or_empty_artifact_is_not_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup_artifacts(tmp_path, monkeypatch)
    built = tmp_path / "core/target/wasm32-unknown-unknown/release/adr_kit_semantic_core.wasm"
    built.write_bytes(b"")
    with pytest.raises(SystemExit):
        guard.main()
    built.unlink()
    with pytest.raises(FileNotFoundError):
        guard.main()


def test_unrelated_change_does_not_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = setup_artifacts(tmp_path, monkeypatch)
    monkeypatch.setattr(guard, "changed_files", lambda: {"docs/guide.md"})
    assert guard.main() == 0
    assert not calls
