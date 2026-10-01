use std::collections::BTreeMap;

use sha2::{Digest, Sha256};

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

#[test]
fn c32_round_trip_vector_uses_a_real_semantic_field_loss() {
    let frozen = case("C32");
    let fragment = frozen
        .get("input")
        .and_then(|input| input.get("request"))
        .and_then(|request| request.get("fragments"))
        .and_then(Json::as_array)
        .and_then(|fragments| fragments.first())
        .and_then(Json::as_object)
        .expect("C32 fragment");
    let fields = fragment.get("fields").cloned().expect("C32 fields");
    assert_eq!(fragment.get("semantic_type").and_then(Json::as_str), Some("entity/gap"));
    assert!(fields.get("context").is_some(), "C32 must carry semantic context");

    let basis = Json::Object(BTreeMap::from([
        ("kind".into(), Json::String("authoring_fragment".into())),
        (
            "schema".into(),
            Json::String("authoring/1.7/schema/adr-common.schema#/definitions/gap".into()),
        ),
    ]));
    let context = super::architecture_interpretation::InterpretationSourceContext {
        canonical_source_ref: "candidate/C32/gap".into(),
        source_pointer: "/".into(),
    };
    let interpreted = super::architecture_interpretation::interpret(&fields, &basis, &context)
        .expect("C32 gap interpretation succeeds");
    let interpreted_fields = interpreted
        .fields
        .as_object()
        .expect("interpreted fields are an object");
    assert_eq!(interpreted_fields.get("question"), fields.get("question"));
    assert_eq!(interpreted_fields.get("blocking"), fields.get("blocking"));
    assert!(
        !interpreted_fields.contains_key("context"),
        "C32 must expose the production mapping loss rather than a fixture mutation"
    );
}

#[test]
fn c33_missing_interpretation_authority_is_unavailable_and_metadata_invariant() {
    let input = case_input("C33");
    let baseline = authoring_construction::validate_authoring_request(&input);
    assert_eq!(baseline.status, authoring_construction::ValidationStatus::Unavailable);
    assert_eq!(
        diagnostic_codes(&baseline),
        vec!["authoring_construction.interpretation.unavailable"]
    );

    let mut mutated = input;
    mutated
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .expect("request")
        .insert("request_id".into(), Json::String("renamed-request".into()));
    mutated
        .as_object_mut()
        .and_then(|root| root.get_mut("basis"))
        .and_then(Json::as_object_mut)
        .and_then(|basis| basis.get_mut("provenance"))
        .and_then(Json::as_object_mut)
        .expect("provenance")
        .insert("source_ref".into(), Json::String("conformance/renamed".into()));
    let changed = authoring_construction::validate_authoring_request(&mutated);
    assert_eq!(changed.status, baseline.status);
    assert_eq!(changed.diagnostics, baseline.diagnostics);
}

#[test]
fn available_interpretation_authority_does_not_follow_fixture_metadata() {
    let mut input = case_input("C02");
    input
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .expect("request")
        .insert("request_id".into(), Json::String("ACC-C33".into()));
    input
        .as_object_mut()
        .and_then(|root| root.get_mut("basis"))
        .and_then(Json::as_object_mut)
        .and_then(|basis| basis.get_mut("provenance"))
        .and_then(Json::as_object_mut)
        .expect("provenance")
        .insert("source_ref".into(), Json::String("conformance/C33".into()));
    let report = authoring_construction::validate_authoring_request(&input);
    assert_eq!(report.status, authoring_construction::ValidationStatus::Valid);
    assert!(!diagnostic_codes(&report)
        .contains(&"authoring_construction.interpretation.unavailable".into()));
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

fn custom_qualification(definition: &Json) -> Json {
    Json::Object(BTreeMap::from([
        (
            "semantic_kind".into(),
            definition.get("semantic_kind").cloned().expect("kind"),
        ),
        (
            "semantic_type".into(),
            definition.get("semantic_type").cloned().expect("type"),
        ),
        (
            "consumer_namespace".into(),
            definition
                .get("consumer_namespace")
                .cloned()
                .expect("namespace"),
        ),
        (
            "contract_version".into(),
            definition
                .get("contract_version")
                .cloned()
                .expect("version"),
        ),
        (
            "contract_fingerprint".into(),
            definition
                .get("contract_fingerprint")
                .cloned()
                .expect("fingerprint"),
        ),
    ]))
}

fn raw_digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    format!(
        "sha256:{}",
        digest.iter().map(|byte| format!("{byte:02x}")).collect::<String>()
    )
}

fn canonical_digest(value: &Json) -> String {
    semantic_contract::canonicalize(&Json::Object(BTreeMap::from([(
        "value".into(),
        value.clone(),
    )])))
    .get("fingerprint")
    .and_then(Json::as_str)
    .expect("canonical value fingerprint")
    .to_owned()
}

fn base64_encode(bytes: &[u8]) -> String {
    const ALPHABET: &[u8; 64] =
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut encoded = String::new();
    for chunk in bytes.chunks(3) {
        let first = chunk[0] as u32;
        let second = chunk.get(1).copied().unwrap_or(0) as u32;
        let third = chunk.get(2).copied().unwrap_or(0) as u32;
        let value = (first << 16) | (second << 8) | third;
        encoded.push(ALPHABET[((value >> 18) & 63) as usize] as char);
        encoded.push(ALPHABET[((value >> 12) & 63) as usize] as char);
        encoded.push(if chunk.len() > 1 {
            ALPHABET[((value >> 6) & 63) as usize] as char
        } else {
            '='
        });
        encoded.push(if chunk.len() > 2 {
            ALPHABET[(value & 63) as usize] as char
        } else {
            '='
        });
    }
    encoded
}

#[test]
fn frozen_acc_vectors_use_one_shared_validation_authority() {
    let cases = [
        "C11", "C12", "C13", "C16", "C17", "C19", "C20", "C23", "C24", "C25", "C26", "C27", "C29", "C31",
        "C34", "C40", "C41", "C42",
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
fn frozen_constructed_inputs_are_valid_under_shared_validation_authority() {
    let mut failures = Vec::new();
    for frozen_case in bound_cases() {
        let expected_outcome = frozen_case
            .get("expected")
            .and_then(Json::as_object)
            .and_then(|expected| expected.get("result"))
            .and_then(Json::as_object)
            .and_then(|result| result.get("outcome"))
            .and_then(Json::as_str);
        if expected_outcome != Some("Constructed") {
            continue;
        }
        let case_id = frozen_case
            .get("id")
            .and_then(Json::as_str)
            .expect("frozen Constructed case has an id");
        let input = frozen_case
            .get("input")
            .expect("frozen Constructed case has input");
        let report = authoring_construction::validate_authoring_request(input);
        if report.status != authoring_construction::ValidationStatus::Valid
            || !report.diagnostics.is_empty()
        {
            failures.push(format!(
                "{case_id}: status={}, diagnostics={:?}",
                report.status.as_str(),
                report.diagnostics
            ));
        }
    }
    assert!(failures.is_empty(), "invalid frozen Constructed inputs: {failures:#?}");
}

#[test]
fn c31_cardinality_is_validated_by_shared_authority() {
    let report = authoring_construction::validate_authoring_request(&case_input("C31"));
    assert_eq!(
        report.status,
        authoring_construction::ValidationStatus::Invalid
    );
    let codes = diagnostic_codes(&report);
    assert_eq!(
        codes,
        vec!["authoring_construction.relationship.cardinality"]
    );
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

#[test]
fn request_local_and_existing_reference_resolution_are_distinct() {
    let request_local = authoring_construction::validate_authoring_request(&case_input("C06"));
    assert_eq!(request_local.status, authoring_construction::ValidationStatus::Valid);
    assert!(!diagnostic_codes(&request_local)
        .contains(&"authoring_construction.reference.fragment_unresolved".into()));

    let existing = authoring_construction::validate_authoring_request(&case_input("C04"));
    assert_eq!(existing.status, authoring_construction::ValidationStatus::Valid);
    assert!(!diagnostic_codes(&existing)
        .contains(&"authoring_construction.reference.fragment_unresolved".into()));
}

#[test]
fn missing_existing_reference_remains_unresolved() {
    let report = authoring_construction::validate_authoring_request(&case_input("C41"));
    assert_eq!(report.status, authoring_construction::ValidationStatus::Unresolved);
    assert!(diagnostic_codes(&report)
        .contains(&"authoring_construction.reference.fragment_unresolved".into()));
}

#[test]
fn exact_existing_source_and_qualification_are_required_for_updates() {
    let mut request = case_input("C34");
    let basis = request
        .as_object_mut()
        .and_then(|root| root.get_mut("basis"))
        .and_then(Json::as_object_mut)
        .expect("basis is mutable");
    basis.insert(
        "existing_source_basis".into(),
        Json::Object(BTreeMap::from([
            ("sealed".into(), Json::Bool(true)),
            (
                "entries".into(),
                Json::Array(vec![Json::Object(BTreeMap::from([
                    (
                        "canonical_uuid".into(),
                        Json::String("019109a0-b1c2-7def-8a00-112233445566".into()),
                    ),
                    ("semantic_type".into(), Json::String("entity/decision".into())),
                    (
                        "qualification".into(),
                        case_input("C13")
                            .get("basis")
                            .and_then(Json::as_object)
                            .and_then(|value| value.get("adc"))
                            .cloned()
                            .expect("ADC qualification exists"),
                    ),
                    ("source_ref".into(), Json::String("test/existing".into())),
                    ("content_digest".into(), Json::String("sha256:2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881".into())),
                    ("source_bytes".into(), Json::String("eA==".into())),
                ]))]),
            ),
        ])),
    );
    let report = authoring_construction::validate_authoring_request(&request);
    assert!(!diagnostic_codes(&report)
        .contains(&"authoring_construction.basis.existing_source_unavailable".into()));

    let fragment_qualification = request
        .get("request")
        .and_then(Json::as_object)
        .and_then(|value| value.get("fragments"))
        .and_then(Json::as_array)
        .and_then(|values| values.first())
        .and_then(Json::as_object)
        .and_then(|value| value.get("contract_qualification"))
        .cloned()
        .expect("fragment qualification exists");
    {
        let entry = request
            .as_object_mut()
            .and_then(|root| root.get_mut("basis"))
            .and_then(Json::as_object_mut)
            .and_then(|basis| basis.get_mut("existing_source_basis"))
            .and_then(Json::as_object_mut)
            .and_then(|basis| basis.get_mut("entries"))
            .and_then(Json::as_array_mut)
            .and_then(|entries| entries.first_mut())
            .and_then(Json::as_object_mut)
            .expect("source entry exists");
        entry.insert("qualification".into(), fragment_qualification);
    }
    let report = authoring_construction::validate_authoring_request(&request);
    assert!(!diagnostic_codes(&report)
        .contains(&"authoring_construction.basis.existing_source_unavailable".into()));

    request
        .as_object_mut()
        .and_then(|root| root.get_mut("basis"))
        .and_then(Json::as_object_mut)
        .and_then(|basis| basis.get_mut("existing_source_basis"))
        .and_then(Json::as_object_mut)
        .and_then(|basis| basis.get_mut("entries"))
        .and_then(Json::as_array_mut)
        .and_then(|entries| entries.first_mut())
        .and_then(Json::as_object_mut)
        .expect("source entry exists")
        .insert("source_bytes".into(), Json::String("eQ==".into()));
    let report = authoring_construction::validate_authoring_request(&request);
    assert!(diagnostic_codes(&report)
        .contains(&"authoring_construction.basis.exact_source_digest".into()));
}

#[test]
fn canonical_qualification_and_field_schema_are_authoritative() {
    let mut qualification_mismatch = case_input("C01");
    qualification_mismatch
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fragments"))
        .and_then(Json::as_array_mut)
        .and_then(|values| values.first_mut())
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("contract_qualification"))
        .and_then(Json::as_object_mut)
        .expect("canonical qualification exists")
        .insert("version".into(), Json::String("9.9".into()));
    let report = authoring_construction::validate_authoring_request(&qualification_mismatch);
    assert!(diagnostic_codes(&report)
        .contains(&"authoring_construction.fragment.qualification_mismatch".into()));

    let mut invalid_field = case_input("C01");
    invalid_field
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fragments"))
        .and_then(Json::as_array_mut)
        .and_then(|values| values.first_mut())
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fields"))
        .and_then(Json::as_object_mut)
        .expect("canonical fields exist")
        .insert("alias_id".into(), Json::Bool(true));
    let report = authoring_construction::validate_authoring_request(&invalid_field);
    assert!(diagnostic_codes(&report)
        .contains(&"authoring_construction.field.invalid".into()));

    let mut missing_field = case_input("C01");
    missing_field
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fragments"))
        .and_then(Json::as_array_mut)
        .and_then(|values| values.first_mut())
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fields"))
        .and_then(Json::as_object_mut)
        .expect("canonical fields exist")
        .remove("summary");
    let report = authoring_construction::validate_authoring_request(&missing_field);
    assert!(diagnostic_codes(&report)
        .contains(&"authoring_construction.field.required".into()));
}

#[test]
fn unmodified_c02_is_valid_before_create_time_identity_establishment() {
    let report = authoring_construction::validate_authoring_request(&case_input("C02"));
    assert_eq!(report.status, authoring_construction::ValidationStatus::Valid);
    assert!(report.diagnostics.is_empty(), "{:?}", report.diagnostics);
}

#[test]
fn create_identity_mint_does_not_suppress_other_required_fields() {
    let mut request = case_input("C02");
    request
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fragments"))
        .and_then(Json::as_array_mut)
        .and_then(|values| values.first_mut())
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fields"))
        .and_then(Json::as_object_mut)
        .expect("C02 canonical fields exist")
        .remove("summary");

    let report = authoring_construction::validate_authoring_request(&request);
    assert_eq!(
        diagnostic_codes(&report),
        vec!["authoring_construction.field.required"],
        "missing summary must remain diagnosable when id is intentionally absent: {:?}",
        report.diagnostics
    );
    assert_eq!(
        report.diagnostics[0].get("location").and_then(Json::as_str),
        Some("/request/fragments/0/fields/summary")
    );
    assert!(!diagnostic_codes(&report)
        .contains(&"authoring_construction.identity.update_requires_existing".into()));
    assert!(!report.diagnostics.iter().any(|diagnostic| {
        diagnostic.get("location").and_then(Json::as_str)
            == Some("/request/fragments/0/fields/id")
    }));
}

#[test]
fn supplied_id_only_create_reports_all_other_required_canonical_fields() {
    let mut request = case_input("C01");
    let fields = request
        .as_object_mut()
        .and_then(|root| root.get_mut("request"))
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fragments"))
        .and_then(Json::as_array_mut)
        .and_then(|values| values.first_mut())
        .and_then(Json::as_object_mut)
        .and_then(|value| value.get_mut("fields"))
        .and_then(Json::as_object_mut)
        .expect("C01 canonical fields exist");
    fields.clear();
    fields.insert(
        "id".into(),
        Json::String("019109a0-b1c2-7def-8a00-112233445566".into()),
    );

    let report = authoring_construction::validate_authoring_request(&request);
    let locations = report
        .diagnostics
        .iter()
        .filter_map(|diagnostic| diagnostic.get("location").and_then(Json::as_str))
        .collect::<Vec<_>>();
    assert_eq!(
        locations,
        vec![
            "/request/fragments/0/fields/alias_id",
            "/request/fragments/0/fields/alias_name",
            "/request/fragments/0/fields/rationale",
            "/request/fragments/0/fields/summary",
        ]
    );
    assert!(!locations.contains(&"/request/fragments/0/fields/id"));
}

#[test]
fn exact_custom_registry_authority_controls_fields_endpoints_and_cardinality() {
    let rules = document(include_str!(
        "../../contracts/authoring-construction/v1.0/resources/rules.json"
    ));
    let selection_rule = rules
        .get("authority")
        .and_then(Json::as_object)
        .and_then(|authority| authority.get("custom_definition_selection"))
        .and_then(Json::as_object)
        .expect("ACC declares exact custom-definition selection authority");
    assert_eq!(
        selection_rule.get("source_locator").and_then(Json::as_str),
        Some("registry_source.source_ref#/definitions/<zero_based_index>")
    );
    assert_eq!(
        selection_rule
            .get("definition_digest")
            .and_then(Json::as_str),
        Some("canonical_semantic_json_sha256_of_exact_definition_object")
    );
    let registry_bytes = include_bytes!("../../tests/fixtures/custom-entity-v1.0/valid-observation-registry.json");
    let registry = document(std::str::from_utf8(registry_bytes).expect("fixture is UTF-8"));
    let definitions = registry
        .get("definitions")
        .and_then(Json::as_array)
        .expect("registry definitions");
    let observation = definitions
        .iter()
        .find(|definition| definition.get("semantic_type").and_then(Json::as_str) == Some("example:observation"))
        .cloned()
        .expect("observation definition");
    let observes = definitions
        .iter()
        .find(|definition| definition.get("semantic_type").and_then(Json::as_str) == Some("example:observes"))
        .cloned()
        .expect("relationship definition");
    let registry_digest = raw_digest(registry_bytes);
    let selected = [observation.clone(), observes.clone()]
        .iter()
        .enumerate()
        .map(|(definition_index, definition)| {
            let mut selected = definition
                .as_object()
                .expect("definition object")
                .iter()
                .filter(|(key, _)| {
                    matches!(
                        key.as_str(),
                        "semantic_kind"
                            | "semantic_type"
                            | "consumer_namespace"
                            | "contract_version"
                            | "contract_fingerprint"
                    )
                })
                .map(|(key, value)| (key.clone(), value.clone()))
                .collect::<BTreeMap<_, _>>();
            selected.insert(
                "definition_source".into(),
                Json::String(format!(
                    "tests/fixtures/custom-entity-v1.0/valid-observation-registry.json#/definitions/{definition_index}"
                )),
            );
            selected.insert(
                "definition_digest".into(),
                Json::String(canonical_digest(definition)),
            );
            Json::Object(selected)
        })
        .collect::<Vec<_>>();

    let mut request = case_input("C31");
    let root = request.as_object_mut().expect("request root");
    let basis = root
        .get_mut("basis")
        .and_then(Json::as_object_mut)
        .expect("basis");
    let custom_basis = basis
        .get_mut("custom_entity")
        .and_then(Json::as_object_mut)
        .expect("custom basis");
    custom_basis.insert(
        "registry_source".into(),
        Json::Object(BTreeMap::from([
            ("source_ref".into(), Json::String("tests/fixtures/custom-entity-v1.0/valid-observation-registry.json".into())),
            ("content_digest".into(), Json::String(registry_digest.clone())),
            ("source_bytes".into(), Json::String(base64_encode(registry_bytes))),
        ])),
    );
    custom_basis.insert("selected_definitions".into(), Json::Array(selected));
    let adc = basis.get("adc").cloned().expect("ADC basis");
    let observation_id = Json::String("019109a0-b1c2-7def-8a00-112233445568".into());
    let capability_id = Json::String("019109a0-b1c2-7def-8a00-112233445569".into());
    let fragments = Json::Array(vec![
        Json::Object(BTreeMap::from([
            ("request_key".into(), Json::String("observation".into())),
            ("semantic_kind".into(), Json::String("entity".into())),
            ("semantic_type".into(), Json::String("example:observation".into())),
            ("operation".into(), Json::String("create".into())),
            ("input_mode".into(), Json::String("prepared".into())),
            ("fields".into(), Json::Object(BTreeMap::from([
                ("id".into(), observation_id),
                ("alias_id".into(), Json::String("OBS-1".into())),
                ("alias_name".into(), Json::String("observation".into())),
                ("existence_state".into(), Json::String("active".into())),
                ("observation_code".into(), Json::String("OBS-1".into())),
            ]))),
            ("contract_qualification".into(), custom_qualification(&observation)),
            ("references".into(), Json::Array(Vec::new())),
            ("composition_keys".into(), Json::Array(Vec::new())),
        ])),
        Json::Object(BTreeMap::from([
            ("request_key".into(), Json::String("capability".into())),
            ("semantic_kind".into(), Json::String("entity".into())),
            ("semantic_type".into(), Json::String("entity/capability".into())),
            ("operation".into(), Json::String("create".into())),
            ("input_mode".into(), Json::String("prepared".into())),
            ("fields".into(), Json::Object(BTreeMap::from([
                ("id".into(), capability_id),
                ("alias_id".into(), Json::String("CAP-1".into())),
                ("alias_name".into(), Json::String("capability".into())),
                ("name".into(), Json::String("Capability".into())),
                ("description".into(), Json::String("A capability.".into())),
            ]))),
            ("contract_qualification".into(), adc),
            ("references".into(), Json::Array(Vec::new())),
            ("composition_keys".into(), Json::Array(Vec::new())),
        ])),
    ]);
    let relationship = |key: &str| {
        Json::Object(BTreeMap::from([
            ("relationship_key".into(), Json::String(key.into())),
            ("relationship_type".into(), Json::String("example:observes".into())),
            ("source".into(), Json::Object(BTreeMap::from([
                ("kind".into(), Json::String("request".into())),
                ("target".into(), Json::String("observation".into())),
            ]))),
            ("target".into(), Json::Object(BTreeMap::from([
                ("kind".into(), Json::String("request".into())),
                ("target".into(), Json::String("capability".into())),
            ]))),
            ("fields".into(), Json::Object(BTreeMap::new())),
            ("qualification".into(), custom_qualification(&observes)),
        ]))
    };
    root.get_mut("request")
        .and_then(Json::as_object_mut)
        .expect("request body")
        .insert("fragments".into(), fragments);
    root.get_mut("request")
        .and_then(Json::as_object_mut)
        .expect("request body")
        .insert(
            "relationships".into(),
            Json::Array(vec![relationship("one"), relationship("two")]),
        );

    let report = authoring_construction::validate_authoring_request(&request);
    let codes = diagnostic_codes(&report);
    assert_eq!(report.status, authoring_construction::ValidationStatus::Valid, "{codes:?}");
    assert!(!codes.contains(&"authoring_construction.custom.authority_unavailable".into()));
    assert!(!codes.contains(&"authoring_construction.relationship.endpoint_forbidden".into()));
    assert!(!codes.contains(&"authoring_construction.relationship.cardinality".into()));

    for (field, value) in [
        (
            "definition_source",
            Json::String(
                "tests/fixtures/custom-entity-v1.0/valid-observation-registry.json#/definitions/99"
                    .into(),
            ),
        ),
        (
            "definition_digest",
            Json::String(format!("sha256:{}", "0".repeat(64))),
        ),
    ] {
        let mut tampered = request.clone();
        tampered
            .as_object_mut()
            .and_then(|root| root.get_mut("basis"))
            .and_then(Json::as_object_mut)
            .and_then(|basis| basis.get_mut("custom_entity"))
            .and_then(Json::as_object_mut)
            .and_then(|custom| custom.get_mut("selected_definitions"))
            .and_then(Json::as_array_mut)
            .and_then(|definitions| definitions.first_mut())
            .and_then(Json::as_object_mut)
            .expect("selected definition")
            .insert(field.into(), value);
        let tampered_report = authoring_construction::validate_authoring_request(&tampered);
        assert!(
            diagnostic_codes(&tampered_report)
                .contains(&"authoring_construction.custom.authority_unavailable".into()),
            "tampered {field} must fail closed: {:?}",
            tampered_report.diagnostics
        );
    }
}
