"""Compiler/projector coverage for homogeneous authoring v1.6 corpora."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from adr_kit.compiler.config import CompilerConfig
from adr_kit.compiler.driver import ArchitectureCompiler
from adr_kit.compiler.pipeline import MixedSchemaVersionError, VersionDetectionPass
from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.models.v2_3 import NormalizedEntityRegistryV23
from adr_kit.scope import ProjectScopeResolver


def _project() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "type": "project_metadata",
        "project": {"name": "v16-fixture", "description": "compiler fixture", "type": "library"},
        "ownership": {"team": "architecture"},
        "repository": {"url": "local", "primary_branch": "main"},
        "architecture_documentation": {
            "adr_directory": "adrs/",
            "manifest_path": "adrs/manifest.yaml",
            "architecture_namespace": "v16-fixture",
        },
    }


def _logical(adr_id: str, alias_id: str, np_id: str, np_alias: str) -> dict[str, object]:
    return {
        "schema_version": "1.6",
        "adr_type": "logical",
        "id": adr_id,
        "alias_id": alias_id,
        "alias_name": "governed-boundary",
        "title": "A governed architecture boundary",
        "status": "accepted",
        "created_date": "2026-01-01",
        "authors": ["test.author"],
        "context": "A bounded context.",
        "decisions": [
            {
                "id": "01940000-0000-7000-8000-000000000003",
                "alias_id": "DEC-0001",
                "alias_name": "choose-boundary",
                "summary": "Use the governed boundary.",
                "rationale": "It is reviewable.",
            }
        ],
        "normative_propositions": [
            {
                "id": np_id,
                "alias_id": np_alias,
                "alias_name": "retain-evidence",
                "statement": "The contract MUST retain source evidence.",
                "normative_force": "MUST",
                "scope": "compiler",
            }
        ],
    }


def _write_scope(root: Path) -> None:
    (root / "adrs" / "logical").mkdir(parents=True)
    (root / "adrs" / "physical-system").mkdir(parents=True)
    (root / "adrs" / "physical-component").mkdir(parents=True)
    (root / "PROJECT.yaml").write_text(
        yaml.safe_dump(_project(), sort_keys=False), encoding="utf-8"
    )
    (root / "adrs" / "logical" / "ADR-L-0001.yaml").write_text(
        yaml.safe_dump(
            _logical(
                "01940000-0000-7000-8000-000000000001",
                "ADR-L-0001",
                "01940000-0000-7000-8000-000000000002",
                "NP-0001",
            ),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    physical_system = _logical(
        "01940000-0000-7000-8000-000000000011",
        "ADR-PS-0001",
        "01940000-0000-7000-8000-000000000012",
        "NP-0002",
    )
    physical_system.update(
        {
            "adr_type": "physical-system",
            "implements_logical": ["01940000-0000-7000-8000-000000000001"],
            "technology_stack": [
                {
                    "category": "language",
                    "name": "Python",
                    "version": "3.12",
                    "rationale": "test",
                }
            ],
            "system": {
                "id": "01940000-0000-7000-8000-000000000013",
                "alias_id": "SYS-0001",
                "alias_name": "test-system",
            },
        }
    )
    (root / "adrs" / "physical-system" / "ADR-PS-0001.yaml").write_text(
        yaml.safe_dump(physical_system, sort_keys=False), encoding="utf-8"
    )
    physical_component = _logical(
        "01940000-0000-7000-8000-000000000021",
        "ADR-PC-0001",
        "01940000-0000-7000-8000-000000000022",
        "NP-0003",
    )
    physical_component.update(
        {
            "adr_type": "physical-component",
            "implements_logical": ["01940000-0000-7000-8000-000000000001"],
            "implements_system": ["01940000-0000-7000-8000-000000000013"],
            "technology_stack": [
                {
                    "category": "language",
                    "name": "Python",
                    "version": "3.12",
                    "rationale": "test",
                }
            ],
            "component_specifications": [
                {
                    "id": "01940000-0000-7000-8000-000000000023",
                    "alias_id": "COMP-0001",
                    "alias_name": "test-component",
                    "name": "Test component",
                    "type": "worker",
                    "responsibilities": "Does test work.",
                    "generation_context": {
                        "purpose": "Testing",
                        "key_responsibilities": ["test"],
                    },
                    "interfaces": [
                        {
                            "id": "01940000-0000-7000-8000-000000000024",
                            "alias_id": "IFACE-0001",
                            "alias_name": "test-interface",
                            "type": "CLI",
                            "specification": "A test interface.",
                        }
                    ],
                }
            ],
        }
    )
    (root / "adrs" / "physical-component" / "ADR-PC-0001.yaml").write_text(
        yaml.safe_dump(physical_component, sort_keys=False), encoding="utf-8"
    )


def _compile(root: Path):
    scope = ProjectScopeResolver(explicit_scope=root).resolve()
    return ArchitectureCompiler().compile(
        scope,
        CompilerConfig(
            dry_run=True,
            pinned_timestamp="2026-01-01T00:00:00Z",
            metadata={"validate_contract": "true"},
        ),
    )


def test_homogeneous_v16_compiles_np_to_lifecycle_free_v23(tmp_path: Path) -> None:
    _write_scope(tmp_path)

    first = _compile(tmp_path)
    second = _compile(tmp_path)

    assert first.success, [item.message for item in first.diagnostics.as_list()]
    assert {item.path: item.content for item in first.artifacts} == {
        item.path: item.content for item in second.artifacts
    }
    assert first.model.entities.by_type("normative_proposition")

    entity_artifact = next(
        item
        for item in first.artifacts
        if item.path.as_posix() == "adrs/index/entity-registry.yaml"
    )
    registry = NormalizedEntityRegistryV23.model_validate(yaml.safe_load(entity_artifact.content))
    propositions = [
        item for item in registry.entities if item.entity_type == "normative_proposition"
    ]
    assert {item.alias_id for item in propositions} == {"NP-0001", "NP-0002", "NP-0003"}
    assert {item.canonical_source.source_type for item in propositions} == {
        "logical_adr",
        "physical_system_adr",
        "physical_component_adr",
    }
    for proposition in propositions:
        assert proposition.statement.endswith("evidence.")
        assert proposition.source_contract.family == "authoring"
        assert proposition.source_contract.version == "1.6"
        assert "lifecycle_stage" not in proposition.model_dump()

    paths = {item.path.as_posix() for item in first.artifacts}
    assert "adrs/manifest.yaml" in paths
    assert any(path.endswith(".md") for path in paths)

    public_result = compile_architecture(
        CompilationRequest(project_root=tmp_path, timestamp="2026-01-01T00:00:00Z")
    )
    assert public_result.success
    assert public_result.model is not None
    assert public_result.model.schema_version == "2.3"


@pytest.mark.parametrize("versions", [("1.5", "1.6"), ("1.4", "1.6")])
def test_mixed_authoring_versions_remain_rejected(versions: tuple[str, str]) -> None:
    state = type("State", (), {"detected_schema_versions": set(versions), "model_version": "1.1"})()
    with pytest.raises(MixedSchemaVersionError):
        VersionDetectionPass().run(state)
