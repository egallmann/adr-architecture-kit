use super::*;
use std::{fs, path::PathBuf, sync::OnceLock};

fn load(path: &str) -> Json {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf();
    serde_json::from_slice(&fs::read(root.join(path)).unwrap()).unwrap()
}
struct Fixture {
    ai: Json,
    acc: Json,
    nm: Json,
    resources: Vec<Json>,
}
fn fixture() -> &'static Fixture {
    static F: OnceLock<Fixture> = OnceLock::new();
    F.get_or_init(|| {
        let acc = load("contracts/authoring-construction/v1.4/contract.json");
        let resources = array(&acc, "resourceManifest")
            .iter()
            .map(|m| {
                let key = text(m, "canonicalResourceKey");
                let name = key
                    .replace(
                        "architecture-interpretation/1.0/source-",
                        "architecture-interpretation/source-",
                    )
                    .replace('/', "-");
                let path = format!("contracts/semantic-contract/v1.0/resources/{name}.json");
                let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                    .parent()
                    .unwrap()
                    .to_path_buf();
                let path = if root.join(&path).exists() {
                    path
                } else {
                    format!(
                        "contracts/semantic-contract/v1.0/definitions/{}.json",
                        name.trim_end_matches("-contract")
                    )
                };
                object([
                    ("canonicalResourceKey".into(), string(key)),
                    ("content".into(), load(&path)),
                ])
            })
            .collect();
        Fixture {
            ai: load(
                "contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.4.json",
            ),
            nm: load("contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json"),
            acc,
            resources,
        }
    })
}
fn subset(def: &Json, all: &[Json]) -> Vec<Json> {
    let keys: BTreeSet<_> = array(def, "resourceManifest")
        .iter()
        .map(|m| text(m, "canonicalResourceKey"))
        .collect();
    all.iter()
        .filter(|r| keys.contains(text(r, "canonicalResourceKey")))
        .cloned()
        .collect()
}
fn run(f: &Fixture) -> Qualification {
    qualify(
        Bundle {
            definition: &f.ai,
            resources: &subset(&f.ai, &f.resources),
        },
        Bundle {
            definition: &f.acc,
            resources: &f.resources,
        },
        Bundle {
            definition: &f.nm,
            resources: &subset(&f.nm, &f.resources),
        },
    )
}
#[test]
fn genuine_full_authority_and_derived_accounting() {
    let r = run(fixture());
    assert_eq!(r.status, Status::CatalogQualified, "{:#?}", r.findings);
    assert!(r.authority_qualified);
    assert_eq!(r.types.len(), 27);
    assert_eq!(
        r.types
            .iter()
            .map(|t| t.branch.clone())
            .collect::<BTreeSet<_>>()
            .len(),
        6
    );
    let outputs: Vec<_> = r.types.iter().flat_map(|t| &t.destinations).collect();
    assert_eq!(
        outputs
            .iter()
            .filter(|d| matches!(d.definition, Definition::Qualified { .. }))
            .count(),
        186
    );
    assert_eq!(
        outputs
            .iter()
            .filter(|d| matches!(d.definition, Definition::Blocked { .. }))
            .count(),
        269
    );
    assert_eq!(r.blocker_register.len(), 14);
    assert_eq!(
        outputs
            .iter()
            .filter(|d| text(&d.declaration, "status") == "QUALIFIED"
                && text(d.declaration.get("producer").unwrap(), "kind") == "literal_string_copy")
            .count(),
        26
    );
    assert!(outputs
        .iter()
        .all(|d| d.applicability == Applicability::Unknown));
    assert_eq!(r.complete_interpretation, Status::Unavailable);
}

fn semantic_run(mutate: impl FnOnce(&mut BTreeMap<String, Json>)) -> Qualification {
    let mut sealed = manifest_resources(&fixture().ai, &fixture().resources);
    mutate(&mut sealed);
    let c = Catalog::new(&sealed).unwrap();
    let mut out = Qualification::new();
    out.authority_qualified = true;
    qualify_catalog(&c, &mut out);
    out.finish()
}
fn mutate_catalog(mutate: impl FnOnce(&mut Value)) -> Qualification {
    semantic_run(|map| {
        let mut value = v(&map[CATALOG]);
        mutate(&mut value);
        map.insert(CATALOG.into(), j(value));
    })
}
fn row<'a>(catalog: &'a mut Value, ty: &str) -> &'a mut Value {
    catalog["types"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|t| st(t, "semantic_type") == ty)
        .unwrap()
}
fn entry<'a>(row: &'a mut Value, path: &str) -> &'a mut Value {
    row["outputs"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|e| st(e, "destination") == path)
        .unwrap()
}
fn assert_failed(r: &Qualification) {
    assert_ne!(r.status, Status::CatalogQualified, "{r:#?}");
    assert!(r.types.is_empty() && r.blocker_register.is_empty());
    assert_eq!(r.complete_interpretation, Status::Unavailable);
    assert!(!r.findings.is_empty());
}

#[test]
fn adversarial_catalog_mutations_do_not_use_scf_or_count_shortcuts() {
    for fault in [
        "source_selector",
        "destination_selector",
        "branch",
        "missing_required",
        "missing_conditional",
        "nested",
        "duplicate",
        "BLOCKED_producer",
        "assumed_condition",
        "inherited_identity",
        "unknown_operation",
        "label_source",
        "label_ownership",
        "lost_semantic_input",
        "custom_owner",
        "owner_local",
        "relationship_branch",
        "truncated_operation",
        "rewritten_system_summary",
        "missing_verification",
        "wrong_input_meaning",
        "wrong_equality",
        "wrong_branch_schema",
        "rewritten_inherited_resource",
    ] {
        let r = mutate_catalog(|catalog| match fault {
            "wrong_branch_schema" => {
                catalog["branches"][0]["schema"] = catalog["branches"][1]["schema"].clone();
            }
            "rewritten_inherited_resource" => {
                entry(row(catalog, "adr/logical"), "/name")["producer"]["rule"]
                    ["canonical_resource_key"] =
                    json!("architecture-interpretation/1.4/field-dispositions-1.7-to-2.5");
            }
            "missing_verification" => {
                entry(row(catalog, "adr/logical"), "/name")["verification"]
                    .as_array_mut()
                    .unwrap()
                    .remove(0);
            }
            "wrong_input_meaning" => {
                entry(row(catalog, "adr/logical"), "/entity_type")["producer"]["source_field"] =
                    json!("infer_from_filename");
            }
            "wrong_equality" => {
                entry(row(catalog, "adr/logical"), "/name")["semantic_equality"] =
                    json!("digest_equality");
            }
            "source_selector" => {
                row(catalog, "adr/logical")["source_schema"]["schema_pointer"] =
                    json!("/properties/title")
            }
            "destination_selector" => {
                entry(row(catalog, "adr/logical"), "/name")["destination_schema"]
                    ["schema_pointer"] = json!("/oneOf/0/properties/summary")
            }
            "branch" => {
                row(catalog, "adr/logical")["output_branch"] = json!("normative-proposition")
            }
            "missing_required" => row(catalog, "adr/logical")["outputs"]
                .as_array_mut()
                .unwrap()
                .retain(|e| st(e, "destination") != "/id"),
            "missing_conditional" => row(catalog, "adr/logical")["outputs"]
                .as_array_mut()
                .unwrap()
                .retain(|e| st(e, "destination") != "/description"),
            "nested" => {
                let e = catalog["types"]
                    .as_array_mut()
                    .unwrap()
                    .iter_mut()
                    .flat_map(|t| t["outputs"].as_array_mut().unwrap())
                    .find(|e| !list(e, "required_subdestinations").is_empty())
                    .unwrap();
                e["required_subdestinations"].as_array_mut().unwrap().pop();
            }
            "duplicate" => {
                let r = row(catalog, "adr/logical");
                let copy = r["outputs"][0].clone();
                r["outputs"].as_array_mut().unwrap().push(copy);
            }
            "BLOCKED_producer" => {
                let r = row(catalog, "adr/logical");
                let p = entry(r, "/name")["producer"].clone();
                entry(r, "/alias_ref")["producer"] = p;
            }
            "assumed_condition" => {
                entry(row(catalog, "adr/logical"), "/description")["applicability"]
                    ["proven_inapplicable"] = json!(true)
            }
            "inherited_identity" => {
                entry(row(catalog, "adr/logical"), "/name")["producer"]["rule_id"] =
                    json!("AI1.4.fake.title")
            }
            "unknown_operation" => {
                entry(row(catalog, "adr/logical"), "/summary")["producer"]["kind"] =
                    json!("summarize")
            }
            "label_source" => {
                entry(row(catalog, "entity/decision"), "/name")["producer"]["source_field"] =
                    json!("summary")
            }
            "label_ownership" => {
                entry(row(catalog, "entity/decision"), "/name")["classification"] =
                    json!("semantic")
            }
            "lost_semantic_input" => row(catalog, "entity/decision")["outputs"]
                .as_array_mut()
                .unwrap()
                .retain(|e| !st(e, "destination").contains("semantic_extensions")),
            "custom_owner" => {
                let owner = entry(row(catalog, "entity/decision"), "/lifecycle_stage").clone();
                *entry(row(catalog, "entity/extension"), "/lifecycle_stage") = owner;
            }
            "owner_local" => {
                row(catalog, "value/topology_component")["identity_policy"] =
                    json!("canonical_uuidv7")
            }
            "relationship_branch" => {
                row(catalog, "relationship/extension")["output_branch"] = json!("regular")
            }
            "truncated_operation" => {
                catalog["operation"]["algorithm"] = json!("take first 80 characters")
            }
            "rewritten_system_summary" => {
                entry(row(catalog, "entity/system"), "/summary")["producer"]["source_field"] =
                    json!("description")
            }
            _ => unreachable!(),
        });
        assert_failed(&r);
        if fault == "inherited_identity" {
            assert!(r.findings.iter().any(|f| f.key == "adr/logical#/name"));
        }
        if fault == "rewritten_inherited_resource" {
            assert_eq!(r.status, Status::Unavailable, "{:?}", r.findings);
        } else {
            assert_eq!(r.status, Status::Rejected, "{fault}: {:?}", r.findings);
        }
    }
}

#[test]
fn missing_branch_constraints_and_broken_schema_references_fail_closed() {
    let r = mutate_catalog(|c| {
        c["branches"][0]["requirements"]
            .as_array_mut()
            .unwrap()
            .pop();
    });
    assert_failed(&r);
    assert!(r
        .findings
        .iter()
        .any(|f| f.detail.contains("incomplete_branch_requirements")));
    for fault in [
        "dependency_keyword",
        "unknown_keyword",
        "broken_ref",
        "schema_digest",
        "open_schema",
    ] {
        let r = semantic_run(|m| {
            let key = format!("{CATALOG}.schema");
            let mut s = v(&m[&key]);
            match fault {
                "dependency_keyword" => s["dependentRequired"] = json!({"types":["arbitrary"]}),
                "unknown_keyword" => s["unevaluatedProperties"] = json!(false),
                "broken_ref" => {
                    s["properties"]["types"]["$ref"] = json!("../../9.9/missing.json#/$defs/types")
                }
                "schema_digest" => {
                    let mut c = v(&m[CATALOG]);
                    c["field_dispositions"]["content_digest"] =
                        json!(format!("sha256:{}", "0".repeat(64)));
                    m.insert(CATALOG.into(), j(c));
                }
                "open_schema" => s["additionalProperties"] = json!(true),
                _ => unreachable!(),
            }
            m.insert(key, j(s));
        });
        if fault == "open_schema" {
            // Closure pinning already forbids this; separately demonstrate that
            // direct semantic qualification must reject an open companion too.
            assert_failed(&r);
        } else {
            assert_failed(&r);
        }
        if ["dependency_keyword", "unknown_keyword"].contains(&fault) {
            assert_eq!(r.status, Status::Unavailable);
        }
    }
}

#[test]
fn full_boundary_rejects_wrong_versions_resources_and_recalculated_invalid_scf() {
    let f = fixture();
    for fault in [
        "ai_version",
        "acc_scf",
        "nm_version",
        "missing",
        "tampered",
        "duplicate",
        "recomputed",
    ] {
        let mut x = Fixture {
            ai: f.ai.clone(),
            acc: f.acc.clone(),
            nm: f.nm.clone(),
            resources: f.resources.clone(),
        };
        match fault {
            "ai_version" => {
                x.ai.as_object_mut()
                    .unwrap()
                    .insert("semanticContractVersion".into(), string("1.3"))
            }
            "acc_scf" => x
                .acc
                .as_object_mut()
                .unwrap()
                .insert("semanticContractFingerprint".into(), string(INHERITED_SCF)),
            "nm_version" => {
                x.nm.as_object_mut()
                    .unwrap()
                    .insert("semanticContractVersion".into(), string("2.4"))
            }
            "missing" => {
                x.resources
                    .retain(|r| text(r, "canonicalResourceKey") != CATALOG);
                None
            }
            "tampered" => {
                let r = x
                    .resources
                    .iter_mut()
                    .find(|r| text(r, "canonicalResourceKey") == CATALOG)
                    .unwrap();
                r.as_object_mut()
                    .unwrap()
                    .insert("content".into(), Json::Null);
                None
            }
            "duplicate" => {
                x.resources.push(x.resources[0].clone());
                None
            }
            "recomputed" => {
                // Modify a valid manifest identity, then calculate its real new
                // SCF. The closed profile must reject it rather than treating
                // consistent hashing as authority selection.
                let d = x.ai.as_object_mut().unwrap();
                d.insert("semanticContractVersion".into(), string("1.5"));
                let fp = semantic_contract::fingerprint(&object([
                    ("definition".into(), x.ai.clone()),
                    ("mode".into(), string("calculate")),
                ]));
                let scf = fp
                    .get("semantic_contract_fingerprint")
                    .expect("SCF actually recalculated");
                assert_ne!(scf.as_str(), Some(AI_SCF));
                x.ai.as_object_mut()
                    .unwrap()
                    .insert("semanticContractFingerprint".into(), scf.clone());
                None
            }
            _ => unreachable!(),
        };
        let r = run(&x);
        assert_failed(&r);
        assert_eq!(r.status, Status::Unavailable, "{fault}");
        assert!(!r.authority_qualified);
    }
}

#[test]
fn permutation_and_independent_replay_preserve_exact_static_evidence() {
    let f = fixture();
    let r = run(f);
    let mut resources = f.resources.clone();
    resources.reverse();
    // Unselected, malformed extras must not establish authority or affect output.
    resources.push(j(
        json!({"canonicalResourceKey":"ambient/latest/schema","content":{"type":"number"}}),
    ));
    let x = Fixture {
        ai: f.ai.clone(),
        acc: f.acc.clone(),
        nm: f.nm.clone(),
        resources,
    };
    assert_eq!(r, run(&x));
    let ai = subset(&f.ai, &f.resources);
    let nm = subset(&f.nm, &f.resources);
    let (a, b, n) = (
        Bundle {
            definition: &f.ai,
            resources: &ai,
        },
        Bundle {
            definition: &f.acc,
            resources: &f.resources,
        },
        Bundle {
            definition: &f.nm,
            resources: &nm,
        },
    );
    assert!(verify(a, b, n, &r));
    let mut forged = r.clone();
    forged.types[0].destinations[0].declaration =
        j(json!({"output_value":"fabricated or truncated"}));
    assert!(!verify(a, b, n, &forged));
    let mut forged = r.clone();
    forged.complete_interpretation = Status::CatalogQualified;
    assert!(!verify(a, b, n, &forged));
}

#[test]
fn source_string_domains_are_retained_without_executing_labels() {
    let sealed = manifest_resources(&fixture().ai, &fixture().resources);
    let c = Catalog::new(&sealed).unwrap();
    let catalog = c.read(CATALOG).unwrap();
    for ty in list(&catalog, "types") {
        for e in list(ty, "outputs") {
            if st(&e["producer"], "kind") != "literal_string_copy" {
                continue;
            }
            let input = &e["producer"]["inputs"][0];
            let key = st(input, "canonical_resource_key");
            let ptr = st(input, "schema_pointer");
            let (_, _, shape) = c.deref(key.into(), ptr.into()).unwrap();
            assert_eq!(shape["type"], "string");
            for nonstring in [Value::Null, json!(false), json!(1), json!([]), json!({})] {
                assert!(schema::validate_fragment(&c.evaluation, key, ptr, &j(nonstring)).is_err());
            }
            // Free narrative source fields keep exact Unicode and arbitrary length;
            // alias constraints remain selected rather than weakened to accept them.
            if st(&e["producer"], "source_field") == "context" {
                for s in ["", "Unicode: Δ🙂", &"x".repeat(10000)] {
                    let actual = schema::validate_fragment(&c.evaluation, key, ptr, &string(s));
                    if s.is_empty() && shape["minLength"].as_u64().unwrap_or(0) > 0 {
                        assert!(actual.is_err());
                    } else {
                        assert!(actual.is_ok());
                    }
                }
            }
        }
    }
}

#[test]
fn semantically_invalid_rule_with_genuinely_recalculated_valid_closure_is_not_authority() {
    let f = fixture();
    let mut sealed = manifest_resources(&f.ai, &f.resources);
    let mut cat = v(&sealed[CATALOG]);
    entry(row(&mut cat, "adr/logical"), "/name")["producer"]["rule_id"] = json!("invented-rule");
    sealed.insert(CATALOG.into(), j(cat));
    // Repair exact resource-reference digests in dependent resource contents;
    // this is adversarial fixture construction, never production publication.
    fn refresh(n: &mut Value, digests: &BTreeMap<String, String>) {
        if let Value::Object(m) = n {
            if let Some(key) = m
                .get("canonical_resource_key")
                .and_then(Value::as_str)
                .map(str::to_owned)
            {
                if m.contains_key("content_digest") {
                    if let Some(d) = digests.get(&key) {
                        m.insert("content_digest".into(), json!(d));
                    }
                }
            }
            for x in m.values_mut() {
                refresh(x, digests);
            }
        } else if let Value::Array(a) = n {
            for x in a {
                refresh(x, digests);
            }
        }
    }
    for _ in 0..sealed.len() {
        let digests = sealed
            .iter()
            .map(|(k, v)| (k.clone(), format!("sha256:{}", digest(v))))
            .collect();
        let old = sealed.clone();
        // Historical resources are never rewritten, even in this adversarial
        // fixture. Only successor-owned contents depend on the new catalog.
        for (key, content) in &mut sealed {
            if key.starts_with(AI) {
                let mut n = v(content);
                refresh(&mut n, &digests);
                *content = j(n);
            }
        }
        if old == sealed {
            break;
        }
    }
    let mut def = v(&f.ai);
    let digests: BTreeMap<_, _> = sealed
        .iter()
        .map(|(k, v)| (k.clone(), format!("sha256:{}", digest(v))))
        .collect();
    for e in def["resourceManifest"].as_array_mut().unwrap() {
        e["contentDigest"] = json!(digests[st(e, "canonicalResourceKey")]);
        for d in e["dependencies"].as_array_mut().unwrap() {
            d["contentDigest"] = json!(digests[st(d, "canonicalResourceKey")]);
        }
    }
    let mut definition = j(def);
    let fp = semantic_contract::fingerprint(&object([
        ("definition".into(), definition.clone()),
        ("mode".into(), string("calculate")),
    ]));
    let scf = fp
        .get("semantic_contract_fingerprint")
        .expect("real recomputed fingerprint")
        .clone();
    assert_ne!(scf, string(AI_SCF));
    definition
        .as_object_mut()
        .unwrap()
        .insert("semanticContractFingerprint".into(), scf);
    let resources: Vec<_> = sealed
        .iter()
        .map(|(k, c)| {
            object([
                ("canonicalResourceKey".into(), string(k)),
                ("content".into(), c.clone()),
            ])
        })
        .collect();
    let closure = semantic_contract::validate_closure(&object([
        ("definition".into(), definition.clone()),
        ("resources".into(), Json::Array(resources.clone())),
    ]));
    assert_eq!(
        closure.get("closure_valid"),
        Some(&Json::Bool(true)),
        "{closure:#?}"
    );
    assert!(verify_bundle(
        Bundle {
            definition: &definition,
            resources: &resources
        },
        "architecture-interpretation",
        "1.4",
        AI_SCF
    )
    .is_err());
    let mut r = Qualification::new();
    qualify_catalog(&Catalog::new(&sealed).unwrap(), &mut r);
    let r = r.finish();
    assert_failed(&r);
    assert!(
        r.findings
            .iter()
            .any(|f| f.detail.contains("wrong_inherited_rule_identity")),
        "{:?}",
        r.findings
    );
}

#[test]
fn string_input_type_and_mixed_failure_precedence_are_independently_checked() {
    for fault in ["number_input", "unsupported_source_condition"] {
        let r = semantic_run(|m| {
            let key = "authoring/1.7/schema/adr-logical.schema";
            let mut source = v(&m[key]);
            if fault == "number_input" {
                source["properties"]["context"]["type"] = json!("number");
            } else {
                source["dependentRequired"] = json!({"title":["context"]});
            }
            m.insert(key.into(), j(source));
            let d = format!("sha256:{}", digest(&m[key]));
            fn update(n: &mut Value, key: &str, d: &str) {
                if let Value::Object(o) = n {
                    if o.get("canonical_resource_key") == Some(&json!(key))
                        && o.contains_key("content_digest")
                    {
                        o.insert("content_digest".into(), json!(d));
                    }
                    for x in o.values_mut() {
                        update(x, key, d);
                    }
                } else if let Value::Array(a) = n {
                    for x in a {
                        update(x, key, d);
                    }
                }
            }
            let mut cat = v(&m[CATALOG]);
            update(&mut cat, key, &d);
            if fault == "unsupported_source_condition" {
                let r = row(&mut cat, "entity/decision");
                let copy = r["outputs"][0].clone();
                r["outputs"].as_array_mut().unwrap().push(copy);
            }
            m.insert(CATALOG.into(), j(cat));
        });
        assert_failed(&r);
        assert_eq!(r.status, Status::Rejected, "{:?}", r.findings);
        if fault == "number_input" {
            assert!(
                r.findings
                    .iter()
                    .any(|f| f.detail.contains("label_input_not_string")),
                "{:?}",
                r.findings
            );
        } else {
            assert!(r.findings.iter().any(|f| f.status == Status::Unavailable));
            assert!(r.findings.iter().any(|f| f.status == Status::Rejected));
        }
        assert!(!r.findings.iter().any(|f| f.status == Status::Unresolved));
    }
}
