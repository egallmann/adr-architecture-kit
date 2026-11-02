use super::*;
use crate::identity_representation::tests::{
    document, inputs, j, sealed, selections, source, uuid,
};
use serde_json::json;

fn failure(p: &Projection, status: Status) {
    assert_eq!(p.status(), status, "{:?}", p.findings());
    assert!(p.units().is_empty());
    assert!(p.representations.is_none());
    assert!(p.authorities.is_empty());
    assert!(p.basis_digest.is_empty());
    assert_eq!(p.complete_interpretation(), Status::Unavailable);
}
fn run(v: serde_json::Value) -> (SealedSources, Projection) {
    let s = sealed(v);
    let p = execute(inputs(), Some(&s), &selections());
    (s, p)
}
#[test]
fn native_logical_decision_and_lifecycle_free_proposition_execute() {
    let (s, p) = run(document(1));
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    assert_eq!(p.units().len(), 3);
    let root = &p.units[0];
    let decision = &p.units[1];
    let proposition = &p.units[2];
    assert_eq!(root.placements["/lifecycle_stage"], string("accepted"));
    assert_eq!(
        root.semantic_extensions["adr/logical#/context"],
        j(json!("Unicode 🧭\n  exact content"))
    );
    assert_eq!(
        root.semantic_extensions["adr/logical#/decisions"],
        j(json!([uuid(1000, 2)]))
    );
    assert_eq!(decision.placements["/summary"], string("Exact Unicode π"));
    assert_eq!(decision.placements["/lifecycle_stage"], string("accepted"));
    let carrier = decision.lifecycle_provenance.as_ref().unwrap();
    assert_eq!(*get(carrier, "declaring_adr_id"), string(uuid(1, 1)));
    assert_eq!(
        *get(get(carrier, "ownership_rule"), "rule_id"),
        string("declaring-lifecycle.adr-logical.decisions")
    );
    assert_eq!(
        *get(get(carrier, "ownership_rule"), "version"),
        string("1.3")
    );
    assert!(carrier.get("lifecycle_stage").is_none());
    assert_eq!(
        decision.contextual_fact.as_ref().unwrap().semantic_identity,
        decision.id
    );
    assert_eq!(
        proposition.placements["/statement"],
        string("Preserve meaning")
    );
    assert_eq!(proposition.placements["/normative_force"], string("MUST"));
    assert!(!proposition.placements.contains_key("/lifecycle_stage"));
    assert!(proposition.contextual_fact.is_none());
    assert!(proposition.lifecycle_provenance.is_none());
    assert_eq!(
        verify(inputs(), Some(&s), &selections(), &p).status(),
        Status::Verified
    );
    assert_eq!(p.complete_interpretation(), Status::Unavailable);
}
#[test]
fn four_literal_lifecycles_and_all_present_fields_are_accounted() {
    for status in ["proposed", "accepted", "deprecated", "superseded"] {
        let mut v = document(1);
        v["status"] = json!(status);
        v["context"] = json!(if status == "proposed" {
            String::new()
        } else {
            "Exact Unicode 🧭 ".repeat(4096)
        });
        v["decisions"][0]["alternatives_considered"] = json!([{"name":"B","rejected_because":"X"},{"name":"A","rejected_because":"Y"},{"name":"A","rejected_because":"Y"}]);
        let (s, p) = run(v.clone());
        assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
        for u in &p.units[0..2] {
            assert_eq!(u.placements["/lifecycle_stage"], string(status));
        }
        assert_eq!(p.units[0].coverage.len(), v.as_object().unwrap().len());
        assert_eq!(
            p.units[1].coverage.len(),
            v["decisions"][0].as_object().unwrap().len()
        );
        assert_eq!(
            p.units[1].semantic_extensions["entity/decision#/alternatives_considered"],
            j(
                json!([{"name":"B","rejected_because":"X"},{"name":"A","rejected_because":"Y"},{"name":"A","rejected_because":"Y"}])
            )
        );
        assert_eq!(
            verify(inputs(), Some(&s), &selections(), &p).status(),
            Status::Verified
        );
    }
}
#[test]
fn inverse_verifier_rejects_omissions_mutations_forged_context_and_receipts() {
    let (s, p) = run(document(1));
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    for n in 0..19 {
        let mut bad = p.clone();
        match n {
            0 => {
                bad.units[0]
                    .semantic_extensions
                    .remove("adr/logical#/context");
            }
            1 => {
                bad.units[1]
                    .semantic_extensions
                    .insert("entity/decision#/rationale".into(), string("changed"));
            }
            2 => {
                bad.units[1]
                    .placements
                    .insert("/lifecycle_stage".into(), string("active"));
            }
            3 => {
                bad.units[1].id = uuid(1, 99);
            }
            4 => {
                let c = bad.units[0].coverage[0].clone();
                bad.units[1].coverage.push(c);
            }
            5 => bad.units[0].coverage.clear(),
            6 => bad.units[1].contextual_fact = None,
            7 => bad.units[1].lifecycle_provenance = None,
            8 => {
                bad.units[1]
                    .contextual_fact
                    .as_mut()
                    .unwrap()
                    .semantic_identity = uuid(1, 99)
            }
            9 => {
                bad.units[1].lifecycle_provenance = Some(j(json!({"declaring_adr_id":uuid(1,99)})));
            }
            10 => {
                bad.units[2]
                    .placements
                    .insert("/lifecycle_stage".into(), string("accepted"));
            }
            11 => {
                bad.units[0]
                    .placements
                    .insert("/summary".into(), string("fallback"));
            }
            12 => {
                bad.units.push(bad.units[1].clone());
            }
            13 => {
                bad.units.pop();
            }
            14 => bad.status = Status::Verified,
            15 => bad.basis_digest = "sha256:forged".into(),
            16 => bad.representations = None,
            17 => {
                bad.units[1].coverage[0].destination = j(
                    json!({"kind":"compatibility_projection","path":"/relationships/compatibility[]"}),
                );
            }
            _ => {
                bad.units[1].contextual_fact.as_mut().unwrap().value =
                    j(json!({"declaring_adr_id":uuid(1,99)}));
            }
        }
        failure(
            &verify(inputs(), Some(&s), &selections(), &bad),
            Status::Rejected,
        );
    }
}
#[test]
fn independently_rebound_changed_source_cannot_replay_old_fields() {
    let (_, p) = run(document(1));
    let mut v = document(1);
    v["context"] = json!("changed");
    let s = sealed(v);
    failure(
        &verify(inputs(), Some(&s), &selections(), &p),
        Status::Rejected,
    );
}
#[test]
fn unordered_multisets_preserve_occurrences_and_ordered_membership_is_significant() {
    let mut v = document(1);
    v["decisions"][0]["alternatives_considered"] = json!([{"name":"B","rejected_because":"X"},{"name":"A","rejected_because":"Y"},{"name":"A","rejected_because":"Y"}]);
    let second = json!({"id":uuid(3000,4),"alias_id":"DEC-0002","alias_name":"second-decision","summary":"Second","rationale":"Reason"});
    v["decisions"].as_array_mut().unwrap().push(second);
    let s = sealed(v);
    let mut selected = selections();
    selected.push(Selection {
        source_ref: "native:logical".into(),
        pointer: "/decisions/1".into(),
        semantic_type: "entity/decision".into(),
    });
    let p = execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    let mut reordered = p.clone();
    reordered.units[1].semantic_extensions.insert("entity/decision#/alternatives_considered".into(),j(json!([{"name":"A","rejected_because":"Y"},{"name":"B","rejected_because":"X"},{"name":"A","rejected_because":"Y"}])));
    assert_eq!(
        verify(inputs(), Some(&s), &selected, &reordered).status(),
        Status::Verified
    );
    reordered.units[1].semantic_extensions.insert(
        "entity/decision#/alternatives_considered".into(),
        j(json!([{"name":"A","rejected_because":"Y"},{"name":"B","rejected_because":"X"}])),
    );
    failure(
        &verify(inputs(), Some(&s), &selected, &reordered),
        Status::Rejected,
    );
    let mut changed = p.clone();
    changed.units[0].semantic_extensions.insert(
        "adr/logical#/decisions".into(),
        j(json!([uuid(3000, 4), uuid(1000, 2)])),
    );
    failure(
        &verify(inputs(), Some(&s), &selected, &changed),
        Status::Rejected,
    );
}
#[test]
fn optional_absence_differs_from_present_empty_and_no_fallback_is_invented() {
    let (_, absent) = run(document(1));
    let mut v = document(1);
    v["decisions"][0]["alternatives_considered"] = json!([]);
    let (s, present) = run(v);
    assert_eq!(
        present.status(),
        Status::Executed,
        "{:?}",
        present.findings()
    );
    assert!(!absent.units[1]
        .semantic_extensions
        .contains_key("entity/decision#/alternatives_considered"));
    assert_eq!(
        present.units[1].semantic_extensions["entity/decision#/alternatives_considered"],
        j(json!([]))
    );
    failure(
        &verify(inputs(), Some(&s), &selections(), &absent),
        Status::Rejected,
    );
}
#[test]
fn unselected_child_and_native_standalone_remain_unavailable() {
    let s = sealed(document(1));
    failure(
        &execute(inputs(), Some(&s), &[selections()[0].clone()]),
        Status::Unavailable,
    );
    failure(&execute(inputs(), None, &selections()), Status::Unavailable);
    let original = crate::identity_representation::tests::original(
        document(1)["decisions"][0].clone(),
        "native:fragment",
        "authoring/1.7/schema/adr-common.schema",
        "/definitions/decision",
        "authoring_fragment",
    );
    let s = identity::seal_sources(
        inputs(),
        &[original],
        Some("architecture-interpretation/1.3/detached-context"),
    )
    .unwrap();
    failure(
        &execute(
            inputs(),
            Some(&s),
            &[Selection {
                source_ref: "native:fragment".into(),
                pointer: String::new(),
                semantic_type: "entity/decision".into(),
            }],
        ),
        Status::Unavailable,
    );
}
#[test]
fn original_source_schema_and_canonical_identity_are_enforced_atomically() {
    let mut v = document(1);
    v["decisions"][0]["id"] = v["id"].clone();
    let s = sealed(v);
    failure(
        &execute(inputs(), Some(&s), &selections()),
        Status::Rejected,
    );
    let s = sealed(document(1));
    let mut selected = selections();
    selected[1].semantic_type = "entity/invariant".into();
    failure(&execute(inputs(), Some(&s), &selected), Status::Rejected);
}
#[test]
fn source_and_selection_permutations_do_not_change_semantic_units() {
    let mut second = document(2);
    second["id"] = json!(uuid(2, 11));
    second["decisions"][0]["id"] = json!(uuid(4000, 12));
    second["normative_propositions"] = json!([]);
    let a = source(document(1));
    let mut b = source(second);
    b.source_ref = "native:second".into();
    let mut selected = selections();
    selected.push(Selection {
        source_ref: "native:second".into(),
        pointer: "/decisions/0".into(),
        semantic_type: "entity/decision".into(),
    });
    selected.push(Selection {
        source_ref: "native:second".into(),
        pointer: String::new(),
        semantic_type: "adr/logical".into(),
    });
    let s = identity::seal_sources(
        inputs(),
        &[a.clone(), b.clone()],
        Some("architecture-interpretation/1.3/detached-context"),
    )
    .unwrap();
    let out = execute(inputs(), Some(&s), &selected);
    assert_eq!(out.status(), Status::Executed, "{:?}", out.findings());
    selected.reverse();
    let s2 = identity::seal_sources(
        inputs(),
        &[b, a],
        Some("architecture-interpretation/1.3/detached-context"),
    )
    .unwrap();
    let out2 = execute(inputs(), Some(&s2), &selected);
    assert_eq!(out, out2);
    assert_eq!(
        verify(inputs(), Some(&s2), &selected, &out).status(),
        Status::Verified
    );
}

#[test]
fn regular_native_children_share_the_qualified_field_engine() {
    let mut v = document(1);
    v["architectural_boundaries"] = json!([{"id":uuid(4000,4),"alias_id":"BOUND-0001","alias_name":"bounded-context","name":"A boundary","description":"Exact boundary narrative","rationale":"Boundary reason"}]);
    let s = sealed(v);
    let mut chosen = selections();
    chosen.push(Selection {
        source_ref: "native:logical".into(),
        pointer: "/architectural_boundaries/0".into(),
        semantic_type: "entity/boundary".into(),
    });
    let out = execute(inputs(), Some(&s), &chosen);
    assert_eq!(out.status(), Status::Executed, "{:?}", out.findings());
    let child = out
        .units
        .iter()
        .find(|u| u.semantic_type == "entity/boundary")
        .unwrap();
    assert_eq!(child.placements["/name"], string("A boundary"));
    assert_eq!(child.placements["/lifecycle_stage"], string("accepted"));
    assert_eq!(
        get(
            get(
                child.lifecycle_provenance.as_ref().unwrap(),
                "ownership_rule"
            ),
            "rule_id"
        ),
        &string("declaring-lifecycle.adr-logical.architectural_boundaries")
    );
    assert_eq!(
        verify(inputs(), Some(&s), &chosen, &out).status(),
        Status::Verified
    );
}
#[test]
fn rehashed_unauthorized_disposition_and_wrong_version_remain_rejected() {
    let s = sealed(document(1));
    let q = crate::candidate_authority::qualify(inputs().nm, inputs().ai, inputs().acc);
    let mut catalog: serde_json::Value = serde_json::to_value(&q.resources()[FD]).unwrap();
    catalog["semantic_types"][0]["field_dispositions"][6]["destination_ref"] = json!("entity_name");
    let (d, r) = crate::candidate_authority::tests::rehashed_with_resource(FD, j(catalog));
    let bad = Inputs {
        nm: crate::candidate_authority::Bundle {
            definition: &d[0],
            resources: &r[0],
        },
        ai: crate::candidate_authority::Bundle {
            definition: &d[1],
            resources: &r[1],
        },
        acc: crate::candidate_authority::Bundle {
            definition: &d[2],
            resources: &r[2],
        },
    };
    failure(&execute(bad, Some(&s), &selections()), Status::Rejected);
    failure(
        &verify(bad, Some(&s), &selections(), &Projection::failure(vec![])),
        Status::Rejected,
    );
    let mut wrong = d[1].clone();
    wrong
        .as_object_mut()
        .unwrap()
        .insert("semanticContractVersion".into(), string("1.3"));
    let bad = Inputs {
        ai: crate::candidate_authority::Bundle {
            definition: &wrong,
            resources: &r[1],
        },
        ..bad
    };
    let failed = execute(bad, None, &selections());
    failure(&failed, Status::Rejected);
    assert!(failed
        .findings()
        .iter()
        .any(|f| f.status == Status::Unavailable));
}
