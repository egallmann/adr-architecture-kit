"""Audit the proposed System boundary; these tests do not qualify provider evidence."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import load_semantic_resource
from adr_kit.validators.adr_validator import ADRValidator

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "adrs/logical/ADR-L-0041-qualified-shared-system-scope-and-producer-evidence.yaml"


def document() -> dict[str, Any]:
    return yaml.safe_load(ADR.read_text(encoding="utf-8"))


def policy() -> dict[str, Any]:
    rationale = document()["decisions"][3]["rationale"]
    return yaml.safe_load(rationale.split("```yaml\n", 1)[1].split("```", 1)[0])


def closed(value: Any) -> dict[str, Any]:
    """Closed design-summary shape, not an instance evidence schema/verifier."""
    if isinstance(value, dict):
        return {
            "type": "object",
            "required": list(value),
            "additionalProperties": False,
            "properties": {k: closed(v) for k, v in value.items()},
        }
    return {"const": value}


def test_governed_identity_and_acceptance_boundary() -> None:
    adr = document()
    validation = ADRValidator(project_root=ROOT).validate_file(ADR, mode="complete")
    assert validation.valid, validation.errors
    assert adr["alias_id"] == "ADR-L-0041"
    assert [d["alias_id"] for d in adr["decisions"]] == [f"DEC-{n}" for n in range(9029, 9035)]
    assert [i["alias_id"] for i in adr["invariants"]] == [f"INV-{n:04}" for n in range(321, 327)]
    ids = [adr["id"], *(d["id"] for d in adr["decisions"]), *(i["id"] for i in adr["invariants"])]
    assert len(set(ids)) == 13
    governance = adr.get("governance") or {}
    if adr["status"] == "proposed":
        assert not governance.get("approved_by") and not governance.get("approved_date")
    elif adr["status"] == "accepted":
        # Authentic acceptance is checked by repository governance, not these strings.
        assert governance.get("approved_by") and governance.get("approved_date")


def test_scope_design_requires_independent_complete_enumeration_and_reuse_only() -> None:
    p = policy()
    assert p["boundary"] == "reuse_only_no_unit_creation"
    assert p["scope"] == {
        "owner": "independently_authorized_namespace_provider",
        "extent": "entire_authoritative_architecture_source_collection_for_namespace",
        "snapshot": "immutable_complete_content_addressed_object_graph",
        "root_authority": "independently_authenticated_provider_publication_binding",
        "enumeration": "independent_exhaustive_expansion_of_every_committed_child_edge",
        "claims": "all_schema_qualified_physical_system_roots_and_their_system_objects",
        "filters": "none_by_status_path_alias_uuid_or_requested_selection",
        "partial_or_unavailable": "Unavailable",
    }
    assert p["unit"]["identity"] == ["architecture_namespace", "canonical_uuidv7"]
    assert p["unit"]["establishment"] == "preexisting_owning_provider_canonical_unit_binding"
    assert p["unit"]["designation"] == "exactly_one_provider_authorized_defining_source_occurrence"
    assert p["unit"]["creation_during_qualification"] is False
    assert p["unit"]["election"] is False
    assert p["reuse"]["second_unit_or_owner"] is False
    assert (
        p["reuse"]["comparison"] == "all_governed_semantic_values_and_applicable_contextual_facts"
    )
    assert set(p["evidence_bindings"]) == {
        "provider_namespace_and_scope_authorization",
        "authenticated_snapshot_root_and_revision",
        "complete_source_object_membership",
        "original_bytes_digests_and_source_schema_identities",
        "preexisting_typed_unit_and_authorized_defining_occurrence",
        "all_descriptor_claims_and_literal_declaring_context",
        "exact_nm_ai_acc_definitions_resources_and_scfs",
    }


@pytest.mark.parametrize(
    ("section", "key", "replacement"),
    [
        ("scope", "owner", "caller"),
        ("scope", "extent", "request_bundle"),
        ("scope", "snapshot", "mutable_directory"),
        ("scope", "root_authority", "producer_signature"),
        ("scope", "enumeration", "validate_supplied_digests"),
        ("scope", "filters", "requested_uuid"),
        ("unit", "creation_during_qualification", True),
        ("unit", "designation", "first_seen"),
        ("unit", "election", True),
        ("unit", "semantic_type", "adr/physical-system"),
        ("reuse", "comparison", "labels_and_uuid"),
        ("reuse", "second_unit_or_owner", True),
        ("outcomes", "competing_authorized_definitions", "reuse_existing_unit_only"),
        ("outcomes", "conflicting_lifecycle_or_context", "Unavailable"),
        ("outcomes", "missing_or_stale_scope", "Unresolved"),
        ("outcomes", "partial_or_unsupported_provider", "eligible_for_bounded_execution"),
    ],
)
def test_design_mutations_cannot_relax_declared_requirements(
    section: str, key: str, replacement: Any
) -> None:
    original = policy()
    bad = copy.deepcopy(original)
    bad[section][key] = replacement
    # This audits mutations of proposed requirements, never actual scope or signatures.
    assert list(Draft202012Validator(closed(original)).iter_errors(bad))


def test_missing_extra_and_forged_design_evidence_are_not_allowed() -> None:
    original = policy()
    for key in original:
        bad = copy.deepcopy(original)
        del bad[key]
        assert list(Draft202012Validator(closed(original)).iter_errors(bad))
    for key in ("complete", "preferred_producer", "verified", "Constructed"):
        bad = copy.deepcopy(original)
        bad[key] = True
        assert list(Draft202012Validator(closed(original)).iter_errors(bad))


def test_actual_inherited_containment_context_and_candidate_prerequisites() -> None:
    p = policy()
    ownership = load_semantic_resource(p["reuse"]["ownership_resource"])
    row = next(r for r in ownership["rows"] if r["rule_id"] == p["reuse"]["ownership_rule"])
    assert row["shared_system_descriptor"] == p["reuse"]["rule"]
    assert row["source_instance_pattern"] == "/system" == p["unit"]["defining_pointer"]
    assert row["child_semantic_type"] == p["unit"]["semantic_type"]
    assert row["ownership_schema_path"][0]["schema_pointer"] == "/properties/system"
    schema = load_semantic_resource(row["source_schema"]["canonical_resource_key"])
    assert "system" in schema["required"]
    child = load_semantic_resource(row["child_schema"]["canonical_resource_key"])
    assert child["definitions"]["system"]["type"] == "object"
    context = load_semantic_resource("architecture-interpretation/1.3/detached-context")
    assert "scope_completeness" not in context
    assert context["provider_kind"] == "adr-kit-detached-candidate"


def test_outcomes_and_future_dependency_boundary_are_explicit() -> None:
    outcomes = policy()["outcomes"]
    assert outcomes == {
        "unique_qualified_definition": "eligible_for_bounded_execution",
        "compatible_additional_descriptor": "reuse_existing_unit_only",
        "conflicting_canonical_values": "Rejected",
        "conflicting_lifecycle_or_context": "Rejected",
        "competing_authorized_definitions": "Rejected",
        "missing_or_stale_scope": "Unavailable",
        "unqualified_existing_unit": "Unavailable",
        "distinct_canonical_uuids": "distinct_units",
        "partial_or_unsupported_provider": "Unavailable",
        "forged_or_substituted_evidence": "Rejected",
        "stale_result_against_changed_qualified_snapshot": "Rejected",
    }
    text = " ".join(" ".join(d["rationale"] for d in document()["decisions"]).split())
    for phrase in (
        "separately governed dependency",
        "Rejected > Unavailable > Unresolved",
        "AI 1.3",
        "provider-context branch",
        "all 215 static BLOCKED statuses",
        "NM 2.5",
        "Authoring 1.7",
        "candidate SCFs",
        "without increasing versions",
        "No latest or ambient lookup",
        "System producer supplies outputs only",
        "Human acceptance is a prerequisite",
        "independently qualified Data Flow/Boundary",
    ):
        assert phrase in text
