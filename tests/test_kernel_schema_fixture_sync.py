from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SIBLING_SPEC_SCHEMA_PATH = (
    REPO_ROOT.parent / "ste-spec" / "contracts" / "architecture-ir" / "architecture-ir.schema.json"
)


def test_public_ir_schema_is_loaded_from_ste_spec_when_available() -> None:
    if not SIBLING_SPEC_SCHEMA_PATH.exists():
        pytest.skip("Sibling ste-spec checkout not available in this environment.")

    assert SIBLING_SPEC_SCHEMA_PATH.read_text(encoding="utf-8").startswith("{")
    assert not (REPO_ROOT / "tests" / "fixtures" / "kernel" / "architecture-ir.schema.json").exists()
