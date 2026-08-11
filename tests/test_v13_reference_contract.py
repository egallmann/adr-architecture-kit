"""v1.3 reference contract tests — UUID refs, external refs, no alias-only refs."""

from __future__ import annotations

from pathlib import Path

import pytest

from adr_kit.identity import (
    derive_alias_ref,
    derive_entity_uri,
    derive_relationship_id_v13,
    entity_fingerprint,
)
from adr_kit.parser import ADRParser, ADRSchemaValidationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class TestUUIDReferences:
    def test_related_adrs_use_uuid(self, tmp_path: Path) -> None:
        source = (FIXTURES / "v1_3" / "logical-minimal.yaml").read_text(encoding="utf-8")
        extended = source + "\nrelated_adrs:\n  - 019109a0-c3d4-7e56-8b00-ffeeddccbbaa\n"
        path = tmp_path / "with-related.yaml"
        path.write_text(extended, encoding="utf-8")

        parser = ADRParser()
        data = parser.parse_yaml(path)
        parser.validate_against_schema(data, parser._authoring_schema_name(data, "logical"))

    def test_related_adrs_reject_alias(self, tmp_path: Path) -> None:
        source = (FIXTURES / "v1_3" / "logical-minimal.yaml").read_text(encoding="utf-8")
        extended = source + "\nrelated_adrs:\n  - ADR-L-0001\n"
        path = tmp_path / "alias-related.yaml"
        path.write_text(extended, encoding="utf-8")

        parser = ADRParser()
        data = parser.parse_yaml(path)
        with pytest.raises(ADRSchemaValidationError):
            parser.validate_against_schema(data, parser._authoring_schema_name(data, "logical"))


class TestExternalReferences:
    def test_valid_external_ref_in_substrate_binding(self, tmp_path: Path) -> None:
        source = (FIXTURES / "v1_3" / "logical-minimal.yaml").read_text(encoding="utf-8")
        binding = """\

substrate_bindings:
  - external_namespace: ste-substrate
    artifact_id: SUBSTRATE-0001
    kind: context_domain
    version: 1.0.0
    fingerprint: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    role: required_context
    selected_by: "019109a0-b1c2-7def-8a00-aabbccddeef0"
"""
        path = tmp_path / "with-binding.yaml"
        path.write_text(source + binding, encoding="utf-8")

        parser = ADRParser()
        data = parser.parse_yaml(path)
        parser.validate_against_schema(data, parser._authoring_schema_name(data, "logical"))


class TestDerivedSurfacesNotAuthored:
    def test_entity_uri_is_derived(self) -> None:
        uuid = "019109a0-b1c2-7def-8a00-112233445566"
        uri = derive_entity_uri("provider-architecture", uuid)
        assert uri.startswith("adr://")

    def test_alias_ref_is_derived(self) -> None:
        ref = derive_alias_ref("ADR-L-0001", "two-layer")
        assert ":" in ref


class TestProviderNamespaceFromProject:
    def test_namespace_not_per_adr(self) -> None:
        parser = ADRParser()
        data = parser.parse_yaml(FIXTURES / "v1_3" / "logical-minimal.yaml")
        assert "architecture_namespace" not in data


class TestRelationshipAndFingerprint:
    def test_relationship_id_uses_uuids(self) -> None:
        src = "019109a0-b1c2-7def-8a00-112233445566"
        tgt = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
        rid = derive_relationship_id_v13("ENABLES", src, tgt)
        assert src in rid
        assert tgt in rid

    def test_fingerprint_sha256(self) -> None:
        record = {"id": "019109a0-b1c2-7def-8a00-112233445566", "type": "cap"}
        fp = entity_fingerprint(record)
        assert fp.startswith("sha256:")
        assert len(fp.split(":")[1]) == 64
