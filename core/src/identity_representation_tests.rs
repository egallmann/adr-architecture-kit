use super::*;
use serde_json::{json, Value};
use std::sync::OnceLock;

fn fixture() -> &'static (Vec<Json>, Vec<Vec<Json>>) {
    static F: OnceLock<(Vec<Json>, Vec<Vec<Json>>)> = OnceLock::new();
    F.get_or_init(crate::candidate_authority::tests::bundles)
}
pub(crate) fn inputs() -> Inputs<'static> {
    let (d, r) = fixture();
    Inputs {
        nm: Bundle {
            definition: &d[0],
            resources: &r[0],
        },
        ai: Bundle {
            definition: &d[1],
            resources: &r[1],
        },
        acc: Bundle {
            definition: &d[2],
            resources: &r[2],
        },
    }
}
pub(crate) fn j(v: Value) -> Json {
    serde_json::from_value(v).unwrap()
}
pub(crate) fn uuid(ms: u64, n: u64) -> String {
    let h = format!("{ms:012x}");
    format!("{}-{}-7000-8000-{n:012x}", &h[..8], &h[8..])
}
pub(crate) fn document(ms: u64) -> Value {
    json!({"schema_version":"1.7","adr_type":"logical","id":uuid(ms,1),"alias_id":"ADR-L-0001","alias_name":"native-logical","title":"Native source","status":"accepted","created_date":"2026-01-01","authors":["author"],"context":"Unicode 🧭\n  exact content","decisions":[{"id":uuid(1000,2),"alias_id":"DEC-0001","alias_name":"authored-decision","summary":"Exact Unicode π","rationale":"Reason"}],"normative_propositions":[{"id":uuid(2000,3),"alias_id":"NP-0001","alias_name":"authored-proposition","statement":"Preserve meaning","normative_force":"MUST","scope":"architecture"}]})
}
pub(crate) fn original(v: Value, source_ref: &str, key: &str, pointer: &str, kind: &str) -> OriginalSource {
    let selector = CandidateSourceSelector {
        canonical_resource_key: key.into(),
        json_pointer: pointer.into(),
    };
    OriginalSource {
        source_ref: source_ref.into(),
        artifact_kind: kind.into(),
        bytes: source::render_source(&selector, &j(v)).unwrap(),
        selector,
    }
}
pub(crate) fn source(v: Value) -> OriginalSource {
    original(
        v,
        "native:logical",
        "authoring/1.7/schema/adr-logical.schema",
        "",
        "authoring_document",
    )
}
pub(crate) fn sealed(v: Value) -> SealedSources {
    seal_sources(inputs(), &[source(v)], Some(CONTEXT)).unwrap()
}
pub(crate) fn selections() -> Vec<Selection> {
    [
        ("", "adr/logical"),
        ("/decisions/0", "entity/decision"),
        ("/normative_propositions/0", "entity/normative_proposition"),
    ]
    .into_iter()
    .map(|(p, t)| Selection {
        source_ref: "native:logical".into(),
        pointer: p.into(),
        semantic_type: t.into(),
    })
    .collect()
}
fn assert_failure(p: &Projection, status: Status) {
    assert_eq!(p.status(), status, "{:?}", p.findings());
    assert!(p.values().is_empty());
    assert!(p.authorities.is_empty());
    assert!(p.basis_digest.is_empty());
    assert_eq!(p.complete_interpretation(), Status::Unavailable)
}

#[test]
fn executes_and_independently_verifies_regular_and_proposition_branches() {
    let sources = sealed(document(0));
    let before = sources.clone();
    let out = execute(inputs(), Some(&sources), &selections());
    assert_eq!(out.status(), Status::Executed, "{:?}", out.findings());
    assert_eq!(out.values().len(), 3);
    assert_eq!(out.values()[0].alias_ref, "ADR-L-0001:native-logical");
    assert_eq!(
        out.values()[0].uri,
        format!(
            "adr://urn:adr-kit:detached-candidate:v1/entities/{}",
            uuid(0, 1)
        )
    );
    assert_eq!(out.values()[0].created_at, "1970-01-01T00:00:00.000Z");
    assert_eq!(out.values()[2].branch, "normative-proposition");
    assert_eq!(
        verify(inputs(), Some(&sources), &selections(), &out).status(),
        Status::Verified
    );
    assert_eq!(sources, before);
    assert_eq!(out.complete_interpretation(), Status::Unavailable);
}

#[test]
fn integer_calendar_boundaries_and_independent_inverse() {
    let vectors = [
        (0, "1970-01-01T00:00:00.000Z"),
        (1, "1970-01-01T00:00:00.001Z"),
        (999, "1970-01-01T00:00:00.999Z"),
        (1000, "1970-01-01T00:00:01.000Z"),
        (86399999, "1970-01-01T23:59:59.999Z"),
        (86400000, "1970-01-02T00:00:00.000Z"),
        (31536000000, "1971-01-01T00:00:00.000Z"),
        (951782400001, "2000-02-29T00:00:00.001Z"),
        (4107542400000, "2100-03-01T00:00:00.000Z"),
        (253402300799999, "9999-12-31T23:59:59.999Z"),
    ];
    for (ms, expected) in vectors {
        let s = sealed(document(ms));
        let selected = vec![selections()[0].clone()];
        let out = execute(inputs(), Some(&s), &selected);
        assert_eq!(out.status(), Status::Executed, "{ms}: {:?}", out.findings());
        assert_eq!(out.values()[0].created_at, expected);
        assert_eq!(
            verify(inputs(), Some(&s), &selected, &out).status(),
            Status::Verified
        );
    }
}

#[test]
fn valid_out_of_range_uuid_is_unavailable_without_partial_output() {
    for ms in [253402300800000, 0xffffffffffff] {
        let s = sealed(document(ms));
        let out = execute(inputs(), Some(&s), &selections());
        assert_failure(&out, Status::Unavailable);
        assert_failure(
            &verify(inputs(), Some(&s), &selections(), &out),
            Status::Unavailable,
        );
        assert!(out.findings().iter().any(|d| d.key == "created_at"));
    }
}

#[test]
fn output_and_receipt_mutations_are_reconstructed_from_original_evidence() {
    let s = sealed(document(1));
    let out = execute(inputs(), Some(&s), &selections());
    assert_eq!(out.status(), Status::Executed);
    for mutation in 0..12 {
        let mut changed = out.clone();
        let v = &mut changed.values[0];
        match mutation {
            0 => v.alias_ref.push(' '),
            1 => v.uri = v.uri.replace("adr://", "https://"),
            2 => v.created_at = "1970-01-01T00:00:00.002Z".into(),
            3 => v.created_at = "1970-01-01T00:00:00.01Z".into(),
            4 => v.created_at = "1970-02-30T00:00:00.001Z".into(),
            5 => v.namespace.push('x'),
            6 => v.id = uuid(1, 99),
            7 => v.rules.clear(),
            8 => v.source_pointer = "/other".into(),
            9 => changed.values.pop().map(|_| ()).unwrap(),
            10 => changed.status = Status::Verified,
            _ => changed.basis_digest = "sha256:forged".into(),
        }
        assert_failure(
            &verify(inputs(), Some(&s), &selections(), &changed),
            Status::Rejected,
        );
    }
}

#[test]
fn missing_source_context_and_standalone_ownership_fail_closed() {
    assert_failure(&execute(inputs(), None, &selections()), Status::Unavailable);
    let raw = source(document(0));
    assert!(seal_sources(inputs(), &[raw.clone()], None)
        .unwrap_err()
        .iter()
        .all(|d| d.status == Status::Unavailable));
    for provider in [
        "repository-provider",
        "caller:namespace",
        "urn:adr-kit:detached-candidate:v1",
        "",
    ] {
        assert!(seal_sources(inputs(), &[raw.clone()], Some(provider)).is_err());
    }
    let child = document(0)["decisions"][0].clone();
    let standalone = original(
        child,
        "native:fragment",
        "authoring/1.7/schema/adr-common.schema",
        "/definitions/decision",
        "authoring_fragment",
    );
    let s = seal_sources(inputs(), &[standalone], Some(CONTEXT)).unwrap();
    let selected = vec![Selection {
        source_ref: "native:fragment".into(),
        pointer: String::new(),
        semantic_type: "entity/decision".into(),
    }];
    assert_failure(&execute(inputs(), Some(&s), &selected), Status::Unavailable);
}

#[test]
fn aliases_obey_actual_source_domain_without_repair_or_truncation() {
    let mut v = document(0);
    v["alias_name"] = json!("a".repeat(96));
    let s = sealed(v);
    let out = execute(inputs(), Some(&s), &[selections()[0].clone()]);
    assert_eq!(
        out.values()[0].alias_ref,
        format!("ADR-L-0001:{}", "a".repeat(96))
    );
    for bad in [
        json!(""),
        json!(" "),
        json!("Native"),
        json!("étiquette"),
        json!("a".repeat(97)),
        json!(1),
        Value::Null,
    ] {
        let mut v = document(0);
        v["alias_name"] = bad;
        let error = seal_sources(inputs(), &[source(v)], Some(CONTEXT)).unwrap_err();
        assert!(error.iter().any(|d| d.status == Status::Rejected));
    }
    let mut v = document(0);
    v.as_object_mut().unwrap().remove("alias_id");
    assert!(seal_sources(inputs(), &[source(v)], Some(CONTEXT)).is_err());
}

#[test]
fn invalid_uuid_format_case_version_and_variant_are_rejected() {
    for bad in [
        "",
        "00000000-0000-7000-8000-00000000000A",
        "00000000-0000-4000-8000-000000000001",
        "00000000-0000-7000-7000-000000000001",
        "00000000000070008000000000000001",
    ] {
        let mut v = document(0);
        v["id"] = json!(bad);
        let e = seal_sources(inputs(), &[source(v)], Some(CONTEXT)).unwrap_err();
        assert!(e.iter().any(|d| d.status == Status::Rejected));
    }
}

#[test]
fn sealed_bytes_rehashed_forgery_does_not_change_original_source_anchor() {
    let s = sealed(document(0));
    let out = execute(inputs(), Some(&s), &selections());
    let mut changed = s.clone();
    let mut v = document(0);
    v["alias_name"] = json!("rewritten-alias");
    let fake = source(v);
    let a = &s.basis.artifacts[0];
    let value = source::decode_canonical_candidate(&fake.bytes).unwrap();
    changed.basis = source::seal_candidate_source_basis(vec![source::seal_candidate_artifact(
        &a.request_key,
        &a.source_ref,
        &a.artifact_kind,
        a.source_schema.clone(),
        a.source_contract.clone(),
        &value,
    )
    .unwrap()])
    .unwrap();
    assert_failure(
        &execute(inputs(), Some(&changed), &selections()),
        Status::Rejected,
    );
    assert_failure(
        &verify(inputs(), Some(&changed), &selections(), &out),
        Status::Rejected,
    );
    let mut changed = s.clone();
    changed
        .context
        .as_object_mut()
        .unwrap()
        .insert("architecture_namespace".into(), string("other-provider"));
    assert_failure(
        &verify(inputs(), Some(&changed), &selections(), &out),
        Status::Rejected,
    );
}

#[test]
fn duplicate_identities_competing_producers_and_wrong_types_fail_atomically() {
    let mut v = document(0);
    let duplicate = v["decisions"][0].clone();
    v["decisions"].as_array_mut().unwrap().push(duplicate);
    let s = sealed(v);
    assert_failure(
        &execute(inputs(), Some(&s), &selections()),
        Status::Rejected,
    );
    let s = sealed(document(0));
    let mut selected = selections();
    selected.push(selected[0].clone());
    assert_failure(&execute(inputs(), Some(&s), &selected), Status::Rejected);
    let mut selected = selections();
    selected[1].semantic_type = "entity/invariant".into();
    assert_failure(&execute(inputs(), Some(&s), &selected), Status::Rejected);
    selected[1].pointer = "/related_adrs/0".into();
    assert_failure(&execute(inputs(), Some(&s), &selected), Status::Unavailable);
}

#[test]
fn source_and_resource_permutations_preserve_identity_and_determinism() {
    let first = source(document(0));
    let mut v = document(3000);
    v["alias_id"] = json!("ADR-L-0002");
    v["decisions"][0]["id"] = json!(uuid(4000, 4));
    v["normative_propositions"][0]["id"] = json!(uuid(5000, 5));
    let second = original(
        v,
        "native:second",
        "authoring/1.7/schema/adr-logical.schema",
        "",
        "authoring_document",
    );
    let s1 = seal_sources(inputs(), &[first.clone(), second.clone()], Some(CONTEXT)).unwrap();
    let s2 = seal_sources(inputs(), &[second, first], Some(CONTEXT)).unwrap();
    assert_eq!(s1, s2);
    let out = execute(inputs(), Some(&s1), &selections());
    let mut order = selections();
    order.reverse();
    assert_eq!(execute(inputs(), Some(&s2), &order), out);
    let (d, mut r) = fixture().clone();
    for v in &mut r {
        v.reverse()
    }
    let perm = Inputs {
        nm: Bundle {
            definition: &d[0],
            resources: &r[0],
        },
        ai: Bundle {
            definition: &d[1],
            resources: &r[1],
        },
        acc: Bundle {
            definition: &d[2],
            resources: &r[2],
        },
    };
    assert_eq!(
        verify(perm, Some(&s2), &order, &out).status(),
        Status::Verified
    );
}

#[test]
fn unauthorized_rehashed_authority_wrong_versions_and_schema_substitution_fail() {
    let s = sealed(document(0));
    let q = qualify(inputs()).unwrap();
    let mut recipe: Value = serde_json::to_value(&q.resources()[RECIPES]).unwrap();
    recipe["recipes"][1]["specification"]["namespace_encoding"] = json!("percent_encode");
    // Shared fixture helper independently verifies all newly recomputed SCFs and closures.
    let (d, r) = crate::candidate_authority::tests::rehashed_with_resource(RECIPES, j(recipe));
    let forged = Inputs {
        nm: Bundle {
            definition: &d[0],
            resources: &r[0],
        },
        ai: Bundle {
            definition: &d[1],
            resources: &r[1],
        },
        acc: Bundle {
            definition: &d[2],
            resources: &r[2],
        },
    };
    assert_failure(&execute(forged, Some(&s), &selections()), Status::Rejected);
    for index in 0..3 {
        let (mut d, r) = fixture().clone();
        d[index]
            .as_object_mut()
            .unwrap()
            .insert("semanticContractVersion".into(), string("1.2"));
        let bad = Inputs {
            nm: Bundle {
                definition: &d[0],
                resources: &r[0],
            },
            ai: Bundle {
                definition: &d[1],
                resources: &r[1],
            },
            acc: Bundle {
                definition: &d[2],
                resources: &r[2],
            },
        };
        assert_failure(&execute(bad, Some(&s), &selections()), Status::Rejected);
    }
    let mut raw = source(document(0));
    raw.selector.canonical_resource_key = "authoring/1.6/schema/adr-logical.schema".into();
    assert!(seal_sources(inputs(), &[raw], Some(CONTEXT))
        .unwrap_err()
        .iter()
        .all(|d| d.status == Status::Unavailable));
    let mut raw = source(document(0));
    raw.selector.canonical_resource_key =
        "authoring/1.7/schema/adr-physical-component.schema".into();
    assert!(seal_sources(inputs(), &[raw], Some(CONTEXT))
        .unwrap_err()
        .iter()
        .any(|d| d.status == Status::Rejected));
}

#[test]
fn manifest_permutations_and_source_relocation_do_not_change_identity_values() {
    let raw = source(document(0));
    let s = seal_sources(inputs(), &[raw.clone()], Some(CONTEXT)).unwrap();
    let (mut d, r) = fixture().clone();
    for root in &mut d {
        root.as_object_mut()
            .unwrap()
            .get_mut("resourceManifest")
            .unwrap()
            .as_array_mut()
            .unwrap()
            .reverse();
    }
    let perm = Inputs {
        nm: Bundle {
            definition: &d[0],
            resources: &r[0],
        },
        ai: Bundle {
            definition: &d[1],
            resources: &r[1],
        },
        acc: Bundle {
            definition: &d[2],
            resources: &r[2],
        },
    };
    assert_eq!(
        seal_sources(perm, &[raw.clone()], Some(CONTEXT)).unwrap(),
        s
    );
    let out = execute(inputs(), Some(&s), &selections());
    let mut moved = raw;
    moved.source_ref = "not-a-namespace/🧭/copy".into();
    let m = seal_sources(inputs(), &[moved.clone()], Some(CONTEXT)).unwrap();
    let mut selected = selections();
    for x in &mut selected {
        x.source_ref = moved.source_ref.clone()
    }
    let moved_out = execute(inputs(), Some(&m), &selected);
    assert_eq!(
        moved_out.status(),
        Status::Executed,
        "{:?}",
        moved_out.findings()
    );
    for (a, b) in out.values().iter().zip(moved_out.values()) {
        assert_eq!(
            (&a.id, &a.namespace, &a.alias_ref, &a.uri, &a.created_at),
            (&b.id, &b.namespace, &b.alias_ref, &b.uri, &b.created_at)
        );
    }
    assert_ne!(s.context, m.context);
    assert_failure(
        &verify(inputs(), Some(&m), &selected, &out),
        Status::Rejected,
    );
    // Only the actual selected detached context is qualified. A different claimed
    // provider with the same UUID is Unavailable, never silently merged/adopted.
    assert!(seal_sources(
        inputs(),
        &[moved],
        Some("other-qualified-provider-assertion")
    )
    .is_err());
}

fn physical(kind: &str) -> Value {
    let mut d = document(3000);
    let fields = d.as_object_mut().unwrap();
    fields.remove("decisions");
    fields.remove("normative_propositions");
    fields.insert("adr_type".into(), json!(kind));
    fields.insert(
        "alias_id".into(),
        json!(if kind == "physical-component" {
            "ADR-PC-0001"
        } else {
            "ADR-PS-0001"
        }),
    );
    fields.insert("implements_logical".into(), json!([uuid(0, 90)]));
    fields.insert("technology_stack".into(),json!([{"category":"language","name":"Rust","version":"stable","rationale":"Exact source"}]));
    if kind == "physical-system" {
        fields.insert(
            "system".into(),
            json!({"id":uuid(3000,1),"alias_id":"SYS-0001","alias_name":"shared-system"}),
        );
    } else {
        fields.insert("implements_system".into(), json!([uuid(0, 91)]));
        fields.insert("component_specifications".into(),json!([{"id":uuid(4000,4),"alias_id":"COMP-0001","alias_name":"native-component","name":"Component","type":"service","responsibilities":"Behavior","generation_context":{"purpose":"Purpose","key_responsibilities":["Behavior"]},"interfaces":[{"id":uuid(5000,5),"alias_id":"IFACE-0001","alias_name":"native-interface","type":"REST","specification":"Contract"}]}]));
    }
    d
}

#[test]
fn nested_schema_units_are_accounted_and_shared_identity_is_unavailable() {
    let raw = original(
        physical("physical-component"),
        "native:pc",
        "authoring/1.7/schema/adr-physical-component.schema",
        "",
        "authoring_document",
    );
    let s = seal_sources(inputs(), &[raw], Some(CONTEXT)).unwrap();
    let selected = vec![Selection {
        source_ref: "native:pc".into(),
        pointer: String::new(),
        semantic_type: "adr/physical-component".into(),
    }];
    let out = execute(inputs(), Some(&s), &selected);
    assert_eq!(out.status(), Status::Executed, "{:?}", out.findings());
    assert_eq!(
        verify(inputs(), Some(&s), &selected, &out).status(),
        Status::Verified
    );
    let mut wrong = physical("physical-component");
    wrong["component_specifications"][0]["interfaces"][0]["id"] = wrong["id"].clone();
    let raw = original(
        wrong,
        "native:pc",
        "authoring/1.7/schema/adr-physical-component.schema",
        "",
        "authoring_document",
    );
    let s = seal_sources(inputs(), &[raw], Some(CONTEXT)).unwrap();
    assert_failure(&execute(inputs(), Some(&s), &selected), Status::Rejected);
    let raw = original(
        physical("physical-system"),
        "native:ps",
        "authoring/1.7/schema/adr-physical-system.schema",
        "",
        "authoring_document",
    );
    let s = seal_sources(inputs(), &[raw], Some(CONTEXT)).unwrap();
    let selected = vec![Selection {
        source_ref: "native:ps".into(),
        pointer: String::new(),
        semantic_type: "adr/physical-system".into(),
    }];
    assert_failure(&execute(inputs(), Some(&s), &selected), Status::Unavailable);
}

#[test]
fn custom_qualification_is_not_fabricated_and_known_invalidity_has_precedence() {
    let custom = json!({"id":uuid(0,10),"alias_id":"CUST-0001","alias_name":"custom-source","entity_type":"demo:custom","qualification":{"semantic_kind":"entity","semantic_type":"demo:custom","consumer_namespace":"demo","contract_version":"1.0","contract_fingerprint":format!("cecf:v1:sha256:{}","a".repeat(64))},"properties":{},"rationale":"Native source"});
    let raw = original(
        custom,
        "native:custom",
        "authoring/1.7/schema/adr-common.schema",
        "/definitions/custom_entity",
        "authoring_fragment",
    );
    let s = seal_sources(inputs(), &[raw], Some(CONTEXT)).unwrap();
    let selected = vec![Selection {
        source_ref: "native:custom".into(),
        pointer: String::new(),
        semantic_type: "entity/extension".into(),
    }];
    assert_failure(&execute(inputs(), Some(&s), &selected), Status::Unavailable);
    let s = sealed(document(0));
    let mut selected = selections();
    selected.push(Selection {
        source_ref: "native:logical".into(),
        pointer: "/missing".into(),
        semantic_type: "entity/decision".into(),
    });
    selected[0].semantic_type = "adr/physical-component".into();
    let out = execute(inputs(), Some(&s), &selected);
    assert_failure(&out, Status::Rejected);
    assert!(out
        .findings()
        .iter()
        .any(|d| d.status == Status::Unavailable));
    assert!(out.findings().iter().any(|d| d.status == Status::Rejected));
}

#[test]
fn source_context_and_rule_receipts_never_replace_original_proof() {
    let s = sealed(document(0));
    let out = execute(inputs(), Some(&s), &selections());
    for mutation in 0..8 {
        let mut changed = s.clone();
        match mutation {
            0 => {
                changed.basis.artifacts.clear();
            }
            1 => changed.basis.artifacts[0].content_digest = "sha256:wrong".into(),
            2 => changed.basis.artifacts[0].source_contract = Json::Null,
            3 => changed
                .context
                .as_object_mut()
                .unwrap()
                .insert("provider_kind".into(), string("repository-provider"))
                .map(|_| ())
                .unwrap(),
            4 => changed
                .context
                .as_object_mut()
                .unwrap()
                .insert("scope_root".into(), string("caller:namespace"))
                .map(|_| ())
                .unwrap(),
            5 => {
                changed.authorities[0].fingerprint = "scf:v1:sha256:caller".into();
            }
            6 => {
                changed.basis.artifacts[0].source_schema.json_pointer =
                    "/definitions/decision".into();
            }
            _ => {
                changed
                    .context
                    .as_object_mut()
                    .unwrap()
                    .get_mut("qualification")
                    .unwrap()
                    .as_object_mut()
                    .unwrap()
                    .insert(
                        "semantic_contract_fingerprint".into(),
                        string("scf:v1:sha256:forged"),
                    );
            }
        }
        assert_failure(
            &verify(inputs(), Some(&changed), &selections(), &out),
            Status::Rejected,
        );
    }
    let mut changed = out.clone();
    changed.values[0].rules[0]
        .as_object_mut()
        .unwrap()
        .get_mut("producer")
        .unwrap()
        .as_object_mut()
        .unwrap()
        .insert("rule_id".into(), string("caller-rule"));
    assert_failure(
        &verify(inputs(), Some(&s), &selections(), &changed),
        Status::Rejected,
    );
    let mut raw = source(document(0));
    raw.bytes
        .extend_from_slice(b"\"alias_id\": \"ADR-L-0001\"\n");
    assert!(seal_sources(inputs(), &[raw], Some(CONTEXT))
        .unwrap_err()
        .iter()
        .any(|d| d.status == Status::Rejected));
}

#[test]
fn relationship_value_and_unqualified_provider_claims_do_not_create_entities() {
    let force = original(
        json!("MUST"),
        "native:force",
        "authoring/1.7/schema/types.schema",
        "/definitions/normative_force",
        "authoring_fragment",
    );
    assert!(seal_sources(inputs(), &[force], Some(CONTEXT))
        .unwrap_err()
        .iter()
        .all(|d| d.status == Status::Unavailable));
    let mut raw = source(document(0));
    raw.artifact_kind = "authoring_fragment".into();
    assert!(seal_sources(inputs(), &[raw], Some(CONTEXT))
        .unwrap_err()
        .iter()
        .any(|d| d.status == Status::Rejected));
    let s = sealed(document(0));
    let selected = vec![Selection {
        source_ref: "native:logical".into(),
        pointer: "/implements_logical/0".into(),
        semantic_type: "relationship/extension".into(),
    }];
    assert_failure(&execute(inputs(), Some(&s), &selected), Status::Unavailable);
    // Absent authority for another namespace stays absent. The engine never
    // turns the same UUID plus a caller namespace into a qualified second unit.
    for namespace in ["other", "a/b", "MiXeD", "naïve"] {
        assert!(seal_sources(inputs(), &[source(document(0))], Some(namespace)).is_err());
    }
}

#[test]
fn recognition_aliases_are_not_unit_identity_and_authority_violations_win() {
    let mut v = document(0);
    let mut child = v["decisions"][0].clone();
    child["id"] = json!(uuid(1000, 99));
    v["decisions"].as_array_mut().unwrap().push(child);
    let s = sealed(v);
    let mut selected = selections();
    selected.push(Selection {
        source_ref: "native:logical".into(),
        pointer: "/decisions/1".into(),
        semantic_type: "entity/decision".into(),
    });
    let out = execute(inputs(), Some(&s), &selected);
    assert_eq!(out.status(), Status::Executed, "{:?}", out.findings());
    let d: Vec<_> = out
        .values()
        .iter()
        .filter(|u| u.semantic_type == "entity/decision")
        .collect();
    assert_eq!(d.len(), 2);
    assert_eq!(d[0].alias_ref, d[1].alias_ref);
    assert_ne!(d[0].uri, d[1].uri);
    assert_eq!(
        verify(inputs(), Some(&s), &selected, &out).status(),
        Status::Verified
    );
    let (mut definitions, resources) = fixture().clone();
    definitions[1]
        .as_object_mut()
        .unwrap()
        .insert("semanticContractVersion".into(), string("1.2"));
    let bad = Inputs {
        nm: Bundle {
            definition: &definitions[0],
            resources: &resources[0],
        },
        ai: Bundle {
            definition: &definitions[1],
            resources: &resources[1],
        },
        acc: Bundle {
            definition: &definitions[2],
            resources: &resources[2],
        },
    };
    let result = execute(bad, None, &selected);
    assert_failure(&result, Status::Rejected);
    assert!(result
        .findings()
        .iter()
        .any(|f| f.status == Status::Unavailable));
}
