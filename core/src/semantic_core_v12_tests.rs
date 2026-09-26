use std::collections::BTreeMap;

use super::{execute_json, semantic_contract, Json};

const TARGET_KEY: &str = "authoring-construction/1.0/conformance";

fn document(raw: &str) -> Json {
    serde_json::from_str(raw).expect("embedded ACC resource is valid JSON")
}

fn resource(key: &str, content: Json) -> Json {
    Json::Object(BTreeMap::from([
        ("canonicalResourceKey".into(), Json::String(key.into())),
        ("content".into(), content),
    ]))
}

fn bound_cases() -> Vec<Json> {
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
        resource(TARGET_KEY, conformance),
        resource("authoring-construction/1.0/rules", rules),
    ];
    let bound =
        semantic_contract::bind_verified_conformance_resource(&definition, &resources, TARGET_KEY)
            .expect("the accepted ACC corpus binds through ADR-L-0031 authority");
    bound
        .get("cases")
        .and_then(Json::as_array)
        .cloned()
        .expect("bound ACC corpus has cases")
}

fn case_input(id: &str) -> Json {
    bound_cases()
        .into_iter()
        .find(|case| case.get("id").and_then(Json::as_str) == Some(id))
        .and_then(|case| case.get("input").cloned())
        .expect("requested frozen ACC case exists")
}

fn execute(request: Json) -> Json {
    serde_json::from_slice(&execute_json(&serde_json::to_vec(&request).unwrap())).unwrap()
}

fn envelope(operation: &str, payload: Json) -> Json {
    Json::Object(BTreeMap::from([
        ("core_contract_version".into(), Json::String("1.2".into())),
        ("operation".into(), Json::String(operation.into())),
        ("request".into(), payload),
    ]))
}

fn nested_result(result: &Json) -> &BTreeMap<String, Json> {
    result
        .get("result")
        .and_then(Json::as_object)
        .expect("protocol result envelope contains an ACC result")
}

#[test]
fn v12_dispatches_validation_to_the_canonical_acc_renderer() {
    let request = case_input("C27");
    let result = execute(envelope("validate_authoring", request));
    assert_eq!(
        result.get("core_contract_version").and_then(Json::as_str),
        Some("1.2")
    );
    assert_eq!(
        result.get("operation").and_then(Json::as_str),
        Some("validate_authoring")
    );
    assert_eq!(
        nested_result(&result)
            .get("operation")
            .and_then(Json::as_str),
        Some("validate_authoring")
    );
    assert_eq!(
        nested_result(&result)
            .get("validation_status")
            .and_then(Json::as_str),
        Some("invalid")
    );
}

#[test]
fn v12_dispatches_construction_and_preserves_c32_c33_outcomes() {
    let constructed = execute(envelope("construct_authoring_set", case_input("C01")));
    assert_eq!(
        nested_result(&constructed)
            .get("outcome")
            .and_then(Json::as_str),
        Some("Constructed")
    );

    let rejected = execute(envelope("construct_authoring_set", case_input("C32")));
    assert_eq!(
        nested_result(&rejected)
            .get("outcome")
            .and_then(Json::as_str),
        Some("Rejected")
    );
    assert_eq!(
        nested_result(&rejected)
            .get("round_trip")
            .and_then(|value| value.get("comparison"))
            .and_then(Json::as_str),
        Some("semantic_mismatch")
    );

    let unavailable = execute(envelope("construct_authoring_set", case_input("C33")));
    assert_eq!(
        nested_result(&unavailable)
            .get("outcome")
            .and_then(Json::as_str),
        Some("Unavailable")
    );
}

#[test]
fn v12_rejects_malformed_acc_and_closed_protocol_envelopes() {
    let mut malformed = case_input("C27");
    malformed
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .expect("C27 request")
        .remove("fragments");
    let result = execute(envelope("validate_authoring", malformed));
    assert_eq!(
        nested_result(&result)
            .get("validation_status")
            .and_then(Json::as_str),
        Some("invalid")
    );

    let missing_payload = execute(Json::Object(BTreeMap::from([
        ("core_contract_version".into(), Json::String("1.2".into())),
        (
            "operation".into(),
            Json::String("validate_authoring".into()),
        ),
    ])));
    assert_eq!(
        missing_payload
            .get("core_contract_version")
            .and_then(Json::as_str),
        Some("1.2")
    );
    assert_eq!(
        missing_payload
            .get("result")
            .and_then(|value| value.get("diagnostics"))
            .and_then(Json::as_array)
            .map(Vec::len),
        Some(1)
    );

    let old_version = execute(Json::Object(BTreeMap::from([
        ("core_contract_version".into(), Json::String("1.1".into())),
        (
            "operation".into(),
            Json::String("validate_authoring".into()),
        ),
    ])));
    assert_eq!(
        old_version
            .get("core_contract_version")
            .and_then(Json::as_str),
        Some("1.1")
    );
    assert_eq!(old_version.get("success"), Some(&Json::Bool(false)));
}
