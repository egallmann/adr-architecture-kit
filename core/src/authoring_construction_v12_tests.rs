//! Frozen cases are property oracles, not claims of full construction coverage.
use super::*;
use serde_json::{json, Value};
use std::{fs, path::PathBuf, sync::OnceLock};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_owned()
}
fn read(path: &str) -> Value {
    serde_json::from_slice(&fs::read(root().join(path)).unwrap()).unwrap()
}
pub(super) fn j(value: &Value) -> Json {
    serde_json::from_value(value.clone()).unwrap()
}
pub(super) fn bundle() -> &'static (Value, Vec<Value>) {
    static BUNDLE: OnceLock<(Value, Vec<Value>)> = OnceLock::new();
    BUNDLE.get_or_init(|| {
        let definition = read("contracts/authoring-construction/v1.2/contract.json");
        let resources = definition["resourceManifest"].as_array().unwrap().iter().map(|member| {
            let key = member["canonicalResourceKey"].as_str().unwrap();
            let filename = key.replace("architecture-interpretation/1.0/source-", "architecture-interpretation/source-").replace('/', "-");
            json!({"canonicalResourceKey":key,"content":read(&format!("contracts/semantic-contract/v1.0/resources/{filename}.json"))})
        }).collect();
        (definition,resources)
    })
}
fn resource(key: &str) -> Value {
    bundle()
        .1
        .iter()
        .find(|v| v["canonicalResourceKey"] == key)
        .unwrap()["content"]
        .clone()
}
fn members(manifest: &Value) -> Value {
    Value::Array(manifest.as_array().unwrap().iter().map(|m|json!({"canonical_resource_key":m["canonicalResourceKey"],"content_digest":m["contentDigest"]})).collect())
}
fn qualification(family: &str, version: &str, prefix: &str) -> Value {
    let manifest = Value::Array(
        bundle().0["resourceManifest"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|m| {
                m["canonicalResourceKey"]
                    .as_str()
                    .unwrap()
                    .starts_with(prefix)
            })
            .cloned()
            .collect(),
    );
    json!({"family":family,"version":version,"resources":members(&manifest)})
}
pub(super) fn fixture(number: usize) -> Value {
    read("contracts/authoring-construction/v1.2/resources/conformance.json")["cases"][number - 1]
        ["fixture"]["input"]
        .clone()
}
pub(super) fn request(input: &Value) -> Value {
    let mut fragments = input["fragments"].clone();
    for fragment in fragments.as_array_mut().unwrap() {
        fragment["semantic_kind"] = json!(fragment["semantic_type"]
            .as_str()
            .unwrap()
            .split('/')
            .next()
            .unwrap());
        fragment["contract_qualification"] =
            qualification("authoring", "1.7", "authoring/1.7/schema/");
        fragment["references"] = json!([]);
    }
    let old_schema = read("contracts/authoring-construction/v1.1/schema.json");
    let policies = &old_schema["$defs"]["identity_establishment_policy"]["properties"];
    let identity: serde_json::Map<String, Value> = policies
        .as_object()
        .unwrap()
        .iter()
        .map(|(key, value)| (key.clone(), value["const"].clone()))
        .collect();
    let mut request = json!({
        "contract_family":"authoring_construction", "contract_version":"1.2", "operation":"construct_authoring_set",
        "request":{"request_id":"qualification-test","fragments":fragments,"compositions":input["compositions"],"relationships":[]},
        "basis":{
            "acc":{"family":"authoring-construction","version":"1.2","semantic_contract_fingerprint":SCF},
            "adc":qualification("authoring-domain","1.1","authoring-domain/1.1/"),
            "authoring":qualification("authoring","1.7","authoring/1.7/schema/"),
            "normalized_model":qualification("normalized-model","2.4","normalized-model/2.4/schema/"),
            "architecture_interpretation":{"family":"architecture-interpretation","version":"1.2","semantic_contract_fingerprint":AI_SCF,
                "authority_closure":{"family":"architecture-interpretation","version":"1.2","resources":members(&resource("architecture-interpretation/1.2/contract")["resourceManifest"]) }},
            "custom_entity":null,"reference_basis":{"sealed":true,"entries":[]},"existing_source_basis":{"sealed":true,"entries":[]},
            "identity_establishment":identity,"provenance":{}
        }
    });
    if input.get("reference_basis").is_some() {
        let entries = input["reference_basis"]["entries"].as_array().unwrap().iter().map(|entry| json!({
            "reference_id":entry["reference_id"],"canonical_uuid":entry["canonical_uuid"],"semantic_kind":"entity","semantic_type":"entity/decision",
            "qualification":qualification("authoring","1.7","authoring/1.7/schema/"),"existence_state":"active"
        })).collect::<Vec<_>>();
        request["basis"]["reference_basis"]["entries"] = json!(entries);
    }
    request
}
fn run(request: &Value) -> Qualification {
    run_bundle(&bundle().0, &bundle().1, request)
}
fn run_bundle(definition: &Value, resources: &[Value], request: &Value) -> Qualification {
    qualify(
        &j(definition),
        &resources.iter().map(j).collect::<Vec<_>>(),
        &j(request),
    )
}
fn codes(result: &Qualification) -> BTreeSet<&str> {
    result.diagnostics.iter().map(|d| d.code.as_str()).collect()
}
fn sealed() -> BTreeMap<String, Json> {
    bundle()
        .1
        .iter()
        .map(|v| {
            (
                v["canonicalResourceKey"].as_str().unwrap().into(),
                j(&v["content"]),
            )
        })
        .collect()
}

#[test]
fn exact_closure_schema_and_binding_without_construction_or_mutation() {
    let request = request(&fixture(1));
    let original = request.clone();
    let result = run(&request);
    assert_eq!(
        result.authority,
        Check::Qualified,
        "{:?}",
        result.authority_diagnostics
    );
    assert_eq!(
        result.binding_table,
        Check::Qualified,
        "{:?}",
        result.diagnostics
    );
    assert_eq!(
        result.request_schema,
        Check::Qualified,
        "{:?}",
        result.diagnostics
    );
    assert_eq!(result.status, Status::Qualified, "{:?}", result.diagnostics);
    assert_eq!(result.endpoint_resolution, Check::Qualified);
    assert_eq!(result.bindings.len(), 1);
    assert_eq!(
        text(&result.bindings[0].binding, "binding_id"),
        "adr-logical.decisions.contains.entity-decision"
    );
    assert_eq!(
        result.bindings[0].child_identity.as_deref(),
        request["request"]["fragments"][1]["fields"]["id"].as_str()
    );
    assert!(!result.outstanding_dependencies.is_empty());
    assert_eq!(request, original);
    // Full result-schema features remain outside this bounded evaluator.
    assert!(
        schema_validation::preflight_fragment(&sealed(), SCHEMA, "/$defs/construction_result")
            .is_err()
    );
    assert!(format!("{result:?}").find("Constructed").is_none());
}

#[test]
fn frozen_structural_oracles_not_whole_construction_claims() {
    let cases = read("contracts/authoring-construction/v1.2/resources/conformance.json");
    for number in (6..=22).chain([40, 41]) {
        let case = &cases["cases"][number - 1];
        let request = request(&fixture(number));
        let result = run(&request);
        assert_eq!(
            result.request_schema,
            Check::Qualified,
            "case {number}: {:?}",
            result.diagnostics
        );
        let assertions = case["assertions"].as_array().unwrap();
        let expected = assertions
            .iter()
            .find(|a| a["path"] == "diagnostics.codes")
            .unwrap()["expected"]
            .as_str()
            .unwrap();
        assert!(
            codes(&result).contains(expected),
            "case {number}: {:?}",
            result.diagnostics
        );
        let status = assertions.iter().find(|a| a["path"] == "outcome").unwrap()["expected"]
            .as_str()
            .unwrap();
        assert_eq!(format!("{:?}", result.status), status, "case {number}");
        assert!(result.bindings.is_empty());
    }
}

#[test]
fn ordered_children_and_permutation_invariance() {
    let mut request = request(&fixture(2));
    let result = run(&request);
    assert_eq!(result.status, Status::Qualified, "{:?}", result.diagnostics);
    assert_eq!(result.bindings.len(), 2);
    assert!(result.bindings[0].ordering.as_u64() < result.bindings[1].ordering.as_u64());
    request["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    request["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    assert_eq!(result, run(&request));
    let case3 = fixture(3);
    assert_eq!(
        run(&super::tests::request(&case3["left"])),
        run(&super::tests::request(&case3["right"]))
    );
}

#[test]
fn identities_are_supplied_or_pending_never_minted() {
    for number in [4, 5] {
        let request = request(&fixture(number));
        let original = request.clone();
        let result = run(&request);
        assert_eq!(result.status, Status::Qualified, "{:?}", result.diagnostics);
        assert_eq!(request, original);
        if number == 5 {
            assert_eq!(result.bindings[0].child_identity, None);
            assert!(result
                .outstanding_dependencies
                .contains("canonical_identity_establishment"));
        }
    }
    let mut request = request(&fixture(1));
    request["request"]["fragments"][1]["fields"]["id"] = json!("not-a-uuid");
    assert_eq!(run(&request).status, Status::Rejected);
    let mut request = super::tests::request(&fixture(41));
    for fragment in request["request"]["fragments"].as_array_mut().unwrap() {
        if fragment["semantic_type"] == "entity/decision" {
            fragment["fields"].as_object_mut().unwrap().remove("id");
        }
    }
    let result = run(&request);
    assert_eq!(result.status, Status::Rejected);
    assert!(result
        .outstanding_dependencies
        .contains("duplicate_identity_after_identity_establishment"));
    assert!(codes(&result).contains("authoring_construction.composition.duplicate_identity"));
    assert!(result
        .diagnostics
        .iter()
        .filter(|d| d.code.ends_with("duplicate_identity"))
        .all(|d| d.semantic_identity.is_none()));
    assert!(result.bindings.is_empty());
}

fn assert_permutations(request: &mut Value) -> Qualification {
    let expected = run(request);
    for _ in 0..request["request"]["compositions"]
        .as_array()
        .unwrap()
        .len()
        .max(2)
    {
        request["request"]["fragments"]
            .as_array_mut()
            .unwrap()
            .reverse();
        request["request"]["compositions"]
            .as_array_mut()
            .unwrap()
            .rotate_left(1);
        assert_eq!(run(request), expected);
    }
    expected
}

#[test]
fn pending_child_multi_parent_ownership_is_provable_without_canonical_identity() {
    let mut request = request(&fixture(41));
    for fragment in request["request"]["fragments"].as_array_mut().unwrap() {
        fragment["fields"].as_object_mut().unwrap().remove("id");
    }
    let original = request.clone();
    let result = assert_permutations(&mut request);
    assert_eq!(result.status, Status::Rejected);
    let conflicts = result
        .diagnostics
        .iter()
        .filter(|d| d.code.ends_with("duplicate_identity"))
        .collect::<Vec<_>>();
    assert_eq!(conflicts.len(), 1);
    assert_eq!(conflicts[0].semantic_identity, None);
    assert!(result.bindings.is_empty());
    assert!(result
        .outstanding_dependencies
        .contains("canonical_identity_establishment"));
    assert!(result
        .outstanding_dependencies
        .contains("duplicate_identity_after_identity_establishment"));
    assert_eq!(
        original["request"]["fragments"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|f| f["fields"].get("id").is_none())
            .count(),
        3
    );
    // Equal content in distinct pending fragments is not proof of equal IDs.
    let mut request = original;
    let mut other = request["request"]["fragments"][1].clone();
    other["request_key"] = json!("other-child");
    request["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .push(other);
    request["request"]["compositions"][1]["child"] = json!("other-child");
    let result = assert_permutations(&mut request);
    assert_eq!(result.status, Status::Qualified);
    assert_eq!(result.bindings.len(), 2);
    assert!(result.bindings.iter().all(|b| b.child_identity.is_none()));

    // Ownership remains independently provable alongside other failed intents.
    let mut request = super::tests::request(&fixture(41));
    for fragment in request["request"]["fragments"].as_array_mut().unwrap() {
        fragment["fields"].as_object_mut().unwrap().remove("id");
    }
    let mut unmapped_child = request["request"]["fragments"][1].clone();
    unmapped_child["request_key"] = json!("unmapped-child");
    unmapped_child["semantic_type"] = json!("entity/invariant");
    request["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .push(unmapped_child);
    request["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .extend([
            json!({"parent":"parent","child":"parent","relation":"unmapped","ordering":0}),
            json!({"parent":"parent","child":"unmapped-child","relation":"contains","ordering":20}),
            json!({"parent":"parent","child":"missing","relation":"contains","ordering":30}),
        ]);
    let result = assert_permutations(&mut request);
    assert_eq!(result.status, Status::Rejected);
    for code in [
        "duplicate_identity",
        "relation_unknown",
        "binding_unavailable",
        "endpoint_unresolved",
    ] {
        assert!(
            codes(&result).contains(format!("authoring_construction.composition.{code}").as_str())
        );
    }
    assert!(!codes(&result).contains("authoring_construction.composition.cycle"));
}

#[test]
fn unknown_and_unmapped_relation_intents_cannot_create_containment_cycles() {
    for relation in ["composed_of", "unmapped"] {
        let mut request = request(&fixture(20));
        request["request"]["compositions"][1]["relation"] = json!(relation);
        let result = assert_permutations(&mut request);
        assert_eq!(result.status, Status::Rejected);
        assert_eq!(
            codes(&result),
            BTreeSet::from(["authoring_construction.composition.relation_unknown"])
        );
        // An unknown self-relation is not self-containment either.
        request["request"]["compositions"] = json!([
            {"parent":"parent","child":"parent","relation":relation,"ordering":0}
        ]);
        assert!(!codes(&assert_permutations(&mut request))
            .contains("authoring_construction.composition.cycle"));
    }
}

#[test]
fn containment_edges_require_the_qualified_tables_endpoint_policy() {
    let table = j(&resource(TABLE));
    let input = fixture(1);
    let parent = j(&input["fragments"][0]);
    let child = j(&input["fragments"][1]);
    let relation = text(
        &table.get("rows").unwrap().as_array().unwrap()[0],
        "relation",
    );
    assert!(governed_containment(&table, relation, &parent, &child));
    // Structural cycle rejection remains independent of full type-pair binding
    // availability, as required by the unchanged ACC12-20 oracle.
    assert!(governed_containment(&table, relation, &child, &parent));
    for role in [0, 1] {
        for operation in ["reference", "retire", "update"] {
            let mut fragments = input["fragments"].clone();
            fragments[role]["operation"] = json!(operation);
            assert!(!governed_containment(
                &table,
                relation,
                &j(&fragments[0]),
                &j(&fragments[1])
            ));
        }
        let mut fragments = input["fragments"].clone();
        fragments[role]["input_mode"] = json!("compact");
        assert!(!governed_containment(
            &table,
            relation,
            &j(&fragments[0]),
            &j(&fragments[1])
        ));
    }
}

#[test]
fn governed_cycles_remain_independent_of_unavailable_and_unknown_intents() {
    let mut request = request(&fixture(20));
    let mut outsider = request["request"]["fragments"][0].clone();
    outsider["request_key"] = json!("outsider");
    outsider["fields"]["id"] = json!("01900000-0000-7000-8000-000000000003");
    request["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .push(outsider);
    request["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .extend([
            json!({"parent":"outsider","child":"outsider","relation":"unmapped","ordering":0}),
            json!({"parent":"parent","child":"missing","relation":"contains","ordering":30}),
        ]);
    let result = assert_permutations(&mut request);
    assert_eq!(result.status, Status::Rejected);
    for code in [
        "cycle",
        "binding_unavailable",
        "relation_unknown",
        "endpoint_unresolved",
    ] {
        assert!(
            codes(&result).contains(format!("authoring_construction.composition.{code}").as_str())
        );
    }
    let cycle = result
        .diagnostics
        .iter()
        .find(|d| d.code.ends_with(".cycle"))
        .unwrap();
    assert_eq!(cycle.payload, j(&json!(["child", "parent"])));
    assert!(result.bindings.is_empty());
}

#[test]
fn exact_authority_faults_fail_before_intent_interpretation() {
    for fault in 27..=32 {
        let mut definition = bundle().0.clone();
        let mut resources = bundle().1.clone();
        let mut request = request(&fixture(1));
        match fault {
            27 => resources.retain(|r| r["canonicalResourceKey"] != TABLE),
            28 => {
                resources
                    .iter_mut()
                    .find(|r| r["canonicalResourceKey"] == TABLE)
                    .unwrap()["content"]["rows"][0]["relation"] = json!("wrong")
            }
            29 => {
                definition["resourceManifest"][0]["contentDigest"] =
                    json!(format!("sha256:{}", "0".repeat(64)));
            }
            30 => request["basis"]["acc"]["version"] = json!("1.1"),
            31 => {
                request["basis"]["acc"]["semantic_contract_fingerprint"] =
                    json!(format!("scf:v1:sha256:{}", "0".repeat(64)))
            }
            32 => {
                resources.pop();
            }
            _ => unreachable!(),
        }
        let result = run_bundle(&definition, &resources, &request);
        assert_eq!(result.status, Status::Unavailable, "fault {fault}");
        assert!(codes(&result).contains("semantic_contract.exact_authority_mismatch"));
        assert!(result.bindings.is_empty());
    }
    for field in ["semanticContractVersion", "semanticContractFingerprint"] {
        let mut definition = bundle().0.clone();
        definition[field] = json!("wrong");
        assert_eq!(
            run_bundle(&definition, &bundle().1, &request(&fixture(1))).status,
            Status::Unavailable
        );
    }
}

#[test]
fn semantic_authority_rechecks_reject_disagreement_and_duplicate_rows() {
    // Inner precondition tests: a mutated closure is separately rejected by
    // the public-to-crate entry before these semantic rechecks can execute.
    let definition = j(&bundle().0);
    let base = sealed();
    let table = base[TABLE].clone();
    assert!(qualify_table(Profile::Acc12, &definition, &base, &table));
    for (key, path, value) in [
        (
            "authoring-domain/1.1/contract",
            vec!["types", "0", "composition_policy", "child_identity"],
            json!("replace"),
        ),
        (
            "authoring-domain/1.1/contract",
            vec!["types", "0", "identity_policy", "supplied_identity"],
            json!("replace"),
        ),
        (
            "architecture-interpretation/1.2/field-dispositions-1.7-to-2.4",
            vec![],
            json!(null),
        ),
    ] {
        let mut resources = base.clone();
        let mut content: Value = serde_json::from_str(&canonical(&resources[key])).unwrap();
        if path.is_empty() {
            let field = content["semantic_types"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .flat_map(|ty| ty["field_dispositions"].as_array_mut().unwrap())
                .find(|f| f["semantic_field_key"] == "adr/logical#/decisions")
                .unwrap();
            field["ordering"] = json!("unordered");
        } else {
            // Select the row's exact parent type, not an incidental ADC index.
            let ty = content["types"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|ty| ty["key"] == json!({"kind":"adr","name":"logical"}))
                .unwrap();
            ty[path[2]][path[3]] = value;
        }
        resources.insert(key.into(), j(&content));
        assert!(
            !qualify_table(Profile::Acc12, &definition, &resources, &table),
            "{key} {path:?}"
        );
    }
    let mut table: Value = serde_json::from_str(&canonical(&table)).unwrap();
    let row = table["rows"][0].clone();
    table["rows"].as_array_mut().unwrap().push(row);
    assert!(!qualify_table(
        Profile::Acc12,
        &definition,
        &base,
        &j(&table)
    ));
    table["rows"].as_array_mut().unwrap().pop();
    table["rows"][0]["ai_authority"]["content_digest"] =
        json!(format!("sha256:{}", "0".repeat(64)));
    assert!(!qualify_table(
        Profile::Acc12,
        &definition,
        &base,
        &j(&table)
    ));
    assert!(schema_validation::validate(&base, TABLE_SCHEMA, &j(&json!({"rows":[]}))).is_err());
}

#[test]
fn independent_failures_precedence_and_diagnostic_order_are_stable() {
    let mut request = request(&fixture(1));
    let mut unsupported = request["request"]["fragments"][1].clone();
    unsupported["request_key"] = json!("other");
    unsupported["semantic_type"] = json!("entity/invariant");
    unsupported["fields"]["id"] = json!("01900000-0000-7000-8000-000000000003");
    request["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .push(unsupported);
    request["request"]["compositions"] = json!([
        {"parent":"parent","child":"child","relation":"composed_of","ordering":0},
        {"parent":"parent","child":"other","relation":"contains","ordering":1},
        {"parent":"parent","child":"missing","relation":"contains","ordering":2}
    ]);
    let result = run(&request);
    let cases = read("contracts/authoring-construction/v1.2/resources/conformance.json");
    let expected = cases["cases"][37]["assertions"][1]["expected"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap())
        .collect::<BTreeSet<_>>();
    assert_eq!(codes(&result), expected);
    assert_eq!(result.status, Status::Rejected);
    for _ in 0..3 {
        request["request"]["fragments"]
            .as_array_mut()
            .unwrap()
            .reverse();
        request["request"]["compositions"]
            .as_array_mut()
            .unwrap()
            .rotate_left(1);
        assert_eq!(result, run(&request));
    }
    request["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .retain(|c| c["relation"] != "composed_of");
    let result = run(&request);
    assert_eq!(result.status, Status::Unavailable);
    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.status == Status::Unresolved));
    assert!(result
        .diagnostics
        .iter()
        .filter(|d| d.code.ends_with("endpoint_unresolved"))
        .all(|d| d.semantic_identity.is_none()));
}

#[test]
fn endpoint_fallbacks_and_unqualified_fragments_never_qualify() {
    for target in [
        "DEC-0001",
        "01900000-0000-7000-8000-000000000002",
        "some/path",
        "0",
    ] {
        let mut request = request(&fixture(1));
        request["request"]["compositions"][0]["child"] = json!(target);
        assert_eq!(run(&request).status, Status::Unresolved, "{target}");
    }
    let mut request = request(&fixture(1));
    request["request"]["fragments"][1]["contract_qualification"]["version"] = json!("1.6");
    assert_eq!(run(&request).status, Status::Unavailable);
    request["request"]["fragments"][1]["contract_qualification"]["version"] = json!("1.7");
    request["request"]["fragments"][1]["fields"]
        .as_object_mut()
        .unwrap()
        .remove("id");
    assert_eq!(run(&request).status, Status::Qualified);
}

#[test]
fn missing_companion_and_dependency_resources_never_use_ambient_authority() {
    for key in [
        TABLE_SCHEMA,
        "authoring-construction/1.1/schema",
        "architecture-interpretation/1.2/contract",
        "authoring-domain/1.1/contract",
        "authoring/1.7/schema/adr-common.schema",
    ] {
        let resources = bundle()
            .1
            .iter()
            .filter(|r| r["canonicalResourceKey"] != key)
            .cloned()
            .collect::<Vec<_>>();
        let result = run_bundle(&bundle().0, &resources, &request(&fixture(1)));
        assert_eq!(result.authority, Check::Unavailable, "{key}");
        assert_eq!(result.endpoint_resolution, Check::Blocked);
    }
    let definition = j(&bundle().0);
    for key in [TABLE_SCHEMA, TABLE] {
        let mut resources = sealed();
        resources.insert(key.into(), j(&json!({"unsupported":true})));
        assert!(!qualify_binding_authority(
            Profile::Acc12,
            &definition,
            &resources
        ));
    }
}

#[test]
fn invalid_request_is_independent_of_unavailable_acc_selection() {
    let mut request = request(&fixture(1));
    request["basis"]["acc"]["version"] = json!("1.1");
    request["request"]["compositions"][0]["ordering"] = json!(-1);
    let result = run(&request);
    assert_eq!(result.status, Status::Rejected);
    assert_eq!(result.request_schema, Check::Rejected);
    assert!(codes(&result).contains("semantic_contract.exact_authority_mismatch"));
    assert!(codes(&result).contains("authoring_construction.request.schema"));
    assert_eq!(result.endpoint_resolution, Check::Blocked);
}

#[test]
fn request_dependency_qualifications_are_exact() {
    for name in ["adc", "authoring", "normalized_model"] {
        let mut request = request(&fixture(1));
        request["basis"][name]["resources"][0]["content_digest"] =
            json!(format!("sha256:{}", "0".repeat(64)));
        let result = run(&request);
        assert_eq!(result.status, Status::Unavailable, "{name}");
        assert!(result.bindings.is_empty());
    }
    let mut request = request(&fixture(1));
    request["basis"]["architecture_interpretation"]["semantic_contract_fingerprint"] =
        json!(format!("scf:v1:sha256:{}", "0".repeat(64)));
    assert_eq!(run(&request).status, Status::Unavailable);
    request["basis"]["architecture_interpretation"]["semantic_contract_fingerprint"] =
        json!(AI_SCF);
    request["basis"]["architecture_interpretation"]["authority_closure"]["resources"]
        .as_array_mut()
        .unwrap()
        .pop();
    assert_eq!(run(&request).status, Status::Unavailable);
}

#[test]
fn endpoint_operation_and_mode_rules_apply_to_both_roles() {
    for role in [0, 1] {
        for (operation, status, code) in [
            ("update", Status::Unavailable, "update_unavailable"),
            ("retire", Status::Rejected, "operation_unsupported"),
            ("reference", Status::Rejected, "reference_not_definition"),
        ] {
            let mut request = request(&fixture(1));
            request["request"]["fragments"][role]["operation"] = json!(operation);
            let result = run(&request);
            assert_eq!(result.status, status);
            assert!(codes(&result)
                .contains(format!("authoring_construction.composition.{code}").as_str()));
            assert_eq!(result.endpoint_resolution, Check::Blocked);
        }
        let mut request = request(&fixture(1));
        request["request"]["fragments"][role]["input_mode"] = json!("compact");
        assert_eq!(run(&request).status, Status::Unavailable);
    }
}

#[test]
fn failed_request_permutations_do_not_change_diagnostics() {
    for number in [6, 7, 8, 10, 19, 20, 41] {
        let mut request = request(&fixture(number));
        let expected = run(&request);
        request["request"]["fragments"]
            .as_array_mut()
            .unwrap()
            .reverse();
        request["request"]["compositions"]
            .as_array_mut()
            .unwrap()
            .reverse();
        assert_eq!(run(&request), expected, "case {number}");
    }
    let mut request = request(&fixture(2));
    request["request"]["compositions"][0]["ordering"] = json!(9007199254740992_u64);
    request["request"]["compositions"][1]["ordering"] = json!(9007199254740993_u64);
    let result = run(&request);
    assert_eq!(result.status, Status::Unavailable);
    assert!(codes(&result).contains("authoring_construction.execution_capability.unavailable"));
}

#[test]
fn internal_qualification_does_not_add_a_protocol_route_or_public_capability() {
    let bytes = super::super::execute_json(
        &serde_json::to_vec(&json!({
            "core_contract_version":"1.5", "operation":"qualify_authoring_construction_1_2",
            "request":{}
        }))
        .unwrap(),
    );
    let response: Value = serde_json::from_slice(&bytes).unwrap();
    assert!(response.to_string().contains("invalid_request"));
    let protocol = read("contracts/semantic-core/v1.5/contract.json");
    assert!(!protocol
        .to_string()
        .contains("qualify_authoring_construction_1_2"));
    assert_eq!(
        read("contracts/authoring-construction/v1.2/contract.json")["semanticContractFingerprint"],
        json!(SCF)
    );
}

// Captured independently from the unmodified 5ab992a tree.

#[test]
fn historical_diagnostic_commitments() {
    for variant in 0..5 {
        let mut input = request(&fixture(2));
        match variant {
            0 => input["request"]["compositions"][0]["relation"] = json!("unknown"),
            1 => input["request"]["compositions"][0]["child"] = json!("absent"),
            2 => input["request"]["fragments"][0]["input_mode"] = json!("compact"),
            3 => {
                input["request"]["fragments"][1]["fields"]["id"] =
                    input["request"]["fragments"][0]["fields"]["id"].clone()
            }
            _ => {
                input["request"]["compositions"][0]["relation"] = json!("unknown");
                input["request"]["compositions"][1]["child"] = json!("absent");
                input["request"]["fragments"][0]["input_mode"] = json!("compact");
            }
        }
        assert_eq!(
            format!(
                "{:x}",
                Sha256::digest(format!("{:?}", run(&input)).as_bytes())
            ),
            [
                "8adb142d54cbc471eb445c49ea5619e2179a08b0cc2abb6800b48fc0fdd16e6a",
                "21f1f0d008dcf86f684164fa59a1c941c8b3cb2adf71bc7f5dbcc57209e5fb68",
                "85f4a25ef03738c121c2269a441f48c8719adc1b461e8b328d775fee1000d7a8",
                "4d4b40116ee7c41c778c13c4f508ff27f779049c3d4f407ccfdb3d29e85c5421",
                "f146ece3446555206c9c7d0c82377199e6c5fa2baa809f873b32bc953af23d44"
            ][variant]
        );
    }
}
