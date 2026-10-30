use super::*;
use sha2::{Digest, Sha256};
use std::{fs, path::PathBuf, sync::OnceLock};

#[derive(Clone)]
struct Fixture {
    definitions: Vec<Json>,
    resources: BTreeMap<String, Json>,
}
fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}
fn load(path: impl AsRef<std::path::Path>) -> Json {
    serde_json::from_slice(&fs::read(root().join(path)).unwrap()).unwrap()
}
fn source(key: &str) -> Json {
    let parts: Vec<_> = key.split('/').collect();
    let base = format!("contracts/{}/v{}", parts[0], parts[1]);
    let own = if parts.len() == 4 && parts[2] == "schema" {
        format!("schema/{}/v{}/{}.json", parts[0], parts[1], parts[3])
    } else if parts[2] == "contract" {
        format!("{base}/contract.json")
    } else if parts[2] == "schema" {
        format!("{base}/schema.json")
    } else {
        format!("{base}/resources/{}.json", parts[2])
    };
    if root().join(&own).exists() {
        return load(own);
    }
    let maintained = (parts[0] == "normalized-model" && parts[1] == "2.5")
        || (matches!(
            parts[0],
            "architecture-interpretation" | "authoring-construction"
        ) && parts[1] == "1.5");
    if maintained
        && !(parts[0] == "normalized-model" && matches!(parts[2], "contract" | "conformance"))
    {
        panic!("missing maintained canonical resource: {own}");
    }
    let flat = if parts[2] == "contract" {
        format!(
            "contracts/semantic-contract/v1.0/definitions/{}-{}.json",
            parts[0], parts[1]
        )
    } else {
        format!(
            "contracts/semantic-contract/v1.0/resources/{}.json",
            key.replace('/', "-")
        )
    };
    if root().join(&flat).exists() {
        return load(flat);
    }
    // Released AI 1.0 source-resource filenames are versionless on disk;
    // the selected canonical resource identity remains exact.
    load(flat.replace(
        "architecture-interpretation-1.0-source-",
        "architecture-interpretation-source-",
    ))
}
fn fixture() -> &'static Fixture {
    static F: OnceLock<Fixture> = OnceLock::new();
    F.get_or_init(|| {
        let definitions: Vec<Json> = CANONICAL
            .iter()
            .map(|s| serde_json::from_str(s).unwrap())
            .collect();
        let resources = definitions
            .iter()
            .flat_map(|d| array(d, "resourceManifest"))
            .map(|m| {
                let k = text(m, "canonicalResourceKey");
                (k.into(), source(k))
            })
            .collect();
        Fixture {
            definitions,
            resources,
        }
    })
}
fn resources(f: &Fixture, index: usize) -> Vec<Json> {
    array(&f.definitions[index], "resourceManifest")
        .iter()
        .map(|m| {
            let key = text(m, "canonicalResourceKey");
            object([
                ("canonicalResourceKey".into(), string(key)),
                ("content".into(), f.resources[key].clone()),
            ])
        })
        .collect()
}
fn run(f: &Fixture) -> Qualification {
    let r: Vec<_> = (0..3).map(|i| resources(f, i)).collect();
    qualify(
        Bundle {
            definition: &f.definitions[0],
            resources: &r[0],
        },
        Bundle {
            definition: &f.definitions[1],
            resources: &r[1],
        },
        Bundle {
            definition: &f.definitions[2],
            resources: &r[2],
        },
    )
}
fn selected_run(f: &Fixture) -> Qualification {
    let r: Vec<_> = (0..3).map(|i| resources(f, i)).collect();
    qualify_selected(
        &f.definitions,
        [
            Bundle {
                definition: &f.definitions[0],
                resources: &r[0],
            },
            Bundle {
                definition: &f.definitions[1],
                resources: &r[1],
            },
            Bundle {
                definition: &f.definitions[2],
                resources: &r[2],
            },
        ],
    )
}
fn assert_rejected(q: &Qualification, code: &str) {
    assert_eq!(q.status(), Status::Rejected, "{:?}", q.findings());
    assert!(
        q.findings().iter().any(|f| f.code == code),
        "{:?}",
        q.findings()
    );
    assert!(q.resources().is_empty() && q.authorities().is_empty());
    assert_eq!(q.complete_interpretation(), Status::Unavailable);
}
fn digest(value: &Json) -> String {
    format!("sha256:{:x}", Sha256::digest(canonical(value).as_bytes()))
}
fn set(value: &mut Json, key: &str, child: Json) {
    value.as_object_mut().unwrap().insert(key.into(), child);
}
fn rehash(def: &mut Json) {
    let result = semantic_contract::fingerprint(&object([
        ("definition".into(), def.clone()),
        ("mode".into(), string("calculate")),
    ]));
    assert!(success(&result), "{result:?}");
    set(
        def,
        "semanticContractFingerprint",
        string(text(&result, "semantic_contract_fingerprint")),
    );
}
fn native_valid(f: &Fixture) {
    for i in 0..3 {
        let result = semantic_contract::validate_closure(&object([
            ("definition".into(), f.definitions[i].clone()),
            ("resources".into(), Json::Array(resources(f, i))),
        ]));
        assert!(success(&result), "{result:?}");
    }
}

#[test]
fn canonical_candidates_qualify_without_execution_or_historical_manifest_import() {
    let f = fixture();
    let q = run(f);
    assert_eq!(q.status(), Status::AuthorityQualified, "{:?}", q.findings());
    assert_eq!(q.complete_interpretation(), Status::Unavailable);
    assert_eq!(q.instance_applicability(), "Unknown");
    for (i, a) in q.authorities().iter().enumerate() {
        assert_eq!(
            a.fingerprint,
            text(&f.definitions[i], "semanticContractFingerprint")
        );
        assert_eq!(
            a.resource_count,
            array(&f.definitions[i], "resourceManifest").len()
        );
    }
    assert!(q
        .resources()
        .contains_key("authoring-construction/1.3/ledger.schema"));
    let history = &q.resources()["architecture-interpretation/1.3/contract"];
    assert!(array(history, "resourceManifest")
        .iter()
        .any(|m| !q.resources().contains_key(text(m, "canonicalResourceKey"))));
    let catalog = &q.resources()["architecture-interpretation/1.5/required-output-derivations"];
    assert_eq!(array(catalog, "types").len(), 27);
    assert_eq!(array(catalog, "branches").len(), 6);
    let outputs: Vec<_> = array(catalog, "types")
        .iter()
        .flat_map(|t| array(t, "outputs"))
        .collect();
    for (status, count) in [("QUALIFIED", 240), ("BLOCKED", 215)] {
        assert_eq!(
            outputs
                .iter()
                .filter(|o| text(o, "status") == status)
                .count(),
            count
        );
    }
    let recipe_count = outputs
        .iter()
        .filter(|o| {
            matches!(
                text(at(o, &["producer"]), "kind"),
                "literal_alias_join"
                    | "literal_entity_uri"
                    | "uuidv7_unix_milliseconds_to_rfc3339_utc"
            )
        })
        .count();
    assert_eq!(recipe_count, 54);
    assert_eq!(
        outputs
            .iter()
            .filter(|o| text(at(o, &["producer"]), "kind") == "literal_string_copy")
            .count(),
        26
    );
    let rules = &q.resources()["authoring-construction/1.5/rules"];
    assert_eq!(
        array(
            at(rules, &["required_output"]),
            "identity_recipe_operations"
        )
        .len(),
        3
    );
    assert_eq!(
        array(
            &q.resources()["authoring-construction/1.5/composition-bindings"],
            "rows"
        )
        .len(),
        1
    );
}

#[test]
fn definition_and_resource_permutations_preserve_exact_qualification() {
    let f = fixture();
    let mut defs = f.definitions.clone();
    let mut r: Vec<_> = (0..3).map(|i| resources(f, i)).collect();
    for (i, d) in defs.iter_mut().enumerate() {
        r[i].reverse();
        let members = d
            .as_object_mut()
            .unwrap()
            .get_mut("resourceManifest")
            .unwrap()
            .as_array_mut()
            .unwrap();
        members.reverse();
        for m in members {
            m.as_object_mut()
                .unwrap()
                .get_mut("dependencies")
                .unwrap()
                .as_array_mut()
                .unwrap()
                .reverse();
        }
    }
    let actual = qualify(
        Bundle {
            definition: &defs[0],
            resources: &r[0],
        },
        Bundle {
            definition: &defs[1],
            resources: &r[1],
        },
        Bundle {
            definition: &defs[2],
            resources: &r[2],
        },
    );
    assert_eq!(actual, run(f));
}

#[test]
fn all_supplied_members_remain_visible_and_fail_atomically() {
    let f = fixture();
    for fault in [
        "missing",
        "duplicate",
        "extra",
        "conflict",
        "digest",
        "claim",
    ] {
        let mut r: Vec<_> = (0..3).map(|i| resources(f, i)).collect();
        let code = match fault {
            "missing" => {
                r[2].pop();
                "semantic_contract.missing_resource_content"
            }
            "duplicate" => {
                let duplicate = r[2][0].clone();
                r[2].push(duplicate);
                "semantic_contract.duplicate_supplied_resource"
            }
            "extra" => {
                r[2].push(object([
                    (
                        "canonicalResourceKey".into(),
                        string("authoring-construction/1.4/conformance"),
                    ),
                    ("content".into(), Json::Null),
                ]));
                "semantic_contract.unlisted_resource"
            }
            "conflict" => {
                let mut x = r[2][0].clone();
                set(&mut x, "content", Json::Null);
                r[2].push(x);
                "semantic_contract.conflicting_resource_definition"
            }
            "claim" => {
                set(&mut r[2][0], "authority_qualified", Json::Bool(true));
                "semantic_contract.unknown_resource_content_field"
            }
            _ => {
                set(&mut r[2][0], "content", Json::Null);
                "semantic_contract.resource_digest_mismatch"
            }
        };
        let q = qualify(
            Bundle {
                definition: &f.definitions[0],
                resources: &r[0],
            },
            Bundle {
                definition: &f.definitions[1],
                resources: &r[1],
            },
            Bundle {
                definition: &f.definitions[2],
                resources: &r[2],
            },
        );
        assert_rejected(&q, code);
        r[2].reverse();
        let again = qualify(
            Bundle {
                definition: &f.definitions[0],
                resources: &r[0],
            },
            Bundle {
                definition: &f.definitions[1],
                resources: &r[1],
            },
            Bundle {
                definition: &f.definitions[2],
                resources: &r[2],
            },
        );
        assert_eq!(q, again);
    }
}

#[test]
fn wrong_versions_roles_conformance_and_edges_cannot_replace_selection() {
    for fault in [
        "family",
        "version",
        "role",
        "conformance",
        "edge",
        "edge_digest",
        "SCF",
    ] {
        let mut f = fixture().clone();
        let d = &mut f.definitions[2];
        match fault {
            "family" => set(d,"semanticContractFamily",string("architecture-interpretation")),
            "version" => set(d,"semanticContractVersion",string("1.4")),
            "SCF" => set(d,"semanticContractFingerprint",string("scf:v1:sha256:0000000000000000000000000000000000000000000000000000000000000000")),
            "conformance" => set(d,"frozenNormativeConformanceResources",Json::Array(vec![string("architecture-interpretation/1.5/conformance")])),
            _ => {
                let members=d.as_object_mut().unwrap().get_mut("resourceManifest").unwrap().as_array_mut().unwrap();
                if fault=="role" {let m=members.iter_mut().find(|m| text(m,"role")!="normative-definition").unwrap();set(m,"role",string("normative-definition"));}
                else {let m=members.iter_mut().find(|m| !array(m,"dependencies").is_empty()).unwrap();let deps=m.as_object_mut().unwrap().get_mut("dependencies").unwrap().as_array_mut().unwrap();if fault=="edge" {deps.pop();} else {set(&mut deps[0],"contentDigest",string("sha256:0000000000000000000000000000000000000000000000000000000000000000"));}}
            }
        }
        if !matches!(fault, "SCF" | "edge_digest") {
            rehash(d);
        }
        // These internally valid commitments still cannot authorize a caller's
        // alternative role or conformance policy.
        if matches!(fault, "role" | "conformance") {
            native_valid(&f);
        }
        assert_rejected(&run(&f), "unselected_definition");
    }
}

#[test]
fn supplied_historical_definitions_are_not_current_authority() {
    let f = fixture();
    // This exact historical definition is already retained as qualified
    // provenance. Verify its original commitment without importing its full
    // old manifest or binding that history to today's mutable NM resources.
    let historical = &f.resources["architecture-interpretation/1.3/contract"];
    assert!(success(&verify_definition(historical)));
    let r: Vec<_> = (0..3).map(|i| resources(f, i)).collect();
    let q = qualify(
        Bundle {
            definition: &f.definitions[0],
            resources: &r[0],
        },
        Bundle {
            definition: historical,
            resources: &r[1],
        },
        Bundle {
            definition: &f.definitions[2],
            resources: &r[2],
        },
    );
    assert_rejected(&q, "wrong_family_or_version");
}

fn replace_current(node: &mut Json, replacements: &BTreeMap<String, String>) {
    match node {
        Json::String(s) => {
            if let Some(new) = replacements.get(s) {
                *s = new.clone();
            }
        }
        Json::Array(a) => {
            for v in a {
                replace_current(v, replacements);
            }
        }
        Json::Object(o) => {
            for (k, v) in o {
                if !matches!(
                    k.as_str(),
                    "inherits"
                        | "inherited_cases"
                        | "inherited_conformance"
                        | "historical_definitions"
                ) {
                    replace_current(v, replacements);
                }
            }
        }
        _ => {}
    }
}
fn recommit(f: &mut Fixture, index: usize) {
    let def = &mut f.definitions[index];
    let rows = def
        .as_object_mut()
        .unwrap()
        .get_mut("resourceManifest")
        .unwrap()
        .as_array_mut()
        .unwrap();
    for row in rows {
        let key = text(row, "canonicalResourceKey").to_owned();
        set(row, "contentDigest", string(&digest(&f.resources[&key])));
        for dep in row
            .as_object_mut()
            .unwrap()
            .get_mut("dependencies")
            .unwrap()
            .as_array_mut()
            .unwrap()
        {
            let k = text(dep, "canonicalResourceKey");
            let hash = digest(&f.resources[k]);
            set(dep, "contentDigest", string(&hash));
        }
    }
    rehash(def);
}
// Test-only assembly of a new maintained cohort, using shared canonical JSON
// and SCF calculation. It is never a production authority-selection pathway.
fn rebuild(f: &mut Fixture) {
    let original = fixture();
    let mut replacements = BTreeMap::new();
    for index in 0..3 {
        let (family, version) = TARGETS[index];
        let prefix = format!("{family}/{version}/");
        let members = array(&f.definitions[index], "resourceManifest").to_vec();
        let mut pending: BTreeSet<String> = members
            .iter()
            .map(|m| text(m, "canonicalResourceKey").to_owned())
            .filter(|k| k.starts_with(&prefix))
            .collect();
        while !pending.is_empty() {
            let key = pending
                .iter()
                .find(|k| {
                    let m = members
                        .iter()
                        .find(|m| text(m, "canonicalResourceKey") == *k)
                        .unwrap();
                    array(m, "dependencies")
                        .iter()
                        .all(|d| !pending.contains(text(d, "canonicalResourceKey")))
                })
                .cloned()
                .expect("qualified acyclic graph");
            let content = f.resources.get_mut(&key).unwrap();
            replace_current(content, &replacements);
            replacements.insert(digest(&original.resources[&key]), digest(content));
            pending.remove(&key);
        }
        recommit(f, index);
        let def = &f.definitions[index];
        replacements.insert(
            text(&original.definitions[index], "semanticContractFingerprint").into(),
            text(def, "semanticContractFingerprint").into(),
        );
        let key = format!("{prefix}contract");
        if f.resources.contains_key(&key) {
            replacements.insert(digest(&original.resources[&key]), digest(def));
            f.resources.insert(key, def.clone());
        }
    }
}

#[test]
fn legitimate_same_version_maintained_revision_changes_commitments_without_rewriting_history() {
    let mut revised = fixture().clone();
    let key = "normalized-model/2.5/schema/unresolved-registry.schema";
    set(
        revised.resources.get_mut(key).unwrap(),
        "title",
        string("Same schema constraints; revised maintained annotation"),
    );
    rebuild(&mut revised);
    native_valid(&revised);
    for i in 0..3 {
        assert_ne!(
            text(&revised.definitions[i], "semanticContractFingerprint"),
            text(&fixture().definitions[i], "semanticContractFingerprint")
        );
    }
    let updated = selected_run(&revised);
    assert_eq!(
        updated.status(),
        Status::AuthorityQualified,
        "{:?}",
        updated.findings()
    );
    for (key, value) in &fixture().resources {
        if !key.starts_with("normalized-model/2.5/") && !key.contains("/1.5/") {
            assert_eq!(&revised.resources[key], value, "historical {key}");
        }
    }
    // The running production build remains selected by its real maintained
    // sources. A caller cannot claim the revised selection before that build.
    assert_rejected(&run(&revised), "unselected_definition");
    let r: Vec<_> = (0..3).map(|i| resources(fixture(), i)).collect();
    let stale = qualify_selected(
        &revised.definitions,
        [
            Bundle {
                definition: &fixture().definitions[0],
                resources: &r[0],
            },
            Bundle {
                definition: &fixture().definitions[1],
                resources: &r[1],
            },
            Bundle {
                definition: &fixture().definitions[2],
                resources: &r[2],
            },
        ],
    );
    assert_rejected(&stale, "unselected_definition");
}

#[test]
fn internally_valid_maintained_cohort_still_requires_independent_cross_selection() {
    for (key, path, code) in [
        (
            "authoring-construction/1.5/rules",
            vec!["authority", "architecture_interpretation", "fingerprint"],
            "wrong_AI_selection",
        ),
        (
            "authoring-construction/1.5/rules",
            vec!["authority", "normalized_model", "fingerprint"],
            "wrong_NM_selection",
        ),
        (
            "architecture-interpretation/1.5/rules",
            vec!["destination_authority", "semantic_contract_fingerprint"],
            "wrong_NM_selection",
        ),
    ] {
        let mut f = fixture().clone();
        let mut n = f.resources.get_mut(key).unwrap();
        for p in &path[..path.len() - 1] {
            n = n.as_object_mut().unwrap().get_mut(*p).unwrap();
        }
        set(
            n,
            path.last().unwrap(),
            string(
                "scf:v1:sha256:0000000000000000000000000000000000000000000000000000000000000000",
            ),
        );
        rebuild(&mut f);
        native_valid(&f);
        assert_rejected(&selected_run(&f), code);
        assert_rejected(&run(&f), "unselected_definition");
    }
}

#[test]
fn canonical_and_packaged_definition_views_agree() {
    for (i, (family, version)) in TARGETS.iter().enumerate() {
        let flat = format!("{family}-{version}.json");
        for dir in [
            "contracts/semantic-contract/v1.0/definitions",
            "src/adr_kit/semantic_contract/v1_0/definitions",
            "src/adr_kit/semantic_contract/v1_0",
        ] {
            assert_eq!(
                load(format!("{dir}/{flat}")),
                fixture().definitions[i],
                "stale mirror {dir}/{flat}"
            );
        }
    }
}

#[test]
fn current_schema_preserves_all_five_independent_checks_without_evaluating_them() {
    let q = run(fixture());
    let schema = &q.resources()["authoring-construction/1.5/schema"];
    let units = at(
        schema,
        &[
            "$defs",
            "required_output_qualification",
            "properties",
            "units",
            "items",
        ],
    );
    let expected: BTreeSet<_> = [
        "source_and_identity",
        "applicability_and_context",
        "inputs_and_types",
        "exact_operation",
        "complete_output",
    ]
    .into_iter()
    .collect();
    let mut definitions = 0;
    for unit in array(units, "oneOf") {
        for destination in array(at(unit, &["properties", "destinations", "items"]), "oneOf") {
            let verification = at(destination, &["properties", "verification"]);
            let fields: BTreeSet<_> = array(verification, "required")
                .iter()
                .map(|x| x.as_str().unwrap())
                .collect();
            assert_eq!(fields, expected);
            assert_eq!(
                at(verification, &["additionalProperties"]),
                &Json::Bool(false)
            );
            definitions += 1;
        }
    }
    assert_eq!(definitions, 240);
    assert_eq!(q.instance_applicability(), "Unknown");
}

#[test]
fn conflicting_contents_across_roots_retain_independent_violations_and_no_evidence() {
    let f = fixture();
    let mut ai = resources(f, 1);
    let nm = resources(f, 0);
    let acc = resources(f, 2);
    let shared = ai
        .iter_mut()
        .find(|r| {
            nm.iter()
                .any(|n| text(n, "canonicalResourceKey") == text(r, "canonicalResourceKey"))
        })
        .unwrap();
    set(shared, "content", Json::Null);
    let mut bad_acc = f.definitions[2].clone();
    set(&mut bad_acc, "semanticContractVersion", string("1.4"));
    let q = qualify(
        Bundle {
            definition: &f.definitions[0],
            resources: &nm,
        },
        Bundle {
            definition: &f.definitions[1],
            resources: &ai,
        },
        Bundle {
            definition: &bad_acc,
            resources: &acc,
        },
    );
    assert_rejected(&q, "cross_authority_content_conflict");
    assert!(q
        .findings()
        .iter()
        .any(|d| d.code == "wrong_family_or_version"));
    assert!(q
        .findings()
        .iter()
        .any(|d| d.code == "semantic_contract.resource_digest_mismatch"));
}

#[test]
fn historical_definition_under_current_resource_key_is_not_a_selected_authority() {
    for (key, historical, first) in [
        (
            "architecture-interpretation/1.5/contract",
            "architecture-interpretation/1.4/contract",
            2,
        ),
        (
            "normalized-model/2.5/contract",
            "normalized-model/2.4/contract",
            1,
        ),
    ] {
        let mut f = fixture().clone();
        f.resources.insert(key.into(), source(historical));
        for index in first..3 {
            recommit(&mut f, index);
            if index == 1 {
                f.resources.insert(
                    "architecture-interpretation/1.5/contract".into(),
                    f.definitions[1].clone(),
                );
            }
        }
        // Even a coherently committed supplied/source graph cannot relabel an
        // embedded historical definition as the independently qualified root.
        native_valid(&f);
        assert_rejected(&selected_run(&f), "wrong_selected_definition");
        assert_rejected(&run(&f), "unselected_definition");
    }
}

#[test]
fn invalid_maintained_input_is_unavailable_and_cannot_hide_a_caller_violation() {
    let f = fixture();
    let mut selected = f.definitions.clone();
    set(
        &mut selected[0],
        "semanticContractFingerprint",
        string("unverified"),
    );
    let r: Vec<_> = (0..3).map(|i| resources(f, i)).collect();
    let q = qualify_selected(
        &selected,
        [
            Bundle {
                definition: &f.definitions[0],
                resources: &r[0],
            },
            Bundle {
                definition: &f.definitions[1],
                resources: &r[1],
            },
            Bundle {
                definition: &f.definitions[2],
                resources: &r[2],
            },
        ],
    );
    assert_eq!(q.status(), Status::Unavailable);
    assert!(q.resources().is_empty() && q.authorities().is_empty());
    let mut wrong_nm = f.definitions[0].clone();
    set(&mut wrong_nm, "semanticContractVersion", string("2.4"));
    let same_root = qualify_selected(
        &selected,
        [
            Bundle {
                definition: &wrong_nm,
                resources: &r[0],
            },
            Bundle {
                definition: &f.definitions[1],
                resources: &r[1],
            },
            Bundle {
                definition: &f.definitions[2],
                resources: &r[2],
            },
        ],
    );
    assert_rejected(&same_root, "wrong_family_or_version");
    assert!(same_root
        .findings()
        .iter()
        .any(|d| d.status == Status::Unavailable));
    let mut bad = f.definitions[2].clone();
    set(&mut bad, "semanticContractVersion", string("1.4"));
    let mixed = qualify_selected(
        &selected,
        [
            Bundle {
                definition: &f.definitions[0],
                resources: &r[0],
            },
            Bundle {
                definition: &f.definitions[1],
                resources: &r[1],
            },
            Bundle {
                definition: &bad,
                resources: &r[2],
            },
        ],
    );
    assert_rejected(&mixed, "wrong_family_or_version");
    assert!(mixed
        .findings()
        .iter()
        .any(|d| d.status == Status::Unavailable));
}

#[test]
fn invalid_canonical_numbers_still_produce_permutation_stable_diagnostics() {
    let f = fixture();
    let mut r: Vec<_> = (0..3).map(|i| resources(f, i)).collect();
    set(
        &mut r[2][0],
        "content",
        Json::Number(9_007_199_254_740_992_i64.into()),
    );
    let mut other = r[2][0].clone();
    set(
        &mut other,
        "content",
        Json::Number(9_007_199_254_740_994_i64.into()),
    );
    r[2].push(other);
    let first = qualify(
        Bundle {
            definition: &f.definitions[0],
            resources: &r[0],
        },
        Bundle {
            definition: &f.definitions[1],
            resources: &r[1],
        },
        Bundle {
            definition: &f.definitions[2],
            resources: &r[2],
        },
    );
    r[2].reverse();
    let second = qualify(
        Bundle {
            definition: &f.definitions[0],
            resources: &r[0],
        },
        Bundle {
            definition: &f.definitions[1],
            resources: &r[1],
        },
        Bundle {
            definition: &f.definitions[2],
            resources: &r[2],
        },
    );
    assert_rejected(&first, "semantic_contract.invalid_resource_content");
    assert_eq!(first, second);
}

#[test]
fn shared_canonical_content_identity_does_not_depend_on_number_spelling() {
    fn change_one(node: &mut Json) -> bool {
        match node {
            Json::Number(n) if n.as_i64() == Some(1) => {
                *n = serde_json::Number::from_f64(1.0).unwrap();
                true
            }
            Json::Object(o) => o.values_mut().any(change_one),
            Json::Array(a) => a.iter_mut().any(change_one),
            _ => false,
        }
    }
    let f = fixture();
    for altered_roots in [vec![1], vec![0, 1, 2]] {
        let mut r: Vec<_> = (0..3).map(|i| resources(f, i)).collect();
        for index in altered_roots {
            let source = r[index]
                .iter_mut()
                .find(|r| {
                    text(r, "canonicalResourceKey")
                        == "normalized-model/2.5/schema/normalized-entity.schema"
                })
                .unwrap();
            let original = source.get("content").unwrap().clone();
            let content = source.as_object_mut().unwrap().get_mut("content").unwrap();
            assert!(change_one(content));
            assert_ne!(&original, content);
            assert_eq!(canonical(&original), canonical(content));
        }
        let actual = qualify(
            Bundle {
                definition: &f.definitions[0],
                resources: &r[0],
            },
            Bundle {
                definition: &f.definitions[1],
                resources: &r[1],
            },
            Bundle {
                definition: &f.definitions[2],
                resources: &r[2],
            },
        );
        assert_eq!(actual, run(f));
    }
}
