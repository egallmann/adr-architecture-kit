"""Tests for v1.3 alias name validation and derived surfaces."""

from __future__ import annotations

import pytest

from adr_kit.identity import (
    ALIAS_NAME_PATTERN,
    RESERVED_GENERIC_ALIAS_NAMES,
    derive_alias_ref,
    validate_alias_name,
)


class TestAliasNamePattern:
    def test_valid_simple(self) -> None:
        assert ALIAS_NAME_PATTERN.match("two-layer-architecture")

    def test_valid_numeric_suffix(self) -> None:
        assert ALIAS_NAME_PATTERN.match("scope-resolver-v2")

    def test_rejects_uppercase(self) -> None:
        assert not ALIAS_NAME_PATTERN.match("Two-Layer")

    def test_rejects_leading_digit(self) -> None:
        assert not ALIAS_NAME_PATTERN.match("1-bad-name")

    def test_rejects_trailing_dash(self) -> None:
        assert not ALIAS_NAME_PATTERN.match("bad-name-")

    def test_rejects_double_dash(self) -> None:
        assert not ALIAS_NAME_PATTERN.match("bad--name")


class TestValidateAliasName:
    def test_valid_name(self) -> None:
        assert validate_alias_name("two-layer-architecture") == "two-layer-architecture"

    def test_too_short(self) -> None:
        with pytest.raises(ValueError, match="3–96 characters"):
            validate_alias_name("ab")

    def test_too_long(self) -> None:
        with pytest.raises(ValueError, match="3–96 characters"):
            validate_alias_name("a" * 97)

    def test_exactly_3_chars(self) -> None:
        assert validate_alias_name("abc") == "abc"

    def test_rejects_uuid_shaped(self) -> None:
        with pytest.raises(ValueError):
            validate_alias_name("019109a0-b1c2-7def-8a00-112233445566")

    def test_rejects_uuid_hex_without_dashes(self) -> None:
        with pytest.raises(ValueError):
            validate_alias_name("019109a0b1c27def8a00112233445566")

    @pytest.mark.parametrize("name", sorted(RESERVED_GENERIC_ALIAS_NAMES))
    def test_rejects_reserved_generics(self, name: str) -> None:
        with pytest.raises(ValueError, match="reserved generic"):
            validate_alias_name(name)

    def test_rejects_entity_type_repetition(self) -> None:
        with pytest.raises(ValueError, match="reserved generic|exact repetition"):
            validate_alias_name("capability", entity_type="capability")

    def test_rejects_non_reserved_entity_type_repetition(self) -> None:
        with pytest.raises(ValueError, match="exact repetition"):
            validate_alias_name("logical", entity_type="logical")

    def test_allows_prefixed_entity_type(self) -> None:
        assert (
            validate_alias_name("capability-graph", entity_type="capability") == "capability-graph"
        )

    def test_pattern_mismatch(self) -> None:
        with pytest.raises(ValueError, match="must match"):
            validate_alias_name("Bad_Name")


class TestDeriveAliasRef:
    def test_basic(self) -> None:
        assert derive_alias_ref("ADR-L-0001", "two-layer") == "ADR-L-0001:two-layer"

    def test_entity_alias(self) -> None:
        assert derive_alias_ref("CAP-0001", "scope-resolution") == "CAP-0001:scope-resolution"
