//! Explicit architecture-materialization@1.1 execution.
//!
//! This module is only the protocol adapter around the retained semantic
//! contract resolver and the already-landed Architecture Interpretation 1.1
//! assembler.  It does not interpret authoring fields or manufacture a
//! second normalized model implementation.

use std::collections::BTreeMap;

use super::architecture_interpretation::{
    assemble_normalized_interpretations, interpret_document, InterpretationSourceContext,
    NormalizedOutputContext,
};
use super::materialization;
use super::schema_validation;
use super::semantic_contract::sort_diagnostics;
use super::semantic_contract_set::resolve_exact_set;
use super::{diagnostic, string, Json};

const OPERATION: &str = "materialize_architecture";
const MATERIALIZATION_VERSION: &str = "1.1";
const EXPECTED_PROFILE: &str = "architecture-materialization@1.1";
const EXPECTED_SCS: &str =
    "scs:v1:sha256:2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020";

fn text(value: Option<&Json>) -> Option<String> {
    value.and_then(Json::as_str).map(str::to_owned)
}

fn object(entries: impl IntoIterator<Item = (&'static str, Json)>) -> Json {
    Json::Object(
        entries
            .into_iter()
            .map(|(key, value)| (key.to_owned(), value))
            .collect(),
    )
}

fn diagnostic_code(
    diagnostics: &mut Vec<Json>,
    code: &str,
    message: impl Into<String>,
    path: &str,
) {
    diagnostics.push(diagnostic(code, message, Some(path.to_owned())));
}

fn source_schema_resources() -> BTreeMap<String, Json> {
    [
        (
            "authoring/1.7/schema/adr-common.schema",
            include_str!("../../schema/authoring/v1.7/adr-common.schema.json"),
        ),
        (
            "authoring/1.7/schema/adr-logical.schema",
            include_str!("../../schema/authoring/v1.7/adr-logical.schema.json"),
        ),
        (
            "authoring/1.7/schema/adr-physical-base.schema",
            include_str!("../../schema/authoring/v1.7/adr-physical-base.schema.json"),
        ),
        (
            "authoring/1.7/schema/adr-physical-component.schema",
            include_str!("../../schema/authoring/v1.7/adr-physical-component.schema.json"),
        ),
        (
            "authoring/1.7/schema/adr-physical-system.schema",
            include_str!("../../schema/authoring/v1.7/adr-physical-system.schema.json"),
        ),
        (
            "authoring/1.7/schema/types.schema",
            include_str!("../../schema/authoring/v1.7/types.schema.json"),
        ),
    ]
    .into_iter()
    .map(|(key, raw)| {
        (
            key.to_owned(),
            serde_json::from_str(raw).expect("canonical authoring 1.7 schema is valid JSON"),
        )
    })
    .collect()
}

fn expected_source_keys(adr_type: &str) -> Option<Vec<String>> {
    let top_level = match adr_type {
        "logical" => "adr-logical.schema",
        "physical-system" => "adr-physical-system.schema",
        "physical-component" => "adr-physical-component.schema",
        _ => return None,
    };
    let mut keys = vec![
        "authoring/1.7/schema/adr-common.schema".to_owned(),
        "authoring/1.7/schema/types.schema".to_owned(),
        format!("authoring/1.7/schema/{top_level}"),
    ];
    if adr_type.starts_with("physical-") {
        keys.push("authoring/1.7/schema/adr-physical-base.schema".to_owned());
    }
    keys.sort();
    Some(keys)
}

fn validate_source_artifact(
    artifact: &Json,
    index: usize,
    provider_key: &str,
    source_resources: &BTreeMap<String, Json>,
    diagnostics: &mut Vec<Json>,
) -> Option<(Json, Json, String, String)> {
    let path = format!("sourceBasis.artifacts[{index}]");
    let value = artifact.as_object()?;
    let source_ref = text(value.get("sourceRef")).unwrap_or_default();
    let artifact_path = text(value.get("artifactPath")).unwrap_or_default();
    let content_digest = text(value.get("contentDigest")).unwrap_or_default();
    let document = value.get("document")?.clone();
    let document_object = document.as_object()?;
    let adr_type = text(document_object.get("adr_type")).unwrap_or_default();
    let Some(expected_keys) = expected_source_keys(&adr_type) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_source_document",
            "authoring 1.7 document has an unsupported adr_type",
            &format!("{path}.document.adr_type"),
        );
        return None;
    };
    let Some(binding) = value.get("sourceContract").and_then(Json::as_object) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_qualification_required",
            "source artifact requires an exact authoring 1.7 source-contract binding",
            &format!("{path}.sourceContract"),
        );
        return None;
    };
    if text(binding.get("family")).as_deref() != Some("authoring")
        || text(binding.get("version")).as_deref() != Some("1.7")
    {
        diagnostic_code(
            diagnostics,
            "semantic_contract.unsupported_source_contract",
            "protocol 1.3 forward materialization requires authoring@1.7",
            &format!("{path}.sourceContract"),
        );
        return None;
    }
    let Some(schema_resource) = binding.get("schemaResource").and_then(Json::as_object) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_schema_unqualified",
            "source contract requires its exact top-level schema resource",
            &format!("{path}.sourceContract.schemaResource"),
        );
        return None;
    };
    let schema_key = text(schema_resource.get("canonicalResourceKey")).unwrap_or_default();
    let schema_digest = text(schema_resource.get("contentDigest")).unwrap_or_default();
    let expected_top_level = expected_keys
        .iter()
        .find(|key| {
            key.ends_with(match adr_type.as_str() {
                "logical" => "adr-logical.schema",
                "physical-system" => "adr-physical-system.schema",
                "physical-component" => "adr-physical-component.schema",
                _ => "",
            })
        })
        .cloned()
        .unwrap_or_default();
    if schema_key != expected_top_level {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_schema_mismatch",
            "schemaResource is not the exact authoring 1.7 schema for adr_type",
            &format!("{path}.sourceContract.schemaResource.canonicalResourceKey"),
        );
    }
    let Some(raw_closure) = binding.get("resourceClosure").and_then(Json::as_array) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_closure_mismatch",
            "source contract requires its complete authoring 1.7 resource closure",
            &format!("{path}.sourceContract.resourceClosure"),
        );
        return None;
    };
    let mut supplied = BTreeMap::new();
    for (closure_index, raw_resource) in raw_closure.iter().enumerate() {
        let resource_path = format!("{path}.sourceContract.resourceClosure[{closure_index}]");
        let Some(resource) = raw_resource.as_object() else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_invalid",
                "source contract closure entry must be an object",
                &resource_path,
            );
            continue;
        };
        let key = text(resource.get("canonicalResourceKey")).unwrap_or_default();
        let digest = text(resource.get("contentDigest")).unwrap_or_default();
        if supplied.insert(key.clone(), digest.clone()).is_some() {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_duplicate",
                "source contract closure cannot repeat a resource identity",
                &resource_path,
            );
        }
        let Some(content) = source_resources.get(&key) else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_unqualified",
                "source contract closure contains a resource outside the canonical authoring 1.7 basis",
                &resource_path,
            );
            continue;
        };
        let expected_digest = materialization::digest_json(content).unwrap_or_default();
        if digest != expected_digest {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_digest_mismatch",
                "source contract closure digest does not match canonical authoring 1.7 bytes",
                &format!("{resource_path}.contentDigest"),
            );
        }
    }
    let expected = expected_keys
        .iter()
        .filter_map(|key| {
            source_resources
                .get(key)
                .and_then(|content| materialization::digest_json(content).ok())
                .map(|digest| (key.clone(), digest))
        })
        .collect::<BTreeMap<_, _>>();
    if supplied != expected {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_closure_mismatch",
            "source contract closure must exactly match the applicable authoring 1.7 schema imports",
            &format!("{path}.sourceContract.resourceClosure"),
        );
    }
    if let Some(content) = source_resources.get(&schema_key) {
        if let Err(error) = schema_validation::validate(source_resources, &schema_key, &document) {
            diagnostic_code(
                diagnostics,
                "semantic_contract.invalid_source_document",
                error.message,
                &if error.path.is_empty() {
                    format!("{path}.document")
                } else {
                    format!("{path}.document.{}", error.path)
                },
            );
        }
        let expected_digest = materialization::digest_json(content).unwrap_or_default();
        if schema_digest != expected_digest {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_schema_digest_mismatch",
                "schemaResource digest does not match canonical authoring 1.7 bytes",
                &format!("{path}.sourceContract.schemaResource.contentDigest"),
            );
        }
    }
    if source_ref.is_empty() || artifact_path.is_empty() || content_digest.is_empty() {
        diagnostic_code(
            diagnostics,
            "semantic_contract.incomplete_source_artifact",
            "sourceRef, artifactPath, and contentDigest are required",
            &path,
        );
    }
    if text(document_object.get("schema_version")).as_deref() != Some("1.7") {
        diagnostic_code(
            diagnostics,
            "semantic_contract.artifact_contract_mismatch",
            "document schema_version must be 1.7",
            &format!("{path}.document.schema_version"),
        );
    }
    if source_ref.is_empty() || artifact_path.is_empty() {
        return None;
    }
    let source_contract = Json::Object(binding.clone());
    if provider_key.is_empty() {
        return None;
    }
    Some((document, source_contract, schema_key, content_digest))
}

fn result(
    outcome: &str,
    authority_provider: Json,
    source_basis: Json,
    source_contract_closure: Vec<Json>,
    set_id: Option<String>,
    fingerprint: Option<String>,
    normalized_model: Json,
    provenance: Json,
    mut diagnostics: Vec<Json>,
) -> Json {
    sort_diagnostics(&mut diagnostics);
    object([
        // The protocol-1.3 envelope owns these fields; the nested result is
        // the materialization-contract payload defined by the retained
        // semantic-core contract.
        ("operation", string(OPERATION)),
        ("success", Json::Bool(outcome == "Materialized")),
        ("outcome", string(outcome)),
        (
            "materializationContractVersion",
            string(MATERIALIZATION_VERSION),
        ),
        ("authorityProvider", authority_provider),
        ("sourceBasis", source_basis),
        (
            "sourceContractClosure",
            Json::Array(source_contract_closure),
        ),
        (
            "semanticBasis",
            object([
                (
                    "semanticContractSetId",
                    set_id.map(string).unwrap_or(Json::Null),
                ),
                (
                    "authorityStateFingerprint",
                    fingerprint.map(string).unwrap_or(Json::Null),
                ),
            ]),
        ),
        ("normalizedModel", normalized_model),
        ("sourceCapabilityLimitations", Json::Array(Vec::new())),
        ("providerProvenance", provenance),
        ("diagnostics", Json::Array(diagnostics)),
    ])
}

fn failure_outcome(diagnostics: &[Json]) -> &'static str {
    if diagnostics.iter().any(|value| {
        text(value.as_object().and_then(|v| v.get("code"))).as_deref()
            == Some("semantic_contract.installed_execution_support_unavailable")
    }) {
        "Unavailable"
    } else {
        "Rejected"
    }
}

fn source_closure_from_basis(source_basis: &Json) -> Vec<Json> {
    let mut values = BTreeMap::new();
    if let Some(artifacts) = source_basis
        .as_object()
        .and_then(|value| value.get("artifacts"))
        .and_then(Json::as_array)
    {
        for artifact in artifacts {
            if let Some(binding) = artifact
                .as_object()
                .and_then(|value| value.get("sourceContract"))
            {
                let key = text(
                    binding
                        .as_object()
                        .and_then(|value| value.get("schemaResource"))
                        .and_then(Json::as_object)
                        .and_then(|value| value.get("canonicalResourceKey")),
                )
                .unwrap_or_default();
                values.entry(key).or_insert_with(|| binding.clone());
            }
        }
    }
    values.into_values().collect()
}

pub(crate) fn execute(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return result(
            "Rejected",
            Json::Null,
            Json::Null,
            Vec::new(),
            None,
            None,
            Json::Null,
            Json::Null,
            vec![diagnostic(
                "semantic_contract.materialization_request_invalid",
                "request must be an object",
                None,
            )],
        );
    };
    let Some(payload) = root.get("request").and_then(Json::as_object) else {
        return result(
            "Rejected",
            Json::Null,
            Json::Null,
            Vec::new(),
            None,
            None,
            Json::Null,
            Json::Null,
            vec![diagnostic(
                "core.invalid_request",
                "protocol 1.3 request payload must be an object",
                None,
            )],
        );
    };
    let request_value = Json::Object(payload.clone());
    let authority_provider = payload
        .get("authorityProvider")
        .cloned()
        .unwrap_or(Json::Null);
    let source_basis = payload.get("sourceBasis").cloned().unwrap_or(Json::Null);
    let provenance = payload
        .get("providerProvenance")
        .cloned()
        .unwrap_or(Json::Null);
    let source_closure = source_closure_from_basis(&source_basis);
    let requested_set_id = text(payload.get("semanticContractSetId"));
    let resolution = resolve_exact_set(&request_value, OPERATION);
    let resolution = match resolution {
        Ok(value) => value,
        Err(mut diagnostics) => {
            sort_diagnostics(&mut diagnostics);
            return result(
                failure_outcome(&diagnostics),
                authority_provider,
                source_basis,
                source_closure,
                requested_set_id,
                None,
                Json::Null,
                provenance,
                diagnostics,
            );
        }
    };
    if resolution.profile_id != EXPECTED_PROFILE || resolution.set_id != EXPECTED_SCS {
        return result(
            "Rejected",
            authority_provider,
            source_basis,
            source_closure,
            Some(resolution.set_id),
            None,
            Json::Null,
            provenance,
            vec![diagnostic(
                "semantic_contract.successor_authority_mismatch",
                "protocol 1.3 materialization requires the retained architecture-materialization@1.1 successor SCS",
                Some("semanticContractSetId".into()),
            )],
        );
    }
    let Some(provider) = authority_provider.as_object() else {
        return result(
            "Rejected",
            Json::Null,
            source_basis,
            source_closure,
            Some(resolution.set_id),
            None,
            Json::Null,
            provenance,
            vec![diagnostic(
                "semantic_contract.provider_identity_required",
                "authorityProvider is required",
                Some("authorityProvider".into()),
            )],
        );
    };
    let provider_kind = text(provider.get("kind")).unwrap_or_default();
    let architecture_namespace = text(provider.get("architectureNamespace")).unwrap_or_default();
    let provider_key = match materialization::provider_key(&provider_kind, &architecture_namespace)
    {
        Ok(value) => value,
        Err(error) => {
            return result(
                "Rejected",
                authority_provider,
                source_basis,
                source_closure,
                Some(resolution.set_id),
                None,
                Json::Null,
                provenance,
                vec![diagnostic(
                    "semantic_contract.provider_identity_required",
                    error,
                    Some("authorityProvider".into()),
                )],
            )
        }
    };
    if text(
        source_basis
            .as_object()
            .and_then(|value| value.get("providerSourceIdentity")),
    )
    .as_deref()
        != Some(provider_key.as_str())
    {
        return result(
            "Rejected",
            authority_provider,
            source_basis,
            source_closure,
            Some(resolution.set_id),
            None,
            Json::Null,
            provenance,
            vec![diagnostic(
                "semantic_contract.provider_identity_mismatch",
                "providerSourceIdentity must equal the canonical provider kind and architecture namespace",
                Some("sourceBasis.providerSourceIdentity".into()),
            )],
        );
    }
    let Some(artifacts) = source_basis
        .as_object()
        .and_then(|value| value.get("artifacts"))
        .and_then(Json::as_array)
    else {
        return result(
            "Rejected",
            authority_provider,
            source_basis,
            source_closure,
            Some(resolution.set_id),
            None,
            Json::Null,
            provenance,
            vec![diagnostic(
                "semantic_contract.incomplete_source_basis",
                "sourceBasis.artifacts must be an array",
                Some("sourceBasis.artifacts".into()),
            )],
        );
    };
    let source_resources = source_schema_resources();
    let mut diagnostics = Vec::new();
    let mut interpretations = Vec::new();
    let mut coverage = Vec::new();
    for (index, artifact) in artifacts.iter().enumerate() {
        let artifact_diagnostics_before = diagnostics.len();
        let Some((document, source_contract, source_schema, content_digest)) =
            validate_source_artifact(
                artifact,
                index,
                &provider_key,
                &source_resources,
                &mut diagnostics,
            )
        else {
            continue;
        };
        let artifact_object = artifact
            .as_object()
            .expect("validated source artifact object");
        let source_ref = text(artifact_object.get("sourceRef")).unwrap_or_default();
        let artifact_path = text(artifact_object.get("artifactPath")).unwrap_or_default();
        if diagnostics.len() == artifact_diagnostics_before {
            let source_context = InterpretationSourceContext {
                canonical_source_ref: source_ref,
                source_pointer: "/".into(),
            };
            let output_context = NormalizedOutputContext {
                architecture_namespace: architecture_namespace.clone(),
                provider_kind: provider_kind.clone(),
                artifact_path,
            };
            match interpret_document(
                &document,
                &source_context,
                &output_context,
                &source_contract,
                &source_schema,
                &content_digest,
            ) {
                Ok(interpretation) => {
                    coverage.push(
                        interpretation
                            .model
                            .as_object()
                            .and_then(|value| value.get("source_coverage"))
                            .cloned()
                            .unwrap_or(Json::Null),
                    );
                    interpretations.push(interpretation);
                }
                Err(error) => diagnostic_code(
                    &mut diagnostics,
                    "semantic_contract.architecture_interpretation_failed",
                    error,
                    &format!("sourceBasis.artifacts[{index}].document"),
                ),
            }
        }
    }
    if !diagnostics.is_empty() || interpretations.is_empty() {
        return result(
            "Rejected",
            authority_provider,
            source_basis,
            source_closure,
            Some(resolution.set_id),
            None,
            Json::Null,
            provenance,
            diagnostics,
        );
    }
    let model = match assemble_normalized_interpretations(
        &interpretations,
        &provider_key,
        &architecture_namespace,
        coverage,
    ) {
        Ok(value) => value,
        Err(error) => {
            return result(
                "Rejected",
                authority_provider,
                source_basis,
                source_closure,
                Some(resolution.set_id),
                None,
                Json::Null,
                provenance,
                vec![diagnostic(
                    "semantic_contract.normalized_model_assembly_failed",
                    error,
                    Some("normalizedModel".into()),
                )],
            )
        }
    };
    let Some(normalized_definition) = resolution.definitions.get("normalized-model") else {
        return result(
            "Rejected",
            authority_provider,
            source_basis,
            source_closure,
            Some(resolution.set_id),
            None,
            Json::Null,
            provenance,
            vec![diagnostic(
                "semantic_contract.missing_definition",
                "resolved successor normalized-model definition is missing",
                Some("definitions.normalized-model".into()),
            )],
        );
    };
    let normalized_resources = normalized_definition
        .resources
        .iter()
        .filter_map(|resource| {
            Some((
                text(resource.as_object()?.get("canonicalResourceKey"))?,
                resource.as_object()?.get("content")?.clone(),
            ))
        })
        .collect::<BTreeMap<_, _>>();
    if let Err(error) = schema_validation::validate(
        &normalized_resources,
        "normalized-model/2.4/schema/normalized-architecture-model.schema",
        &model,
    ) {
        return result(
            "Rejected",
            authority_provider,
            source_basis,
            source_closure,
            Some(resolution.set_id),
            None,
            Json::Null,
            provenance,
            vec![diagnostic(
                "semantic_contract.normalized_model_invalid",
                error.message,
                Some(if error.path.is_empty() {
                    "normalizedModel".into()
                } else {
                    format!("normalizedModel.{}", error.path)
                }),
            )],
        );
    }
    let fingerprint =
        materialization::authority_state_fingerprint(&authority_provider, &model, &[]);
    result(
        "Materialized",
        authority_provider,
        source_basis,
        source_closure,
        Some(resolution.set_id),
        Some(fingerprint),
        model,
        provenance,
        Vec::new(),
    )
}
