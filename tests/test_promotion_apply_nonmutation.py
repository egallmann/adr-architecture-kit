"""Promotion apply must separate detached validation from authority commits."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from adr_kit.api import PromotionApplyRequest, apply_promotion
from adr_kit.promotion import service
from adr_kit.promotion.bindings import (
    authorized_adr_schema_fingerprint,
    fingerprint_bytes,
    roadmap_rules_fingerprint,
)
from adr_kit.promotion.candidate_validation import validate_adr_payload_bytes
from adr_kit.promotion.candidates import build_create_adr_post_image
from adr_kit.promotion.ste_contract import (
    human_lock_valid,
    locked_intent_fingerprint,
    validate_contract,
)
from tests.test_architecture_index_generator import _create_fixture


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    # Keep journal + overlay paths within Windows path limits in managed worktrees.
    base = Path(__file__).resolve().parent / ".tmp"
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="promotion-", dir=base) as directory:
        yield Path(directory)


def _snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "ROADMAP.md", root / "PROJECT.yaml"]
    paths.extend(path for path in (root / "adrs").rglob("*") if path.is_file())
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in paths}


def _prepared_project(tmp_path: Path, lock: str = "valid") -> tuple[Path, Path]:
    root = tmp_path / "project"
    _create_fixture(root)
    (root / "ROADMAP.md").write_text("# Roadmap\n\n## Phase 1\n", encoding="utf-8")
    seed = build_create_adr_post_image(
        adr_id="ADR-L-0098",
        title="Original decision",
        decisions=[{"id": "DEC-0098", "summary": "Original", "rationale": "Test authority"}],
        invariants=[],
    )
    amend_path = "adrs/logical/ADR-L-0098-original.yaml"
    (root / amend_path).write_text(seed, encoding="utf-8")
    for args in (
        ("init",),
        ("config", "core.autocrlf", "false"),
        ("add", "."),
        (
            "-c",
            "user.name=Promotion Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "authority baseline",
        ),
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

    amended = yaml.safe_load(seed)
    amended["title"] = "Amended decision"
    supersede_path = "adrs/logical/ADR-L-1000-discovery.yaml"
    superseded = yaml.safe_load((root / supersede_path).read_text(encoding="utf-8"))
    superseded["supersedes"] = ["ADR-L-0098"]
    create_path = "adrs/logical/ADR-L-0099-created.yaml"
    created = build_create_adr_post_image(
        adr_id="ADR-L-0099",
        title="Created decision",
        decisions=[{"id": "DEC-0099", "summary": "New", "rationale": "Test authority"}],
        invariants=[],
    )
    post_images = [
        ("create", create_path, created.encode()),
        ("amend", amend_path, yaml.safe_dump(amended, sort_keys=False).encode()),
        ("supersede", supersede_path, yaml.safe_dump(superseded, sort_keys=False).encode()),
        ("amend", "ROADMAP.md", b"# Roadmap\n\n## Phase 1\n\n## Phase 2\n"),
    ]
    fixture = Path(__file__).parent / "fixtures/ste_promotion_contract_v0_1/02-valid-locked.json"
    contract = json.loads(fixture.read_text(encoding="utf-8"))["contract"]
    contract["provider"] = "adr-architecture-kit"
    contract["authority_baseline"].update(provider="adr-architecture-kit", value=baseline)
    contract["mutations"] = []
    store = root / ".adr-kit/promotion"
    (store / "payloads").mkdir(parents=True)
    resolved = {}
    for index, (operation, relative, content) in enumerate(post_images, 1):
        mutation_id = f"M-{index:02d}"
        ref = f"payloads/{mutation_id}"
        (store / ref).write_bytes(content)
        if relative.endswith(".yaml"):
            assert validate_adr_payload_bytes(content, relative_path=relative) == []
            schema_ref, schema_fp = authorized_adr_schema_fingerprint(root)
            target_ref = "adr:" + yaml.safe_load(content)["id"]
        else:
            schema_ref, schema_fp = "rules:roadmap-file-v1", roadmap_rules_fingerprint()
            target_ref = "file:ROADMAP.md"
        payload_fp = fingerprint_bytes(content)
        contract["mutations"].append(
            {
                "id": mutation_id,
                "operation": operation,
                "provider": "adr-architecture-kit",
                "provider_target_ref": target_ref,
                "outcome_refs": ["O-01"],
                "payload_binding": {"ref": ref, "fingerprint": payload_fp},
                "schema_binding": {"ref": schema_ref, "fingerprint": schema_fp},
                "validation_evidence": {
                    "payload_fingerprint": payload_fp,
                    "schema_binding_fingerprint": schema_fp,
                    "result": "valid",
                },
            }
        )
        resolved[mutation_id] = relative
    (store / "resolved-targets.json").write_text(json.dumps(resolved), encoding="utf-8")
    human_lock = contract["human_lock"]
    human_lock["authority_baseline"] = contract["authority_baseline"]
    human_lock["promotion_scope"]["mutation_ids"] = list(resolved)
    human_lock["payload_bindings"] = [m["payload_binding"] for m in contract["mutations"]]
    human_lock["schema_bindings"] = [m["schema_binding"] for m in contract["mutations"]]
    human_lock["locked_intent_fingerprint"] = locked_intent_fingerprint(contract)
    assert human_lock_valid(contract) == (True, [])
    if lock == "missing":
        contract["human_lock"] = None
        contract["lifecycle_state"] = "lock_ready"
    elif lock == "invalid":
        human_lock["locked_intent_fingerprint"] = "sha256:" + "0" * 64
    assert validate_contract(contract) == []
    pc = store / "prepared.json"
    pc.write_text(json.dumps(contract), encoding="utf-8")
    return root, pc


@pytest.mark.parametrize("lock", ["missing", "valid", "invalid"])
def test_dry_run_leaves_authority_and_execution_evidence_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lock: str,
) -> None:
    root, pc = _prepared_project(tmp_path, lock)
    before = _snapshot(root)
    contract_before = pc.read_bytes()
    regeneration = Mock(side_effect=AssertionError("dry-run must not regenerate authority"))
    monkeypatch.setattr(service, "regenerate_and_validate", regeneration)
    result = apply_promotion(PromotionApplyRequest(root, pc, commit=False))
    assert result.success, result.diagnostics
    assert _snapshot(root) == before
    assert not (root / "adrs/logical/ADR-L-0099-created.yaml").exists()
    assert pc.read_bytes() == contract_before
    assert result.semantic_state == "DRY_RUN_OK"
    assert result.authority_committed is False
    assert result.apply_execution_evidence_appended is False
    assert result.regeneration_completed is False
    assert result.validation_success is False
    assert result.execution_evidence == ()
    assert result.corpus_fingerprint is None
    regeneration.assert_not_called()


def test_dry_run_never_enters_committing_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, pc = _prepared_project(tmp_path, "missing")
    transaction = Mock(side_effect=AssertionError("authoritative transaction entered"))
    monkeypatch.setattr(service, "commit_all_or_none", transaction)
    result = apply_promotion(PromotionApplyRequest(root, pc))
    assert result.success, result.diagnostics
    transaction.assert_not_called()


@pytest.mark.parametrize("lock", ["missing", "invalid"])
def test_commit_rejects_invalid_human_lock_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lock: str,
) -> None:
    root, pc = _prepared_project(tmp_path, lock)
    before, evidence_before = _snapshot(root), pc.read_bytes()
    transaction = Mock(side_effect=AssertionError("invalid lock entered transaction"))
    monkeypatch.setattr(service, "commit_all_or_none", transaction)
    result = apply_promotion(PromotionApplyRequest(root, pc, commit=True))
    assert not result.success
    assert any(d.code == "PROMOTION_HUMAN_LOCK_INVALID" for d in result.diagnostics)
    assert _snapshot(root) == before
    assert pc.read_bytes() == evidence_before
    transaction.assert_not_called()


def test_commit_applies_locked_payloads_and_regenerates(tmp_path: Path) -> None:
    root, pc = _prepared_project(tmp_path)
    result = apply_promotion(
        PromotionApplyRequest(root, pc, commit=True, timestamp="2026-10-03T00:00:00Z")
    )
    assert result.success, result.diagnostics
    assert result.semantic_state == "PROMOTION_COMPLETE"
    assert result.authority_committed
    assert result.apply_execution_evidence_appended
    assert result.regeneration_completed
    assert result.validation_success
    contract = json.loads(pc.read_text(encoding="utf-8"))
    resolved = json.loads((pc.parent / "resolved-targets.json").read_text(encoding="utf-8"))
    for mutation in contract["mutations"]:
        assert (root / resolved[mutation["id"]]).read_bytes() == (
            pc.parent / mutation["payload_binding"]["ref"]
        ).read_bytes()
    assert contract["execution_evidence"][-1]["class"] == "apply_success"


def test_commit_fault_rolls_back_create_and_amend(tmp_path: Path) -> None:
    root, pc = _prepared_project(tmp_path)
    before, evidence_before = _snapshot(root), pc.read_bytes()

    def fault(phase: str) -> None:
        if phase.startswith("during_commit:") and "ADR-L-1000" in phase:
            raise RuntimeError("failure after create and amend")

    result = service.apply_promotion(PromotionApplyRequest(root, pc, commit=True), fault=fault)
    assert not result.success
    assert result.authority_committed is False
    assert _snapshot(root) == before
    assert pc.read_bytes() == evidence_before


def test_dry_run_rejects_invalid_post_state_without_mutation(tmp_path: Path) -> None:
    root, pc = _prepared_project(tmp_path, "missing")
    contract = json.loads(pc.read_text(encoding="utf-8"))
    mutation = contract["mutations"][0]
    invalid = b"id: ADR-L-0099\n"
    (pc.parent / mutation["payload_binding"]["ref"]).write_bytes(invalid)
    fingerprint = fingerprint_bytes(invalid)
    mutation["payload_binding"]["fingerprint"] = fingerprint
    mutation["validation_evidence"]["payload_fingerprint"] = fingerprint
    pc.write_text(json.dumps(contract), encoding="utf-8")
    before, evidence_before = _snapshot(root), pc.read_bytes()
    result = apply_promotion(PromotionApplyRequest(root, pc))
    assert not result.success
    assert any(d.code == "PROMOTION_STAGED_VALIDATION_FAILED" for d in result.diagnostics)
    assert result.authority_committed is False
    assert _snapshot(root) == before
    assert pc.read_bytes() == evidence_before


def test_cli_promotion_default_apply_is_nonmutating(tmp_path: Path) -> None:
    from click.testing import CliRunner
    from adr_kit.cli.main import cli

    root, pc = _prepared_project(tmp_path, "missing")
    before, evidence_before = _snapshot(root), pc.read_bytes()
    result = CliRunner().invoke(
        cli, ["promote", "apply", "--project-root", str(root), "--contract", str(pc)]
    )
    assert result.exit_code == 0, result.output
    assert "DRY_RUN_OK" in result.output
    assert _snapshot(root) == before
    assert pc.read_bytes() == evidence_before
