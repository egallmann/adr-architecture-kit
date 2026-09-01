"""v2.2 runtime plumbing: public getters, SDK compile result, frozen RelationshipType."""

from __future__ import annotations

from pathlib import Path

import pytest

from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.compiler.backend.projection import project_relationship, project_relationship_v22
from adr_kit.compiler.ir.rel_graph import IRRelationship
from adr_kit.models.v2_0.relationship_record import RelationshipRecordV2
from adr_kit.models.v2_2 import NormalizedArchitectureModelV22
from adr_kit.repository._normalized_bundle import load_normalized_bundle_from_bytes
from adr_kit.repository import ArchitectureRegistryError

ROOT = Path(__file__).resolve().parents[1]
UUID_A = "018f4f20-0000-7000-8000-000000000001"
UUID_B = "018f4f20-0000-7000-8000-000000000002"
OWNER = "018f4f20-0000-7000-8000-000000000003"


def test_depends_on_is_projected_through_normalized_contracts() -> None:
    ir = IRRelationship(
        relationship_type="depends_on",
        from_entity_id=UUID_A,
        to_entity_id=UUID_B,
        canonical_source_ref=OWNER,
        provenance_classification="explicit",
        source_owner_id=OWNER,
        source_pointer="/component_topology/relationships/0",
        record_kind="compatibility",
    )
    projected_v11 = project_relationship(ir)
    assert projected_v11.relationship_type == "depends_on"
    projected_v20 = RelationshipRecordV2(
        relationship_id="depends_on:a:b",
        assertion_id="asrt-" + "0" * 64,
        relationship_type="depends_on",  # type: ignore[arg-type]
        from_entity_id=UUID_A,
        to_entity_id=UUID_B,
        source_owner_id=OWNER,
        provenance_classification="explicit",
        canonical_source_ref=OWNER,
    )
    assert projected_v20.relationship_type == "depends_on"
    projected = project_relationship_v22(ir)
    assert projected is not None
    assert projected.relationship_type == "depends_on"
    assert projected.record_kind == "compatibility"


def test_kit_compile_returns_detached_v22_and_getters_fail_closed() -> None:
    result = compile_architecture(
        CompilationRequest(project_root=ROOT, artifact_groups=("registries",), write=False)
    )
    assert result.success, result.diagnostics
    assert isinstance(result.model, NormalizedArchitectureModelV22)
    assert result.model.schema_version == "2.2"
    assert result.model.__class__.__module__.startswith("adr_kit.models")
    types = {type(item).__name__ for item in (result.model.entities + result.model.relationships)}
    assert "ArchModel" not in types
    assert "IRRelationship" not in types

    repo_model = None
    try:
        from adr_kit.api import open_repository

        repo = open_repository(ROOT)
        if repo.model_version == "2.2":
            loaded = repo.get_model_v22()
            assert loaded.schema_version == "2.2"
            assert result.fingerprint == repo.fingerprint()
            with pytest.raises(ArchitectureRegistryError, match="use get_model_v22"):
                repo.get_model()
            with pytest.raises(ArchitectureRegistryError, match="2.0 unavailable"):
                repo.get_model_v2()
            with pytest.raises(ArchitectureRegistryError, match="2.1 unavailable"):
                repo.get_model_v21()
            repo_model = loaded
    except ArchitectureRegistryError:
        repo_model = None

    emitted = {item.relative_path: item.content for item in result.artifacts}
    bundle = load_normalized_bundle_from_bytes(ROOT, emitted)
    assert isinstance(bundle.model, NormalizedArchitectureModelV22)
    loaded = repo_model or bundle.model
    assert not any(entity.id.startswith("TOPO-") for entity in loaded.entities)
    depends = [
        rel
        for rel in loaded.relationships
        if getattr(rel, "relationship_type", None) == "depends_on"
    ]
    assert depends
    composed = [
        rel
        for rel in loaded.relationships
        if getattr(rel, "relationship_type", None) == "composed_of"
    ]
    assert composed
    entity_ids = {entity.id for entity in loaded.entities}
    entity_types = {entity.id: entity.entity_type for entity in loaded.entities}
    for rel in composed:
        assert entity_types[rel.from_entity_id] == "system"
        assert entity_types[rel.to_entity_id] == "component"
        assert rel.to_entity_id in entity_ids
        assert not rel.to_entity_id.startswith("TOPO-")
    assert not any(
        getattr(rel, "relationship_type", None) == "consumes_interface"
        for rel in loaded.relationships
    )
