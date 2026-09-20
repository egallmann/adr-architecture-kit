use std::collections::BTreeMap;

use super::{authoring_construction, semantic_contract, Json};

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

fn case(id: &str) -> Json {
    bound_cases()
        .into_iter()
        .find(|case| case.get("id").and_then(Json::as_str) == Some(id))
        .expect("requested frozen ACC case exists")
}

fn diagnostic_codes(report: &authoring_construction::ValidationReport) -> Vec<String> {
    report
        .diagnostics
        .iter()
        .filter_map(|diagnostic| {
            diagnostic
                .get("code")
                .and_then(Json::as_str)
                .map(ToOwned::to_owned)
        })
        .collect()
}

#[test]
fn frozen_acc_vectors_use_one_shared_validation_authority() {
    let cases = [
        "C11", "C12", "C13", "C16", "C17", "C19", "C20", "C23", "C24", "C25", "C26", "C27", "C29",
        "C31", "C34", "C40", "C41", "C42",
    ];
    for id in cases {
        let frozen_case = case(id);
        let input = frozen_case.get("input").cloned().expect("case has input");
        let report = authoring_construction::validate_authoring_request(&input);
        assert!(
            !report.diagnostics.is_empty(),
            "{id} must remain non-success validation material"
        );
        let expected = frozen_case
            .get("expected")
            .and_then(Json::as_object)
            .and_then(|value| value.get("result"))
            .and_then(Json::as_object)
            .expect("case has expected result");
        let expected_status = expected
            .get("validation_status")
            .and_then(Json::as_str)
            .or_else(|| {
                expected
                    .get("outcome")
                    .and_then(Json::as_str)
                    .map(|outcome| match outcome {
                        "Rejected" => "invalid",
                        "Unavailable" => "unavailable",
                        "Unresolved" => "unresolved",
                        _ => "valid",
                    })
            })
            .expect("expected non-success status");
        assert_eq!(
            report.status.as_str(),
            expected_status,
            "{id} preserves bounded ACC status"
        );
        let expected_codes = expected
            .get("diagnostics")
            .and_then(Json::as_array)
            .expect("expected result has diagnostics")
            .iter()
            .filter_map(|diagnostic| {
                diagnostic
                    .get("code")
                    .and_then(Json::as_str)
                    .map(ToOwned::to_owned)
            })
            .collect::<Vec<_>>();
        let actual_codes = diagnostic_codes(&report);
        assert_eq!(
            actual_codes, expected_codes,
            "{id} preserves frozen diagnostic meaning"
        );
        assert_eq!(
            report.diagnostics.clone(),
            expected
                .get("diagnostics")
                .and_then(Json::as_array)
                .cloned()
                .expect("expected result has diagnostic objects"),
            "{id} preserves exact frozen diagnostic fields"
        );
        let rendered = authoring_construction::render_validation_result(&input, &report);
        assert_eq!(
            rendered.get("operation").and_then(Json::as_str),
            input.get("operation").and_then(Json::as_str),
            "{id} preserves the ACC operation in its semantic result"
        );
    }
}

#[test]
fn acc_diagnostics_are_aggregated_and_deterministically_ordered() {
    let report = authoring_construction::validate_authoring_request(&case_input("C27"));
    assert_eq!(
        diagnostic_codes(&report),
        vec![
            "authoring_construction.field.unknown",
            "authoring_construction.field.unknown"
        ],
        "diagnostics: {:?}",
        report.diagnostics
    );
    let keys = report
        .diagnostics
        .iter()
        .map(|diagnostic| {
            diagnostic
                .get("request_key")
                .and_then(Json::as_str)
                .expect("C27 diagnostics have request keys")
        })
        .collect::<Vec<_>>();
    assert_eq!(keys, vec!["a", "z"]);
}

#[test]
fn acc_blocked_checks_remain_visible_after_an_unresolved_prerequisite() {
    let report = authoring_construction::validate_authoring_request(&case_input("C25"));
    assert_eq!(
        report.status,
        authoring_construction::ValidationStatus::Unresolved,
        "{:?}",
        report.diagnostics
    );
    assert_eq!(
        diagnostic_codes(&report),
        vec![
            "authoring_construction.reference.endpoint_unresolved",
            "authoring_construction.relationship.type_check_blocked",
            "authoring_construction.relationship.cardinality_check_blocked",
        ]
    );
}

#[test]
fn independent_mutations_use_the_same_validator_without_case_dispatch() {
    let mut request = case_input("C13");
    let fragment = request
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(|request| request.as_object_mut())
        .and_then(|request| request.get_mut("fragments"))
        .and_then(Json::as_array_mut)
        .and_then(|fragments| fragments.first_mut())
        .and_then(Json::as_object_mut)
        .expect("fixture fragment is mutable");
    fragment.insert("operation".into(), Json::String("update".into()));
    let fields = fragment
        .get_mut("fields")
        .and_then(Json::as_object_mut)
        .expect("fixture fields are mutable");
    fields.remove("id");
    fields.insert("unknown".into(), Json::Null);
    let report = authoring_construction::validate_authoring_request(&request);
    let codes = diagnostic_codes(&report);
    assert!(codes.contains(&"authoring_construction.identity.update_requires_existing".into()));
    assert!(codes.contains(&"authoring_construction.field.unknown".into()));
}

#[test]
fn exact_basis_qualification_is_required_before_semantic_checks() {
    let mut request = case_input("C13");
    let resource = request
        .as_object_mut()
        .and_then(|root| root.get_mut("basis"))
        .and_then(Json::as_object_mut)
        .and_then(|basis| basis.get_mut("adc"))
        .and_then(Json::as_object_mut)
        .and_then(|adc| adc.get_mut("resources"))
        .and_then(Json::as_array_mut)
        .and_then(|resources| resources.first_mut())
        .and_then(Json::as_object_mut)
        .and_then(|resource| resource.get_mut("content_digest"))
        .expect("ACC basis resource digest is mutable");
    *resource = Json::String(
        "sha256:0000000000000000000000000000000000000000000000000000000000000000".into(),
    );
    let report = authoring_construction::validate_authoring_request(&request);
    assert!(diagnostic_codes(&report)
        .contains(&"authoring_construction.basis.exact_qualification".into()));
}

#[test]
fn custom_relationships_require_the_exact_selected_cec_definition() {
    let mut request = case_input("C31");
    let qualification = request
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .and_then(|request| request.get_mut("relationships"))
        .and_then(Json::as_array_mut)
        .and_then(|relationships| relationships.first_mut())
        .and_then(Json::as_object_mut)
        .and_then(|relationship| relationship.get_mut("qualification"))
        .and_then(Json::as_object_mut)
        .expect("custom relationship qualification is mutable");
    qualification.insert(
        "semantic_type".into(),
        Json::String("payments:other".into()),
    );
    let report = authoring_construction::validate_authoring_request(&request);
    assert!(diagnostic_codes(&report)
        .contains(&"authoring_construction.custom.qualification_mismatch".into()));
}
