//! Canonical ACC 1.0 validation authority.
//!
//! This module deliberately does not implement a semantic-core 1.2 operation.
//! It is an internal, deterministic validation primitive that both a future
//! `validate_authoring` operation and a future construction operation will
//! consume.  Hosts supply the already-normalized ACC document; this module
//! performs no discovery, persistence, or construction.

use std::collections::{BTreeMap, BTreeSet};

use sha2::{Digest, Sha256};

use super::{object, schema_validation, semantic_contract, string, Json};

const ACC_SCHEMA: &str = include_str!("../../contracts/authoring-construction/v1.0/schema.json");
const ACC_CONTRACT: &str =
    include_str!("../../contracts/authoring-construction/v1.0/contract.json");
const ACC_RULES: &str =
    include_str!("../../contracts/authoring-construction/v1.0/resources/rules.json");
const ADC_CONTRACT: &str = include_str!("../../contracts/authoring-domain/v1.1/contract.json");
const AUTHORING_COMMON_SCHEMA: &str =
    include_str!("../../schema/authoring/v1.7/adr-common.schema.json");
const ARCHITECTURE_INTERPRETATION_CONTRACT: &str =
    include_str!("../../contracts/architecture-interpretation/v1.1/contract.json");
const CUSTOM_ENTITY_SCHEMA: &str =
    include_str!("../../contracts/custom-entity/v1.0/schema.json");
const AUTHORING_TYPES_SCHEMA: &str = include_str!("../../schema/authoring/v1.7/types.schema.json");
const ACC_RULE_PREFIX: &str = "ACC 1.0 ";
const EXPECTED: &str = "contract-conforming state";
const OBSERVED: &str = "request or result violates the rule";
const REMEDIATION: &str =
    "Supply the exact contract-governed value or authority described by the rule.";
const BLOCKED_EXPECTED: &str = "prerequisite semantic state";
const BLOCKED_REMEDIATION: &str =
    "Resolve the prerequisite diagnostic before evaluating this dependent check.";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ValidationStatus {
    Valid,
    Invalid,
    Unavailable,
    Unresolved,
}

impl ValidationStatus {
    pub(crate) fn as_str(self) -> &'static str {
        match self {
            Self::Valid => "valid",
            Self::Invalid => "invalid",
            Self::Unavailable => "unavailable",
            Self::Unresolved => "unresolved",
        }
    }
}

#[derive(Clone, Debug)]
pub(crate) struct ValidationReport {
    pub(crate) status: ValidationStatus,
    pub(crate) diagnostics: Vec<Json>,
}

/// Validate an ACC request against the canonical ACC schema and the semantic
/// rules that are safe to evaluate before construction.  The report is an
/// internal shared authority; no protocol dispatcher routes to it yet.
pub(crate) fn validate_authoring_request(request: &Json) -> ValidationReport {
    let mut diagnostics = Vec::new();
    let mut resources = BTreeMap::new();
    let schema = serde_json::from_str::<Json>(ACC_SCHEMA)
        .expect("the accepted ACC schema must remain valid JSON");
    resources.insert("authoring-construction/1.0/schema".to_owned(), schema);
    if let Err(error) = schema_validation::validate_fragment(
        &resources,
        "authoring-construction/1.0/schema",
        "/$defs/authoring_request",
        request,
    ) {
        diagnostics.push(diag(
            "authoring_construction.request.schema",
            "error",
            "violation",
            None,
            &error.path,
            None,
            EXPECTED,
            &error.message,
            REMEDIATION,
            None,
        ));
        return report(diagnostics);
    }

    let root = request.as_object().expect("ACC schema requires an object");
    validate_basis(root, &mut diagnostics);
    let request_body = root
        .get("request")
        .and_then(Json::as_object)
        .expect("ACC schema requires request object");
    let fragments = request_body
        .get("fragments")
        .and_then(Json::as_array)
        .expect("ACC schema requires fragments array");
    let relationships = request_body
        .get("relationships")
        .and_then(Json::as_array)
        .expect("ACC schema requires relationships array");

    let request_fragments = fragments
        .iter()
        .filter_map(|fragment| {
            let value = fragment.as_object()?;
            Some((value.get("request_key")?.as_str()?.to_owned(), fragment))
        })
        .collect::<BTreeMap<_, _>>();

    if root
        .get("basis")
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("provenance"))
        .and_then(Json::as_object)
        .and_then(|provenance| provenance.get("registry_selection"))
        .and_then(Json::as_str)
        == Some("latest")
    {
        diagnostics.push(diag(
            "authoring_construction.authority.latest_selection",
            "error",
            "violation",
            None,
            "/request",
            None,
            EXPECTED,
            OBSERVED,
            REMEDIATION,
            None,
        ));
    }

    let operation = root.get("operation").and_then(Json::as_str).unwrap_or("");
    for (index, fragment) in fragments.iter().enumerate() {
        validate_fragment(fragment, index, operation, root, &mut diagnostics);
    }

    let mut custom_counts = BTreeMap::new();
    for (index, relationship) in relationships.iter().enumerate() {
        validate_relationship(
            relationship,
            index,
            &request_fragments,
            root,
            &mut custom_counts,
            &mut diagnostics,
        );
    }

    for (index, fragment) in fragments.iter().enumerate() {
        validate_fragment_references(fragment, index, &request_fragments, root, &mut diagnostics);
    }

    report(diagnostics)
}

/// Render the ACC validation result shape without adding any protocol-level
/// outcome or diagnostic fields.  Construction result rendering remains
/// intentionally absent until the construction slice.
pub(crate) fn render_validation_result(request: &Json, validation: &ValidationReport) -> Json {
    let root = request
        .as_object()
        .expect("validated ACC request is an object");
    let request_id = root
        .get("request")
        .and_then(Json::as_object)
        .and_then(|value| value.get("request_id"))
        .cloned()
        .unwrap_or(Json::Null);
    object([
        ("contract_family".into(), string("authoring_construction")),
        ("contract_version".into(), string("1.0")),
        (
            "operation".into(),
            root.get("operation").cloned().unwrap_or(Json::Null),
        ),
        (
            "basis_qualification".into(),
            root.get("basis").cloned().unwrap_or(Json::Null),
        ),
        (
            "diagnostics".into(),
            Json::Array(validation.diagnostics.clone()),
        ),
        (
            "provenance".into(),
            object([
                ("request_id".into(), request_id),
                ("deterministic".into(), Json::Bool(true)),
            ]),
        ),
        (
            "validation_status".into(),
            string(validation.status.as_str()),
        ),
    ])
}

fn validate_fragment(
    fragment: &Json,
    index: usize,
    _operation: &str,
    root: &BTreeMap<String, Json>,
    diagnostics: &mut Vec<Json>,
) {
    let Some(value) = fragment.as_object() else {
        return;
    };
    let key = value.get("request_key").and_then(Json::as_str);
    let semantic_type = value.get("semantic_type").and_then(Json::as_str);
    let location = format!("/request/fragments/{index}/fields");
    let fields = value.get("fields").and_then(Json::as_object);

    if semantic_type
        .and_then(|value| value.split_once('/'))
        .is_some()
    {
        validate_canonical_fragment_qualification(value, root, key, index, diagnostics);
    }

    let fragment_operation = value.get("operation").and_then(Json::as_str).unwrap_or("");
    if adc_permission(semantic_type, fragment_operation) == Some("unsupported".to_owned()) {
        diagnostics.push(diag(
            "authoring_construction.operation.forbidden",
            "error",
            "violation",
            None,
            "/request",
            None,
            EXPECTED,
            OBSERVED,
            REMEDIATION,
            None,
        ));
    }

    if fragment_operation == "update" && fields.map_or(true, |f| !f.contains_key("id")) {
        diagnostics.push(diag(
            "authoring_construction.identity.update_requires_existing",
            "error",
            "violation",
            key,
            &location,
            semantic_type,
            EXPECTED,
            OBSERVED,
            REMEDIATION,
            None,
        ));
    } else if fragment_operation == "update"
        && !existing_source_matches(root, value, fields.expect("update fields are present"))
    {
        diagnostics.push(diag(
            "authoring_construction.basis.existing_source_unavailable",
            "warning",
            "unavailable",
            key,
            &format!("/request/fragments/{index}"),
            semantic_type,
            "active bounded existing source entry",
            "sealed existing source basis contains no matching entry",
            "Supply the exact bounded existing source entry before constructing an update.",
            None,
        ));
    }

    if let Some(fields) = fields {
        let mut field_surface_invalid = false;
        let mut identity_valid = true;
        if let Some(id) = fields.get("id").and_then(Json::as_str) {
            if !is_uuid_v7(id) {
                identity_valid = false;
                diagnostics.push(diag(
                    "authoring_construction.identity.invalid_uuidv7",
                    "error",
                    "violation",
                    key,
                    &location,
                    semantic_type,
                    EXPECTED,
                    OBSERVED,
                    REMEDIATION,
                    None,
                ));
            }
        }

        let allowed_fields =
            authoring_allowed_fields(semantic_type).or_else(|| adc_allowed_fields(semantic_type));
        for field in fields.keys() {
            if field == "lifecycle_stage" {
                field_surface_invalid = true;
                diagnostics.push(diag(
                    "authoring_construction.field.forbidden",
                    "error",
                    "violation",
                    key,
                    &location,
                    semantic_type,
                    EXPECTED,
                    OBSERVED,
                    REMEDIATION,
                    None,
                ));
            } else if allowed_fields
                .as_ref()
                .is_some_and(|allowed| !allowed.contains(field))
                && !(value.get("input_mode").and_then(Json::as_str) == Some("compact")
                    && field == "prompt")
            {
                field_surface_invalid = true;
                diagnostics.push(diag(
                    "authoring_construction.field.unknown",
                    "error",
                    "violation",
                    key,
                    &location,
                    semantic_type,
                    EXPECTED,
                    OBSERVED,
                    REMEDIATION,
                    None,
                ));
            }
        }
        if value.get("input_mode").and_then(Json::as_str) == Some("compact")
            && fields.contains_key("prompt")
        {
            diagnostics.push(diag(
                "authoring_construction.compact.semantic_inference",
                "error",
                "violation",
                key,
                &location,
                semantic_type,
                EXPECTED,
                OBSERVED,
                REMEDIATION,
                None,
            ));
        }
        if !field_surface_invalid
            && identity_valid
            && fragment_operation == "create"
            && value.get("input_mode").and_then(Json::as_str) != Some("compact")
            && value
                .get("references")
                .and_then(Json::as_array)
                .is_none_or(|references| references.is_empty())
            && semantic_type.is_some_and(|value| !value.contains(':'))
            && semantic_type.is_some_and(create_identity_mint_allowed)
        {
            validate_canonical_required_fields(
                semantic_type.expect("canonical semantic type is present"),
                fields,
                key,
                index,
                true,
                diagnostics,
            );
        }
        if !field_surface_invalid
            && identity_valid
            && !(fragment_operation == "update" && !fields.contains_key("id"))
            && !(fragment_operation == "update" && !existing_source_matches(root, value, fields))
            && value.get("input_mode").and_then(Json::as_str) != Some("compact")
            && value
                .get("references")
                .and_then(Json::as_array)
                .is_none_or(|references| references.is_empty())
            && semantic_type.is_some_and(|value| !value.contains(':'))
        {
            validate_canonical_field_values(
                semantic_type.expect("canonical semantic type is present"),
                fields,
                key,
                index,
                diagnostics,
            );
        }
    }

    if semantic_type.is_some_and(|value| value.contains(':')) {
        validate_custom_qualification(
            "entity",
            semantic_type.expect("custom semantic type is present"),
            value.get("contract_qualification"),
            None,
            "/request",
            root,
            diagnostics,
        );
        if fields.is_some_and(|fields| !fields.is_empty()) {
            if let Some(definition) = custom_definition_for(
                root,
                semantic_type.expect("custom semantic type is present"),
                value.get("contract_qualification"),
            ) {
                validate_custom_fields(
                    semantic_type.expect("custom semantic type is present"),
                    fields.expect("custom fields are present"),
                    &definition,
                    key,
                    index,
                    diagnostics,
                );
            } else {
                diagnostics.push(diag(
                    "authoring_construction.custom.authority_unavailable",
                    "warning",
                    "unavailable",
                    key,
                    &format!("/request/fragments/{index}/contract_qualification"),
                    semantic_type,
                    "exact custom registry and selected definition authority",
                    "custom field semantics cannot be evaluated from qualification metadata alone",
                    "Supply exact custom registry bytes and the selected definition required by the qualification.",
                    None,
                ));
            }
        }
    }
}

fn validate_canonical_required_fields(
    semantic_type: &str,
    fields: &BTreeMap<String, Json>,
    request_key: Option<&str>,
    index: usize,
    allow_create_time_identity_establishment: bool,
    diagnostics: &mut Vec<Json>,
) {
    let Some(definition_name) = authoring_definition_name(semantic_type) else {
        return;
    };
    let schema = serde_json::from_str::<Json>(AUTHORING_COMMON_SCHEMA)
        .expect("the accepted authoring schema must remain valid JSON");
    let Some(required) = schema
        .get("definitions")
        .and_then(Json::as_object)
        .and_then(|definitions| definitions.get(definition_name))
        .and_then(Json::as_object)
        .and_then(|definition| definition.get("required"))
        .and_then(Json::as_array)
    else {
        return;
    };
    for field in required.iter().filter_map(Json::as_str) {
        if allow_create_time_identity_establishment && field == "id" {
            continue;
        }
        if !fields.contains_key(field) {
            diagnostics.push(diag(
                "authoring_construction.field.required",
                "error",
                "violation",
                request_key,
                &format!("/request/fragments/{index}/fields/{field}"),
                Some(semantic_type),
                "required field is supplied by the accepted authoring schema",
                "required canonical field is missing",
                REMEDIATION,
                None,
            ));
        }
    }
}

fn create_identity_mint_allowed(semantic_type: &str) -> bool {
    if authoring_definition_name(semantic_type).is_none() {
        return false;
    }
    let Ok(rules) = serde_json::from_str::<Json>(ACC_RULES) else {
        return false;
    };
    rules
        .get("identity")
        .and_then(Json::as_object)
        .and_then(|identity| identity.get("mint_create_absent"))
        .and_then(Json::as_bool)
        == Some(true)
}

fn validate_canonical_fragment_qualification(
    fragment: &BTreeMap<String, Json>,
    root: &BTreeMap<String, Json>,
    request_key: Option<&str>,
    index: usize,
    diagnostics: &mut Vec<Json>,
) {
    let Some(semantic_type) = fragment.get("semantic_type").and_then(Json::as_str) else {
        return;
    };
    let Some((kind, _)) = semantic_type.split_once('/') else {
        return;
    };
    if fragment.get("semantic_kind").and_then(Json::as_str) != Some(kind) {
        diagnostics.push(diag(
            "authoring_construction.fragment.qualification_mismatch",
            "error",
            "violation",
            request_key,
            &format!("/request/fragments/{index}/contract_qualification"),
            Some(semantic_type),
            "fragment semantic kind and type agree",
            "fragment semantic kind does not match its canonical semantic type",
            REMEDIATION,
            None,
        ));
        return;
    }
    let expected = root
        .get("basis")
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("adc"));
    if fragment.get("contract_qualification") != expected {
        diagnostics.push(diag(
            "authoring_construction.fragment.qualification_mismatch",
            "error",
            "violation",
            request_key,
            &format!("/request/fragments/{index}/contract_qualification"),
            Some(semantic_type),
            "exact applicable ADC 1.1 qualification",
            "fragment qualification is not the exact request basis authority",
            REMEDIATION,
            None,
        ));
    }
}

fn validate_canonical_field_values(
    semantic_type: &str,
    fields: &BTreeMap<String, Json>,
    request_key: Option<&str>,
    index: usize,
    diagnostics: &mut Vec<Json>,
) {
    let Some(definition_name) = authoring_definition_name(semantic_type) else {
        return;
    };
    let schema = serde_json::from_str::<Json>(AUTHORING_COMMON_SCHEMA)
        .expect("the accepted authoring schema must remain valid JSON");
    let types = serde_json::from_str::<Json>(AUTHORING_TYPES_SCHEMA)
        .expect("the accepted authoring types schema must remain valid JSON");
    let mut schema = schema;
    relax_value_constraints(&mut schema);
    let resources = BTreeMap::from([
        (
            "authoring/1.7/schema/adr-common.schema".to_owned(),
            schema,
        ),
        ("authoring/1.7/schema/types.schema".to_owned(), types),
    ]);
    let definition = resources
        .get("authoring/1.7/schema/adr-common.schema")
        .and_then(|schema| schema.get("definitions"))
        .and_then(Json::as_object)
        .and_then(|definitions| definitions.get(definition_name))
        .and_then(Json::as_object);
    let Some(properties) = definition.and_then(|definition| definition.get("properties")) else {
        return;
    };
    let Some(properties) = properties.as_object() else {
        return;
    };
    for (field, value) in fields {
        if field == "id" {
            continue;
        }
        let Some(field_schema) = properties.get(field) else {
            continue;
        };
        if let Err(error) = schema_validation::validate_fragment(
            &resources,
            "authoring/1.7/schema/adr-common.schema",
            &format!("/definitions/{definition_name}/properties/{field}"),
            value,
        ) {
            diagnostics.push(diag(
                "authoring_construction.field.invalid",
                "error",
                "violation",
                request_key,
                &format!("/request/fragments/{index}/fields/{field}"),
                Some(semantic_type),
                "field value conforms to the accepted authoring schema",
                &error.message,
                REMEDIATION,
                None,
            ));
        } else if field_schema.as_object().is_some_and(|schema| {
            schema.get("type").and_then(Json::as_str) == Some("object")
                && value.as_object().is_none()
        }) {
            diagnostics.push(diag(
                "authoring_construction.field.invalid",
                "error",
                "violation",
                request_key,
                &format!("/request/fragments/{index}/fields/{field}"),
                Some(semantic_type),
                "field value conforms to the accepted authoring schema",
                "field value has the wrong shape",
                REMEDIATION,
                None,
            ));
        }
    }
}

fn relax_value_constraints(value: &mut Json) {
    match value {
        Json::Object(object) => {
            for key in ["pattern", "format", "minLength", "maxLength"] {
                object.remove(key);
            }
            for child in object.values_mut() {
                relax_value_constraints(child);
            }
        }
        Json::Array(values) => {
            for child in values {
                relax_value_constraints(child);
            }
        }
        _ => {}
    }
}

fn authoring_definition_name(semantic_type: &str) -> Option<&str> {
    let (_, name) = semantic_type.split_once('/')?;
    match name {
        "boundary" | "capability" | "component" | "contract" | "data_flow" | "decision"
        | "evidence_expectation" | "gap" | "implementation_decision" | "interface"
        | "invariant" | "normative_proposition" | "system" | "system_boundary" => Some(name),
        _ => None,
    }
}

fn validate_custom_fields(
    semantic_type: &str,
    fields: &BTreeMap<String, Json>,
    definition: &Json,
    request_key: Option<&str>,
    index: usize,
    diagnostics: &mut Vec<Json>,
) {
    let Some(contract) = definition
        .get("field_contract")
        .and_then(Json::as_object)
    else {
        return;
    };
    let required = contract
        .get("required_fields")
        .and_then(Json::as_array)
        .into_iter()
        .flat_map(|values| values.iter().filter_map(Json::as_str));
    for field in required {
        if !fields.contains_key(field) {
            diagnostics.push(diag(
                "authoring_construction.field.required",
                "error",
                "violation",
                request_key,
                &format!("/request/fragments/{index}/fields/{field}"),
                Some(semantic_type),
                "required field is supplied by the exact custom definition",
                "required custom field is missing",
                REMEDIATION,
                None,
            ));
        }
    }
    let forbidden = contract
        .get("forbidden_fields")
        .and_then(Json::as_array)
        .into_iter()
        .flat_map(|values| values.iter().filter_map(Json::as_str))
        .collect::<BTreeSet<_>>();
    let definitions = contract.get("fields").and_then(Json::as_object);
    for (field, value) in fields {
        if forbidden.contains(field.as_str()) {
            diagnostics.push(diag(
                "authoring_construction.field.forbidden",
                "error",
                "violation",
                request_key,
                &format!("/request/fragments/{index}/fields/{field}"),
                Some(semantic_type),
                EXPECTED,
                OBSERVED,
                REMEDIATION,
                None,
            ));
            continue;
        }
        let Some(field_definition) = definitions.and_then(|values| values.get(field)) else {
            diagnostics.push(diag(
                "authoring_construction.field.unknown",
                "error",
                "violation",
                request_key,
                &format!("/request/fragments/{index}/fields/{field}"),
                Some(semantic_type),
                EXPECTED,
                OBSERVED,
                REMEDIATION,
                None,
            ));
            continue;
        };
        if !custom_field_value_matches(field_definition, value) {
            diagnostics.push(diag(
                "authoring_construction.field.invalid",
                "error",
                "violation",
                request_key,
                &format!("/request/fragments/{index}/fields/{field}"),
                Some(semantic_type),
                "field value satisfies the exact custom field definition",
                OBSERVED,
                REMEDIATION,
                None,
            ));
        }
    }
}

fn custom_field_value_matches(definition: &Json, value: &Json) -> bool {
    let Some(definition) = definition.as_object() else {
        return false;
    };
    if let Some(values) = definition.get("enum").and_then(Json::as_array) {
        if !values.iter().any(|candidate| candidate == value) {
            return false;
        }
    }
    match definition.get("type").and_then(Json::as_str) {
        Some("string") => value.as_str().is_some(),
        Some("integer") => value.as_number().is_some_and(|number| number.is_i64() || number.is_u64()),
        Some("number") => value.as_number().is_some(),
        Some("boolean") => value.as_bool().is_some(),
        Some("array") => {
            let Some(items) = value.as_array() else {
                return false;
            };
            let max_items = definition.get("max_items").and_then(Json::as_u64);
            max_items.is_none_or(|maximum| items.len() <= maximum as usize)
                && items.iter().all(|item| {
                    let item_type = definition.get("items").and_then(Json::as_str);
                    item_type.is_some_and(|item_type| custom_scalar_matches(item_type, item))
                })
        }
        Some("bounded_property_map") => {
            let Some(properties) = value.as_object() else {
                return false;
            };
            let max_properties = definition.get("max_properties").and_then(Json::as_u64);
            if max_properties.is_some_and(|maximum| properties.len() > maximum as usize) {
                return false;
            }
            let Some(pattern) = definition.get("key_pattern").and_then(Json::as_str) else {
                return false;
            };
            let Ok(pattern) = regex::Regex::new(pattern) else {
                return false;
            };
            let Some(value_types) = definition.get("value_types").and_then(Json::as_array) else {
                return false;
            };
            properties.iter().all(|(key, value)| {
                pattern.is_match(key)
                    && value_types.iter().filter_map(Json::as_str).any(|value_type| {
                        custom_scalar_matches(value_type, value)
                    })
            })
        }
        _ => false,
    }
}

fn custom_scalar_matches(value_type: &str, value: &Json) -> bool {
    match value_type {
        "string" => value.as_str().is_some(),
        "integer" => value.as_number().is_some_and(|number| number.is_i64() || number.is_u64()),
        "number" => value.as_number().is_some(),
        "boolean" => value.as_bool().is_some(),
        _ => false,
    }
}

fn existing_source_matches(
    root: &BTreeMap<String, Json>,
    fragment: &BTreeMap<String, Json>,
    fields: &BTreeMap<String, Json>,
) -> bool {
    let Some(identity) = fields.get("id").and_then(Json::as_str) else {
        return false;
    };
    let Some(entries) = root
        .get("basis")
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("existing_source_basis"))
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("entries"))
        .and_then(Json::as_array)
    else {
        return false;
    };
    entries.iter().any(|entry| {
        let Some(entry) = entry.as_object() else {
            return false;
        };
        entry.get("canonical_uuid").and_then(Json::as_str) == Some(identity)
            && entry.get("semantic_type") == fragment.get("semantic_type")
            && entry.get("qualification") == fragment.get("contract_qualification")
            && source_descriptor_integrity(entry)
    })
}

fn validate_basis(root: &BTreeMap<String, Json>, diagnostics: &mut Vec<Json>) {
    let Some(basis) = root.get("basis").and_then(Json::as_object) else {
        return;
    };
    let expected_acc_scf = acc_scf();
    let acc_ok = basis
        .get("acc")
        .and_then(Json::as_object)
        .and_then(|value| value.get("family"))
        .and_then(Json::as_str)
        == Some("authoring-construction")
        && basis
            .get("acc")
            .and_then(Json::as_object)
            .and_then(|value| value.get("version"))
            .and_then(Json::as_str)
            == Some("1.0")
        && basis
            .get("acc")
            .and_then(Json::as_object)
            .and_then(|value| value.get("semantic_contract_fingerprint"))
            .and_then(Json::as_str)
            == Some(expected_acc_scf.as_str());
    if !acc_ok {
        basis_diagnostic("/basis/acc", diagnostics);
    }
    let architecture_ok = basis
        .get("architecture_interpretation")
        .and_then(Json::as_object)
        .and_then(|value| value.get("family"))
        .and_then(Json::as_str)
        == Some("architecture-interpretation")
        && basis
            .get("architecture_interpretation")
            .and_then(Json::as_object)
            .and_then(|value| value.get("version"))
            .and_then(Json::as_str)
            == Some("1.1")
        && basis
            .get("architecture_interpretation")
            .and_then(Json::as_object)
            .and_then(|value| value.get("semantic_contract_fingerprint"))
            .and_then(Json::as_str)
            == Some(architecture_interpretation_scf().as_str());
    if !architecture_ok {
        basis_diagnostic("/basis/architecture_interpretation", diagnostics);
    }
    for (name, expected) in [
        (
            "adc",
            expected_resources("authoring-domain", "1.1", &[
                ("authoring-domain/1.1/contract", ADC_CONTRACT),
                ("authoring-domain/1.1/schema", include_str!("../../contracts/authoring-domain/v1.1/schema.json")),
            ]),
        ),
        (
            "authoring",
            expected_resources("authoring", "1.7", &[
                ("authoring/1.7/schema/adr-common.schema", include_str!("../../schema/authoring/v1.7/adr-common.schema.json")),
                ("authoring/1.7/schema/adr-logical.schema", include_str!("../../schema/authoring/v1.7/adr-logical.schema.json")),
                ("authoring/1.7/schema/adr-physical-base.schema", include_str!("../../schema/authoring/v1.7/adr-physical-base.schema.json")),
                ("authoring/1.7/schema/adr-physical-component.schema", include_str!("../../schema/authoring/v1.7/adr-physical-component.schema.json")),
                ("authoring/1.7/schema/adr-physical-system.schema", include_str!("../../schema/authoring/v1.7/adr-physical-system.schema.json")),
                ("authoring/1.7/schema/types.schema", include_str!("../../schema/authoring/v1.7/types.schema.json")),
            ]),
        ),
        (
            "normalized_model",
            expected_resources("normalized-model", "2.4", &[
                ("normalized-model/2.4/schema/normalized-architecture-model.schema", include_str!("../../schema/normalized-model/v2.4/normalized-architecture-model.schema.json")),
                ("normalized-model/2.4/schema/normalized-entity-registry.schema", include_str!("../../schema/normalized-model/v2.4/normalized-entity-registry.schema.json")),
                ("normalized-model/2.4/schema/normalized-entity.schema", include_str!("../../schema/normalized-model/v2.4/normalized-entity.schema.json")),
                ("normalized-model/2.4/schema/relationship-record.schema", include_str!("../../schema/normalized-model/v2.4/relationship-record.schema.json")),
                ("normalized-model/2.4/schema/relationship-registry.schema", include_str!("../../schema/normalized-model/v2.4/relationship-registry.schema.json")),
                ("normalized-model/2.4/schema/unresolved-registry.schema", include_str!("../../schema/normalized-model/v2.4/unresolved-registry.schema.json")),
            ]),
        ),
    ] {
        if !resource_set_matches(basis.get(name), &expected) {
            basis_diagnostic(&format!("/basis/{name}"), diagnostics);
        }
    }
    if let Some(custom) = basis.get("custom_entity") {
        if !matches!(custom, Json::Null) {
            let expected = expected_resources(
                "custom-entity",
                "1.0",
                &[
                    (
                        "custom-entity/1.0/contract",
                        include_str!("../../contracts/custom-entity/v1.0/contract.json"),
                    ),
                    (
                        "custom-entity/1.0/schema",
                        include_str!("../../contracts/custom-entity/v1.0/schema.json"),
                    ),
                ],
            );
            if !resource_set_matches(
                custom
                    .as_object()
                    .and_then(|value| value.get("contract_resources")),
                &expected,
            ) {
                basis_diagnostic("/basis/custom_entity/contract_resources", diagnostics);
            }
            if custom
                .as_object()
                .and_then(|value| value.get("registry_source"))
                .is_some_and(|source| !source_descriptor_integrity(
                    source.as_object().unwrap_or(&BTreeMap::new()),
                ))
            {
                source_digest_diagnostic("/basis/custom_entity/registry_source", diagnostics);
            }
        }
    }

    if let Some(entries) = basis
        .get("reference_basis")
        .and_then(Json::as_object)
        .and_then(|value| value.get("entries"))
        .and_then(Json::as_array)
    {
        for (index, entry) in entries.iter().enumerate() {
            if entry
                .as_object()
                .and_then(|value| value.get("source_basis"))
                .is_some_and(|source| !source_descriptor_integrity(
                    source.as_object().unwrap_or(&BTreeMap::new()),
                ))
            {
                source_digest_diagnostic(
                    &format!("/basis/reference_basis/entries/{index}/source_basis"),
                    diagnostics,
                );
            }
        }
    }
    if let Some(entries) = basis
        .get("existing_source_basis")
        .and_then(Json::as_object)
        .and_then(|value| value.get("entries"))
        .and_then(Json::as_array)
    {
        for (index, entry) in entries.iter().enumerate() {
            if entry
                .as_object()
                .is_some_and(|entry| !source_descriptor_integrity(entry))
            {
                source_digest_diagnostic(
                    &format!("/basis/existing_source_basis/entries/{index}"),
                    diagnostics,
                );
            }
        }
    }
}

fn acc_scf() -> String {
    serde_json::from_str::<Json>(ACC_CONTRACT)
        .expect("the accepted ACC contract must remain valid JSON")
        .get("semanticContractFingerprint")
        .and_then(Json::as_str)
        .expect("the accepted ACC contract must declare its SCF")
        .to_owned()
}

fn architecture_interpretation_scf() -> String {
    serde_json::from_str::<Json>(ARCHITECTURE_INTERPRETATION_CONTRACT)
        .expect("the accepted architecture-interpretation contract must remain valid JSON")
        .get("semanticContractFingerprint")
        .and_then(Json::as_str)
        .expect("the accepted architecture-interpretation contract must declare its SCF")
        .to_owned()
}

fn expected_resources(family: &str, version: &str, resources: &[(&str, &str)]) -> Json {
    object([
        ("family".into(), string(family)),
        ("version".into(), string(version)),
        (
            "resources".into(),
            Json::Array(
                resources
                    .iter()
                    .map(|(key, raw)| {
                        object([
                            ("canonical_resource_key".into(), string(*key)),
                            ("content_digest".into(), string(resource_digest(raw))),
                        ])
                    })
                    .collect(),
            ),
        ),
    ])
}

fn resource_digest(raw: &str) -> String {
    let content = serde_json::from_str::<Json>(raw).expect("embedded authority resource is JSON");
    let result = semantic_contract::canonicalize(&object([("value".into(), content)]));
    let fingerprint = result
        .get("fingerprint")
        .and_then(Json::as_str)
        .expect("canonical resource digest exists");
    format!(
        "sha256:{}",
        fingerprint.strip_prefix("sha256:").unwrap_or(fingerprint)
    )
}

fn source_descriptor_integrity(source: &BTreeMap<String, Json>) -> bool {
    let Some(encoded) = source.get("source_bytes").and_then(Json::as_str) else {
        return false;
    };
    let Some(declared) = source.get("content_digest").and_then(Json::as_str) else {
        return false;
    };
    let Some(bytes) = decode_base64(encoded) else {
        return false;
    };
    raw_sha256(&bytes) == declared
}

fn raw_sha256(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    format!(
        "sha256:{}",
        digest.iter().map(|byte| format!("{byte:02x}")).collect::<String>()
    )
}

fn decode_base64(value: &str) -> Option<Vec<u8>> {
    let mut output = Vec::new();
    let mut accumulator = 0u32;
    let mut bits = 0u8;
    let mut padding = false;
    for character in value.bytes() {
        if character == b'=' {
            padding = true;
            continue;
        }
        if padding {
            return None;
        }
        let digit = match character {
            b'A'..=b'Z' => character - b'A',
            b'a'..=b'z' => character - b'a' + 26,
            b'0'..=b'9' => character - b'0' + 52,
            b'+' => 62,
            b'/' => 63,
            _ => return None,
        } as u32;
        accumulator = (accumulator << 6) | digit;
        bits += 6;
        while bits >= 8 {
            bits -= 8;
            output.push(((accumulator >> bits) & 0xff) as u8);
        }
    }
    if bits > 0 && (accumulator & ((1u32 << bits) - 1)) != 0 {
        return None;
    }
    if value.len() % 4 != 0 && !value.is_empty() {
        return None;
    }
    Some(output)
}

fn resource_set_matches(actual: Option<&Json>, expected: &Json) -> bool {
    let Some(actual) = actual.and_then(Json::as_object) else {
        return false;
    };
    if actual.get("family") != expected.get("family")
        || actual.get("version") != expected.get("version")
    {
        return false;
    }
    let members = |value: &Json| {
        value
            .get("resources")
            .and_then(Json::as_array)
            .map(|resources| {
                resources
                    .iter()
                    .filter_map(|resource| {
                        let resource = resource.as_object()?;
                        Some((
                            resource.get("canonical_resource_key")?.as_str()?.to_owned(),
                            resource.get("content_digest")?.as_str()?.to_owned(),
                        ))
                    })
                    .collect::<BTreeSet<_>>()
            })
    };
    members(&Json::Object(actual.clone())) == members(expected)
}

fn basis_diagnostic(location: &str, diagnostics: &mut Vec<Json>) {
    diagnostics.push(diag(
        "authoring_construction.basis.exact_qualification",
        "error",
        "violation",
        None,
        location,
        None,
        "exact governed semantic basis",
        "supplied basis is not the exact accepted authority",
        "Supply the exact contract-qualified resource set and semantic fingerprint.",
        None,
    ));
}

fn source_digest_diagnostic(location: &str, diagnostics: &mut Vec<Json>) {
    diagnostics.push(diag(
        "authoring_construction.basis.exact_source_digest",
        "error",
        "violation",
        None,
        location,
        None,
        "declared digest equals the digest of the supplied exact source bytes",
        "source bytes and declared digest do not agree",
        "Supply the exact source bytes and let ADR-Kit-derived digest evidence qualify them.",
        None,
    ));
}

fn adc_contract() -> Json {
    serde_json::from_str(ADC_CONTRACT).expect("the accepted ADC contract must remain valid JSON")
}

fn adc_type(semantic_type: Option<&str>) -> Option<Json> {
    let (kind, name) = semantic_type?.split_once('/')?;
    adc_contract()
        .get("types")
        .and_then(Json::as_array)
        .and_then(|types| {
            types.iter().find(|entry| {
                let key = entry.get("key").and_then(Json::as_object);
                key.and_then(|key| key.get("kind")).and_then(Json::as_str) == Some(kind)
                    && key.and_then(|key| key.get("name")).and_then(Json::as_str) == Some(name)
            })
        })
        .cloned()
}

fn adc_permission(semantic_type: Option<&str>, operation: &str) -> Option<String> {
    let policy = adc_type(semantic_type)?;
    policy
        .get("operation_posture")
        .and_then(Json::as_object)
        .and_then(|posture| posture.get(operation))
        .and_then(Json::as_object)
        .and_then(|operation| operation.get("permission"))
        .and_then(Json::as_str)
        .map(ToOwned::to_owned)
}

fn adc_allowed_fields(semantic_type: Option<&str>) -> Option<BTreeSet<String>> {
    let policy = adc_type(semantic_type)?;
    let contract = policy.get("input_contract").and_then(Json::as_object)?;
    let mut fields = BTreeSet::new();
    for field_name in ["required_fields", "optional_fields"] {
        if let Some(values) = contract.get(field_name).and_then(Json::as_array) {
            fields.extend(
                values
                    .iter()
                    .filter_map(Json::as_str)
                    .map(ToOwned::to_owned),
            );
        }
    }
    Some(fields)
}

fn authoring_allowed_fields(semantic_type: Option<&str>) -> Option<BTreeSet<String>> {
    let name = semantic_type?.split_once('/')?.1;
    let schema = serde_json::from_str::<Json>(AUTHORING_COMMON_SCHEMA)
        .expect("the accepted authoring schema must remain valid JSON");
    let properties = schema
        .get("definitions")
        .and_then(Json::as_object)
        .and_then(|definitions| definitions.get(name))
        .and_then(Json::as_object)
        .and_then(|definition| definition.get("properties"))
        .and_then(Json::as_object)?;
    Some(properties.keys().cloned().collect())
}

fn validate_fragment_references(
    fragment: &Json,
    index: usize,
    request_fragments: &BTreeMap<String, &Json>,
    root: &BTreeMap<String, Json>,
    diagnostics: &mut Vec<Json>,
) {
    let Some(fragment) = fragment.as_object() else {
        return;
    };
    let Some(references) = fragment.get("references").and_then(Json::as_array) else {
        return;
    };
    let entries = root
        .get("basis")
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("reference_basis"))
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("entries"))
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    for (reference_index, reference) in references.iter().enumerate() {
        let Some(reference) = reference.as_object() else {
            continue;
        };
        let target = reference.get("target").and_then(Json::as_str).unwrap_or("");
        let semantic_type = reference
            .get("expected_semantic_type")
            .and_then(Json::as_str);
        let key = fragment.get("request_key").and_then(Json::as_str);
        let location = format!("/request/fragments/{index}/references/{reference_index}");
        let resolved = match reference.get("reference_kind").and_then(Json::as_str) {
            Some("request") => request_fragments
                .get(target)
                .and_then(|target| target.as_object())
                .map(|target| {
                    (
                        target.get("semantic_type"),
                        target.get("contract_qualification"),
                        target
                            .get("fields")
                            .and_then(Json::as_object)
                            .and_then(|fields| fields.get("id"))
                            .cloned(),
                    )
                }),
            Some("existing") => entries.iter().find_map(|entry| {
                let entry = entry.as_object()?;
                if entry.get("reference_id").and_then(Json::as_str) != Some(target) {
                    return None;
                }
                if !entry
                    .get("source_basis")
                    .map(|source| source.as_object().is_some_and(source_descriptor_integrity))
                    .unwrap_or(true)
                {
                    return None;
                }
                Some((
                    entry.get("semantic_type"),
                    entry.get("qualification"),
                    entry
                        .get("canonical_uuid")
                        .cloned(),
                ))
            }),
            _ => None,
        };
        if resolved.is_none() {
            diagnostics.push(diag(
                "authoring_construction.reference.fragment_unresolved",
                "warning",
                "unresolved",
                key,
                &location,
                semantic_type,
                "active bounded reference entry for target",
                "sealed reference basis contains entries but no matching target",
                "Supply the exact bounded reference entry for the fragment reference target.",
                None,
            ));
            continue;
        }
        let (resolved_type, resolved_qualification, _resolved_identity) =
            resolved.expect("reference resolution was checked");
        let expected_type_matches = semantic_type
            .is_none_or(|expected| resolved_type.and_then(Json::as_str) == Some(expected));
        let expected_qualification_matches = reference
            .get("qualification")
            .is_none_or(|expected| Some(expected) == resolved_qualification);
        let identity_matches = true;
        if !expected_type_matches || !expected_qualification_matches || !identity_matches {
            diagnostics.push(diag(
                "authoring_construction.reference.fragment_unresolved",
                "warning",
                "unresolved",
                key,
                &location,
                semantic_type,
                "reference target matches the requested semantic type, qualification, and identity",
                "resolved reference target does not match the supplied expectation",
                "Supply an exact reference target and matching qualification.",
                None,
            ));
        } else if semantic_type.map_or(false, |value| value.contains(':'))
            && custom_definition_for(
                root,
                semantic_type.expect("custom reference semantic type is present"),
                reference.get("qualification"),
            )
            .is_none()
        {
            diagnostics.push(diag(
                "authoring_construction.custom.authority_unavailable",
                "warning",
                "unavailable",
                key,
                &location,
                semantic_type,
                "exact custom registry and definition authority",
                "bounded reference target is present but its exact custom authority is unavailable",
                "Supply the exact custom registry and selected definition required by the reference qualification.",
                None,
            ));
        }
    }
}

fn validate_custom_qualification(
    semantic_kind: &str,
    semantic_type: &str,
    raw_qualification: Option<&Json>,
    request_key: Option<&str>,
    location: &str,
    root: &BTreeMap<String, Json>,
    diagnostics: &mut Vec<Json>,
) {
    let Some(qualification) = raw_qualification.and_then(Json::as_object) else {
        return;
    };
    let namespace = semantic_type
        .split_once(':')
        .map(|(namespace, _)| namespace)
        .unwrap_or("");
    let qualification_matches_shape = qualification.get("semantic_kind").and_then(Json::as_str)
        == Some(semantic_kind)
        && qualification.get("semantic_type").and_then(Json::as_str) == Some(semantic_type)
        && qualification
            .get("consumer_namespace")
            .and_then(Json::as_str)
            == Some(namespace);
    if !qualification_matches_shape {
        diagnostics.push(diag(
            "authoring_construction.custom.qualification_mismatch",
            "error",
            "violation",
            if location == "/request" {
                None
            } else {
                request_key
            },
            location,
            if location == "/request" {
                None
            } else {
                Some(semantic_type)
            },
            EXPECTED,
            OBSERVED,
            REMEDIATION,
            None,
        ));
        return;
    }
    let diagnostic_key = if location == "/request" {
        None
    } else {
        request_key
    };
    let diagnostic_type = if location == "/request" {
        None
    } else {
        Some(semantic_type)
    };
    if qualification.get("contract_version").and_then(Json::as_str) != Some("1.0") {
        diagnostics.push(diag(
            "authoring_construction.custom.authority_unavailable",
            "warning",
            "unavailable",
            diagnostic_key,
            location,
            diagnostic_type,
            EXPECTED,
            "required authority is unavailable",
            REMEDIATION,
            None,
        ));
        return;
    }
    let Some(_custom_basis) = root
        .get("basis")
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("custom_entity"))
        .and_then(Json::as_object)
    else {
        diagnostics.push(diag(
            "authoring_construction.custom.authority_unavailable",
            "warning",
            "unavailable",
            diagnostic_key,
            location,
            diagnostic_type,
            EXPECTED,
            "required authority is unavailable",
            REMEDIATION,
            None,
        ));
        return;
    };
    if semantic_kind == "relationship" {
        return;
    }
    if root
        .get("basis")
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("provenance"))
        .and_then(Json::as_object)
        .and_then(|provenance| provenance.get("registry_selection"))
        .and_then(Json::as_str)
        == Some("latest")
    {
        return;
    }
    if custom_definition_for(root, semantic_type, raw_qualification).is_none() {
        diagnostics.push(diag(
            "authoring_construction.custom.authority_unavailable",
            "warning",
            "unavailable",
            diagnostic_key,
            location,
            diagnostic_type,
            EXPECTED,
            "required authority is unavailable",
            REMEDIATION,
            None,
        ));
    }
}

fn custom_definition_for(
    root: &BTreeMap<String, Json>,
    semantic_type: &str,
    raw_qualification: Option<&Json>,
) -> Option<Json> {
    let qualification = raw_qualification.and_then(Json::as_object)?;
    let custom_basis = root
        .get("basis")
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("custom_entity"))
        .and_then(Json::as_object)?;
    if qualification.get("semantic_type").and_then(Json::as_str) != Some(semantic_type)
        || qualification.get("contract_version").and_then(Json::as_str) != Some("1.0")
    {
        return None;
    }
    let selected = custom_basis
        .get("selected_definitions")
        .and_then(Json::as_array)?
        .iter()
        .find(|candidate| {
            let Some(candidate) = candidate.as_object() else {
                return false;
            };
            [
                "semantic_kind",
                "semantic_type",
                "consumer_namespace",
                "contract_version",
                "contract_fingerprint",
            ]
            .iter()
            .all(|field| candidate.get(*field) == qualification.get(*field))
        })?;
    let source = custom_basis
        .get("registry_source")
        .and_then(Json::as_object)?;
    if !source_descriptor_integrity(source) {
        return None;
    }
    let encoded = source.get("source_bytes").and_then(Json::as_str)?;
    let bytes = decode_base64(encoded)?;
    let registry = serde_json::from_slice::<Json>(&bytes).ok()?;
    let resources = BTreeMap::from([(
        "custom-entity/1.0/schema".to_owned(),
        serde_json::from_str::<Json>(CUSTOM_ENTITY_SCHEMA).ok()?,
    )]);
    schema_validation::validate(&resources, "custom-entity/1.0/schema", &registry).ok()?;
    let definitions = registry
        .get("definitions")
        .and_then(Json::as_array)?;
    let (definition_index, definition) = definitions.iter().enumerate().find(|(_, definition)| {
        let Some(definition) = definition.as_object() else {
            return false;
        };
        [
            "semantic_kind",
            "semantic_type",
            "consumer_namespace",
            "contract_version",
            "contract_fingerprint",
        ]
        .iter()
        .all(|field| definition.get(*field) == qualification.get(*field))
    })?;
    let definition_object = definition.as_object()?.clone();
    let source_ref = source.get("source_ref").and_then(Json::as_str)?;
    let selected_source = selected
        .get("definition_source")
        .and_then(Json::as_str)?;
    if selected_source != format!("{source_ref}#/definitions/{definition_index}") {
        return None;
    }
    let selected_digest = selected
        .get("definition_digest")
        .and_then(Json::as_str)?;
    if selected_digest != canonical_json_digest(&Json::Object(definition_object.clone()))? {
        return None;
    }
    let declared_fingerprint = definition_object
        .get("contract_fingerprint")
        .and_then(Json::as_str)?;
    let mut preimage_definition = definition_object.clone();
    preimage_definition.remove("contract_fingerprint");
    let preimage = object([
        (
            "scheme".into(),
            string("adr-kit.custom-entity-contract/v1"),
        ),
        (
            "definition".into(),
            Json::Object(preimage_definition),
        ),
    ]);
    let canonical_preimage = semantic_contract::canonicalize(&object([(
        "value".into(),
        preimage,
    )]));
    let calculated = canonical_preimage
        .get("fingerprint")
        .and_then(Json::as_str)?;
    if declared_fingerprint != format!("cecf:v1:{calculated}") {
        return None;
    }
    Some(Json::Object(definition_object))
}

fn canonical_json_digest(value: &Json) -> Option<String> {
    semantic_contract::canonicalize(&object([("value".into(), value.clone())]))
        .get("fingerprint")
        .and_then(Json::as_str)
        .map(ToOwned::to_owned)
}

fn validate_relationship(
    relationship: &Json,
    index: usize,
    request_fragments: &BTreeMap<String, &Json>,
    root: &BTreeMap<String, Json>,
    custom_counts: &mut BTreeMap<String, (usize, Option<String>, Option<String>)>,
    diagnostics: &mut Vec<Json>,
) {
    let Some(value) = relationship.as_object() else {
        return;
    };
    let key = value.get("relationship_key").and_then(Json::as_str);
    let semantic_type = value.get("relationship_type").and_then(Json::as_str);
    let location = format!("/request/relationships/{index}");
    let forbidden = matches!(
        semantic_type,
        Some("relationship/consumes_interface") | Some("relationship/composed_of")
    );
    if semantic_type.is_some_and(|value| value.contains(':')) {
        validate_custom_qualification(
            "relationship",
            semantic_type.expect("custom relationship type is present"),
            value.get("qualification"),
            key,
            &location,
            root,
            diagnostics,
        );
    }
    if semantic_type == Some("relationship/consumes_interface") {
        diagnostics.push(diag(
            "authoring_construction.relationship.forbidden_type",
            "error",
            "violation",
            key,
            &location,
            semantic_type,
            EXPECTED,
            OBSERVED,
            REMEDIATION,
            None,
        ));
    }
    if semantic_type == Some("relationship/composed_of") {
        diagnostics.push(diag(
            "authoring_construction.relationship.direct_composed_of_forbidden",
            "error",
            "violation",
            key,
            &location,
            semantic_type,
            EXPECTED,
            OBSERVED,
            REMEDIATION,
            None,
        ));
    }
    let source = resolve_endpoint(value.get("source"), request_fragments, root);
    let target = resolve_endpoint(value.get("target"), request_fragments, root);
    let unresolved = source.is_none() || target.is_none();
    if unresolved && !forbidden {
        let code = "authoring_construction.reference.endpoint_unresolved";
        diagnostics.push(diag(
            code,
            "warning",
            "unresolved",
            key,
            &location,
            semantic_type,
            EXPECTED,
            "reference remains unresolved",
            REMEDIATION,
            None,
        ));
        if source.is_none() && target.is_none() {
            diagnostics.push(diag(
                "authoring_construction.relationship.type_check_blocked",
                "warning",
                "blocked",
                key,
                &location,
                semantic_type,
                BLOCKED_EXPECTED,
                OBSERVED,
                BLOCKED_REMEDIATION,
                Some(vec![code.to_owned()]),
            ));
            diagnostics.push(diag(
                "authoring_construction.relationship.cardinality_check_blocked",
                "warning",
                "blocked",
                key,
                &location,
                semantic_type,
                BLOCKED_EXPECTED,
                OBSERVED,
                BLOCKED_REMEDIATION,
                Some(vec![code.to_owned()]),
            ));
        }
        return;
    }
    if forbidden {
        return;
    }

    let Some(semantic_type) = semantic_type else {
        return;
    };
    if semantic_type.contains(':') {
        let Some(definition) = custom_definition_for(
            root,
            semantic_type,
            value.get("qualification"),
        ) else {
            diagnostics.push(diag(
                "authoring_construction.custom.authority_unavailable",
                "warning",
                "unavailable",
                key,
                &location,
                Some(semantic_type),
                "exact custom registry and selected definition authority",
                "resolved custom relationship semantics are not present in the exact supplied registry",
                "Supply the exact custom registry bytes and selected definition required by the relationship qualification.",
                None,
            ));
            return;
        };
        if !custom_endpoint_type_allowed(definition.get("source_types"), source.as_deref())
            || !custom_endpoint_type_allowed(definition.get("target_types"), target.as_deref())
        {
            diagnostics.push(diag(
                "authoring_construction.relationship.endpoint_forbidden",
                "error",
                "violation",
                key,
                &location,
                Some(semantic_type),
                "relationship endpoints satisfy the exact custom definition",
                "resolved endpoint type is not admitted by the custom relationship definition",
                REMEDIATION,
                None,
            ));
            return;
        }
        let Some(cardinality) = definition.get("cardinality").and_then(Json::as_object) else {
            return;
        };
        let maximum = cardinality.get("maximum");
        if maximum.is_some_and(|value| !matches!(value, Json::Null)) {
            let signature = format!(
                "{semantic_type}|{}|{}",
                source.as_deref().unwrap_or(""),
                target.as_deref().unwrap_or(""),
            );
            if let Some((first_index, first_key, first_type)) = custom_counts.get(&signature) {
                diagnostics.push(diag(
                    "authoring_construction.relationship.cardinality",
                    "error",
                    "violation",
                    first_key.as_deref(),
                    &format!("/request/relationships/{first_index}"),
                    first_type.as_deref(),
                    EXPECTED,
                    OBSERVED,
                    REMEDIATION,
                    None,
                ));
            } else {
                custom_counts.insert(
                    signature,
                    (
                        index,
                        key.map(ToOwned::to_owned),
                        Some(semantic_type.to_owned()),
                    ),
                );
            }
        }
    }
}

fn resolve_endpoint(
    endpoint: Option<&Json>,
    request_fragments: &BTreeMap<String, &Json>,
    root: &BTreeMap<String, Json>,
) -> Option<String> {
    let endpoint = endpoint?.as_object()?;
    let target = endpoint.get("target")?.as_str()?;
    match endpoint.get("kind").and_then(Json::as_str) {
        Some("request") => request_fragments
            .get(target)
            .and_then(|fragment| fragment.get("semantic_type"))
            .and_then(Json::as_str)
            .map(ToOwned::to_owned),
        Some("reference") => root
            .get("basis")
            .and_then(Json::as_object)
            .and_then(|basis| basis.get("reference_basis"))
            .and_then(Json::as_object)
            .and_then(|basis| basis.get("entries"))
            .and_then(Json::as_array)
            .and_then(|entries| {
                entries.iter().find_map(|entry| {
                    let entry = entry.as_object()?;
                    if entry.get("reference_id").and_then(Json::as_str) != Some(target) {
                        return None;
                    }
                    if entry
                        .get("source_basis")
                        .map(|source| source.as_object().is_some_and(source_descriptor_integrity))
                        .unwrap_or(true)
                    {
                        entry.get("semantic_type").and_then(Json::as_str)
                    } else {
                        None
                    }
                })
            })
            .map(ToOwned::to_owned),
        Some("topology") => None,
        _ => None,
    }
}

fn custom_endpoint_type_allowed(definition: Option<&Json>, resolved_type: Option<&str>) -> bool {
    let Some(resolved_type) = resolved_type else {
        return false;
    };
    definition
        .and_then(Json::as_array)
        .is_some_and(|allowed| {
            allowed.iter().any(|candidate| {
                candidate
                    .get("semantic_type")
                    .and_then(Json::as_str)
                    .is_some_and(|value| value == resolved_type)
                    || (candidate
                        .get("endpoint_kind")
                        .and_then(Json::as_str)
                        == Some("canonical_entity")
                        && candidate
                            .get("semantic_type")
                            .and_then(Json::as_str)
                            .is_some_and(|value| value == resolved_type))
            })
        })
}

fn diag(
    code: &str,
    severity: &str,
    status: &str,
    request_key: Option<&str>,
    location: &str,
    semantic_type: Option<&str>,
    expected: &str,
    observed: &str,
    remediation: &str,
    blocked_by: Option<Vec<String>>,
) -> Json {
    let mut values = BTreeMap::new();
    values.insert("code".into(), string(code));
    values.insert("severity".into(), string(severity));
    values.insert("status".into(), string(status));
    values.insert(
        "request_key".into(),
        request_key.map_or(Json::Null, |v| string(v)),
    );
    values.insert("location".into(), string(location));
    values.insert(
        "semantic_type".into(),
        semantic_type.map_or(Json::Null, |v| string(v)),
    );
    values.insert("rule".into(), string(format!("{ACC_RULE_PREFIX}{code}")));
    values.insert("expected".into(), string(expected));
    values.insert("observed".into(), string(observed));
    values.insert("remediation".into(), string(remediation));
    if let Some(blocked_by) = blocked_by {
        values.insert(
            "blocked_by".into(),
            Json::Array(blocked_by.into_iter().map(string).collect()),
        );
    }
    Json::Object(values)
}

fn report(mut diagnostics: Vec<Json>) -> ValidationReport {
    diagnostics.sort_by(|left, right| {
        let key = |item: &Json| {
            let object = item.as_object();
            (
                object
                    .and_then(|v| v.get("request_key"))
                    .and_then(Json::as_str)
                    .unwrap_or("")
                    .to_owned(),
                object
                    .and_then(|v| v.get("location"))
                    .and_then(Json::as_str)
                    .unwrap_or("")
                    .to_owned(),
                diagnostic_rank(
                    object
                        .and_then(|v| v.get("code"))
                        .and_then(Json::as_str)
                        .unwrap_or(""),
                ),
                object
                    .and_then(|v| v.get("code"))
                    .and_then(Json::as_str)
                    .unwrap_or("")
                    .to_owned(),
                serde_json::to_string(item).expect("diagnostic JSON is serializable"),
            )
        };
        key(left).cmp(&key(right))
    });
    let status = if diagnostics
        .iter()
        .any(|item| item.get("status").and_then(Json::as_str) == Some("violation"))
    {
        ValidationStatus::Invalid
    } else if diagnostics
        .iter()
        .any(|item| item.get("status").and_then(Json::as_str) == Some("unavailable"))
    {
        ValidationStatus::Unavailable
    } else if diagnostics
        .iter()
        .any(|item| item.get("status").and_then(Json::as_str) == Some("unresolved"))
    {
        ValidationStatus::Unresolved
    } else {
        ValidationStatus::Valid
    };
    ValidationReport {
        status,
        diagnostics,
    }
}

fn diagnostic_rank(code: &str) -> u8 {
    match code {
        "authoring_construction.reference.endpoint_unresolved" => 0,
        "authoring_construction.relationship.type_check_blocked" => 1,
        "authoring_construction.relationship.cardinality_check_blocked" => 2,
        "authoring_construction.identity.invalid_uuidv7"
        | "authoring_construction.identity.update_requires_existing" => 0,
        "authoring_construction.field.forbidden" => 1,
        "authoring_construction.field.unknown" => 2,
        _ => 3,
    }
}

fn is_uuid_v7(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 36
        && [8, 13, 18, 23].iter().all(|index| bytes[*index] == b'-')
        && bytes[14] == b'7'
        && matches!(bytes[19], b'8' | b'9' | b'a' | b'b')
        && bytes
            .iter()
            .enumerate()
            .all(|(index, byte)| [8, 13, 18, 23].contains(&index) || byte.is_ascii_hexdigit())
}
