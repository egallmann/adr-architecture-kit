"""Require tracked WASM updates or prove unchanged bytes with a fresh build."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {
    "src/adr_kit/core/semantic-core.wasm",
    "packages/node/src/generated/semantic-core.wasm",
}
SOURCE_PREFIXES = ("core/src/", "core/Cargo.toml", "core/Cargo.lock")


def verify_unchanged_artifacts() -> None:
    # Internal/test-only Rust can optimize out completely. Never accept that
    # assertion from a change label or stale target file: build this checkout.
    subprocess.run(
        [
            "cargo",
            "build",
            "--manifest-path",
            str(ROOT / "core/Cargo.toml"),
            "--target",
            "wasm32-unknown-unknown",
            "--release",
        ],
        cwd=ROOT,
        check=True,
    )
    built = ROOT / "core/target/wasm32-unknown-unknown/release/adr_kit_semantic_core.wasm"
    expected = built.read_bytes()
    if not expected or any((ROOT / path).read_bytes() != expected for path in ARTIFACTS):
        raise SystemExit(
            "semantic-core source-built bytes differ from tracked host artifacts; "
            "build and commit both current host copies"
        )
    print("fresh source build proves both tracked host artifacts unchanged")


def changed_files() -> set[str]:
    base = os.environ.get("GITHUB_BASE_SHA")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not base and event_path:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
        base = payload.get("pull_request", {}).get("base", {}).get("sha")
        base = base or payload.get("before")
    if base:
        command = ["git", "diff", "--name-only", f"{base}...HEAD"]
    else:
        command = ["git", "diff", "--name-only", "HEAD^", "HEAD"]
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return {line.replace("\\", "/") for line in result.stdout.splitlines() if line}


def main() -> int:
    changed = changed_files()
    semantic_source_changed = any(path.startswith(SOURCE_PREFIXES) for path in changed)
    if semantic_source_changed and not ARTIFACTS.issubset(changed):
        verify_unchanged_artifacts()
    print("semantic-core source/artifact change guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
