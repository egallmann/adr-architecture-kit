from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SIBLING_KERNEL_SCHEMA_PATH = (
    REPO_ROOT.parent / "ste-kernel" / "architecture-ir" / "architecture-ir.schema.json"
)
FIXTURE_KERNEL_SCHEMA_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "kernel" / "architecture-ir.schema.json"
)


def test_kernel_schema_fixture_exists() -> None:
    assert FIXTURE_KERNEL_SCHEMA_PATH.exists()


def test_kernel_schema_fixture_matches_sibling_checkout_when_available() -> None:
    if not SIBLING_KERNEL_SCHEMA_PATH.exists():
        pytest.skip("Sibling ste-kernel checkout not available in this environment.")

    assert FIXTURE_KERNEL_SCHEMA_PATH.read_bytes() == SIBLING_KERNEL_SCHEMA_PATH.read_bytes()
