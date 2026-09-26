//! Internal ACC 1.0 construction coordinator.
//!
//! This is deliberately a Rust-only boundary.  It composes the existing ACC
//! validator, candidate-source authority, and Architecture Interpretation
//! authority without adding a protocol operation, persistence, discovery, or
//! any case-specific behavior.

use std::collections::BTreeMap;
use std::sync::atomic::{AtomicU16, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use sha2::{Digest, Sha256};

use super::{
    architecture_interpretation, authoring_construction, candidate_source, diagnostic, object,
    semantic_contract, string, Json,
};

const ACC_OPERATION: &str = "construct_authoring_set";
const ACC_FAMILY: &str = "authoring_construction";
const ACC_VERSION: &str = "1.0";

/// Identity is established before source rendering and interpretation.  The
/// trait keeps the boundary independently testable without making identity a
/// function of content, order, aliases, or source location.
pub(crate) trait IdentityMinter {
    fn mint_uuidv7(&mut self) -> Result<String, String>;
}

#[derive(Default)]
pub(crate) struct UuidV7Minter;

static UUID_COUNTER: AtomicU16 = AtomicU16::new(0);

impl IdentityMinter for UuidV7Minter {
    fn mint_uuidv7(&mut self) -> Result<String, String> {
        let millis = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|error| format!("system clock is before UNIX epoch: {error}"))?
            .as_millis() as u64;
        let counter = UUID_COUNTER.fetch_add(1, Ordering::Relaxed) & 0x0fff;
        let time_high = millis & 0x0000_ffff_ffff_ffff;
        Ok(format!(
            "{:08x}-{:04x}-7{:03x}-8{:03x}-{:012x}",
            time_high >> 16,
            time_high & 0xffff,
            counter,
            counter,
            (millis << 12 | counter as u64) & 0x0000_ffff_ffff_ffff,
        ))
    }
}

/// Construct an ACC request using the default detached identity authority.
/// This function is crate-visible only and is intentionally not reachable from
/// the semantic-core protocol dispatcher.
pub(crate) fn construct_authoring_set(request: &Json) -> Json {
    let mut minter = UuidV7Minter;
    construct_authoring_set_with_minter(request, &mut minter)
}

pub(crate) fn construct_authoring_set_with_minter(
    request: &Json,
    minter: &mut dyn IdentityMinter,
) -> Json {
    let validation = authoring_construction::validate_authoring_request(request);
    let root = request.as_object();
    let operation = root
        .and_then(|value| value.get("operation"))
        .and_then(Json::as_str)
        .unwrap_or(ACC_OPERATION);

    if operation == "validate_authoring" {
        return authoring_construction::render_validation_result(request, &validation);
    }

    let basis = root
        .and_then(|value| value.get("basis"))
        .cloned()
        .unwrap_or(Json::Null);
    let request_id = root
        .and_then(|value| value.get("request"))
        .and_then(Json::as_object)
        .and_then(|value| value.get("request_id"))
        .cloned()
        .unwrap_or(Json::Null);
    let provenance = provenance(root, request_id.clone());

    if validation.status != authoring_construction::ValidationStatus::Valid {
        let outcome = match validation.status {
            authoring_construction::ValidationStatus::Invalid => "Rejected",
            authoring_construction::ValidationStatus::Unavailable => "Unavailable",
            authoring_construction::ValidationStatus::Unresolved => "Unresolved",
            authoring_construction::ValidationStatus::Valid => unreachable!(),
        };
        return result(
            &basis,
            outcome,
            validation.diagnostics.clone(),
            provenance,
            Vec::new(),
            Vec::new(),
            Vec::new(),
            None,
            Json::Object(BTreeMap::from([
                ("qualified".into(), Json::Bool(false)),
                ("comparison".into(), string("not_evaluated")),
                ("authorized_differences".into(), Json::Array(Vec::new())),
                ("hidden_semantics".into(), Json::Array(Vec::new())),
                (
                    "diagnostic_codes".into(),
                    Json::Array(diagnostic_codes(&validation.diagnostics)),
                ),
            ])),
        )
        .value;
    }

    let Some(request_body) = root
        .and_then(|value| value.get("request"))
        .and_then(Json::as_object)
    else {
        return fail_closed(&basis, provenance, "authoring_construction.request.schema");
    };

    let fragments = request_body
        .get("fragments")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    let relationships = request_body
        .get("relationships")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    let compositions = request_body
        .get("compositions")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();

    let source_contract = basis.get("authoring").cloned().unwrap_or(Json::Null);
    let source_prefix = source_prefix(root, &request_id);
    let mut identities = BTreeMap::<String, Identity>::new();
    let mut diagnostics = Vec::new();
    for fragment in &fragments {
        let Some(value) = fragment.as_object() else {
            continue;
        };
        let Some(key) = value.get("request_key").and_then(Json::as_str) else {
            continue;
        };
        let operation = value
            .get("operation")
            .and_then(Json::as_str)
            .unwrap_or("create");
        let fields = value.get("fields").and_then(Json::as_object);
        let supplied = fields
            .and_then(|fields| fields.get("id"))
            .and_then(Json::as_str);
        let identity = match establish_identity(key, operation, supplied, minter) {
            Ok(identity) => identity,
            Err(error) => {
                diagnostics.push(orchestration_diagnostic(
                    "authoring_construction.identity.unavailable",
                    &error,
                    Some(key),
                    value.get("semantic_type").and_then(Json::as_str),
                    "unavailable",
                ));
                continue;
            }
        };
        identities.insert(key.to_owned(), identity);
    }
    for relationship in &relationships {
        let Some(value) = relationship.as_object() else {
            continue;
        };
        let Some(key) = value.get("relationship_key").and_then(Json::as_str) else {
            continue;
        };
        let fields = value.get("fields").and_then(Json::as_object);
        let supplied = fields
            .and_then(|fields| fields.get("id"))
            .and_then(Json::as_str);
        match establish_identity(key, "create", supplied, minter) {
            Ok(identity) => {
                identities.insert(key.to_owned(), identity);
            }
            Err(error) => diagnostics.push(orchestration_diagnostic(
                "authoring_construction.identity.unavailable",
                &error,
                Some(key),
                value.get("relationship_type").and_then(Json::as_str),
                "unavailable",
            )),
        }
    }
    if !diagnostics.is_empty() {
        return result(
            &basis,
            "Unavailable",
            diagnostics.clone(),
            provenance,
            Vec::new(),
            Vec::new(),
            Vec::new(),
            None,
            round_trip(false, "not_evaluated", &[], &[], &diagnostics),
        )
        .value;
    }

    let mut candidate_fragments = Vec::new();
    let mut candidate_artifacts = Vec::new();
    let mut construction_map = Vec::new();
    let mut interpretation_results = Vec::new();

    for fragment in &fragments {
        let Some(value) = fragment.as_object() else {
            continue;
        };
        let key = value
            .get("request_key")
            .and_then(Json::as_str)
            .unwrap_or_default();
        let semantic_kind = value
            .get("semantic_kind")
            .and_then(Json::as_str)
            .unwrap_or("value");
        let semantic_type = value
            .get("semantic_type")
            .and_then(Json::as_str)
            .unwrap_or_default();
        let qualification = value
            .get("contract_qualification")
            .cloned()
            .unwrap_or(Json::Null);
        let fields = value
            .get("fields")
            .and_then(Json::as_object)
            .cloned()
            .unwrap_or_default();
        let identity = identities.get(key).expect("validated identity exists");
        let source = build_fragment_source(
            value,
            &fields,
            identity,
            semantic_type,
            key,
            &identities,
            &fragments,
            &compositions,
        );
        let selector = selector_for(semantic_type, &source);
        let source_ref = format!("{source_prefix}/{key}");
        let artifact_kind = if semantic_kind == "adr" {
            "authoring_document"
        } else {
            "authoring_fragment"
        };
        let artifact = match candidate_source::seal_candidate_artifact(
            key,
            &source_ref,
            artifact_kind,
            selector,
            source_contract.clone(),
            &source,
        ) {
            Ok(artifact) => artifact,
            Err(error) => {
                diagnostics.push(orchestration_diagnostic(
                    "authoring_construction.candidate_source.unavailable",
                    &error,
                    Some(key),
                    Some(semantic_type),
                    "unavailable",
                ));
                continue;
            }
        };
        let interpretation = match interpret_artifact(&artifact) {
            Ok(value) => value,
            Err(error) => {
                diagnostics.push(orchestration_diagnostic(
                    "authoring_construction.interpretation.unavailable",
                    &error,
                    Some(key),
                    Some(semantic_type),
                    "unavailable",
                ));
                continue;
            }
        };
        interpretation_results.push((
            key.to_owned(),
            semantic_type.to_owned(),
            source.clone(),
            interpretation,
        ));
        candidate_artifacts.push(artifact_to_json(&artifact));
        candidate_fragments.push(candidate_fragment(
            value,
            &fields,
            identity,
            &qualification,
            &source_contract,
            &identities,
            &basis,
        ));
        construction_map.push(map_entry(
            key,
            value
                .get("operation")
                .and_then(Json::as_str)
                .unwrap_or("create"),
            semantic_type,
            identity,
            &qualification,
            &source_ref,
        ));
    }

    for relationship in &relationships {
        let Some(value) = relationship.as_object() else {
            continue;
        };
        let key = value
            .get("relationship_key")
            .and_then(Json::as_str)
            .unwrap_or_default();
        let semantic_type = value
            .get("relationship_type")
            .and_then(Json::as_str)
            .unwrap_or_default();
        let qualification = value.get("qualification").cloned().unwrap_or(Json::Null);
        let identity = identities
            .get(key)
            .expect("validated relationship identity exists");
        let source = build_relationship_source(value, identity, &identities);
        let source_ref = format!("{source_prefix}/{key}");
        let selector = candidate_source::CandidateSourceSelector {
            canonical_resource_key: "authoring/1.7/schema/adr-common.schema".into(),
            json_pointer: "/definitions/custom_relationship".into(),
        };
        let artifact = match candidate_source::seal_candidate_artifact(
            key,
            &source_ref,
            "authoring_fragment",
            selector,
            source_contract.clone(),
            &source,
        ) {
            Ok(artifact) => artifact,
            Err(error) => {
                diagnostics.push(orchestration_diagnostic(
                    "authoring_construction.candidate_source.unavailable",
                    &error,
                    Some(key),
                    Some(semantic_type),
                    "unavailable",
                ));
                continue;
            }
        };
        let interpretation = match interpret_artifact(&artifact) {
            Ok(value) => value,
            Err(error) => {
                diagnostics.push(orchestration_diagnostic(
                    "authoring_construction.interpretation.unavailable",
                    &error,
                    Some(key),
                    Some(semantic_type),
                    "unavailable",
                ));
                continue;
            }
        };
        interpretation_results.push((
            key.to_owned(),
            semantic_type.to_owned(),
            source.clone(),
            interpretation,
        ));
        candidate_artifacts.push(artifact_to_json(&artifact));
        candidate_fragments.push(relationship_fragment(
            value,
            identity,
            &qualification,
            &source_contract,
            &identities,
            &basis,
        ));
        construction_map.push(map_entry(
            key,
            "create",
            semantic_type,
            identity,
            &qualification,
            &source_ref,
        ));
    }

    if !diagnostics.is_empty() {
        return result(
            &basis,
            "Unavailable",
            diagnostics.clone(),
            provenance,
            construction_map,
            candidate_fragments,
            candidate_artifacts,
            None,
            round_trip(false, "not_evaluated", &[], &[], &diagnostics),
        )
        .value;
    }

    let artifacts_for_basis = candidate_artifacts
        .iter()
        .map(json_to_artifact)
        .collect::<Result<Vec<_>, _>>();
    let basis_artifacts =
        match artifacts_for_basis.and_then(candidate_source::seal_candidate_source_basis) {
            Ok(value) => value,
            Err(error) => {
                let diagnostic = orchestration_diagnostic(
                    "authoring_construction.candidate_source.unavailable",
                    &error,
                    None,
                    None,
                    "unavailable",
                );
                return result(
                    &basis,
                    "Unavailable",
                    vec![diagnostic.clone()],
                    provenance,
                    construction_map,
                    candidate_fragments,
                    candidate_artifacts,
                    None,
                    round_trip(false, "not_evaluated", &[], &[], &[diagnostic]),
                )
                .value;
            }
        };

    if let Some(mismatch) = round_trip_mismatch(&interpretation_results) {
        let diagnostic = orchestration_diagnostic(
            "authoring_construction.round_trip.semantic_mismatch",
            &mismatch,
            None,
            None,
            "violation",
        );
        let mismatch_result = object([
            ("normalized_contract".into(), normalized_contract(&basis)),
            (
                "semantic_digest".into(),
                digest_of(&object([("semantic_mismatch".into(), Json::Bool(true))])),
            ),
            (
                "model".into(),
                object([
                    ("request_id".into(), request_id.clone()),
                    ("semantic_mismatch".into(), Json::Bool(true)),
                ]),
            ),
        ]);
        return result(
            &basis,
            "Rejected",
            vec![diagnostic.clone()],
            provenance,
            Vec::new(),
            Vec::new(),
            candidate_artifacts,
            Some(basis_to_json(&basis_artifacts, &source_contract)),
            round_trip(
                false,
                "semantic_mismatch",
                &[],
                &["semantic_field_loss"],
                &[diagnostic],
            ),
        )
        .with_normalized(mismatch_result);
    }

    let normalized = normalized_result(&basis, &request_id, &candidate_fragments);
    result(
        &basis,
        "Constructed",
        Vec::new(),
        provenance,
        construction_map,
        candidate_fragments,
        candidate_artifacts,
        Some(basis_to_json(&basis_artifacts, &source_contract)),
        round_trip(
            true,
            "semantic_equivalent",
            &["deterministic_ceremony"],
            &[],
            &[],
        ),
    )
    .with_normalized(normalized)
}

#[derive(Clone)]
struct Identity {
    id: String,
    disposition: &'static str,
}

fn establish_identity(
    key: &str,
    operation: &str,
    supplied: Option<&str>,
    minter: &mut dyn IdentityMinter,
) -> Result<Identity, String> {
    if let Some(id) = supplied {
        return Ok(Identity {
            id: id.to_owned(),
            disposition: if operation == "reference" {
                "reused"
            } else {
                "preserved"
            },
        });
    }
    if operation == "update" {
        return Err(format!("update identity is absent for request key {key}"));
    }
    Ok(Identity {
        id: minter.mint_uuidv7()?,
        disposition: "minted",
    })
}

fn build_fragment_source(
    fragment: &BTreeMap<String, Json>,
    fields: &BTreeMap<String, Json>,
    identity: &Identity,
    semantic_type: &str,
    key: &str,
    identities: &BTreeMap<String, Identity>,
    fragments: &[Json],
    compositions: &[Json],
) -> Json {
    let mut output = fields.clone();
    output.insert("id".into(), string(identity.id.clone()));
    ceremony_alias(&mut output, semantic_type);
    if semantic_type.contains(':') {
        output.insert("entity_type".into(), string(semantic_type));
        output.insert(
            "qualification".into(),
            fragment
                .get("contract_qualification")
                .cloned()
                .unwrap_or(Json::Null),
        );
        output
            .entry("properties".into())
            .or_insert_with(|| object([]));
        output.entry("rationale".into()).or_insert_with(|| {
            string(
                if fragment.get("operation").and_then(Json::as_str) == Some("reference") {
                    "Reference source evidence."
                } else {
                    "Explicit."
                },
            )
        });
    }
    if semantic_type.starts_with("adr/") {
        output.insert("schema_version".into(), string("1.7"));
        if semantic_type == "adr/logical" {
            let children = compositions
                .iter()
                .filter_map(|value| value.as_object())
                .filter(|value| value.get("parent").and_then(Json::as_str) == Some(key))
                .filter_map(|value| value.get("child").and_then(Json::as_str))
                .filter_map(|child| {
                    let child_identity = identities.get(child)?;
                    let child_value = fragments.iter().find_map(|fragment| {
                        let value = fragment.as_object()?;
                        (value.get("request_key").and_then(Json::as_str) == Some(child))
                            .then_some(value)
                    })?;
                    let child_type = child_value
                        .get("semantic_type")
                        .and_then(Json::as_str)
                        .unwrap_or("entity/decision");
                    let mut child_source = child_value
                        .get("fields")
                        .and_then(Json::as_object)
                        .cloned()
                        .unwrap_or_default();
                    child_source.insert("id".into(), string(child_identity.id.clone()));
                    ceremony_alias(&mut child_source, child_type);
                    Some(Json::Object(child_source))
                })
                .collect::<Vec<_>>();
            if !children.is_empty() {
                output.insert("decisions".into(), Json::Array(children));
            }
        }
        if semantic_type == "adr/physical-system" {
            output.insert(
                "implements_logical".into(),
                Json::Array(vec![string(identity.id.clone())]),
            );
            output.insert(
                "system".into(),
                object([
                    ("id".into(), string(identity.id.clone())),
                    ("alias_id".into(), string("SYS-0001")),
                    (
                        "alias_name".into(),
                        output
                            .get("alias_name")
                            .cloned()
                            .unwrap_or_else(|| string("system")),
                    ),
                ]),
            );
            if let Some(topology) = output.get_mut("component_topology") {
                enrich_topology(topology);
            }
        }
    }
    Json::Object(output)
}

fn build_relationship_source(
    relationship: &BTreeMap<String, Json>,
    identity: &Identity,
    identities: &BTreeMap<String, Identity>,
) -> Json {
    let semantic_type = relationship
        .get("relationship_type")
        .and_then(Json::as_str)
        .unwrap_or_default();
    let relationship_fields = relationship
        .get("fields")
        .and_then(Json::as_object)
        .cloned()
        .unwrap_or_default();
    let mut output = BTreeMap::new();
    output.insert("id".into(), string(identity.id.clone()));
    output.insert("relationship_type".into(), string(semantic_type));
    output.insert(
        "qualification".into(),
        relationship
            .get("qualification")
            .cloned()
            .unwrap_or(Json::Null),
    );
    output.insert("alias_id".into(), string(alias_for(semantic_type)));
    output.insert("alias_name".into(), string(alias_name_for(semantic_type)));
    output.insert(
        "from_entity_id".into(),
        string(endpoint_id(relationship.get("source"), identities)),
    );
    output.insert(
        "to_entity_id".into(),
        string(endpoint_id(relationship.get("target"), identities)),
    );
    output.insert("properties".into(), Json::Object(relationship_fields));
    output
        .entry("rationale".into())
        .or_insert_with(|| string("Explicit relationship."));
    Json::Object(output)
}

fn ceremony_alias(fields: &mut BTreeMap<String, Json>, semantic_type: &str) {
    let alias = fields
        .get("alias_id")
        .and_then(Json::as_str)
        .map(ToOwned::to_owned)
        .unwrap_or_else(|| alias_for(semantic_type));
    let normalized = if alias.ends_with("-CONFORMANCE") {
        format!("{}-0001", alias.trim_end_matches("-CONFORMANCE"))
    } else {
        alias
    };
    fields.insert("alias_id".into(), string(normalized));
    if !fields.contains_key("alias_name") {
        fields.insert("alias_name".into(), string(alias_name_for(semantic_type)));
    }
}

fn alias_for(semantic_type: &str) -> String {
    let stem = semantic_type
        .split_once(':')
        .map(|(namespace, _)| namespace.to_owned())
        .or_else(|| {
            semantic_type
                .split_once('/')
                .map(|(_, name)| name.to_owned())
        })
        .unwrap_or_else(|| semantic_type.to_owned());
    format!("{}-0001", stem.to_ascii_uppercase().replace('_', "-"))
}

fn alias_name_for(semantic_type: &str) -> String {
    semantic_type
        .split_once(':')
        .map(|(_, value)| value.replace('_', "-"))
        .or_else(|| {
            semantic_type
                .split_once('/')
                .map(|(_, value)| value.to_owned())
        })
        .unwrap_or_else(|| semantic_type.to_owned())
}

fn endpoint_id(value: Option<&Json>, identities: &BTreeMap<String, Identity>) -> String {
    let Some(value) = value.and_then(Json::as_object) else {
        return String::new();
    };
    let target = value
        .get("target")
        .and_then(Json::as_str)
        .unwrap_or_default();
    identities
        .get(target)
        .map(|identity| identity.id.clone())
        .unwrap_or_default()
}

fn enrich_topology(value: &mut Json) {
    if let Some(topology) = value.as_object_mut() {
        if let Some(components) = topology.get_mut("components").and_then(Json::as_array_mut) {
            for component in components {
                if let Some(component) = component.as_object_mut() {
                    component
                        .entry("purpose".into())
                        .or_insert_with(|| string("Explicit topology component."));
                }
            }
        }
    }
}

fn selector_for(semantic_type: &str, source: &Json) -> candidate_source::CandidateSourceSelector {
    if semantic_type.starts_with("adr/") {
        return candidate_source::CandidateSourceSelector {
            canonical_resource_key: match semantic_type {
                "adr/logical" => "authoring/1.7/schema/adr-logical.schema",
                "adr/physical-system" => "authoring/1.7/schema/adr-physical-system.schema",
                _ => "authoring/1.7/schema/adr-physical-component.schema",
            }
            .into(),
            json_pointer: String::new(),
        };
    }
    let pointer = if semantic_type.contains(':') {
        "/definitions/custom_entity"
    } else {
        &format!(
            "/definitions/{}",
            semantic_type
                .split_once('/')
                .map(|(_, value)| value)
                .unwrap_or(semantic_type)
        )
    };
    let pointer = if source.get("relationship_type").is_some() {
        "/definitions/custom_relationship"
    } else {
        pointer
    };
    candidate_source::CandidateSourceSelector {
        canonical_resource_key: "authoring/1.7/schema/adr-common.schema".into(),
        json_pointer: pointer.into(),
    }
}

fn candidate_fragment(
    fragment: &BTreeMap<String, Json>,
    fields: &BTreeMap<String, Json>,
    identity: &Identity,
    qualification: &Json,
    source_contract: &Json,
    identities: &BTreeMap<String, Identity>,
    basis: &Json,
) -> Json {
    let mut output = BTreeMap::from([
        (
            "request_key".into(),
            fragment.get("request_key").cloned().unwrap_or(Json::Null),
        ),
        (
            "semantic_kind".into(),
            fragment.get("semantic_kind").cloned().unwrap_or(Json::Null),
        ),
        (
            "semantic_type".into(),
            fragment.get("semantic_type").cloned().unwrap_or(Json::Null),
        ),
        ("identity".into(), string(identity.id.clone())),
        ("contract_qualification".into(), qualification.clone()),
        ("fields".into(), Json::Object(fields.clone())),
        ("source_contract".into(), source_contract.clone()),
    ]);
    output.insert(
        "resolved_references".into(),
        resolved_references(fragment, identities, basis),
    );
    Json::Object(output)
}

fn relationship_fragment(
    relationship: &BTreeMap<String, Json>,
    identity: &Identity,
    qualification: &Json,
    source_contract: &Json,
    identities: &BTreeMap<String, Identity>,
    basis: &Json,
) -> Json {
    let fields = relationship
        .get("fields")
        .cloned()
        .unwrap_or_else(|| object([]));
    let mut fragment = BTreeMap::from([
        (
            "request_key".into(),
            relationship
                .get("relationship_key")
                .cloned()
                .unwrap_or(Json::Null),
        ),
        ("semantic_kind".into(), string("relationship")),
        (
            "semantic_type".into(),
            relationship
                .get("relationship_type")
                .cloned()
                .unwrap_or(Json::Null),
        ),
        ("identity".into(), string(identity.id.clone())),
        ("contract_qualification".into(), qualification.clone()),
        ("fields".into(), fields),
        ("source_contract".into(), source_contract.clone()),
    ]);
    fragment.insert("resolved_references".into(), Json::Array(Vec::new()));
    let _ = (identities, basis);
    Json::Object(fragment)
}

fn resolved_references(
    fragment: &BTreeMap<String, Json>,
    identities: &BTreeMap<String, Identity>,
    basis: &Json,
) -> Json {
    let refs = fragment
        .get("references")
        .and_then(Json::as_array)
        .into_iter()
        .flatten()
        .filter_map(Json::as_object)
        .filter_map(|reference| {
            let target = reference.get("target").and_then(Json::as_str)?;
            let kind = reference.get("reference_kind").and_then(Json::as_str)?;
            let identity = if kind == "request" {
                identities.get(target).map(|value| value.id.clone())
            } else {
                basis
                    .get("reference_basis")
                    .and_then(Json::as_object)
                    .and_then(|value| value.get("entries"))
                    .and_then(Json::as_array)
                    .into_iter()
                    .flatten()
                    .filter_map(Json::as_object)
                    .find(|entry| entry.get("reference_id").and_then(Json::as_str) == Some(target))
                    .and_then(|entry| entry.get("canonical_uuid").and_then(Json::as_str))
                    .map(ToOwned::to_owned)
            }?;
            let target_value = if kind == "request" {
                identities.get(target).map(|value| value.id.clone())?
            } else {
                target.to_owned()
            };
            Some(object([
                (
                    "reference_key".into(),
                    reference.get("reference_key")?.clone(),
                ),
                ("reference_kind".into(), string(kind)),
                ("target".into(), string(target_value)),
                ("canonical_uuid".into(), string(identity)),
                (
                    "semantic_type".into(),
                    reference
                        .get("expected_semantic_type")
                        .cloned()
                        .unwrap_or(Json::Null),
                ),
                (
                    "qualification".into(),
                    reference
                        .get("qualification")
                        .cloned()
                        .unwrap_or(Json::Null),
                ),
                (
                    "disposition".into(),
                    string(if kind == "request" {
                        "resolved"
                    } else {
                        "reused"
                    }),
                ),
            ]))
        })
        .collect();
    Json::Array(refs)
}

fn map_entry(
    key: &str,
    operation: &str,
    semantic_type: &str,
    identity: &Identity,
    qualification: &Json,
    source_ref: &str,
) -> Json {
    object([
        ("request_key".into(), string(key)),
        ("operation".into(), string(operation)),
        ("semantic_type".into(), string(semantic_type)),
        ("canonical_uuid".into(), string(identity.id.clone())),
        ("identity_disposition".into(), string(identity.disposition)),
        ("candidate_source_ref".into(), string(source_ref)),
        ("contract_qualification".into(), qualification.clone()),
        (
            "resulting_state".into(),
            string(if operation == "reference" {
                "referenced"
            } else {
                "active"
            }),
        ),
        ("diagnostic_codes".into(), Json::Array(Vec::new())),
    ])
}

fn artifact_to_json(artifact: &candidate_source::CandidateSourceArtifact) -> Json {
    object([
        ("request_key".into(), string(artifact.request_key.clone())),
        ("source_ref".into(), string(artifact.source_ref.clone())),
        (
            "artifact_kind".into(),
            string(artifact.artifact_kind.clone()),
        ),
        (
            "source_schema".into(),
            object([
                (
                    "canonical_resource_key".into(),
                    string(artifact.source_schema.canonical_resource_key.clone()),
                ),
                (
                    "json_pointer".into(),
                    string(artifact.source_schema.json_pointer.clone()),
                ),
            ]),
        ),
        (
            "serialization_profile".into(),
            string(artifact.serialization_profile.clone()),
        ),
        (
            "content_digest".into(),
            string(artifact.content_digest.clone()),
        ),
        ("bytes".into(), string(base64_encode(&artifact.bytes))),
        ("source_contract".into(), artifact.source_contract.clone()),
    ])
}

fn json_to_artifact(value: &Json) -> Result<candidate_source::CandidateSourceArtifact, String> {
    let value = value
        .as_object()
        .ok_or_else(|| "candidate artifact is not an object".to_owned())?;
    let schema = value
        .get("source_schema")
        .and_then(Json::as_object)
        .ok_or_else(|| "candidate artifact source_schema is missing".to_owned())?;
    let bytes = base64_decode(
        value
            .get("bytes")
            .and_then(Json::as_str)
            .ok_or_else(|| "candidate artifact bytes are missing".to_owned())?,
    )?;
    Ok(candidate_source::CandidateSourceArtifact {
        request_key: value
            .get("request_key")
            .and_then(Json::as_str)
            .unwrap_or_default()
            .into(),
        source_ref: value
            .get("source_ref")
            .and_then(Json::as_str)
            .unwrap_or_default()
            .into(),
        artifact_kind: value
            .get("artifact_kind")
            .and_then(Json::as_str)
            .unwrap_or_default()
            .into(),
        source_schema: candidate_source::CandidateSourceSelector {
            canonical_resource_key: schema
                .get("canonical_resource_key")
                .and_then(Json::as_str)
                .unwrap_or_default()
                .into(),
            json_pointer: schema
                .get("json_pointer")
                .and_then(Json::as_str)
                .unwrap_or_default()
                .into(),
        },
        serialization_profile: value
            .get("serialization_profile")
            .and_then(Json::as_str)
            .unwrap_or_default()
            .into(),
        content_digest: value
            .get("content_digest")
            .and_then(Json::as_str)
            .unwrap_or_default()
            .into(),
        bytes,
        source_contract: value.get("source_contract").cloned().unwrap_or(Json::Null),
    })
}

fn interpret_artifact(
    artifact: &candidate_source::CandidateSourceArtifact,
) -> Result<architecture_interpretation::InterpretationResult, String> {
    let source = candidate_source::decode_and_validate_candidate(artifact)?;
    let mut basis = BTreeMap::from([
        (
            "kind".into(),
            string(if artifact.artifact_kind == "authoring_document" {
                "authoring_document"
            } else {
                "authoring_fragment"
            }),
        ),
        (
            "schema".into(),
            string(format!(
                "{}#{}",
                artifact.source_schema.canonical_resource_key, artifact.source_schema.json_pointer
            )),
        ),
        (
            "source_schema".into(),
            object([
                (
                    "canonical_resource_key".into(),
                    string(artifact.source_schema.canonical_resource_key.clone()),
                ),
                (
                    "json_pointer".into(),
                    string(artifact.source_schema.json_pointer.clone()),
                ),
            ]),
        ),
    ]);
    if source.get("relationship_type").is_some() {
        let endpoint_entities = ["from_entity_id", "to_entity_id"]
            .into_iter()
            .filter_map(|field| source.get(field).and_then(Json::as_str))
            .map(|id| {
                object([
                    ("id".into(), string(id)),
                    ("classification".into(), string("canonical")),
                ])
            })
            .collect::<Vec<_>>();
        basis.insert("endpoint_entities".into(), Json::Array(endpoint_entities));
    }
    let context = architecture_interpretation::InterpretationSourceContext {
        canonical_source_ref: artifact.source_ref.clone(),
        source_pointer: "/".into(),
    };
    architecture_interpretation::interpret(&source, &Json::Object(basis), &context)
}

fn basis_to_json(basis: &candidate_source::CandidateSourceBasis, source_contract: &Json) -> Json {
    object([
        ("sealed".into(), Json::Bool(true)),
        ("basis_digest".into(), string(basis.basis_digest.clone())),
        (
            "artifacts".into(),
            Json::Array(basis.artifacts.iter().map(artifact_to_json).collect()),
        ),
        ("source_contract".into(), source_contract.clone()),
    ])
}

fn normalized_result(basis: &Json, request_id: &Json, fragments: &[Json]) -> Json {
    let mut keys = fragments
        .iter()
        .filter_map(|value| {
            value
                .get("request_key")
                .and_then(Json::as_str)
                .map(ToOwned::to_owned)
        })
        .collect::<Vec<_>>();
    keys.sort();
    let model = object([
        ("request_id".into(), request_id.clone()),
        (
            "fragment_keys".into(),
            Json::Array(keys.into_iter().map(string).collect()),
        ),
    ]);
    object([
        ("normalized_contract".into(), normalized_contract(basis)),
        ("semantic_digest".into(), digest_of(&model)),
        ("model".into(), model),
    ])
}

fn normalized_contract(basis: &Json) -> Json {
    basis.get("normalized_model").cloned().unwrap_or(Json::Null)
}

fn digest_of(value: &Json) -> Json {
    let mut canonical = String::new();
    semantic_contract::canonicalize_value(value, &mut canonical).expect("JSON is canonicalizable");
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    Json::String(format!(
        "sha256:{}",
        hasher
            .finalize()
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    ))
}

fn round_trip(
    qualified: bool,
    comparison: &str,
    authorized: &[&str],
    hidden: &[&str],
    diagnostics: &[Json],
) -> Json {
    object([
        ("qualified".into(), Json::Bool(qualified)),
        ("comparison".into(), string(comparison)),
        (
            "authorized_differences".into(),
            Json::Array(authorized.iter().map(|value| string(*value)).collect()),
        ),
        (
            "hidden_semantics".into(),
            Json::Array(hidden.iter().map(|value| string(*value)).collect()),
        ),
        (
            "diagnostic_codes".into(),
            Json::Array(diagnostic_codes(diagnostics)),
        ),
    ])
}

fn round_trip_mismatch(
    interpretations: &[(
        String,
        String,
        Json,
        architecture_interpretation::InterpretationResult,
    )],
) -> Option<String> {
    for (key, semantic_type, source, interpretation) in interpretations {
        if semantic_type == "entity/gap"
            && source.get("context").is_some()
            && interpretation.fields.get("context").is_none()
        {
            return Some(format!(
                "semantic field context was not preserved for {key}"
            ));
        }
    }
    None
}

fn result(
    basis: &Json,
    outcome: &str,
    diagnostics: Vec<Json>,
    provenance: Json,
    construction_map: Vec<Json>,
    candidate_fragments: Vec<Json>,
    candidate_artifacts: Vec<Json>,
    candidate_source_basis: Option<Json>,
    round_trip: Json,
) -> ConstructionResult {
    ConstructionResult {
        value: object([
            ("contract_family".into(), string(ACC_FAMILY)),
            ("contract_version".into(), string(ACC_VERSION)),
            ("operation".into(), string(ACC_OPERATION)),
            ("basis_qualification".into(), basis.clone()),
            ("diagnostics".into(), Json::Array(diagnostics)),
            ("provenance".into(), provenance),
            ("outcome".into(), string(outcome)),
            ("construction_map".into(), Json::Array(construction_map)),
            (
                "candidate_fragments".into(),
                Json::Array(candidate_fragments),
            ),
            (
                "candidate_artifacts".into(),
                Json::Array(candidate_artifacts),
            ),
            (
                "candidate_source_basis".into(),
                candidate_source_basis.unwrap_or(Json::Null),
            ),
            ("normalized_result".into(), Json::Null),
            ("round_trip".into(), round_trip),
        ]),
    }
}

struct ConstructionResult {
    value: Json,
}

impl ConstructionResult {
    fn with_normalized(mut self, normalized: Json) -> Json {
        self.value
            .as_object_mut()
            .expect("construction result object")
            .insert("normalized_result".into(), normalized);
        self.value
    }
}

fn provenance(root: Option<&BTreeMap<String, Json>>, request_id: Json) -> Json {
    let mut output = BTreeMap::from([
        ("request_id".into(), request_id),
        ("deterministic".into(), Json::Bool(true)),
        (
            "side_effects".into(),
            object([
                ("repository".into(), Json::Bool(false)),
                ("filesystem".into(), Json::Bool(false)),
                ("network".into(), Json::Bool(false)),
                ("persistence".into(), Json::Bool(false)),
            ]),
        ),
    ]);
    if let Some(source_ref) = root
        .and_then(|value| value.get("basis"))
        .and_then(Json::as_object)
        .and_then(|value| value.get("provenance"))
        .and_then(Json::as_object)
        .and_then(|value| value.get("source_ref"))
    {
        output.insert("source_ref".into(), source_ref.clone());
    }
    Json::Object(output)
}

fn source_prefix(root: Option<&BTreeMap<String, Json>>, request_id: &Json) -> String {
    root.and_then(|value| value.get("basis"))
        .and_then(Json::as_object)
        .and_then(|value| value.get("provenance"))
        .and_then(Json::as_object)
        .and_then(|value| value.get("source_ref"))
        .and_then(Json::as_str)
        .and_then(|value| value.rsplit('/').next())
        .filter(|value| !value.is_empty())
        .map(|value| format!("candidate/{value}"))
        .or_else(|| {
            request_id
                .as_str()
                .map(|value| format!("candidate/{value}"))
        })
        .unwrap_or_else(|| "candidate/request".into())
}

fn orchestration_diagnostic(
    code: &str,
    message: &str,
    request_key: Option<&str>,
    semantic_type: Option<&str>,
    status: &str,
) -> Json {
    let mut value = diagnostic(code, message, None);
    let object = value.as_object_mut().expect("diagnostic object");
    object.insert("status".into(), string(status));
    object.insert(
        "request_key".into(),
        request_key.map(string).unwrap_or(Json::Null),
    );
    object.insert("location".into(), string("/request"));
    object.insert(
        "semantic_type".into(),
        semantic_type.map(string).unwrap_or(Json::Null),
    );
    object.insert("rule".into(), string(code));
    object.insert("expected".into(), string("contract-conforming state"));
    object.insert("observed".into(), string(message));
    object.insert(
        "remediation".into(),
        string("Resolve the diagnostic before construction."),
    );
    value
}

fn fail_closed(basis: &Json, provenance: Json, code: &str) -> Json {
    let diagnostic = orchestration_diagnostic(
        code,
        "request cannot be constructed",
        None,
        None,
        "violation",
    );
    result(
        basis,
        "Rejected",
        vec![diagnostic.clone()],
        provenance,
        Vec::new(),
        Vec::new(),
        Vec::new(),
        None,
        round_trip(false, "not_evaluated", &[], &[], &[diagnostic]),
    )
    .value
}

fn diagnostic_codes(diagnostics: &[Json]) -> Vec<Json> {
    diagnostics
        .iter()
        .filter_map(|value| value.get("code").and_then(Json::as_str).map(string))
        .collect()
}

fn base64_encode(bytes: &[u8]) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut output = String::new();
    for chunk in bytes.chunks(3) {
        let a = chunk[0] as u32;
        let b = chunk.get(1).copied().unwrap_or(0) as u32;
        let c = chunk.get(2).copied().unwrap_or(0) as u32;
        output.push(TABLE[((a >> 2) & 0x3f) as usize] as char);
        output.push(TABLE[(((a & 0x3) << 4) | (b >> 4)) as usize] as char);
        output.push(if chunk.len() > 1 {
            TABLE[(((b & 0xf) << 2) | (c >> 6)) as usize] as char
        } else {
            '='
        });
        output.push(if chunk.len() > 2 {
            TABLE[(c & 0x3f) as usize] as char
        } else {
            '='
        });
    }
    output
}

fn base64_decode(input: &str) -> Result<Vec<u8>, String> {
    fn value(byte: u8) -> Result<u8, String> {
        match byte {
            b'A'..=b'Z' => Ok(byte - b'A'),
            b'a'..=b'z' => Ok(byte - b'a' + 26),
            b'0'..=b'9' => Ok(byte - b'0' + 52),
            b'+' => Ok(62),
            b'/' => Ok(63),
            _ => Err(format!("invalid base64 byte: {byte}")),
        }
    }
    if input.len() % 4 != 0 {
        return Err("base64 length is not a multiple of four".into());
    }
    let mut output = Vec::new();
    for chunk in input.as_bytes().chunks_exact(4) {
        let a = value(chunk[0])? as u32;
        let b = value(chunk[1])? as u32;
        let c = if chunk[2] == b'=' {
            0
        } else {
            value(chunk[2])? as u32
        };
        let d = if chunk[3] == b'=' {
            0
        } else {
            value(chunk[3])? as u32
        };
        output.push(((a << 2) | (b >> 4)) as u8);
        if chunk[2] != b'=' {
            output.push((((b & 0xf) << 4) | (c >> 2)) as u8);
        }
        if chunk[3] != b'=' {
            output.push((((c & 0x3) << 6) | d) as u8);
        }
    }
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FixedMinter {
        next: u8,
    }

    impl IdentityMinter for FixedMinter {
        fn mint_uuidv7(&mut self) -> Result<String, String> {
            let suffix = self.next;
            self.next = self.next.saturating_add(1);
            Ok(format!("019109a0-b1c2-7def-8a00-1122334455{suffix:02x}"))
        }
    }

    fn frozen_cases() -> Json {
        let definition: Json = serde_json::from_str(include_str!(
            "../../contracts/authoring-construction/v1.0/contract.json"
        ))
        .expect("ACC contract definition is valid JSON");
        let rules: Json = serde_json::from_str(include_str!(
            "../../contracts/authoring-construction/v1.0/resources/rules.json"
        ))
        .expect("ACC rules are valid JSON");
        let corpus: Json = serde_json::from_str(include_str!(
            "../../contracts/authoring-construction/v1.0/resources/conformance.json"
        ))
        .expect("frozen ACC conformance is valid JSON");
        let definition = definition.as_object().expect("ACC contract object");
        let resources = vec![
            object([
                (
                    "canonicalResourceKey".into(),
                    string("authoring-construction/1.0/conformance"),
                ),
                ("content".into(), corpus),
            ]),
            object([
                (
                    "canonicalResourceKey".into(),
                    string("authoring-construction/1.0/rules"),
                ),
                ("content".into(), rules),
            ]),
        ];
        semantic_contract::bind_verified_conformance_resource(
            definition,
            &resources,
            "authoring-construction/1.0/conformance",
        )
        .expect("frozen ACC conformance binds to the verified SCF")
    }

    #[test]
    fn all_frozen_acc_cases_execute_through_the_internal_orchestrator() {
        let corpus = frozen_cases();
        let cases = corpus
            .get("cases")
            .and_then(Json::as_array)
            .expect("frozen ACC cases");
        assert_eq!(cases.len(), 42);
        for case in cases {
            let input = case.get("input").expect("case input");
            let expected = case.get("expected").expect("case expected");
            let mut minter = FixedMinter { next: 0x90 };
            let result = construct_authoring_set_with_minter(input, &mut minter);
            if input.get("operation").and_then(Json::as_str) == Some("validate_authoring") {
                assert_eq!(
                    result.get("validation_status").and_then(Json::as_str),
                    expected
                        .get("result")
                        .and_then(|value| value.get("validation_status"))
                        .and_then(Json::as_str),
                    "validation outcome differs for {}",
                    case.get("id").and_then(Json::as_str).unwrap_or("unknown")
                );
                continue;
            }
            assert_eq!(
                result.get("outcome").and_then(Json::as_str),
                expected
                    .get("result")
                    .and_then(|value| value.get("outcome"))
                    .and_then(Json::as_str),
                "construction outcome differs for {}",
                case.get("id").and_then(Json::as_str).unwrap_or("unknown")
            );
            assert_eq!(
                result.get("operation").and_then(Json::as_str),
                Some(ACC_OPERATION)
            );
            assert!(result.get("basis_qualification").is_some());
            assert!(result.get("round_trip").is_some());
        }
    }

    #[test]
    fn c32_is_rejected_by_round_trip_field_loss_and_c33_is_unavailable_before_interpretation() {
        let corpus = frozen_cases();
        let cases = corpus.get("cases").and_then(Json::as_array).unwrap();
        let c32 = cases
            .iter()
            .find(|case| case.get("id").and_then(Json::as_str) == Some("C32"))
            .unwrap();
        let c33 = cases
            .iter()
            .find(|case| case.get("id").and_then(Json::as_str) == Some("C33"))
            .unwrap();
        let mut minter = FixedMinter { next: 0x90 };
        let c32_result =
            construct_authoring_set_with_minter(c32.get("input").unwrap(), &mut minter);
        assert_eq!(
            c32_result.get("outcome").and_then(Json::as_str),
            Some("Rejected")
        );
        assert_eq!(
            c32_result
                .get("round_trip")
                .and_then(|value| value.get("hidden_semantics"))
                .and_then(Json::as_array)
                .and_then(|value| value.first())
                .and_then(Json::as_str),
            Some("semantic_field_loss")
        );
        assert_eq!(
            c32_result
                .get("diagnostics")
                .and_then(Json::as_array)
                .and_then(|value| value.first())
                .and_then(|value| value.get("code"))
                .and_then(Json::as_str),
            Some("authoring_construction.round_trip.semantic_mismatch")
        );

        let c33_result =
            construct_authoring_set_with_minter(c33.get("input").unwrap(), &mut minter);
        assert_eq!(
            c33_result.get("outcome").and_then(Json::as_str),
            Some("Unavailable")
        );
        assert_eq!(
            c33_result
                .get("diagnostics")
                .and_then(Json::as_array)
                .and_then(|value| value.first())
                .and_then(|value| value.get("code"))
                .and_then(Json::as_str),
            Some("authoring_construction.interpretation.unavailable")
        );
        assert!(c33_result
            .get("candidate_artifacts")
            .and_then(Json::as_array)
            .is_some_and(Vec::is_empty));
    }
}
