use super::super::tests::{bundle, fixture, j, request};
use super::*;
use crate::authoring_construction_orchestration::EntropyUuidV7Minter;
use serde_json::{json, Value};

fn proven(input: &Value) -> InsertionResult {
    insertion::insert(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &j(input),
        &mut EntropyUuidV7Minter::new(Some(1_767_000_000_123), Some([0x42; 32])),
    )
}
fn refs(proven: &InsertionResult) -> BTreeMap<String, String> {
    proven
        .materials
        .keys()
        .map(|k| (k.clone(), format!("candidate/{k}")))
        .collect()
}
fn prepare_case(input: &Value) -> (InsertionResult, AccountingResult) {
    let p = proven(input);
    let result = prepare(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &p,
        &refs(&p),
    );
    (p, result)
}
fn check(
    p: &InsertionResult,
    artifacts: Vec<CandidateSourceArtifact>,
    roots: Option<&[String]>,
) -> AccountingResult {
    qualify_accounting(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        p,
        artifacts,
        roots,
    )
}
fn passed(result: &AccountingResult) {
    assert_eq!(
        result.status,
        AccountingStatus::RootsAccounted,
        "{result:#?}"
    );
    assert!(result.diagnostics.is_empty());
    for obligation in [
        "non_composition_reference_and_relationship_resolution",
        "complete_composition_evidence",
        "composed_candidate_basis_sealing",
        "complete_construction_qualification",
    ] {
        assert!(result.outstanding_dependencies.contains(obligation));
    }
}
fn rejected(result: &AccountingResult) {
    assert_eq!(result.status, AccountingStatus::Rejected, "{result:#?}");
    assert!(result.artifacts.is_empty());
    assert!(result.accounting.is_empty());
    assert!(result.selected_root_source_refs.is_empty());
    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.code == "authoring_construction.composition.containment_accounting"));
}

#[test]
fn acc12_01_02_exact_artifacts_and_minimal_roots_match_frozen_properties() {
    for case in [1, 2] {
        let (p, result) = prepare_case(&request(&fixture(case)));
        passed(&result);
        assert_eq!(result.artifacts.len(), p.materials.len());
        assert_eq!(result.selected_root_source_refs, vec!["candidate/parent"]);
        assert_eq!(result.accounting.len(), p.proofs.len());
        for a in &result.artifacts {
            assert_eq!(a.bytes, p.materials[&a.request_key].bytes);
            assert!(candidate_source::decode_and_validate_candidate(a).is_ok());
            assert_eq!(
                a.artifact_kind,
                if a.request_key == "parent" {
                    "authoring_document"
                } else {
                    "authoring_fragment"
                }
            );
        }
        let frozen: Value = serde_json::from_str(include_str!(
            "../../contracts/authoring-construction/v1.2/resources/conformance.json"
        ))
        .unwrap();
        for assertion in frozen["cases"][case - 1]["assertions"].as_array().unwrap() {
            if assertion["path"] == "source_root_identities" {
                let ids: Vec<_> = result
                    .artifacts
                    .iter()
                    .filter(|a| result.selected_root_source_refs.contains(&a.source_ref))
                    .map(|a| {
                        text(
                            &candidate_source::decode_and_validate_candidate(a).unwrap(),
                            "id",
                        )
                        .to_owned()
                    })
                    .collect();
                assert_eq!(json!(ids), assertion["expected"]);
            }
        }
        let mut ownership = BTreeSet::new();
        for root in &result.selected_root_source_refs {
            let a = result
                .artifacts
                .iter()
                .find(|a| &a.source_ref == root)
                .unwrap();
            assert!(ownership.insert(p.materials[&a.request_key].identity.clone()));
        }
        for (index, e) in result.accounting.iter().enumerate() {
            assert!(
                e.exact_subtree
                    && e.child_candidate_artifact_retained
                    && e.child_source_root_omitted
            );
            assert_eq!(e.induced_sequence_index, index);
            assert!(ownership.insert(e.binding.child_identity.clone().unwrap()));
            let child = result
                .artifacts
                .iter()
                .find(|a| a.source_ref == e.child_source_ref)
                .unwrap();
            assert_eq!(child.content_digest, e.child_content_digest);
            assert!(!result.selected_root_source_refs.contains(&child.source_ref));
        }
        assert_eq!(ownership.len(), result.artifacts.len());
    }
}

#[test]
fn acc12_25_26_reject_root_inclusion_and_omission_without_complete_proof() {
    for case in [25, 26] {
        let f = fixture(case);
        let (mut p, good) = prepare_case(&request(&f["candidate"]));
        passed(&good);
        if f["exact_subtree"] == false {
            p.proofs.clear();
        }
        let roots: Vec<_> = f["observed_source_root_identities"]
            .as_array()
            .unwrap()
            .iter()
            .map(|id| {
                good.artifacts
                    .iter()
                    .find(|a| {
                        text(
                            &candidate_source::decode_and_validate_candidate(a).unwrap(),
                            "id",
                        ) == id.as_str().unwrap()
                    })
                    .unwrap()
                    .source_ref
                    .clone()
            })
            .collect();
        rejected(&check(&p, good.artifacts, Some(&roots)));
    }
}

#[test]
fn fixed_identity_request_artifact_and_root_permutations_are_invariant() {
    let f = fixture(3);
    let (p, left) = prepare_case(&request(&f["left"]));
    let (_, right) = prepare_case(&request(&f["right"]));
    passed(&left);
    passed(&right);
    assert_eq!(left, right);
    let mut artifacts = left.artifacts.clone();
    artifacts.reverse();
    assert_eq!(
        check(&p, artifacts, Some(&left.selected_root_source_refs)),
        left
    );
}

#[test]
fn missing_proof_wrong_property_identity_and_qualification_cannot_release_artifacts() {
    let (good, artifacts) = prepare_case(&request(&fixture(1)));
    for variant in 0..8 {
        let mut p = good.clone();
        match variant {
            0 => p.proofs.clear(),
            1 => p.proofs[0]
                .binding
                .binding
                .as_object_mut()
                .unwrap()
                .insert("parent_property".into(), string("context"))
                .map(|_| ())
                .unwrap(),
            2 => {
                p.proofs[0].binding.child_identity =
                    Some("01900000-0000-7000-8000-000000000099".into())
            }
            3 => p.proofs[0]
                .binding
                .binding
                .as_object_mut()
                .unwrap()
                .insert("relation".into(), string("composed_of"))
                .map(|_| ())
                .unwrap(),
            4 => p.proofs.push(p.proofs[0].clone()),
            5 => p.qualification.bindings.clear(),
            6 => p.materials.get_mut("child").unwrap().identity_disposition = "minted",
            _ => p.materials.get_mut("child").unwrap().bytes.push(b' '),
        }
        rejected(&check(&p, artifacts.artifacts.clone(), None));
    }
    // Generic subtree equality alone would accept these pairs. ACC authority
    // must still qualify the property, identities, ordering and insertion.
    assert!(candidate_source::select_minimal_candidate_source_roots(
        artifacts.artifacts.clone(),
        &[CandidateSourceContainment {
            parent_request_key: "parent".into(),
            child_request_key: "child".into()
        }]
    )
    .is_ok());
    let mut input = request(&fixture(1));
    input["request"]["compositions"] = json!([]);
    let mut only_qualifier = proven(&input);
    only_qualifier.status = InsertionStatus::PreservationProven;
    only_qualifier.qualification = good.qualification.clone();
    only_qualifier.materials = good.materials.clone();
    only_qualifier.proofs = good.proofs.clone();
    rejected(&check(&only_qualifier, artifacts.artifacts, None));
}

#[test]
fn artifact_integrity_metadata_and_complete_retention_are_mandatory() {
    let (p, good) = prepare_case(&request(&fixture(1)));
    for variant in 0..10 {
        let mut artifacts = good.artifacts.clone();
        let child = artifacts
            .iter()
            .position(|a| a.request_key == "child")
            .unwrap();
        match variant {
            0 => artifacts[child].bytes.push(b' '),
            1 => {
                artifacts[child].content_digest =
                    "sha256:0000000000000000000000000000000000000000000000000000000000000000".into()
            }
            2 => {
                artifacts[child].source_ref = artifacts
                    .iter()
                    .find(|a| a.request_key == "parent")
                    .unwrap()
                    .source_ref
                    .clone()
            }
            3 => artifacts[child].source_ref.clear(),
            4 => artifacts[child].artifact_kind = "authoring_document".into(),
            5 => artifacts[child].source_schema.json_pointer.clear(),
            6 => artifacts[child].source_contract = Json::Null,
            7 => artifacts[child].serialization_profile = "ambient".into(),
            8 => {
                artifacts.remove(child);
            }
            _ => artifacts.push(artifacts[child].clone()),
        }
        rejected(&check(&p, artifacts, None));
    }
    let child = good
        .artifacts
        .iter()
        .find(|a| a.request_key == "child")
        .unwrap();
    let mut changed = candidate_source::decode_and_validate_candidate(child).unwrap();
    changed
        .as_object_mut()
        .unwrap()
        .insert("id".into(), string("01900000-0000-7000-8000-000000000099"));
    let rewritten = candidate_source::seal_candidate_artifact(
        &child.request_key,
        &child.source_ref,
        &child.artifact_kind,
        child.source_schema.clone(),
        child.source_contract.clone(),
        &changed,
    )
    .unwrap();
    assert!(candidate_source::decode_and_validate_candidate(&rewritten).is_ok());
    let artifacts = good
        .artifacts
        .iter()
        .map(|a| {
            if a.request_key == "child" {
                rewritten.clone()
            } else {
                a.clone()
            }
        })
        .collect();
    rejected(&check(&p, artifacts, None));
}

#[test]
fn incorrect_root_sets_and_mixed_integrity_diagnostics_are_deterministic() {
    let (p, good) = prepare_case(&request(&fixture(2)));
    for roots in [
        vec![],
        vec!["candidate/child".into()],
        vec!["candidate/parent".into(), "candidate/parent".into()],
        vec!["missing".into()],
    ] {
        rejected(&check(&p, good.artifacts.clone(), Some(&roots)));
    }
    let mut artifacts = good.artifacts.clone();
    artifacts[0].content_digest = "sha256:bad".into();
    artifacts[1].source_ref = artifacts[0].source_ref.clone();
    let left = check(&p, artifacts.clone(), None);
    rejected(&left);
    assert!(left.diagnostics.len() > 1);
    artifacts.reverse();
    assert_eq!(left, check(&p, artifacts, None));
}

#[test]
fn reference_obligations_remain_explicit_and_source_refs_are_opaque() {
    let mut input = request(&fixture(1));
    input["request"]["fragments"][1]["fields"]["related_invariants"] =
        json!(["01900000-0000-7000-8000-000000000099"]);
    let p = proven(&input);
    let mut source_refs = refs(&p);
    source_refs.insert("parent".into(), "urn:opaque:parent/../x".into());
    let result = prepare(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &p,
        &source_refs,
    );
    passed(&result);
    assert_eq!(
        result.selected_root_source_refs,
        vec!["urn:opaque:parent/../x"]
    );
    source_refs.remove("child");
    rejected(&prepare(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &p,
        &source_refs,
    ));
}

#[test]
fn authority_loss_is_unavailable_not_invalid_source_evidence() {
    let (p, good) = prepare_case(&request(&fixture(1)));
    let mut resources = bundle().1.iter().map(j).collect::<Vec<_>>();
    resources.pop();
    let result = qualify_accounting(&j(&bundle().0), &resources, &p, good.artifacts, None);
    assert_eq!(result.status, AccountingStatus::Unavailable);
    assert!(result.artifacts.is_empty());
    assert!(result.accounting.is_empty());
}

#[test]
fn additional_unaccounted_semantic_membership_is_unavailable_not_silently_counted() {
    let mut input = request(&fixture(1));
    input["request"]["fragments"][0]["fields"]["capabilities"] = json!([{
        "id":"01900000-0000-7000-8000-000000000099", "alias_id":"CAP-0001",
        "alias_name":"other", "name":"Other", "description":"Other authored unit"
    }]);
    let (p, result) = prepare_case(&input);
    assert_eq!(p.status, InsertionStatus::PreservationProven);
    assert_eq!(result.status, AccountingStatus::Unavailable);
    assert!(result.artifacts.is_empty());
    assert!(result.accounting.is_empty());
    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.field_or_relation_key == "adr/logical#/capabilities"));
}

#[test]
fn multiple_parent_roots_are_sorted_by_opaque_source_reference() {
    let mut input = request(&fixture(1));
    let mut extra = input["request"]["fragments"].clone();
    extra[0]["request_key"] = json!("second-parent");
    extra[0]["fields"]["id"] = json!("01900000-0000-7000-8000-000000000098");
    extra[1]["request_key"] = json!("second-child");
    extra[1]["fields"]["id"] = json!("01900000-0000-7000-8000-000000000099");
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .extend(extra.as_array().unwrap().clone());
    input["request"]["compositions"].as_array_mut().unwrap().push(json!({"parent":"second-parent","child":"second-child","relation":"contains","ordering":0}));
    let (p, good) = prepare_case(&input);
    passed(&good);
    assert_eq!(good.artifacts.len(), 4);
    assert_eq!(
        good.selected_root_source_refs,
        vec!["candidate/parent", "candidate/second-parent"]
    );
    let mut reversed = good.selected_root_source_refs.clone();
    reversed.reverse();
    assert_eq!(good, check(&p, good.artifacts.clone(), Some(&reversed)));
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    assert_eq!(good, prepare_case(&input).1);
}

#[test]
fn minted_identities_are_reused_and_incomplete_results_never_gain_success() {
    let input = request(&fixture(5));
    let (p, result) = prepare_case(&input);
    passed(&result);
    for artifact in &result.artifacts {
        let material = &p.materials[&artifact.request_key];
        let original = input["request"]["fragments"]
            .as_array()
            .unwrap()
            .iter()
            .find(|f| f["request_key"] == artifact.request_key)
            .unwrap();
        assert_eq!(
            material.identity_disposition,
            if original["fields"].get("id").is_some() {
                "preserved"
            } else {
                "minted"
            }
        );
        assert_eq!(
            text(
                &candidate_source::decode_and_validate_candidate(artifact).unwrap(),
                "id"
            ),
            material.identity
        );
    }
    let mut input = request(&fixture(1));
    input["request"]["compositions"] = json!([]);
    let mut incomplete = proven(&input);
    incomplete.qualification.diagnostics = vec![Diagnostic {
        status: Status::Qualified,
        code: "not_a_failure".into(),
        semantic_identity: None,
        field_or_relation_key: "test".into(),
        payload: Json::Null,
    }];
    let result = check(&incomplete, Vec::new(), None);
    assert_eq!(result.status, AccountingStatus::Unavailable);
    assert!(result.artifacts.is_empty());
    assert!(result.accounting.is_empty());
}
