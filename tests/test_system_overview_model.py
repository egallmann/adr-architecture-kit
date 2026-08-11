"""Tests for the typed SYSTEM-OVERVIEW semantic model and provider projection."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from adr_kit.api import capabilities
from adr_kit.generators.system_overview_generator import SystemOverviewGenerator
from adr_kit.generators.system_overview_model import (
    SystemOverviewModel,
    SystemOverviewSourceError,
)
from adr_kit.integrity.core import compute_source_hash, parse_integrity_header
from adr_kit.validators.system_overview_validator import SystemOverviewValidator


def _write_minimal_project(root: Path, project_name: str, *, with_highlights: bool = False) -> None:
    (root / "PROJECT.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: project_metadata",
                "project:",
                f'  name: "{project_name}"',
                '  description: "fixture project"',
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


def _kit_section_order(body: str) -> list[str]:
    headings = [
        "## Start Here",
        "## What ADR Kit Is",
        "## Responsibility and Authority Boundaries",
        "## Supported Consumer Surfaces",
        "## Architecture and Artifact Layers",
        "## Provider Capabilities",
        "## How to Enter for Common Tasks",
        "## Authority Anchors",
        "## Safe Extension Rules",
        "## Common Category Errors",
        "## Validation Gates",
        "## Read Next",
        "## One-Line Orientation",
    ]
    return [heading for heading in headings if heading in body]


def test_kit_overview_is_provider_oriented():
    generator = SystemOverviewGenerator(repo_root=Path.cwd())
    model = generator.build_model()
    body = generator.render()

    assert isinstance(model, SystemOverviewModel)
    assert model.profile.profile_kind == "adr-architecture-kit"
    assert model.provider is not None
    assert model.provider.primary_module == "adr_kit.api"
    assert "documentation-state toolkit" not in body
    assert "## First Discovery Order" not in body
    assert "## Start Here" in body
    assert "## Supported Consumer Surfaces" in body
    assert "adr_kit.api" in body
    assert "## What ADR Kit Is" in body
    assert "authoring-side provider" in body.lower() or "adr_kit.api" in body
    assert "Python SDK — primary programmatic boundary" in body
    caps = capabilities()
    assert model.provider.api_contract_version == caps.api_contract_version
    assert model.provider.operations == caps.operations
    assert model.provider.normalized_model_schema_version == caps.normalized_model_schema_version
    for operation in caps.operations:
        assert operation in body
    assert all(anchor.status == "accepted" for anchor in model.authority_anchors)
    assert {anchor.id for anchor in model.authority_anchors} >= {
        "ADR-L-0003",
        "ADR-L-0007",
        "ADR-L-0013",
        "ADR-L-0019",
    }


def test_kit_section_order_puts_provider_before_internal_guidance():
    body = SystemOverviewGenerator(repo_root=Path.cwd()).render()
    order = _kit_section_order(body)
    assert order[0] == "## Start Here"
    assert order[-1] == "## One-Line Orientation"
    assert order.index("## Supported Consumer Surfaces") < order.index(
        "## How to Enter for Common Tasks"
    )
    assert "Internal surfaces" in body
    assert body.index("Python SDK — primary programmatic boundary") < body.index(
        "Internal surfaces"
    )
    assert "exhaustive" not in body.lower()


def test_provider_consistency_guard_uses_current_owning_declarations():
    generator = SystemOverviewGenerator(repo_root=Path.cwd())
    model = generator.build_model()
    from adr_kit.models.normalized_architecture_model import NormalizedArchitectureModel
    import adr_kit.api as api_module

    caps = capabilities()
    assert (
        model.provider.normalized_model_schema_version
        == NormalizedArchitectureModel.model_fields["schema_version"].default
    )
    assert set(model.provider.operations).issubset(set(api_module.__all__))
    assert model.provider.supported_adr_schema_versions == caps.supported_adr_schema_versions


def test_provider_consistency_fails_closed_on_contradiction():
    from dataclasses import replace

    real = capabilities()

    def bad_caps():
        return replace(real, normalized_model_schema_version="__contradictory__")

    generator = SystemOverviewGenerator(
        repo_root=Path.cwd(),
        capabilities_provider=bad_caps,
    )
    with pytest.raises(SystemOverviewSourceError, match="normalized_model_schema_version"):
        generator.build_model()


def test_projection_source_closure_sensitivity(tmp_path: Path):
    from adr_kit.integrity import HashInput

    generator = SystemOverviewGenerator(repo_root=Path.cwd())
    model = generator.build_model()
    output = tmp_path / "SYSTEM-OVERVIEW.md"
    base_inputs = generator.declared_source_inputs(output)
    base_hash = compute_source_hash(Path.cwd(), base_inputs, generator.generator_identity)

    # Template change alters projection-rule basis.
    mutated = []
    for item in base_inputs:
        label = getattr(item, "label", None)
        content = getattr(item, "content", None)
        if label and label.endswith("system-overview.md.jinja2"):
            mutated.append(HashInput(label, content + b"\n<!-- mutated -->\n"))
        else:
            mutated.append(item)
    assert compute_source_hash(Path.cwd(), mutated, generator.generator_identity) != base_hash

    # Semantic model change alters semantic basis.
    semantic_mutated = []
    for item in base_inputs:
        label = getattr(item, "label", None)
        content = getattr(item, "content", None)
        if label == "__semantic__/system-overview-model.json":
            semantic_mutated.append(HashInput(label, content + b" "))
        else:
            semantic_mutated.append(item)
    assert (
        compute_source_hash(Path.cwd(), semantic_mutated, generator.generator_identity) != base_hash
    )

    # Unrelated on-disk file mutation does not change declared source basis.
    readme = Path.cwd() / "README.md"
    original = readme.read_bytes()
    try:
        readme.write_bytes(original + b"\n# unrelated\n")
        regenerator = SystemOverviewGenerator(repo_root=Path.cwd())
        regenerator.build_model()
        refreshed = regenerator.declared_source_inputs(output)
        assert (
            compute_source_hash(Path.cwd(), refreshed, regenerator.generator_identity) == base_hash
        )
    finally:
        readme.write_bytes(original)

    assert model.to_canonical_json()


def test_generator_identity_is_v2():
    generator = SystemOverviewGenerator(repo_root=Path.cwd())
    assert generator.generator_identity.generator_id == "adr-system-overview"
    assert generator.generator_identity.generator_version == 2


def test_ste_runtime_profile_has_no_provider_leak(chdir_tmp: Path):
    _write_minimal_project(chdir_tmp, "ste-runtime", with_highlights=True)
    generator = SystemOverviewGenerator(repo_root=chdir_tmp)
    output = chdir_tmp / "SYSTEM-OVERVIEW.md"
    generator.save(output)
    body = output.read_text(encoding="utf-8")
    result = SystemOverviewValidator(generator=generator).validate_file(output)

    assert result.is_valid, result.errors
    assert "implements STE runtime workflows" in body
    assert "ADR-L-0009" in body
    assert "INV-0014" in body
    assert "adr_kit.api" not in body
    assert "## First Discovery Order" not in body
    assert "src/adr_kit/" not in body
    assert "## Supported Consumer Surfaces" not in body
    assert "generator_version: 2" in body


def test_case_b_legacy_generic_preserves_success_without_provider_ia(chdir_tmp: Path):
    _write_minimal_project(chdir_tmp, "overview-consumer-fixture")
    generator = SystemOverviewGenerator(repo_root=chdir_tmp)
    output = chdir_tmp / "SYSTEM-OVERVIEW.md"
    generator.save(output)
    body = output.read_text(encoding="utf-8")
    result = SystemOverviewValidator(generator=generator).validate_file(output)

    assert result.is_valid, result.errors
    assert "project: overview-consumer-fixture" in body
    assert "## Compatibility Orientation" in body
    assert "documentation-state toolkit" not in body
    assert "## First Discovery Order" not in body
    assert "adr_kit.api" not in body
    assert "src/adr_kit/" not in body
    assert "## Supported Consumer Surfaces" not in body
    header = parse_integrity_header(body)
    assert header["generator_version"] == "2"


def test_profiles_are_packaged_as_template_data():
    from importlib import resources

    templates = resources.files("adr_kit.templates")
    assert templates.joinpath("system-overview-adr-architecture-kit.yaml").is_file()
    assert templates.joinpath("system-overview-ste-runtime.yaml").is_file()
    assert templates.joinpath("system-overview.md.jinja2").is_file()
