use super::super::tests::{bundle, fixture, j, request};
use super::super::{dependencies, insertion, sources};
use super::*;
use crate::authoring_construction_orchestration::{self, EntropyUuidV7Minter};
use serde_json::{json, Value};

fn chain(
    input: &Value,
) -> (
    InsertionResult,
    AccountingResult,
    DependencyResult,
    RecordResult,
) {
    let p = insertion::insert(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &j(input),
        &mut EntropyUuidV7Minter::new(Some(1_767_000_000_123), Some([0x35; 32])),
    );
    let source_refs = p
        .materials
        .keys()
        .map(|k| (k.clone(), format!("opaque:候補/{k}")))
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
    let records = records::assemble(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &p,
        &roots,
        &deps,
    );
    (p, roots, deps, records)
}
fn run(
    p: &InsertionResult,
    roots: &AccountingResult,
    deps: &DependencyResult,
    records: &RecordResult,
) -> SealingResult {
    let before = (p.clone(), roots.clone(), deps.clone(), records.clone());
    let r = prepare(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        p,
        roots,
        deps,
        records,
    );
    assert_eq!(
        before,
        (p.clone(), roots.clone(), deps.clone(), records.clone()),
        "sealing rewrote prior evidence"
    );
    r
}
fn verify(
    p: &InsertionResult,
    roots: &AccountingResult,
    deps: &DependencyResult,
    records: &RecordResult,
    supplied: &SealingResult,
) -> SealingResult {
    qualify_seal(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        p,
        roots,
        deps,
        records,
        supplied,
    )
}
fn passed(r: &SealingResult) {
    assert_eq!(r.status, SealingStatus::Sealed, "{r:#?}");
    assert!(r.diagnostics.is_empty() && r.evidence.is_some());
    assert!(!r
        .outstanding_dependencies
        .contains("composed_candidate_basis_sealing"));
    for key in [
        "complete_nm_2_4_interpretation",
        "expected_and_observed_ledgers",
        "whole_ledger_equivalence",
        "complete_construction_qualification",
    ] {
        assert!(r.outstanding_dependencies.contains(key));
    }
}
fn failed(r: &SealingResult) {
    assert_ne!(r.status, SealingStatus::Sealed, "{r:#?}");
    assert!(r.evidence.is_none() && !r.diagnostics.is_empty());
    assert!(r
        .outstanding_dependencies
        .contains("composed_candidate_basis_sealing"));
}

#[test]
fn acc12_01_02_source_basis_properties_and_native_primitive_reuse() {
    for (case, count) in [(1, 2), (2, 3)] {
        let (p, roots, deps, records) = chain(&request(&fixture(case)));
        let sealed = run(&p, &roots, &deps, &records);
        passed(&sealed);
        assert_eq!(verify(&p, &roots, &deps, &records, &sealed), sealed);
        let e = sealed.evidence.unwrap();
        assert_eq!(e.retained_artifacts.len(), count);
        assert_eq!(e.basis.artifacts.len(), 1);
        assert_eq!(e.basis.artifacts[0].request_key, "parent");
        assert_eq!(e.retained_artifacts, roots.artifacts);
        let native = candidate_source::seal_candidate_source_basis(vec![roots
            .artifacts
            .iter()
            .find(|a| a.request_key == "parent")
            .unwrap()
            .clone()])
        .unwrap();
        assert_eq!(e.basis, native);
        assert_eq!(
            e.candidate_source_basis,
            basis::qualified_basis_to_json(&native, &native.artifacts[0].source_contract)
        );
        assert_eq!(
            e.context.roots[0].canonical_uuid,
            p.materials["parent"].identity
        );
        assert_eq!(e.context.roots[0].source.source_pointer, "/");
        assert_eq!(
            e.context.roots[0].source.canonical_source_ref,
            e.basis.artifacts[0].source_ref
        );
        for accounting in &roots.accounting {
            assert!(e
                .retained_artifacts
                .iter()
                .any(|a| a.request_key == accounting.binding.child_request_key
                    && a.artifact_kind == "authoring_fragment"));
            assert!(!e
                .basis
                .artifacts
                .iter()
                .any(|a| a.request_key == accounting.binding.child_request_key));
        }
    }
}

#[test]
fn exact_descriptor_domain_and_utf8_context_derivation_are_reproducible() {
    let (p, roots, deps, records) = chain(&request(&fixture(2)));
    let r = run(&p, &roots, &deps, &records);
    passed(&r);
    let e = r.evidence.unwrap();
    // Independent test-only reproduction of ADR-L-0032's exact descriptor.
    // Production uses only the native sealer; no second serializer is added.
    let artifacts = e
        .basis
        .artifacts
        .iter()
        .map(|a| {
            let mut json = authoring_construction_orchestration::artifact_to_json(a);
            json.as_object_mut().unwrap().remove("bytes");
            json
        })
        .collect();
    let descriptor = object([
        ("domain".into(), string("adr-kit.candidate-source-basis/v1")),
        ("artifacts".into(), Json::Array(artifacts)),
    ]);
    let expected = format!(
        "sha256:{:x}",
        Sha256::digest(canonical(&descriptor).as_bytes())
    );
    assert_eq!(e.basis.basis_digest, expected);
    assert_eq!(
        e.context.domain,
        "adr-kit.detached-candidate-normalization/v1"
    );
    assert_eq!(
        e.context.scope_root,
        format!(
            "urn:adr-kit:detached-candidate:v1:source-basis:{}",
            expected
        )
    );
    for (artifact, context) in e.basis.artifacts.iter().zip(&e.context.roots) {
        assert_eq!(
            context.output.artifact_path,
            format!(
                "{}/root:sha256:{:x}",
                e.context.scope_root,
                Sha256::digest(artifact.source_ref.as_bytes())
            )
        );
        assert_eq!(context.output.provider_kind, "adr-kit-detached-candidate");
        assert_eq!(
            context.output.architecture_namespace,
            "urn:adr-kit:detached-candidate:v1"
        );
        assert_eq!(context.source_contract, artifact.source_contract);
    }
    assert_eq!(
        at(
            &e.context.qualification,
            &[
                "architecture_interpretation",
                "semantic_contract_fingerprint"
            ]
        )
        .as_str(),
        Some(AI_SCF)
    );
    assert_eq!(
        text(
            at(&e.context.qualification, &["normalized_model"]),
            "version"
        ),
        "2.4"
    );
}

fn multiple_parents() -> Value {
    let mut input = request(&fixture(2));
    let mut parent = input["request"]["fragments"][0].clone();
    parent["request_key"] = json!("a-parent");
    parent["fields"]["id"] = json!("01900000-0000-7000-8000-000000000099");
    let mut child = input["request"]["fragments"][1].clone();
    child["request_key"] = json!("a-child");
    child["fields"]["id"] = json!("01900000-0000-7000-8000-000000000098");
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .extend([parent, child]);
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .push(json!({"parent":"a-parent","child":"a-child","relation":"contains","ordering":3}));
    input
}

#[test]
fn fixed_identity_request_resource_and_proposed_root_permutations_are_stable() {
    let mut input = multiple_parents();
    let (p, roots, deps, records) = chain(&input);
    let good = run(&p, &roots, &deps, &records);
    passed(&good);
    let e = good.evidence.as_ref().unwrap();
    assert_eq!(e.basis.artifacts.len(), 2);
    assert!(e
        .basis
        .artifacts
        .windows(2)
        .all(|a| a[0].source_ref < a[1].source_ref));
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    let (p, roots, deps, records) = chain(&input);
    assert_eq!(run(&p, &roots, &deps, &records), good);
    let mut resources = bundle().1.iter().map(j).collect::<Vec<_>>();
    resources.reverse();
    assert_eq!(
        prepare(&j(&bundle().0), &resources, &p, &roots, &deps, &records),
        good
    );
    let mut artifacts = roots.artifacts.clone();
    artifacts.reverse();
    let mut proposed = roots.selected_root_source_refs.clone();
    proposed.reverse();
    let checked_roots =
        sources::qualify_accounting(&j(&bundle().0), &resources, &p, artifacts, Some(&proposed));
    assert_eq!(checked_roots, roots);
    assert_eq!(
        prepare(
            &j(&bundle().0),
            &resources,
            &p,
            &checked_roots,
            &deps,
            &records
        ),
        good
    );
}

#[test]
fn caller_set_status_and_incomplete_producer_evidence_cannot_seal() {
    let (p, roots, deps, records) = chain(&request(&fixture(1)));
    for variant in 0..9 {
        let (mut p, mut roots, mut deps, mut records) =
            (p.clone(), roots.clone(), deps.clone(), records.clone());
        match variant {
            0 => p.proofs.clear(),
            1 => roots.accounting.clear(),
            2 => roots.artifacts.pop().map(|_| ()).unwrap(),
            3 => deps.references.clear(),
            4 => deps.authority = None,
            5 => records.records.clear(),
            6 => records.records.push(records.records[0].clone()),
            7 => records.outstanding_dependencies.clear(),
            _ => records.diagnostics.push(Diagnostic {
                status: Status::Rejected,
                code: "untrusted".into(),
                semantic_identity: None,
                field_or_relation_key: "untrusted".into(),
                payload: Json::Null,
            }),
        }
        failed(&run(&p, &roots, &deps, &records));
    }
}

#[test]
fn invalid_root_membership_bytes_selectors_profile_and_contract_fail_atomically() {
    let (p, roots, deps, records) = chain(&request(&fixture(1)));
    for variant in 0..10 {
        let mut roots = roots.clone();
        match variant {
            0 => roots.selected_root_source_refs.clear(),
            1 => roots
                .selected_root_source_refs
                .push(roots.selected_root_source_refs[0].clone()),
            2 => roots.selected_root_source_refs.push(
                roots
                    .artifacts
                    .iter()
                    .find(|a| a.request_key == "child")
                    .unwrap()
                    .source_ref
                    .clone(),
            ),
            3 => roots.artifacts[0].bytes.push(b' '),
            4 => {
                roots.artifacts[0].bytes.push(b' ');
                roots.artifacts[0].content_digest =
                    format!("sha256:{:x}", Sha256::digest(&roots.artifacts[0].bytes));
            }
            5 => {
                roots.artifacts[0].source_schema.canonical_resource_key =
                    "authoring/1.7/schema/types.schema".into()
            }
            6 => roots.artifacts[0].serialization_profile = "other".into(),
            7 => roots.artifacts[0].source_contract = Json::Null,
            8 => roots.artifacts[0].source_ref = roots.artifacts[1].source_ref.clone(),
            _ => roots.accounting[0].exact_subtree = false,
        }
        let bad = run(&p, &roots, &deps, &records);
        failed(&bad);
        assert_eq!(bad.status, SealingStatus::Rejected);
    }
}

#[test]
fn basis_commitment_wire_descriptor_and_detached_context_are_reverified() {
    let (p, roots, deps, records) = chain(&request(&fixture(1)));
    let good = run(&p, &roots, &deps, &records);
    passed(&good);
    for variant in 0..18 {
        let mut supplied = good.clone();
        let e = supplied.evidence.as_mut().unwrap();
        match variant {
            0 => e.basis.basis_digest = format!("sha256:{}", "0".repeat(64)),
            1 => e.basis.artifacts.clear(),
            2 => e.basis.artifacts.push(e.basis.artifacts[0].clone()),
            3 => e.basis.artifacts[0].bytes.push(b' '),
            4 => e.retained_artifacts.pop().map(|_| ()).unwrap(),
            5 => e
                .candidate_source_basis
                .as_object_mut()
                .unwrap()
                .insert("sealed".into(), Json::Bool(false))
                .map(|_| ())
                .unwrap(),
            6 => e.context.scope_root.push_str("/stale"),
            7 => e.context.domain = "wrong".into(),
            8 => e.context.roots[0].output.artifact_path.push_str("/wrong"),
            9 => e.context.roots[0].source.canonical_source_ref = "alias:parent".into(),
            10 => e.context.roots[0].source.source_pointer = "/decisions/0".into(),
            11 => e.context.roots[0].canonical_uuid = "01900000-0000-7000-8000-000000000099".into(),
            12 => e.context.roots[0].source_contract = Json::Null,
            13 => e.context.qualification = Json::Null,
            14 => e.context.roots.clear(),
            15 => e.context.roots[0].output.provider_kind = "repository".into(),
            16 => supplied.outstanding_dependencies.clear(),
            _ => supplied.evidence = None,
        }
        let bad = verify(&p, &roots, &deps, &records, &supplied);
        failed(&bad);
        assert_eq!(bad.status, SealingStatus::Rejected);
    }
}

#[test]
fn tampered_record_to_source_linkage_and_proof_flags_block_sealing() {
    let (p, roots, deps, records) = chain(&request(&fixture(1)));
    let value: Value = serde_json::to_value(&records.records[0]).unwrap();
    for pointer in [
        "/integrity/parent_source_ref",
        "/integrity/child_content_digest",
        "/integrity/composition_binding_content_digest",
        "/semantic/child_canonical_uuid",
        "/integrity/identity_disposition/child",
    ] {
        let mut records = records.clone();
        let mut bad = value.clone();
        *bad.pointer_mut(pointer).unwrap() = json!("wrong");
        records.records[0] = j(&bad);
        failed(&run(&p, &roots, &deps, &records));
    }
}

#[test]
fn unsupported_dependencies_and_unbound_standalone_fragments_stay_blocked() {
    for variant in 0..6 {
        let mut input = request(&fixture(1));
        match variant {
            0 => {
                input["request"]["relationships"] = json!([{"relationship_key":"pending","relationship_type":"relationship/calls","source":{"kind":"request","target":"parent"},"target":{"kind":"request","target":"child"},"fields":{},"qualification":input["basis"]["authoring"]}])
            }
            1 => {
                input["basis"]["reference_basis"]["entries"] = json!([{"reference_id":"external","canonical_uuid":"01900000-0000-7000-8000-000000000088","semantic_kind":"entity","semantic_type":"entity/decision","qualification":input["basis"]["authoring"],"existence_state":"retired"}]);
                input["request"]["fragments"][0]["references"] = json!([{"reference_key":"retired","reference_kind":"existing","target":"external"}]);
            }
            2 => {
                input["request"]["fragments"][0]["fields"]["capabilities"] = json!([{"id":"01900000-0000-7000-8000-000000000088","alias_id":"CAP-0001","alias_name":"other","name":"Other","description":"Other authored unit"}])
            }
            3 => {
                let mut f = input["request"]["fragments"][1].clone();
                f["request_key"] = json!("standalone");
                f["fields"]["id"] = json!("01900000-0000-7000-8000-000000000088");
                input["request"]["fragments"]
                    .as_array_mut()
                    .unwrap()
                    .push(f);
            }
            _ => {
                let (kind, semantic_type) = if variant == 4 {
                    ("entity", "example:custom")
                } else {
                    ("relationship", "relationship/calls")
                };
                input["basis"]["reference_basis"]["entries"] = json!([{"reference_id":"unsupported","canonical_uuid":"01900000-0000-7000-8000-000000000088","semantic_kind":kind,"semantic_type":semantic_type,"qualification":input["basis"]["authoring"],"existence_state":"active"}]);
                input["request"]["fragments"][0]["references"] = json!([{"reference_key":"unsupported","reference_kind":"existing","target":"unsupported"}]);
            }
        }
        let (p, roots, deps, records) = chain(&input);
        failed(&run(&p, &roots, &deps, &records));
    }
}

#[test]
fn complete_references_seal_but_unresolved_and_mixed_failures_preserve_precedence() {
    let mut input = request(&fixture(1));
    input["basis"]["reference_basis"]["entries"] = json!([{"reference_id":"external","canonical_uuid":"01900000-0000-7000-8000-000000000088","semantic_kind":"entity","semantic_type":"entity/invariant","qualification":input["basis"]["authoring"],"existence_state":"active"}]);
    input["request"]["fragments"][0]["references"] = json!([
        {"reference_key":"local","reference_kind":"request","target":"child"},
        {"reference_key":"external","reference_kind":"existing","target":"external"}
    ]);
    let (p, roots, deps, records) = chain(&input);
    passed(&run(&p, &roots, &deps, &records));
    input["request"]["fragments"][0]["references"]
        .as_array_mut()
        .unwrap()
        .push(json!({"reference_key":"missing","reference_kind":"request","target":"absent"}));
    let (p, roots, deps, records) = chain(&input);
    let unresolved = run(&p, &roots, &deps, &records);
    failed(&unresolved);
    assert_eq!(unresolved.status, SealingStatus::Unresolved);
    input["request"]["fragments"][0]["references"][1]["expected_semantic_type"] =
        json!("entity/decision");
    input["basis"]["reference_basis"]["entries"][0]["existence_state"] = json!("retired");
    let (p, roots, deps, records) = chain(&input);
    let mixed = run(&p, &roots, &deps, &records);
    failed(&mixed);
    assert_eq!(mixed.status, SealingStatus::Rejected);
    assert_eq!(
        mixed
            .diagnostics
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
    let (p, roots, deps, records) = chain(&input);
    assert_eq!(run(&p, &roots, &deps, &records), mixed);
}

#[test]
fn exact_context_authority_cannot_be_replaced_or_omitted() {
    let (p, roots, deps, records) = chain(&request(&fixture(1)));
    for variant in 0..3 {
        let mut resources = bundle().1.clone();
        let i = resources
            .iter()
            .position(|r| r["canonicalResourceKey"] == CONTEXT)
            .unwrap();
        match variant {
            0 => {
                resources.remove(i);
            }
            1 => resources[i]["content"]["domain"] = json!("other"),
            _ => resources[i]["content"]["architecture_namespace"] = json!("repository"),
        }
        let bad = prepare(
            &j(&bundle().0),
            &resources.iter().map(j).collect::<Vec<_>>(),
            &p,
            &roots,
            &deps,
            &records,
        );
        failed(&bad);
        assert_eq!(bad.status, SealingStatus::Unavailable);
    }
}
