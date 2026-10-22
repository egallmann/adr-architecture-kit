use super::super::tests::{bundle, fixture, j, request};
use super::*;
use crate::authoring_construction_orchestration::EntropyUuidV7Minter;
use serde_json::{json, Value};

fn prepared(input: &Value) -> (InsertionResult, AccountingResult, DependencyResult) {
    let p = insertion::insert(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &j(input),
        &mut EntropyUuidV7Minter::new(Some(1_767_000_000_123), Some([0x58; 32])),
    );
    let source_refs = p
        .materials
        .keys()
        .map(|k| (k.clone(), format!("candidate/{k}")))
        .collect();
    let roots = sources::prepare(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &p,
        &source_refs,
    );
    let deps = dependencies::qualify_dependencies(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &p,
        &roots,
    );
    (p, roots, deps)
}
fn run(p: &InsertionResult, roots: &AccountingResult, deps: &DependencyResult) -> RecordResult {
    let before = (p.clone(), roots.clone(), deps.clone());
    let r = assemble(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        p,
        roots,
        deps,
    );
    assert_eq!(before, (p.clone(), roots.clone(), deps.clone()));
    r
}
fn validate(
    p: &InsertionResult,
    roots: &AccountingResult,
    deps: &DependencyResult,
    records: &[Value],
) -> RecordResult {
    qualify_records(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        p,
        roots,
        deps,
        &records.iter().map(j).collect::<Vec<_>>(),
    )
}
fn records(r: &RecordResult) -> Vec<Value> {
    r.records
        .iter()
        .map(|r| serde_json::to_value(r).unwrap())
        .collect()
}
fn passed(r: &RecordResult, count: usize) {
    assert_eq!(r.status, RecordStatus::RecordsQualified, "{r:#?}");
    assert_eq!(r.records.len(), count);
    assert!(r.diagnostics.is_empty());
    assert!(!r
        .outstanding_dependencies
        .contains("complete_composition_evidence"));
    for key in [
        "composed_candidate_basis_sealing",
        "complete_nm_2_4_interpretation",
        "expected_and_observed_ledgers",
        "whole_ledger_equivalence",
        "complete_construction_qualification",
    ] {
        assert!(r.outstanding_dependencies.contains(key));
    }
}
fn failed(r: &RecordResult) {
    assert_ne!(r.status, RecordStatus::RecordsQualified, "{r:#?}");
    assert!(r.records.is_empty() && !r.diagnostics.is_empty());
    assert!(r
        .outstanding_dependencies
        .contains("complete_composition_evidence"));
}

#[test]
fn acc12_01_02_complete_records_are_schema_valid_and_proof_bound() {
    for (case, count) in [(1, 1), (2, 2)] {
        let input = request(&fixture(case));
        assert!(input["basis"]["custom_entity"].is_null());
        let (p, roots, deps) = prepared(&input);
        let r = run(&p, &roots, &deps);
        passed(&r, count);
        assert_eq!(validate(&p, &roots, &deps, &records(&r)), r);
        for record in records(&r) {
            let integrity = &record["integrity"];
            assert!(integrity["prepared_property_absent"].as_bool().unwrap());
            assert!(integrity["exact_subtree"].as_bool().unwrap());
            assert!(integrity["child_candidate_artifact_retained"]
                .as_bool()
                .unwrap());
            assert!(integrity["child_source_root_omitted"].as_bool().unwrap());
            assert_eq!(
                record["qualification"]["acc"]["semantic_contract_fingerprint"],
                SCF
            );
            assert_eq!(
                record["qualification"]["custom_entity"]["family"],
                "custom-entity"
            );
            assert!(!record["qualification"]["custom_entity"]["resources"]
                .as_array()
                .unwrap()
                .is_empty());
            assert!(record["qualification"]["custom_entity"]
                .get("registry_source")
                .is_none());
        }
    }
}

#[test]
fn missing_duplicate_and_fabricated_records_fail_atomically() {
    let (p, roots, deps) = prepared(&request(&fixture(2)));
    let good = records(&run(&p, &roots, &deps));
    for records in [
        vec![],
        vec![good[0].clone()],
        vec![good[0].clone(), good[0].clone()],
        vec![good[0].clone(), good[1].clone(), good[0].clone()],
    ] {
        failed(&validate(&p, &roots, &deps, &records));
    }
}

#[test]
fn malformed_proposed_resource_members_fail_without_canonicalizer_panics() {
    let (p, roots, deps) = prepared(&request(&fixture(1)));
    let good = records(&run(&p, &roots, &deps));
    for malformed in [
        json!(9007199254740992_u64),
        json!({"unqualified":9007199254740992_u64}),
    ] {
        let mut altered = good.clone();
        altered[0]["qualification"]["custom_entity"]["resources"] = json!([malformed, {}]);
        let r = validate(&p, &roots, &deps, &altered);
        failed(&r);
        assert_eq!(r.status, RecordStatus::Rejected);
    }
}

#[test]
fn every_record_field_is_checked_against_independent_proof_not_just_shape() {
    let (p, roots, deps) = prepared(&request(&fixture(1)));
    let good = records(&run(&p, &roots, &deps));
    let changes = [
        (
            "/semantic/parent_canonical_uuid",
            json!("01900000-0000-7000-8000-000000000099"),
        ),
        (
            "/semantic/child_canonical_uuid",
            json!("01900000-0000-7000-8000-000000000099"),
        ),
        (
            "/semantic/parent_semantic_type",
            json!("adr/physical-system"),
        ),
        ("/semantic/child_semantic_type", json!("entity/invariant")),
        ("/semantic/relation", json!("composed_of")),
        (
            "/semantic/semantic_field_key",
            json!("adr/logical#/capabilities"),
        ),
        ("/semantic/binding_id", json!("other")),
        ("/semantic/authoring_property", json!("capabilities")),
        ("/semantic/ordering", json!(999)),
        ("/semantic/resolution_kind", json!("existing")),
        ("/integrity/parent_request_key", json!("wrong")),
        ("/integrity/child_request_key", json!("wrong")),
        ("/integrity/parent_source_ref", json!("wrong")),
        ("/integrity/child_source_ref", json!("wrong")),
        (
            "/integrity/parent_content_digest",
            json!(format!("sha256:{}", "0".repeat(64))),
        ),
        (
            "/integrity/child_content_digest",
            json!(format!("sha256:{}", "0".repeat(64))),
        ),
        (
            "/integrity/composition_binding_resource_key",
            json!("wrong"),
        ),
        (
            "/integrity/composition_binding_content_digest",
            json!(format!("sha256:{}", "0".repeat(64))),
        ),
        ("/integrity/prepared_property_absent", json!(false)),
        ("/integrity/exact_subtree", json!(false)),
        ("/integrity/child_candidate_artifact_retained", json!(false)),
        ("/integrity/child_source_root_omitted", json!(false)),
        ("/integrity/induced_sequence_index", json!(1)),
        ("/integrity/identity_disposition/parent", json!("minted")),
        ("/integrity/identity_disposition/child", json!("minted")),
        (
            "/qualification/acc/semantic_contract_fingerprint",
            json!(format!("scf:v1:sha256:{}", "0".repeat(64))),
        ),
        (
            "/qualification/authoring_domain/content_digest",
            json!(format!("sha256:{}", "0".repeat(64))),
        ),
        (
            "/qualification/composition_binding/content_digest",
            json!(format!("sha256:{}", "0".repeat(64))),
        ),
    ];
    for (path, value) in changes {
        let mut altered = good.clone();
        *altered[0].pointer_mut(path).unwrap() = value;
        let r = validate(&p, &roots, &deps, &altered);
        failed(&r);
        assert_eq!(r.status, RecordStatus::Rejected, "{path}: {r:#?}");
    }
    for partition in ["semantic", "integrity", "qualification"] {
        for key in good[0][partition].as_object().unwrap().keys() {
            let mut altered = good.clone();
            altered[0][partition].as_object_mut().unwrap().remove(key);
            failed(&validate(&p, &roots, &deps, &altered));
        }
    }
}

#[test]
fn exact_qualification_resource_sets_cannot_be_omitted_or_replaced() {
    let (p, roots, deps) = prepared(&request(&fixture(1)));
    let good = records(&run(&p, &roots, &deps));
    for path in [
        "/qualification/architecture_interpretation/authority_closure/resources",
        "/qualification/authoring/resources",
        "/qualification/normalized_model/resources",
        "/qualification/custom_entity/resources",
    ] {
        for variant in 0..3 {
            let mut altered = good.clone();
            let members = altered[0]
                .pointer_mut(path)
                .unwrap()
                .as_array_mut()
                .unwrap();
            match variant {
                0 => {
                    members.pop();
                }
                1 => members[0]["content_digest"] = json!(format!("sha256:{}", "0".repeat(64))),
                _ => members.push(members[0].clone()),
            }
            failed(&validate(&p, &roots, &deps, &altered));
        }
    }
}

#[test]
fn proof_and_dependency_status_flags_cannot_forge_record_qualification() {
    let (p, roots, deps) = prepared(&request(&fixture(1)));
    for variant in 0..9 {
        let (mut p, mut roots, mut deps) = (p.clone(), roots.clone(), deps.clone());
        match variant {
            0 => p.proofs.clear(),
            1 => p.materials.get_mut("child").unwrap().bytes.push(b' '),
            2 => roots.accounting[0].exact_subtree = false,
            3 => roots.accounting[0].child_source_root_omitted = false,
            4 => roots.accounting[0].induced_sequence_index = 9,
            5 => roots.artifacts[0].source_ref = "wrong".into(),
            6 => deps.references.clear(),
            7 => deps.outstanding_dependencies.clear(),
            _ => deps.authority = None,
        }
        failed(&run(&p, &roots, &deps));
    }
    let mut input = request(&fixture(1));
    input["request"]["relationships"] = json!([{"relationship_key":"pending","relationship_type":"relationship/calls","source":{"kind":"request","target":"parent"},"target":{"kind":"request","target":"child"},"fields":{},"qualification":input["basis"]["authoring"]}]);
    let (p, roots, mut deps) = prepared(&input);
    deps.status = DependencyStatus::DependenciesQualified;
    deps.pending.clear();
    deps.diagnostics.clear();
    let r = run(&p, &roots, &deps);
    failed(&r);
    assert!(r
        .diagnostics
        .iter()
        .any(|d| d.status == Status::Unavailable));
}

#[test]
fn cec_missing_corrupt_or_mismatched_closure_never_qualifies() {
    let (p, roots, deps) = prepared(&request(&fixture(1)));
    for variant in 0..3 {
        let mut resources = bundle().1.clone();
        let index = resources
            .iter()
            .position(|r| r["canonicalResourceKey"] == "custom-entity/1.0/contract")
            .unwrap();
        match variant {
            0 => {
                resources.remove(index);
            }
            1 => resources[index]["content"]["contract_version"] = json!("9.0"),
            _ => resources[index]["content"] = json!({}),
        }
        let r = assemble(
            &j(&bundle().0),
            &resources.iter().map(j).collect::<Vec<_>>(),
            &p,
            &roots,
            &deps,
        );
        failed(&r);
        assert_eq!(r.status, RecordStatus::Unavailable);
    }
}

#[test]
fn canonical_record_order_and_qualification_sets_are_permutation_invariant() {
    let mut input = request(&fixture(2));
    let (p, roots, deps) = prepared(&input);
    let good = run(&p, &roots, &deps);
    passed(&good, 2);
    let mut proposed = records(&good);
    proposed.reverse();
    for r in &mut proposed {
        for path in [
            "/qualification/architecture_interpretation/authority_closure/resources",
            "/qualification/authoring/resources",
            "/qualification/normalized_model/resources",
            "/qualification/custom_entity/resources",
        ] {
            r.pointer_mut(path)
                .unwrap()
                .as_array_mut()
                .unwrap()
                .reverse();
        }
    }
    assert_eq!(validate(&p, &roots, &deps, &proposed), good);
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    let (p, roots, deps) = prepared(&input);
    assert_eq!(run(&p, &roots, &deps), good);
}

#[test]
fn minted_and_preserved_dispositions_come_only_from_insertion() {
    let mut input = request(&fixture(1));
    input["request"]["fragments"][1]["fields"]
        .as_object_mut()
        .unwrap()
        .remove("id");
    let (p, roots, deps) = prepared(&input);
    let r = run(&p, &roots, &deps);
    passed(&r, 1);
    let records = records(&r);
    assert_eq!(
        records[0]["integrity"]["identity_disposition"],
        json!({"parent":"preserved","child":"minted"})
    );
    assert_eq!(
        records[0]["semantic"]["child_canonical_uuid"],
        p.materials["child"].identity
    );
}

#[test]
fn multiple_parents_sort_by_uuid_not_request_key_or_discovery_order() {
    let mut input = request(&fixture(1));
    let mut parent = input["request"]["fragments"][0].clone();
    let mut child = input["request"]["fragments"][1].clone();
    parent["request_key"] = json!("a-parent");
    parent["fields"]["id"] = json!("01900000-0000-7000-8000-000000000099");
    child["request_key"] = json!("a-child");
    child["fields"]["id"] = json!("01900000-0000-7000-8000-000000000098");
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .extend([parent, child]);
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .push(json!({"parent":"a-parent","child":"a-child","relation":"contains","ordering":0}));
    let (p, roots, deps) = prepared(&input);
    let good = run(&p, &roots, &deps);
    passed(&good, 2);
    assert_eq!(
        records(&good)[0]["integrity"]["parent_request_key"],
        "parent"
    );
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    let (p, roots, deps) = prepared(&input);
    assert_eq!(run(&p, &roots, &deps), good);
}

#[test]
fn completed_references_and_independent_failure_precedence_survive_replay() {
    let mut input = request(&fixture(1));
    input["basis"]["reference_basis"]["entries"] = json!([{"reference_id":"external","canonical_uuid":"01900000-0000-7000-8000-000000000088","semantic_kind":"entity","semantic_type":"entity/invariant","qualification":input["basis"]["authoring"],"existence_state":"active"}]);
    input["request"]["fragments"][0]["references"] = json!([
        {"reference_key":"local","reference_kind":"request","target":"child"},
        {"reference_key":"existing","reference_kind":"existing","target":"external"}
    ]);
    let (p, roots, deps) = prepared(&input);
    passed(&run(&p, &roots, &deps), 1);
    input["request"]["fragments"][0]["references"][1]["expected_semantic_type"] =
        json!("entity/decision");
    input["request"]["fragments"][0]["references"]
        .as_array_mut()
        .unwrap()
        .push(json!({"reference_key":"missing","reference_kind":"request","target":"absent"}));
    input["basis"]["reference_basis"]["entries"][0]["existence_state"] = json!("retired");
    let (p, roots, deps) = prepared(&input);
    let bad = run(&p, &roots, &deps);
    failed(&bad);
    assert_eq!(bad.status, RecordStatus::Rejected);
    assert_eq!(
        bad.diagnostics
            .iter()
            .map(|d| d.status)
            .collect::<BTreeSet<_>>(),
        BTreeSet::from([Status::Rejected, Status::Unavailable, Status::Unresolved])
    );
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    for f in input["request"]["fragments"].as_array_mut().unwrap() {
        f["references"].as_array_mut().unwrap().reverse();
    }
    let (p, roots, deps) = prepared(&input);
    assert_eq!(run(&p, &roots, &deps), bad);
}
