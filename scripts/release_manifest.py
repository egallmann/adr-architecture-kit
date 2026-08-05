"""Create and strictly verify a build-once release artifact manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

WHEEL_SUFFIX = ".whl"
SDIST_SUFFIX = ".tar.gz"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _distribution_files(dist_dir: Path) -> list[Path]:
    wheels = sorted(
        path for path in dist_dir.iterdir() if path.is_file() and path.name.endswith(WHEEL_SUFFIX)
    )
    sdists = sorted(
        path for path in dist_dir.iterdir() if path.is_file() and path.name.endswith(SDIST_SUFFIX)
    )
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError(
            f"expected exactly one wheel and one sdist; found {len(wheels)} wheel(s), {len(sdists)} sdist(s)"
        )
    return [wheels[0], sdists[0]]


def _filename_has_version(filename: str, package_version: str) -> bool:
    escaped = re.escape(package_version)
    if filename.endswith(WHEEL_SUFFIX):
        return re.search(rf"-{escaped}-[^/]+\.whl$", filename) is not None
    return filename.endswith(f"-{package_version}{SDIST_SUFFIX}")


def create_manifest(dist_dir: Path, output: Path, source_commit: str, package_version: str) -> None:
    artifacts = _distribution_files(dist_dir)
    if not all(_filename_has_version(path.name, package_version) for path in artifacts):
        raise ValueError("distribution filename/version mismatch")
    payload = {
        "schema_version": 1,
        "source_commit": source_commit,
        "package_version": package_version,
        "artifacts": [
            {"filename": path.name, "size": path.stat().st_size, "sha256": _sha256(path)}
            for path in artifacts
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest(
    dist_dir: Path,
    manifest_path: Path,
    expected_source_commit: str | None = None,
    expected_version: str | None = None,
    expected_tag: str | None = None,
) -> None:
    payload: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported release manifest schema")
    source_commit = str(payload.get("source_commit", ""))
    package_version = str(payload.get("package_version", ""))
    if expected_source_commit is not None and source_commit != expected_source_commit:
        raise ValueError("source commit mismatch")
    if expected_version is not None and package_version != expected_version:
        raise ValueError("package version mismatch")
    if expected_tag is not None and expected_tag != f"v{package_version}":
        raise ValueError("release tag must equal v<package-version>")

    files = _distribution_files(dist_dir)
    actual_names = {path.name for path in files}
    records = payload.get("artifacts")
    if not isinstance(records, list):
        raise ValueError("release manifest artifacts must be a list")
    manifest_names = {
        str(record.get("filename", "")) for record in records if isinstance(record, dict)
    }
    if actual_names != manifest_names or len(records) != 2:
        raise ValueError("release manifest has missing or extra artifacts")

    by_name = {path.name: path for path in files}
    for untyped_record in records:
        if not isinstance(untyped_record, dict):
            raise ValueError("invalid artifact record")
        record: dict[str, Any] = untyped_record
        filename = str(record.get("filename", ""))
        path = by_name[filename]
        if not _filename_has_version(filename, package_version):
            raise ValueError(f"artifact version mismatch: {filename}")
        if record.get("size") != path.stat().st_size:
            raise ValueError(f"artifact size mismatch: {filename}")
        if record.get("sha256") != _sha256(path):
            raise ValueError(f"artifact hash mismatch: {filename}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--dist-dir", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--source-commit", required=True)
    create.add_argument("--version", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--dist-dir", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--expected-source-commit")
    verify.add_argument("--expected-version")
    verify.add_argument("--expected-tag")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "create":
            create_manifest(
                arguments.dist_dir, arguments.output, arguments.source_commit, arguments.version
            )
            print(arguments.output)
        else:
            verify_manifest(
                arguments.dist_dir,
                arguments.manifest,
                arguments.expected_source_commit,
                arguments.expected_version,
                arguments.expected_tag,
            )
            print("release manifest verified")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"release manifest error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
