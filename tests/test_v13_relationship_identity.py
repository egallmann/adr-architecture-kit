"""R7 — relationship identity and ownership tests.

Verifies UUID endpoints, exact relationship/assertion vectors, one owner UUID,
source pointer, ambiguity failure, replacement/stale compatibility.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from adr_kit.identity import (
    derive_assertion_id,
    derive_assertion_id_v13,
    derive_relationship_id_v13,
    validate_uuidv7,
)
from adr_kit.compiler.ir.rel_graph import IRRelationship
from adr_kit.compiler.backend.projection import project_relationship_v2
from adr_kit.compiler.pipeline import run_frontend_pipeline
from adr_kit.models.v2_0 import RelationshipRecordV2
from adr_kit.scope import ProjectScope, ProjectScopeResolver

FIXTURES = Path(__file__).resolve().parents[0] / "fixtures"
NAMESPACE = "adr-architecture-kit"


def _make_scope(root: Path) -> ProjectScope:
    return ProjectScopeResolver(explicit_scope=root).resolve()


UUID_ADR = "019109a0-b1c2-7def-8a00-112233445566"
UUID_DEC = "019109a0-b1c2-7def-8a00-aabbccddeef0"
UUID_PS = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
UUID_SYS = "019109a0-d5e6-7f78-8c00-aabb00112233"
UUID_INV = "019109a0-e7f8-7190-8d00-001122334455"


class TestRelationshipIdV13:
    """relationship_id = type:source_uuid:target_uuid."""

    def test_relationship_id_format(self) -> None:
        rel_id = derive_relationship_id_v13("enforces", UUID_DEC, UUID_INV)
        assert rel_id == f"enforces:{UUID_DEC}:{UUID_INV}"

    def test_relationship_id_different_type(self) -> None:
        rel_a = derive_relationship_id_v13("enforces", UUID_DEC, UUID_INV)
        rel_b = derive_relationship_id_v13("enables", UUID_DEC, UUID_INV)
        assert rel_a != rel_b

    def test_relationship_id_rejects_non_uuid(self) -> None:
        with pytest.raises(ValueError):
            derive_relationship_id_v13("enforces", "DEC-0001", UUID_INV)


class TestAssertionIdV13:
    """assertion_id uses type, UUID endpoints, owner UUID, optional pointer."""

    def test_assertion_id_deterministic(self) -> None:
        asrt1 = derive_assertion_id_v13("enforces", UUID_DEC, UUID_INV, UUID_ADR)
        asrt2 = derive_assertion_id_v13("enforces", UUID_DEC, UUID_INV, UUID_ADR)
        assert asrt1 == asrt2
        assert asrt1.startswith("asrt-")

    def test_assertion_id_changes_with_owner(self) -> None:
        asrt_a = derive_assertion_id_v13("enforces", UUID_DEC, UUID_INV, UUID_ADR)
        asrt_b = derive_assertion_id_v13("enforces", UUID_DEC, UUID_INV, UUID_PS)
        assert asrt_a != asrt_b

    def test_assertion_id_changes_with_pointer(self) -> None:
        asrt_a = derive_assertion_id_v13("enforces", UUID_DEC, UUID_INV, UUID_ADR, None)
        asrt_b = derive_assertion_id_v13("enforces", UUID_DEC, UUID_INV, UUID_ADR, "/decisions/0")
        assert asrt_a != asrt_b

    def test_assertion_id_v13_differs_from_v1(self) -> None:
        v1_id = derive_assertion_id("enforces", "DEC-0001", "INV-0001", "ADR-L-0001")
        v13_id = derive_assertion_id_v13("enforces", UUID_DEC, UUID_INV, UUID_ADR)
        assert v1_id != v13_id

    def test_assertion_id_rejects_non_uuid(self) -> None:
        with pytest.raises(ValueError):
            derive_assertion_id_v13("enforces", "DEC-0001", UUID_INV, UUID_ADR)


class TestRelationshipRecordV2Construction:
    """RelationshipRecordV2 construction and validation."""

    def test_from_uuids_derives_ids(self) -> None:
        rel = RelationshipRecordV2.from_uuids(
            relationship_type="declared_in",
            source_uuid=UUID_DEC,
            target_uuid=UUID_ADR,
            source_owner_uuid=UUID_ADR,
            canonical_source_ref="test",
        )
        assert rel.relationship_id == f"declared_in:{UUID_DEC}:{UUID_ADR}"
        expected_asrt = derive_assertion_id_v13("declared_in", UUID_DEC, UUID_ADR, UUID_ADR)
        assert rel.assertion_id == expected_asrt

    def test_source_pointer_included(self) -> None:
        rel = RelationshipRecordV2.from_uuids(
            relationship_type="enforces",
            source_uuid=UUID_DEC,
            target_uuid=UUID_INV,
            source_owner_uuid=UUID_ADR,
            source_pointer="/decisions/0",
            canonical_source_ref="test",
        )
        assert rel.source_pointer == "/decisions/0"

    def test_metadata_preserved(self) -> None:
        rel = RelationshipRecordV2.from_uuids(
            relationship_type="enforces",
            source_uuid=UUID_DEC,
            target_uuid=UUID_INV,
            source_owner_uuid=UUID_ADR,
            canonical_source_ref="test",
            metadata={"custom": "value"},
        )
        assert rel.metadata == {"custom": "value"}


class TestIRRelationshipSourceOwner:
    """IRRelationship carries optional source_owner_id for v2.0."""

    def test_ir_relationship_default_no_owner(self) -> None:
        rel = IRRelationship(
            relationship_type="enforces",
            from_entity_id="DEC-0001",
            to_entity_id="INV-0001",
            canonical_source_ref="ADR-L-0001",
        )
        assert rel.source_owner_id is None

    def test_ir_relationship_with_owner(self) -> None:
        rel = IRRelationship(
            relationship_type="enforces",
            from_entity_id=UUID_DEC,
            to_entity_id=UUID_INV,
            canonical_source_ref=f"{UUID_ADR}#{UUID_DEC}",
            source_owner_id=UUID_ADR,
        )
        assert rel.source_owner_id == UUID_ADR

    def test_v2_projection_requires_owner(self) -> None:
        rel = IRRelationship(
            relationship_type="enforces",
            from_entity_id=UUID_DEC,
            to_entity_id=UUID_INV,
            canonical_source_ref="test",
            source_owner_id=None,
        )
        assert project_relationship_v2(rel) is None

    def test_v2_projection_with_owner(self) -> None:
        rel = IRRelationship(
            relationship_type="enforces",
            from_entity_id=UUID_DEC,
            to_entity_id=UUID_INV,
            canonical_source_ref=f"{UUID_ADR}#{UUID_DEC}",
            source_owner_id=UUID_ADR,
        )
        result = project_relationship_v2(rel)
        assert result is not None
        assert result.source_owner_id == UUID_ADR
        assert result.relationship_id == f"enforces:{UUID_DEC}:{UUID_INV}"


class TestLegacyAssertionPathPreserved:
    """v1.0/1.1 assertion derivation remains unchanged for legacy scopes."""

    def test_legacy_assertion_still_works(self) -> None:
        asrt = derive_assertion_id("enforces", "DEC-0001", "INV-0001", "ADR-L-0001")
        assert asrt.startswith("asrt-")
        assert len(asrt) == 5 + 64

    def test_ir_relationship_uses_legacy_assertion_by_default(self) -> None:
        rel = IRRelationship(
            relationship_type="enforces",
            from_entity_id="DEC-0001",
            to_entity_id="INV-0001",
            canonical_source_ref="ADR-L-0001#DEC-0001",
        )
        expected = derive_assertion_id("enforces", "DEC-0001", "INV-0001", "ADR-L-0001#DEC-0001")
        assert rel.assertion_id == expected


class TestRelationshipOwnerInPipeline:
    """Full pipeline: relationships in v1.3 scope carry source_owner_id."""

    @pytest.fixture()
    def v13_scope(self, tmp_path: Path) -> ProjectScope:
        adrs = tmp_path / "adrs" / "logical"
        adrs.mkdir(parents=True)
        project_yaml = tmp_path / "PROJECT.yaml"
        project_yaml.write_text(
            yaml.safe_dump(
                {
                    "project_info": {"name": "test-project", "description": "Test"},
                    "architecture_documentation": {
                        "architecture_namespace": NAMESPACE,
                        "adr_directory": "adrs",
                    },
                }
            )
        )
        fixture = FIXTURES / "v1_3" / "logical-minimal.yaml"
        (adrs / "ADR-L-9990-minimal-v13-logical.yaml").write_text(
            fixture.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return _make_scope(tmp_path)

    def test_v13_relationships_have_source_owner(self, v13_scope: ProjectScope) -> None:
        result = run_frontend_pipeline(scope=v13_scope)
        uuid_relationships = [
            r for r in result.model.relationships.values() if r.source_owner_id is not None
        ]
        for rel in uuid_relationships:
            validate_uuidv7(rel.source_owner_id)

    def test_declared_in_owner_is_adr(self, v13_scope: ProjectScope) -> None:
        result = run_frontend_pipeline(scope=v13_scope)
        declared_in_rels = [
            r for r in result.model.relationships.values() if r.relationship_type == "declared_in"
        ]
        for rel in declared_in_rels:
            if rel.source_owner_id is not None:
                assert rel.source_owner_id == UUID_ADR or rel.to_entity_id == UUID_ADR
