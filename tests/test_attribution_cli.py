from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from click.testing import CliRunner

from src.adr_kit.cli.main import cli
from src.adr_kit.models import (
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    ImplementationAttributionEvidence,
    NormalizedArchitectureModel,
    NormalizedEntity,
)


def _adr_entity(adr_id: str, *, status: str = "accepted") -> NormalizedEntity:
    return NormalizedEntity(
        id=adr_id,
        entity_type="adr",
        name=adr_id,
        summary="test adr",
        canonical_source=CanonicalSource(
            source_type="logical_adr",
            source_ref=adr_id,
            artifact_path=f"adrs/logical/{adr_id}.yaml",
        ),
        metadata={"status": status, "domains": ["test"], "tags": ["traceability"]},
        completeness=Completeness(status="complete", missing_fields=[]),
        provenance=DiscoveryProvenance(
            source_type="adr",
            source_ref=adr_id,
            extraction_phase="test",
            classification="explicit",
            generator="test",
        ),
    )


def _minimal_model_for_cli() -> NormalizedArchitectureModel:
    return NormalizedArchitectureModel(
        mode="normalized",
        scope_root=".",
        architecture_namespace="test-cli",
        fingerprint="cli-test",
        entities=[_adr_entity("ADR-L-0999")],
        relationships=[],
        unresolved=[],
        validation_summary=None,
        source_coverage=None,
    )


def test_attribution_generate_shim_python():
    runner = CliRunner()
    result = runner.invoke(cli, ["attribution", "generate-shim", "--lang", "python"])
    assert result.exit_code == 0
    assert "implements_adr" in result.output
    assert "implements_adrs" in result.output


def test_attribution_workspace_report_writes_federation(tmp_path: Path) -> None:
    workspace_root = tmp_path / "ws"
    state_dir = workspace_root / ".ste-workspace"
    repo_a = workspace_root / "repo-a"
    repo_a.mkdir(parents=True)
    (workspace_root / "workspace.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "output_dir": ".ste-workspace/",
                "repos": [{"name": "repo-a", "path": "repo-a", "kind": "library", "lang": "python"}],
            },
        ),
        encoding="utf-8",
    )
    (repo_a / "adrs").mkdir(parents=True)
    (repo_a / "adrs" / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "type": "manifest",
                "adrs": [{"id": "ADR-L-0001", "title": "Test", "status": "accepted"}],
            },
        ),
        encoding="utf-8",
    )
    ev_dir = state_dir / "state" / "repo-a" / "attribution"
    ev_dir.mkdir(parents=True)
    (ev_dir / "implementation-attribution-evidence.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.2",
                "type": "implementation_attribution_evidence",
                "records": [
                    {
                        "implementation_entity_id": "fn:1",
                        "implementation_entity_type": "function",
                        "attributed_adrs": ["ADR-L-0001"],
                        "enforced_invariants": [],
                        "provenance": {"source_file": "a.py", "extractor": "t", "commit": None},
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "attribution",
            "workspace-report",
            "--workspace-root",
            str(workspace_root),
        ],
    )
    assert result.exit_code == 0, result.output
    out_file = state_dir / "workspace-attribution-federation.yaml"
    assert out_file.is_file()
    doc = yaml.safe_load(out_file.read_text(encoding="utf-8"))
    assert doc["type"] == "workspace_attribution_federation"
    assert any(r["qualified_id"] == "repo-a:ADR-L-0001" for r in doc["qualified_adrs"])


def test_attribution_generate_shim_typescript():
    runner = CliRunner()
    result = runner.invoke(cli, ["attribution", "generate-shim", "--lang", "typescript"])
    assert result.exit_code == 0
    assert "implements_adr" in result.output


def test_attribution_generate_shim_writes_output(tmp_path: Path):
    runner = CliRunner()
    target = tmp_path / "decorators.ts"
    result = runner.invoke(cli, ["attribution", "generate-shim", "--lang", "typescript", "-o", str(target)])
    assert result.exit_code == 0
    assert target.is_file()


def test_attribution_check_reads_evidence(tmp_path: Path):
    """Validate attribution check wiring with a mocked corpus model."""
    scope = tmp_path / "fake-root"
    scope.mkdir()

    ev_path = tmp_path / "implementation-attribution-evidence.yaml"
    ev_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.2",
                "type": "implementation_attribution_evidence",
                "records": [
                    {
                        "implementation_entity_id": "test-fn",
                        "implementation_entity_type": "function",
                        "attributed_adrs": ["ADR-L-0999"],
                        "enforced_invariants": [],
                        "provenance": {
                            "source_file": "dummy.py",
                            "extractor": "pytest",
                            "commit": None,
                        },
                        "confidence": "declared",
                        "attributed_capabilities": [],
                        "attribution_source_language": "unknown",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    mock_repo = MagicMock()
    mock_repo.load.return_value = None
    mock_repo.get_model.return_value = _minimal_model_for_cli()

    with patch("src.adr_kit.cli.main.ArchitectureRepository", return_value=mock_repo):
        result = runner.invoke(
            cli,
            [
                "attribution",
                "check",
                "--scope",
                str(scope),
                "--evidence",
                str(ev_path),
                "--profile",
                "brownfield",
            ],
        )
    assert result.exit_code == 0
    assert "compliant" in result.output.lower() or "outcome" in result.output


def test_attribution_coverage_cmd(tmp_path: Path):
    scope = tmp_path / "fake-root"
    scope.mkdir()
    runner = CliRunner()

    mm = MagicMock()
    mm.adr_status_map.return_value = {"ADR-L-0999": "accepted"}
    mock_repo = MagicMock()
    mock_repo.load.return_value = None
    mock_repo.get_model.return_value = mm

    with patch("src.adr_kit.cli.main.ArchitectureRepository", return_value=mock_repo):
        result = runner.invoke(cli, ["attribution", "coverage", "--scope", str(scope)])

    assert result.exit_code == 0
    assert "evidence_schema_version" in result.output
    assert "ADR-L-0999" in result.output or "ADR" in result.output


def test_legacy_schema_1_point_0_evidence_round_trips_via_pydantic() -> None:
    obj = ImplementationAttributionEvidence.model_validate(
        {
            "schema_version": "1.0",
            "type": "implementation_attribution_evidence",
            "records": [
                {
                    "implementation_entity_id": "fn:a.py:f:1",
                    "implementation_entity_type": "function",
                    "attributed_adrs": ["ADR-L-0001"],
                    "enforced_invariants": [],
                    "provenance": {
                        "source_file": "a.py",
                        "extractor": "x",
                        "commit": None,
                    },
                }
            ],
        }
    )
    assert obj.records[0].confidence == "declared"
    assert obj.records[0].attributed_capabilities == []
    assert obj.records[0].attribution_source_language is None
