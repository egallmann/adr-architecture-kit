use std::collections::{BTreeMap, BTreeSet};

use super::{semantic_contract, Json};

const TARGET_KEY: &str = "authoring-construction/1.0/conformance";
const VERIFIED_SCF: &str = "scf:v1:sha256:e81fde7ff0a8bc440e92fbe3e79c6a8743b21bd7186f5137fcadf1b68b68f1c0";
const MARKER: &str = "$enclosing_scf";

fn document(raw: &str) -> Json {
    serde_json::from_str(raw).expect("embedded semantic-contract resource is valid JSON")
}

fn acc_fixture() -> (BTreeMap<String, Json>, Vec<Json>, Json) {
    let definition = document(include_str!(
        "../../contracts/authoring-construction/v1.0/contract.json"
    ));
    let rules = document(include_str!(
        "../../contracts/authoring-construction/v1.0/resources/rules.json"
    ));
    let conformance = document(include_str!(
        "../../contracts/authoring-construction/v1.0/resources/conformance.json"
    ));
    let definition = definition
        .as_object()
        .cloned()
        .expect("ACC definition is an object");
    let resources = vec![
        resource(TARGET_KEY, conformance.clone()),
        resource("authoring-construction/1.0/rules", rules),
    ];
    (definition, resources, conformance)
}

fn resource(key: &str, content: Json) -> Json {
    Json::Object(BTreeMap::from([
        ("canonicalResourceKey".into(), Json::String(key.into())),
        ("content".into(), content),
    ]))
}

fn conformance_mut(resources: &mut [Json]) -> &mut BTreeMap<String, Json> {
    let resource = resources
        .iter_mut()
        .find(|resource| {
            resource
                .as_object()
                .and_then(|value| value.get("canonicalResourceKey"))
                .and_then(Json::as_str)
                == Some(TARGET_KEY)
        })
        .expect("ACC conformance resource is supplied");
    let resource = match resource {
        Json::Object(value) => value,
        _ => panic!("supplied resource is an object"),
    };
    match resource.get_mut("content").expect("resource has content") {
        Json::Object(value) => value,
        _ => panic!("ACC conformance resource is an object"),
    }
}

fn scalar_values(value: &Json, output: &mut Vec<String>) {
    match value {
        Json::Object(values) => values.values().for_each(|child| scalar_values(child, output)),
        Json::Array(values) => values.iter().for_each(|child| scalar_values(child, output)),
        Json::String(value) => output.push(value.clone()),
        Json::Null | Json::Bool(_) | Json::Number(_) => {}
    }
}

fn canonical_digest(value: &Json) -> String {
    let result = semantic_contract::canonicalize(&Json::Object(BTreeMap::from([(
        "value".into(),
        value.clone(),
    )])));
    result
        .get("fingerprint")
        .and_then(Json::as_str)
        .expect("canonicalization returns a digest")
        .strip_prefix("sha256:")
        .map(|hex| format!("sha256:{hex}"))
        .expect("canonicalization digest uses sha256")
}

fn reseal_fixture(definition: &mut BTreeMap<String, Json>, resources: &[Json]) {
    let mut digests = BTreeMap::new();
    for resource in resources {
        let resource = resource.as_object().expect("resource is an object");
        let key = resource
            .get("canonicalResourceKey")
            .and_then(Json::as_str)
            .expect("resource has a canonical key");
        let content = resource.get("content").expect("resource has content");
        digests.insert(key.to_owned(), canonical_digest(content));
    }
    let manifest = definition
        .get_mut("resourceManifest")
        .and_then(|value| match value {
            Json::Array(value) => Some(value),
            _ => None,
        })
        .expect("definition has a manifest");
    for raw_entry in manifest {
        let entry = match raw_entry {
            Json::Object(value) => value,
            _ => panic!("manifest entry is an object"),
        };
        let key = entry
            .get("canonicalResourceKey")
            .and_then(Json::as_str)
            .expect("manifest entry has a key");
        entry.insert(
            "contentDigest".into(),
            Json::String(digests.get(key).expect("manifest resource is supplied").clone()),
        );
        if let Some(Json::Array(dependencies)) = entry.get_mut("dependencies") {
            for raw_dependency in dependencies {
                let dependency = match raw_dependency {
                    Json::Object(value) => value,
                    _ => panic!("dependency is an object"),
                };
                let dependency_key = dependency
                    .get("canonicalResourceKey")
                    .and_then(Json::as_str)
                    .expect("dependency has a key");
                dependency.insert(
                    "contentDigest".into(),
                    Json::String(
                        digests
                            .get(dependency_key)
                            .expect("dependency resource is supplied")
                            .clone(),
                    ),
                );
            }
        }
    }
    definition.remove("semanticContractFingerprint");
    let fingerprint = semantic_contract::fingerprint(&Json::Object(BTreeMap::from([
        (
            "definition".into(),
            Json::Object(definition.clone()),
        ),
        ("mode".into(), Json::String("calculate".into())),
    ])));
    definition.insert(
        "semanticContractFingerprint".into(),
        Json::String(
            fingerprint
                .get("semantic_contract_fingerprint")
                .and_then(Json::as_str)
                .expect("resealed definition has an SCF")
                .to_owned(),
        ),
    );
}

fn bind(
    definition: &BTreeMap<String, Json>,
    resources: &[Json],
) -> Result<Json, String> {
    semantic_contract::bind_verified_conformance_resource(definition, resources, TARGET_KEY)
}

#[test]
fn acc_known_answer_binding_uses_the_verified_enclosing_scf() {
    let (definition, resources, original) = acc_fixture();
    let original_bytes = serde_json::to_vec(&original).expect("original corpus serializes");
    let bound = bind(&definition, &resources).expect("ACC conformance binding succeeds");
    let cases = bound
        .get("cases")
        .and_then(Json::as_array)
        .expect("bound corpus has cases");
    assert_eq!(cases.len(), 42);
    let case_ids = cases
        .iter()
        .map(|case| {
            case.get("id")
                .and_then(Json::as_str)
                .expect("ACC case has an id")
                .to_owned()
        })
        .collect::<BTreeSet<_>>();
    let expected_case_ids = (1..=42)
        .map(|number| format!("C{number:02}"))
        .collect::<BTreeSet<_>>();
    assert_eq!(case_ids, expected_case_ids);
    assert!(bound.get("self_binding").is_none());

    for case in cases {
        assert_eq!(
            case.get_path(&["input", "basis", "acc", "semantic_contract_fingerprint"])
                .and_then(Json::as_str),
            Some(VERIFIED_SCF)
        );
        assert_eq!(
            case.get_path(&[
                "expected",
                "result",
                "basis_qualification",
                "acc",
                "semantic_contract_fingerprint",
            ])
            .and_then(Json::as_str),
            Some(VERIFIED_SCF)
        );
    }

    let mut bound_scalars = Vec::new();
    scalar_values(&bound, &mut bound_scalars);
    assert!(!bound_scalars.iter().any(|value| value.starts_with('$')));
    assert_eq!(
        serde_json::to_vec(&original).expect("original corpus serializes"),
        original_bytes
    );
    let mut original_scalars = Vec::new();
    scalar_values(&original, &mut original_scalars);
    assert!(original_scalars.iter().any(|value| value == MARKER));
    assert!(!original_scalars.iter().any(|value| value == VERIFIED_SCF));
    assert_ne!(bound, original);
}

#[test]
fn binding_rejects_an_incorrect_declared_enclosing_scf() {
    let (mut definition, resources, _) = acc_fixture();
    definition.insert(
        "semanticContractFingerprint".into(),
        Json::String(format!("scf:v1:sha256:{}", "0".repeat(64))),
    );
    let error = bind(&definition, &resources).expect_err("incorrect SCF must fail closed");
    assert!(error.contains("fingerprint"));
}

#[test]
fn binding_rejects_a_resource_digest_mismatch() {
    let (definition, mut resources, _) = acc_fixture();
    conformance_mut(&mut resources).insert("tampered".into(), Json::Bool(true));
    let error = bind(&definition, &resources).expect_err("digest mismatch must fail closed");
    assert!(error.contains("resource_digest_mismatch"));
}

#[test]
fn binding_rejects_an_incomplete_resource_closure() {
    let (definition, mut resources, _) = acc_fixture();
    resources.pop();
    let error = bind(&definition, &resources).expect_err("incomplete closure must fail closed");
    assert!(error.contains("missing_resource_content"));
}

#[test]
fn binding_rejects_a_target_absent_from_the_manifest() {
    let (definition, resources, _) = acc_fixture();
    let error = semantic_contract::bind_verified_conformance_resource(
        &definition,
        &resources,
        "authoring-construction/1.0/missing",
    )
    .expect_err("missing target must fail closed");
    assert!(error.contains("absent from the enclosing manifest"));
}

#[test]
fn binding_rejects_a_target_that_is_not_frozen_normative_conformance() {
    let (definition, resources, _) = acc_fixture();
    let error = semantic_contract::bind_verified_conformance_resource(
        &definition,
        &resources,
        "authoring-construction/1.0/rules",
    )
    .expect_err("non-frozen target must fail closed");
    assert!(error.contains("not a frozen normative conformance resource"));
}

#[test]
fn binding_rejects_malformed_self_binding_declarations() {
    let (mut definition, mut resources, _) = acc_fixture();
    let binding = conformance_mut(&mut resources)
        .get_mut("self_binding")
        .and_then(|value| match value {
            Json::Object(value) => Some(value),
            _ => None,
        })
        .expect("self_binding is an object");
    binding.remove("source");
    reseal_fixture(&mut definition, &resources);
    let error = bind(&definition, &resources).expect_err("malformed declaration must fail closed");
    assert!(error.contains("self_binding.source"));
}

#[test]
fn binding_rejects_wrong_marker_and_binding_source_identifiers() {
    let (mut definition, mut resources, _) = acc_fixture();
    let binding = conformance_mut(&mut resources)
        .get_mut("self_binding")
        .and_then(|value| match value {
            Json::Object(value) => Some(value),
            _ => None,
        })
        .expect("self_binding is an object");
    binding.insert("marker".into(), Json::String("$ambient_scf".into()));
    reseal_fixture(&mut definition, &resources);
    let error = bind(&definition, &resources).expect_err("wrong marker must fail closed");
    assert!(error.contains("self_binding.marker"));

    let (mut definition, mut resources, _) = acc_fixture();
    let binding = conformance_mut(&mut resources)
        .get_mut("self_binding")
        .and_then(|value| match value {
            Json::Object(value) => Some(value),
            _ => None,
        })
        .expect("self_binding is an object");
    binding.insert("source".into(), Json::String("ambient_source".into()));
    reseal_fixture(&mut definition, &resources);
    let error = bind(&definition, &resources).expect_err("wrong source must fail closed");
    assert!(error.contains("self_binding.source"));
}

#[test]
fn binding_rejects_undeclared_and_unknown_markers() {
    let (mut definition, mut resources, _) = acc_fixture();
    conformance_mut(&mut resources).insert("undeclared".into(), Json::String(MARKER.into()));
    reseal_fixture(&mut definition, &resources);
    let error = bind(&definition, &resources).expect_err("undeclared marker must fail closed");
    assert!(error.contains("undeclared path"));

    let (mut definition, mut resources, _) = acc_fixture();
    conformance_mut(&mut resources)
        .insert("unknown".into(), Json::String("$ambient_scf".into()));
    reseal_fixture(&mut definition, &resources);
    let error = bind(&definition, &resources).expect_err("unknown marker must fail closed");
    assert!(error.contains("unknown self-binding marker"));
}

#[test]
fn binding_rejects_invalid_and_ambiguous_json_pointer_patterns() {
    let (mut definition, mut resources, _) = acc_fixture();
    let binding = conformance_mut(&mut resources)
        .get_mut("self_binding")
        .and_then(|value| match value {
            Json::Object(value) => Some(value),
            _ => None,
        })
        .expect("self_binding is an object");
    binding.insert(
        "allowed_json_pointer_patterns".into(),
        Json::Array(vec![Json::String("/cases/*/input/~2".into())]),
    );
    reseal_fixture(&mut definition, &resources);
    let error = bind(&definition, &resources).expect_err("invalid pointer must fail closed");
    assert!(error.contains("invalid JSON Pointer escape"));

    let (mut definition, mut resources, _) = acc_fixture();
    let binding = conformance_mut(&mut resources)
        .get_mut("self_binding")
        .and_then(|value| match value {
            Json::Object(value) => Some(value),
            _ => None,
        })
        .expect("self_binding is an object");
    let patterns = binding
        .get_mut("allowed_json_pointer_patterns")
        .and_then(|value| match value {
            Json::Array(value) => Some(value),
            _ => None,
        })
        .expect("binding patterns are an array");
    patterns.push(Json::String(
        "/cases/0/input/basis/acc/semantic_contract_fingerprint".into(),
    ));
    reseal_fixture(&mut definition, &resources);
    let error = bind(&definition, &resources).expect_err("overlap must fail closed");
    assert!(error.contains("overlaps another declaration"));
}

#[test]
fn residual_binding_markers_are_detected_fail_closed() {
    let residual = Json::Object(BTreeMap::from([(
        "value".into(),
        Json::String(MARKER.into()),
    )]));
    assert!(semantic_contract::projection_has_marker(&residual).is_some());
}
