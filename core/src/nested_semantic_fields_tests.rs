use super::super as semantic;
use super::*;
use crate::identity_representation::{
    self as identity,
    tests::{inputs, j, original, physical, uuid},
};
use serde_json::{json, Value};
const CONTEXT: &str = "architecture-interpretation/1.3/detached-context";
const OWN: &str = "architecture-interpretation/1.3/lifecycle-ownership";
const COMPONENT: &str = "declaring-lifecycle.adr-physical-component.component_specifications";
const INTERFACE: &str =
    "declaring-lifecycle.adr-physical-component.component_specifications.interfaces";
fn document(seed: u64, count: usize, children: usize) -> Value {
    let mut v = physical("physical-component");
    v["id"] = json!(uuid(3000 + seed * 10000, 1));
    v["alias_id"] = json!(format!("ADR-PC-{:04}", seed + 1));
    let template = v["component_specifications"][0].clone();
    v["component_specifications"]=Value::Array((0..count).map(|c| {
        let mut component=template.clone();component["id"]=json!(uuid(4000+seed*10000+c as u64,10+c as u64));
        component["alias_id"]=json!(format!("COMP-{:04}",c+1));component["alias_name"]=json!(format!("component-{c}"));
        component["responsibilities"]=json!(format!("  Exact responsibilities π {c}\n "));
        component["dependencies"]=json!([uuid(1,90),uuid(1,90)]);component["implements_capabilities"]=json!([uuid(1,91)]);component["realizes_entities"]=json!([uuid(1,92)]);
        component["generation_context"]["constraints"]=json!(["one","one"]);component["generation_context"]["success_criteria"]=json!(["Typed values"]);
        component["interfaces"]=Value::Array((0..children).map(|n| json!({"id":uuid(5000+seed*10000+c as u64*100+n as u64,100+c as u64*10+n as u64),"alias_id":format!("IFACE-{:04}",c*10+n+1),"alias_name":format!("interface-{c}-{n}"),"type":"REST","specification":format!(" Exact specification 🧭 {c}/{n}\n "),"contract_reference":uuid(1,93),"contract_tests":""})).collect());component
    }).collect());
    v
}
fn source(v: Value, name: &str) -> identity::OriginalSource {
    original(
        v,
        name,
        "authoring/1.7/schema/adr-physical-component.schema",
        "",
        "authoring_document",
    )
}
fn selections(v: &Value, name: &str) -> Vec<Selection> {
    let mut out = vec![];
    for (c, component) in v["component_specifications"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
    {
        out.push(Selection {
            source_ref: name.into(),
            pointer: format!("/component_specifications/{c}"),
            semantic_type: "entity/component".into(),
        });
        for n in 0..component["interfaces"].as_array().unwrap().len() {
            out.push(Selection {
                source_ref: name.into(),
                pointer: format!("/component_specifications/{c}/interfaces/{n}"),
                semantic_type: "entity/interface".into(),
            });
        }
    }
    out
}
fn fixture(v: Value) -> (SealedSources, Vec<Selection>) {
    let selected = selections(&v, "native:pc");
    let sealed =
        identity::seal_sources(inputs(), &[source(v, "native:pc")], Some(CONTEXT)).unwrap();
    (sealed, selected)
}
fn field_failure(p: &semantic::Projection, status: Status) {
    assert_eq!(p.status(), status, "{:?}", p.findings());
    assert!(p.units().is_empty());
    assert!(p.containment.is_empty());
    assert!(p.representations.is_none());
    assert!(p.authorities.is_empty());
    assert!(p.basis_digest.is_empty());
    assert_eq!(p.complete_interpretation(), Status::Unavailable);
}
fn label_failure(p: &Projection, status: Status) {
    assert_eq!(p.status(), status, "{:?}", p.findings());
    assert!(p.values().is_empty());
    assert!(p.semantic_evidence.is_none());
    assert!(p.authorities.is_empty());
    assert!(p.basis.is_empty());
    assert_eq!(p.complete_interpretation(), Status::Unavailable);
}
#[test]
fn nested_fields_and_three_catalog_labels_execute_with_distinct_identity_roles() {
    let v = document(0, 1, 2);
    let (s, selected) = fixture(v.clone());
    let original = s.clone();
    let p = execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    assert_eq!(p.values().len(), 5);
    let proof = p.semantics().unwrap();
    assert_eq!(proof.units().len(), 3);
    assert_eq!(proof.containment.len(), 3);
    let q = authority::qualify(inputs().nm, inputs().ai, inputs().acc);
    let catalog = &q.resources()[CATALOG];
    let mut covered = BTreeSet::new();
    let mut rules = BTreeSet::new();
    for u in proof.units() {
        let chosen = selected
            .iter()
            .find(|x| v.pointer(&x.pointer).unwrap()["id"].as_str() == Some(&u.id))
            .unwrap();
        let authored = v.pointer(&chosen.pointer).unwrap();
        assert_eq!(u.coverage.len(), authored.as_object().unwrap().len());
        for field in &u.coverage {
            covered.insert(field.semantic_field_key.clone());
            assert_eq!(
                field.source_value,
                j(authored[&field.semantic_field_key.split_once('#').unwrap().1[1..]].clone())
            );
        }
        let chain = &proof.containment[&u.id];
        assert_eq!(chain.declaring.id, uuid(3000, 1));
        assert_eq!(chain.child.id, u.id);
        assert_eq!(chain.child.selection, *chosen);
        assert_eq!(u.placements["/lifecycle_stage"], string("accepted"));
        let carrier = u.lifecycle_provenance.as_ref().unwrap();
        assert_eq!(get(carrier, "declaring_adr_id"), &string(uuid(3000, 1)));
        assert_eq!(
            text(carrier, "declaring_adr_semantic_type"),
            "adr/physical-component"
        );
        assert!(carrier.get("lifecycle_stage").is_none());
        assert_eq!(text(get(carrier, "ownership_rule"), "version"), "1.3");
        assert_eq!(
            text(get(carrier, "ownership_rule"), "canonical_resource_key"),
            OWN
        );
        if u.semantic_type == "entity/interface" {
            assert_eq!(chain.parent.id, uuid(4000, 10));
            assert_eq!(text(&chain.rule, "rule_id"), INTERFACE);
            assert_eq!(array(&chain.rule, "ownership_schema_path").len(), 2);
        } else {
            assert_eq!(chain.parent, chain.declaring);
            assert_eq!(text(&chain.rule, "rule_id"), COMPONENT);
            assert_eq!(
                u.semantic_extensions["entity/component#/interfaces"],
                j(json!([uuid(5000, 100), uuid(5001, 101)]))
            );
            assert_eq!(
                u.semantic_extensions["entity/component#/dependencies"],
                j(json!([uuid(1, 90), uuid(1, 90)]))
            );
        }
    }
    assert_eq!(covered.len(), 18); // All 11 Component and seven Interface fields in these sources.
    for l in p.values() {
        rules.insert(l.definition.rule_id.clone());
        let chosen = selected
            .iter()
            .find(|x| v.pointer(&x.pointer).unwrap()["id"].as_str() == Some(&l.id))
            .unwrap();
        let authored = v.pointer(&chosen.pointer).unwrap();
        assert_eq!(
            l.value,
            authored[&l.definition.source_field].as_str().unwrap()
        );
        let t = array(catalog, "types")
            .iter()
            .find(|t| text(t, "semantic_type") == l.definition.semantic_type)
            .unwrap();
        assert!(array(t, "outputs").contains(&l.definition.declaration));
    }
    assert_eq!(rules.len(), 3);
    assert_eq!(qualify_catalog(inputs()).unwrap().len(), 26);
    assert_eq!(
        array(catalog, "types")
            .iter()
            .flat_map(|t| array(t, "outputs"))
            .filter(|o| text(o, "status") == "BLOCKED")
            .count(),
        215
    );
    assert_eq!(
        verify(inputs(), Some(&s), &selected, &p).status(),
        Status::Verified
    );
    assert_eq!(s, original);
    assert_eq!(p.complete_interpretation(), Status::Unavailable);
}
#[test]
fn four_literal_statuses_come_from_the_declaring_adr_not_the_component() {
    for status in ["proposed", "accepted", "deprecated", "superseded"] {
        let mut v = document(0, 1, 1);
        v["status"] = json!(status);
        let (s, selected) = fixture(v);
        let p = execute(inputs(), Some(&s), &selected);
        assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
        for u in p.semantics().unwrap().units() {
            assert_eq!(u.placements["/lifecycle_stage"], string(status));
            assert!(u
                .lifecycle_provenance
                .as_ref()
                .unwrap()
                .get("lifecycle_stage")
                .is_none());
        }
        assert_eq!(
            verify(inputs(), Some(&s), &selected, &p).status(),
            Status::Verified
        );
    }
}
#[test]
fn multiple_parents_declaring_adrs_and_permutations_preserve_identity_and_proof() {
    let a = document(0, 2, 2);
    let mut b = document(1, 2, 2);
    b["status"] = json!("deprecated");
    let mut selected = selections(&a, "native:a");
    selected.extend(selections(&b, "native:b"));
    let first = source(a, "native:a");
    let second = source(b, "native:b");
    let s =
        identity::seal_sources(inputs(), &[first.clone(), second.clone()], Some(CONTEXT)).unwrap();
    let reverse = identity::seal_sources(inputs(), &[second, first], Some(CONTEXT)).unwrap();
    let p = execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    assert_eq!(p.semantics().unwrap().units().len(), 12);
    assert_eq!(p.values().len(), 20);
    for u in p.semantics().unwrap().units() {
        let c = &p.semantics().unwrap().containment[&u.id];
        let expected = if c.declaring.selection.source_ref == "native:a" {
            "accepted"
        } else {
            "deprecated"
        };
        assert_eq!(u.placements["/lifecycle_stage"], string(expected));
        assert_eq!(c.parent.selection.source_ref, c.child.selection.source_ref);
    }
    selected.reverse();
    assert_eq!(p, execute(inputs(), Some(&reverse), &selected));
    let (d, mut r) = crate::candidate_authority::tests::bundles();
    for x in &mut r {
        x.reverse();
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
    assert_eq!(
        verify(perm, Some(&reverse), &selected, &p).status(),
        Status::Verified
    );
}
#[test]
fn missing_conflicting_parent_declaring_and_schema_evidence_fails_qualification() {
    let (s, selected) = fixture(document(0, 2, 1));
    let p = semantic::prepare(inputs(), Some(&s), &selected).unwrap();
    let iface = p
        .selected
        .iter()
        .find(|u| u.selection.semantic_type == "entity/interface")
        .unwrap();
    assert!(identity::native_ownership(&p.q, &p.all, iface).is_ok());
    for n in 0..10 {
        let mut child = iface.clone();
        let mut all = p.all.clone();
        match n {
            0 => child.parent = None,
            1 => child.parent.as_mut().unwrap().id = uuid(1, 99),
            2 => child.owner.as_mut().unwrap().1 = uuid(1, 99),
            3 => {
                child.parent = Some(identity::Occurrence {
                    selection: all
                        .iter()
                        .find(|u| {
                            u.selection.semantic_type == "entity/component"
                                && u.selection.pointer == "/component_specifications/1"
                        })
                        .unwrap()
                        .selection
                        .clone(),
                    id: uuid(4001, 11),
                })
            }
            4 => {
                let parent = all
                    .iter()
                    .find(|u| Some(&u.selection) == child.parent.as_ref().map(|p| &p.selection))
                    .unwrap()
                    .clone();
                all.push(parent);
            }
            5 => {
                let parent = all
                    .iter_mut()
                    .find(|u| Some(&u.selection) == child.parent.as_ref().map(|p| &p.selection))
                    .unwrap();
                parent
                    .row
                    .as_object_mut()
                    .unwrap()
                    .insert("source_schema".into(), Json::Null);
            }
            6 => {
                child
                    .row
                    .as_object_mut()
                    .unwrap()
                    .insert("source_schema".into(), Json::Null);
            }
            7 => child.owner.as_mut().unwrap().2 = "/incorrect/*/interfaces/*".into(),
            8 => all.retain(|u| !u.selection.pointer.is_empty()),
            _ => {
                child
                    .value
                    .as_object_mut()
                    .unwrap()
                    .insert("id".into(), string(uuid(1, 99)));
            }
        }
        let error = identity::native_ownership(&p.q, &all, &child).unwrap_err();
        assert_eq!(
            error[0].status,
            if [0, 7, 8].contains(&n) {
                Status::Unavailable
            } else {
                Status::Rejected
            },
            "{n}: {error:?}"
        );
    }
}
#[test]
fn inverse_rejects_nested_witness_carrier_fields_membership_and_label_mutations() {
    let (s, selected) = fixture(document(0, 1, 2));
    let p = execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    for n in 0..16 {
        let mut bad = p.clone();
        let proof = bad.semantic_evidence.as_mut().unwrap();
        let iface = proof
            .units
            .iter()
            .position(|u| u.semantic_type == "entity/interface")
            .unwrap();
        let component = proof
            .units
            .iter()
            .position(|u| u.semantic_type == "entity/component")
            .unwrap();
        let id = proof.units[iface].id.clone();
        match n {
            0 => proof.containment.get_mut(&id).unwrap().parent.id = uuid(1, 99),
            1 => proof.containment.get_mut(&id).unwrap().declaring.id = uuid(1, 99),
            2 => {
                proof.containment.remove(&id);
            }
            3 => {
                proof
                    .containment
                    .insert(uuid(1, 99), proof.containment[&id].clone());
            }
            4 => {
                proof
                    .containment
                    .get_mut(&id)
                    .unwrap()
                    .rule
                    .as_object_mut()
                    .unwrap()
                    .insert("ownership_schema_path".into(), Json::Array(vec![]));
            }
            5 => {
                proof.units[iface]
                    .lifecycle_provenance
                    .as_mut()
                    .unwrap()
                    .as_object_mut()
                    .unwrap()
                    .insert("declaring_adr_id".into(), string(uuid(4000, 10)));
            }
            6 => {
                proof.units[iface]
                    .placements
                    .insert("/lifecycle_stage".into(), string("active"));
            }
            7 => {
                proof.units[component]
                    .semantic_extensions
                    .get_mut("entity/component#/interfaces")
                    .unwrap()
                    .as_array_mut()
                    .unwrap()
                    .reverse();
            }
            8 => {
                proof.units[component]
                    .semantic_extensions
                    .remove("entity/component#/interfaces");
            }
            9 => {
                proof.units[iface]
                    .semantic_extensions
                    .insert("entity/interface#/specification".into(), string("changed"));
            }
            10 => {
                proof.units[component].semantic_extensions.insert(
                    "entity/component#/responsibilities".into(),
                    string("changed"),
                );
            }
            11 => bad.values[0].value.push(' '),
            12 => proof.representations = None,
            13 => bad.status = Status::Verified,
            14 => {
                proof
                    .containment
                    .get_mut(&id)
                    .unwrap()
                    .rule
                    .as_object_mut()
                    .unwrap()
                    .insert("source_instance_pattern".into(), string("/interfaces/*"));
            }
            _ => {
                proof
                    .containment
                    .get_mut(&id)
                    .unwrap()
                    .rule
                    .as_object_mut()
                    .unwrap()
                    .insert("parent_identity_selector".into(), string("/alias_id"));
            }
        }
        label_failure(
            &verify(inputs(), Some(&s), &selected, &bad),
            Status::Rejected,
        );
    }
}
#[test]
fn valid_source_changes_cannot_rebind_old_field_or_containment_evidence() {
    let original = document(0, 2, 2);
    let (s, selected) = fixture(original.clone());
    let p = semantic::execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    for n in 0..3 {
        let mut v = original.clone();
        match n {
            0 => {
                v["component_specifications"][0]["responsibilities"] =
                    json!("Changed original responsibility")
            }
            1 => {
                v["component_specifications"][0]["interfaces"][0]["specification"] =
                    json!("Changed original specification")
            }
            _ => {
                let child = v["component_specifications"][0]["interfaces"]
                    .as_array_mut()
                    .unwrap()
                    .remove(0);
                v["component_specifications"][1]["interfaces"]
                    .as_array_mut()
                    .unwrap()
                    .push(child);
            }
        }
        let (new, chosen) = fixture(v);
        let mut stale = p.clone();
        stale.basis_digest = semantic::prepare(inputs(), Some(&new), &chosen)
            .unwrap()
            .basis;
        stale.representations = Some(identity::execute(inputs(), Some(&new), &chosen));
        field_failure(
            &semantic::verify(inputs(), Some(&new), &chosen, &stale),
            Status::Rejected,
        );
        let fresh = semantic::execute(inputs(), Some(&new), &chosen);
        assert_eq!(fresh.status(), Status::Executed, "{:?}", fresh.findings());
        assert_eq!(
            semantic::verify(inputs(), Some(&new), &chosen, &fresh).status(),
            Status::Verified
        );
        if n == 2 {
            assert_eq!(
                fresh.containment[&uuid(5000, 100)].parent.id,
                uuid(4001, 11)
            );
            assert_eq!(
                fresh.containment[&uuid(5000, 100)].declaring.id,
                uuid(3000, 1)
            );
        }
    }
}
#[test]
fn duplicate_identities_and_incomplete_or_fragment_context_fail_atomically() {
    for n in 0..2 {
        let mut v = document(0, 1, 2);
        v["component_specifications"][0]["interfaces"][1]["id"] = if n == 0 {
            v["component_specifications"][0]["id"].clone()
        } else {
            v["component_specifications"][0]["interfaces"][0]["id"].clone()
        };
        let (s, selected) = fixture(v);
        label_failure(&execute(inputs(), Some(&s), &selected), Status::Rejected);
    }
    let v = document(0, 1, 1);
    let (s, mut selected) = fixture(v.clone());
    selected.pop();
    label_failure(&execute(inputs(), Some(&s), &selected), Status::Unavailable);
    let nested = execute(inputs(), Some(&s), &selections(&v, "native:pc"));
    assert_eq!(nested.status(), Status::Executed, "{:?}", nested.findings());
    assert!(nested
        .semantics()
        .unwrap()
        .units()
        .iter()
        .all(|u| !u.semantic_type.starts_with("adr/")));
    assert_eq!(nested.complete_interpretation(), Status::Unavailable);
    let fragment = original(
        v["component_specifications"][0].clone(),
        "native:fragment",
        "authoring/1.7/schema/adr-common.schema",
        "/definitions/component",
        "authoring_fragment",
    );
    let s = identity::seal_sources(inputs(), &[fragment], Some(CONTEXT)).unwrap();
    let chosen = vec![
        Selection {
            source_ref: "native:fragment".into(),
            pointer: String::new(),
            semantic_type: "entity/component".into(),
        },
        Selection {
            source_ref: "native:fragment".into(),
            pointer: "/interfaces/0".into(),
            semantic_type: "entity/interface".into(),
        },
    ];
    label_failure(&execute(inputs(), Some(&s), &chosen), Status::Unavailable);
}
#[test]
fn rehashed_unauthorized_nested_ownership_path_cannot_qualify() {
    let q = authority::qualify(inputs().nm, inputs().ai, inputs().acc);
    let mut resource: Value = serde_json::to_value(&q.resources()[OWN]).unwrap();
    let row = resource["rows"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|r| r["rule_id"] == INTERFACE)
        .unwrap();
    row["ownership_schema_path"][0]["schema_pointer"] =
        json!("/properties/component_specifications/items/properties/interfaces/items");
    let (d, r) = crate::candidate_authority::tests::rehashed_with_resource(OWN, j(resource));
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
    let (s, selected) = fixture(document(0, 1, 1));
    label_failure(&execute(bad, Some(&s), &selected), Status::Rejected);
}
