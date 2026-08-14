"""Tests for v1.3 UUIDv7 identity primitives."""

from __future__ import annotations

import pytest

from adr_kit.identity import (
    UUIDV7_PATTERN,
    derive_entity_uri,
    derive_relationship_id_v13,
    derive_assertion_id_v13,
    mint_uuidv7,
    parse_uuidv7,
    uuidv7_created_at,
    validate_uuidv7,
)


class TestUUIDv7Validation:
    def test_valid_uuidv7(self) -> None:
        valid = "019109a0-b1c2-7def-8a00-112233445566"
        assert validate_uuidv7(valid) == valid

    def test_rejects_uppercase(self) -> None:
        with pytest.raises(ValueError, match="Not a valid lowercase UUIDv7"):
            validate_uuidv7("019109A0-B1C2-7DEF-8A00-112233445566")

    def test_rejects_v4_uuid(self) -> None:
        with pytest.raises(ValueError, match="Not a valid lowercase UUIDv7"):
            validate_uuidv7("550e8400-e29b-41d4-a716-446655440000")

    def test_rejects_non_uuid_string(self) -> None:
        with pytest.raises(ValueError, match="Not a valid lowercase UUIDv7"):
            validate_uuidv7("not-a-uuid")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="Not a valid lowercase UUIDv7"):
            validate_uuidv7("")

    def test_parse_is_alias(self) -> None:
        valid = "019109a0-b1c2-7def-8a00-112233445566"
        assert parse_uuidv7(valid) == valid

    def test_uuidv7_pattern_is_shared_leaf_export(self) -> None:
        from adr_kit._uuidv7 import UUIDV7_PATTERN as leaf_pattern
        from adr_kit.decorators import UUIDV7_PATTERN as decorator_pattern

        assert UUIDV7_PATTERN is leaf_pattern is decorator_pattern
        assert UUIDV7_PATTERN.match("019109a0-b1c2-7def-8a00-112233445566")


class TestMintUUIDv7:
    def test_mint_returns_valid_uuidv7(self) -> None:
        result = mint_uuidv7()
        assert UUIDV7_PATTERN.match(result)
        validate_uuidv7(result)

    def test_injectable_timestamp(self) -> None:
        ts_ms = 1723334400000  # fixed epoch ms
        result = mint_uuidv7(timestamp_ms=ts_ms)
        assert UUIDV7_PATTERN.match(result)

    def test_injectable_random(self) -> None:
        rand = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a"
        r1 = mint_uuidv7(timestamp_ms=1000, rand_bytes=rand)
        r2 = mint_uuidv7(timestamp_ms=1000, rand_bytes=rand)
        assert r1 == r2

    def test_wrong_rand_length_raises(self) -> None:
        with pytest.raises(ValueError, match="10 bytes"):
            mint_uuidv7(rand_bytes=b"\x00" * 5)

    def test_deterministic_with_same_inputs(self) -> None:
        rand = bytes(range(10))
        ts = 1700000000000
        a = mint_uuidv7(timestamp_ms=ts, rand_bytes=rand)
        b = mint_uuidv7(timestamp_ms=ts, rand_bytes=rand)
        assert a == b

    def test_version_nibble_is_7(self) -> None:
        result = mint_uuidv7()
        assert result[14] == "7"

    def test_variant_bits_correct(self) -> None:
        result = mint_uuidv7()
        variant_char = result[19]
        assert variant_char in "89ab"


class TestUUIDv7CreatedAt:
    def test_decode_known_timestamp(self) -> None:
        ts_ms = 1723334400123
        rand = bytes(10)
        uuid_str = mint_uuidv7(timestamp_ms=ts_ms, rand_bytes=rand)
        created = uuidv7_created_at(uuid_str)
        assert created == "2024-08-11T00:00:00.123Z"

    def test_invalid_uuid_raises(self) -> None:
        with pytest.raises(ValueError):
            uuidv7_created_at("not-a-uuid")


class TestDeriveEntityUri:
    def test_basic_uri(self) -> None:
        uuid = "019109a0-b1c2-7def-8a00-112233445566"
        uri = derive_entity_uri("provider-architecture", uuid)
        assert uri == f"adr://provider-architecture/entities/{uuid}"

    def test_invalid_uuid_raises(self) -> None:
        with pytest.raises(ValueError):
            derive_entity_uri("ns", "bad-uuid")


class TestDeriveRelationshipIdV13:
    def test_basic_format(self) -> None:
        src = "019109a0-b1c2-7def-8a00-112233445566"
        tgt = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
        result = derive_relationship_id_v13("ENABLES", src, tgt)
        assert result == f"ENABLES:{src}:{tgt}"

    def test_invalid_source_raises(self) -> None:
        with pytest.raises(ValueError):
            derive_relationship_id_v13("X", "bad", "019109a0-b1c2-7def-8a00-112233445566")


class TestDeriveAssertionIdV13:
    def test_deterministic(self) -> None:
        src = "019109a0-b1c2-7def-8a00-112233445566"
        tgt = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
        owner = "019109a0-d5e6-7f78-8c00-aabb00112233"
        a = derive_assertion_id_v13("ENABLES", src, tgt, owner, "/decisions/0")
        b = derive_assertion_id_v13("ENABLES", src, tgt, owner, "/decisions/0")
        assert a == b
        assert a.startswith("asrt-")

    def test_different_pointer_yields_different_id(self) -> None:
        src = "019109a0-b1c2-7def-8a00-112233445566"
        tgt = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
        owner = "019109a0-d5e6-7f78-8c00-aabb00112233"
        a = derive_assertion_id_v13("E", src, tgt, owner, "/a")
        b = derive_assertion_id_v13("E", src, tgt, owner, "/b")
        assert a != b

    def test_none_pointer_uses_empty(self) -> None:
        src = "019109a0-b1c2-7def-8a00-112233445566"
        tgt = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
        owner = "019109a0-d5e6-7f78-8c00-aabb00112233"
        a = derive_assertion_id_v13("E", src, tgt, owner, None)
        b = derive_assertion_id_v13("E", src, tgt, owner, "")
        assert a == b
