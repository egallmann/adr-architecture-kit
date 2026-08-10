"""RED/GREEN tests for scoped Design Journal → ADR amend candidate projection."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from adr_kit.compiler.frontend.support import classify_author_gap
from adr_kit.promotion.amendment_projection import (
    ANNOTATION_ONLY_MARKER,
    assert_amendment_embodied,
    reject_annotation_only_candidate,
)
from adr_kit.promotion.candidates import build_amend_post_image
from adr_kit.promotion.identity_v13 import (
    IDENTITY_V13_JOURNAL_ID,
    apply_identity_v13_amend,
    build_identity_v13_create_children,
    deferred_children_are_non_active,
)
from adr_kit.promotion.service import _build_post_images

REPO_ROOT = Path(__file__).resolve().parents[1]


def _minimal_adr_l0001() -> dict:
    return {
        "schema_version": "1.0",
        "id": "ADR-L-0001",
        "title": "Seed",
        "status": "accepted",
        "decisions": [
            {
                "id": "DEC-0004",
                "summary": "Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX) with 4-digit numbering",
                "rationale": "Graph clarity: node type obvious in queries",
                "alternatives_considered": [
                    {
                        "name": "UUID identifiers",
                        "rejected_because": (
                            "Not human-readable. Difficult to reference in conversation. "
                            "No semantic meaning. Poor for documentation."
                        ),
                    }
                ],
                "related_invariants": ["INV-0005"],
            }
        ],
        "interaction_contracts": [
            {
                "id": "CONTRACT-0001",
                "parties": ["adr-kit", "ste-runtime"],
                "protocol": "YAML",
                "guarantees": (
                    "ADR Kit guarantees:\n"
                    "- Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX)\n"
                    "- Parses YAML into graph nodes and edges\n"
                ),
            }
        ],
        "constraints": [
            {
                "id": "CONST-0002",
                "type": "technical",
                "description": "Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX) with 4-digit numbering.",
                "rationale": "Graph clarity (node type obvious in queries).",
            }
        ],
        "invariants": [
            {
                "id": "INV-0005",
                "statement": "ADR IDs must be unique across the project",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "automated",
                "rationale": (
                    "Graph node identity requires unique IDs. Collision breaks graph "
                    "traversal. Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX) prevent collision."
                ),
            }
        ],
        "capabilities": [{"id": "CAP-0001", "name": "Keep", "description": "unrelated"}],
        "notes": "",
    }


def _minimal_adr_l0012() -> dict:
    return {
        "schema_version": "1.0",
        "id": "ADR-L-0012",
        "title": "Federation",
        "status": "accepted",
        "context": (
            "Bare local IDs must evolve into an unambiguous multi-repository identity "
            "model without breaking single-repo authoring.\n\n"
            "What is needed is one explicit ADR that formalizes:\n"
            "1. Federation as a read-only aggregation step\n"
            "2. Provider-authoritative conflict resolution\n"
            "3. A qualified identity model with namespace separated from bare ID\n"
            "4. Bare local references remaining valid by default, with qualification only\n"
            "   when cross-repo references are intended\n"
        ),
        "decisions": [
            {
                "id": "DEC-0045",
                "summary": "Preserve read-only provider authority",
                "rationale": "unrelated preserve",
            },
            {
                "id": "DEC-0047",
                "summary": (
                    "Keep namespace separate from bare ID and use qualification only "
                    "for cross-repo references"
                ),
                "rationale": "bare ID local ergonomics + global qualification",
            },
            {
                "id": "DEC-0077",
                "summary": "Emit workspace-attribution-federation.yaml",
                "rationale": (
                    "keyed by qualified_id (workspaceRepoKey:ADR-L-XXXX) so homonymous "
                    "bare ids across repositories are never merged"
                ),
                "consequences": {
                    "negative": [
                        "Workspace manifest repo keys must remain stable for qualified_id namespaces"
                    ]
                },
            },
        ],
        "capabilities": [
            {
                "id": "CAP-0038",
                "name": "Federated Qualified Identity Resolution",
                "description": "preserving bare local references in source ADRs",
                "acceptance_criteria": [
                    "Bare local IDs remain valid within a repository",
                    "Cross-repo references use namespace-qualified identifiers",
                    "Provider repositories remain authoritative for their own entity definitions",
                ],
            }
        ],
        "invariants": [
            {
                "id": "INV-0058",
                "statement": "Provider remains authoritative",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "manual",
                "rationale": "preserve",
            }
        ],
    }


def _minimal_adr_l0013() -> dict:
    return {
        "schema_version": "1.0",
        "id": "ADR-L-0013",
        "title": "Repository boundary",
        "status": "accepted",
        "decisions": [
            {
                "id": "DEC-0050",
                "summary": "Use ArchitectureRepository as the supported in-process semantic entry point",
                "rationale": "repository seam",
            },
            {
                "id": "DEC-0051",
                "summary": "Expose a NormalizedArchitectureModel as the repository semantic payload",
                "rationale": "normalized model",
            },
            {
                "id": "DEC-0052",
                "summary": "Keep ArchModel compiler-internal",
                "rationale": "preserve unscoped",
            },
            {
                "id": "DEC-0080",
                "summary": "Establish adr_kit.api as the narrow supported authoring SDK facade",
                "rationale": "narrow facade",
            },
        ],
        "capabilities": [
            {
                "id": "CAP-0039",
                "name": "Stable Repository Semantic Boundary",
                "description": "stable normalized semantic model",
                "acceptance_criteria": ["load bundles into NormalizedArchitectureModel"],
            },
            {
                "id": "CAP-0047",
                "name": "Narrow Supported Authoring SDK",
                "description": (
                    "Provide a deterministic Python facade for validation, compilation, "
                    "repository loading, and capability discovery."
                ),
                "acceptance_criteria": [
                    "`adr_kit.api` exposes exactly the approved Phase 1 symbol inventory",
                    "validation and compilation return immutable public results",
                    "capability discovery is deterministic, local, resource-backed, and versioned",
                ],
            },
        ],
        "invariants": [
            {
                "id": "INV-0059",
                "statement": "Consumers use ArchitectureRepository",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "manual",
                "rationale": "preserve",
            }
        ],
        "notes": (
            "Explicitly deferred beyond Phase 1: graph bundles, assertion identity, "
            "entity/schema expansion, topology identity, bindings, transactional authoring, "
            "normalized-model expansion, Assembler, MCP, runtime extraction."
        ),
    }


def _minimal_adr_l0018() -> dict:
    return {
        "schema_version": "1.0",
        "id": "ADR-L-0018",
        "title": "Schema v1.2 foundation",
        "status": "accepted",
        "decisions": [
            {
                "id": "DEC-0084",
                "summary": "Represent external bindings as qualified references",
                "rationale": (
                    "Local entity references remain bare IDs. A cross-repository entity "
                    "reference is an object containing required namespace, id, kind, and fingerprint."
                ),
            },
            {
                "id": "DEC-0085",
                "summary": "Promote four types into normalized model version 1.1",
                "rationale": "model 1.1 is the expanded projectable vocabulary",
            },
            {
                "id": "DEC-0086",
                "summary": "Add assertion identity",
                "rationale": (
                    "assertion_id from relationship_type, from_entity_id, to_entity_id, "
                    "canonical_source_ref"
                ),
            },
            {
                "id": "DEC-0088",
                "summary": "Make ADR Kit exclusive repair authority for canonical entity-ID collisions",
                "rationale": "repair collisions by allocating next monotonic prefix IDs",
            },
        ],
        "invariants": [
            {
                "id": "INV-0079",
                "statement": "assertion_id using DEC-0086; relationship_id unchanged",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "automated",
                "rationale": "phase-2",
            },
            {
                "id": "INV-0081",
                "statement": "normalized projectable vocabulary MUST be exactly ten types",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "automated",
                "rationale": "phase-2",
            },
            {
                "id": "INV-0082",
                "statement": "ADR Kit MUST own detection and repair of canonical entity-ID collisions",
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "automated",
                "rationale": "repair",
            },
        ],
        "capabilities": [
            {
                "id": "CAP-0049",
                "name": "Expanded Normalized Semantic Model",
                "description": "reports schema version 1.1",
                "acceptance_criteria": ["reports schema version 1.1"],
            },
            {
                "id": "CAP-0052",
                "name": "Canonical Entity Identity Repair",
                "description": "collisions repaired via monotonic non-reusing allocation",
                "acceptance_criteria": ["auto-repair canonical entity-ID collisions"],
            },
        ],
    }


def _minimal_adr_l0016() -> dict:
    return {
        "schema_version": "1.0",
        "id": "ADR-L-0016",
        "title": "Orientation",
        "status": "accepted",
        "decisions": [
            {
                "id": "DEC-0069",
                "summary": "Extend ArchitectureRepository with deterministic orientation helpers",
                "rationale": "entity reference lookup and forward-authoring ID allocation",
            },
            {
                "id": "DEC-0073",
                "summary": "Make forward-authoring ADR ID allocation monotonic and non-reusable",
                "rationale": "ADR identifiers are architectural identity, not recyclable sequence numbers.",
            },
            {
                "id": "DEC-0075",
                "summary": "Exclude reserved ADR IDs 9000-9999 from standard forward allocation",
                "rationale": "preserved-identity range for exceptional records",
            },
        ],
        "capabilities": [
            {
                "id": "CAP-0045",
                "name": "Deterministic Corpus Orientation Surface",
                "description": "scope-local next ADR ID allocation",
                "acceptance_criteria": [
                    "normal-band ADR IDs allocate monotonically and never reused"
                ],
            }
        ],
        "invariants": [
            {
                "id": "INV-0069",
                "statement": (
                    "Forward-authoring ADR ID allocation MUST be monotonic and non-reusable."
                ),
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "automated",
                "rationale": "identity",
            },
            {
                "id": "INV-0071",
                "statement": (
                    "Reserved ADR IDs `9000-9999` MUST NOT participate in standard "
                    "forward authoring allocation."
                ),
                "scope": "global",
                "enforcement_level": "must",
                "enforcement_mechanism": "design",
                "verification_method": "automated",
                "rationale": "reserved",
            },
        ],
    }


def test_annotation_only_amendment_rejected() -> None:
    before = _minimal_adr_l0001()
    after = copy.deepcopy(before)
    after["notes"] = ANNOTATION_ONLY_MARKER
    with pytest.raises(ValueError, match="ANNOTATION_ONLY_AMENDMENT"):
        reject_annotation_only_candidate(before, after)
    errors = assert_amendment_embodied(
        mutation_id="M-02",
        before=before,
        after=after,
        journal_id=IDENTITY_V13_JOURNAL_ID,
    )
    assert errors
    assert any("ANNOTATION_ONLY" in item or "scoped amendment" in item.lower() for item in errors)


def test_m02_must_reframe_type_prefixed_as_alias(tmp_path: Path) -> None:
    path = tmp_path / "ADR-L-0001.yaml"
    before = _minimal_adr_l0001()
    path.write_text(yaml.safe_dump(before, sort_keys=False), encoding="utf-8")
    after = apply_identity_v13_amend("M-02", copy.deepcopy(before))
    text = yaml.safe_dump(after, sort_keys=False)
    assert "governed" in text.lower() and "alias" in text.lower()
    assert "canonical machine identity" in text.lower() or "uuid" in text.lower()
    dec = next(item for item in after["decisions"] if item["id"] == "DEC-0004")
    assert "alias" in dec["summary"].lower() or "alias" in dec["rationale"].lower()
    uuid_alt = next(item for item in dec["alternatives_considered"] if "UUID" in item["name"])
    assert "human" in uuid_alt["rejected_because"].lower()
    inv = next(item for item in after["invariants"] if item["id"] == "INV-0005")
    assert "graph node identity requires unique ids" not in inv["rationale"].lower()
    assert "alias" in inv["rationale"].lower()
    # annotation-only path must not satisfy embodiment
    annotation = yaml.safe_load(
        build_amend_post_image(path, set_fields={"notes": ANNOTATION_ONLY_MARKER})
    )
    errors = assert_amendment_embodied(
        mutation_id="M-02",
        before=before,
        after=annotation,
        journal_id=IDENTITY_V13_JOURNAL_ID,
    )
    assert errors


def test_m02_preserves_unrelated_capability() -> None:
    before = _minimal_adr_l0001()
    after = apply_identity_v13_amend("M-02", copy.deepcopy(before))
    assert after["capabilities"] == before["capabilities"]
    assert after["id"] == before["id"]
    assert after["title"] == before["title"]


def test_m03_federation_identity_reconciliation() -> None:
    before = _minimal_adr_l0012()
    after = apply_identity_v13_amend("M-03", copy.deepcopy(before))
    blob = yaml.safe_dump(after, sort_keys=False).lower()
    assert "architecture_namespace" in blob
    assert "uuid" in blob
    assert "pre-v1.3" in blob or "pre-v1.3" in after["context"].lower()
    dec77 = next(item for item in after["decisions"] if item["id"] == "DEC-0077")
    dec77_text = yaml.safe_dump(dec77, sort_keys=False).lower()
    assert "workspacerepokey:adr-l" not in dec77_text
    assert "routing" in dec77_text
    assert "architecture_namespace" in dec77_text
    # preserve unscoped
    assert next(item for item in after["decisions"] if item["id"] == "DEC-0045") == next(
        item for item in before["decisions"] if item["id"] == "DEC-0045"
    )
    assert next(item for item in after["invariants"] if item["id"] == "INV-0058") == next(
        item for item in before["invariants"] if item["id"] == "INV-0058"
    )


def test_m03_context_scopes_bare_local_to_prev13() -> None:
    """A-N2: bare-local default rule must not remain the active v1.3 context claim."""
    before = _minimal_adr_l0012()
    after = apply_identity_v13_amend("M-03", copy.deepcopy(before))
    context = str(after["context"])
    lowered = context.lower()
    # Active unscoped bare-local default must be gone.
    assert "bare local references remaining valid by default" not in lowered
    # Historical pre-v1.3 scoping and v1.3 UUID semantics must be present.
    assert "pre-v1.3" in lowered
    assert "uuid" in lowered
    assert "architecture_namespace" in lowered
    # Decisions remain consistent with context.
    dec47 = next(item for item in after["decisions"] if item["id"] == "DEC-0047")
    assert "uuid" in yaml.safe_dump(dec47, sort_keys=False).lower()
    # Unrelated decision preserved.
    assert next(item for item in after["decisions"] if item["id"] == "DEC-0045") == next(
        item for item in before["decisions"] if item["id"] == "DEC-0045"
    )


def test_m04_cap0047_reconciles_phase1_symbol_inventory() -> None:
    """A-N2: CAP-0047 must not timelessly freeze Phase 1 symbols after promotion SDK."""
    before = _minimal_adr_l0013()
    after = apply_identity_v13_amend("M-04", copy.deepcopy(before))
    cap47 = next(item for item in after["capabilities"] if item["id"] == "CAP-0047")
    criteria = "\n".join(str(item) for item in (cap47.get("acceptance_criteria") or [])).lower()
    blob = yaml.safe_dump(cap47, sort_keys=False).lower()
    assert "exactly the approved phase 1 symbol inventory" not in criteria
    assert "narrow" in before["capabilities"][1]["name"].lower()
    assert cap47["name"] == "Narrow Supported Authoring SDK"
    assert "promotion" in criteria or "promotion" in blob
    assert "authorized" in criteria or "supported public" in criteria
    assert "schema 1.3 is implemented" not in blob
    assert "normalized model 2.0 is implemented" not in blob
    assert "schema 1.3" not in blob
    assert "graphprojectionbundle" not in blob.replace(" ", "")
    # Unrelated ArchModel decision preserved.
    assert next(item for item in after["decisions"] if item["id"] == "DEC-0052") == next(
        item for item in before["decisions"] if item["id"] == "DEC-0052"
    )


def test_m05_v12_identity_reconciled_not_left_contradictory() -> None:
    before = _minimal_adr_l0018()
    after = apply_identity_v13_amend("M-05", copy.deepcopy(before))
    blob = yaml.safe_dump(after, sort_keys=False).lower()
    assert "model 2.0" in blob or "model-2.0" in blob
    assert "alias" in blob
    dec88 = next(item for item in after["decisions"] if item["id"] == "DEC-0088")
    text88 = yaml.safe_dump(dec88, sort_keys=False).lower()
    assert "uuid" in text88
    assert "fail closed" in text88 or "fail-closed" in text88
    cap52 = next(item for item in after["capabilities"] if item["id"] == "CAP-0052")
    assert "alias" in yaml.safe_dump(cap52, sort_keys=False).lower()


def test_m07_alias_allocation_not_machine_identity() -> None:
    before = _minimal_adr_l0016()
    after = apply_identity_v13_amend("M-07", copy.deepcopy(before))
    dec73 = next(item for item in after["decisions"] if item["id"] == "DEC-0073")
    text = yaml.safe_dump(dec73, sort_keys=False).lower()
    assert "alias" in text
    assert "architectural identity" not in text or "not canonical" in text
    dec69 = next(item for item in after["decisions"] if item["id"] == "DEC-0069")
    assert "uuid" in yaml.safe_dump(dec69, sort_keys=False).lower()


def test_complete_post_image_not_patch() -> None:
    before = _minimal_adr_l0001()
    after = apply_identity_v13_amend("M-02", copy.deepcopy(before))
    assert after.get("id") == "ADR-L-0001"
    assert isinstance(after.get("decisions"), list)
    assert isinstance(after.get("invariants"), list)
    assert isinstance(after.get("capabilities"), list)


def test_deferred_d12_i13_non_active_encoding() -> None:
    outcomes = [
        {
            "id": "D-12",
            "disposition": "deferred",
            "statement": (
                "V1.3 does not add canonical entity-level updated_at; deferred to "
                "transactional-authoring governance."
            ),
        },
        {
            "id": "I-13",
            "disposition": "deferred",
            "statement": (
                "The constraint that canonical updated_at cannot precede created_at "
                "is deferred and is not a v1.3 identity invariant."
            ),
        },
        {
            "id": "D-01",
            "disposition": "accepted",
            "statement": "UUID is canonical machine identity.",
        },
        {
            "id": "I-01",
            "disposition": "accepted",
            "statement": "Canonical machine identity is UUIDv7.",
        },
    ]
    decisions, invariants, gaps = build_identity_v13_create_children(
        outcomes,
        dec_ids=["DEC-9001", "DEC-9002"],
        inv_ids=["INV-9001", "INV-9002"],
    )
    assert deferred_children_are_non_active(decisions, invariants, gaps)
    d12 = next(item for item in decisions if "updated_at" in item["rationale"])
    assert "status" not in d12 or d12.get("status") != "accepted"
    assert "[DEFERRED v1.3]" not in d12.get("details", "")
    i13 = next(item for item in invariants if "updated_at" in item["statement"])
    assert i13["enforcement_level"] != "must"
    assert i13["enforcement_level"] == "may"
    assert any(
        classify_author_gap(type("G", (), gap)()) == "author_declared_deferred_gap" for gap in gaps
    )


def test_provider_amend_path_no_longer_annotation_only(tmp_path: Path) -> None:
    root = tmp_path / "project"
    adr_dir = root / "adrs" / "logical"
    adr_dir.mkdir(parents=True)
    path = adr_dir / "ADR-L-0001-seed.yaml"
    path.write_text(yaml.safe_dump(_minimal_adr_l0001(), sort_keys=False), encoding="utf-8")
    contract = {
        "journal_id": IDENTITY_V13_JOURNAL_ID,
        "outcomes": [
            {
                "id": "D-01",
                "statement": "UUID canonical",
                "disposition": "accepted",
                "promotion_required": True,
                "category": "candidate_decision",
            }
        ],
        "mutations": [
            {
                "id": "M-02",
                "operation": "amend",
                "provider_target_ref": "adr:ADR-L-0001",
                "outcome_refs": ["D-01"],
            }
        ],
    }
    images = _build_post_images(root, contract)
    _, content = images["M-02"]
    text = content.decode("utf-8")
    assert ANNOTATION_ONLY_MARKER not in text
    assert "alias" in text.lower()
    doc = yaml.safe_load(text)
    errors = assert_amendment_embodied(
        mutation_id="M-02",
        before=_minimal_adr_l0001(),
        after=doc,
        journal_id=IDENTITY_V13_JOURNAL_ID,
    )
    assert errors == []


def test_real_corpus_m02_projection_against_repo_authority() -> None:
    """Optional integration: project against real ADR-L-0001 when present."""
    path = next(
        (candidate for candidate in (REPO_ROOT / "adrs" / "logical").glob("ADR-L-0001-*.yaml")),
        None,
    )
    if path is None:
        pytest.skip("ADR-L-0001 not present")
    before = yaml.safe_load(path.read_text(encoding="utf-8"))
    after = apply_identity_v13_amend("M-02", copy.deepcopy(before))
    errors = assert_amendment_embodied(
        mutation_id="M-02",
        before=before,
        after=after,
        journal_id=IDENTITY_V13_JOURNAL_ID,
    )
    assert errors == []
    # Unscoped CAP-0001 description preserved
    before_cap = next(item for item in before["capabilities"] if item["id"] == "CAP-0001")
    after_cap = next(item for item in after["capabilities"] if item["id"] == "CAP-0001")
    assert before_cap == after_cap
