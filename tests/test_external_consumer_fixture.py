"""Regression coverage for the canonical external-consumer SDK fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from adr_kit.api import CompilationRequest, compile_architecture
from adr_kit.generators.system_overview_generator import SystemOverviewGenerator
from adr_kit.scope import ProjectScopeResolver
from scripts.external_consumer_fixture import (
    ADR_KIT_PROJECT_NAME,
    EXTERNAL_CONSUMER_PROJECT_NAME,
    PROJECT_YAML,
    STE_RUNTIME_PROJECT_NAME,
    materialize_external_consumer_fixture,
)
from scripts.test_sdk_consumer import PINNED_TIMESTAMP, run_consumer

REPO_ROOT = Path(__file__).resolve().parents[1]
RETAINED_WHEEL = next(iter(sorted((REPO_ROOT / "dist").glob("adr_architecture_kit-*.whl"))), None)


def _venv_python(environment: Path) -> Path:
    windows_python = environment / "Scripts" / "python.exe"
    if windows_python.is_file():
        return windows_python
    return environment / "bin" / "python"


def _venv_pip(environment: Path) -> Path:
    windows_pip = environment / "Scripts" / "pip.exe"
    if windows_pip.is_file():
        return windows_pip
    return environment / "bin" / "pip"


def _project_name(project_root: Path) -> str:
    payload = yaml.safe_load((project_root / "PROJECT.yaml").read_text(encoding="utf-8"))
    return str(payload["project"]["name"])


def test_canonical_external_consumer_fixture_identity() -> None:
    payload = yaml.safe_load(PROJECT_YAML.read_text(encoding="utf-8"))
    name = payload["project"]["name"]
    assert name == EXTERNAL_CONSUMER_PROJECT_NAME
    assert name != ADR_KIT_PROJECT_NAME
    assert name != STE_RUNTIME_PROJECT_NAME
    assert "development_methodology" not in payload
    assert "implementation_identifiers" not in payload


def test_external_consumer_selects_legacy_generic_system_overview(tmp_path: Path) -> None:
    project_root = materialize_external_consumer_fixture(tmp_path)
    assert _project_name(project_root) == EXTERNAL_CONSUMER_PROJECT_NAME

    scope = ProjectScopeResolver(explicit_scope=project_root).resolve()
    model = SystemOverviewGenerator(scope=scope).build_model()
    assert model.profile.profile_kind == "legacy-generic"
    assert model.project.name == EXTERNAL_CONSUMER_PROJECT_NAME


def test_external_consumer_compiles_through_supported_sdk(tmp_path: Path) -> None:
    project_root = materialize_external_consumer_fixture(tmp_path)
    preview = compile_architecture(CompilationRequest(project_root, timestamp=PINNED_TIMESTAMP))
    assert preview.success, preview.diagnostics
    assert preview.model is not None
    assert preview.fingerprint is not None
    artifact_ids = {item.artifact_id for item in preview.artifacts}
    assert artifact_ids
    assert "system-overview" in artifact_ids


def test_external_consumer_sdk_harness_from_source_install(tmp_path: Path) -> None:
    project_root = materialize_external_consumer_fixture(tmp_path)
    evidence = run_consumer(project_root, "source")
    assert evidence["package_version"] != "0+unknown"
    assert evidence["artifact_ids"]


@pytest.mark.skipif(RETAINED_WHEEL is None, reason="retained wheel not built under dist/")
def test_external_consumer_sdk_harness_from_installed_wheel(tmp_path: Path) -> None:
    project_root = materialize_external_consumer_fixture(tmp_path / "consumer-workspace")
    consumer_script = tmp_path / "test_sdk_consumer.py"
    consumer_script.write_text(
        (REPO_ROOT / "scripts" / "test_sdk_consumer.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    environment = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    subprocess.run([str(_venv_pip(environment)), "install", str(RETAINED_WHEEL)], check=True)
    completed = subprocess.run(
        [
            str(_venv_python(environment)),
            str(consumer_script),
            "--project-root",
            str(project_root),
            "--version-source",
            "metadata",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    evidence = json.loads(completed.stdout)
    assert evidence["artifact_ids"]
