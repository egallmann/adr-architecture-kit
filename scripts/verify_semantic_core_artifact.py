"""Verify that every host ships the exact source-built semantic-core artifact."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (
    ROOT / "core" / "target" / "wasm32-unknown-unknown" / "release" / "adr_kit_semantic_core.wasm",
    ROOT / "src" / "adr_kit" / "core" / "semantic-core.wasm",
    ROOT / "packages" / "node" / "src" / "generated" / "semantic-core.wasm",
)


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in ARTIFACTS if not path.is_file()]
    if missing:
        raise SystemExit(f"missing semantic-core WASM artifact(s): {', '.join(missing)}")

    size = ARTIFACTS[0].stat().st_size
    if size == 0 or any(path.stat().st_size != size for path in ARTIFACTS[1:]):
        raise SystemExit("semantic-core WASM artifacts must be non-empty and same-sized")

    digests = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in ARTIFACTS
    }
    if len(digests) != 1:
        details = ", ".join(
            f"{path.relative_to(ROOT)}={hashlib.sha256(path.read_bytes()).hexdigest()}"
            for path in ARTIFACTS
        )
        raise SystemExit(f"semantic-core WASM artifacts differ: {details}")

    print(f"source-built semantic-core WASM is byte-identical across hosts: {size} bytes")
    print(f"sha256: {next(iter(digests))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
