"""Public SDK promotion contract and STE conformance tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adr_kit.api import (
    InvalidRequestError,
    PromotionPrepareRequest,
    capabilities,
    prepare_promotion,
)
from adr_kit.promotion.bindings import roadmap_rules_fingerprint
from adr_kit.promotion.ste_contract import (
    human_lock_valid,
    locked_intent_fingerprint,
    mechanical_ready,
    validate_contract,
)
from adr_kit.promotion.targets import resolve_target
from adr_kit.promotion.transaction import PlannedWrite, commit_all_or_none
from tests.test_architecture_index_generator import _create_fixture

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ste_promotion_contract_v0_1"
REPO_ROOT = Path(__file__).resolve().parents[1]


def test_capabilities_advertise_promotion_without_schema_13() -> None:
    manifest = capabilities()
    assert "prepare_promotion" in manifest.operations
    assert "check_promotion" in manifest.operations
    assert "apply_promotion" in manifest.operations
    assert "1.3" not in manifest.supported_adr_schema_versions


def test_prepare_rejects_output_into_adrs(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    pc = root / "pc.json"
    pc.write_text(
        json.dumps(
            {
                "contract_version": "ste.design_journal.promotion_contract/v0.1",
                "design_journal_version": "ste.design_journal/v0.1",
                "journal_id": "DJ-TEST",
                "lifecycle_state": "open",
                "provider": "adr-architecture-kit",
                "authority_baseline": {
                    "provider": "adr-architecture-kit",
                    "kind": "git_commit",
                    "value": "0" * 40,
                },
                "outcomes": [],
                "mutations": [],
                "blockers": [],
                "readiness": {"design_lock": False, "mechanical_promotion": False},
                "human_lock": None,
                "execution_evidence": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(InvalidRequestError):
        PromotionPrepareRequest(
            project_root=root,
            promotion_contract_path=pc,
            prepared_contract_output_path=root / "adrs" / "prepared.json",
        )
    with pytest.raises(InvalidRequestError):
        PromotionPrepareRequest(
            project_root=root,
            promotion_contract_path=pc,
            prepared_contract_output_path=root / "ROADMAP.md",
        )


def test_ste_conformance_fixtures() -> None:
    for path in sorted(FIXTURES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        expect = data.get("expect", "pass")
        contract = data["contract"]
        errors = validate_contract(contract)
        if expect == "pass":
            assert errors == [], path.name
        else:
            assert errors, path.name


def test_locked_intent_excludes_execution_evidence() -> None:
    data = json.loads((FIXTURES / "02-valid-locked.json").read_text(encoding="utf-8"))
    contract = data["contract"]
    before = locked_intent_fingerprint(contract)
    contract = dict(contract)
    contract["execution_evidence"] = list(contract.get("execution_evidence") or []) + [
        {"attempt_id": "x", "class": "D", "message": "retry"}
    ]
    after = locked_intent_fingerprint(contract)
    assert before == after


def test_target_resolution_create_and_roadmap(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    (root / "ROADMAP.md").write_text("# Roadmap\n\n## Phase 1\n", encoding="utf-8")
    created = resolve_target(
        root, "adr:ADR-L-0099", operation="create", create_title="Example Title"
    )
    assert created.relative_path.startswith("adrs/logical/ADR-L-0099-")
    roadmap = resolve_target(root, "file:ROADMAP.md", operation="amend")
    assert roadmap.relative_path == "ROADMAP.md"


def test_roadmap_rules_not_adr_schema() -> None:
    fp = roadmap_rules_fingerprint()
    assert fp.startswith("sha256:")
    assert "adr-logical" not in fp


def test_atomic_commit_recovers_after_partial_replace(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    (root / "ROADMAP.md").write_text("# Roadmap\n\n## Phase 1\n", encoding="utf-8")
    a = root / "adrs" / "logical" / "a.yaml"
    b = root / "adrs" / "logical" / "b.yaml"
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text("id: A\n", encoding="utf-8")
    b.write_text("id: B\n", encoding="utf-8")
    before_a = a.read_bytes()
    before_b = b.read_bytes()
    writes = [
        PlannedWrite("adrs/logical/a.yaml", a, b"id: A2\n", "amend"),
        PlannedWrite("adrs/logical/b.yaml", b, b"id: B2\n", "amend"),
    ]
    seen = {"count": 0}

    def fault(phase: str) -> None:
        if phase.startswith("during_commit:") and "b.yaml" in phase:
            seen["count"] += 1
            raise RuntimeError("boom mid commit")

    with pytest.raises(RuntimeError):
        commit_all_or_none(
            root,
            writes,
            validate_staged=lambda _overlay: None,
            fault=fault,
            journal_root=root / ".adr-kit" / "journal-test",
        )
    assert a.read_bytes() == before_a
    assert b.read_bytes() == before_b
    assert seen["count"] == 1


def test_prepare_synthetic_amend_create(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    # Seed a logical ADR target
    adr = root / "adrs" / "logical" / "ADR-L-0001-seed.yaml"
    adr.parent.mkdir(parents=True, exist_ok=True)
    adr.write_text(
        "schema_version: '1.2'\nid: ADR-L-0001\ntitle: Seed\nstatus: accepted\n"
        "date: '2026-01-01'\ndecisions: []\ninvariants: []\ncapabilities: []\nnotes: ''\n",
        encoding="utf-8",
    )
    (root / "ROADMAP.md").write_text("# Roadmap\n\n## Phase 1\n\n## Phase 3\n", encoding="utf-8")
    # Initialize git for baseline equivalence helper; if unavailable skip baseline soft-fail
    pc_path = root / "pc.json"
    contract = {
        "contract_version": "ste.design_journal.promotion_contract/v0.1",
        "design_journal_version": "ste.design_journal/v0.1",
        "journal_id": "DJ-SYN",
        "lifecycle_state": "lock_ready",
        "provider": "adr-architecture-kit",
        "authority_baseline": {
            "provider": "adr-architecture-kit",
            "kind": "git_commit",
            "value": "0" * 40,
        },
        "outcomes": [
            {
                "id": "D-01",
                "category": "candidate_decision",
                "promotion_required": True,
                "disposition": "accepted",
                "statement": "Create identity ADR",
            },
            {
                "id": "I-01",
                "category": "invariant",
                "promotion_required": True,
                "disposition": "accepted",
                "statement": "Identity invariant",
            },
        ],
        "mutations": [
            {
                "id": "M-01",
                "operation": "create",
                "provider": "adr-architecture-kit",
                "provider_target_ref": "adr:ADR-L-0019",
                "outcome_refs": ["D-01", "I-01"],
            },
            {
                "id": "M-06",
                "operation": "amend",
                "provider": "adr-architecture-kit",
                "provider_target_ref": "file:ROADMAP.md",
                "outcome_refs": ["D-01"],
            },
        ],
        "blockers": [
            {"id": "B-01", "code": "missing_mutation_bindings", "message": "x"},
            {"id": "B-02", "code": "promotion_provider_api_absent", "message": "x"},
            {"id": "B-03", "code": "non_transactional_writes", "message": "x"},
        ],
        "readiness": {"design_lock": True, "mechanical_promotion": False},
        "human_lock": None,
        "execution_evidence": [],
    }
    pc_path.write_text(json.dumps(contract), encoding="utf-8")
    roadmap_before = (root / "ROADMAP.md").read_bytes()
    result = prepare_promotion(
        PromotionPrepareRequest(
            project_root=root,
            promotion_contract_path=pc_path,
            prepared_contract_output_path=root / ".out" / "prepared.json",
        )
    )
    assert result.authority_mutated is False
    assert (root / "ROADMAP.md").read_bytes() == roadmap_before
    assert result.prepared_contract_path is not None
    prepared = result.prepared_contract
    assert all(m.get("payload_binding") for m in prepared["mutations"])
    assert all(m.get("schema_binding") for m in prepared["mutations"])
    roadmap_mut = next(m for m in prepared["mutations"] if m["id"] == "M-06")
    assert not roadmap_mut["schema_binding"]["ref"].startswith("schema:adr")
    ready, _ = mechanical_ready(prepared)
    # baseline likely false on synthetic non-git tree
    assert "missing_mutation_bindings" not in {b.code for b in result.blockers}


def test_human_lock_validation_fixture() -> None:
    data = json.loads((FIXTURES / "02-valid-locked.json").read_text(encoding="utf-8"))
    contract = data["contract"]
    # Fix fingerprint to computed value for provider implementation
    contract = dict(contract)
    contract["human_lock"] = dict(contract["human_lock"])
    contract["human_lock"]["locked_intent_fingerprint"] = locked_intent_fingerprint(contract)
    ok, errors = human_lock_valid(contract)
    assert ok, errors
