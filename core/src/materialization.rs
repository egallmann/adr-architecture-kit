//! Canonical semantic-core architecture materialization.
//!
//! This module is intentionally the semantic center of the capability.  A
//! host may discover files, read bytes, parse YAML, and convert its native
//! DTOs into the request below, but it may not decide what an authoring field
//! means or manufacture a normalized identity.  The module has no filesystem
//! imports and no host-specific types; its only boundary representation is
//! the internal JSON transport used by the WASM entry point.

use std::collections::{BTreeMap, BTreeSet};

use sha2::{Digest, Sha256};

use super::schema_validation;
use super::semantic_contract::canonicalize_value;
use super::semantic_contract_set::{resolve_exact_set, ExactResolution};
use super::{diagnostic, object, string, Json};

const OPERATION: &str = "materialize_architecture";
const MATERIALIZATION_VERSION: &str = "1.0";
const NORMALIZED_MODEL_VERSION: &str = "2.3";
const AUTHORITY_FINGERPRINT_SCHEME: &str = "asf:v1:sha256:";

#[derive(Clone, Debug)]
struct Identity {
    id: String,
    source_id: String,
    alias_id: String,
    alias_name: String,
}

/// The source-contract qualification is the only authority boundary at which
/// authoring schemas enter the core.  Keep both the manifest digest and the
/// sealed content together so validation cannot accidentally consult a file,
/// a host registry, or a different version of a schema.
struct GovernedSourceResources {
    digests: BTreeMap<String, String>,
    contents: BTreeMap<String, Json>,
}

fn text(value: Option<&Json>) -> Option<String> {
    value.and_then(Json::as_str).map(str::to_owned)
}

fn array<'a>(value: Option<&'a Json>) -> Option<&'a Vec<Json>> {
    match value {
        Some(Json::Array(values)) => Some(values),
        _ => None,
    }
}

fn bool_value(value: Option<&Json>) -> Option<bool> {
    match value {
        Some(Json::Bool(value)) => Some(*value),
        _ => None,
    }
}

fn is_sha256(value: &str) -> bool {
    let Some(hex) = value.strip_prefix("sha256:") else {
        return false;
    };
    hex.len() == 64
        && hex
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn is_uuid_v7(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 36
        && [8, 13, 18, 23].iter().all(|index| bytes[*index] == b'-')
        && bytes
            .iter()
            .enumerate()
            .filter(|(index, _)| ![8, 13, 18, 23].contains(index))
            .all(|(_, byte)| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
        && bytes[14] == b'7'
        && matches!(bytes[19], b'8' | b'9' | b'a' | b'b')
}

fn digest_bytes(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    format!(
        "sha256:{}",
        digest
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    )
}

fn digest_json(value: &Json) -> Result<String, String> {
    let mut canonical = String::new();
    canonicalize_value(value, &mut canonical)?;
    Ok(digest_bytes(canonical.as_bytes()))
}

fn diagnostic_code(
    diagnostics: &mut Vec<Json>,
    code: &str,
    message: impl Into<String>,
    path: &str,
) {
    diagnostics.push(diagnostic(code, message, Some(path.to_owned())));
}

fn canonical_alias(value: &str, fallback: &str) -> String {
    // Authoring aliases are retained as identity evidence.  normalized-model
    // v2.3 additionally requires a lower-kebab alias_name, so the projection
    // normalizes only that presentation field and keeps alias_id/source_ref.
    let mut result = String::new();
    let mut previous_separator = false;
    for character in value.chars().flat_map(char::to_lowercase) {
        if character.is_ascii_alphanumeric() {
            result.push(character);
            previous_separator = false;
        } else if !previous_separator && !result.is_empty() {
            result.push('-');
            previous_separator = true;
        }
    }
    while result.ends_with('-') {
        result.pop();
    }
    if result.len() < 3 {
        fallback.to_owned()
    } else {
        result.chars().take(96).collect()
    }
}

fn lifecycle_stage(status: &str) -> &'static str {
    match status {
        "accepted" | "active" => "active",
        "deprecated" => "deprecated",
        "superseded" => "superseded",
        _ => "proposed",
    }
}

fn source_artifact_value(
    source_type: &str,
    source_ref: &str,
    artifact_path: &str,
    content_digest: &str,
) -> Json {
    object([
        ("source_type".into(), string(source_type)),
        ("source_ref".into(), string(source_ref)),
        ("artifact_path".into(), string(artifact_path)),
        ("content_digest".into(), string(content_digest)),
    ])
}

fn map_source_id(
    source_id: &str,
    identity_map: &BTreeMap<String, String>,
    diagnostics: &mut Vec<Json>,
    path: &str,
) -> Option<String> {
    if is_uuid_v7(source_id) {
        return Some(source_id.to_owned());
    }
    match identity_map.get(source_id) {
        Some(mapped) if is_uuid_v7(mapped) => Some(mapped.clone()),
        Some(_) => {
            diagnostic_code(
                diagnostics,
                "semantic_contract.identity_map_invalid_target",
                "legacy identity map target must be a UUIDv7 canonical identity",
                path,
            );
            None
        }
        None => {
            diagnostic_code(
                diagnostics,
                "semantic_contract.identity_qualification_required",
                "legacy source identity requires an exact sealed provider-authoritative identity map",
                path,
            );
            None
        }
    }
}

fn candidate_identity(
    value: Option<&Json>,
    identity_map: &BTreeMap<String, String>,
) -> Option<String> {
    let source_id = text(value?.as_object()?.get("id"))?;
    if is_uuid_v7(&source_id) {
        Some(source_id)
    } else {
        identity_map.get(&source_id).cloned()
    }
}

fn collect_candidate_identities(
    document: &BTreeMap<String, Json>,
    identity_map: &BTreeMap<String, String>,
    identities: &mut BTreeSet<String>,
) {
    let mut collect = |value: Option<&Json>| {
        if let Some(id) = candidate_identity(value, identity_map) {
            identities.insert(id);
        }
    };
    collect(Some(&Json::Object(document.clone())));
    for field in [
        "decisions",
        "invariants",
        "constraints",
        "non_functional_requirements",
        "gaps",
        "extension_entities",
        "normative_propositions",
    ] {
        if let Some(values) = array(document.get(field)) {
            for value in values {
                collect(Some(value));
            }
        }
    }
    if let Some(system) = document.get("system") {
        collect(Some(system));
    }
    if let Some(specifications) = array(document.get("component_specifications")) {
        for specification in specifications {
            collect(Some(specification));
            if let Some(interfaces) = specification
                .as_object()
                .and_then(|value| value.get("interfaces"))
                .and_then(Json::as_array)
            {
                for interface in interfaces {
                    collect(Some(interface));
                }
            }
        }
    }
}

fn identity_map(
    value: Option<&Json>,
    provider: &BTreeMap<String, Json>,
    diagnostics: &mut Vec<Json>,
) -> BTreeMap<String, String> {
    let Some(raw) = value else {
        return BTreeMap::new();
    };
    let Some(map) = raw.as_object() else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.identity_map_invalid",
            "legacyIdentityMap must be an object",
            "sourceBasis.legacyIdentityMap",
        );
        return BTreeMap::new();
    };
    if bool_value(map.get("sealed")) != Some(true) {
        diagnostic_code(
            diagnostics,
            "semantic_contract.identity_map_unsealed",
            "legacy identity map must be explicitly sealed",
            "sourceBasis.legacyIdentityMap.sealed",
        );
    }
    if let Some(declared_provider) = text(map.get("provider")) {
        let expected_provider = format!(
            "{}:{}",
            text(provider.get("kind")).unwrap_or_default(),
            text(provider.get("architectureNamespace")).unwrap_or_default()
        );
        if declared_provider != expected_provider {
            diagnostic_code(
                diagnostics,
                "semantic_contract.identity_map_provider_mismatch",
                "legacy identity map provider does not match the authority provider",
                "sourceBasis.legacyIdentityMap.provider",
            );
        }
    }
    let mut entries = BTreeMap::new();
    if let Some(raw_entries) = array(map.get("entries").or_else(|| map.get("mappings"))) {
        for (index, raw_entry) in raw_entries.iter().enumerate() {
            let path = format!("sourceBasis.legacyIdentityMap.entries[{index}]");
            let Some(entry) = raw_entry.as_object() else {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.identity_map_invalid_entry",
                    "legacy identity map entry must be an object",
                    &path,
                );
                continue;
            };
            let source = text(entry.get("sourceId").or_else(|| entry.get("source_id")));
            let target = text(
                entry
                    .get("canonicalId")
                    .or_else(|| entry.get("canonical_id")),
            );
            match (source, target) {
                (Some(source), Some(target)) => {
                    if entries.insert(source, target).is_some() {
                        diagnostic_code(
                            diagnostics,
                            "semantic_contract.identity_map_duplicate_source",
                            "legacy identity map source identity occurs more than once",
                            &path,
                        );
                    }
                }
                _ => diagnostic_code(
                    diagnostics,
                    "semantic_contract.identity_map_invalid_entry",
                    "legacy identity map entries require sourceId and canonicalId",
                    &path,
                ),
            }
        }
    }
    // A compact object map is accepted as a transport convenience, but only
    // its explicitly governed mapping members are interpreted.
    for (source, target) in map {
        if ["sealed", "provider", "entries", "mappings"].contains(&source.as_str()) {
            continue;
        }
        if let Some(target) = target.as_str() {
            if entries.insert(source.clone(), target.to_owned()).is_some() {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.identity_map_duplicate_source",
                    "legacy identity map source identity occurs more than once",
                    &format!("sourceBasis.legacyIdentityMap.{source}"),
                );
            }
        }
    }
    entries
}

fn is_lower_kebab(value: &str) -> bool {
    let bytes = value.as_bytes();
    (3..=96).contains(&bytes.len())
        && bytes[0].is_ascii_lowercase()
        && (bytes[bytes.len() - 1].is_ascii_lowercase() || bytes[bytes.len() - 1].is_ascii_digit())
        && bytes.iter().enumerate().all(|(index, byte)| {
            byte.is_ascii_lowercase()
                || byte.is_ascii_digit()
                || (*byte == b'-'
                    && index > 0
                    && index + 1 < bytes.len()
                    && bytes[index - 1] != b'-'
                    && bytes[index + 1] != b'-')
        })
}

fn is_four_digits(value: &str) -> bool {
    value.len() == 4 && value.bytes().all(|byte| byte.is_ascii_digit())
}

fn is_np_alias(value: &str) -> bool {
    value.strip_prefix("NP-").is_some_and(is_four_digits)
}

fn is_iso_date(value: &str) -> bool {
    value.len() == 10
        && value.as_bytes()[4] == b'-'
        && value.as_bytes()[7] == b'-'
        && value
            .bytes()
            .enumerate()
            .all(|(index, byte)| [4, 7].contains(&index) || byte.is_ascii_digit())
}

fn source_error(diagnostics: &mut Vec<Json>, path: &str, message: impl Into<String>) {
    diagnostic_code(
        diagnostics,
        "semantic_contract.invalid_source_document",
        message,
        path,
    );
}

/// Build the only resource view materialization is allowed to consume.
///
/// `ExactResolution` has already selected one immutable bundle per participating
/// family by the complete family/version/SCF identity.  This function never
/// revisits the request's retained definitions, so a historical or future
/// bundle that was not a member of the requested SCS cannot shadow anything.
/// Overlapping imports are accepted only when their qualified digest and
/// canonical bytes agree exactly.
fn resolved_resource_view(
    resolution: &ExactResolution,
    diagnostics: &mut Vec<Json>,
) -> GovernedSourceResources {
    let mut resources = GovernedSourceResources {
        digests: BTreeMap::new(),
        contents: BTreeMap::new(),
    };
    for bundle in resolution.definitions.values() {
        let definition = bundle.definition.as_object();
        let bundle_resources = bundle
            .resources
            .iter()
            .filter_map(Json::as_object)
            .filter_map(|resource| {
                Some((
                    text(resource.get("canonicalResourceKey"))?,
                    resource.get("content")?.clone(),
                ))
            })
            .collect::<BTreeMap<_, _>>();
        let Some(manifest) = definition.and_then(|value| array(value.get("resourceManifest")))
        else {
            continue;
        };
        for entry in manifest {
            let Some(entry) = entry.as_object() else {
                continue;
            };
            let Some(key) = text(entry.get("canonicalResourceKey")) else {
                continue;
            };
            let Some(digest) = text(entry.get("contentDigest")) else {
                continue;
            };
            let Some(content) = bundle_resources.get(&key) else {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.source_resource_content_missing",
                    format!(
                        "selected {} definition lists a resource without sealed content",
                        bundle.member.family
                    ),
                    &format!("definitions.{}.resources", bundle.member.family),
                );
                continue;
            };
            if let Some(existing_digest) = resources.digests.get(&key) {
                let existing_content = resources.contents.get(&key);
                let same_content = existing_content.is_some_and(|existing| {
                    let mut left = String::new();
                    let mut right = String::new();
                    canonicalize_value(existing, &mut left).is_ok()
                        && canonicalize_value(content, &mut right).is_ok()
                        && left == right
                });
                if existing_digest != &digest || !same_content {
                    diagnostic_code(
                        diagnostics,
                        "semantic_contract.selected_resource_conflict",
                        format!(
                            "selected resource {key} has conflicting identity or canonical bytes across exact SCS members"
                        ),
                        &format!("definitions.{}.resourceManifest", bundle.member.family),
                    );
                }
                continue;
            }
            resources.digests.insert(key.clone(), digest);
            resources.contents.insert(key, content.clone());
        }
    }
    if resources.digests.is_empty() {
        source_error(
            diagnostics,
            "definitions",
            "architecture-interpretation source resource closure is unavailable",
        );
    }
    for key in resources.digests.keys() {
        let Some(content) = resources.contents.get(key) else {
            continue;
        };
        match digest_json(content) {
            Ok(actual) if resources.digests.get(key) == Some(&actual) => {}
            Ok(_) => diagnostic_code(
                diagnostics,
                "semantic_contract.source_resource_content_unqualified",
                "governed source resource content does not match its qualified digest",
                "definitions",
            ),
            Err(_) => diagnostic_code(
                diagnostics,
                "semantic_contract.source_resource_content_invalid",
                "governed source resource content cannot be canonicalized",
                "definitions",
            ),
        }
    }
    resources
}

fn validate_selected_import_ownership(
    resolution: &ExactResolution,
    diagnostics: &mut Vec<Json>,
) {
    let Some(architecture) = resolution.definitions.get("architecture-interpretation") else {
        return;
    };
    let Some(normalized) = resolution.definitions.get("normalized-model") else {
        return;
    };
    let architecture_manifest = architecture
        .definition
        .as_object()
        .and_then(|definition| array(definition.get("resourceManifest")))
        .into_iter()
        .flatten()
        .filter_map(Json::as_object)
        .filter_map(|entry| text(entry.get("canonicalResourceKey")))
        .filter(|key| key.starts_with("normalized-model/"));
    let normalized_manifest = normalized
        .definition
        .as_object()
        .and_then(|definition| array(definition.get("resourceManifest")))
        .into_iter()
        .flatten()
        .filter_map(Json::as_object)
        .filter_map(|entry| {
            Some((
                text(entry.get("canonicalResourceKey"))?,
                text(entry.get("contentDigest"))?,
            ))
        })
        .collect::<BTreeMap<_, _>>();
    for key in architecture_manifest {
        match normalized_manifest.get(&key) {
            None => diagnostic_code(
                diagnostics,
                "semantic_contract.selected_import_owner_missing",
                format!(
                    "architecture-interpretation imports {key}, but the selected normalized-model member does not own it"
                ),
                "definitions.architecture-interpretation.resourceManifest",
            ),
            // Digest disagreement is reported once while the immutable view
            // is assembled.  Keeping ownership validation focused on the
            // missing-owner case avoids duplicate conflict diagnostics.
            Some(_) => {}
        }
    }
}

fn expected_source_resource_keys(version: &str, adr_type: &str) -> Vec<String> {
    let mut keys = vec![
        format!("authoring/{version}/schema/adr-common.schema"),
        format!("authoring/{version}/schema/types.schema"),
    ];
    keys.push(format!(
        "authoring/{version}/schema/{}",
        match adr_type {
            "logical" => "adr-logical.schema",
            "physical-system" => "adr-physical-system.schema",
            "physical-component" => "adr-physical-component.schema",
            _ => "adr-common.schema",
        }
    ));
    if matches!(adr_type, "physical-system" | "physical-component") {
        keys.push(format!(
            "authoring/{version}/schema/adr-physical-base.schema"
        ));
    }
    keys.sort();
    keys
}

fn identity(
    value: &BTreeMap<String, Json>,
    identity_map: &BTreeMap<String, String>,
    diagnostics: &mut Vec<Json>,
    path: &str,
) -> Option<Identity> {
    let source_id = text(value.get("id"));
    let Some(source_id) = source_id else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_source_identity",
            "source declaration requires an id",
            &format!("{path}.id"),
        );
        return None;
    };
    let Some(id) = map_source_id(&source_id, identity_map, diagnostics, &format!("{path}.id"))
    else {
        return None;
    };
    let Some(alias_id) = text(value.get("alias_id")) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_source_identity",
            "source declaration requires an alias_id",
            &format!("{path}.alias_id"),
        );
        return None;
    };
    let Some(raw_alias_name) = text(value.get("alias_name")) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_source_identity",
            "source declaration requires an alias_name",
            &format!("{path}.alias_name"),
        );
        return None;
    };
    let alias_name = canonical_alias(&raw_alias_name, "unnamed-entity");
    Some(Identity {
        id,
        source_id,
        alias_id,
        alias_name,
    })
}

fn source_contract(
    value: &BTreeMap<String, Json>,
    document: &BTreeMap<String, Json>,
    governed_resources: &GovernedSourceResources,
    diagnostics: &mut Vec<Json>,
    path: &str,
) -> Option<(String, Json)> {
    let Some(binding) = value.get("sourceContract").and_then(Json::as_object) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.missing_source_contract_binding",
            "every source artifact requires an exact source-contract binding",
            &format!("{path}.sourceContract"),
        );
        return None;
    };
    let family = text(binding.get("family")).unwrap_or_default();
    let version = text(binding.get("version")).unwrap_or_default();
    let Some(schema_resource) = binding.get("schemaResource").and_then(Json::as_object) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_qualification_required",
            "source contract requires the exact applicable schema resource",
            &format!("{path}.sourceContract.schemaResource"),
        );
        return None;
    };
    let Some(resource_closure) = array(binding.get("resourceClosure")) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_qualification_required",
            "source contract requires its exact imported schema resource closure",
            &format!("{path}.sourceContract.resourceClosure"),
        );
        return None;
    };
    if family != "authoring" || !matches!(version.as_str(), "1.5" | "1.6") {
        diagnostic_code(
            diagnostics,
            "semantic_contract.unsupported_source_contract",
            "only qualified authoring source contracts 1.5 and 1.6 are supported",
            &format!("{path}.sourceContract"),
        );
        return None;
    }
    let adr_type = text(document.get("adr_type")).unwrap_or_default();
    let expected_keys = expected_source_resource_keys(&version, &adr_type);
    let Some(schema_key) = text(schema_resource.get("canonicalResourceKey")) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_qualification_required",
            "schemaResource requires canonicalResourceKey",
            &format!("{path}.sourceContract.schemaResource.canonicalResourceKey"),
        );
        return None;
    };
    let Some(schema_digest) = text(schema_resource.get("contentDigest")) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_qualification_required",
            "schemaResource requires contentDigest",
            &format!("{path}.sourceContract.schemaResource.contentDigest"),
        );
        return None;
    };
    let expected_schema = expected_keys
        .iter()
        .find(|key| {
            key.ends_with(match adr_type.as_str() {
                "logical" => "adr-logical.schema",
                "physical-system" => "adr-physical-system.schema",
                "physical-component" => "adr-physical-component.schema",
                _ => "adr-common.schema",
            })
        })
        .cloned()
        .unwrap_or_default();
    if schema_key != expected_schema {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_schema_mismatch",
            "schemaResource is not the exact top-level authoring schema for adr_type",
            &format!("{path}.sourceContract.schemaResource.canonicalResourceKey"),
        );
    }
    let mut supplied = BTreeMap::new();
    for (index, raw_resource) in resource_closure.iter().enumerate() {
        let resource_path = format!("{path}.sourceContract.resourceClosure[{index}]");
        let Some(resource) = raw_resource.as_object() else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_invalid",
                "source contract closure entry must be an object",
                &resource_path,
            );
            continue;
        };
        let Some(key) = text(resource.get("canonicalResourceKey")) else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_invalid",
                "source contract closure entry requires canonicalResourceKey",
                &format!("{resource_path}.canonicalResourceKey"),
            );
            continue;
        };
        let Some(digest) = text(resource.get("contentDigest")) else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_invalid",
                "source contract closure entry requires contentDigest",
                &format!("{resource_path}.contentDigest"),
            );
            continue;
        };
        if supplied.insert(key.clone(), digest.clone()).is_some() {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_duplicate",
                "source contract closure cannot repeat a resource identity",
                &resource_path,
            );
        }
        if governed_resources.digests.get(&key) != Some(&digest) {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_unqualified",
                "source contract resource is not part of the exact resolved semantic basis with the selected member digest",
                &resource_path,
            );
        }
    }
    if supplied
        != expected_keys
            .iter()
            .filter_map(|key| {
                governed_resources
                    .digests
                    .get(key)
                    .map(|digest| (key.clone(), digest.clone()))
            })
            .collect::<BTreeMap<_, _>>()
    {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_closure_mismatch",
            "source contract closure does not exactly match the applicable authoring schema imports",
            &format!("{path}.sourceContract.resourceClosure"),
        );
    }
    if governed_resources.digests.get(&schema_key) != Some(&schema_digest) {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_schema_unqualified",
            "top-level schema resource is not part of the exact resolved semantic basis with the selected member digest",
            &format!("{path}.sourceContract.schemaResource"),
        );
    }
    let mut canonical_resources = resource_closure.to_vec();
    canonical_resources.sort_by_key(|resource| {
        text(
            resource
                .as_object()
                .and_then(|value| value.get("canonicalResourceKey")),
        )
        .unwrap_or_default()
    });
    let result = object([
        ("family".into(), string(family.clone())),
        ("version".into(), string(version.clone())),
        (
            "schemaResource".into(),
            Json::Object(schema_resource.clone()),
        ),
        ("resourceClosure".into(), Json::Array(canonical_resources)),
    ]);
    let key = format!("{family}@{version}@{schema_key}");
    Some((key, result))
}

fn source_identity_ref(binding: &Json) -> Json {
    binding.clone()
}

fn normalized_source_contract(binding: &Json) -> Json {
    // normalized-model v2.3 predates the richer transport binding and keeps
    // its compatibility-shaped source_contract member.  Its fingerprint is
    // the exact qualified top-level schema resource digest; it is never an
    // aggregate or caller-supplied digest.  The complete binding remains on
    // the artifact and in sourceContractClosure.
    let binding_object = binding.as_object();
    let family = text(binding_object.and_then(|value| value.get("family"))).unwrap_or_default();
    let version = text(binding_object.and_then(|value| value.get("version"))).unwrap_or_default();
    let fingerprint = text(
        binding_object
            .and_then(|value| value.get("schemaResource"))
            .and_then(Json::as_object)
            .and_then(|value| value.get("contentDigest")),
    )
    .unwrap_or_default();
    object([
        ("family".into(), string(family)),
        ("version".into(), string(version)),
        ("fingerprint".into(), string(fingerprint)),
    ])
}

fn regular_entity(
    raw: &BTreeMap<String, Json>,
    entity_type: &str,
    declaration_kind: &str,
    parent: Option<&Identity>,
    provider: &BTreeMap<String, Json>,
    source: &BTreeMap<String, Json>,
    source_contract: &Json,
    identity_map: &BTreeMap<String, String>,
    diagnostics: &mut Vec<Json>,
    path: &str,
) -> Option<Json> {
    let identity = identity(raw, identity_map, diagnostics, path)?;
    let title = text(
        raw.get("title")
            .or_else(|| raw.get("name"))
            .or_else(|| raw.get("summary")),
    )
    .unwrap_or_else(|| identity.alias_name.clone());
    let summary = text(
        raw.get("summary")
            .or_else(|| raw.get("context"))
            .or_else(|| raw.get("rationale")),
    )
    .unwrap_or_else(|| title.clone());
    let created_at = text(raw.get("created_date").or_else(|| raw.get("created_at")))
        .unwrap_or_else(|| "unknown".into());
    let status = text(raw.get("status")).unwrap_or_else(|| "proposed".into());
    let provider_key = format!(
        "{}:{}",
        text(provider.get("kind")).unwrap_or_default(),
        text(provider.get("architectureNamespace")).unwrap_or_default()
    );
    let source_ref = text(source.get("sourceRef")).unwrap_or_default();
    let artifact_path = text(source.get("artifactPath")).unwrap_or_default();
    let content_digest = text(source.get("contentDigest")).unwrap_or_default();
    let source_type = format!("{declaration_kind}_adr");
    let mut values = BTreeMap::from([
        ("id".into(), string(identity.id.clone())),
        ("alias_id".into(), string(identity.alias_id.clone())),
        ("alias_name".into(), string(identity.alias_name.clone())),
        (
            "alias_ref".into(),
            string(format!("{provider_key}:{}", identity.alias_id)),
        ),
        ("entity_type".into(), string(entity_type)),
        ("name".into(), string(title)),
        ("summary".into(), string(summary)),
        (
            "uri".into(),
            string(format!(
                "adr://{}/{}",
                text(provider.get("architectureNamespace")).unwrap_or_default(),
                identity.id
            )),
        ),
        ("created_at".into(), string(created_at)),
        ("lifecycle_stage".into(), string(lifecycle_stage(&status))),
        (
            "canonical_source".into(),
            object([
                ("source_type".into(), string(source_type.clone())),
                ("source_ref".into(), string(source_ref.clone())),
                ("artifact_path".into(), string(artifact_path.clone())),
                ("content_digest".into(), string(content_digest.clone())),
                ("provider".into(), string(provider_key.clone())),
            ]),
        ),
        (
            "source_refs".into(),
            Json::Array(vec![string(source_ref.clone())]),
        ),
        (
            "metadata".into(),
            object([
                ("source_alias_id".into(), string(identity.alias_id.clone())),
                ("source_identity".into(), string(identity.source_id.clone())),
                ("declaring_kind".into(), string(declaration_kind)),
            ]),
        ),
        ("relationships".into(), Json::Object(BTreeMap::new())),
        (
            "completeness".into(),
            object([
                ("status".into(), string("complete")),
                ("missing_fields".into(), Json::Array(Vec::new())),
            ]),
        ),
        (
            "provenance".into(),
            object([
                ("provider".into(), string(provider_key)),
                ("source_ref".into(), string(source_ref)),
                ("artifact_path".into(), string(artifact_path)),
                ("source_contract".into(), source_contract.clone()),
                ("classification".into(), string("explicit")),
            ]),
        ),
    ]);
    if let Some(parent) = parent {
        values.insert(
            "metadata".into(),
            object([
                ("source_alias_id".into(), string(identity.alias_id.clone())),
                ("source_identity".into(), string(identity.source_id.clone())),
                ("declaring_kind".into(), string(declaration_kind)),
                ("declaring_adr_id".into(), string(parent.id.clone())),
            ]),
        );
    }
    let fingerprint_basis = Json::Object(values.clone());
    let fingerprint = digest_json(&fingerprint_basis).unwrap_or_else(|_| digest_bytes(&[]));
    values.insert("entity_fingerprint".into(), string(fingerprint));
    Some(Json::Object(values))
}

/// Retain authored physical detail as source evidence on the corresponding
/// normalized entity.  This is intentionally not a guessed new normalized
/// vocabulary: the accepted interpretation contract permits provenance and
/// source coverage, while only the identity-bearing constructs below receive
/// normalized entity/relationship projections.
fn retain_source_semantics(
    entity: &mut Json,
    raw: &BTreeMap<String, Json>,
    source_fields: &[&str],
) {
    let Json::Object(values) = entity else {
        return;
    };
    let mut metadata = values
        .get("metadata")
        .and_then(Json::as_object)
        .cloned()
        .unwrap_or_default();
    let source_semantics = source_fields
        .iter()
        .filter_map(|field| {
            raw.get(*field)
                .map(|value| ((*field).to_owned(), value.clone()))
        })
        .collect::<BTreeMap<_, _>>();
    metadata.insert("source_semantics".into(), Json::Object(source_semantics));
    values.insert("metadata".into(), Json::Object(metadata));
    values.remove("entity_fingerprint");
    let fingerprint =
        digest_json(&Json::Object(values.clone())).unwrap_or_else(|_| digest_bytes(&[]));
    values.insert("entity_fingerprint".into(), string(fingerprint));
}

fn compatibility_relationship(
    relationship_type: &str,
    from: &str,
    to: &str,
    source_ref: &str,
    source_owner_id: &str,
    source_pointer: &str,
    evidence: Option<Json>,
) -> Json {
    let preimage = object([
        ("relationship_type".into(), string(relationship_type)),
        ("from_entity_id".into(), string(from)),
        ("to_entity_id".into(), string(to)),
        ("canonical_source_ref".into(), string(source_ref)),
        ("source_pointer".into(), string(source_pointer)),
    ]);
    let assertion = digest_json(&preimage)
        .unwrap_or_else(|_| digest_bytes(&[]))
        .trim_start_matches("sha256:")
        .to_owned();
    object([
        ("record_kind".into(), string("compatibility")),
        (
            "relationship_id".into(),
            string(format!("assertion:{assertion}")),
        ),
        ("assertion_id".into(), string(format!("asrt-{assertion}"))),
        ("relationship_type".into(), string(relationship_type)),
        ("from_entity_id".into(), string(from)),
        ("to_entity_id".into(), string(to)),
        ("source_owner_id".into(), string(source_owner_id)),
        ("source_pointer".into(), string(source_pointer)),
        ("provenance_classification".into(), string("explicit")),
        (
            "evidence".into(),
            evidence.unwrap_or_else(|| Json::Array(Vec::new())),
        ),
        ("canonical_source_ref".into(), string(source_ref)),
    ])
}

fn unresolved_relationship(
    source_ref: &str,
    source_pointer: &str,
    reference: &str,
    relationship_type: &str,
    from: &str,
    to: &str,
) -> Json {
    object([
        ("kind".into(), string("unresolved_source_relationship")),
        ("reference".into(), string(reference)),
        ("relationship_type".into(), string(relationship_type)),
        ("from_entity_id".into(), string(from)),
        ("to_entity_id".into(), string(to)),
        ("source_ref".into(), string(source_ref)),
        ("source_pointer".into(), string(source_pointer)),
    ])
}

fn physical_source_coverage(
    document: &BTreeMap<String, Json>,
    adr_type: &str,
    artifact_path: &str,
) -> Json {
    let mut fields = Vec::new();
    let common = [
        "schema_version",
        "adr_type",
        "id",
        "alias_id",
        "alias_name",
        "title",
        "status",
        "created_date",
        "modified_date",
        "authors",
        "context",
        "decisions",
        "invariants",
        "constraints",
        "non_functional_requirements",
        "gaps",
        "extension_entities",
        "extension_relationships",
        "normative_propositions",
        "related_adrs",
    ];
    for field in common {
        if document.contains_key(field) {
            fields.push(object([
                ("source_field".into(), string(field)),
                (
                    "classification".into(),
                    string("projected_or_retained_provenance"),
                ),
            ]));
        }
    }
    if adr_type == "physical-system" {
        for (field, classification) in [
            ("implements_logical", "projected_as_implements_relationship"),
            ("technology_stack", "retained_in_entity_provenance"),
            ("system", "projected_identity"),
            ("system_boundaries", "retained_in_entity_provenance"),
            (
                "component_topology",
                "projected_as_relationships_and_retained_provenance",
            ),
            ("integration_patterns", "retained_in_entity_provenance"),
            ("data_flows", "retained_in_entity_provenance"),
            ("references_components", "retained_in_entity_provenance"),
            ("scalability_strategy", "retained_in_entity_provenance"),
            ("failure_modes", "retained_in_entity_provenance"),
        ] {
            if document.contains_key(field) {
                fields.push(object([
                    ("source_field".into(), string(field)),
                    ("classification".into(), string(classification)),
                ]));
            }
        }
    }
    if adr_type == "physical-component" {
        for (field, classification) in [
            ("implements_logical", "projected_as_implements_relationship"),
            ("technology_stack", "retained_in_entity_provenance"),
            ("implements_system", "projected_as_implements_relationship"),
            (
                "component_specifications",
                "projected_identity_and_retained_provenance",
            ),
        ] {
            if document.contains_key(field) {
                fields.push(object([
                    ("source_field".into(), string(field)),
                    ("classification".into(), string(classification)),
                ]));
            }
        }
    }
    object([
        ("artifact_path".into(), string(artifact_path)),
        ("adr_type".into(), string(adr_type)),
        ("fields".into(), Json::Array(fields)),
    ])
}

fn reject_unmapped_source_fields(
    document: &BTreeMap<String, Json>,
    adr_type: &str,
    path: &str,
    diagnostics: &mut Vec<Json>,
) {
    let mut allowed = BTreeSet::from([
        "schema_version",
        "adr_type",
        "id",
        "alias_id",
        "alias_name",
        "title",
        "status",
        "created_date",
        "modified_date",
        "authors",
        "context",
        "decisions",
        "invariants",
        "constraints",
        "non_functional_requirements",
        "gaps",
        "extension_entities",
        "extension_relationships",
        "normative_propositions",
        "related_adrs",
    ]);
    if adr_type == "physical-system" {
        allowed.extend([
            "implements_logical",
            "technology_stack",
            "system",
            "system_boundaries",
            "component_topology",
            "integration_patterns",
            "data_flows",
            "references_components",
            "scalability_strategy",
            "failure_modes",
        ]);
    } else if adr_type == "physical-component" {
        allowed.extend([
            "implements_logical",
            "technology_stack",
            "implements_system",
            "component_specifications",
        ]);
    }
    for field in document
        .keys()
        .filter(|field| !allowed.contains(field.as_str()))
    {
        diagnostic_code(
            diagnostics,
            "semantic_contract.unsupported_source_construct",
            format!("source field {field} has no accepted architecture-interpretation mapping"),
            &format!("{path}.{field}"),
        );
    }
}

fn extension_entity(
    raw: &BTreeMap<String, Json>,
    provider: &BTreeMap<String, Json>,
    source: &BTreeMap<String, Json>,
    source_contract: &Json,
    identity_map: &BTreeMap<String, String>,
    diagnostics: &mut Vec<Json>,
    path: &str,
) -> Option<Json> {
    // Extension entities remain ordinary canonical entities, but their
    // namespaced type is accompanied by the authored extension payload.  The
    // payload is semantic evidence; it is not interpreted as a new lifecycle
    // or applicability authority by this materializer.
    let entity_type = text(raw.get("entity_type"));
    let Some(entity_type) = entity_type.filter(|value| !value.is_empty()) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_extension_entity",
            "extension entity requires a non-empty entity_type",
            &format!("{path}.entity_type"),
        );
        return None;
    };
    let Some(properties) = raw
        .get("properties")
        .filter(|value| value.as_object().is_some())
    else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_extension_entity",
            "extension entity requires an object properties payload",
            &format!("{path}.properties"),
        );
        return None;
    };
    let Some(rationale) = text(raw.get("rationale")).filter(|value| !value.is_empty()) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_extension_entity",
            "extension entity requires a non-empty rationale",
            &format!("{path}.rationale"),
        );
        return None;
    };
    let mut entity = regular_entity(
        raw,
        &entity_type,
        "extension",
        None,
        provider,
        source,
        source_contract,
        identity_map,
        diagnostics,
        path,
    )?;
    if let Json::Object(values) = &mut entity {
        values.insert(
            "extension".into(),
            object([
                ("properties".into(), properties.clone()),
                ("rationale".into(), string(rationale)),
            ]),
        );
    }
    Some(entity)
}

fn normative_proposition(
    raw: &BTreeMap<String, Json>,
    parent: &Identity,
    provider: &BTreeMap<String, Json>,
    source: &BTreeMap<String, Json>,
    source_contract: &Json,
    identity_map: &BTreeMap<String, String>,
    diagnostics: &mut Vec<Json>,
    path: &str,
) -> Option<Json> {
    let identity = identity(raw, identity_map, diagnostics, path)?;
    let statement = text(raw.get("statement"));
    let force = text(raw.get("normative_force"));
    let scope = text(raw.get("scope"));
    if statement.as_deref().is_none_or(str::is_empty) {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_normative_proposition",
            "NormativeProposition requires a non-empty statement",
            &format!("{path}.statement"),
        );
        return None;
    }
    if !matches!(
        force.as_deref(),
        Some("MUST" | "MUST NOT" | "SHOULD" | "SHOULD NOT" | "MAY")
    ) {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_normative_force",
            "normative_force is outside the closed governed vocabulary",
            &format!("{path}.normative_force"),
        );
        return None;
    }
    if scope.as_deref().is_none_or(str::is_empty) {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_normative_proposition",
            "NormativeProposition requires an explicit scope",
            &format!("{path}.scope"),
        );
        return None;
    }
    let provider_key = format!(
        "{}:{}",
        text(provider.get("kind")).unwrap_or_default(),
        text(provider.get("architectureNamespace")).unwrap_or_default()
    );
    let source_ref = text(source.get("sourceRef")).unwrap_or_default();
    let artifact_path = text(source.get("artifactPath")).unwrap_or_default();
    let content_digest = text(source.get("contentDigest")).unwrap_or_default();
    let mut values = BTreeMap::from([
        ("id".into(), string(identity.id.clone())),
        ("alias_id".into(), string(identity.alias_id.clone())),
        ("alias_name".into(), string(identity.alias_name.clone())),
        (
            "alias_ref".into(),
            string(format!("{provider_key}:{}", identity.alias_id)),
        ),
        ("entity_type".into(), string("normative_proposition")),
        ("name".into(), string(identity.alias_name.clone())),
        (
            "summary".into(),
            string(statement.clone().unwrap_or_default()),
        ),
        (
            "uri".into(),
            string(format!(
                "adr://{}/{}",
                text(provider.get("architectureNamespace")).unwrap_or_default(),
                identity.id
            )),
        ),
        (
            "created_at".into(),
            string(text(source.get("createdAt")).unwrap_or_else(|| "unknown".into())),
        ),
        ("statement".into(), string(statement.unwrap_or_default())),
        ("normative_force".into(), string(force.unwrap_or_default())),
        ("scope".into(), string(scope.unwrap_or_default())),
        (
            "declaring_adr".into(),
            object([
                ("provider".into(), string(provider_key.clone())),
                ("id".into(), string(parent.id.clone())),
                ("alias_id".into(), string(parent.alias_id.clone())),
                ("alias_name".into(), string(parent.alias_name.clone())),
            ]),
        ),
        (
            "source_artifact".into(),
            source_artifact_value(
                "authoring_adr",
                &source_ref,
                &artifact_path,
                &content_digest,
            ),
        ),
        (
            "source_contract".into(),
            normalized_source_contract(source_contract),
        ),
        (
            "canonical_source".into(),
            object([
                ("source_type".into(), string("authoring_adr")),
                ("source_ref".into(), string(source_ref.clone())),
                ("artifact_path".into(), string(artifact_path.clone())),
                ("content_digest".into(), string(content_digest.clone())),
                ("provider".into(), string(provider_key.clone())),
            ]),
        ),
        (
            "source_refs".into(),
            Json::Array(vec![string(source_ref.clone())]),
        ),
        (
            "completeness".into(),
            object([
                ("status".into(), string("complete")),
                ("missing_fields".into(), Json::Array(Vec::new())),
            ]),
        ),
        (
            "provenance".into(),
            object([
                ("provider".into(), string(provider_key)),
                ("source_ref".into(), string(source_ref)),
                ("artifact_path".into(), string(artifact_path)),
                ("classification".into(), string("explicit")),
                ("declaring_adr".into(), string(parent.id.clone())),
            ]),
        ),
    ]);
    let fingerprint =
        digest_json(&Json::Object(values.clone())).unwrap_or_else(|_| digest_bytes(&[]));
    values.insert("entity_fingerprint".into(), string(fingerprint));
    Some(Json::Object(values))
}

fn relationship_record(
    raw: &BTreeMap<String, Json>,
    source: &BTreeMap<String, Json>,
    identity_map: &BTreeMap<String, String>,
    diagnostics: &mut Vec<Json>,
    path: &str,
) -> Option<Json> {
    let id = identity(raw, identity_map, diagnostics, path)?;
    let from = text(raw.get("from_entity_id").or_else(|| raw.get("from_id")));
    let to = text(raw.get("to_entity_id").or_else(|| raw.get("to_id")));
    let relationship_type =
        text(raw.get("relationship_type")).unwrap_or_else(|| "related_to".into());
    let (Some(from), Some(to)) = (from, to) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.invalid_source_relationship",
            "relationship requires from and to entity identities",
            path,
        );
        return None;
    };
    let from = map_source_id(
        &from,
        identity_map,
        diagnostics,
        &format!("{path}.from_entity_id"),
    )?;
    let to = map_source_id(
        &to,
        identity_map,
        diagnostics,
        &format!("{path}.to_entity_id"),
    )?;
    let source_ref = text(source.get("sourceRef")).unwrap_or_default();
    let mut values = BTreeMap::from([
        ("record_kind".into(), string("canonical")),
        ("id".into(), string(id.id)),
        ("alias_id".into(), string(id.alias_id)),
        ("alias_name".into(), string(id.alias_name)),
        ("relationship_type".into(), string(&relationship_type)),
        ("from_entity_id".into(), string(from)),
        ("to_entity_id".into(), string(to)),
        ("source_owner_id".into(), Json::Null),
        ("source_pointer".into(), string(path)),
        ("provenance_classification".into(), string("explicit")),
        ("evidence".into(), Json::Array(Vec::new())),
        ("canonical_source_ref".into(), string(source_ref)),
    ]);
    if relationship_type.contains(':') {
        let Some(properties) = raw
            .get("properties")
            .filter(|value| value.as_object().is_some())
        else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.invalid_source_relationship",
                "extension relationship requires an object properties payload",
                &format!("{path}.properties"),
            );
            return None;
        };
        let Some(rationale) = text(raw.get("rationale")).filter(|value| !value.is_empty()) else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.invalid_source_relationship",
                "extension relationship requires a non-empty rationale",
                &format!("{path}.rationale"),
            );
            return None;
        };
        values.insert(
            // The v2.3 relationship schema admits namespaced relationship
            // types in the canonical branch, while its external extension
            // pointer is not rooted in the supplied normalized-entity
            // resource.  Preserve the validated extension payload as explicit
            // evidence so exact closure validation remains schema-governed and
            // no authored rationale or property is discarded.
            "evidence".into(),
            Json::Array(vec![object([
                ("source_extension_properties".into(), properties.clone()),
                ("source_extension_rationale".into(), string(rationale)),
            ])]),
        );
    }
    Some(Json::Object(values))
}

fn limitation(binding: &Json, capability: &str) -> Json {
    object([
        ("sourceContractRef".into(), source_identity_ref(binding)),
        ("semanticCapability".into(), string(capability)),
        (
            "classification".into(),
            string("not_expressible_by_source_contract"),
        ),
    ])
}

fn sort_json_array(values: &mut Vec<Json>, key: impl Fn(&Json) -> String) {
    values.sort_by_key(key);
}

fn source_basis_with_sorted_artifacts(source_basis: &Json, artifacts: &[Json]) -> Json {
    let Some(mut values) = source_basis.as_object().cloned() else {
        return Json::Null;
    };
    let mut sorted = artifacts.to_vec();
    sorted.sort_by_key(|artifact| {
        (
            text(
                artifact
                    .as_object()
                    .and_then(|value| value.get("sourceRef")),
            )
            .unwrap_or_default(),
            text(
                artifact
                    .as_object()
                    .and_then(|value| value.get("artifactPath")),
            )
            .unwrap_or_default(),
        )
    });
    values.insert("artifacts".into(), Json::Array(sorted));
    Json::Object(values)
}

fn state_projection(value: &Json, key: Option<&str>) -> Option<Json> {
    // Source locators and transport provenance describe how the state was
    // acquired, not the normalized architectural meaning. Excluding them is
    // what lets a sourceRevision-only change preserve the authority state
    // fingerprint. The provider is supplied separately below and is retained.
    if matches!(
        key,
        Some(
            "fingerprint"
                | "canonical_source"
                | "source_refs"
                | "source_artifact"
                | "source_contract"
                | "provenance"
        )
    ) {
        return None;
    }
    match value {
        Json::Object(values) => {
            let mut projected = BTreeMap::new();
            for (child_key, child) in values {
                if let Some(child) = state_projection(child, Some(child_key)) {
                    projected.insert(child_key.clone(), child);
                }
            }
            Some(Json::Object(projected))
        }
        Json::Array(values) => Some(Json::Array(
            values
                .iter()
                .filter_map(|child| state_projection(child, None))
                .collect(),
        )),
        _ => Some(value.clone()),
    }
}

fn authority_state_fingerprint(
    provider: &Json,
    normalized_model: &Json,
    limitations: &[Json],
) -> String {
    let projected_model = state_projection(normalized_model, None).unwrap_or(Json::Null);
    let projected_limitations = Json::Array(
        limitations
            .iter()
            .filter_map(|limitation| {
                let members = limitation.as_object()?;
                Some(object([
                    (
                        "semanticCapability".into(),
                        members.get("semanticCapability")?.clone(),
                    ),
                    (
                        "classification".into(),
                        members.get("classification")?.clone(),
                    ),
                ]))
            })
            .collect(),
    );
    let preimage = object([
        ("scheme".into(), string("adr-kit.authority-state/v1")),
        ("provider".into(), provider.clone()),
        (
            "state".into(),
            object([
                ("normalizedModel".into(), projected_model),
                ("sourceCapabilityLimitations".into(), projected_limitations),
            ]),
        ),
    ]);
    let mut canonical = String::new();
    if canonicalize_value(&preimage, &mut canonical).is_err() {
        return format!(
            "{AUTHORITY_FINGERPRINT_SCHEME}{}",
            digest_bytes(&[]).trim_start_matches("sha256:")
        );
    }
    format!(
        "{AUTHORITY_FINGERPRINT_SCHEME}{}",
        digest_bytes(canonical.as_bytes()).trim_start_matches("sha256:")
    )
}

fn result(
    outcome: &str,
    authority_provider: Json,
    source_basis: Json,
    closure: Vec<Json>,
    set_id: Option<String>,
    fingerprint: Option<String>,
    normalized_model: Json,
    limitations: Vec<Json>,
    provenance: Json,
    mut diagnostics: Vec<Json>,
) -> Json {
    super::semantic_contract::sort_diagnostics(&mut diagnostics);
    let mut values = BTreeMap::new();
    values.insert("core_contract_version".into(), string("1.1"));
    values.insert("operation".into(), string(OPERATION));
    values.insert("success".into(), Json::Bool(outcome == "Materialized"));
    values.insert("outcome".into(), string(outcome));
    values.insert(
        "materializationContractVersion".into(),
        string(MATERIALIZATION_VERSION),
    );
    values.insert("authorityProvider".into(), authority_provider);
    values.insert("sourceBasis".into(), source_basis);
    values.insert("sourceContractClosure".into(), Json::Array(closure));
    values.insert(
        "semanticBasis".into(),
        object([
            (
                "semanticContractSetId".into(),
                set_id.map(string).unwrap_or(Json::Null),
            ),
            (
                "authorityStateFingerprint".into(),
                fingerprint.map(string).unwrap_or(Json::Null),
            ),
        ]),
    );
    values.insert("normalizedModel".into(), normalized_model);
    values.insert(
        "sourceCapabilityLimitations".into(),
        Json::Array(limitations),
    );
    values.insert("providerProvenance".into(), provenance);
    values.insert("diagnostics".into(), Json::Array(diagnostics));
    Json::Object(values)
}

fn failure(
    outcome: &str,
    authority_provider: Json,
    source_basis: Json,
    set_id: Option<String>,
    provenance: Json,
    diagnostics: Vec<Json>,
) -> Json {
    result(
        outcome,
        authority_provider,
        source_basis,
        Vec::new(),
        set_id,
        None,
        Json::Null,
        Vec::new(),
        provenance,
        diagnostics,
    )
}

fn materialize_sources(
    source_basis: &Json,
    authority_provider: &Json,
    governed_resources: &GovernedSourceResources,
    diagnostics: &mut Vec<Json>,
) -> (Json, Vec<Json>, Vec<Json>) {
    let Some(provider) = authority_provider.as_object() else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.provider_identity_required",
            "authorityProvider must be a provider-qualified object",
            "authorityProvider",
        );
        return (Json::Null, Vec::new(), Vec::new());
    };
    for key in ["kind", "architectureNamespace"] {
        if text(provider.get(key)).unwrap_or_default().is_empty() {
            diagnostic_code(
                diagnostics,
                "semantic_contract.provider_identity_required",
                format!("authorityProvider.{key} must be non-empty"),
                &format!("authorityProvider.{key}"),
            );
        }
    }
    let Some(source) = source_basis.as_object() else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_basis_unavailable",
            "the sealed source basis is unavailable",
            "sourceBasis",
        );
        return (Json::Null, Vec::new(), Vec::new());
    };
    if bool_value(source.get("sealed")) != Some(true) {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_basis_not_sealed",
            "sourceBasis.sealed must be true",
            "sourceBasis.sealed",
        );
    }
    for key in ["providerSourceIdentity", "sourceRevision"] {
        if text(source.get(key)).unwrap_or_default().is_empty() {
            diagnostic_code(
                diagnostics,
                "semantic_contract.incomplete_source_basis",
                format!("sourceBasis.{key} must be non-empty"),
                &format!("sourceBasis.{key}"),
            );
        }
    }
    let Some(raw_artifacts) = array(source.get("artifacts")) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.incomplete_source_basis",
            "sourceBasis.artifacts must be an array",
            "sourceBasis.artifacts",
        );
        return (Json::Null, Vec::new(), Vec::new());
    };
    if raw_artifacts.is_empty() {
        diagnostic_code(
            diagnostics,
            "semantic_contract.incomplete_source_basis",
            "sourceBasis.artifacts must not be empty",
            "sourceBasis.artifacts",
        );
    }
    let identity_map = identity_map(source.get("legacyIdentityMap"), provider, diagnostics);
    let mut seen_refs = BTreeSet::new();
    let mut seen_source_ids = BTreeSet::new();
    let mut identity_index = BTreeSet::new();
    for raw_artifact in raw_artifacts {
        if let Some(document) = raw_artifact
            .as_object()
            .and_then(|artifact| artifact.get("document"))
            .and_then(Json::as_object)
        {
            collect_candidate_identities(document, &identity_map, &mut identity_index);
        }
    }
    let mut artifacts = Vec::new();
    let mut closure_by_key = BTreeMap::new();
    let mut limitations = BTreeMap::new();
    let mut entities = Vec::new();
    let mut relationships = Vec::new();
    let mut unresolved = Vec::new();
    let mut known_entity_ids = BTreeSet::new();
    let mut source_coverage = Vec::new();

    let mut artifact_order = raw_artifacts.iter().enumerate().collect::<Vec<_>>();
    artifact_order.sort_by_key(|(_, artifact)| {
        let artifact = artifact.as_object();
        (
            text(artifact.and_then(|value| value.get("sourceRef"))).unwrap_or_default(),
            text(artifact.and_then(|value| value.get("artifactPath"))).unwrap_or_default(),
            text(artifact.and_then(|value| value.get("contentDigest"))).unwrap_or_default(),
        )
    });
    for (index, (_original_index, raw_artifact)) in artifact_order.iter().enumerate() {
        let path = format!("sourceBasis.artifacts[{index}]");
        let Some(artifact) = raw_artifact.as_object() else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.invalid_source_artifact",
                "source artifact must be an object",
                &path,
            );
            continue;
        };
        let source_ref = text(artifact.get("sourceRef")).unwrap_or_default();
        let artifact_path = text(artifact.get("artifactPath")).unwrap_or_default();
        let content_digest = text(artifact.get("contentDigest")).unwrap_or_default();
        if source_ref.is_empty() || artifact_path.is_empty() || !is_sha256(&content_digest) {
            diagnostic_code(
                diagnostics,
                "semantic_contract.incomplete_source_artifact",
                "sourceRef, artifactPath, and a valid contentDigest are required",
                &path,
            );
            continue;
        }
        let Some(document) = artifact.get("document").and_then(Json::as_object) else {
            diagnostic_code(
                diagnostics,
                "semantic_contract.incomplete_source_artifact",
                "source artifact requires the exact host-parsed document",
                &format!("{path}.document"),
            );
            continue;
        };
        let source_version = text(
            artifact
                .get("sourceContract")
                .and_then(Json::as_object)
                .and_then(|value| value.get("version")),
        )
        .unwrap_or_default();
        let declared_version = text(document.get("schema_version")).unwrap_or_default();
        if declared_version != source_version {
            diagnostic_code(
                diagnostics,
                "semantic_contract.artifact_contract_mismatch",
                "document schema_version does not match its artifact-level source-contract binding",
                &format!("{path}.document.schema_version"),
            );
            continue;
        }
        let validation_path = format!("{path}.document");
        let qualification_diagnostic_count = diagnostics.len();
        let Some((closure_key, binding)) =
            source_contract(artifact, document, governed_resources, diagnostics, &path)
        else {
            continue;
        };
        if diagnostics.len() == qualification_diagnostic_count {
            let schema_key = binding
                .as_object()
                .and_then(|value| value.get("schemaResource"))
                .and_then(Json::as_object)
                .and_then(|value| text(value.get("canonicalResourceKey")))
                .unwrap_or_default();
            if let Err(error) = schema_validation::validate(
                &governed_resources.contents,
                &schema_key,
                &Json::Object(document.clone()),
            ) {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.invalid_source_document",
                    error.message,
                    &if error.path.is_empty() {
                        validation_path.clone()
                    } else {
                        format!("{validation_path}.{}", error.path)
                    },
                );
                continue;
            }
            // The v1.5 schema intentionally keeps the common envelope open,
            // while the accepted architecture-interpretation rule makes the
            // NP field source-contract-inexpressible for that version.  This
            // is semantic qualification, not a second schema rendition.
            if source_version == "1.5" && document.contains_key("normative_propositions") {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.invalid_source_document",
                    "authoring 1.5 cannot declare normative_propositions",
                    &format!("{validation_path}.normative_propositions"),
                );
                continue;
            }
        } else {
            continue;
        }
        if !seen_refs.insert(source_ref.clone()) {
            diagnostic_code(
                diagnostics,
                "semantic_contract.duplicate_source_identity",
                "sourceRef occurs more than once in the sealed source basis",
                &format!("{path}.sourceRef"),
            );
        }
        let root_identity = identity(
            document,
            &identity_map,
            diagnostics,
            &format!("{path}.document"),
        );
        if let Some(root_identity) = &root_identity {
            if !seen_source_ids.insert(root_identity.source_id.clone()) {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.duplicate_source_identity",
                    "source declaration identity occurs more than once in the sealed source basis",
                    &format!("{path}.document.id"),
                );
            }
        }
        // The result retains the exact qualified binding.  It deliberately
        // does not collapse the imported schema closure into an aggregate
        // fingerprint: the closure is the authority evidence.
        let closure_ref = source_identity_ref(&binding);
        // Different authoring top-level schemas at the same version are
        // distinct qualified bindings.  Deduplicate only the exact binding,
        // not merely family@version.
        closure_by_key.entry(closure_key).or_insert(closure_ref);
        let mut output_artifact = artifact.clone();
        output_artifact.insert("sourceContract".into(), binding.clone());
        artifacts.push(Json::Object(output_artifact));
        let source_revision = text(source.get("sourceRevision"));
        let source = BTreeMap::from([
            ("sourceRef".into(), string(source_ref.clone())),
            ("artifactPath".into(), string(artifact_path.clone())),
            ("contentDigest".into(), string(content_digest.clone())),
            (
                "createdAt".into(),
                text(document.get("created_date"))
                    .map(string)
                    .unwrap_or(Json::Null),
            ),
            (
                "sourceRevision".into(),
                source_revision.map(string).unwrap_or(Json::Null),
            ),
        ]);
        let adr_type = text(document.get("adr_type")).unwrap_or_else(|| "logical".into());
        let (entity_type, declaration_kind) = match adr_type.as_str() {
            "logical" => ("adr", "logical"),
            "physical-system" => ("system", "physical-system"),
            "physical-component" => ("component", "physical-component"),
            _ => {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.unmapped_source_kind",
                    "source adr_type is not supported by the architecture-interpretation contract",
                    &format!("{path}.document.adr_type"),
                );
                continue;
            }
        };
        let Some(root_identity) = root_identity else {
            continue;
        };
        reject_unmapped_source_fields(
            document,
            &adr_type,
            &format!("{path}.document"),
            diagnostics,
        );
        if matches!(adr_type.as_str(), "physical-system" | "physical-component") {
            source_coverage.push(physical_source_coverage(
                document,
                &adr_type,
                &artifact_path,
            ));
        }
        if !known_entity_ids.insert(root_identity.id.clone()) {
            diagnostic_code(
                diagnostics,
                "semantic_contract.duplicate_canonical_definition",
                "two source declarations resolve to one canonical identity",
                &format!("{path}.document.id"),
            );
        }
        if let Some(mut entity) = regular_entity(
            document,
            entity_type,
            declaration_kind,
            None,
            provider,
            &source,
            &binding,
            &identity_map,
            diagnostics,
            &format!("{path}.document"),
        ) {
            if matches!(adr_type.as_str(), "physical-system" | "physical-component") {
                let fields = if adr_type == "physical-system" {
                    [
                        "implements_logical",
                        "technology_stack",
                        "system",
                        "system_boundaries",
                        "component_topology",
                        "integration_patterns",
                        "data_flows",
                        "references_components",
                        "scalability_strategy",
                        "failure_modes",
                    ]
                    .as_slice()
                } else {
                    [
                        "implements_logical",
                        "technology_stack",
                        "implements_system",
                        "component_specifications",
                    ]
                    .as_slice()
                };
                retain_source_semantics(&mut entity, document, fields);
            }
            entities.push(entity);
        }
        if adr_type == "physical-system" {
            if let Some(system) = document.get("system").and_then(Json::as_object) {
                if let Some(mut entity) = regular_entity(
                    system,
                    "system",
                    "physical-system",
                    Some(&root_identity),
                    provider,
                    &source,
                    &binding,
                    &identity_map,
                    diagnostics,
                    &format!("{path}.document.system"),
                ) {
                    retain_source_semantics(&mut entity, system, &["id", "alias_id", "alias_name"]);
                    if let Some(id) = entity.as_object().and_then(|value| text(value.get("id"))) {
                        if !known_entity_ids.insert(id) {
                            diagnostic_code(
                                diagnostics,
                                "semantic_contract.duplicate_canonical_definition",
                                "two source declarations resolve to one canonical identity",
                                &format!("{path}.document.system.id"),
                            );
                        }
                    }
                    entities.push(entity);
                }
            }
        }
        if adr_type == "physical-component" {
            if let Some(specifications) = array(document.get("component_specifications")) {
                for (specification_index, specification) in specifications.iter().enumerate() {
                    let specification_path =
                        format!("{path}.document.component_specifications[{specification_index}]");
                    let Some(specification) = specification.as_object() else {
                        continue;
                    };
                    if let Some(mut entity) = regular_entity(
                        specification,
                        "component",
                        "physical-component",
                        Some(&root_identity),
                        provider,
                        &source,
                        &binding,
                        &identity_map,
                        diagnostics,
                        &specification_path,
                    ) {
                        retain_source_semantics(
                            &mut entity,
                            specification,
                            &[
                                "id",
                                "alias_id",
                                "alias_name",
                                "name",
                                "type",
                                "responsibilities",
                                "generation_context",
                                "interfaces",
                            ],
                        );
                        if let Some(id) = entity.as_object().and_then(|value| text(value.get("id")))
                        {
                            if !known_entity_ids.insert(id) {
                                diagnostic_code(
                                    diagnostics,
                                    "semantic_contract.duplicate_canonical_definition",
                                    "two source declarations resolve to one canonical identity",
                                    &format!("{specification_path}.id"),
                                );
                            }
                        }
                        entities.push(entity);
                    }
                    if let Some(interfaces) = array(specification.get("interfaces")) {
                        for (interface_index, interface) in interfaces.iter().enumerate() {
                            let interface_path =
                                format!("{specification_path}.interfaces[{interface_index}]");
                            let Some(interface) = interface.as_object() else {
                                continue;
                            };
                            if let Some(mut entity) = regular_entity(
                                interface,
                                "interface",
                                "physical-component",
                                Some(&root_identity),
                                provider,
                                &source,
                                &binding,
                                &identity_map,
                                diagnostics,
                                &interface_path,
                            ) {
                                retain_source_semantics(
                                    &mut entity,
                                    interface,
                                    &["id", "alias_id", "alias_name", "type", "specification"],
                                );
                                if let Some(id) =
                                    entity.as_object().and_then(|value| text(value.get("id")))
                                {
                                    if !known_entity_ids.insert(id) {
                                        diagnostic_code(
                                            diagnostics,
                                            "semantic_contract.duplicate_canonical_definition",
                                            "two source declarations resolve to one canonical identity",
                                            &format!("{interface_path}.id"),
                                        );
                                    }
                                }
                                entities.push(entity);
                            }
                        }
                    }
                }
            }
        }
        for field in ["implements_logical", "implements_system"] {
            if let Some(references) = array(document.get(field)) {
                for (reference_index, reference) in references.iter().enumerate() {
                    let Some(reference) = reference.as_str() else {
                        continue;
                    };
                    let Some(target) = map_source_id(
                        reference,
                        &identity_map,
                        diagnostics,
                        &format!("{path}.document.{field}[{reference_index}]"),
                    ) else {
                        continue;
                    };
                    relationships.push(compatibility_relationship(
                        "implements",
                        &root_identity.id,
                        &target,
                        &source_ref,
                        &root_identity.id,
                        &format!("{path}.document.{field}[{reference_index}]"),
                        None,
                    ));
                }
            }
        }
        if adr_type == "physical-system" {
            if let Some(topology) = document.get("component_topology").and_then(Json::as_object) {
                let handles = topology
                    .get("components")
                    .and_then(Json::as_array)
                    .into_iter()
                    .flatten()
                    .filter_map(Json::as_object)
                    .filter_map(|component| {
                        Some((
                            text(component.get("id"))?,
                            text(component.get("component_ref"))?,
                        ))
                    })
                    .collect::<BTreeMap<_, _>>();
                // The accepted normalized-model vocabulary defines explicit
                // PS topology membership as a system-to-component
                // `composed_of` relationship.  The local TOPO handle is only
                // an addressing aid; the authored component_ref is the
                // canonical endpoint.  Unknown component references remain
                // first-class unresolved evidence and never become a
                // relationship with a fabricated endpoint.
                if let Some(system) = document.get("system").and_then(Json::as_object) {
                    let system_id = text(system.get("id"))
                        .and_then(|id| map_source_id(&id, &identity_map, diagnostics, &format!("{path}.document.system.id")));
                    if let Some(system_id) = system_id {
                        if let Some(topology_components) =
                            topology.get("components").and_then(Json::as_array)
                        {
                            for (component_index, component) in
                                topology_components.iter().enumerate()
                            {
                                let component_path = format!(
                                    "{path}.document.component_topology.components[{component_index}]"
                                );
                                let Some(component) = component.as_object() else {
                                    continue;
                                };
                                let component_ref = text(component.get("component_ref"))
                                    .unwrap_or_default();
                                if known_entity_ids.contains(&component_ref) {
                                    relationships.push(compatibility_relationship(
                                        "composed_of",
                                        &system_id,
                                        &component_ref,
                                        &source_ref,
                                        &root_identity.id,
                                        &component_path,
                                        Some(Json::Array(vec![Json::Object(component.clone())])),
                                    ));
                                } else {
                                    unresolved.push(unresolved_relationship(
                                        &source_ref,
                                        &component_path,
                                        &component_ref,
                                        "composed_of",
                                        &system_id,
                                        &component_ref,
                                    ));
                                }
                            }
                        }
                    }
                }
                if let Some(topology_relationships) =
                    topology.get("relationships").and_then(Json::as_array)
                {
                    for (relationship_index, topology_relationship) in
                        topology_relationships.iter().enumerate()
                    {
                        let relationship_path = format!("{path}.document.component_topology.relationships[{relationship_index}]");
                        let Some(topology_relationship) = topology_relationship.as_object() else {
                            continue;
                        };
                        let from_handle =
                            text(topology_relationship.get("from")).unwrap_or_default();
                        let to_handle = text(topology_relationship.get("to")).unwrap_or_default();
                        let relationship_type =
                            text(topology_relationship.get("type")).unwrap_or_default();
                        let from = handles.get(&from_handle).cloned().unwrap_or_default();
                        let to = handles.get(&to_handle).cloned().unwrap_or_default();
                        if from.is_empty() || to.is_empty() {
                            unresolved.push(unresolved_relationship(
                                &source_ref,
                                &relationship_path,
                                if from.is_empty() {
                                    &from_handle
                                } else {
                                    &to_handle
                                },
                                &relationship_type,
                                &from,
                                &to,
                            ));
                        } else {
                            relationships.push(compatibility_relationship(
                                &relationship_type,
                                &from,
                                &to,
                                &source_ref,
                                &root_identity.id,
                                &relationship_path,
                                Some(Json::Array(vec![Json::Object(
                                    topology_relationship.clone(),
                                )])),
                            ));
                        }
                    }
                }
            }
        }
        for (field, child_type) in [
            ("decisions", "decision"),
            ("invariants", "invariant"),
            ("constraints", "constraint"),
            ("non_functional_requirements", "nfr"),
            ("gaps", "gap"),
        ] {
            if let Some(values) = array(document.get(field)) {
                for (child_index, child) in values.iter().enumerate() {
                    let child_path = format!("{path}.document.{field}[{child_index}]");
                    let Some(child) = child.as_object() else {
                        diagnostic_code(
                            diagnostics,
                            "semantic_contract.invalid_source_declaration",
                            "source declaration must be an object",
                            &child_path,
                        );
                        continue;
                    };
                    if let Some(entity) = regular_entity(
                        child,
                        child_type,
                        declaration_kind,
                        Some(&root_identity),
                        provider,
                        &source,
                        &binding,
                        &identity_map,
                        diagnostics,
                        &child_path,
                    ) {
                        if let Some(id) = entity.as_object().and_then(|value| text(value.get("id")))
                        {
                            if !known_entity_ids.insert(id) {
                                diagnostic_code(
                                    diagnostics,
                                    "semantic_contract.duplicate_canonical_definition",
                                    "two source declarations resolve to one canonical identity",
                                    &child_path,
                                );
                            }
                        }
                        entities.push(entity);
                    }
                }
            }
        }
        if let Some(raw_extensions) = array(document.get("extension_entities")) {
            for (extension_index, extension) in raw_extensions.iter().enumerate() {
                let extension_path =
                    format!("{path}.document.extension_entities[{extension_index}]");
                let Some(extension) = extension.as_object() else {
                    diagnostic_code(
                        diagnostics,
                        "semantic_contract.invalid_extension_entity",
                        "extension entity must be an object",
                        &extension_path,
                    );
                    continue;
                };
                if let Some(entity) = extension_entity(
                    extension,
                    provider,
                    &source,
                    &binding,
                    &identity_map,
                    diagnostics,
                    &extension_path,
                ) {
                    if let Some(id) = entity.as_object().and_then(|value| text(value.get("id"))) {
                        if !known_entity_ids.insert(id) {
                            diagnostic_code(
                                diagnostics,
                                "semantic_contract.duplicate_canonical_definition",
                                "two source declarations resolve to one canonical identity",
                                &extension_path,
                            );
                        }
                    }
                    entities.push(entity);
                }
            }
        }
        if source_version == "1.5" {
            let limitation_key = format!(
                "{}:{}",
                text(
                    binding
                        .as_object()
                        .and_then(|value| value.get("schemaResource"))
                        .and_then(Json::as_object)
                        .and_then(|value| value.get("canonicalResourceKey")),
                )
                .unwrap_or_default(),
                "normative_proposition"
            );
            limitations
                .entry(limitation_key)
                .or_insert_with(|| limitation(&binding, "normative_proposition"));
        } else if let Some(values) = array(document.get("normative_propositions")) {
            for (np_index, np) in values.iter().enumerate() {
                let np_path = format!("{path}.document.normative_propositions[{np_index}]");
                let Some(np) = np.as_object() else {
                    diagnostic_code(
                        diagnostics,
                        "semantic_contract.invalid_source_declaration",
                        "normative proposition must be an object",
                        &np_path,
                    );
                    continue;
                };
                if let Some(entity) = normative_proposition(
                    np,
                    &root_identity,
                    provider,
                    &source,
                    &binding,
                    &identity_map,
                    diagnostics,
                    &np_path,
                ) {
                    if let Some(id) = entity.as_object().and_then(|value| text(value.get("id"))) {
                        if !known_entity_ids.insert(id) {
                            diagnostic_code(
                                diagnostics,
                                "semantic_contract.duplicate_canonical_definition",
                                "two source declarations resolve to one canonical identity",
                                &np_path,
                            );
                        }
                    }
                    entities.push(entity);
                }
            }
        }
        if let Some(raw_relationships) = array(document.get("extension_relationships")) {
            for (relationship_index, relationship) in raw_relationships.iter().enumerate() {
                let relationship_path =
                    format!("{path}.document.extension_relationships[{relationship_index}]");
                if let Some(relationship) = relationship.as_object() {
                    if let Some(record) = relationship_record(
                        relationship,
                        &source,
                        &identity_map,
                        diagnostics,
                        &relationship_path,
                    ) {
                        relationships.push(record);
                    }
                } else {
                    diagnostic_code(
                        diagnostics,
                        "semantic_contract.invalid_source_relationship",
                        "source relationship must be an object",
                        &relationship_path,
                    );
                }
            }
        }
        if let Some(raw_related) = array(document.get("related_adrs")) {
            for (related_index, related) in raw_related.iter().enumerate() {
                if let Some(related) = related.as_str() {
                    let canonical = if is_uuid_v7(related) {
                        related.to_owned()
                    } else {
                        identity_map.get(related).cloned().unwrap_or_default()
                    };
                    if canonical.is_empty() || !identity_index.contains(&canonical) {
                        unresolved.push(object([
                            ("kind".into(), string("unresolved_source_reference")),
                            ("reference".into(), string(related)),
                            ("source_ref".into(), string(source_ref.clone())),
                            (
                                "source_pointer".into(),
                                string(format!("document.related_adrs[{related_index}]")),
                            ),
                        ]));
                    }
                }
            }
        }
    }
    let mut admitted_relationships = Vec::new();
    for relationship in relationships {
        let Some(relationship) = relationship.as_object() else {
            continue;
        };
        let from = text(relationship.get("from_entity_id")).unwrap_or_default();
        let to = text(relationship.get("to_entity_id")).unwrap_or_default();
        if known_entity_ids.contains(&from) && known_entity_ids.contains(&to) {
            admitted_relationships.push(Json::Object(relationship.clone()));
        } else {
            unresolved.push(unresolved_relationship(
                &text(relationship.get("canonical_source_ref")).unwrap_or_default(),
                &text(relationship.get("source_pointer")).unwrap_or_default(),
                if !known_entity_ids.contains(&from) {
                    &from
                } else {
                    &to
                },
                &text(relationship.get("relationship_type")).unwrap_or_default(),
                &from,
                &to,
            ));
        }
    }
    relationships = admitted_relationships;
    sort_json_array(&mut entities, |value| {
        text(value.as_object().and_then(|object| object.get("id"))).unwrap_or_default()
    });
    sort_json_array(&mut relationships, |value| {
        text(value.as_object().and_then(|object| object.get("id"))).unwrap_or_default()
    });
    sort_json_array(&mut unresolved, |value| {
        format!(
            "{}\u{0}{}\u{0}{}",
            text(value.as_object().and_then(|object| object.get("reference"))).unwrap_or_default(),
            text(
                value
                    .as_object()
                    .and_then(|object| object.get("source_ref")),
            )
            .unwrap_or_default(),
            text(
                value
                    .as_object()
                    .and_then(|object| object.get("source_pointer")),
            )
            .unwrap_or_default()
        )
    });
    let mut limitations = limitations.into_values().collect::<Vec<_>>();
    limitations.sort_by_key(|value| {
        text(
            value
                .as_object()
                .and_then(|object| object.get("semanticCapability")),
        )
        .unwrap_or_default()
    });
    let mut closure = closure_by_key.into_values().collect::<Vec<_>>();
    closure.sort_by_key(|value| {
        (
            text(value.as_object().and_then(|object| object.get("family"))).unwrap_or_default(),
            text(value.as_object().and_then(|object| object.get("version"))).unwrap_or_default(),
            text(
                value
                    .as_object()
                    .and_then(|object| object.get("schemaResource"))
                    .and_then(Json::as_object)
                    .and_then(|resource| resource.get("canonicalResourceKey")),
            )
            .unwrap_or_default(),
        )
    });
    let source_basis = source_basis_with_sorted_artifacts(source_basis, &artifacts);
    let normalized = object([
        ("schema_version".into(), string(NORMALIZED_MODEL_VERSION)),
        ("type".into(), string("normalized_architecture_model")),
        ("mode".into(), string("normalized")),
        (
            "scope_root".into(),
            string(format!(
                "{}:{}",
                text(provider.get("kind")).unwrap_or_default(),
                text(provider.get("architectureNamespace")).unwrap_or_default()
            )),
        ),
        (
            "architecture_namespace".into(),
            string(text(provider.get("architectureNamespace")).unwrap_or_default()),
        ),
        ("fingerprint".into(), string("sha256:pending")),
        ("entities".into(), Json::Array(entities)),
        ("relationships".into(), Json::Array(relationships)),
        ("unresolved".into(), Json::Array(unresolved)),
        (
            "validation_summary".into(),
            object([
                ("source_contracts".into(), number(closure.len() as u64)),
                ("entity_count".into(), number(known_entity_ids.len() as u64)),
            ]),
        ),
        (
            "source_coverage".into(),
            object([
                (
                    "source_artifact_count".into(),
                    number(artifacts.len() as u64),
                ),
                (
                    "normative_proposition_semantics".into(),
                    string("declared-only; no applicability inferred"),
                ),
                ("physical_fields".into(), Json::Array(source_coverage)),
            ]),
        ),
    ]);
    let model_fingerprint = digest_json(&normalized).unwrap_or_else(|_| digest_bytes(&[]));
    if let Json::Object(mut values) = normalized {
        values.insert("fingerprint".into(), string(model_fingerprint));
        let model = Json::Object(values);
        return (
            source_basis,
            closure,
            vec![object([
                ("normalizedModel".into(), model),
                ("limitations".into(), Json::Array(limitations.clone())),
            ])],
        );
    }
    (source_basis, closure, vec![Json::Null])
}

fn number(value: u64) -> Json {
    Json::Number(serde_json::Number::from(value))
}

fn extract_materialized_parts(value: Json) -> (Json, Vec<Json>, Json, Vec<Json>) {
    let Some(wrapper) = value
        .as_array()
        .and_then(|values| values.first())
        .and_then(Json::as_object)
    else {
        return (Json::Null, Vec::new(), Json::Null, Vec::new());
    };
    let model = wrapper
        .get("normalizedModel")
        .cloned()
        .unwrap_or(Json::Null);
    let limitations = wrapper
        .get("limitations")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    (model, limitations, Json::Null, Vec::new())
}

fn validate_relationship_endpoint_closure(model: &Json, diagnostics: &mut Vec<Json>) -> bool {
    let Some(model) = model.as_object() else {
        return false;
    };
    let Some(entities) = model.get("entities").and_then(Json::as_array) else {
        return false;
    };
    let entity_ids = entities
        .iter()
        .filter_map(Json::as_object)
        .filter_map(|entity| text(entity.get("id")))
        .collect::<BTreeSet<_>>();
    let Some(relationships) = model.get("relationships").and_then(Json::as_array) else {
        return false;
    };
    let mut valid = true;
    for (index, relationship) in relationships.iter().enumerate() {
        let Some(relationship) = relationship.as_object() else {
            continue;
        };
        for endpoint in ["from_entity_id", "to_entity_id"] {
            let value = text(relationship.get(endpoint)).unwrap_or_default();
            if !entity_ids.contains(&value) {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.normalized_model_invalid",
                    format!("normalized relationship endpoint {endpoint} is not an emitted entity"),
                    &format!("normalizedModel.relationships[{index}].{endpoint}"),
                );
                valid = false;
            }
        }
    }
    valid
}

/// Execute the v1.1 materialization operation.  Every failure remains an
/// explicit bounded outcome; there is no partial success branch.
pub fn execute(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return failure(
            "Rejected",
            Json::Null,
            Json::Null,
            None,
            Json::Null,
            vec![diagnostic(
                "semantic_contract.materialization_request_invalid",
                "request must be an object",
                None,
            )],
        );
    };
    let requested_set_id = text(root.get("semanticContractSetId"));
    let mut request_diagnostics = Vec::new();
    if text(root.get("materializationContractVersion")).as_deref() != Some(MATERIALIZATION_VERSION)
    {
        diagnostic_code(
            &mut request_diagnostics,
            "semantic_contract.materialization_contract_version_unsupported",
            "materializationContractVersion must be 1.0",
            "materializationContractVersion",
        );
    }
    let authority_provider = root.get("authorityProvider").cloned().unwrap_or(Json::Null);
    let source_basis = root.get("sourceBasis").cloned().unwrap_or(Json::Null);
    let provenance = root
        .get("providerProvenance")
        .cloned()
        .unwrap_or(Json::Null);
    if let Some(provenance) = provenance.as_object() {
        if text(provenance.get("semanticCoreContractVersion")).as_deref() != Some("1.1") {
            diagnostic_code(
                &mut request_diagnostics,
                "semantic_contract.provider_provenance_mismatch",
                "providerProvenance.semanticCoreContractVersion must be 1.1",
                "providerProvenance.semanticCoreContractVersion",
            );
        }
        for key in ["packageVersion", "hostBinding"] {
            if text(provenance.get(key)).unwrap_or_default().is_empty() {
                diagnostic_code(
                    &mut request_diagnostics,
                    "semantic_contract.provider_provenance_required",
                    format!("providerProvenance.{key} must be non-empty"),
                    &format!("providerProvenance.{key}"),
                );
            }
        }
    } else {
        diagnostic_code(
            &mut request_diagnostics,
            "semantic_contract.provider_provenance_required",
            "providerProvenance is required and must be retained request input",
            "providerProvenance",
        );
    }
    if requested_set_id.is_none() {
        diagnostic_code(
            &mut request_diagnostics,
            "semantic_contract.semantic_contract_set_required",
            "materialization requires an explicit semanticContractSetId",
            "semanticContractSetId",
        );
    }
    let resolution = if request_diagnostics.is_empty() {
        resolve_exact_set(request, OPERATION)
    } else {
        Err(request_diagnostics.clone())
    };
    let resolution = match resolution {
        Ok(value) => value,
        Err(diagnostics) => {
            return failure(
                "Rejected",
                Json::Null,
                Json::Null,
                requested_set_id,
                Json::Null,
                diagnostics,
            );
        }
    };
    let Some(provider) = authority_provider.as_object() else {
        return failure(
            "Rejected",
            Json::Null,
            Json::Null,
            Some(resolution.set_id),
            Json::Null,
            vec![diagnostic(
                "semantic_contract.provider_identity_required",
                "authorityProvider is required",
                Some("authorityProvider".into()),
            )],
        );
    };
    let _ = provider;
    if source_basis.as_object().is_none() {
        return failure(
            "Unavailable",
            Json::Null,
            Json::Null,
            Some(resolution.set_id),
            Json::Null,
            vec![diagnostic(
                "semantic_contract.source_basis_unavailable",
                "the sealed source basis is unavailable",
                Some("sourceBasis".into()),
            )],
        );
    }
    let governed_resources = resolved_resource_view(&resolution, &mut request_diagnostics);
    validate_selected_import_ownership(&resolution, &mut request_diagnostics);
    let (materialized, closure, parts) = materialize_sources(
        &source_basis,
        &authority_provider,
        &governed_resources,
        &mut request_diagnostics,
    );
    let (normalized_model, limitations, _, _) = extract_materialized_parts(Json::Array(parts));
    if !request_diagnostics.is_empty() || normalized_model == Json::Null {
        return failure(
            "Rejected",
            Json::Null,
            Json::Null,
            Some(resolution.set_id),
            Json::Null,
            request_diagnostics,
        );
    }
    if let Err(error) = schema_validation::validate(
        &governed_resources.contents,
        // Resource identities are the qualified manifest keys, including the
        // governed `.schema` suffix.  Using the exact key keeps normalized
        // validation bound to the sealed definition closure rather than to a
        // filename or an ambient schema lookup.
        "normalized-model/2.3/schema/normalized-architecture-model.schema",
        &normalized_model,
    ) {
        diagnostic_code(
            &mut request_diagnostics,
            "semantic_contract.normalized_model_invalid",
            error.message,
            &if error.path.is_empty() {
                "normalizedModel".to_owned()
            } else {
                format!("normalizedModel.{}", error.path)
            },
        );
    }
    let _ = validate_relationship_endpoint_closure(&normalized_model, &mut request_diagnostics);
    if !request_diagnostics.is_empty() {
        return failure(
            "Rejected",
            Json::Null,
            Json::Null,
            Some(resolution.set_id),
            Json::Null,
            request_diagnostics,
        );
    }
    let fingerprint =
        authority_state_fingerprint(&authority_provider, &normalized_model, &limitations);
    result(
        "Materialized",
        authority_provider,
        materialized,
        closure,
        Some(resolution.set_id),
        Some(fingerprint),
        normalized_model,
        limitations,
        provenance,
        Vec::new(),
    )
}
