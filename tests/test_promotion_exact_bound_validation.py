"""RED/GREEN tests for exact-bound promotion candidate validation parity."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from adr_kit.api import PromotionPrepareRequest, prepare_promotion
from adr_kit.promotion.candidate_validation import (
    default_create_adr_authors,
    validate_adr_payload_bytes,
)
from adr_kit.promotion.candidates import build_create_adr_post_image
from adr_kit.promotion.ste_contract import mechanical_ready
from tests.test_architecture_index_generator import _create_fixture


def test_default_create_authors_comes_from_scaffold_convention() -> None:
    authors = default_create_adr_authors()
    assert authors == ["adr-architecture-kit"]
    assert all(isinstance(item, str) and item for item in authors)


def test_create_post_image_without_authors_fails_canonical_validator() -> None:
    # Reproduce the exact Leg B failure class: final bytes missing required authors.
    text = build_create_adr_post_image(
        adr_id="ADR-L-0099",
        title="Canonical Entity Identity",
        decisions=[
            {
                "id": "DEC-0001",
                "summary": "example decision",
                "rationale": "example rationale for schema completeness",
            }
        ],
        invariants=[
            {
                "id": "INV-0001",
                "statement": "example invariant",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "manual",
                "rationale": "example",
            }
        ],
    )
    doc = yaml.safe_load(text)
    # Force the historical omission if construction already fixed.
    doc.pop("authors", None)
    broken = yaml.safe_dump(doc, sort_keys=False)
    errors = validate_adr_payload_bytes(
        broken.encode("utf-8"),
        relative_path="adrs/logical/ADR-L-0099-canonical-entity-identity.yaml",
    )
    assert errors
    assert any("authors" in item.lower() for item in errors)


def test_create_post_image_with_required_metadata_passes_canonical_validator() -> None:
    text = build_create_adr_post_image(
        adr_id="ADR-L-0099",
        title="Canonical Entity Identity",
        decisions=[
            {
                "id": "DEC-0001",
                "summary": "example decision",
                "rationale": "example rationale for schema completeness",
            }
        ],
        invariants=[
            {
                "id": "INV-0001",
                "statement": "example invariant",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "manual",
                "rationale": "example",
            }
        ],
        authors=default_create_adr_authors(),
    )
    doc = yaml.safe_load(text)
    assert doc["authors"] == ["adr-architecture-kit"]
    assert isinstance(doc.get("context"), str) and doc["context"].strip()
    errors = validate_adr_payload_bytes(
        text.encode("utf-8"),
        relative_path="adrs/logical/ADR-L-0099-canonical-entity-identity.yaml",
    )
    assert errors == []


def test_prepare_rejects_create_payload_missing_authors(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    (root / "ROADMAP.md").write_text("# Roadmap\n\n## Phase 1\n\n## Phase 3\n", encoding="utf-8")
    # Seed PROJECT.yaml so overlay validation paths resembling production work.
    if not (root / "PROJECT.yaml").exists():
        (root / "PROJECT.yaml").write_text(
            "schema_version: '1.0'\ntype: project_metadata\n", encoding="utf-8"
        )

    # Monkeypatch create builder path by writing a broken payload through a local
    # prepare contract that targets ADR-L-0019 create with minimal outcomes.
    # The production builder must refuse to mark such a candidate valid.
    from adr_kit.promotion import candidates as candidates_mod
    from adr_kit.promotion import service as service_mod

    original = candidates_mod.build_create_adr_post_image

    def broken_create(**kwargs):  # type: ignore[no-untyped-def]
        text = original(**kwargs)
        doc = yaml.safe_load(text)
        doc.pop("authors", None)
        return yaml.safe_dump(doc, sort_keys=False)

    candidates_mod.build_create_adr_post_image = broken_create  # type: ignore[assignment]
    service_mod.build_create_adr_post_image = broken_create  # type: ignore[assignment]
    try:
        pc = root / "pc.json"
        contract = {
            "contract_version": "ste.design_journal.promotion_contract/v0.1",
            "design_journal_version": "ste.design_journal/v0.1",
            "journal_id": "DJ-VAL-PARITY",
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
                }
            ],
            "blockers": [],
            "readiness": {"design_lock": True, "mechanical_promotion": False},
            "human_lock": None,
            "execution_evidence": [],
        }
        pc.write_text(json.dumps(contract), encoding="utf-8")
        result = prepare_promotion(
            PromotionPrepareRequest(
                project_root=root,
                promotion_contract_path=pc,
                prepared_contract_output_path=root / ".out" / "prepared.json",
            )
        )
        prepared = result.prepared_contract
        mutation = prepared["mutations"][0]
        assert mutation["validation_evidence"]["result"] == "invalid"
        ready, _ = mechanical_ready(prepared)
        assert ready is False
        assert result.mechanical_promotion_ready is False
        assert any(
            "authors" in (b.message or "").lower() or b.code == "candidate_validation_failure"
            for b in result.blockers
        ) or any(
            item.get("code") == "candidate_validation_failure"
            for item in prepared.get("blockers", [])
        )
    finally:
        candidates_mod.build_create_adr_post_image = original  # type: ignore[assignment]
        service_mod.build_create_adr_post_image = original  # type: ignore[assignment]


def test_prepare_create_emits_authors_and_valid_evidence(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    (root / "ROADMAP.md").write_text("# Roadmap\n\n## Phase 1\n\n## Phase 3\n", encoding="utf-8")
    pc = root / "pc.json"
    contract = {
        "contract_version": "ste.design_journal.promotion_contract/v0.1",
        "design_journal_version": "ste.design_journal/v0.1",
        "journal_id": "DJ-VAL-PARITY-OK",
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
            }
        ],
        "blockers": [],
        "readiness": {"design_lock": True, "mechanical_promotion": False},
        "human_lock": None,
        "execution_evidence": [],
    }
    pc.write_text(json.dumps(contract), encoding="utf-8")
    result = prepare_promotion(
        PromotionPrepareRequest(
            project_root=root,
            promotion_contract_path=pc,
            prepared_contract_output_path=root / ".out" / "prepared.json",
        )
    )
    prepared = result.prepared_contract
    mutation = next(m for m in prepared["mutations"] if m["id"] == "M-01")
    payload = (root / ".adr-kit" / "promotion" / mutation["payload_binding"]["ref"]).read_bytes()
    doc = yaml.safe_load(payload)
    assert doc["authors"] == ["adr-architecture-kit"]
    assert isinstance(doc.get("context"), str) and doc["context"].strip()
    assert mutation["validation_evidence"]["result"] == "valid"
    assert (
        mutation["validation_evidence"]["payload_fingerprint"]
        == mutation["payload_binding"]["fingerprint"]
    )
    # Exact bound bytes must pass the same canonical validator.
    assert (
        validate_adr_payload_bytes(
            payload,
            relative_path="adrs/logical/ADR-L-0019-canonical-entity-identity.yaml",
        )
        == []
    )
