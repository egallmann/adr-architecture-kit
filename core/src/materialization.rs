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

use super::semantic_contract::canonicalize_value;
use super::semantic_contract_set::resolve_exact_set;
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

fn candidate_identity(value: Option<&Json>, identity_map: &BTreeMap<String, String>) -> Option<String> {
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
        && (bytes[bytes.len() - 1].is_ascii_lowercase()
            || bytes[bytes.len() - 1].is_ascii_digit())
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

fn is_adr_alias(value: &str, adr_type: &str) -> bool {
    let prefix = match adr_type {
        "logical" => ["ADR-L-", "ADR-V-"].as_slice(),
        "physical-system" => ["ADR-PS-"].as_slice(),
        "physical-component" => ["ADR-PC-"].as_slice(),
        _ => &[] as &[&str],
    };
    prefix.iter().any(|prefix| {
        value
            .strip_prefix(prefix)
            .is_some_and(is_four_digits)
    })
}

fn is_extension_type(value: &str) -> bool {
    let Some((namespace, local)) = value.split_once(':') else {
        return false;
    };
    !namespace.is_empty()
        && namespace.len() <= 64
        && namespace.as_bytes()[0].is_ascii_alphanumeric()
        && namespace
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"._-".contains(&byte))
        && (2..=64).contains(&local.len())
        && local.as_bytes()[0].is_ascii_lowercase()
        && local
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
}

fn is_extension_alias(value: &str) -> bool {
    let Some((prefix, suffix)) = value.split_once('-') else {
        return false;
    };
    (1..=16).contains(&prefix.len())
        && prefix.bytes().all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit())
        && is_four_digits(suffix)
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

fn source_error(
    diagnostics: &mut Vec<Json>,
    path: &str,
    message: impl Into<String>,
) {
    diagnostic_code(
        diagnostics,
        "semantic_contract.invalid_source_document",
        message,
        path,
    );
}

fn required_string(
    value: &BTreeMap<String, Json>,
    key: &str,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> Option<String> {
    match text(value.get(key)).filter(|value| !value.is_empty()) {
        Some(value) => Some(value),
        None => {
            source_error(
                diagnostics,
                &format!("{path}.{key}"),
                format!("required source field {key} must be a non-empty string"),
            );
            None
        }
    }
}

fn validate_identity_envelope(
    value: &BTreeMap<String, Json>,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let Some(id) = required_string(value, "id", path, diagnostics) else {
        return false;
    };
    let Some(alias_id) = required_string(value, "alias_id", path, diagnostics) else {
        return false;
    };
    let Some(alias_name) = required_string(value, "alias_name", path, diagnostics) else {
        return false;
    };
    let mut valid = true;
    if !is_uuid_v7(&id) {
        source_error(
            diagnostics,
            &format!("{path}.id"),
            "source identity must be UUIDv7",
        );
        valid = false;
    }
    if alias_id.is_empty() {
        source_error(diagnostics, &format!("{path}.alias_id"), "alias_id must be non-empty");
        valid = false;
    }
    if !is_lower_kebab(&alias_name) {
        source_error(
            diagnostics,
            &format!("{path}.alias_name"),
            "alias_name must use the governed lower-kebab grammar",
        );
        valid = false;
    }
    valid
}

fn validate_extension_properties(
    value: Option<&Json>,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let Some(properties) = value.and_then(Json::as_object) else {
        source_error(
            diagnostics,
            path,
            "extension properties must be an object",
        );
        return false;
    };
    let mut valid = true;
    for (key, value) in properties {
        if key.is_empty()
            || !key
                .bytes()
                .enumerate()
                .all(|(index, byte)| byte.is_ascii_lowercase() || byte.is_ascii_digit() || (byte == b'_' && index > 0))
        {
            source_error(
                diagnostics,
                &format!("{path}.{key}"),
                "extension property names must use lower snake case",
            );
            valid = false;
        }
        let scalar = matches!(value, Json::String(_) | Json::Number(_) | Json::Bool(_));
        let scalar_array = array(Some(value)).is_some_and(|values| {
            values
                .iter()
                .all(|value| matches!(value, Json::String(_) | Json::Number(_) | Json::Bool(_)))
        });
        if !scalar && !scalar_array {
            source_error(
                diagnostics,
                &format!("{path}.{key}"),
                "extension property values must be scalar or scalar arrays",
            );
            valid = false;
        }
    }
    valid
}

fn validate_extension_entity(
    value: Option<&Json>,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let Some(value) = value.and_then(Json::as_object) else {
        source_error(diagnostics, path, "extension entity must be an object");
        return false;
    };
    let mut valid = validate_identity_envelope(value, path, diagnostics);
    let entity_type = required_string(value, "entity_type", path, diagnostics);
    if !entity_type.as_deref().is_some_and(is_extension_type) {
        source_error(
            diagnostics,
            &format!("{path}.entity_type"),
            "extension entity_type is not governed",
        );
        valid = false;
    }
    if !text(value.get("alias_id")).is_some_and(|value| is_extension_alias(&value)) {
        source_error(diagnostics, &format!("{path}.alias_id"), "extension alias_id must match the governed PREFIX-#### grammar");
        valid = false;
    }
    valid &= validate_extension_properties(value.get("properties"), &format!("{path}.properties"), diagnostics);
    if required_string(value, "rationale", path, diagnostics).is_none() {
        valid = false;
    }
    let allowed = ["id", "alias_id", "alias_name", "entity_type", "properties", "rationale"];
    for key in value.keys() {
        if !allowed.contains(&key.as_str()) {
            source_error(
                diagnostics,
                &format!("{path}.{key}"),
                "extension entity contains an undeclared field",
            );
            valid = false;
        }
    }
    valid
}

fn validate_extension_relationship(
    value: Option<&Json>,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let Some(value) = value.and_then(Json::as_object) else {
        source_error(diagnostics, path, "extension relationship must be an object");
        return false;
    };
    let mut valid = validate_identity_envelope(value, path, diagnostics);
    let relationship_type = required_string(value, "relationship_type", path, diagnostics);
    if !relationship_type.as_deref().is_some_and(is_extension_type) {
        source_error(
            diagnostics,
            &format!("{path}.relationship_type"),
            "extension relationship_type is not governed",
        );
        valid = false;
    }
    if !text(value.get("alias_id")).is_some_and(|value| is_extension_alias(&value)) {
        source_error(diagnostics, &format!("{path}.alias_id"), "extension alias_id must match the governed PREFIX-#### grammar");
        valid = false;
    }
    for key in ["from_entity_id", "to_entity_id"] {
        match required_string(value, key, path, diagnostics) {
            Some(id) if is_uuid_v7(&id) => {}
            Some(_) => {
                source_error(
                    diagnostics,
                    &format!("{path}.{key}"),
                    "relationship endpoint must be UUIDv7",
                );
                valid = false;
            }
            None => valid = false,
        }
    }
    valid &= validate_extension_properties(value.get("properties"), &format!("{path}.properties"), diagnostics);
    if required_string(value, "rationale", path, diagnostics).is_none() {
        valid = false;
    }
    let allowed = [
        "id",
        "alias_id",
        "alias_name",
        "relationship_type",
        "from_entity_id",
        "to_entity_id",
        "properties",
        "rationale",
    ];
    for key in value.keys() {
        if !allowed.contains(&key.as_str()) {
            source_error(
                diagnostics,
                &format!("{path}.{key}"),
                "extension relationship contains an undeclared field",
            );
            valid = false;
        }
    }
    valid
}

fn validate_normative_proposition(
    value: Option<&Json>,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let Some(value) = value.and_then(Json::as_object) else {
        source_error(diagnostics, path, "normative proposition must be an object");
        return false;
    };
    let mut valid = validate_identity_envelope(value, path, diagnostics);
    if !text(value.get("alias_id")).is_some_and(|value| is_np_alias(&value)) {
        source_error(diagnostics, &format!("{path}.alias_id"), "normative proposition alias_id must match NP-####");
        valid = false;
    }
    let alias_id = text(value.get("alias_id"));
    if !alias_id.as_deref().is_some_and(is_np_alias) {
        source_error(
            diagnostics,
            &format!("{path}.alias_id"),
            "normative proposition alias_id must match NP-####",
        );
        valid = false;
    }
    if required_string(value, "statement", path, diagnostics).is_none()
        || required_string(value, "scope", path, diagnostics).is_none()
    {
        valid = false;
    }
    let force = text(value.get("normative_force"));
    if !matches!(
        force.as_deref(),
        Some("MUST" | "MUST NOT" | "SHOULD" | "SHOULD NOT" | "MAY")
    ) {
        source_error(
            diagnostics,
            &format!("{path}.normative_force"),
            "normative_force is outside the governed vocabulary",
        );
        valid = false;
    }
    let allowed = [
        "id",
        "alias_id",
        "alias_name",
        "statement",
        "normative_force",
        "scope",
        "rationale",
    ];
    for key in value.keys() {
        if !allowed.contains(&key.as_str()) {
            source_error(
                diagnostics,
                &format!("{path}.{key}"),
                "normative proposition contains an undeclared field",
            );
            valid = false;
        }
    }
    valid
}

fn validate_component_specification(
    value: Option<&Json>,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let Some(value) = value.and_then(Json::as_object) else {
        source_error(diagnostics, path, "component specification must be an object");
        return false;
    };
    let mut valid = validate_identity_envelope(value, path, diagnostics);
    for key in ["name", "type", "responsibilities", "generation_context"] {
        if !value.contains_key(key) {
            source_error(diagnostics, &format!("{path}.{key}"), format!("component specification requires {key}"));
            valid = false;
        }
    }
    if !matches!(text(value.get("type")).as_deref(), Some("service" | "library" | "database" | "queue" | "cache" | "gateway" | "proxy" | "worker" | "scheduler")) {
        source_error(diagnostics, &format!("{path}.type"), "component specification type is outside the governed vocabulary");
        valid = false;
    }
    let Some(generation_context) = value.get("generation_context").and_then(Json::as_object) else {
        source_error(diagnostics, &format!("{path}.generation_context"), "generation_context must be an object");
        return false;
    };
    for key in ["purpose", "key_responsibilities"] {
        if !generation_context.contains_key(key) {
            source_error(diagnostics, &format!("{path}.generation_context.{key}"), format!("generation_context requires {key}"));
            valid = false;
        }
    }
    if !array(generation_context.get("key_responsibilities")).is_some_and(|values| !values.is_empty() && values.iter().all(|value| matches!(value, Json::String(_)))) {
        source_error(diagnostics, &format!("{path}.generation_context.key_responsibilities"), "key_responsibilities must contain at least one string");
        valid = false;
    }
    if let Some(interfaces) = value.get("interfaces") {
        let Some(interfaces) = array(Some(interfaces)) else {
            source_error(diagnostics, &format!("{path}.interfaces"), "interfaces must be an array");
            return false;
        };
        if interfaces.is_empty() {
            source_error(diagnostics, &format!("{path}.interfaces"), "interfaces must not be empty when present");
            valid = false;
        }
        for (index, interface) in interfaces.iter().enumerate() {
            let interface_path = format!("{path}.interfaces[{index}]");
            let Some(interface) = interface.as_object() else {
                source_error(diagnostics, &interface_path, "interface must be an object");
                valid = false;
                continue;
            };
            if !validate_identity_envelope(interface, &interface_path, diagnostics)
                || !matches!(text(interface.get("type")).as_deref(), Some("REST" | "gRPC" | "GraphQL" | "message" | "event" | "stream" | "batch" | "CLI" | "library_api"))
                || text(interface.get("specification")).is_none()
            {
                source_error(diagnostics, &interface_path, "interface requires governed identity, type, and specification");
                valid = false;
            }
        }
    }
    valid
}

fn validate_source_document(
    document: &BTreeMap<String, Json>,
    version: &str,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let mut valid = true;
    let schema_version = required_string(document, "schema_version", path, diagnostics);
    if schema_version.as_deref() != Some(version) {
        source_error(
            diagnostics,
            &format!("{path}.schema_version"),
            "schema_version does not match the qualified source contract",
        );
        valid = false;
    }
    let Some(adr_type) = required_string(document, "adr_type", path, diagnostics) else {
        return false;
    };
    if !matches!(adr_type.as_str(), "logical" | "physical-system" | "physical-component") {
        source_error(diagnostics, &format!("{path}.adr_type"), "adr_type is not governed");
        valid = false;
    }
    if let Some(id) = text(document.get("id")) {
        if !is_uuid_v7(&id) {
            source_error(diagnostics, &format!("{path}.id"), "id must be UUIDv7");
            valid = false;
        }
    } else {
        valid = false;
        source_error(diagnostics, &format!("{path}.id"), "required source field id is missing");
    }
    if let Some(alias_id) = text(document.get("alias_id")) {
        if !is_adr_alias(&alias_id, &adr_type) {
            source_error(diagnostics, &format!("{path}.alias_id"), "alias_id does not match adr_type");
            valid = false;
        }
    } else {
        valid = false;
        source_error(diagnostics, &format!("{path}.alias_id"), "required source field alias_id is missing");
    }
    if let Some(alias_name) = text(document.get("alias_name")) {
        if !is_lower_kebab(&alias_name) {
            source_error(diagnostics, &format!("{path}.alias_name"), "alias_name is not governed");
            valid = false;
        }
    } else {
        valid = false;
        source_error(diagnostics, &format!("{path}.alias_name"), "required source field alias_name is missing");
    }
    for key in ["title", "status"] {
        if required_string(document, key, path, diagnostics).is_none() {
            valid = false;
        }
    }
    if let Some(title) = text(document.get("title")) {
        if !(5..=200).contains(&title.len()) {
            source_error(diagnostics, &format!("{path}.title"), "title length is outside the governed range");
            valid = false;
        }
    }
    if !matches!(text(document.get("status")).as_deref(), Some("proposed" | "accepted" | "deprecated" | "superseded")) {
        source_error(diagnostics, &format!("{path}.status"), "status is outside the governed vocabulary");
        valid = false;
    }
    for key in ["created_date", "modified_date"] {
        if let Some(value) = text(document.get(key)) {
            if !is_iso_date(&value) {
                source_error(diagnostics, &format!("{path}.{key}"), "date must use YYYY-MM-DD");
                valid = false;
            }
        } else if key == "created_date" {
            valid = false;
            source_error(diagnostics, &format!("{path}.{key}"), "required source date is missing");
        }
    }
    if let Some(authors) = array(document.get("authors")) {
        if authors.is_empty() || authors.iter().any(|author| !matches!(author, Json::String(_))) {
            source_error(diagnostics, &format!("{path}.authors"), "authors must contain strings and at least one author");
            valid = false;
        }
    } else {
        valid = false;
        source_error(diagnostics, &format!("{path}.authors"), "authors must be a non-empty array");
    }
    match adr_type.as_str() {
        "logical" => {
            if !matches!(document.get("context"), Some(Json::String(_))) {
                source_error(diagnostics, &format!("{path}.context"), "logical ADR requires context");
                valid = false;
            }
            if !array(document.get("decisions")).is_some_and(|values| !values.is_empty()) {
                source_error(diagnostics, &format!("{path}.decisions"), "logical ADR requires decisions");
                valid = false;
            }
        }
        "physical-system" => {
            for key in ["implements_logical", "technology_stack"] {
                if !array(document.get(key)).is_some_and(|values| !values.is_empty()) {
                    source_error(diagnostics, &format!("{path}.{key}"), format!("physical-system ADR requires {key}"));
                    valid = false;
                }
            }
            if let Some(values) = array(document.get("implements_logical")) {
                if values.iter().any(|value| !value.as_str().is_some_and(is_uuid_v7)) {
                    source_error(diagnostics, &format!("{path}.implements_logical"), "implements_logical must contain UUIDv7 identities");
                    valid = false;
                }
            }
            if !matches!(document.get("context"), Some(Json::String(_))) {
                source_error(diagnostics, &format!("{path}.context"), "physical ADR requires context");
                valid = false;
            }
            if let Some(system) = document.get("system").and_then(Json::as_object) {
                if !validate_identity_envelope(system, &format!("{path}.system"), diagnostics) {
                    valid = false;
                }
                if !text(system.get("alias_id")).is_some_and(|value| value.starts_with("SYS-") && is_four_digits(&value[4..])) {
                    source_error(diagnostics, &format!("{path}.system.alias_id"), "system alias_id must match SYS-####");
                    valid = false;
                }
            } else {
                source_error(diagnostics, &format!("{path}.system"), "physical-system ADR requires system identity");
                valid = false;
            }
        }
        "physical-component" => {
            for key in ["implements_system", "component_specifications"] {
                if !array(document.get(key)).is_some_and(|values| !values.is_empty()) {
                    source_error(diagnostics, &format!("{path}.{key}"), format!("physical-component ADR requires {key}"));
                    valid = false;
                }
            }
            if let Some(values) = array(document.get("implements_system")) {
                if values.iter().any(|value| !value.as_str().is_some_and(is_uuid_v7)) {
                    source_error(diagnostics, &format!("{path}.implements_system"), "implements_system must contain UUIDv7 identities");
                    valid = false;
                }
            }
            if !matches!(document.get("context"), Some(Json::String(_))) {
                source_error(diagnostics, &format!("{path}.context"), "physical ADR requires context");
                valid = false;
            }
            if let Some(specifications) = document.get("component_specifications") {
                if let Some(specifications) = array(Some(specifications)) {
                    for (index, specification) in specifications.iter().enumerate() {
                        valid &= validate_component_specification(Some(specification), &format!("{path}.component_specifications[{index}]"), diagnostics);
                    }
                }
            }
        }
        _ => {}
    }
    for (field, values) in [
        ("decisions", document.get("decisions")),
        ("invariants", document.get("invariants")),
        ("constraints", document.get("constraints")),
        ("non_functional_requirements", document.get("non_functional_requirements")),
        ("gaps", document.get("gaps")),
    ] {
        if let Some(value) = values {
            if array(Some(value)).is_none() {
                source_error(diagnostics, &format!("{path}.{field}"), "source declaration collection must be an array");
                valid = false;
            } else if let Some(items) = array(Some(value)) {
                for (index, item) in items.iter().enumerate() {
                    if !item.as_object().is_some_and(|item| validate_identity_envelope(item, &format!("{path}.{field}[{index}]"), diagnostics)) {
                        valid = false;
                    }
                }
            }
        }
    }
    if let Some(values) = document.get("extension_entities") {
        if let Some(values) = array(Some(values)) {
            for (index, value) in values.iter().enumerate() {
                valid &= validate_extension_entity(Some(value), &format!("{path}.extension_entities[{index}]"), diagnostics);
            }
        } else {
            source_error(diagnostics, &format!("{path}.extension_entities"), "extension_entities must be an array");
            valid = false;
        }
    }
    if let Some(values) = document.get("extension_relationships") {
        if let Some(values) = array(Some(values)) {
            for (index, value) in values.iter().enumerate() {
                valid &= validate_extension_relationship(Some(value), &format!("{path}.extension_relationships[{index}]"), diagnostics);
            }
        } else {
            source_error(diagnostics, &format!("{path}.extension_relationships"), "extension_relationships must be an array");
            valid = false;
        }
    }
    if version == "1.5" {
        if document.contains_key("normative_propositions") {
            source_error(diagnostics, &format!("{path}.normative_propositions"), "authoring 1.5 cannot declare normative_propositions");
            valid = false;
        }
    } else if let Some(values) = document.get("normative_propositions") {
        if let Some(values) = array(Some(values)) {
            for (index, value) in values.iter().enumerate() {
                valid &= validate_normative_proposition(Some(value), &format!("{path}.normative_propositions[{index}]"), diagnostics);
            }
        } else {
            source_error(diagnostics, &format!("{path}.normative_propositions"), "normative_propositions must be an array");
            valid = false;
        }
    }
    valid
}

fn governed_source_resources(
    request: &Json,
    diagnostics: &mut Vec<Json>,
) -> BTreeMap<String, String> {
    let mut resources = BTreeMap::new();
    let Some(definitions) = request
        .as_object()
        .and_then(|root| root.get("definitions"))
        .and_then(Json::as_array)
    else {
        source_error(diagnostics, "definitions", "architecture-interpretation definition closure is required");
        return resources;
    };
    for bundle in definitions {
        let Some(definition) = bundle
            .as_object()
            .and_then(|bundle| bundle.get("definition"))
            .and_then(Json::as_object)
        else {
            continue;
        };
        if text(definition.get("semanticContractFamily")).as_deref() != Some("architecture-interpretation") {
            continue;
        }
        if let Some(manifest) = array(definition.get("resourceManifest")) {
            for entry in manifest {
                let Some(entry) = entry.as_object() else { continue; };
                let Some(key) = text(entry.get("canonicalResourceKey")) else { continue; };
                if let Some(digest) = text(entry.get("contentDigest")) {
                    resources.insert(key, digest);
                }
            }
        }
    }
    if resources.is_empty() {
        source_error(diagnostics, "definitions", "architecture-interpretation source resource closure is unavailable");
    }
    resources
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
        keys.push(format!("authoring/{version}/schema/adr-physical-base.schema"));
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
    governed_resources: &BTreeMap<String, String>,
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
        .find(|key| key.ends_with(match adr_type.as_str() {
            "logical" => "adr-logical.schema",
            "physical-system" => "adr-physical-system.schema",
            "physical-component" => "adr-physical-component.schema",
            _ => "adr-common.schema",
        }))
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
        if governed_resources.get(&key) != Some(&digest) {
            diagnostic_code(
                diagnostics,
                "semantic_contract.source_contract_resource_unqualified",
                "source contract resource is not the governed imported resource and digest",
                &resource_path,
            );
        }
    }
    if supplied != expected_keys
        .iter()
        .filter_map(|key| governed_resources.get(key).map(|digest| (key.clone(), digest.clone())))
        .collect::<BTreeMap<_, _>>()
    {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_closure_mismatch",
            "source contract closure does not exactly match the applicable authoring schema imports",
            &format!("{path}.sourceContract.resourceClosure"),
        );
    }
    if governed_resources.get(&schema_key) != Some(&schema_digest) {
        diagnostic_code(
            diagnostics,
            "semantic_contract.source_contract_schema_unqualified",
            "top-level schema resource does not match the governed resource digest",
            &format!("{path}.sourceContract.schemaResource"),
        );
    }
    let mut canonical_resources = resource_closure.to_vec();
    canonical_resources.sort_by_key(|resource| {
        text(resource.as_object().and_then(|value| value.get("canonicalResourceKey")))
            .unwrap_or_default()
    });
    let result = object([
        ("family".into(), string(family.clone())),
        ("version".into(), string(version.clone())),
        ("schemaResource".into(), Json::Object(schema_resource.clone())),
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
    let Some(properties) = raw.get("properties").filter(|value| value.as_object().is_some())
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
        ("source_contract".into(), normalized_source_contract(source_contract)),
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
        let Some(properties) = raw.get("properties").filter(|value| value.as_object().is_some())
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
            "extension".into(),
            object([
                ("properties".into(), properties.clone()),
                ("rationale".into(), string(rationale)),
            ]),
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
    governed_resources: &BTreeMap<String, String>,
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
        let source_version =
            text(artifact
                .get("sourceContract")
                .and_then(Json::as_object)
                .and_then(|value| value.get("version")))
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
        if !validate_source_document(document, &source_version, &format!("{path}.document"), diagnostics) {
            continue;
        }
        let Some((closure_key, binding)) = source_contract(
            artifact,
            document,
            governed_resources,
            diagnostics,
            &path,
        ) else {
            continue;
        };
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
        if !known_entity_ids.insert(root_identity.id.clone()) {
            diagnostic_code(
                diagnostics,
                "semantic_contract.duplicate_canonical_definition",
                "two source declarations resolve to one canonical identity",
                &format!("{path}.document.id"),
            );
        }
        if let Some(entity) = regular_entity(
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
            entities.push(entity);
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
                    if let Some(id) = entity.as_object().and_then(|value| text(value.get("id")))
                    {
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
            if document.contains_key("normative_propositions") {
                diagnostic_code(
                    diagnostics,
                    "semantic_contract.unsupported_source_construct",
                    "authoring 1.5 cannot declare normative_propositions",
                    &format!("{path}.document.normative_propositions"),
                );
            }
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
    sort_json_array(&mut entities, |value| {
        text(value.as_object().and_then(|object| object.get("id"))).unwrap_or_default()
    });
    sort_json_array(&mut relationships, |value| {
        text(value.as_object().and_then(|object| object.get("id"))).unwrap_or_default()
    });
    sort_json_array(&mut unresolved, |value| {
        format!(
            "{}\u{0}{}\u{0}{}",
            text(value.as_object().and_then(|object| object.get("reference")))
                .unwrap_or_default(),
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
            ]),
        ),
    ]);
    let model_fingerprint = digest_json(&normalized).unwrap_or_else(|_| digest_bytes(&[]));
    if let Json::Object(mut values) = normalized {
        values.insert("fingerprint".into(), string(model_fingerprint));
        let model = Json::Object(values);
        let _valid = validate_normalized_model(&model, diagnostics);
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

fn required_object<'a>(value: &'a BTreeMap<String, Json>, key: &str) -> Option<&'a BTreeMap<String, Json>> {
    value.get(key).and_then(Json::as_object)
}

fn normalized_field(value: &BTreeMap<String, Json>, key: &str) -> bool {
    value.contains_key(key)
}

fn validate_normalized_model(model: &Json, diagnostics: &mut Vec<Json>) -> bool {
    // This is the executable guard for the v2.3 normalized boundary.  The
    // schema remains the normative artifact, while this small structural
    // mirror prevents a malformed model from being returned when a host only
    // has the WASM core and cannot run a JSON-Schema implementation.
    let Some(model) = model.as_object() else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.normalized_model_invalid",
            "normalized model must be an object",
            "normalizedModel",
        );
        return false;
    };
    let mut valid = true;
    for (key, expected) in [
        ("schema_version", "2.3"),
        ("type", "normalized_architecture_model"),
        ("mode", "normalized"),
    ] {
        if text(model.get(key)).as_deref() != Some(expected) {
            diagnostic_code(
                diagnostics,
                "semantic_contract.normalized_model_invalid",
                format!("normalizedModel.{key} must be {expected}"),
                &format!("normalizedModel.{key}"),
            );
            valid = false;
        }
    }
    for key in ["scope_root", "fingerprint"] {
        if !normalized_field(model, key) || text(model.get(key)).unwrap_or_default().is_empty() {
            diagnostic_code(
                diagnostics,
                "semantic_contract.normalized_model_invalid",
                format!("normalizedModel.{key} is required"),
                &format!("normalizedModel.{key}"),
            );
            valid = false;
        }
    }
    if !text(model.get("fingerprint")).is_some_and(|value| is_sha256(&value)) {
        diagnostic_code(
            diagnostics,
            "semantic_contract.normalized_model_invalid",
            "normalizedModel.fingerprint must be a sha256 digest",
            "normalizedModel.fingerprint",
        );
        valid = false;
    }
    let Some(entities) = array(model.get("entities")) else {
        diagnostic_code(
            diagnostics,
            "semantic_contract.normalized_model_invalid",
            "normalizedModel.entities must be an array",
            "normalizedModel.entities",
        );
        return false;
    };
    let mut entity_ids = BTreeSet::new();
    for (index, raw_entity) in entities.iter().enumerate() {
        let path = format!("normalizedModel.entities[{index}]");
        let Some(entity) = raw_entity.as_object() else {
            diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "normalized entity must be an object", &path);
            valid = false;
            continue;
        };
        for key in [
            "id", "alias_id", "alias_name", "alias_ref", "entity_type", "name", "summary",
            "uri", "created_at", "entity_fingerprint", "canonical_source", "completeness", "provenance",
        ] {
            if !normalized_field(entity, key) {
                diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", format!("normalized entity requires {key}"), &format!("{path}.{key}"));
                valid = false;
            }
        }
        let id = text(entity.get("id")).unwrap_or_default();
        if !is_uuid_v7(&id) || !entity_ids.insert(id) {
            diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "normalized entity id must be a unique UUIDv7", &format!("{path}.id"));
            valid = false;
        }
        if !text(entity.get("alias_name")).is_some_and(|value| is_lower_kebab(&value))
            || !text(entity.get("entity_fingerprint")).is_some_and(|value| is_sha256(&value))
        {
            diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "normalized entity identity or fingerprint is invalid", &path);
            valid = false;
        }
        let entity_type = text(entity.get("entity_type")).unwrap_or_default();
        if entity_type == "normative_proposition" {
            for key in ["statement", "normative_force", "scope", "declaring_adr", "source_artifact", "source_contract"] {
                if !normalized_field(entity, key) {
                    diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", format!("normative proposition requires {key}"), &format!("{path}.{key}"));
                    valid = false;
                }
            }
            if normalized_field(entity, "lifecycle_stage") {
                diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "normative proposition must not have lifecycle_stage", &format!("{path}.lifecycle_stage"));
                valid = false;
            }
            if !text(entity.get("alias_id")).is_some_and(|value| is_np_alias(&value)) {
                diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "normative proposition alias_id is invalid", &format!("{path}.alias_id"));
                valid = false;
            }
            let Some(source_contract) = required_object(entity, "source_contract") else {
                valid = false;
                continue;
            };
            if !matches!(text(source_contract.get("family")).as_deref(), Some(value) if !value.is_empty())
                || !matches!(text(source_contract.get("version")).as_deref(), Some(value) if !value.is_empty())
                || !text(source_contract.get("fingerprint")).is_some_and(|value| is_sha256(&value))
            {
                diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "normative proposition source_contract compatibility projection is invalid", &format!("{path}.source_contract"));
                valid = false;
            }
        } else {
            if !normalized_field(entity, "lifecycle_stage") {
                diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "regular normalized entity requires lifecycle_stage", &format!("{path}.lifecycle_stage"));
                valid = false;
            }
            if entity_type.contains(':') && !normalized_field(entity, "extension") {
                diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "extension entity requires extension evidence", &format!("{path}.extension"));
                valid = false;
            }
        }
    }
    let Some(relationships) = array(model.get("relationships")) else {
        diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "normalizedModel.relationships must be an array", "normalizedModel.relationships");
        return false;
    };
    for (index, raw_relationship) in relationships.iter().enumerate() {
        let path = format!("normalizedModel.relationships[{index}]");
        let Some(relationship) = raw_relationship.as_object() else {
            diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "relationship record must be an object", &path);
            valid = false;
            continue;
        };
        for key in ["record_kind", "relationship_type", "from_entity_id", "to_entity_id", "canonical_source_ref"] {
            if !normalized_field(relationship, key) {
                diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", format!("relationship requires {key}"), &format!("{path}.{key}"));
                valid = false;
            }
        }
        if text(relationship.get("record_kind")).as_deref() != Some("canonical")
            || !text(relationship.get("id")).is_some_and(|value| is_uuid_v7(&value))
            || !text(relationship.get("from_entity_id")).is_some_and(|value| is_uuid_v7(&value))
            || !text(relationship.get("to_entity_id")).is_some_and(|value| is_uuid_v7(&value))
        {
            diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "relationship record has invalid UUID identity or kind", &path);
            valid = false;
        }
    }
    if array(model.get("unresolved")).is_none() {
        diagnostic_code(diagnostics, "semantic_contract.normalized_model_invalid", "normalizedModel.unresolved must be an array", "normalizedModel.unresolved");
        valid = false;
    }
    valid
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
    let governed_resources = governed_source_resources(request, &mut request_diagnostics);
    let (materialized, closure, parts) =
        materialize_sources(
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
