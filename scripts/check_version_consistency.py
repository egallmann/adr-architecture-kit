"""Require package, runtime, installed metadata, and CLI versions to agree."""

from __future__ import annotations

import sys
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path
from typing import Any

from click.testing import CliRunner

import adr_kit
from adr_kit.cli.main import cli

ROOT = Path(__file__).resolve().parents[1]


def _project_version() -> str:
    payload: dict[str, Any] = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def main() -> int:
    project = _project_version()
    runtime = adr_kit.__version__
    try:
        metadata = installed_version("adr-architecture-kit")
    except PackageNotFoundError:
        print(
            "adr-architecture-kit is not installed; install the project before validation",
            file=sys.stderr,
        )
        return 1

    result = CliRunner().invoke(cli, ["--version"])
    if result.exit_code != 0:
        print(result.output, file=sys.stderr)
        return 1
    cli_version = result.output.strip().rsplit(" ", 1)[-1]
    versions = {
        "pyproject.toml": project,
        "installed metadata": metadata,
        "adr_kit.__version__": runtime,
        "adr --version": cli_version,
    }
    for source, value in versions.items():
        print(f"{source}: {value}")
    if len(set(versions.values())) != 1:
        print("version drift detected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
