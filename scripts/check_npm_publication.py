"""Determine whether a retained npm tarball needs publication."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY = "https://registry.npmjs.org"
NOOP = "noop"
PUBLISH = "publish"


class NpmPublicationError(RuntimeError):
    """Raised when an existing npm version cannot be proven equivalent."""


def _read_package_identity(tarball: Path) -> tuple[str, str]:
    with tarfile.open(tarball, mode="r:gz") as archive:
        try:
            member = archive.getmember("package/package.json")
        except KeyError as exc:
            raise NpmPublicationError("npm tarball does not contain package/package.json") from exc
        package_file = archive.extractfile(member)
        if package_file is None:
            raise NpmPublicationError("npm tarball package.json is not readable")
        package = json.loads(package_file.read())

    name = package.get("name")
    version = package.get("version")
    if not isinstance(name, str) or not name:
        raise NpmPublicationError("npm tarball package.json has no package name")
    if not isinstance(version, str) or not version:
        raise NpmPublicationError("npm tarball package.json has no package version")
    return name, version


def _integrity(tarball: Path) -> str:
    digest = hashlib.sha512(tarball.read_bytes()).digest()
    return "sha512-" + base64.b64encode(digest).decode("ascii")


def fetch_metadata(package_name: str, registry: str = DEFAULT_REGISTRY) -> dict[str, Any] | None:
    """Return package metadata, or ``None`` when the package does not exist."""

    package_path = urllib.parse.quote(package_name, safe="")
    request = urllib.request.Request(
        f"{registry.rstrip('/')}/{package_path}",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise NpmPublicationError(
            f"npm registry metadata request failed with HTTP {exc.code}"
        ) from exc
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise NpmPublicationError(f"npm registry metadata request failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise NpmPublicationError("npm registry returned an invalid metadata payload")
    return payload


def decide_publication(
    *,
    package_name: str,
    package_version: str,
    tarball_integrity: str,
    metadata: dict[str, Any] | None,
) -> str:
    """Return ``publish`` or ``noop``; reject an unverifiable existing version."""

    if metadata is None:
        return PUBLISH

    versions = metadata.get("versions")
    if not isinstance(versions, dict) or package_version not in versions:
        return PUBLISH

    version_metadata = versions[package_version]
    dist = version_metadata.get("dist") if isinstance(version_metadata, dict) else None
    existing_integrity = dist.get("integrity") if isinstance(dist, dict) else None
    if existing_integrity != tarball_integrity:
        raise NpmPublicationError(
            "existing npm version does not match the retained tarball: "
            f"{package_name}@{package_version}"
        )
    return NOOP


def check_tarball(tarball: Path, registry: str = DEFAULT_REGISTRY) -> str:
    package_name, package_version = _read_package_identity(tarball)
    return decide_publication(
        package_name=package_name,
        package_version=package_version,
        tarball_integrity=_integrity(tarball),
        metadata=fetch_metadata(package_name, registry),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tarball", type=Path, required=True)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    arguments = parser.parse_args()
    if not arguments.tarball.is_file():
        raise SystemExit(f"npm tarball does not exist: {arguments.tarball}")
    try:
        print(check_tarball(arguments.tarball, arguments.registry))
    except NpmPublicationError as exc:
        raise SystemExit(str(exc)) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
