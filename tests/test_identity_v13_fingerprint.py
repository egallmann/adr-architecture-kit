"""Tests for v1.3 entity fingerprint computation."""

from __future__ import annotations

from adr_kit.identity import entity_fingerprint


class TestEntityFingerprint:
    def test_basic_record(self) -> None:
        record = {"id": "019109a0-b1c2-7def-8a00-112233445566", "name": "test"}
        fp = entity_fingerprint(record)
        assert fp.startswith("sha256:")
        assert len(fp) == 71  # "sha256:" + 64 hex chars

    def test_deterministic(self) -> None:
        record = {"alpha": 1, "beta": "hello"}
        assert entity_fingerprint(record) == entity_fingerprint(record)

    def test_key_order_independent(self) -> None:
        r1 = {"b": 2, "a": 1}
        r2 = {"a": 1, "b": 2}
        assert entity_fingerprint(r1) == entity_fingerprint(r2)

    def test_different_values_differ(self) -> None:
        r1 = {"key": "value1"}
        r2 = {"key": "value2"}
        assert entity_fingerprint(r1) != entity_fingerprint(r2)

    def test_empty_record(self) -> None:
        fp = entity_fingerprint({})
        assert fp.startswith("sha256:")

    def test_nested_record(self) -> None:
        record = {"outer": {"inner": [1, 2, 3]}}
        fp = entity_fingerprint(record)
        assert fp.startswith("sha256:")
