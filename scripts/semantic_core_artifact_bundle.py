"""Create and consume commit-bound semantic-core workflow artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WASM_NAME = "semantic-core.wasm"
MANIFEST_NAME = "manifest.json"
ARTIFACT_DESTINATIONS = (
    Path("core/target/wasm32-unknown-unknown/release/adr_kit_semantic_core.wasm"),
    Path("src/adr_kit/core/semantic-core.wasm"),
    Path("packages/node/src/generated/semantic-core.wasm"),
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _commit(value: str) -> str:
    if not COMMIT_PATTERN.fullmatch(value):
        raise ValueError("source commit must be a full lowercase 40-character Git SHA")
    return value


def create_bundle(artifact: Path, output_dir: Path, source_commit: str) -> dict[str, Any]:
    """Copy a verified build output into a bundle bound to its source commit."""

    source_commit = _commit(source_commit)
    data = artifact.read_bytes()
    if not data:
        raise ValueError("semantic-core artifact must not be empty")
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / WASM_NAME).write_bytes(data)
    manifest = {
        "artifact": WASM_NAME,
        "format_version": 1,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "source_commit": source_commit,
    }
    (output_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return manifest


def consume_bundle(
    bundle_dir: Path, expected_commit: str, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Verify commit and content identity before placing bytes at host paths."""

    expected_commit = _commit(expected_commit)
    manifest_path = bundle_dir / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_keys = {"artifact", "format_version", "sha256", "size_bytes", "source_commit"}
    if not isinstance(manifest, dict) or set(manifest) != expected_keys:
        raise ValueError("semantic-core artifact manifest has an unexpected shape")
    if manifest["format_version"] != 1 or manifest["artifact"] != WASM_NAME:
        raise ValueError("unsupported semantic-core artifact manifest")
    if manifest["source_commit"] != expected_commit:
        raise ValueError("semantic-core artifact source commit does not match this checkout")
    if not isinstance(manifest["sha256"], str) or not SHA256_PATTERN.fullmatch(manifest["sha256"]):
        raise ValueError("semantic-core artifact manifest has an invalid SHA-256")
    data = (bundle_dir / WASM_NAME).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if not data or len(data) != manifest["size_bytes"] or digest != manifest["sha256"]:
        raise ValueError("semantic-core artifact bytes do not match the qualified manifest")

    repo_root = repo_root.resolve()
    for relative_path in ARTIFACT_DESTINATIONS:
        destination = (repo_root / relative_path).resolve()
        if not destination.is_relative_to(repo_root):
            raise ValueError("semantic-core artifact destination escapes the checkout")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundle_dir / WASM_NAME, destination)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--artifact", type=Path, required=True)
    create.add_argument("--output-dir", type=Path, required=True)
    create.add_argument("--source-commit", required=True)
    consume = subparsers.add_parser("consume")
    consume.add_argument("--bundle-dir", type=Path, required=True)
    consume.add_argument("--source-commit", required=True)
    consume.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        if args.command == "create":
            result = create_bundle(args.artifact, args.output_dir, args.source_commit)
        else:
            result = consume_bundle(args.bundle_dir, args.source_commit, args.repo_root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(
        f"semantic-core artifact {args.command} verified for {result['source_commit']} "
        f"sha256={result['sha256']} size={result['size_bytes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
