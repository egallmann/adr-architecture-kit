"""Helpers for implementation attribution retrofit contract guards."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ADR_ID_PATTERN = re.compile(r"^ADR-L-\d{4}$")
INV_ID_PATTERN = re.compile(r"^INV-\d{4}$")
ADR_PC_PATTERN = re.compile(r"^ADR-PC-\d{4}$")

REPO_ROOT = Path(__file__).resolve().parents[1]


def function_adr_metadata(target: Any) -> tuple[str, ...]:
    return getattr(target, "__implements_adrs__", ()) or ()


def function_invariant_metadata(target: Any) -> tuple[str, ...]:
    return getattr(target, "__enforces_invariants__", ()) or ()


def class_adr_metadata(class_ref: type[Any]) -> tuple[str, ...]:
    return getattr(class_ref, "__implements_adrs__", ()) or ()


def class_invariant_metadata(class_ref: type[Any]) -> tuple[str, ...]:
    return getattr(class_ref, "__enforces_invariants__", ()) or ()


def expect_adr_claims(
    target: Any,
    adr_id: str,
    invariant_ids: tuple[str, ...] = (),
) -> None:
    adr_ids = function_adr_metadata(target)
    assert adr_id in adr_ids, f"expected {adr_id} in {adr_ids}"
    for value in adr_ids:
        assert ADR_ID_PATTERN.match(value) or ADR_PC_PATTERN.match(value), value

    if invariant_ids:
        inv_ids = function_invariant_metadata(target)
        for inv_id in invariant_ids:
            assert inv_id in inv_ids, f"expected {inv_id} in {inv_ids}"
        for value in inv_ids:
            assert INV_ID_PATTERN.match(value), value


def expect_adr_source_exists(adr_id: str, relative_path: str) -> None:
    manifest = (REPO_ROOT / "adrs" / "manifest.yaml").read_text(encoding="utf-8")
    assert adr_id in manifest
    assert (REPO_ROOT / relative_path).is_file()
