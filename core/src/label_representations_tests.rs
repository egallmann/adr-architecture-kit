use super::*;
use crate::identity_representation::{
    self as identity,
    tests::{document, inputs, j, original, physical, sealed, selections, uuid},
};
use serde_json::{json, Value};
const CONTEXT: &str = "architecture-interpretation/1.3/detached-context";
fn failure(p: &Projection, status: Status) {
    assert_eq!(p.status(), status, "{:?}", p.findings());
    assert!(p.values().is_empty());
    assert!(p.semantics().is_none());
    assert!(p.authorities.is_empty());
    assert!(p.basis.is_empty());
    assert_eq!(p.complete_interpretation(), Status::Unavailable);
}
fn rich() -> (Value, Vec<Selection>) {
    let mut v = document(1);
    let mut selected = selections();
    let children = [
        (
            "architectural_boundaries",
            "entity/boundary",
            json!({"alias_id":"BOUND-0001","alias_name":"a-boundary","name":"Boundary","description":"Boundary description","rationale":"Reason"}),
        ),
        (
            "capabilities",
            "entity/capability",
            json!({"alias_id":"CAP-0001","alias_name":"a-capability","name":"Capability","description":"Capability description"}),
        ),
        (
            "contracts",
            "entity/contract",
            json!({"alias_id":"CONTRACT-0001","alias_name":"a-contract","parties":[uuid(1,1),uuid(1000,2)],"protocol":"Protocol","guarantees":"Guarantees"}),
        ),
        (
            "evidence_expectations",
            "entity/evidence_expectation",
            json!({"alias_id":"EVID-TEST","alias_name":"an-expectation","kind":"test","description":"Expected evidence"}),
        ),
        (
            "gaps",
            "entity/gap",
            json!({"alias_id":"GAP-0001","alias_name":"a-gap","question":"Question?","impact":"high","blocking":true}),
        ),
        (
            "invariants",
            "entity/invariant",
            json!({"alias_id":"INV-0001","alias_name":"an-invariant","statement":"Statement","scope":"Architecture","enforcement_level":"must","enforcement_mechanism":"test","verification_method":"automated","rationale":"Reason"}),
        ),
    ];
    for (n, (property, ty, mut child)) in children.into_iter().enumerate() {
        child["id"] = json!(uuid(5000 + n as u64, 10 + n as u64));
        v[property] = json!([child]);
        selected.push(Selection {
            source_ref: "native:logical".into(),
            pointer: format!("/{property}/0"),
            semantic_type: ty.into(),
        });
    }
    (v, selected)
}
#[test]
fn complete_inventory_is_derived_from_actual_qualified_authority() {
    let defs = qualify_catalog(inputs()).unwrap();
    assert_eq!(defs.len(), 26);
    let q = authority::qualify(inputs().nm, inputs().ai, inputs().acc);
    let c = &q.resources()[CATALOG];
    let expected: BTreeMap<_, _> = array(c, "types")
        .iter()
        .flat_map(|t| {
            array(t, "outputs")
                .iter()
                .filter(|o| text(get(o, "producer"), "kind") == "literal_string_copy")
                .map(move |o| {
                    (
                        (
                            text(t, "semantic_type").to_owned(),
                            text(o, "destination").to_owned(),
                        ),
                        o.clone(),
                    )
                })
        })
        .collect();
    let actual: BTreeMap<_, _> = defs
        .iter()
        .map(|d| {
            (
                (d.semantic_type.clone(), d.destination.clone()),
                d.declaration.clone(),
            )
        })
        .collect();
    assert_eq!(actual, expected);
    for d in defs {
        assert!(!d.semantic_field_key.is_empty());
        assert_eq!(
            text(&d.rule_authority, "canonical_resource_key"),
            "architecture-interpretation/1.4/required-output-derivations"
        );
        assert_eq!(text(&d.rule_authority, "schema_pointer"), "/operation");
        assert!(["regular", "normative-proposition"].contains(&d.branch.as_str()));
    }
    assert_eq!(array(c, "types").len(), 27);
    assert_eq!(
        array(c, "types")
            .iter()
            .flat_map(|t| array(t, "outputs"))
            .filter(|o| text(o, "status") == "BLOCKED")
            .count(),
        215
    );
}
#[test]
fn logical_and_owned_regular_and_proposition_labels_preserve_semantic_ownership() {
    let (v, selected) = rich();
    let s = sealed(v.clone());
    let before = s.clone();
    let p = execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    assert_eq!(p.values().len(), 14);
    assert_eq!(
        p.values()
            .iter()
            .map(|l| l.definition.semantic_type.as_str())
            .collect::<BTreeSet<_>>()
            .len(),
        9
    );
    for label in p.values() {
        let pointer = &selected
            .iter()
            .find(|s| s.semantic_type == label.definition.semantic_type)
            .unwrap()
            .pointer;
        let source = v.pointer(pointer).unwrap();
        assert_eq!(
            label.value,
            source[&label.definition.source_field].as_str().unwrap()
        );
        let u = p
            .semantics()
            .unwrap()
            .units()
            .iter()
            .find(|u| u.id == label.id)
            .unwrap();
        assert!(!u.placements.contains_key(&label.definition.destination));
        if label.definition.source_field != "alias_name" {
            let value = u
                .semantic_extensions
                .get(&label.definition.semantic_field_key)
                .or_else(|| {
                    u.placements
                        .get(&format!("/{}", label.definition.source_field))
                })
                .unwrap();
            assert_eq!(value, &string(&label.value));
        }
    }
    let units = p.semantics().unwrap().units();
    let decision = units
        .iter()
        .find(|u| u.semantic_type == "entity/decision")
        .unwrap();
    assert_eq!(decision.placements["/lifecycle_stage"], string("accepted"));
    assert!(decision.lifecycle_provenance.is_some());
    let prop = units
        .iter()
        .find(|u| u.semantic_type == "entity/normative_proposition")
        .unwrap();
    assert!(!prop.placements.contains_key("/lifecycle_stage"));
    assert!(prop.lifecycle_provenance.is_none());
    assert_eq!(
        verify(inputs(), Some(&s), &selected, &p).status(),
        Status::Verified
    );
    assert_eq!(s, before);
    assert_eq!(p.complete_interpretation(), Status::Unavailable);
}
#[test]
fn implementation_decision_uses_qualified_physical_declaring_context() {
    let mut v = physical("physical-component");
    v["implementation_decisions"] = json!([{"id":uuid(6000,6),"alias_id":"IMPL-0001","alias_name":"implementation-label","summary":"Substantive summary","rationale":"Reason"}]);
    let raw = original(
        v,
        "native:physical",
        "authoring/1.7/schema/adr-physical-component.schema",
        "",
        "authoring_document",
    );
    let s = identity::seal_sources(inputs(), &[raw], Some(CONTEXT)).unwrap();
    let selected = vec![Selection {
        source_ref: "native:physical".into(),
        pointer: "/implementation_decisions/0".into(),
        semantic_type: "entity/implementation_decision".into(),
    }];
    let p = execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    assert_eq!(p.values().len(), 1);
    assert_eq!(p.values()[0].value, "implementation-label");
    assert_eq!(
        verify(inputs(), Some(&s), &selected, &p).status(),
        Status::Verified
    );
}
#[test]
fn exact_strings_include_source_valid_empty_long_unicode_case_and_whitespace() {
    for value in [
        String::new(),
        "  Case É e\u{301} 🧭\n\t exact  ".repeat(4096),
    ] {
        let mut v = document(1);
        v["context"] = json!(value);
        let s = sealed(v);
        let p = execute(inputs(), Some(&s), &selections());
        assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
        assert_eq!(
            p.values()
                .iter()
                .find(|l| l.definition.semantic_type == "adr/logical")
                .unwrap()
                .value,
            value
        );
        assert_eq!(
            verify(inputs(), Some(&s), &selections(), &p).status(),
            Status::Verified
        );
    }
}
#[test]
fn inverse_rejects_mutated_output_rule_selectors_duplicates_and_receipts_atomically() {
    let s = sealed(document(1));
    let p = execute(inputs(), Some(&s), &selections());
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    for n in 0..13 {
        let mut bad = p.clone();
        match n {
            0 => bad.values[0].value.push(' '),
            1 => {
                bad.values.pop();
            }
            2 => bad.values.push(bad.values[0].clone()),
            3 => bad.values[0].definition.source_field = "title".into(),
            4 => bad.values[0].definition.rule_id = "forged".into(),
            5 => bad.values[0].definition.destination = "/name".into(),
            6 => bad.values[0].definition.source_schema = Json::Null,
            7 => bad.values[0].definition.rule_authority = Json::Null,
            8 => bad.basis = "forged".into(),
            9 => bad.authorities.clear(),
            10 => bad.status = Status::Verified,
            11 => bad.semantic_evidence = None,
            _ => bad.values[0].id = uuid(1, 99),
        }
        failure(
            &verify(inputs(), Some(&s), &selections(), &bad),
            Status::Rejected,
        );
    }
}
#[test]
fn original_semantic_extensions_are_independently_verified() {
    let s = sealed(document(1));
    let p = execute(inputs(), Some(&s), &selections());
    for remove in [true, false] {
        let mut bad = p.clone();
        let root = &mut bad.semantic_evidence.as_mut().unwrap().units[0];
        if remove {
            root.semantic_extensions.remove("adr/logical#/context");
        } else {
            root.semantic_extensions
                .insert("adr/logical#/context".into(), string("changed"));
        }
        failure(
            &verify(inputs(), Some(&s), &selections(), &bad),
            Status::Rejected,
        );
    }
    let mut changed = document(1);
    changed["context"] = json!("New original semantic content");
    let changed = sealed(changed);
    let mut stale = p.clone();
    stale.semantic_evidence = Some(super::super::execute(
        inputs(),
        Some(&changed),
        &selections(),
    ));
    stale.basis = super::super::prepare(inputs(), Some(&changed), &selections())
        .unwrap()
        .basis;
    failure(
        &verify(inputs(), Some(&changed), &selections(), &stale),
        Status::Rejected,
    );
}
#[test]
fn authority_mutations_fail_independent_selector_and_operation_qualification() {
    let q = authority::qualify(inputs().nm, inputs().ai, inputs().acc);
    let engine = Authority::from_candidate(&q).unwrap();
    for n in 0..9 {
        let mut r = q.resources().clone();
        let mut c: Value = serde_json::to_value(&r[CATALOG]).unwrap();
        let t = c["types"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|t| t["semantic_type"] == "adr/logical")
            .unwrap();
        let o = t["outputs"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|o| o["producer"]["kind"] == "literal_string_copy")
            .unwrap();
        match n {
            0 => o["producer"]["inputs"][0]["schema_pointer"] = json!("/properties/title"),
            1 => o["destination_schema"]["schema_pointer"] = json!("/oneOf/1/properties/summary"),
            2 => o["status"] = json!("BLOCKED"),
            3 => o["classification"] = json!("semantic"),
            4 => o["producer"]["rule"]["local_rule"] = json!("fallback"),
            5 => {
                let duplicate = o.clone();
                t["outputs"].as_array_mut().unwrap().push(duplicate);
            }
            6 => c["operation"]["fallback"] = json!(true),
            7 => c["operation"]["id"] = json!("format_string"),
            _ => o["producer"]["inputs"][0]["content_digest"] = json!("sha256:forged"),
        }
        r.insert(CATALOG.into(), j(c));
        assert!(compile_inventory(&r, &engine).is_err(), "mutation {n}");
    }
}
#[test]
fn consistently_rehashed_unauthorized_authority_and_wrong_version_are_rejected() {
    let q = authority::qualify(inputs().nm, inputs().ai, inputs().acc);
    let mut c: Value = serde_json::to_value(&q.resources()[CATALOG]).unwrap();
    c["operation"]["fallback"] = json!(true);
    let (d, r) = crate::candidate_authority::tests::rehashed_with_resource(CATALOG, j(c));
    let bad = Inputs {
        nm: authority::Bundle {
            definition: &d[0],
            resources: &r[0],
        },
        ai: authority::Bundle {
            definition: &d[1],
            resources: &r[1],
        },
        acc: authority::Bundle {
            definition: &d[2],
            resources: &r[2],
        },
    };
    let s = sealed(document(1));
    failure(&execute(bad, Some(&s), &selections()), Status::Rejected);
    let mut wrong = d[1].clone();
    wrong
        .as_object_mut()
        .unwrap()
        .insert("semanticContractVersion".into(), string("1.4"));
    failure(
        &execute(
            Inputs {
                ai: authority::Bundle {
                    definition: &wrong,
                    resources: &r[1],
                },
                ..bad
            },
            None,
            &selections(),
        ),
        Status::Rejected,
    );
}
#[test]
fn selection_and_resource_permutations_do_not_change_qualified_values() {
    let s = sealed(document(1));
    let selected = selections();
    let p = execute(inputs(), Some(&s), &selected);
    let mut reverse = selected.clone();
    reverse.reverse();
    assert_eq!(p, execute(inputs(), Some(&s), &reverse));
    let (d, mut r) = crate::candidate_authority::tests::bundles();
    for items in &mut r {
        items.reverse();
    }
    let perm = Inputs {
        nm: authority::Bundle {
            definition: &d[0],
            resources: &r[0],
        },
        ai: authority::Bundle {
            definition: &d[1],
            resources: &r[1],
        },
        acc: authority::Bundle {
            definition: &d[2],
            resources: &r[2],
        },
    };
    assert_eq!(p, execute(perm, Some(&s), &selected));
    assert_eq!(
        verify(perm, Some(&s), &reverse, &p).status(),
        Status::Verified
    );
}
#[test]
fn absent_context_and_unavailable_receipts_never_release_partial_facts() {
    failure(&execute(inputs(), None, &selections()), Status::Unavailable);
    let s = sealed(document(1));
    let denied = Projection::failure(vec![]);
    failure(
        &verify(inputs(), Some(&s), &selections(), &denied),
        Status::Unavailable,
    );
    let mut partial = execute(inputs(), Some(&s), &selections());
    partial.status = Status::Unavailable;
    failure(
        &verify(inputs(), Some(&s), &selections(), &partial),
        Status::Rejected,
    );
    for ms in [253402300800000, 0xffffffffffff] {
        let s = sealed(document(ms));
        failure(
            &execute(inputs(), Some(&s), &selections()),
            Status::Unavailable,
        );
    }
    let mut duplicate = document(1);
    duplicate["decisions"][0]["id"] = duplicate["id"].clone();
    let s = sealed(duplicate);
    failure(
        &execute(inputs(), Some(&s), &selections()),
        Status::Rejected,
    );
}

#[test]
fn invalid_inputs_and_missing_declaring_context_never_activate_fallback() {
    for invalid in [json!(null), json!(42)] {
        let mut v = document(1);
        v["context"] = invalid;
        let raw = crate::identity_representation::tests::source(v);
        let e = identity::seal_sources(inputs(), &[raw], Some(CONTEXT)).unwrap_err();
        assert!(e.iter().any(|f| f.status == Status::Rejected));
    }
    let mut v = document(1);
    v.as_object_mut().unwrap().remove("context");
    assert!(identity::seal_sources(
        inputs(),
        &[crate::identity_representation::tests::source(v)],
        Some(CONTEXT)
    )
    .is_err());
    let child = document(1)["decisions"][0].clone();
    let raw = original(
        child,
        "native:fragment",
        "authoring/1.7/schema/adr-common.schema",
        "/definitions/decision",
        "authoring_fragment",
    );
    let s = identity::seal_sources(inputs(), &[raw], Some(CONTEXT)).unwrap();
    let chosen = vec![Selection {
        source_ref: "native:fragment".into(),
        pointer: String::new(),
        semantic_type: "entity/decision".into(),
    }];
    failure(&execute(inputs(), Some(&s), &chosen), Status::Unavailable);
}

#[test]
fn original_source_artifact_order_is_not_label_identity() {
    let first = crate::identity_representation::tests::source(document(1));
    let mut second = document(2);
    second["decisions"][0]["id"] = json!(uuid(4000, 4));
    second["normative_propositions"][0]["id"] = json!(uuid(5000, 5));
    second["alias_id"] = json!("ADR-L-0002");
    second["alias_name"] = json!("second-logical");
    let second = original(
        second,
        "native:second",
        "authoring/1.7/schema/adr-logical.schema",
        "",
        "authoring_document",
    );
    let a =
        identity::seal_sources(inputs(), &[first.clone(), second.clone()], Some(CONTEXT)).unwrap();
    let b = identity::seal_sources(inputs(), &[second, first], Some(CONTEXT)).unwrap();
    let mut chosen = selections();
    chosen.extend(selections().into_iter().map(|mut s| {
        s.source_ref = "native:second".into();
        s
    }));
    let p = execute(inputs(), Some(&a), &chosen);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    assert_eq!(p, execute(inputs(), Some(&b), &chosen));
    assert_eq!(
        verify(inputs(), Some(&b), &chosen, &p).status(),
        Status::Verified
    );
}
