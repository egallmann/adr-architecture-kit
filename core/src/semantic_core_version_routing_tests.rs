use std::collections::BTreeMap;

use super::{execute_json, Json};

fn execute(version: &str, operation: &str) -> Json {
    let request = Json::Object(BTreeMap::from([
        ("core_contract_version".into(), Json::String(version.into())),
        ("operation".into(), Json::String(operation.into())),
    ]));
    serde_json::from_slice(&execute_json(&serde_json::to_vec(&request).unwrap())).unwrap()
}

fn valid_v10_contract_request(version: &str) -> Json {
    Json::Object(BTreeMap::from([
        ("core_contract_version".into(), Json::String(version.into())),
        ("operation".into(), Json::String("validate_contract".into())),
        ("profile".into(), Json::String("greenfield".into())),
        (
            "entity_registry".into(),
            Json::Object(BTreeMap::from([("entities".into(), Json::Array(Vec::new()))])),
        ),
    ]))
}

fn execute_request(request: Json) -> Json {
    serde_json::from_slice(&execute_json(&serde_json::to_vec(&request).unwrap())).unwrap()
}

fn assert_generic_rejection(result: &Json) {
    assert_eq!(
        result
            .as_object()
            .and_then(|value| value.get("core_contract_version"))
            .and_then(Json::as_str),
        Some("1.0")
    );
    assert_eq!(
        result
            .as_object()
            .and_then(|value| value.get("operation"))
            .and_then(Json::as_str),
        Some("validate_contract")
    );
    assert_eq!(
        result.as_object().and_then(|value| value.get("success")),
        Some(&Json::Bool(false))
    );
    assert_eq!(
        result
            .as_object()
            .and_then(|value| value.get("outcome"))
            .and_then(Json::as_str),
        Some("invalid_request")
    );
}

#[test]
fn v12_does_not_fall_through_to_the_v10_dispatcher() {
    let request = valid_v10_contract_request("1.2");
    let result = execute_request(request);
    assert_generic_rejection(&result);
}

#[test]
fn v12_does_not_execute_v11_operations() {
    for operation in ["resolve_semantic_contract_set", "materialize_architecture"] {
        let result = execute("1.2", operation);
        assert_generic_rejection(&result);
    }
}

#[test]
fn v12_authoring_operations_remain_non_executable() {
    for operation in ["validate_authoring", "construct_authoring_set"] {
        let result = execute("1.2", operation);
        assert_generic_rejection(&result);
    }
}

#[test]
fn v12_unknown_operations_are_rejected_at_the_version_boundary() {
    let result = execute("1.2", "unknown_future_operation");
    assert_generic_rejection(&result);
}

#[test]
fn unsupported_versions_cannot_execute_v10_operations() {
    let result = execute_request(valid_v10_contract_request("9.9"));
    assert_generic_rejection(&result);
}

#[test]
fn unsupported_versions_cannot_execute_v11_operations() {
    for operation in ["resolve_semantic_contract_set", "materialize_architecture"] {
        let result = execute("9.9", operation);
        assert_generic_rejection(&result);
    }
}
