"""Canonical external-consumer workspace materialization for compatibility harnesses."""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "external-consumer-sdk"
PROJECT_YAML = FIXTURE_DIR / "PROJECT.yaml"
LOGICAL_ADR_SOURCE = REPO_ROOT / "tests" / "fixtures" / "valid" / "logical-minimal.yaml"
EXTERNAL_CONSUMER_PROJECT_NAME = "adr-kit-external-consumer-fixture"
ADR_KIT_PROJECT_NAME = "adr-architecture-kit"
STE_RUNTIME_PROJECT_NAME = "ste-runtime"


def materialize_external_consumer_fixture(destination: Path) -> Path:
    """Copy the canonical external-consumer PROJECT metadata and minimal ADR into destination."""

    project_root = destination / "fixture"
    logical = project_root / "adrs" / "logical"
    logical.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_YAML, project_root / "PROJECT.yaml")
    shutil.copy2(LOGICAL_ADR_SOURCE, logical / "ADR-L-9999-minimal.yaml")
    return project_root
