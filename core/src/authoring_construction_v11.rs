//! ACC 1.1 authority qualification and fail-closed execution boundary.
//!
//! This module deliberately qualifies the published authority without
//! claiming that the complete ACC 1.1 construction pipeline is executable.

use std::collections::BTreeMap;

use super::{object, schema_validation, semantic_contract, string, Json};

const OPERATION: &str = "qualify_authoring_construction_1_1";
const ACC_FINGERPRINT: &str =
    "scf:v1:sha256:dcb38e2247396759ed3cbf0ee308ba4c02c087bf47599e72a342cc5efe6a79c5";
const AI12_FINGERPRINT: &str =
    "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a";
const SCHEMA_KEY: &str = "authoring-construction/1.1/schema";
const RULES_KEY: &str = "authoring-construction/1.1/rules";

pub(crate) fn execute(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return invalid_request("protocol 1.4 request payload must be an object");
    };
    if root.get("operation").and_then(Json::as_str) != Some(OPERATION) {
        return invalid_request("operation must be qualify_authoring_construction_1_1");
    }

    let definition = root.get("definition").and_then(Json::as_object);
    let resources = root.get("resources").and_then(Json::as_array);
    let construction_request = root.get("construction_request");

    let mut authority_diagnostics = Vec::new();
    let authority_ok = if let (Some(definition), Some(resources)) = (definition, resources) {
        qualify_authority(definition, resources, &mut authority_diagnostics)
    } else {
        authority_diagnostics.push(object([
            ("code".into(), string("semantic_contract.invalid_request")),
            (
                "message".into(),
                string("definition and resources are required"),
            ),
            ("path".into(), string("authority")),
        ]));
        false
    };

    let mut diagnostics = Vec::new();
    let mut outcome = "Unavailable";
    let mut request_schema_validated = false;
    if authority_ok {
        if let Some(construction_request) = construction_request {
            if let Some(schema) = resources.and_then(|items| resource_content(items, SCHEMA_KEY)) {
                let schema_resources = BTreeMap::from([(SCHEMA_KEY.to_owned(), schema.clone())]);
                request_schema_validated = true;
                match schema_validation::validate(
                    &schema_resources,
                    SCHEMA_KEY,
                    construction_request,
                ) {
                    Ok(()) => {
                        diagnostics.push(acc_diagnostic(
                            "authoring_construction.execution_capability.unavailable",
                            "unavailable",
                            "/construction_request",
                            "complete ACC 1.1 construction qualification",
                            "construction semantics are not implemented",
                            "ACC 1.1 construction cannot complete until every qualification operation is executable.",
                        ));
                    }
                    Err(error) => {
                        outcome = "Rejected";
                        diagnostics.push(acc_diagnostic(
                            "authoring_construction.request.schema",
                            "violation",
                            &format!("/construction_request{}", error.path),
                            "schema-valid ACC 1.1 construction request",
                            &error.message,
                            "Correct the construction request using the exact ACC 1.1 schema.",
                        ));
                    }
                }
            } else {
                authority_ok_unreachable(&mut diagnostics);
            }
        } else {
            outcome = "Rejected";
            diagnostics.push(acc_diagnostic(
                "authoring_construction.request.schema",
                "violation",
                "/construction_request",
                "ACC 1.1 construction request",
                "missing construction_request",
                "Supply a construction request governed by ACC 1.1.",
            ));
        }
    } else {
        diagnostics.push(acc_diagnostic(
            "authoring_construction.authority.unavailable",
            "unavailable",
            "/authority",
            "exact, integrity-qualified ACC 1.1 authority and dependency closure",
            "authority qualification failed",
            "Supply the exact ACC 1.1 authority and complete unmodified resource closure.",
        ));
    }

    let authority_fingerprint = definition
        .and_then(|value| value.get("semanticContractFingerprint"))
        .and_then(Json::as_str)
        .map(string)
        .unwrap_or(Json::Null);
    object([
        ("operation".into(), string(OPERATION)),
        ("contract_family".into(), string("authoring_construction")),
        ("contract_version".into(), string("1.1")),
        (
            "authority".into(),
            object([
                ("available".into(), Json::Bool(authority_ok)),
                ("fingerprint".into(), authority_fingerprint),
            ]),
        ),
        (
            "capabilities".into(),
            capability_report(authority_ok, request_schema_validated),
        ),
        ("success".into(), Json::Bool(false)),
        ("outcome".into(), string(outcome)),
        ("diagnostics".into(), Json::Array(diagnostics)),
        (
            "authority_diagnostics".into(),
            Json::Array(authority_diagnostics),
        ),
    ])
}

fn qualify_authority(
    definition: &BTreeMap<String, Json>,
    resources: &[Json],
    diagnostics: &mut Vec<Json>,
) -> bool {
    let closure_request = object([
        ("definition".into(), Json::Object(definition.clone())),
        ("resources".into(), Json::Array(resources.to_vec())),
    ]);
    let closure = semantic_contract::validate_closure(&closure_request);
    let closure_valid = closure
        .as_object()
        .and_then(|result| result.get("closure_valid"))
        .and_then(Json::as_bool)
        == Some(true);
    if let Some(items) = closure
        .as_object()
        .and_then(|result| result.get("diagnostics"))
        .and_then(Json::as_array)
    {
        diagnostics.extend(items.iter().cloned());
    }

    let exact_acc = definition
        .get("semanticContractFamily")
        .and_then(Json::as_str)
        == Some("authoring-construction")
        && definition
            .get("semanticContractVersion")
            .and_then(Json::as_str)
            == Some("1.1")
        && definition
            .get("semanticContractFingerprint")
            .and_then(Json::as_str)
            == Some(ACC_FINGERPRINT);
    let rules = resource_content(resources, RULES_KEY).and_then(Json::as_object);
    let authority = rules
        .and_then(|value| value.get("authority"))
        .and_then(Json::as_object);
    let ai12 = authority
        .and_then(|value| value.get("architecture_interpretation"))
        .and_then(Json::as_object);
    let exact_bindings = ai12
        .and_then(|value| value.get("family"))
        .and_then(Json::as_str)
        == Some("architecture-interpretation")
        && ai12
            .and_then(|value| value.get("version"))
            .and_then(Json::as_str)
            == Some("1.2")
        && ai12
            .and_then(|value| value.get("fingerprint"))
            .and_then(Json::as_str)
            == Some(AI12_FINGERPRINT)
        && authority
            .and_then(|value| value.get("authoring_domain"))
            .and_then(Json::as_object)
            .and_then(|value| value.get("contract_id"))
            .and_then(Json::as_str)
            == Some("adr-kit.authoring-domain")
        && authority
            .and_then(|value| value.get("authoring_domain"))
            .and_then(Json::as_object)
            .and_then(|value| value.get("version"))
            .and_then(Json::as_str)
            == Some("1.1")
        && authority
            .and_then(|value| value.get("authoring"))
            .and_then(Json::as_object)
            .and_then(|value| value.get("schema_version"))
            .and_then(Json::as_str)
            == Some("1.7")
        && authority
            .and_then(|value| value.get("normalized_model"))
            .and_then(Json::as_object)
            .and_then(|value| value.get("family"))
            .and_then(Json::as_str)
            == Some("normalized-model")
        && authority
            .and_then(|value| value.get("normalized_model"))
            .and_then(Json::as_object)
            .and_then(|value| value.get("version"))
            .and_then(Json::as_str)
            == Some("2.4")
        && authority
            .and_then(|value| value.get("custom_entity"))
            .and_then(Json::as_object)
            .and_then(|value| value.get("contract_id"))
            .and_then(Json::as_str)
            == Some("adr-kit.custom-entity")
        && authority
            .and_then(|value| value.get("custom_entity"))
            .and_then(Json::as_object)
            .and_then(|value| value.get("version"))
            .and_then(Json::as_str)
            == Some("1.0");

    if !exact_acc || !exact_bindings {
        diagnostics.push(object([
            ("code".into(), string("semantic_contract.exact_authority_mismatch")),
            (
                "message".into(),
                string("authority family, version, fingerprint, or exact dependency binding does not match ACC 1.1"),
            ),
            ("path".into(), string("definition")),
        ]));
    }
    diagnostics.sort_by(|left, right| stable_json(left).cmp(&stable_json(right)));
    closure_valid && exact_acc && exact_bindings
}

fn resource_content<'a>(resources: &'a [Json], key: &str) -> Option<&'a Json> {
    resources.iter().find_map(|resource| {
        let value = resource.as_object()?;
        (value.get("canonicalResourceKey").and_then(Json::as_str) == Some(key))
            .then(|| value.get("content"))
            .flatten()
    })
}

fn capability_report(authority_available: bool, schema_validated: bool) -> Json {
    object([
        (
            "exact_authority_qualification".into(),
            Json::Bool(authority_available),
        ),
        (
            "request_schema_validation".into(),
            Json::Bool(schema_validated),
        ),
        ("authoring_validation".into(), Json::Bool(false)),
        ("identity_establishment".into(), Json::Bool(false)),
        (
            "reference_and_composition_resolution".into(),
            Json::Bool(false),
        ),
        ("candidate_source_basis_sealing".into(), Json::Bool(false)),
        ("complete_nm24_interpretation".into(), Json::Bool(false)),
        ("expected_ledger_derivation".into(), Json::Bool(false)),
        ("observed_ledger_derivation".into(), Json::Bool(false)),
        ("whole_ledger_comparison".into(), Json::Bool(false)),
        ("complete_acc11_qualification".into(), Json::Bool(false)),
        ("construct_authoring_set".into(), Json::Bool(false)),
    ])
}

fn acc_diagnostic(
    code: &str,
    status: &str,
    location: &str,
    expected: &str,
    observed: &str,
    remediation: &str,
) -> Json {
    object([
        ("code".into(), string(code)),
        ("severity".into(), string("error")),
        ("status".into(), string(status)),
        ("request_key".into(), Json::Null),
        ("location".into(), string(location)),
        ("semantic_type".into(), Json::Null),
        (
            "rule".into(),
            string("ACC 1.1 exact authority and complete execution capability"),
        ),
        ("expected".into(), string(expected)),
        ("observed".into(), string(observed)),
        ("remediation".into(), string(remediation)),
    ])
}

fn stable_json(value: &Json) -> String {
    serde_json::to_string(value).unwrap_or_default()
}

fn invalid_request(message: &str) -> Json {
    object([
        ("operation".into(), string(OPERATION)),
        ("contract_family".into(), string("authoring_construction")),
        ("contract_version".into(), string("1.1")),
        (
            "authority".into(),
            object([
                ("available".into(), Json::Bool(false)),
                ("fingerprint".into(), Json::Null),
            ]),
        ),
        ("capabilities".into(), capability_report(false, false)),
        ("success".into(), Json::Bool(false)),
        ("outcome".into(), string("Rejected")),
        (
            "diagnostics".into(),
            Json::Array(vec![acc_diagnostic(
                "authoring_construction.request.schema",
                "violation",
                "/request",
                "ACC 1.1 authority qualification request",
                message,
                "Supply the exact version-qualified ACC 1.1 qualification request.",
            )]),
        ),
        ("authority_diagnostics".into(), Json::Array(Vec::new())),
    ])
}

fn authority_ok_unreachable(diagnostics: &mut Vec<Json>) {
    diagnostics.push(acc_diagnostic(
        "authoring_construction.authority.unavailable",
        "unavailable",
        "/authority/resources",
        "the schema resource in the verified ACC 1.1 closure",
        "schema resource is unavailable",
        "Supply the complete exact ACC 1.1 resource closure.",
    ));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unavailable_authority_never_claims_constructed_or_unresolved() {
        let request = object([
            ("operation".into(), string(OPERATION)),
            ("definition".into(), object([])),
            ("resources".into(), Json::Array(Vec::new())),
            ("construction_request".into(), object([])),
        ]);
        let result = execute(&request);
        let result = result
            .as_object()
            .expect("qualification result is an object");
        assert_eq!(
            result.get("outcome").and_then(Json::as_str),
            Some("Unavailable")
        );
        assert_eq!(result.get("success").and_then(Json::as_bool), Some(false));
        let capabilities = result
            .get("capabilities")
            .and_then(Json::as_object)
            .unwrap();
        assert_eq!(
            capabilities
                .get("construct_authoring_set")
                .and_then(Json::as_bool),
            Some(false)
        );
        assert_eq!(
            capabilities
                .get("complete_acc11_qualification")
                .and_then(Json::as_bool),
            Some(false)
        );
    }
}
