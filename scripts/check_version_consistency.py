"""Require package, runtime, installed metadata, and CLI versions to agree."""

from __future__ import annotations

import sys
import json
import re
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path
from typing import Any

from click.testing import CliRunner

import adr_kit
from adr_kit.api import capabilities
from adr_kit.cli.main import cli

ROOT = Path(__file__).resolve().parents[1]


def _node_package_versions() -> dict[str, str]:
    package_path = ROOT / "packages" / "node" / "package.json"
    lock_path = ROOT / "packages" / "node" / "package-lock.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock_root = lock["packages"][""]
    return {
        "packages/node/package.json": str(package["version"]),
        "packages/node/package-lock.json": str(lock["version"]),
        "packages/node/package-lock.json packages['']": str(lock_root["version"]),
    }


def _project_metadata() -> tuple[str, str]:
    payload: dict[str, Any] = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["name"]), str(payload["project"]["version"])


def main() -> int:
    project_name, project = _project_metadata()
    if project_name != "adr-architecture-kit":
        print(f"unexpected project name: {project_name}", file=sys.stderr)
        return 1

    package_init = (ROOT / "src" / "adr_kit" / "__init__.py").read_text(encoding="utf-8")
    if re.search(r"__version__\s*=\s*['\"]\d", package_init):
        print(
            "duplicate runtime version literal detected in src/adr_kit/__init__.py", file=sys.stderr
        )
        return 1

    runtime = adr_kit.__version__
    try:
        metadata = installed_version("adr-architecture-kit")
    except PackageNotFoundError:
        metadata = None

    result = CliRunner().invoke(cli, ["--version"])
    if result.exit_code != 0:
        print(result.output, file=sys.stderr)
        return 1
    cli_version = result.output.strip().rsplit(" ", 1)[-1]
    versions = {
        "pyproject.toml": project,
        "adr_kit.__version__": runtime,
        "adr --version": cli_version,
        "adr_kit.api capabilities": capabilities().package_version,
        **_node_package_versions(),
    }
    if metadata is not None:
        versions["installed metadata"] = metadata
    for source, value in versions.items():
        print(f"{source}: {value}")
    if len(set(versions.values())) != 1:
        print("version drift detected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
