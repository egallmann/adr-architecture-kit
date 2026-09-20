//! Canonical ACC 1.0 validation authority.
//!
//! This module deliberately does not implement a semantic-core 1.2 operation.
//! It is an internal, deterministic validation primitive that both a future
//! `validate_authoring` operation and a future construction operation will
//! consume.  Hosts supply the already-normalized ACC document; this module
//! performs no discovery, persistence, or construction.

use std::collections::{BTreeMap, BTreeSet};

use super::{object, schema_validation, semantic_contract, string, Json};

const ACC_SCHEMA: &str = include_str!("../../contracts/authoring-construction/v1.0/schema.json");
const ACC_CONTRACT: &str =
    include_str!("../../contracts/authoring-construction/v1.0/contract.json");
const ADC_CONTRACT: &str = include_str!("../../contracts/authoring-domain/v1.1/contract.json");
const AUTHORING_COMMON_SCHEMA: &str =
    include_str!("../../schema/authoring/v1.7/adr-common.schema.json");
const ARCHITECTURE_INTERPRETATION_CONTRACT: &str =
    include_str!("../../contracts/architecture-interpretation/v1.1/contract.json");
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
    let mut request_keys = BTreeSet::new();
    for fragment in fragments {
        if let Some(fragment_object) = fragment.as_object() {
            if let Some(key) = fragment_object.get("request_key").and_then(Json::as_str) {
                request_keys.insert(key.to_owned());
            }
        }
    }

    for (index, fragment) in fragments.iter().enumerate() {
        validate_fragment(fragment, index, operation, root, &mut diagnostics);
        if fragment
            .as_object()
            .and_then(|value| value.get("operation"))
            .and_then(Json::as_str)
            == Some("update")
            && fragment
                .as_object()
                .and_then(|value| value.get("fields"))
                .and_then(Json::as_object)
                .is_some_and(|fields| fields.contains_key("id"))
            && root
                .get("basis")
                .and_then(Json::as_object)
                .and_then(|basis| basis.get("existing_source_basis"))
                .and_then(Json::as_object)
                .and_then(|basis| basis.get("entries"))
                .and_then(Json::as_array)
                .is_some_and(|entries| entries.is_empty())
        {
            let value = fragment.as_object().expect("fragment is an object");
            diagnostics.push(diag(
                "authoring_construction.basis.existing_source_unavailable",
                "warning",
                "unavailable",
                value.get("request_key").and_then(Json::as_str),
                &format!("/request/fragments/{index}"),
                value.get("semantic_type").and_then(Json::as_str),
                "active bounded existing source entry",
                "sealed existing source basis contains no matching entry",
                "Supply the exact bounded existing source entry before constructing an update.",
                None,
            ));
        }
    }

    let mut relationship_signatures = BTreeMap::new();
    for (index, relationship) in relationships.iter().enumerate() {
        validate_relationship(
            relationship,
            index,
            &request_keys,
            root,
            &mut relationship_signatures,
            &mut diagnostics,
        );
    }

    for (index, fragment) in fragments.iter().enumerate() {
        validate_fragment_references(fragment, index, root, &mut diagnostics);
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

    if value.get("operation").and_then(Json::as_str) == Some("update")
        && fields.map_or(true, |f| !f.contains_key("id"))
    {
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
    }

    if let Some(fields) = fields {
        if let Some(id) = fields.get("id").and_then(Json::as_str) {
            if !is_uuid_v7(id) {
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
    }
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
        let match_entry = entries.iter().any(|entry| {
            entry
                .as_object()
                .and_then(|entry| entry.get("reference_id"))
                .and_then(Json::as_str)
                == Some(target)
        });
        let location = format!("/request/fragments/{index}/references/{reference_index}");
        if !match_entry {
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
        } else if semantic_type.map_or(false, |value| value.contains(':'))
            && root
                .get("basis")
                .and_then(Json::as_object)
                .and_then(|basis| basis.get("custom_entity"))
                .is_none_or(|value| matches!(value, Json::Null))
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
    if qualification.get("contract_version").and_then(Json::as_str) != Some("1.0") {
        diagnostics.push(diag(
            "authoring_construction.custom.authority_unavailable",
            "warning",
            "unavailable",
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
            "required authority is unavailable",
            REMEDIATION,
            None,
        ));
    }
    let Some(custom_basis) = root
        .get("basis")
        .and_then(Json::as_object)
        .and_then(|basis| basis.get("custom_entity"))
        .and_then(Json::as_object)
    else {
        diagnostics.push(diag(
            "authoring_construction.custom.authority_unavailable",
            "warning",
            "unavailable",
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
            "required authority is unavailable",
            REMEDIATION,
            None,
        ));
        return;
    };
    let selected = custom_basis
        .get("selected_definitions")
        .and_then(Json::as_array)
        .is_some_and(|definitions| {
            definitions.iter().any(|definition| {
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
            })
        });
    if !selected {
        diagnostics.push(diag(
            "authoring_construction.custom.authority_unavailable",
            "warning",
            "unavailable",
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
            "required authority is unavailable",
            REMEDIATION,
            None,
        ));
    }
}

fn validate_relationship(
    relationship: &Json,
    index: usize,
    request_keys: &BTreeSet<String>,
    root: &BTreeMap<String, Json>,
    signatures: &mut BTreeMap<String, (usize, Option<String>, Option<String>)>,
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
    let endpoint_key = |field: &str| {
        value
            .get(field)
            .and_then(Json::as_object)
            .map(|endpoint| {
                format!(
                    "{}:{}",
                    endpoint.get("kind").and_then(Json::as_str).unwrap_or(""),
                    endpoint.get("target").and_then(Json::as_str).unwrap_or("")
                )
            })
            .unwrap_or_default()
    };
    let from = endpoint_key("source");
    let to = endpoint_key("target");
    if forbidden {
        return;
    }
    let signature = format!("{semantic_type:?}|{from}|{to}");
    if let Some((first_index, first_key, first_type)) = signatures.get(&signature) {
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
        signatures.insert(
            signature,
            (
                index,
                key.map(ToOwned::to_owned),
                semantic_type.map(ToOwned::to_owned),
            ),
        );
    }
    let unresolved = [from.as_str(), to.as_str()]
        .iter()
        .filter(|endpoint| {
            let mut parts = endpoint.splitn(2, ':');
            let kind = parts.next().unwrap_or("");
            let target = parts.next().unwrap_or("");
            matches!(kind, "request" | "reference") && !request_keys.contains(target)
        })
        .count();
    if unresolved > 0 {
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
        if unresolved == 2 {
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
    }
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
