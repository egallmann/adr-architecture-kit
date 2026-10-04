"""Derived child lifecycle projection follows the declaring ADR status."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from adr_kit.compiler.backend.projection import (
    project_entity,
    project_entity_v2,
    project_entity_v23,
)
from adr_kit.compiler.config import CompilerConfig
from adr_kit.compiler.driver import ArchitectureCompiler
from adr_kit.compiler.ir import IREntity
from adr_kit.models import lifecycle_stage_from_adr_status
from adr_kit.models.architecture_discovery import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    NormalizedEntity,
)
from adr_kit.models.v2_3 import NormativePropositionEntityV23
from adr_kit.parser.yaml_parser import ADRSchemaValidationError
from adr_kit.scope import ProjectScopeResolver

NAMESPACE = "lifecycle-fixture"
LIFECYCLE_BY_STATUS = {
    "proposed": "proposed",
    "accepted": "active",
    "deprecated": "deprecated",
    "superseded": "superseded",
}

LOGICAL_ADR = "01940000-0000-7000-8000-000000000001"
INVARIANT = "01940000-0000-7000-8000-000000000002"
DECISION = "01940000-0000-7000-8000-000000000003"
CAPABILITY = "01940000-0000-7000-8000-000000000004"
PROPOSITION = "01940000-0000-7000-8000-000000000005"
SYSTEM_ADR = "01940000-0000-7000-8000-000000000011"
SYSTEM = "01940000-0000-7000-8000-000000000013"
COMPONENT_ADR = "01940000-0000-7000-8000-000000000021"
COMPONENT = "01940000-0000-7000-8000-000000000023"
INTERFACE = "01940000-0000-7000-8000-000000000024"


def _write(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _write_project(root: Path) -> None:
    _write(
        root / "PROJECT.yaml",
        {
            "schema_version": "1.0",
            "type": "project_metadata",
            "project": {"name": NAMESPACE, "description": "fixture", "type": "library"},
            "ownership": {"team": "architecture"},
            "repository": {"url": "local", "primary_branch": "main"},
            "architecture_documentation": {
                "adr_directory": "adrs/",
                "manifest_path": "adrs/manifest.yaml",
                "architecture_namespace": NAMESPACE,
            },
        },
    )


def _v16_common(adr_id: str, alias_id: str, alias_name: str, status: str) -> dict[str, Any]:
    return {
        "schema_version": "1.6",
        "adr_type": "logical",
        "id": adr_id,
        "alias_id": alias_id,
        "alias_name": alias_name,
        "title": "Lifecycle projection fixture",
        "status": status,
        "created_date": "2026-01-01",
        "authors": ["test.author"],
        "context": "A bounded context.",
    }


def _v16_logical(status: str, *, with_proposition: bool = False) -> dict[str, Any]:
    document = _v16_common(LOGICAL_ADR, "ADR-L-0001", "lifecycle-fixture", status)
    document.update(
        {
            "capabilities": [
                {
                    "id": CAPABILITY,
                    "alias_id": "CAP-0001",
                    "alias_name": "fixture-capability",
                    "name": "Fixture capability",
                    "description": "A capability.",
                }
            ],
            "invariants": [
                {
                    "id": INVARIANT,
                    "alias_id": "INV-0001",
                    "alias_name": "fixture-invariant",
                    "statement": "The fixture MUST stay bounded.",
                    "scope": "compiler",
                    "enforcement_level": "must",
                    "enforcement_mechanism": "test",
                    "verification_method": "automated",
                    "rationale": "Fixture.",
                }
            ],
            "decisions": [
                {
                    "id": DECISION,
                    "alias_id": "DEC-0001",
                    "alias_name": "fixture-decision",
                    "summary": "Use the fixture.",
                    "rationale": "It is reviewable.",
                    "enforces_invariants": [INVARIANT],
                }
            ],
        }
    )
    if with_proposition:
        document["normative_propositions"] = [
            {
                "id": PROPOSITION,
                "alias_id": "NP-0001",
                "alias_name": "retain-evidence",
                "statement": "The contract MUST retain source evidence.",
                "normative_force": "MUST",
                "scope": "compiler",
                "rationale": "The proposition remains reviewable and explicit.",
            }
        ]
    return document


def _v16_physical(status: str) -> tuple[dict[str, Any], dict[str, Any]]:
    stack = [{"category": "language", "name": "Python", "version": "3.12", "rationale": "test"}]
    system_adr = _v16_common(SYSTEM_ADR, "ADR-PS-0001", "fixture-system-adr", status)
    system_adr.update(
        {
            "adr_type": "physical-system",
            "implements_logical": [LOGICAL_ADR],
            "technology_stack": stack,
            "system": {"id": SYSTEM, "alias_id": "SYS-0001", "alias_name": "fixture-system"},
        }
    )
    component_adr = _v16_common(COMPONENT_ADR, "ADR-PC-0001", "fixture-component-adr", status)
    component_adr.update(
        {
            "adr_type": "physical-component",
            "implements_logical": [LOGICAL_ADR],
            "implements_system": [SYSTEM],
            "technology_stack": stack,
            "component_specifications": [
                {
                    "id": COMPONENT,
                    "alias_id": "COMP-0001",
                    "alias_name": "fixture-component",
                    "name": "Fixture component",
                    "type": "worker",
                    "responsibilities": "Does fixture work.",
                    "generation_context": {
                        "purpose": "Testing",
                        "key_responsibilities": ["test"],
                    },
                    "interfaces": [
                        {
                            "id": INTERFACE,
                            "alias_id": "IFACE-0001",
                            "alias_name": "fixture-interface",
                            "type": "CLI",
                            "specification": "A fixture interface.",
                        }
                    ],
                }
            ],
        }
    )
    return system_adr, component_adr


def _legacy_logical(status: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "adr_type": "logical",
        "id": "ADR-L-1000",
        "title": "Legacy lifecycle fixture",
        "status": status,
        "created_date": "2026-01-01",
        "authors": ["test.author"],
        "context": "Legacy fixture.",
        "capabilities": [
            {"id": "CAP-1000", "name": "Legacy capability", "description": "A capability."}
        ],
        "invariants": [
            {
                "id": "INV-1000",
                "statement": "The legacy fixture MUST stay bounded.",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "automated",
                "rationale": "Fixture.",
                "declaration_mode": "local",
            }
        ],
        "decisions": [
            {
                "id": "DEC-1000",
                "summary": "Use the legacy fixture.",
                "rationale": "It is reviewable.",
                "enforces_invariants": ["INV-1000"],
                "enables_capabilities": ["CAP-1000"],
            }
        ],
        "architectural_boundaries": [],
        "interaction_contracts": [],
        "constraints": [],
        "non_functional_requirements": [],
        "gaps": [],
    }


def _compile_registry(root: Path) -> dict[str, dict[str, Any]]:
    scope = ProjectScopeResolver(explicit_scope=root).resolve()
    result = ArchitectureCompiler().compile(
        scope,
        CompilerConfig(
            dry_run=True,
            pinned_timestamp="2026-01-01T00:00:00Z",
            metadata={"validate_contract": "true"},
        ),
    )
    assert result.success, [item.message for item in result.diagnostics.as_list()]
    artifact = next(
        item
        for item in result.artifacts
        if item.path.as_posix() == "adrs/index/entity-registry.yaml"
    )
    registry = yaml.safe_load(artifact.content)
    return {str(entity.get("alias_id") or entity["id"]): entity for entity in registry["entities"]}


@pytest.mark.parametrize("status", list(LIFECYCLE_BY_STATUS))
def test_logical_children_project_declaring_adr_lifecycle(tmp_path: Path, status: str) -> None:
    _write_project(tmp_path)
    _write(tmp_path / "adrs" / "logical" / "ADR-L-0001.yaml", _v16_logical(status))

    entities = _compile_registry(tmp_path)

    expected = LIFECYCLE_BY_STATUS[status]
    assert {
        alias: entities[alias]["lifecycle_stage"]
        for alias in ("ADR-L-0001", "DEC-0001", "INV-0001", "CAP-0001")
    } == dict.fromkeys(("ADR-L-0001", "DEC-0001", "INV-0001", "CAP-0001"), expected)


@pytest.mark.parametrize("status", list(LIFECYCLE_BY_STATUS))
def test_physical_children_project_their_own_declaring_adr_lifecycle(
    tmp_path: Path, status: str
) -> None:
    _write_project(tmp_path)
    _write(tmp_path / "adrs" / "logical" / "ADR-L-0001.yaml", _v16_logical("accepted"))
    system_adr, component_adr = _v16_physical(status)
    _write(tmp_path / "adrs" / "physical-system" / "ADR-PS-0001.yaml", system_adr)
    _write(tmp_path / "adrs" / "physical-component" / "ADR-PC-0001.yaml", component_adr)

    entities = _compile_registry(tmp_path)

    expected = LIFECYCLE_BY_STATUS[status]
    physical = ("ADR-PS-0001", "SYS-0001", "ADR-PC-0001", "COMP-0001", "IFACE-0001")
    assert {alias: entities[alias]["lifecycle_stage"] for alias in physical} == dict.fromkeys(
        physical, expected
    )
    assert entities["DEC-0001"]["lifecycle_stage"] == "active"


def test_legacy_registry_children_project_declaring_adr_lifecycle(tmp_path: Path) -> None:
    _write_project(tmp_path)
    _write(tmp_path / "adrs" / "logical" / "ADR-L-1000.yaml", _legacy_logical("proposed"))

    entities = _compile_registry(tmp_path)

    legacy = ("ADR-L-1000", "DEC-1000", "INV-1000", "CAP-1000")
    assert {item: entities[item]["lifecycle_stage"] for item in legacy} == dict.fromkeys(
        legacy, "proposed"
    )


def test_normative_proposition_remains_lifecycle_free(tmp_path: Path) -> None:
    projected: dict[str, dict[str, Any]] = {}
    for status in ("proposed", "accepted"):
        root = tmp_path / status
        _write_project(root)
        _write(
            root / "adrs" / "logical" / "ADR-L-0001.yaml",
            _v16_logical(status, with_proposition=True),
        )
        projected[status] = _compile_registry(root)["NP-0001"]

    proposition = projected["proposed"]
    semantic_fields = (
        "id",
        "alias_id",
        "alias_name",
        "entity_type",
        "statement",
        "normative_force",
        "scope",
        "rationale",
        "declaring_adr",
        "source_contract",
    )
    assert {field: proposition[field] for field in semantic_fields} == {
        field: projected["accepted"][field] for field in semantic_fields
    }
    assert not {"lifecycle_stage", "status"} & set(proposition)
    assert not {"lifecycle_stage", "status"} & set(proposition["metadata"])
    assert proposition["normative_force"] == "MUST"
    assert proposition["scope"] == "compiler"
    assert proposition["declaring_adr"]["id"] == LOGICAL_ADR
    assert "lifecycle_stage" not in NormativePropositionEntityV23.model_fields


@pytest.mark.parametrize("status", [None, "draft"])
def test_compiler_rejects_missing_or_unknown_adr_status(tmp_path: Path, status: str | None) -> None:
    document = _v16_logical("proposed")
    if status is None:
        del document["status"]
    else:
        document["status"] = status
    _write_project(tmp_path)
    _write(tmp_path / "adrs" / "logical" / "ADR-L-0001.yaml", document)
    scope = ProjectScopeResolver(explicit_scope=tmp_path).resolve()

    with pytest.raises(ADRSchemaValidationError, match="status"):
        ArchitectureCompiler().compile(scope, CompilerConfig(dry_run=True))


def _provenance() -> DiscoveryProvenance:
    return DiscoveryProvenance(
        source_type="logical_adr",
        source_ref=f"{LOGICAL_ADR}#{DECISION}",
        extraction_phase="extract_decision",
        classification="explicit",
        generator="test",
    )


def _canonical() -> CanonicalSource:
    return CanonicalSource(
        source_type="logical_adr",
        source_ref=f"{LOGICAL_ADR}#{DECISION}",
        artifact_path="adrs/logical/ADR-L-0001.yaml",
    )


def _decision_metadata(**extra: Any) -> dict[str, Any]:
    return {
        "adr_id": LOGICAL_ADR,
        "alias_id": "DEC-0001",
        "alias_name": "fixture-decision",
        **extra,
    }


PROJECTORS = {
    "normalized-1.1": lambda entity: project_entity(entity),
    "normalized-2.0": lambda entity: project_entity_v2(entity, None, NAMESPACE),
    "normalized-2.3": lambda entity: project_entity_v23(entity, None, NAMESPACE),
}


@pytest.mark.parametrize("projector", PROJECTORS.values(), ids=PROJECTORS.keys())
def test_projection_rejects_missing_lifecycle(projector) -> None:
    entity = IREntity(
        id=DECISION,
        entity_type="decision",
        name="Use the fixture.",
        summary="It is reviewable.",
        canonical_source=_canonical(),
        metadata=_decision_metadata(),
        provenance=_provenance(),
    )

    with pytest.raises(ValueError, match="Missing ADR status"):
        projector(entity)


@pytest.mark.parametrize("projector", PROJECTORS.values(), ids=PROJECTORS.keys())
def test_projection_rejects_model_default_lifecycle(projector) -> None:
    entity = NormalizedEntity(
        id=DECISION,
        entity_type="decision",
        name="Use the fixture.",
        summary="It is reviewable.",
        canonical_source=_canonical(),
        metadata=_decision_metadata(),
        completeness=Completeness(status="complete"),
        provenance=_provenance(),
    )

    with pytest.raises(ValueError, match="Missing ADR status"):
        projector(entity)


@pytest.mark.parametrize("projector", PROJECTORS.values(), ids=PROJECTORS.keys())
def test_projection_rejects_unknown_status(projector) -> None:
    entity = IREntity(
        id=DECISION,
        entity_type="decision",
        name="Use the fixture.",
        summary="It is reviewable.",
        canonical_source=_canonical(),
        metadata=_decision_metadata(status="draft"),
        provenance=_provenance(),
    )

    with pytest.raises(ValueError, match="Unknown ADR status 'draft'"):
        projector(entity)


@pytest.mark.parametrize(("status", "expected"), list(LIFECYCLE_BY_STATUS.items()))
def test_lifecycle_stage_from_adr_status_maps_supported_statuses(
    status: str, expected: str
) -> None:
    assert lifecycle_stage_from_adr_status(status) == expected
    assert lifecycle_stage_from_adr_status(status.upper()) == expected


@pytest.mark.parametrize("status", [None, ""])
def test_lifecycle_stage_from_adr_status_rejects_missing_status(status: str | None) -> None:
    with pytest.raises(ValueError, match="Missing ADR status"):
        lifecycle_stage_from_adr_status(status)


@pytest.mark.parametrize("status", ["draft", "active", "retired"])
def test_lifecycle_stage_from_adr_status_rejects_unknown_status(status: str) -> None:
    with pytest.raises(ValueError, match=f"Unknown ADR status {status!r}"):
        lifecycle_stage_from_adr_status(status)
