"""Verified kit corpus cutover: current ADR sources are authoring v1.5."""

from __future__ import annotations

from pathlib import Path

import yaml

from adr_kit.parser import ADRParser

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = (
    ROOT / "adrs" / "logical",
    ROOT / "adrs" / "physical-system",
    ROOT / "adrs" / "physical-component",
)


def _current_sources() -> list[Path]:
    paths: list[Path] = []
    for directory in SOURCE_DIRS:
        paths.extend(sorted(directory.glob("ADR-*.yaml")))
    return paths


def test_current_kit_adr_sources_are_authoring_v15() -> None:
    versions = {
        path.as_posix(): yaml.safe_load(path.read_text(encoding="utf-8")).get("schema_version")
        for path in _current_sources()
    }
    unexpected = {path: version for path, version in versions.items() if version != "1.5"}
    assert not unexpected, unexpected


def test_current_kit_adr_sources_parse_as_v15() -> None:
    parser = ADRParser()
    for path in _current_sources():
        parsed = parser.parse_adr(path)
        assert parsed.schema_version == "1.5", path
