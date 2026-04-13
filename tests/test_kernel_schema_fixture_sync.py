from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_PUBLIC_IR_SCHEMA_PATH = (
    REPO_ROOT / "contracts" / "architecture-ir" / "architecture-ir.schema.json"
)
SIBLING_SPEC_SCHEMA_PATH = (
    REPO_ROOT.parent / "ste-spec" / "contracts" / "architecture-ir" / "architecture-ir.schema.json"
)


def test_public_ir_schema_mirror_exists() -> None:
    assert LOCAL_PUBLIC_IR_SCHEMA_PATH.exists()
    assert LOCAL_PUBLIC_IR_SCHEMA_PATH.read_text(encoding="utf-8").startswith("{")


def test_public_ir_schema_mirror_matches_ste_spec_when_available() -> None:
    if not SIBLING_SPEC_SCHEMA_PATH.exists():
        pytest.skip("Sibling ste-spec checkout not available in this environment.")

    assert LOCAL_PUBLIC_IR_SCHEMA_PATH.read_text(encoding="utf-8") == SIBLING_SPEC_SCHEMA_PATH.read_text(
        encoding="utf-8"
    )
