"""Source-aware runtime package-version resolution."""

from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from pathlib import Path
from typing import Any

DIST_NAME = "adr-architecture-kit"
UNKNOWN_VERSION = "0+unknown"
SOURCE_PROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _source_version() -> str:
    """Resolve a direct-source version from the authoritative project metadata."""

    try:
        payload: dict[str, Any] = tomllib.loads(SOURCE_PROJECT.read_text(encoding="utf-8"))
        project = payload["project"]
        if not isinstance(project, dict) or project.get("name") != DIST_NAME:
            return UNKNOWN_VERSION
        version = project.get("version")
        return version if isinstance(version, str) and version else UNKNOWN_VERSION
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):  # fmt: skip
        return UNKNOWN_VERSION


def resolve_version() -> str:
    """Return checkout metadata when running from source, else installed metadata."""

    source_version = _source_version()
    if source_version != UNKNOWN_VERSION:
        return source_version
    try:
        return distribution_version(DIST_NAME)
    except PackageNotFoundError:
        return UNKNOWN_VERSION


__version__ = resolve_version()
