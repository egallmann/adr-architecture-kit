"""Synchronize checked-in Node package versions from pyproject.toml."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "packages" / "node" / "package.json"
PACKAGE_LOCK = ROOT / "packages" / "node" / "package-lock.json"
PACKAGE_NAME = "@system-of-thought/adr-kit"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return payload


def _project_version() -> str:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("version"), str):
        raise ValueError("pyproject.toml project.version is unavailable")
    return str(project["version"])


def _lock_root(payload: dict[str, Any]) -> dict[str, Any]:
    packages = payload.get("packages")
    root = packages.get("") if isinstance(packages, dict) else None
    if not isinstance(root, dict):
        raise ValueError("package-lock.json packages[''] metadata is unavailable")
    return cast(dict[str, Any], root)


def _version_fields(package: dict[str, Any], lock: dict[str, Any]) -> dict[str, str | None]:
    return {
        "packages/node/package.json": (
            package.get("version") if isinstance(package.get("version"), str) else None
        ),
        "packages/node/package-lock.json": (
            lock.get("version") if isinstance(lock.get("version"), str) else None
        ),
        "packages/node/package-lock.json packages['']": (
            _lock_root(lock).get("version")
            if isinstance(_lock_root(lock).get("version"), str)
            else None
        ),
    }


def _check(package: dict[str, Any], lock: dict[str, Any], expected: str) -> list[str]:
    errors: list[str] = []
    if package.get("name") != PACKAGE_NAME:
        errors.append(f"packages/node/package.json name is not {PACKAGE_NAME}")
    if lock.get("name") != PACKAGE_NAME:
        errors.append(f"packages/node/package-lock.json name is not {PACKAGE_NAME}")
    for source, actual in _version_fields(package, lock).items():
        if actual != expected:
            errors.append(f"{source} version {actual!r} does not match pyproject.toml {expected!r}")
    return errors


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail if Node versions drift")
    mode.add_argument("--write", action="store_true", help="synchronize Node versions")
    args = parser.parse_args(argv)

    try:
        expected = _project_version()
        package = _load_json(PACKAGE_JSON)
        lock = _load_json(PACKAGE_LOCK)
        errors = _check(package, lock, expected)
        if args.write:
            package["version"] = expected
            lock["version"] = expected
            _lock_root(lock)["version"] = expected
            _write_json(PACKAGE_JSON, package)
            _write_json(PACKAGE_LOCK, lock)
            errors = _check(_load_json(PACKAGE_JSON), _load_json(PACKAGE_LOCK), expected)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            if not args.write:
                print("run with --write after editing pyproject.toml", file=sys.stderr)
            return 1
        action = "synchronized" if args.write else "consistent"
        print(f"Node package versions {action} with pyproject.toml: {expected}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"Node package version check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
