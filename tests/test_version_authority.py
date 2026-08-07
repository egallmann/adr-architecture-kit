"""Executable contracts for metadata-first package-version authority."""

from __future__ import annotations

import re
from importlib import import_module, metadata
from pathlib import Path
from types import ModuleType

import pytest
from click.testing import CliRunner

import adr_kit
from adr_kit.cli.main import cli

ROOT = Path(__file__).resolve().parents[1]


def _version_module() -> ModuleType:
    return import_module("adr_kit._version")


def test_runtime_version_has_no_duplicate_literal() -> None:
    source = (ROOT / "src" / "adr_kit" / "__init__.py").read_text(encoding="utf-8")

    assert not re.search(r"__version__\s*=\s*['\"]\d", source)
    assert "from ._version import __version__" in source


def test_direct_source_fallback_reads_pyproject(monkeypatch: pytest.MonkeyPatch) -> None:
    version_module = _version_module()

    def missing_metadata(_distribution: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(version_module, "distribution_version", missing_metadata)
    monkeypatch.setattr(version_module, "SOURCE_PROJECT", ROOT / "pyproject.toml")

    assert version_module.resolve_version() == "0.1.0"


def test_editable_install_uses_distribution_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    version_module = _version_module()
    expected = metadata.version("adr-architecture-kit")

    def forbidden_fallback() -> str:
        raise AssertionError("source fallback must not run when metadata exists")

    monkeypatch.setattr(version_module, "_source_version", forbidden_fallback)

    assert version_module.resolve_version() == expected


def test_cli_runtime_and_capability_versions_match() -> None:
    api = import_module("adr_kit.api")
    cli_result = CliRunner().invoke(cli, ["--version"])

    assert cli_result.exit_code == 0, cli_result.output
    cli_version = cli_result.output.strip().rsplit(" ", 1)[-1]
    assert adr_kit.__version__ == metadata.version("adr-architecture-kit")
    assert cli_version == adr_kit.__version__
    assert api.capabilities().package_version == adr_kit.__version__


def test_missing_metadata_and_source_returns_unknown_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version_module = _version_module()

    def missing_metadata(_distribution: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(version_module, "distribution_version", missing_metadata)
    monkeypatch.setattr(version_module, "SOURCE_PROJECT", tmp_path / "missing.toml")

    assert version_module.resolve_version() == "0+unknown"
