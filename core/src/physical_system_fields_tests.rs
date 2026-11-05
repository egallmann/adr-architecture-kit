use super::super as semantic;
use super::*;
use crate::identity_representation::{
    self as identity,
    tests::{inputs, j, original, physical, uuid},
};
use serde_json::{json, Value};
const CONTEXT: &str = "architecture-interpretation/1.3/detached-context";
const OWN: &str = "architecture-interpretation/1.3/lifecycle-ownership";
const SYSTEM: &str = "declaring-lifecycle.adr-physical-system.system";
const FLOW: &str = "declaring-lifecycle.adr-physical-system.data_flows";
const BOUNDARY: &str = "declaring-lifecycle.adr-physical-system.system_boundaries";
fn document(seed: u64, count: usize) -> Value {
    let mut v = physical("physical-system");
    v["id"] = json!(uuid(3000 + seed * 10000, 1));
    v["alias_id"] = json!(format!("ADR-PS-{:04}", seed + 1));
    v["system"]["id"] = v["id"].clone();
    v["data_flows"]=Value::Array((0..count).map(|n| json!({"id":uuid(4000+seed*10000+n as u64,10+n as u64),"alias_id":format!("FLOW-{:04}",n+1),"alias_name":format!("flow-{n}"),"name":format!("Flow {n}"),"description":format!("  Original flow π {n}\n "),"path":["TOPO-WEB","TOPO-API","TOPO-API","TOPO-DB"],"data_type":"JSON","volume":"1 per second","latency_requirements":"under 1s"})).collect());
    v["system_boundaries"]=Value::Array((0..count).map(|n| json!({"id":uuid(5000+seed*10000+n as u64,20+n as u64),"alias_id":format!("SYSBOUND-{:04}",n+1),"alias_name":format!("boundary-{n}"),"name":format!("Boundary {n}"),"description":format!(" Exact boundary 🧭 {n}\n "),"external_dependencies":["external","external","another"],"exposed_interfaces":[uuid(1,90),uuid(1,90)]})).collect());
    v
}
fn source(v: Value, name: &str) -> identity::OriginalSource {
    original(
        v,
        name,
        "authoring/1.7/schema/adr-physical-system.schema",
        "",
        "authoring_document",
    )
}
fn selection(name: &str, pointer: &str, ty: &str) -> Selection {
    Selection {
        source_ref: name.into(),
        pointer: pointer.into(),
        semantic_type: ty.into(),
    }
}
fn selections(v: &Value, name: &str) -> Vec<Selection> {
    let mut out = vec![];
    for (property, ty) in [
        ("data_flows", "entity/data_flow"),
        ("system_boundaries", "entity/system_boundary"),
    ] {
        for n in 0..v[property].as_array().unwrap().len() {
            out.push(selection(name, &format!("/{property}/{n}"), ty));
        }
    }
    out
}
fn fixture(v: Value) -> (SealedSources, Vec<Selection>) {
    let selected = selections(&v, "native:ps");
    (
        identity::seal_sources(inputs(), &[source(v, "native:ps")], Some(CONTEXT)).unwrap(),
        selected,
    )
}
fn failure(p: &Projection, status: Status) {
    assert_eq!(p.status(), status, "{:?}", p.findings());
    assert!(
        p.values().is_empty()
            && p.semantic_evidence.is_none()
            && p.authorities.is_empty()
            && p.basis.is_empty()
    );
    assert_eq!(p.complete_interpretation(), Status::Unavailable);
}
#[test]
fn physical_siblings_execute_all_authored_fields_and_two_catalog_label_definitions() {
    let mut v = document(0, 2);
    v["data_flows"][1]["description"] = json!("  Long exact Unicode π🧭\n ".repeat(700));
    let (s, selected) = fixture(v.clone());
    let before = s.clone();
    let p = execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    assert_eq!(p.values().len(), 4);
    let proof = p.semantics().unwrap();
    assert_eq!(proof.units().len(), 4);
    let mut covered = BTreeSet::new();
    let mut labels = BTreeSet::new();
    for u in proof.units() {
        let chosen = selected
            .iter()
            .find(|x| v.pointer(&x.pointer).unwrap()["id"].as_str() == Some(&u.id))
            .unwrap();
        let authored = v.pointer(&chosen.pointer).unwrap();
        assert_eq!(u.coverage.len(), authored.as_object().unwrap().len());
        for field in &u.coverage {
            covered.insert(field.semantic_field_key.clone());
            let name = &field.semantic_field_key.split_once('#').unwrap().1[1..];
            assert_eq!(field.source_value, j(authored[name].clone()));
            assert_eq!(
                text(&field.disposition, "disposition"),
                "canonical_field_placement"
            );
            assert_eq!(u.placements[&format!("/{name}")], j(authored[name].clone()));
        }
        let chain = &proof.containment[&u.id];
        assert_eq!(chain.parent, chain.declaring);
        assert_eq!(chain.declaring.id, uuid(3000, 1));
        assert_eq!(chain.child.selection, *chosen);
        assert_eq!(array(&chain.rule, "ownership_schema_path").len(), 1);
        assert_eq!(
            text(&chain.rule, "rule_id"),
            if u.semantic_type == "entity/data_flow" {
                FLOW
            } else {
                BOUNDARY
            }
        );
        assert_eq!(u.placements["/lifecycle_stage"], string("accepted"));
        let carrier = u.lifecycle_provenance.as_ref().unwrap();
        assert_eq!(
            text(carrier, "declaring_adr_semantic_type"),
            "adr/physical-system"
        );
        assert_eq!(text(carrier, "declaring_adr_id"), uuid(3000, 1));
        assert_eq!(text(get(carrier, "ownership_rule"), "version"), "1.3");
        assert_eq!(
            text(get(carrier, "ownership_rule"), "canonical_resource_key"),
            OWN
        );
        assert!(carrier.get("lifecycle_stage").is_none());
    }
    assert_eq!(covered.len(), 16);
    for l in p.values() {
        labels.insert(l.definition.rule_id.clone());
        assert_eq!(l.definition.source_field, "description");
        let authored = selected
            .iter()
            .map(|x| v.pointer(&x.pointer).unwrap())
            .find(|x| x["id"].as_str() == Some(&l.id))
            .unwrap();
        assert_eq!(l.value, authored["description"].as_str().unwrap());
    }
    assert_eq!(labels.len(), 2);
    assert_eq!(qualify_catalog(inputs()).unwrap().len(), 26);
    let q = authority::qualify(inputs().nm, inputs().ai, inputs().acc);
    assert_eq!(
        array(&q.resources()[CATALOG], "types")
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
    assert_eq!(s, before);
    assert_eq!(proof.complete_interpretation(), Status::Unavailable);
}
#[test]
fn literal_status_provider_and_source_selection_permutations_are_independent() {
    for status in ["proposed", "accepted", "deprecated", "superseded"] {
        let mut a = document(0, 1);
        a["status"] = json!(status);
        let mut b = document(1, 1);
        b["status"] = json!("deprecated");
        let mut selected = selections(&a, "native:a");
        selected.extend(selections(&b, "native:b"));
        let a = source(a, "native:a");
        let b = source(b, "native:b");
        let s = identity::seal_sources(inputs(), &[a.clone(), b.clone()], Some(CONTEXT)).unwrap();
        let reverse = identity::seal_sources(inputs(), &[b, a], Some(CONTEXT)).unwrap();
        let p = execute(inputs(), Some(&s), &selected);
        assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
        for u in p.semantics().unwrap().units() {
            let chain = &p.semantics().unwrap().containment[&u.id];
            assert_eq!(
                u.placements["/lifecycle_stage"],
                string(if chain.declaring.selection.source_ref == "native:a" {
                    status
                } else {
                    "deprecated"
                })
            );
        }
        assert_eq!(
            verify(inputs(), Some(&s), &selected, &p).status(),
            Status::Verified
        );
        // Exercise every literal status and both declaring sources. Resource,
        // source and selection permutation invariance need one representative
        // status, rather than repeating the same cross-product four times.
        if status != "accepted" {
            continue;
        }
        selected.reverse();
        assert_eq!(p, execute(inputs(), Some(&reverse), &selected));
        assert_eq!(
            verify(inputs(), Some(&reverse), &selected, &p).status(),
            Status::Verified
        );
        let (d, mut r) = crate::candidate_authority::tests::bundles();
        for resources in &mut r {
            resources.reverse();
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
        assert_eq!(p, execute(perm, Some(&reverse), &selected));
        assert_eq!(
            verify(perm, Some(&reverse), &selected, &p).status(),
            Status::Verified
        );
    }
}
#[test]
fn system_object_geometry_qualifies_without_claiming_a_unique_semantic_producer() {
    for coincident in [false, true] {
        let mut v = document(0, 1);
        if !coincident {
            v["system"]["id"] = json!(uuid(9000, 99));
        }
        let (s, selected) = fixture(v);
        let p = semantic::prepare(inputs(), Some(&s), &selected).unwrap();
        let system = p
            .all
            .iter()
            .find(|u| u.selection.semantic_type == "entity/system")
            .unwrap();
        let chain = identity::native_ownership(&p.q, &p.all, system).unwrap();
        assert_eq!(chain.child.selection.pointer, "/system");
        assert_eq!(chain.parent, chain.declaring);
        assert_eq!(text(&chain.rule, "rule_id"), SYSTEM);
        assert_eq!(
            text(
                &array(&chain.rule, "ownership_schema_path")[0],
                "schema_pointer"
            ),
            "/properties/system"
        );
        let selected_system = [system.selection.clone()];
        let unavailable = execute(inputs(), Some(&s), &selected_system);
        failure(&unavailable, Status::Unavailable);
        assert!(unavailable
            .findings()
            .iter()
            .any(|f| f.key == "shared_identity" && f.detail.contains("provider-complete")));
        for n in 0..7 {
            let mut child = system.clone();
            let mut all = p.all.clone();
            match n {
                0 => child.owner.as_mut().unwrap().1 = uuid(1, 99),
                1 => child.parent.as_mut().unwrap().id = uuid(1, 99),
                2 => child.selection.pointer = "/system/0".into(),
                3 => child.owner.as_mut().unwrap().2 = "/system/*".into(),
                4 => {
                    child
                        .row
                        .as_object_mut()
                        .unwrap()
                        .insert("source_schema".into(), Json::Null);
                }
                5 => {
                    let root = all
                        .iter_mut()
                        .find(|u| u.selection.pointer.is_empty())
                        .unwrap();
                    root.row
                        .as_object_mut()
                        .unwrap()
                        .insert("source_schema".into(), Json::Null);
                }
                _ => {
                    child
                        .value
                        .as_object_mut()
                        .unwrap()
                        .insert("id".into(), string(uuid(1, 99)));
                }
            }
            assert!(
                identity::native_ownership(&p.q, &all, &child).is_err(),
                "{n}"
            );
        }
        let root = [selection("native:ps", "", "adr/physical-system")];
        let facts = identity::execute(inputs(), Some(&s), &root);
        assert_eq!(facts.status(), Status::Executed, "{:?}", facts.findings());
        assert_eq!(
            identity::verify(inputs(), Some(&s), &root, &facts).status(),
            Status::Verified
        );
        // Root identity facts do not supply System semantics or a complete root projection.
        failure(&execute(inputs(), Some(&s), &root), Status::Unavailable);
        let mut atomic = selected.clone();
        atomic.extend(selected_system);
        atomic.extend(root);
        failure(&execute(inputs(), Some(&s), &atomic), Status::Unavailable);
    }
}
#[test]
fn shared_system_claims_never_elect_a_winner_or_poison_independent_siblings() {
    for mode in 0..3 {
        let mut a = document(0, 1);
        let mut b = document(1, 1);
        a["system"]["id"] = json!(uuid(9000, 99));
        b["system"]["id"] = json!(if mode == 0 {
            uuid(9001, 99)
        } else {
            uuid(9000, 99)
        });
        if mode == 2 {
            b["system"]["alias_name"] = json!("conflicting-system-label");
        }
        let selected = selections(&a, "native:a");
        let single =
            identity::seal_sources(inputs(), &[source(a.clone(), "native:a")], Some(CONTEXT))
                .unwrap();
        let both = identity::seal_sources(
            inputs(),
            &[source(a, "native:a"), source(b, "native:b")],
            Some(CONTEXT),
        )
        .unwrap();
        let system = [selection("native:a", "/system", "entity/system")];
        failure(
            &execute(inputs(), Some(&single), &system),
            Status::Unavailable,
        );
        let p = execute(inputs(), Some(&both), &selected);
        assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
        let raw = semantic::prepare(inputs(), Some(&both), &selected).unwrap();
        let system_ids: BTreeSet<_> = raw
            .all
            .iter()
            .filter(|u| u.selection.semantic_type == "entity/system")
            .map(|u| text(&u.value, "id"))
            .collect();
        assert_eq!(system_ids.len(), if mode == 0 { 2 } else { 1 });
        assert_eq!(
            verify(inputs(), Some(&both), &selected, &p).status(),
            Status::Verified
        );
        let blocked = execute(inputs(), Some(&both), &system);
        failure(
            &blocked,
            if mode == 2 {
                Status::Rejected
            } else {
                Status::Unavailable
            },
        );
        if mode == 2 {
            assert!(blocked
                .findings()
                .iter()
                .any(|f| f.status == Status::Unavailable));
            assert!(blocked
                .findings()
                .iter()
                .any(|f| f.key == "entity/system#/alias_name"));
        }
        let mut atomic = selected;
        atomic.extend(system);
        failure(
            &execute(inputs(), Some(&both), &atomic),
            if mode == 2 {
                Status::Rejected
            } else {
                Status::Unavailable
            },
        );
    }
}
#[test]
fn independent_inverse_detects_fields_lifecycle_ownership_labels_and_forged_receipts() {
    let (s, selected) = fixture(document(0, 2));
    let p = execute(inputs(), Some(&s), &selected);
    assert_eq!(p.status(), Status::Executed, "{:?}", p.findings());
    for n in 0..15 {
        let mut bad = p.clone();
        let proof = bad.semantic_evidence.as_mut().unwrap();
        let unit = &mut proof.units[0];
        let id = unit.id.clone();
        match n {
            0 => proof.containment.get_mut(&id).unwrap().parent.id = uuid(1, 99),
            1 => proof.containment.get_mut(&id).unwrap().declaring.id = uuid(1, 99),
            2 => {
                proof.containment.remove(&id);
            }
            3 => {
                proof
                    .containment
                    .get_mut(&id)
                    .unwrap()
                    .rule
                    .as_object_mut()
                    .unwrap()
                    .insert("ownership_schema_path".into(), Json::Array(vec![]));
            }
            4 => {
                unit.placements
                    .insert("/lifecycle_stage".into(), string("active"));
            }
            5 => {
                unit.lifecycle_provenance
                    .as_mut()
                    .unwrap()
                    .as_object_mut()
                    .unwrap()
                    .insert("declaring_adr_id".into(), string(uuid(1, 99)));
            }
            6 => {
                unit.placements
                    .insert("/description".into(), string("changed"));
            }
            7 => {
                unit.placements.remove("/description");
            }
            8 => bad.values[0].value.push(' '),
            9 => {
                bad.values.push(bad.values[0].clone());
            }
            10 => {
                bad.values[0].definition.destination = "/name".into();
            }
            11 => proof.representations = None,
            12 => bad.status = Status::Verified,
            13 => {
                unit.coverage.pop();
            }
            _ => {
                unit.semantic_extensions
                    .insert("entity/system#/alias_name".into(), string("invented"));
            }
        }
        failure(
            &verify(inputs(), Some(&s), &selected, &bad),
            Status::Rejected,
        );
    }
    let original = document(0, 2);
    for n in 0..4 {
        let mut v = original.clone();
        match n {
            0 => v["data_flows"][0]["description"] = json!("Changed semantic source"),
            1 => v["system_boundaries"][0]["description"] = json!("Changed boundary"),
            2 => v["status"] = json!("superseded"),
            _ => v["data_flows"].as_array_mut().unwrap().reverse(),
        }
        let (new, chosen) = fixture(v);
        let mut stale = p.semantics().unwrap().clone();
        stale.basis_digest = semantic::prepare(inputs(), Some(&new), &chosen)
            .unwrap()
            .basis;
        stale.representations = Some(identity::execute(inputs(), Some(&new), &chosen));
        let checked = semantic::verify(inputs(), Some(&new), &chosen, &stale);
        assert_eq!(
            checked.status(),
            Status::Rejected,
            "{n}: {:?}",
            checked.findings()
        );
        assert!(
            checked.units().is_empty()
                && checked.containment.is_empty()
                && checked.representations.is_none()
                && checked.authorities.is_empty()
                && checked.basis_digest.is_empty()
        );
    }
}
#[test]
fn invalid_identity_source_shape_context_and_destination_values_fail_closed() {
    for n in 0..4 {
        let mut v = document(0, 2);
        match n {
            0 => v["data_flows"][1]["id"] = v["data_flows"][0]["id"].clone(),
            1 => v["system_boundaries"][1]["id"] = v["system_boundaries"][0]["id"].clone(),
            2 => v["data_flows"][0]["id"] = v["system"]["id"].clone(),
            _ => v["data_flows"][0]["data_type"] = json!(""),
        }
        let (s, selected) = fixture(v);
        failure(&execute(inputs(), Some(&s), &selected), Status::Rejected);
    }
    for replacement in [
        "\"system\": []\n".to_owned(),
        "\"system\": null\n".to_owned(),
        String::new(),
    ] {
        // The schema-driven renderer intentionally cannot manufacture an array
        // at this object property. Mutate real original bytes, then test sealing.
        let mut raw = source(document(0, 1), "native:ps");
        let mut bytes = String::from_utf8(raw.bytes).unwrap();
        let start = bytes.find("\"system\":\n").unwrap();
        let end = start
            + "\"system\":\n".len()
            + bytes[start + "\"system\":\n".len()..]
                .lines()
                .take_while(|line| line.starts_with(' '))
                .map(|line| line.len() + 1)
                .sum::<usize>();
        bytes.replace_range(start..end, &replacement);
        raw.bytes = bytes.into_bytes();
        assert!(identity::seal_sources(inputs(), &[raw], Some(CONTEXT)).is_err());
    }
    for field in ["description", "complete"] {
        let mut raw = source(document(0, 1), "native:ps");
        let bytes = String::from_utf8(raw.bytes).unwrap();
        raw.bytes = bytes
            .replacen(
                "\"system\":\n",
                &format!("\"system\":\n  \"{field}\": true\n"),
                1,
            )
            .into_bytes();
        assert!(identity::seal_sources(inputs(), &[raw], Some(CONTEXT)).is_err());
    }
    let v = document(0, 1);
    assert!(identity::seal_sources(
        inputs(),
        &[source(v.clone(), "native:ps")],
        Some("caller-namespace")
    )
    .is_err());
    let fragment = original(
        v["data_flows"][0].clone(),
        "native:fragment",
        "authoring/1.7/schema/adr-common.schema",
        "/definitions/data_flow",
        "authoring_fragment",
    );
    let s = identity::seal_sources(inputs(), &[fragment], Some(CONTEXT)).unwrap();
    failure(
        &execute(
            inputs(),
            Some(&s),
            &[selection("native:fragment", "", "entity/data_flow")],
        ),
        Status::Unavailable,
    );
    let (s, mut selected) = fixture(v);
    selected[0].semantic_type = "entity/system_boundary".into();
    failure(&execute(inputs(), Some(&s), &selected), Status::Rejected);
    failure(&execute(inputs(), None, &selected), Status::Unavailable);
}
#[test]
fn rehashed_unauthorized_direct_object_rule_cannot_become_current_authority() {
    let q = authority::qualify(inputs().nm, inputs().ai, inputs().acc);
    let mut resource: Value = serde_json::to_value(&q.resources()[OWN]).unwrap();
    let row = resource["rows"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|r| r["rule_id"] == SYSTEM)
        .unwrap();
    row["ownership_schema_path"][0]["schema_pointer"] = json!("/properties/system/items");
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
    let (s, selected) = fixture(document(0, 1));
    failure(&execute(bad, Some(&s), &selected), Status::Rejected);
}
