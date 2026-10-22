use super::super::tests::{bundle, fixture, j, request};
use super::*;
use crate::authoring_construction_orchestration::EntropyUuidV7Minter;
use serde_json::{json, Value};

#[test]
fn canonical_identity_claims_are_reconciled_across_candidate_and_reference_bases() {
    let mut input = request(&fixture(1));
    existing(&mut input);
    input["basis"]["reference_basis"]["entries"][0]["canonical_uuid"] =
        input["request"]["fragments"][1]["fields"]["id"].clone();
    refs(
        &mut input,
        json!([
            reference("local", "request", "child"),
            reference("external", "existing", "external")
        ]),
    );
    passed(&run(&input)); // Multiple selectors for one consistent identity are valid.
    input["basis"]["reference_basis"]["entries"][0]["semantic_type"] = json!("entity/invariant");
    let result = run(&input);
    failed(&result, DependencyStatus::Rejected);
    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.field_or_relation_key == "canonical_identity"));
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    assert_eq!(run(&input), result);
}

#[test]
fn contradictory_existing_claims_fail_even_with_distinct_selectors() {
    for field in ["semantic_type", "existence_state", "qualification"] {
        let mut input = request(&fixture(1));
        let mut conflicting = existing(&mut input);
        conflicting["reference_id"] = json!("second");
        match field {
            "semantic_type" => conflicting[field] = json!("entity/invariant"),
            "existence_state" => conflicting[field] = json!("retired"),
            _ => {
                conflicting[field]["resources"][0]["content_digest"] =
                    json!(format!("sha256:{}", "0".repeat(64)))
            }
        }
        input["basis"]["reference_basis"]["entries"]
            .as_array_mut()
            .unwrap()
            .push(conflicting);
        refs(
            &mut input,
            json!([reference("external", "existing", "external")]),
        );
        let result = run(&input);
        failed(&result, DependencyStatus::Rejected);
        input["basis"]["reference_basis"]["entries"]
            .as_array_mut()
            .unwrap()
            .reverse();
        assert_eq!(run(&input), result);
    }
}

fn prepared(input: &Value) -> (InsertionResult, AccountingResult) {
    let p = insertion::insert(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &j(input),
        &mut EntropyUuidV7Minter::new(Some(1_767_000_000_123), Some([0x55; 32])),
    );
    let refs = p
        .materials
        .keys()
        .map(|k| (k.clone(), format!("candidate/{k}")))
        .collect();
    let roots = sources::prepare(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &p,
        &refs,
    );
    (p, roots)
}
fn run(input: &Value) -> DependencyResult {
    let (p, roots) = prepared(input);
    let before = (p.clone(), roots.clone());
    let result = qualify_dependencies(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &p,
        &roots,
    );
    assert_eq!(
        (p, roots),
        before,
        "dependency execution mutated insertion or artifacts/root proof"
    );
    result
}
fn reference(key: &str, kind: &str, target: &str) -> Value {
    json!({"reference_key":key,"reference_kind":kind,"target":target})
}
fn existing(input: &mut Value) -> Value {
    let entry = json!({"reference_id":"external","canonical_uuid":"01900000-0000-7000-8000-000000000099","semantic_kind":"entity","semantic_type":"entity/decision","qualification":input["basis"]["authoring"],"existence_state":"active"});
    input["basis"]["reference_basis"]["entries"] = json!([entry]);
    entry
}
fn refs(input: &mut Value, values: Value) {
    input["request"]["fragments"][0]["references"] = values;
}
fn failed(result: &DependencyResult, status: DependencyStatus) {
    assert_eq!(result.status, status, "{result:#?}");
    assert!(result.references.is_empty());
    assert!(!result.relationships_explicitly_empty && !result.memberships_explicitly_empty);
    assert!(result
        .outstanding_dependencies
        .contains("non_composition_reference_and_relationship_resolution"));
}
fn passed(result: &DependencyResult) {
    assert_eq!(
        result.status,
        DependencyStatus::DependenciesQualified,
        "{result:#?}"
    );
    assert!(result.diagnostics.is_empty() && result.pending.is_empty());
    assert_eq!(
        text(
            at(result.authority.as_ref().unwrap(), &["acc"]),
            "semantic_contract_fingerprint"
        ),
        SCF
    );
    assert!(!result
        .outstanding_dependencies
        .contains("non_composition_reference_and_relationship_resolution"));
    for obligation in [
        "complete_composition_evidence",
        "composed_candidate_basis_sealing",
        "complete_construction_qualification",
    ] {
        assert!(result.outstanding_dependencies.contains(obligation));
    }
}

#[test]
fn empty_collections_are_explicitly_executed_not_presumed_complete() {
    let result = run(&request(&fixture(1)));
    passed(&result);
    assert_eq!(result.references.len(), 2);
    assert!(result
        .references
        .iter()
        .all(|c| c.explicitly_empty && c.resolved_references.as_array().unwrap().is_empty()));
    assert!(result.relationships_explicitly_empty && result.memberships_explicitly_empty);
}

#[test]
fn exact_local_and_active_existing_references_have_acc_shaped_auditable_records() {
    let mut input = request(&fixture(1));
    existing(&mut input);
    let mut local = reference("local", "request", "child");
    local["expected_semantic_type"] = json!("entity/decision");
    local["qualification"] = input["basis"]["authoring"].clone();
    refs(
        &mut input,
        json!([local, reference("external", "existing", "external")]),
    );
    input["request"]["fragments"][1]["references"] =
        json!([reference("back", "request", "parent")]);
    let result = run(&input);
    passed(&result);
    let source = result
        .references
        .iter()
        .find(|r| r.source_request_key == "parent")
        .unwrap();
    assert!(!source.explicitly_empty);
    let records = source.resolved_references.as_array().unwrap();
    assert_eq!(records.len(), 2);
    assert_eq!(text(&records[0], "disposition"), "reused");
    assert_eq!(
        text(&records[0], "canonical_uuid"),
        "01900000-0000-7000-8000-000000000099"
    );
    assert_eq!(text(&records[1], "disposition"), "resolved");
    assert_eq!(
        text(&records[1], "canonical_uuid"),
        "01900000-0000-7000-8000-000000000002"
    );
    for basis in &source.governing_basis {
        assert_eq!(text(basis, "acc_fingerprint"), SCF);
        assert_eq!(array(basis, "authority_resources").len(), 2);
        assert!(basis
            .get("adc_reference_policy")
            .unwrap()
            .as_object()
            .is_some());
    }
}

#[test]
fn request_and_existing_targets_have_no_alias_uuid_path_or_composition_fallback() {
    for kind in ["request", "existing"] {
        for target in [
            "missing",
            "choice",
            "DEC-0001",
            "candidate/child",
            "01900000-0000-7000-8000-000000000002",
        ] {
            let mut input = request(&fixture(1));
            existing(&mut input);
            refs(&mut input, json!([reference("r", kind, target)]));
            let result = run(&input);
            failed(&result, DependencyStatus::Unresolved);
            assert!(result
                .diagnostics
                .iter()
                .any(|d| d.code == "authoring_construction.reference.unresolved"));
        }
    }
}

#[test]
fn duplicate_reference_keys_and_nonunique_existing_targets_fail_closed() {
    let mut input = request(&fixture(1));
    let entry = existing(&mut input);
    refs(
        &mut input,
        json!([
            reference("same", "request", "child"),
            reference("same", "existing", "external")
        ]),
    );
    let result = run(&input);
    failed(&result, DependencyStatus::Rejected);
    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.code.ends_with("duplicate_key")));
    refs(
        &mut input,
        json!([reference("unique", "existing", "external")]),
    );
    input["basis"]["reference_basis"]["entries"] = json!([entry.clone(), entry]);
    failed(&run(&input), DependencyStatus::Unresolved);
    let mut local = request(&fixture(1));
    let duplicate = local["request"]["fragments"][1].clone();
    local["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .push(duplicate);
    failed(&run(&local), DependencyStatus::Rejected);
}

#[test]
fn expectations_and_target_qualification_are_independent_violations() {
    let mut input = request(&fixture(1));
    existing(&mut input);
    let mut r = reference("r", "existing", "external");
    r["expected_semantic_type"] = json!("entity/invariant");
    refs(&mut input, json!([r.clone()]));
    failed(&run(&input), DependencyStatus::Rejected);
    r.as_object_mut().unwrap().remove("expected_semantic_type");
    r["qualification"] = input["basis"]["authoring"].clone();
    r["qualification"]["resources"][0]["content_digest"] =
        json!(format!("sha256:{}", "0".repeat(64)));
    refs(&mut input, json!([r]));
    failed(&run(&input), DependencyStatus::Rejected);
    refs(&mut input, json!([reference("r", "existing", "external")]));
    input["basis"]["reference_basis"]["entries"][0]["qualification"]["resources"][0]
        ["content_digest"] = json!(format!("sha256:{}", "0".repeat(64)));
    failed(&run(&input), DependencyStatus::Unavailable);
    input["request"]["fragments"][0]["references"][0]["expected_semantic_type"] =
        json!("entity/invariant");
    input["request"]["fragments"][0]["references"]
        .as_array_mut()
        .unwrap()
        .push(reference("missing", "request", "absent"));
    let result = run(&input);
    failed(&result, DependencyStatus::Rejected);
    let statuses: BTreeSet<_> = result.diagnostics.iter().map(|d| d.status).collect();
    assert_eq!(
        statuses,
        BTreeSet::from([Status::Rejected, Status::Unavailable, Status::Unresolved])
    );
}

#[test]
fn invalid_identity_state_kind_and_unimplemented_target_categories_are_distinct() {
    for field in ["canonical_uuid", "existence_state"] {
        let mut input = request(&fixture(1));
        existing(&mut input);
        refs(&mut input, json!([reference("r", "existing", "external")]));
        input["basis"]["reference_basis"]["entries"][0][field] = json!("invalid");
        failed(&run(&input), DependencyStatus::Rejected);
    }
    for (field, value, status) in [
        ("existence_state", "retired", DependencyStatus::Unavailable),
        ("semantic_kind", "adr", DependencyStatus::Rejected),
        (
            "semantic_type",
            "example:custom",
            DependencyStatus::Unavailable,
        ),
        (
            "semantic_type",
            "relationship/calls",
            DependencyStatus::Rejected,
        ),
    ] {
        let mut input = request(&fixture(1));
        existing(&mut input);
        refs(&mut input, json!([reference("r", "existing", "external")]));
        input["basis"]["reference_basis"]["entries"][0][field] = json!(value);
        failed(&run(&input), status);
    }
    let mut input = request(&fixture(1));
    existing(&mut input);
    refs(&mut input, json!([reference("r", "existing", "external")]));
    input["basis"]["reference_basis"]["entries"][0]["semantic_type"] = json!("relationship/calls");
    input["basis"]["reference_basis"]["entries"][0]["semantic_kind"] = json!("relationship");
    failed(&run(&input), DependencyStatus::Unavailable);
}

#[test]
fn source_descriptor_integrity_is_checked_even_for_unused_basis_entries() {
    let mut input = request(&fixture(1));
    existing(&mut input);
    input["basis"]["reference_basis"]["entries"][0]["source_basis"] = json!({"source_ref":"opaque","source_bytes":"eA==","content_digest":format!("sha256:{:x}",Sha256::digest(b"x"))});
    refs(&mut input, json!([reference("r", "existing", "external")]));
    passed(&run(&input));
    input["basis"]["reference_basis"]["entries"][0]["source_basis"]["content_digest"] =
        json!(format!("sha256:{}", "0".repeat(64)));
    refs(&mut input, json!([]));
    let result = run(&input);
    failed(&result, DependencyStatus::Rejected);
    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.code == "authoring_construction.basis.exact_source_digest"));
}

#[test]
fn request_resource_and_reference_array_permutations_preserve_evidence_and_diagnostics() {
    let mut input = request(&fixture(2));
    let entry = existing(&mut input);
    let mut another = entry;
    another["reference_id"] = json!("another");
    input["basis"]["reference_basis"]["entries"]
        .as_array_mut()
        .unwrap()
        .push(another);
    refs(
        &mut input,
        json!([
            reference("b", "existing", "external"),
            reference("a", "request", "child")
        ]),
    );
    let good = run(&input);
    passed(&good);
    fn permute(input: &mut Value) {
        for f in input["request"]["fragments"].as_array_mut().unwrap() {
            f["references"].as_array_mut().unwrap().reverse();
            f["contract_qualification"]["resources"]
                .as_array_mut()
                .unwrap()
                .reverse();
        }
        input["request"]["fragments"]
            .as_array_mut()
            .unwrap()
            .reverse();
        input["request"]["compositions"]
            .as_array_mut()
            .unwrap()
            .reverse();
        input["basis"]["authoring"]["resources"]
            .as_array_mut()
            .unwrap()
            .reverse();
        for e in input["basis"]["reference_basis"]["entries"]
            .as_array_mut()
            .unwrap()
        {
            e["qualification"]["resources"]
                .as_array_mut()
                .unwrap()
                .reverse();
        }
        input["basis"]["reference_basis"]["entries"]
            .as_array_mut()
            .unwrap()
            .reverse();
    }
    permute(&mut input);
    assert_eq!(run(&input), good);
    let parent = input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|f| f["request_key"] == "parent")
        .unwrap();
    parent["references"].as_array_mut().unwrap().extend([
        reference("missing", "existing", "absent"),
        reference("a", "request", "child"),
    ]);
    let bad = run(&input);
    failed(&bad, DependencyStatus::Rejected);
    permute(&mut input);
    assert_eq!(run(&input), bad);
}

#[test]
fn relationships_and_additional_memberships_are_inspected_independently() {
    let mut input = request(&fixture(1));
    input["request"]["relationships"] = json!([{"relationship_key":"calls","relationship_type":"relationship/calls","source":{"kind":"request","target":"parent"},"target":{"kind":"request","target":"child"},"fields":{},"qualification":input["basis"]["authoring"]}]);
    let result = run(&input);
    failed(&result, DependencyStatus::Unavailable);
    assert_eq!(result.pending.len(), 1);
    assert_eq!(result.pending[0].authority, Check::Qualified);
    input["request"]["relationships"][0]["relationship_type"] = json!("relationship/unknown");
    let result = run(&input);
    failed(&result, DependencyStatus::Unavailable);
    assert_eq!(result.pending[0].authority, Check::Unavailable);
    input["request"]["fragments"][0]["fields"]["capabilities"] = json!([{"id":"01900000-0000-7000-8000-000000000088","alias_id":"CAP-0001","alias_name":"other","name":"Other","description":"Other authored unit"}]);
    let mut r = reference("wrong", "request", "child");
    r["expected_semantic_type"] = json!("adr/logical");
    refs(&mut input, json!([r]));
    let result = run(&input);
    failed(&result, DependencyStatus::Rejected);
    assert!(result
        .pending
        .iter()
        .any(|p| p.category == "membership" && p.authority == Check::Qualified));
    assert!(result.pending.iter().any(|p| p.category == "relationship"));
    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.code.ends_with("expectation_mismatch")));
}

#[test]
fn proof_tampering_and_unsealed_basis_cannot_create_dependency_completion() {
    let input = request(&fixture(1));
    let (p, good) = prepared(&input);
    for variant in 0..5 {
        let mut roots = good.clone();
        match variant {
            0 => roots.accounting.clear(),
            1 => roots.artifacts[0].bytes.push(b' '),
            2 => roots
                .selected_root_source_refs
                .push("candidate/child".into()),
            3 => roots.outstanding_dependencies.clear(),
            _ => roots.status = AccountingStatus::Unavailable,
        }
        let r = qualify_dependencies(
            &j(&bundle().0),
            &bundle().1.iter().map(j).collect::<Vec<_>>(),
            &p,
            &roots,
        );
        failed(
            &r,
            if variant == 4 {
                DependencyStatus::Unavailable
            } else {
                DependencyStatus::Rejected
            },
        );
    }
    let mut input = input;
    input["basis"]["reference_basis"]["sealed"] = json!(false);
    failed(&run(&input), DependencyStatus::Rejected);
}

#[test]
fn typed_json_uuid_fields_are_not_implicitly_references_or_relationships() {
    let mut input = request(&fixture(1));
    input["request"]["fragments"][1]["fields"]["related_invariants"] =
        json!(["01900000-0000-7000-8000-000000000077"]);
    let result = run(&input);
    passed(&result);
    assert!(result.references.iter().all(|r| r.explicitly_empty));
    // Exact AI 1.2 classifies this field complete_typed_json/member_value,
    // not an instruction to fabricate a reference or relationship.
}

#[test]
fn unsupported_relationship_permutations_preserve_authority_and_diagnostics() {
    let mut input = request(&fixture(1));
    input["request"]["relationships"] = json!([
        {"relationship_key":"known","relationship_type":"relationship/calls","source":{"kind":"request","target":"parent"},"target":{"kind":"request","target":"child"},"fields":{},"qualification":input["basis"]["authoring"]},
        {"relationship_key":"unknown","relationship_type":"example:custom","source":{"kind":"request","target":"parent"},"target":{"kind":"request","target":"child"},"fields":{},"qualification":input["basis"]["authoring"]}
    ]);
    let left = run(&input);
    failed(&left, DependencyStatus::Unavailable);
    for relationship in input["request"]["relationships"].as_array_mut().unwrap() {
        relationship["qualification"]["resources"]
            .as_array_mut()
            .unwrap()
            .reverse();
    }
    input["request"]["relationships"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["basis"]["adc"]["resources"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["basis"]["architecture_interpretation"]["authority_closure"]["resources"]
        .as_array_mut()
        .unwrap()
        .reverse();
    assert_eq!(left, run(&input));
}
