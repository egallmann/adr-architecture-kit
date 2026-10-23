use super::*;
use crate::authoring_construction_v13::tests::{bundle, refs, request, run};
use serde_json::{json, Value};
fn j(v: &Value) -> Json {
    serde_json::from_value(v.clone()).unwrap()
}
fn qualify(input: &Value, sealed: &SealResult) -> Projection {
    interpret(
        &bundle().0,
        &bundle().1,
        &bundle().2,
        &j(input),
        &refs(input),
        sealed,
    )
}
#[test]
fn exact_catalog_and_logical_decision_projection() {
    let a = Authority::qualify(&bundle().0, &bundle().1, &bundle().2).unwrap();
    assert_eq!(a.types.len(), 27);
    let input = request(2);
    let seal = run(&input);
    assert_eq!(seal.status, SealStatus::Sealed, "{seal:#?}");
    let r = qualify(&input, &seal);
    assert_eq!(r.status, Status::DispositionsQualified, "{r:#?}");
    assert_eq!(r.units.len(), 3);
    assert_eq!(
        verify_projection(
            &bundle().0,
            &bundle().1,
            &bundle().2,
            &j(&input),
            &refs(&input),
            &seal,
            &r
        ),
        r
    );
    assert!(!r.outstanding.is_empty());
}
#[test]
fn ai13_022_to_033_exact_literal_domains() {
    let oracle: Value = serde_json::from_str(include_str!(
        "../../contracts/architecture-interpretation/v1.3/resources/conformance.json"
    ))
    .unwrap();
    for case in &oracle["cases"].as_array().unwrap()[21..33] {
        assert_eq!(case["category"], "root-lifecycle");
        assert_eq!(case["expected"], "preserves");
    }
    let a = Authority::qualify(&bundle().0, &bundle().1, &bundle().2).unwrap();
    for ty in [
        "adr/logical",
        "adr/physical-system",
        "adr/physical-component",
    ] {
        for status in ["proposed", "accepted", "deprecated", "superseded"] {
            assert_eq!(a.lifecycle(ty, &string(status)).unwrap(), string(status));
            assert_eq!(
                a.root_lifecycle(ty, &root_fixture(ty, status)).unwrap(),
                string(status)
            );
        }
        for invalid in ["active", "unknown", ""] {
            assert!(a.lifecycle(ty, &string(invalid)).is_err());
        }
    }
}

fn root_fixture(ty: &str, status: &str) -> Json {
    let id = "01900000-0000-7000-8000-000000000001";
    let kind = ty.strip_prefix("adr/").unwrap();
    let mut root = json!({"schema_version":"1.7","adr_type":kind,"id":id,"alias_id":"ADR-L-0001","alias_name":"test-root","title":"Test root authority","status":status,"created_date":"2026-10-23","authors":["Test"],"context":"Typed source"});
    if kind == "logical" {
        root["decisions"] = json!([request(1)["request"]["fragments"][1]["fields"].clone()]);
    } else {
        root["alias_id"] = json!(if kind == "physical-system" {
            "ADR-PS-0001"
        } else {
            "ADR-PC-0001"
        });
        root["implements_logical"] = json!([id]);
        root["technology_stack"] =
            json!([{"category":"language","name":"Rust","version":"1","rationale":"Test"}]);
        if kind == "physical-system" {
            root["system"] = json!({"id":id,"alias_id":"SYS-0001","alias_name":"system"});
        } else {
            root["implements_system"] = json!([id]);
            root["component_specifications"] = json!([{"id":"01900000-0000-7000-8000-000000000002","alias_id":"COMP-0001","alias_name":"component","name":"Component","type":"service","responsibilities":"Test","generation_context":{"purpose":"Test","key_responsibilities":["Test"]},"interfaces":[{"id":"01900000-0000-7000-8000-000000000003","alias_id":"IFACE-0001","alias_name":"interface","type":"REST","specification":"Test"}]}]);
        }
    }
    j(&root)
}

fn failed(r: &Projection) {
    assert_ne!(r.status, Status::DispositionsQualified, "{r:#?}");
    assert!(r.units.is_empty() && r.source_commitment.is_none());
    assert_eq!(r.complete_interpretation, Status::Unavailable);
}

#[test]
fn exact_authority_substitution_missing_and_corrupt_resources_fail_closed() {
    let input = request(1);
    let seal = run(&input);
    for key in [
        FD,
        OWNER,
        CARRIER,
        "architecture-interpretation/1.3/contextual-facts",
        "normalized-model/2.5/schema/normalized-entity.schema",
    ] {
        let mut resources = bundle().1.clone();
        resources.retain(|r| text(r, "canonicalResourceKey") != key);
        let r = interpret(
            &bundle().0,
            &resources,
            &bundle().2,
            &j(&input),
            &refs(&input),
            &seal,
        );
        failed(&r);
        assert_eq!(r.status, Status::Unavailable);
        let mut resources = bundle().1.clone();
        let entry = resources
            .iter_mut()
            .find(|r| text(r, "canonicalResourceKey") == key)
            .unwrap();
        entry
            .as_object_mut()
            .unwrap()
            .insert("content".into(), Json::Null);
        failed(&interpret(
            &bundle().0,
            &resources,
            &bundle().2,
            &j(&input),
            &refs(&input),
            &seal,
        ));
    }
    for (family, version) in [
        ("authoring-construction", "1.2"),
        ("architecture-interpretation", "1.2"),
        ("normalized-model", "2.4"),
    ] {
        let mut changed = input.clone();
        let field = match family {
            "authoring-construction" => "acc",
            "architecture-interpretation" => "architecture_interpretation",
            _ => "normalized_model",
        };
        changed["basis"][field]["version"] = json!(version);
        failed(&qualify(&changed, &seal));
    }
}

#[test]
fn independent_projection_verification_rejects_mutated_meaning_and_provenance() {
    let input = request(2);
    let seal = run(&input);
    let good = qualify(&input, &seal);
    assert_eq!(good.status, Status::DispositionsQualified, "{good:#?}");
    for mutation in 0..10 {
        let mut forged = good.clone();
        let child = forged
            .units
            .iter_mut()
            .find(|u| u.semantic_type == "entity/decision")
            .unwrap();
        match mutation {
            0 => {
                child
                    .placements
                    .insert("/lifecycle_stage".into(), string("active"));
            }
            1 => {
                child
                    .lifecycle_provenance
                    .as_mut()
                    .unwrap()
                    .as_object_mut()
                    .unwrap()
                    .insert("declaring_adr_id".into(), string(&child.id));
            }
            2 => {
                child
                    .lifecycle_provenance
                    .as_mut()
                    .unwrap()
                    .as_object_mut()
                    .unwrap()
                    .remove("status_source_authority");
            }
            3 => {
                child.contextual_fact = None;
            }
            4 => {
                child
                    .contextual_fact
                    .as_mut()
                    .unwrap()
                    .value
                    .as_object_mut()
                    .unwrap()
                    .insert("extra_fact".into(), string("invented"));
            }
            5 => {
                child.semantic_extensions.clear();
            }
            6 => {
                child
                    .placements
                    .insert("/wrong_destination".into(), string("invented"));
            }
            7 => {
                child.coverage.clear();
            }
            8 => {}
            _ => {
                forged.complete_interpretation = Status::DispositionsQualified;
            }
        }
        if mutation == 8 {
            let duplicate = forged
                .units
                .iter()
                .find(|u| u.semantic_type == "entity/decision")
                .unwrap()
                .clone();
            forged.units.push(duplicate);
        }
        let r = verify_projection(
            &bundle().0,
            &bundle().1,
            &bundle().2,
            &j(&input),
            &refs(&input),
            &seal,
            &forged,
        );
        failed(&r);
        assert_eq!(r.status, Status::Rejected);
    }
}

#[test]
fn request_resource_permutations_preserve_complete_projection_and_seal() {
    let input = request(2);
    let seal = run(&input);
    let first = qualify(&input, &seal);
    let mut permuted = input.clone();
    permuted["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    permuted["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    let mut resources = bundle().1.clone();
    resources.reverse();
    let second = interpret(
        &bundle().0,
        &resources,
        &bundle().2,
        &j(&permuted),
        &refs(&permuted),
        &seal,
    );
    assert_eq!(first.status, Status::DispositionsQualified, "{first:#?}");
    assert_eq!(first, second);
    assert_eq!(seal, run(&permuted));
}

#[test]
fn source_rewrite_with_recalculated_digest_and_forged_context_fail_atomically() {
    let input = request(1);
    let original = run(&input);
    for mode in 0..4 {
        let mut seal = original.clone();
        let e = seal.evidence.as_mut().unwrap();
        match mode {
            0 => {
                let mut v =
                    candidate_source::decode_canonical_candidate(&e.basis.artifacts[0].bytes)
                        .unwrap();
                v.as_object_mut()
                    .unwrap()
                    .insert("status".into(), string("active"));
                let artifact = &mut e.basis.artifacts[0];
                artifact.bytes =
                    candidate_source::render_source(&artifact.source_schema, &v).unwrap();
                {
                    use sha2::{Digest, Sha256};
                    artifact.content_digest =
                        format!("sha256:{:x}", Sha256::digest(&artifact.bytes));
                }
            }
            1 => {
                e.context.scope_root.push_str("-forged");
            }
            2 => {
                seal.composition_records.clear();
            }
            _ => {
                e.basis.artifacts.push(e.retained_artifacts[1].clone());
            }
        }
        failed(&qualify(&input, &seal));
    }
    assert_eq!(original, run(&input));
}

#[test]
fn standalone_decision_retains_native_source_without_invented_lifecycle() {
    let mut input = request(1);
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .remove(0);
    input["request"]["compositions"] = json!([]);
    let seal = run(&input);
    assert_eq!(seal.status, SealStatus::Unavailable, "{seal:#?}");
    let r = qualify(&input, &seal);
    failed(&r);
    assert_eq!(r.status, Status::Unavailable);
    assert_eq!(
        input["request"]["fragments"][0]["semantic_type"],
        "entity/decision"
    );
    assert!(seal.evidence.is_none());
    let mut forged = seal.clone();
    forged.status = SealStatus::Sealed;
    let invalid = qualify(&input, &forged);
    failed(&invalid);
    assert_eq!(invalid.status, Status::Rejected);
}

#[test]
fn unknown_duplicate_dispositions_and_unknown_source_fields_are_not_omitted() {
    let mut a = Authority::qualify(&bundle().0, &bundle().1, &bundle().2).unwrap();
    let ty = a.types.get_mut("entity/decision").unwrap();
    let fields = ty
        .as_object_mut()
        .unwrap()
        .get_mut("field_dispositions")
        .unwrap()
        .as_array_mut()
        .unwrap();
    fields.push(fields[0].clone());
    assert!(a.field("entity/decision", "/id").is_err());
    let mut source = request(1)["request"]["fragments"][1]["fields"].clone();
    source["unknown_semantic_value"] = json!({"typed":[1,true,null]});
    let mut r = Projection::new();
    project_fields(&a, "entity/decision", &j(&source), &mut r);
    let r = r.finish();
    failed(&r);
    assert_eq!(r.status, Status::Rejected);
    assert!(r.findings.iter().any(|f| f.status == Status::Unavailable));
}

#[test]
fn schema_integrity_annotations_are_checked_and_unknown_keywords_stay_blocked() {
    let sealed = BTreeMap::from([(
        "example/1.0/schema".into(),
        j(&json!({"semanticDependencies":["missing/1.0/schema"]})),
    )]);
    assert!(qualified_schema_map(&sealed).is_err());
    let sealed = BTreeMap::from([(
        "example/1.0/schema".into(),
        j(&json!({"semanticDependencies":[],"inventedKeyword":true})),
    )]);
    let evaluated = qualified_schema_map(&sealed).unwrap();
    assert!(schema_validation::preflight_fragment(&evaluated, "example/1.0/schema", "").is_err());
}

#[test]
fn complete_structured_child_values_and_authored_membership_are_preserved() {
    let mut input = request(2);
    input["request"]["fragments"][1]["fields"]["alternatives_considered"] = json!([
        {"name":"Second","rejected_because":"Typed α"},
        {"name":"First","rejected_because":"Typed β"}]);
    input["request"]["fragments"][1]["fields"]["consequences"] =
        json!({"positive":["z","a","z"],"negative":[]});
    let seal = run(&input);
    let r = qualify(&input, &seal);
    assert_eq!(r.status, Status::DispositionsQualified, "{r:#?}");
    let child = r
        .units
        .iter()
        .find(|u| {
            u.id == input["request"]["fragments"][1]["fields"]["id"]
                .as_str()
                .unwrap()
        })
        .unwrap();
    for field in ["alternatives_considered", "consequences"] {
        assert_eq!(
            child.semantic_extensions[&format!("entity/decision#/{field}")],
            j(&input["request"]["fragments"][1]["fields"][field])
        );
    }
    let parent = r
        .units
        .iter()
        .find(|u| u.semantic_type == "adr/logical")
        .unwrap();
    let decoded = candidate_source::decode_canonical_candidate(
        &seal.evidence.as_ref().unwrap().basis.artifacts[0].bytes,
    )
    .unwrap();
    assert_eq!(
        parent.semantic_extensions["adr/logical#/decisions"],
        Json::Array(
            array(&decoded, "decisions")
                .iter()
                .map(|c| at(c, &["id"]).clone())
                .collect()
        )
    );
    assert!(parent.lifecycle_provenance.is_none() && parent.contextual_fact.is_none());
    assert!(parent.semantic_extensions["adr/logical#/decisions"]
        .as_array()
        .unwrap()
        .iter()
        .all(|id| id.as_str().is_some()));
}

#[test]
fn mixed_diagnostics_have_governed_precedence_and_stable_order() {
    let mut input = request(1);
    let original = run(&input);
    input["request"]["compositions"][0]["relation"] = json!("unknown");
    // Exact request receipt mismatch is independently Rejected; downstream
    // unavailable evidence cannot turn it into an unresolved dependency.
    let first = qualify(&input, &original);
    failed(&first);
    assert_eq!(first.status, Status::Rejected);
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    assert_eq!(first, qualify(&input, &original));
    assert!(!first
        .findings
        .iter()
        .any(|f| f.status == Status::Unresolved));
}

#[test]
fn record_or_location_alone_cannot_establish_declaring_ownership() {
    let a = Authority::qualify(&bundle().0, &bundle().1, &bundle().2).unwrap();
    let input = request(1);
    let seal = run(&input);
    let e = seal.evidence.as_ref().unwrap();
    let artifact = &e.basis.artifacts[0];
    let parent = candidate_source::decode_canonical_candidate(&artifact.bytes).unwrap();
    let child = &array(&parent, "decisions")[0];
    for mode in 0..3 {
        let mut forged = parent.clone();
        match mode {
            0 => {
                forged
                    .as_object_mut()
                    .unwrap()
                    .insert("id".into(), string(text(child, "id")));
            }
            1 => {
                forged
                    .as_object_mut()
                    .unwrap()
                    .insert("decisions".into(), Json::Array(vec![]));
            }
            _ => {
                forged.as_object_mut().unwrap().insert(
                    "decisions".into(),
                    Json::Array(vec![child.clone(), child.clone()]),
                );
            }
        }
        assert!(ownership(
            &a,
            &forged,
            child,
            artifact,
            &seal.composition_records,
            &e.retained_artifacts
        )
        .is_err());
    }
    assert!(ownership(&a, &parent, child, artifact, &[], &e.retained_artifacts).is_err());
}
#[test]
fn ai13_046_to_049_decision_ownership_and_typed_fields() {
    let oracle: Value = serde_json::from_str(include_str!(
        "../../contracts/architecture-interpretation/v1.3/resources/conformance.json"
    ))
    .unwrap();
    for case in &oracle["cases"].as_array().unwrap()[45..49] {
        assert_eq!(case["rule_id"], DECISION_OWNER);
        assert_eq!(case["expected"], "preserves");
    }
    for status in ["proposed", "accepted", "deprecated", "superseded"] {
        let mut input = request(2);
        input["request"]["fragments"][0]["fields"]["status"] = json!(status);
        let seal = run(&input);
        let r = qualify(&input, &seal);
        assert_eq!(r.status, Status::DispositionsQualified, "{r:#?}");
        let parent = r
            .units
            .iter()
            .find(|u| u.semantic_type == "adr/logical")
            .unwrap();
        assert_eq!(parent.placements["/lifecycle_stage"], string(status));
        for child in r
            .units
            .iter()
            .filter(|u| u.semantic_type == "entity/decision")
        {
            assert_eq!(child.placements["/lifecycle_stage"], string(status));
            let carrier = child.lifecycle_provenance.as_ref().unwrap();
            assert_eq!(text(carrier, "declaring_adr_id"), parent.id);
            assert!(carrier.get("lifecycle_stage").is_none());
            assert_eq!(
                text(at(carrier, &["ownership_rule"]), "rule_id"),
                DECISION_OWNER
            );
            assert_eq!(
                child.contextual_fact.as_ref().unwrap().semantic_identity,
                child.id
            );
            for coverage in &child.coverage {
                if text(&coverage.destination, "kind") == "semantic_extension" {
                    assert_eq!(
                        child.semantic_extensions[&coverage.semantic_field_key],
                        coverage.source_value
                    );
                }
            }
        }
    }
}
