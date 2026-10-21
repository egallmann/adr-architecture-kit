"""Require updated WASM artifacts or fresh proof that their bytes are unchanged."""

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
    """Build current source; never accept a cached artifact as parity evidence.

    Internal-only Rust changes can disappear from the exported WASM after
    optimization. In that case an artifact diff cannot exist. Compile without
    overwriting host copies and compare both working and committed copies.
    """
    subprocess.run(
        [
            "cargo",
            "build",
            "--manifest-path",
            "core/Cargo.toml",
            "--target",
            "wasm32-unknown-unknown",
            "--release",
            "--locked",
        ],
        cwd=ROOT,
        check=True,
    )
    source = ROOT / "core/target/wasm32-unknown-unknown/release/adr_kit_semantic_core.wasm"
    compiled = source.read_bytes()
    if not compiled:
        raise SystemExit("source-built semantic-core WASM must not be empty")
    for relative in sorted(ARTIFACTS):
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative}"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        if committed != compiled or (ROOT / relative).read_bytes() != compiled:
            raise SystemExit(
                "semantic-core source changed its WASM bytes; build and commit both host artifacts"
            )
    print("fresh source build is byte-identical to both committed host WASM artifacts")


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
        if ARTIFACTS.intersection(changed):
            raise SystemExit("semantic-core artifact updates must include both host copies")
        verify_unchanged_artifacts()
    print("semantic-core source/artifact change guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
