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
        "claims": "all_selected_system_definition_occurrences_including_native_fragments",
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
        ("scope", "claims", "physical_system_roots_only"),
        ("source_sets", "selected_existing", "E_must_equal_P"),
        ("source_sets", "request_basis", "all_provider_objects_are_request_roots"),
        ("source_sets", "unselected_system_claims", "ignore_claims_outside_B"),
        ("source_sets", "existing_member_checks", ["content_digest"]),
        ("source_sets", "new_candidates", "already_published_members_of_P"),
        ("source_sets", "new_candidate_comparison", "same_uuid_is_sufficient"),
        ("source_sets", "implicit_publication_or_overlay", True),
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
        "every native typed System fragment",
        "Reference-only fields and relationship endpoints are not defining occurrences",
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


def test_provider_inventory_and_minimal_request_basis_are_distinct_obligations() -> None:
    # These are proposal requirements, not a live membership/completeness verifier.
    s = policy()["source_sets"]
    assert s == {
        "provider_inventory": "complete_authenticated_P_independent_of_request_selection",
        "selected_existing": "E_is_a_qualified_subset_of_P_not_required_equal_P",
        "request_basis": "B_is_operation_selected_minimal_nonoverlapping_roots_not_all_P",
        "existing_member_checks": [
            "source_identity",
            "schema_and_selector",
            "snapshot_revision",
            "exact_original_bytes",
        ],
        "unselected_system_claims": "account_in_complete_P_even_when_outside_B",
        "new_candidates": "C_is_sealed_detached_source_not_prior_provider_membership",
        "new_candidate_comparison": "Unavailable_without_selected_candidate_to_provider_authority_and_evidence",
        "implicit_publication_or_overlay": False,
    }
    adr32 = yaml.safe_load(
        next((ROOT / "adrs/logical").glob("ADR-L-0032-*.yaml")).read_text(encoding="utf-8")
    )
    assert adr32["id"] in document()["related_adrs"]
    minimal = next(d for d in adr32["decisions"] if d["alias_id"] == "DEC-0254")
    assert "minimal non-overlapping source roots" in minimal["rationale"]
    assert "while remaining a candidate artifact" in minimal["rationale"]
    # Parent root coverage is not a mandate to import every provider member.
    assert "provider" not in minimal["rationale"]


@pytest.mark.parametrize(
    "omitted",
    ["source_identity", "schema_and_selector", "snapshot_revision", "exact_original_bytes"],
)
def test_existing_member_design_cannot_drop_an_exact_membership_commitment(omitted: str) -> None:
    original = policy()
    bad = copy.deepcopy(original)
    bad["source_sets"]["existing_member_checks"].remove(omitted)
    assert list(Draft202012Validator(closed(original)).iter_errors(bad))


def test_new_candidate_absence_is_not_membership_or_an_automatic_violation() -> None:
    text = document()["decisions"][0]["rationale"]
    for phrase in (
        "E may be a strict subset of P",
        "including unselected claims outside B",
        "absence from the prior snapshot is not by itself a violation",
        "MUST NOT be represented as existing membership or provider publication",
        "without that selected comparison authority and evidence",
    ):
        assert phrase.lower() in " ".join(text.split()).lower()
    assert policy()["source_sets"]["new_candidate_comparison"].startswith("Unavailable_")
    assert policy()["unit"]["creation_during_qualification"] is False
    assert policy()["unit"]["election"] is False


def test_actual_context_equality_prevents_cross_adr_descriptor_coalescence() -> None:
    p = policy()
    ownership = load_semantic_resource(p["reuse"]["ownership_resource"])
    row = next(r for r in ownership["rows"] if r["rule_id"] == p["reuse"]["ownership_rule"])
    schema = load_semantic_resource(row["source_schema"]["canonical_resource_key"])
    assert "system" in schema["required"]
    assert schema["properties"]["system"]["$ref"].endswith("#/definitions/system")
    assert "items" not in schema["properties"]["system"]
    assert schema["additionalProperties"] is False
    assert row["declaring_adr_identity_selector"] == "/id"
    fact = load_semantic_resource("architecture-interpretation/1.3/contextual-facts")["facts"][0]
    keys = fact["semantic_equality_fields"]
    assert "declaring_adr_id" in keys
    # Hypothetical equality counterexample only: these do not assert live authority,
    # complete scope, an established unit or a successful execution receipt.
    a = {
        "declaring_adr_id": "00000000-0000-7000-8000-000000000001",
        "declaring_adr_semantic_type": row["declaring_adr_semantic_type"],
        "status_semantic_field_key": row["status_semantic_field_key"],
        "ownership_rule.rule_id": row["rule_id"],
    }
    unselected_b = {**a, "declaring_adr_id": "00000000-0000-7000-8000-000000000002"}
    assert tuple(a[k] for k in keys) != tuple(unselected_b[k] for k in keys)
    assert (
        p["source_sets"]["unselected_system_claims"] == "account_in_complete_P_even_when_outside_B"
    )
    assert p["outcomes"]["conflicting_lifecycle_or_context"] == "Rejected"
    assert p["outcomes"]["unqualified_existing_unit"] == "Unavailable"


def test_positive_reference_reuse_is_not_a_second_descriptor_definition() -> None:
    reachability = policy()["reuse"]["reachability"]
    assert reachability == {
        "descriptor_shape": "one_required_direct_system_object_per_physical_system_ADR",
        "distinct_declaring_ADRs_equal_context": False,
        "positive_case": "repeat_reference_or_reverification_same_qualified_unit_no_new_definition",
        "duplicate_definitions_permitted": False,
        "cross_ADR_capability": "human_decision_if_required_not_admitted_here",
    }
    assert policy()["reuse"]["second_unit_or_owner"] is False
    text = " ".join(document()["decisions"][2]["rationale"].split())
    for phrase in (
        "They cannot satisfy the exact contextual equality",
        "same already-established source occurrence and typed unit",
        "does not acquire a new declaring lifecycle",
        "not two distinct declaring ADRs",
        "unresolved human architectural decision",
    ):
        assert phrase in text


def test_authority_shape_does_not_claim_provider_or_rust_implementation() -> None:
    assert policy()["execution_prerequisites"] == [
        "accepted_decision_and_independently_qualified_candidate_authority",
        "implemented_authenticated_complete_provider_snapshot_capability",
        "independently_qualified_prior_System_unit_and_defining_producer",
        "implemented_private_scope_unit_and_output_verifiers",
        "selected_candidate_to_provider_comparison_when_new_candidate_claims_are_involved",
    ]
    text = " ".join(document()["decisions"][5]["rationale"].split())
    assert "AI/ACC candidate revision alone cannot make System executable" in text
    assert "No existing provider path inspected supplies the complete handoff" in text
    assert "baseline observation, not a permanent prohibition" in text
    assert "design audits, not evidence of a live provider" in text
