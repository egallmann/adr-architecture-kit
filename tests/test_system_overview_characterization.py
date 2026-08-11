"""Phase A observational characterization for System Overview generation.

These tests originally recorded pre-refactor behavior. After the approved
authority lock and Case B realization, they assert the post-lock compatibility
boundaries (kit provider accuracy, ste-runtime isolation, Case B legacy path).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from adr_kit.generators.system_overview_generator import SystemOverviewGenerator
from adr_kit.validators.system_overview_validator import SystemOverviewValidator


def _write_minimal_project(root: Path, project_name: str, *, with_highlights: bool = False) -> None:
    (root / "PROJECT.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: project_metadata",
                "project:",
                f'  name: "{project_name}"',
                '  description: "characterization fixture"',
                '  type: "tool"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    adrs = root / "adrs"
    adrs.mkdir(parents=True, exist_ok=True)
    if with_highlights:
        (adrs / "manifest.yaml").write_text(
            "\n".join(
                [
                    'schema_version: "1.0"',
                    "type: manifest",
                    "adrs:",
                    "  - id: ADR-L-0009",
                    "    type: logical",
                    "    title: Workspace Scope Characterization",
                    "    status: accepted",
                    "    file_path: adrs/logical/ADR-L-0009.yaml",
                    "  - id: ADR-L-0010",
                    "    type: logical",
                    "    title: Bootstrap Characterization",
                    "    status: accepted",
                    "    file_path: adrs/logical/ADR-L-0010.yaml",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        (adrs / "manifest.yaml").write_text(
            'schema_version: "1.0"\ntype: manifest\nadrs: []\n',
            encoding="utf-8",
        )


@pytest.fixture
def chdir_tmp(tmp_path: Path):
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(previous)


def test_characterize_kit_baseline_still_green():
    """Kit overview validates under the post-lock provider-oriented generator."""
    repo_file = Path("SYSTEM-OVERVIEW.md")
    result = SystemOverviewValidator(
        generator=SystemOverviewGenerator(repo_root=Path.cwd())
    ).validate_file(repo_file)
    assert result.is_valid, result.errors


def test_characterize_ste_runtime_current_behavior(chdir_tmp: Path):
    """ste-runtime keeps runtime purpose/highlights without kit provider leak."""
    _write_minimal_project(chdir_tmp, "ste-runtime", with_highlights=True)
    generator = SystemOverviewGenerator(repo_root=chdir_tmp)
    output = chdir_tmp / "SYSTEM-OVERVIEW.md"
    generator.save(output)
    body = output.read_text(encoding="utf-8")
    result = SystemOverviewValidator(generator=generator).validate_file(output)

    assert result.is_valid, result.errors
    assert "project: ste-runtime" in body
    assert "implements STE runtime workflows" in body
    assert "ADR-L-0009" in body
    assert "INV-0014" in body
    assert "## First Discovery Order" not in body
    assert "src/adr_kit/" not in body
    assert "adr_kit.api" not in body


def test_characterize_generic_project_current_behavior(chdir_tmp: Path):
    """Case B: overview-consumer-fixture still emits/validates without kit provider IA."""
    _write_minimal_project(chdir_tmp, "overview-consumer-fixture")
    generator = SystemOverviewGenerator(repo_root=chdir_tmp)
    output = chdir_tmp / "SYSTEM-OVERVIEW.md"
    generator.save(output)
    body = output.read_text(encoding="utf-8")
    result = SystemOverviewValidator(generator=generator).validate_file(output)

    assert result.is_valid, result.errors
    assert output.is_file()
    assert "project: overview-consumer-fixture" in body
    assert "## Compatibility Orientation" in body
    assert "documentation-state toolkit" not in body
    assert "## First Discovery Order" not in body
    assert "src/adr_kit/" not in body
    assert "generator_version: 2" in body
