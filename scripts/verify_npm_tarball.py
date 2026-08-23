"""Verify the retained npm package before publication."""

from __future__ import annotations

import argparse
import json
import tarfile
import tomllib
from pathlib import Path

DEFAULT_PACKAGE_NAME = "@system-of-thought/adr-kit"
EXPECTED_REPOSITORY_URL = "https://github.com/egallmann/adr-architecture-kit"
REQUIRED_FILES = (
    "package.json",
    "dist/index.js",
    "dist/index.d.ts",
    "dist/schemas/canonical/normalized-model/v2.1/normalized-architecture-model.schema.json",
    "README.md",
    "LICENSE",
)


def expected_version() -> str:
    root = Path(__file__).resolve().parents[1]
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def verify(tarball: Path, package_name: str, package_version: str) -> int:
    with tarfile.open(tarball, mode="r:gz") as archive:
        members = {member.name for member in archive.getmembers()}
        prefix = "package/"
        package_json_name = prefix + "package.json"
        package_member = archive.getmember(package_json_name)
        package_file = archive.extractfile(package_member)
        if package_file is None:
            raise SystemExit("npm package does not contain readable package.json")
        package = json.loads(package_file.read())

        if package.get("name") != package_name:
            raise SystemExit(
                f"npm package name mismatch: {package.get('name')!r} != {package_name!r}"
            )
        if package.get("version") != package_version:
            raise SystemExit(
                f"npm package version mismatch: {package.get('version')!r} != {package_version!r}"
            )
        repository = package.get("repository")
        repository_url = repository.get("url") if isinstance(repository, dict) else None
        if repository_url != EXPECTED_REPOSITORY_URL:
            raise SystemExit(
                "npm package repository mismatch: "
                f"{repository_url!r} != {EXPECTED_REPOSITORY_URL!r}"
            )

        missing = [prefix + path for path in REQUIRED_FILES if prefix + path not in members]
        if missing:
            raise SystemExit(f"npm package is missing required files: {', '.join(missing)}")
        if any(
            name == prefix + "node_modules" or name.startswith(prefix + "node_modules/")
            for name in members
        ):
            raise SystemExit("npm package must not contain node_modules")

    print(f"verified npm package {package_name}@{package_version} ({len(members)} files)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tarball", type=Path, required=True)
    parser.add_argument("--expected-name", default=DEFAULT_PACKAGE_NAME)
    parser.add_argument("--expected-version", default=None)
    args = parser.parse_args()
    if not args.tarball.is_file():
        raise SystemExit(f"npm tarball does not exist: {args.tarball}")
    return verify(args.tarball, args.expected_name, args.expected_version or expected_version())


if __name__ == "__main__":
    raise SystemExit(main())
