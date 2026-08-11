"""R5 — model 2.0 boundary tests.

Verifies structurally distinct v2.0 schemas/classes, 1.1 readability,
required UUID/alias/type/URI/time/fingerprint fields.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from adr_kit.identity import (
    derive_alias_ref,
    derive_entity_uri,
    entity_fingerprint,
    uuidv7_created_at,
    validate_uuidv7,
)
from adr_kit.models.architecture_discovery import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    NormalizedEntity,
    RelationshipRecord,
)
from adr_kit.models.normalized_architecture_model import NormalizedArchitectureModel
from adr_kit.models.v2_0 import (
    NormalizedArchitectureModelV2,
    NormalizedEntityRegistryV2,
    NormalizedEntityV2,
    RelationshipRecordV2,
    RelationshipRegistryV2,
    UnresolvedRegistryV2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "adr-architecture-kit"

UUID_A = "019109a0-b1c2-7def-8a00-112233445566"
UUID_B = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
UUID_C = "019109a0-d5e6-7f78-8c00-aabb00112233"


def _make_provenance() -> DiscoveryProvenance:
    return DiscoveryProvenance(
        source_type="test",
        source_ref="test",
        extraction_phase="test",
        classification="explicit",
        generator="test",
    )


def _make_canonical() -> CanonicalSource:
    return CanonicalSource(source_type="test", source_ref="test", artifact_path="test.yaml")


class TestNormalizedEntityV2StructuralDistinction:
    """Model 2.0 entities require UUID identity fields absent in 1.1."""

    def test_v2_entity_requires_uuid_id(self) -> None:
        with pytest.raises(ValidationError, match="id"):
            NormalizedEntityV2(
                id="ADR-L-0001",
                alias_id="ADR-L-0001",
                alias_name="test-adr",
                alias_ref="ADR-L-0001:test-adr",
                entity_type="adr",
                name="Test",
                summary="Test",
                uri=f"adr://{NAMESPACE}/entities/{UUID_A}",
                created_at="2026-01-01T00:00:00.000Z",
                entity_fingerprint="sha256:" + "a" * 64,
                canonical_source=_make_canonical(),
                completeness=Completeness(status="complete"),
                provenance=_make_provenance(),
            )

    def test_v2_entity_accepts_valid_uuid(self) -> None:
        fp_record = {
            "id": UUID_A,
            "alias_id": "ADR-L-9990",
            "alias_name": "test-adr",
            "entity_type": "adr",
            "name": "Test ADR",
        }
        entity = NormalizedEntityV2(
            id=UUID_A,
            alias_id="ADR-L-9990",
            alias_name="test-adr",
            alias_ref=derive_alias_ref("ADR-L-9990", "test-adr"),
            entity_type="adr",
            name="Test ADR",
            summary="Test summary",
            uri=derive_entity_uri(NAMESPACE, UUID_A),
            created_at=uuidv7_created_at(UUID_A),
            entity_fingerprint=entity_fingerprint(fp_record),
            canonical_source=_make_canonical(),
            completeness=Completeness(status="complete"),
            provenance=_make_provenance(),
        )
        assert validate_uuidv7(entity.id) == UUID_A
        assert entity.alias_ref == "ADR-L-9990:test-adr"
        assert entity.uri.startswith("adr://")

    def test_v2_entity_requires_valid_uri(self) -> None:
        with pytest.raises(ValidationError, match="uri"):
            NormalizedEntityV2(
                id=UUID_A,
                alias_id="ADR-L-9990",
                alias_name="test-adr",
                alias_ref="ADR-L-9990:test-adr",
                entity_type="adr",
                name="Test",
                summary="Test",
                uri="http://wrong-scheme/test",
                created_at="2026-01-01T00:00:00.000Z",
                entity_fingerprint="sha256:" + "a" * 64,
                canonical_source=_make_canonical(),
                completeness=Completeness(status="complete"),
                provenance=_make_provenance(),
            )

    def test_v2_entity_requires_fingerprint(self) -> None:
        with pytest.raises(ValidationError, match="entity_fingerprint"):
            NormalizedEntityV2(
                id=UUID_A,
                alias_id="ADR-L-9990",
                alias_name="test-adr",
                alias_ref="ADR-L-9990:test-adr",
                entity_type="adr",
                name="Test",
                summary="Test",
                uri=derive_entity_uri(NAMESPACE, UUID_A),
                created_at="2026-01-01T00:00:00.000Z",
                entity_fingerprint="invalid",
                canonical_source=_make_canonical(),
                completeness=Completeness(status="complete"),
                provenance=_make_provenance(),
            )

    def test_v1_entity_does_not_require_uuid(self) -> None:
        entity = NormalizedEntity(
            id="ADR-L-0001",
            entity_type="adr",
            name="Test",
            summary="Test",
            canonical_source=_make_canonical(),
            completeness=Completeness(status="complete"),
            provenance=_make_provenance(),
        )
        assert entity.id == "ADR-L-0001"

    def test_v2_from_identity_fields(self) -> None:
        entity = NormalizedEntityV2.from_identity_fields(
            uuid=UUID_A,
            alias_id="ADR-L-9990",
            alias_name="test-adr",
            entity_type="adr",
            name="Test ADR",
            summary="Test",
            architecture_namespace=NAMESPACE,
            canonical_source=_make_canonical(),
        )
        assert entity.id == UUID_A
        assert entity.alias_ref == "ADR-L-9990:test-adr"
        assert entity.uri == derive_entity_uri(NAMESPACE, UUID_A)
        assert entity.created_at == uuidv7_created_at(UUID_A)
        assert entity.entity_fingerprint.startswith("sha256:")


class TestRelationshipRecordV2:
    """v2.0 relationships require UUID endpoints and source_owner_id."""

    def test_v2_relationship_requires_uuid_endpoints(self) -> None:
        with pytest.raises(ValidationError, match="from_entity_id"):
            RelationshipRecordV2(
                relationship_id="enforces:ADR-L-0001:INV-0001",
                assertion_id="asrt-" + "a" * 64,
                relationship_type="enforces",
                from_entity_id="ADR-L-0001",
                to_entity_id="INV-0001",
                source_owner_id=UUID_A,
                provenance_classification="explicit",
                canonical_source_ref="test",
            )

    def test_v2_relationship_requires_source_owner(self) -> None:
        with pytest.raises(ValidationError, match="source_owner_id"):
            RelationshipRecordV2(
                relationship_id=f"enforces:{UUID_A}:{UUID_B}",
                assertion_id="asrt-" + "a" * 64,
                relationship_type="enforces",
                from_entity_id=UUID_A,
                to_entity_id=UUID_B,
                source_owner_id="ADR-L-0001",
                provenance_classification="explicit",
                canonical_source_ref="test",
            )

    def test_v2_relationship_from_uuids(self) -> None:
        rel = RelationshipRecordV2.from_uuids(
            relationship_type="enforces",
            source_uuid=UUID_A,
            target_uuid=UUID_B,
            source_owner_uuid=UUID_C,
            canonical_source_ref="test",
        )
        assert rel.relationship_id == f"enforces:{UUID_A}:{UUID_B}"
        assert rel.source_owner_id == UUID_C
        assert rel.assertion_id.startswith("asrt-")
        assert validate_uuidv7(rel.from_entity_id)
        assert validate_uuidv7(rel.to_entity_id)

    def test_v1_relationship_does_not_require_owner(self) -> None:
        rel = RelationshipRecord(
            relationship_id="enforces:DEC-0001:INV-0001",
            relationship_type="enforces",
            from_entity_id="DEC-0001",
            to_entity_id="INV-0001",
            provenance_classification="explicit",
            canonical_source_ref="test",
        )
        assert rel.from_entity_id == "DEC-0001"


class TestNormalizedArchitectureModelV2:
    """Model 2.0 top-level model is structurally distinct from 1.1."""

    def test_v2_model_schema_version(self) -> None:
        model = NormalizedArchitectureModelV2(
            mode="normalized",
            scope_root="/test",
            fingerprint="test",
        )
        assert model.schema_version == "2.0"

    def test_v1_model_schema_version(self) -> None:
        model = NormalizedArchitectureModel(
            mode="normalized",
            scope_root="/test",
            fingerprint="test",
        )
        assert model.schema_version == "1.1"

    def test_v2_model_entities_are_v2_type(self) -> None:
        entity = NormalizedEntityV2.from_identity_fields(
            uuid=UUID_A,
            alias_id="ADR-L-9990",
            alias_name="test-adr",
            entity_type="adr",
            name="Test",
            summary="Test",
            architecture_namespace=NAMESPACE,
            canonical_source=_make_canonical(),
        )
        model = NormalizedArchitectureModelV2(
            mode="normalized",
            scope_root="/test",
            fingerprint="test",
            entities=[entity],
        )
        assert len(model.entities) == 1
        assert isinstance(model.entities[0], NormalizedEntityV2)
        assert model.entities[0].uri.startswith("adr://")

    def test_v2_model_find_entity_by_uuid(self) -> None:
        entity = NormalizedEntityV2.from_identity_fields(
            uuid=UUID_A,
            alias_id="ADR-L-9990",
            alias_name="test-adr",
            entity_type="adr",
            name="Test",
            summary="Test",
            architecture_namespace=NAMESPACE,
            canonical_source=_make_canonical(),
        )
        model = NormalizedArchitectureModelV2(
            mode="normalized",
            scope_root="/test",
            fingerprint="test",
            entities=[entity],
        )
        assert model.find_entity(UUID_A) is not None
        assert model.find_entity_by_alias_id("ADR-L-9990") is not None
        assert model.find_entity("nonexistent") is None


class TestRegistriesV2:
    """v2.0 registries carry schema_version 2.0."""

    def test_entity_registry_v2(self) -> None:
        reg = NormalizedEntityRegistryV2()
        assert reg.schema_version == "2.0"
        assert reg.type == "normalized_entity_registry"

    def test_relationship_registry_v2(self) -> None:
        reg = RelationshipRegistryV2()
        assert reg.schema_version == "2.0"
        assert reg.type == "relationship_registry"

    def test_unresolved_registry_v2(self) -> None:
        reg = UnresolvedRegistryV2()
        assert reg.schema_version == "2.0"


class TestSchemaV2Parity:
    """Canonical schema/v2.0 JSON matches the bundled package mirror."""

    def test_v2_schemas_exist(self) -> None:
        canonical = REPO_ROOT / "schema" / "v2.0"
        bundled = REPO_ROOT / "src" / "adr_kit" / "schema" / "v2_0"
        for schema_file in sorted(canonical.glob("*.json")):
            mirror = bundled / schema_file.name
            assert mirror.exists(), f"Missing package mirror: {mirror}"
            canonical_data = json.loads(schema_file.read_text())
            mirror_data = json.loads(mirror.read_text())
            assert canonical_data == mirror_data, f"Drift: {schema_file.name}"

    def test_v2_normalized_entity_schema_requires_uuid(self) -> None:
        schema_path = REPO_ROOT / "schema" / "v2.0" / "normalized-entity.schema.json"
        schema = json.loads(schema_path.read_text())
        assert "id" in schema["required"]
        assert "uri" in schema["required"]
        assert "entity_fingerprint" in schema["required"]
        assert "created_at" in schema["required"]
        assert schema["properties"]["id"]["pattern"].startswith("^[0-9a-f]")

    def test_v2_relationship_schema_requires_owner(self) -> None:
        schema_path = REPO_ROOT / "schema" / "v2.0" / "relationship-record.schema.json"
        schema = json.loads(schema_path.read_text())
        assert "source_owner_id" in schema["required"]
        assert "from_entity_id" in schema["required"]


class TestNonAdmittedTopology:
    """Non-admitted topology records do not receive UUID identity fields."""

    def test_v2_entity_rejects_non_admitted_type(self) -> None:
        with pytest.raises(ValidationError, match="entity_type"):
            NormalizedEntityV2(
                id=UUID_A,
                alias_id="TOPO-0001",
                alias_name="topology-component",
                alias_ref="TOPO-0001:topology-component",
                entity_type="topology",
                name="Topology",
                summary="Topology",
                uri=derive_entity_uri(NAMESPACE, UUID_A),
                created_at=uuidv7_created_at(UUID_A),
                entity_fingerprint="sha256:" + "a" * 64,
                canonical_source=_make_canonical(),
                completeness=Completeness(status="complete"),
                provenance=_make_provenance(),
            )
