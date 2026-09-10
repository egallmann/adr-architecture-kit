//! Canonical semantic-contract identity and resource-closure rules.
//!
//! This module is the only meaning-affecting implementation of Slice B. The
//! Python and Node hosts pass ordinary JSON values to this boundary and only
//! construct idiomatic immutable views around the result. No host may sort
//! keys, normalize Unicode, or calculate a digest independently.

use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};

use sha2::{Digest, Sha256};

use super::{diagnostic, object, simple_result, string, Json};

const SCF_SCHEME: &str = "scf:v1:sha256";
const SCS_SCHEME: &str = "scs:v1:sha256";
const SCF_DOMAIN: &str = "adr-kit.semantic-contract/v1";
const SCS_DOMAIN: &str = "adr-kit.semantic-contract-set/v1";
const MAX_SAFE_INTEGER: i128 = 9_007_199_254_740_991;

#[derive(Clone, Debug)]
struct ResourceEntry {
    key: String,
    digest: String,
    role: String,
    dependencies: Vec<(String, String)>,
}

fn is_family(value: &str) -> bool {
    let bytes = value.as_bytes();
    if bytes.is_empty() || !bytes[0].is_ascii_lowercase() { return false; }
    let mut previous_hyphen = false;
    for byte in bytes {
        if byte.is_ascii_lowercase() || byte.is_ascii_digit() { previous_hyphen = false; }
        else if *byte == b'-' && !previous_hyphen { previous_hyphen = true; }
        else { return false; }
    }
    !previous_hyphen
}

fn is_version(value: &str) -> bool {
    let mut parts = value.split('.');
    let Some(major) = parts.next() else { return false; };
    let Some(minor) = parts.next() else { return false; };
    parts.next().is_none() && !major.is_empty() && !minor.is_empty()
        && major.bytes().all(|byte| byte.is_ascii_digit())
        && minor.bytes().all(|byte| byte.is_ascii_digit())
}

fn is_sha256(value: &str) -> bool {
    let Some(hex) = value.strip_prefix("sha256:") else { return false; };
    hex.len() == 64 && hex.bytes().all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn is_scf(value: &str) -> bool {
    let Some(hex) = value.strip_prefix("scf:v1:sha256:") else { return false; };
    hex.len() == 64 && hex.bytes().all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn canonical_key(value: &str) -> bool {
    !value.is_empty() && !value.starts_with('/') && !value.contains('\\')
        && !value.split('/').any(|part| part.is_empty() || part == "." || part == "..")
        && value.bytes().all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || b"._/-".contains(&byte))
}

fn role_is_conformance(role: &str) -> bool {
    matches!(role, "normative-conformance" | "interpretation-conformance" | "normalized-model-conformance")
}

fn role_is_valid(role: &str) -> bool {
    matches!(role,
        "normative-definition" | "normative-conformance" | "interpretation-rule" |
        "interpretation-conformance" | "normalized-model-schema" | "normalized-model-conformance" |
        "source-contract-schema" | "source-contract-mapping")
}

// RFC 8785 sorts object names by UTF-16 code units, not Unicode scalar value.
// This is observable for supplementary-plane characters and must be shared by
// every host through this Rust boundary.
fn utf16_cmp(left: &str, right: &str) -> Ordering { left.encode_utf16().cmp(right.encode_utf16()) }

fn canonical_string(value: &str) -> String {
    // serde_json escapes strings without Unicode normalization, as required by JCS.
    serde_json::to_string(value).expect("JSON strings must serialize")
}

fn canonical_number(value: &serde_json::Number) -> Result<String, String> {
    let raw = value.to_string();
    if !raw.contains('.') && !raw.contains('e') && !raw.contains('E') {
        let integer = raw.parse::<i128>().map_err(|_| "integer is outside the supported safe range".to_owned())?;
        if integer.abs() > MAX_SAFE_INTEGER { return Err("unsafe integer input; values beyond IEEE-754 safe range are rejected".into()); }
    }
    let number = value.as_f64().ok_or_else(|| "JSON number must be finite".to_owned())?;
    if !number.is_finite() { return Err("JSON number must be finite".into()); }

    // RFC 8785 delegates number spelling to ECMAScript Number::toString. The
    // parser is part of that boundary too: serde_json's default long-decimal
    // path uses repeated multiply/divide operations and can round a witness
    // such as 333333333.33333329 down by one ULP before formatting begins.
    // `float_roundtrip` uses its correctly-rounded decimal parser, while
    // `zmij_ecma` supplies the ECMAScript shortest-round-trip spelling and
    // notation thresholds. Both choices are semantic, not host conveniences.
    let mut buffer = zmij_ecma::Buffer::new();
    let rendered = buffer.format(number);
    let rendered = rendered.strip_suffix(".0").unwrap_or(rendered);
    let (mantissa, exponent) = match rendered.split_once('e') {
        Some((mantissa, exponent)) => (mantissa, exponent.parse::<i32>().unwrap_or(0)),
        None => (rendered, 0),
    };
    let negative = mantissa.starts_with('-');
    let unsigned = mantissa.strip_prefix('-').unwrap_or(mantissa);
    let digits = unsigned.replace('.', "");
    let decimal_index = unsigned.find('.').unwrap_or(unsigned.len()) as i32 + exponent;
    if number == 0.0 { return Ok("0".into()); }
    let sign = if negative { "-" } else { "" };
    if (-5..=21).contains(&decimal_index) {
        let body = if decimal_index <= 0 {
            format!("0.{}{}", "0".repeat((-decimal_index) as usize), digits)
        } else if decimal_index as usize >= digits.len() {
            format!("{}{}", digits, "0".repeat(decimal_index as usize - digits.len()))
        } else {
            let index = decimal_index as usize;
            format!("{}.{}", &digits[..index], &digits[index..])
        };
        Ok(format!("{sign}{body}"))
    } else {
        let first = &digits[..1];
        let tail = digits[1..].trim_end_matches('0');
        let exponent = decimal_index - 1;
        let exponent_text = if exponent >= 0 { format!("+{exponent}") } else { exponent.to_string() };
        let body = if tail.is_empty() { first.to_owned() } else { format!("{first}.{tail}") };
        Ok(format!("{sign}{body}e{exponent_text}"))
    }
}

fn canonicalize_value(value: &Json, output: &mut String) -> Result<(), String> {
    match value {
        Json::Null => output.push_str("null"),
        Json::Bool(value) => output.push_str(if *value { "true" } else { "false" }),
        Json::Number(value) => output.push_str(&canonical_number(value)?),
        Json::String(value) => output.push_str(&canonical_string(value)),
        Json::Array(values) => {
            output.push('[');
            for (index, value) in values.iter().enumerate() {
                if index != 0 { output.push(','); }
                canonicalize_value(value, output)?;
            }
            output.push(']');
        }
        Json::Object(values) => {
            output.push('{');
            let mut entries: Vec<_> = values.iter().collect();
            entries.sort_by(|left, right| utf16_cmp(left.0, right.0));
            for (index, (key, value)) in entries.iter().enumerate() {
                if index != 0 { output.push(','); }
                output.push_str(&canonical_string(key));
                output.push(':');
                canonicalize_value(value, output)?;
            }
            output.push('}');
        }
    }
    Ok(())
}

fn digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let result = hasher.finalize();
    format!("sha256:{}", result.iter().map(|byte| format!("{byte:02x}")).collect::<String>())
}

fn canonical_result(operation: &str, canonical: String, fingerprint: String) -> Json {
    let hex = canonical.as_bytes().iter().map(|byte| format!("{byte:02x}")).collect::<String>();
    let mut result = match simple_result(operation, true, Vec::new()) { Json::Object(value) => value, _ => unreachable!() };
    result.insert("canonical_preimage_json".into(), string(canonical));
    result.insert("canonical_preimage_hex".into(), string(hex));
    result.insert("fingerprint".into(), string(fingerprint));
    Json::Object(result)
}

fn canonical_failure(operation: &str, diagnostics: Vec<Json>) -> Json {
    let mut result = match simple_result(operation, false, diagnostics) { Json::Object(value) => value, _ => unreachable!() };
    result.insert("fingerprint".into(), Json::Null);
    Json::Object(result)
}

fn add_diagnostic(diagnostics: &mut Vec<Json>, code: &str, message: impl Into<String>, path: Option<String>) {
    diagnostics.push(diagnostic(code, message, path));
}

fn sort_diagnostics(diagnostics: &mut Vec<Json>) {
    diagnostics.sort_by_key(|item| {
        let object = item.as_object();
        (
            object.and_then(|value| value.get("path")).and_then(Json::as_str).unwrap_or("").to_owned(),
            object.and_then(|value| value.get("code")).and_then(Json::as_str).unwrap_or("").to_owned(),
            object.and_then(|value| value.get("message")).and_then(Json::as_str).unwrap_or("").to_owned(),
        )
    });
}

fn parse_definition(definition: &BTreeMap<String, Json>, require_fingerprint: bool, diagnostics: &mut Vec<Json>) -> Option<Vec<ResourceEntry>> {
    let allowed = ["semanticContractFamily", "semanticContractVersion", "fingerprintScheme", "resourceManifest", "frozenNormativeConformanceResources", "semanticContractFingerprint"];
    for key in definition.keys() {
        if !allowed.contains(&key.as_str()) {
            let code = if ["deprecated", "newUsePolicy", "executable", "historicalSupport", "catalogRevision", "currentSelection", "policy"].contains(&key.as_str()) { "semantic_contract.mutable_policy_field" } else { "semantic_contract.unknown_field" };
            add_diagnostic(diagnostics, code, format!("field is outside the immutable definition: {key}"), Some(key.clone()));
        }
    }
    if definition.get("semanticContractFamily").and_then(Json::as_str).filter(|value| is_family(value)).is_none() { add_diagnostic(diagnostics, "semantic_contract.invalid_family", "family must match the approved lower-case grammar", Some("semanticContractFamily".into())); }
    if definition.get("semanticContractVersion").and_then(Json::as_str).filter(|value| is_version(value)).is_none() { add_diagnostic(diagnostics, "semantic_contract.invalid_version", "version must be an exact major.minor value", Some("semanticContractVersion".into())); }
    if definition.get("fingerprintScheme").and_then(Json::as_str) != Some(SCF_SCHEME) { add_diagnostic(diagnostics, "semantic_contract.invalid_fingerprint_scheme", format!("fingerprintScheme must be {SCF_SCHEME}"), Some("fingerprintScheme".into())); }
    if require_fingerprint && !definition.contains_key("semanticContractFingerprint") { add_diagnostic(diagnostics, "semantic_contract.missing_fingerprint", "an immutable definition must declare semanticContractFingerprint", Some("semanticContractFingerprint".into())); }
    if let Some(value) = definition.get("semanticContractFingerprint") {
        if value.as_str().filter(|value| is_scf(value)).is_none() { add_diagnostic(diagnostics, "semantic_contract.invalid_fingerprint", "semanticContractFingerprint must match ^scf:v1:sha256:[0-9a-f]{64}$", Some("semanticContractFingerprint".into())); }
    }
    let Some(raw_manifest) = definition.get("resourceManifest").and_then(Json::as_array) else { add_diagnostic(diagnostics, "semantic_contract.missing_resource_manifest", "resourceManifest must be an array", Some("resourceManifest".into())); return None; };
    if raw_manifest.is_empty() { add_diagnostic(diagnostics, "semantic_contract.empty_resource_manifest", "resourceManifest must not be empty", Some("resourceManifest".into())); }
    let mut entries = Vec::new();
    let mut keys = BTreeSet::new();
    for (index, raw) in raw_manifest.iter().enumerate() {
        let path = format!("resourceManifest[{index}]");
        let Some(item) = raw.as_object() else { add_diagnostic(diagnostics, "semantic_contract.invalid_resource", "resource manifest entry must be an object", Some(path)); continue; };
        for key in item.keys() { if !["canonicalResourceKey", "contentDigest", "role", "dependencies"].contains(&key.as_str()) { add_diagnostic(diagnostics, "semantic_contract.unknown_resource_field", format!("field is not allowed in a resource manifest entry: {key}"), Some(format!("{path}.{key}"))); } }
        let key = item.get("canonicalResourceKey").and_then(Json::as_str).unwrap_or("").to_owned();
        if !canonical_key(&key) { add_diagnostic(diagnostics, "semantic_contract.invalid_resource_key", "resource key is not canonical", Some(format!("{path}.canonicalResourceKey"))); }
        if !keys.insert(key.clone()) { add_diagnostic(diagnostics, "semantic_contract.duplicate_resource_key", "resource key occurs more than once", Some(format!("{path}.canonicalResourceKey"))); }
        let digest = item.get("contentDigest").and_then(Json::as_str).unwrap_or("").to_owned();
        if !is_sha256(&digest) { add_diagnostic(diagnostics, "semantic_contract.invalid_resource_digest", "resource digest must be sha256:<64 lowercase hex characters>", Some(format!("{path}.contentDigest"))); }
        let role = item.get("role").and_then(Json::as_str).unwrap_or("").to_owned();
        if !role_is_valid(&role) { add_diagnostic(diagnostics, "semantic_contract.invalid_resource_role", "resource role is not in the governed vocabulary", Some(format!("{path}.role"))); }
        let Some(raw_dependencies) = item.get("dependencies").and_then(Json::as_array) else { add_diagnostic(diagnostics, "semantic_contract.missing_dependencies", "dependencies must be explicit, including when empty", Some(format!("{path}.dependencies"))); entries.push(ResourceEntry { key, digest, role, dependencies: Vec::new() }); continue; };
        let mut dependencies = Vec::new();
        let mut dependency_keys = BTreeSet::new();
        for (dependency_index, raw_dependency) in raw_dependencies.iter().enumerate() {
            let dependency_path = format!("{path}.dependencies[{dependency_index}]");
            let Some(dependency) = raw_dependency.as_object() else { add_diagnostic(diagnostics, "semantic_contract.invalid_dependency", "dependency must be an object", Some(dependency_path)); continue; };
            for field in dependency.keys() { if !["canonicalResourceKey", "contentDigest"].contains(&field.as_str()) { add_diagnostic(diagnostics, "semantic_contract.unknown_dependency_field", format!("field is not allowed in a dependency: {field}"), Some(format!("{dependency_path}.{field}"))); } }
            let dependency_key = dependency.get("canonicalResourceKey").and_then(Json::as_str).unwrap_or("").to_owned();
            let dependency_digest = dependency.get("contentDigest").and_then(Json::as_str).unwrap_or("").to_owned();
            if !canonical_key(&dependency_key) { add_diagnostic(diagnostics, "semantic_contract.invalid_dependency_key", "dependency resource key is not canonical", Some(format!("{dependency_path}.canonicalResourceKey"))); }
            if !is_sha256(&dependency_digest) { add_diagnostic(diagnostics, "semantic_contract.invalid_dependency_digest", "dependency digest is invalid", Some(format!("{dependency_path}.contentDigest"))); }
            if !dependency_keys.insert(dependency_key.clone()) { add_diagnostic(diagnostics, "semantic_contract.duplicate_dependency", "a resource dependency may appear only once", Some(format!("{dependency_path}.canonicalResourceKey"))); }
            dependencies.push((dependency_key, dependency_digest));
        }
        entries.push(ResourceEntry { key, digest, role, dependencies });
    }
    let by_key = entries.iter().map(|entry| (entry.key.clone(), entry)).collect::<BTreeMap<_, _>>();
    for entry in &entries { for (dependency_key, dependency_digest) in &entry.dependencies { match by_key.get(dependency_key) { None => add_diagnostic(diagnostics, "semantic_contract.dangling_dependency", format!("dependency does not exist: {dependency_key}"), Some(entry.key.clone())), Some(target) if target.digest != *dependency_digest => add_diagnostic(diagnostics, "semantic_contract.conflicting_dependency_digest", format!("dependency digest does not match resource manifest: {dependency_key}"), Some(entry.key.clone())), Some(_) => {} } } }
    let Some(raw_frozen) = definition.get("frozenNormativeConformanceResources").and_then(Json::as_array) else { add_diagnostic(diagnostics, "semantic_contract.missing_frozen_resources", "frozenNormativeConformanceResources must be an array", Some("frozenNormativeConformanceResources".into())); return Some(entries); };
    if raw_frozen.is_empty() { add_diagnostic(diagnostics, "semantic_contract.empty_frozen_resources", "frozenNormativeConformanceResources must not be empty", Some("frozenNormativeConformanceResources".into())); }
    let mut frozen = BTreeSet::new();
    for (index, value) in raw_frozen.iter().enumerate() {
        let Some(key) = value.as_str() else { add_diagnostic(diagnostics, "semantic_contract.invalid_frozen_resource", "frozen resource key must be a string", Some(format!("frozenNormativeConformanceResources[{index}]"))); continue; };
        if !frozen.insert(key.to_owned()) { add_diagnostic(diagnostics, "semantic_contract.duplicate_frozen_resource", "frozen resource key occurs more than once", Some(key.to_owned())); }
        match by_key.get(key) { None => add_diagnostic(diagnostics, "semantic_contract.dangling_frozen_resource", "frozen resource is absent from resourceManifest", Some(key.to_owned())), Some(entry) if !role_is_conformance(&entry.role) => add_diagnostic(diagnostics, "semantic_contract.invalid_frozen_resource_role", "frozen resource role must be a declared conformance role", Some(key.to_owned())), Some(_) => {} }
    }
    let mut visiting = BTreeSet::new();
    let mut visited = BTreeSet::new();
    for entry in &entries { detect_cycle(&entry.key, &by_key, &mut visiting, &mut visited, diagnostics); }
    Some(entries)
}

fn detect_cycle(key: &str, by_key: &BTreeMap<String, &ResourceEntry>, visiting: &mut BTreeSet<String>, visited: &mut BTreeSet<String>, diagnostics: &mut Vec<Json>) {
    if visited.contains(key) { return; }
    if !visiting.insert(key.to_owned()) { add_diagnostic(diagnostics, "semantic_contract.dependency_cycle", "resource dependency cycle detected", Some(key.to_owned())); return; }
    if let Some(entry) = by_key.get(key) { for (dependency, _) in &entry.dependencies { if by_key.contains_key(dependency) { detect_cycle(dependency, by_key, visiting, visited, diagnostics); } } }
    visiting.remove(key);
    visited.insert(key.to_owned());
}

fn normalized_definition(definition: &BTreeMap<String, Json>) -> BTreeMap<String, Json> {
    // Resource manifests and dependency lists are identity-keyed. Their authored
    // order cannot create a fictitious semantic successor.
    let mut normalized = definition.clone();
    normalized.remove("semanticContractFingerprint");
    if let Some(Json::Array(manifest)) = normalized.get_mut("resourceManifest") {
        for entry in manifest.iter_mut() { if let Json::Object(values) = entry { if let Some(Json::Array(dependencies)) = values.get_mut("dependencies") { dependencies.sort_by(|left, right| { let left_key = left.as_object().and_then(|value| value.get("canonicalResourceKey")).and_then(Json::as_str).unwrap_or(""); let right_key = right.as_object().and_then(|value| value.get("canonicalResourceKey")).and_then(Json::as_str).unwrap_or(""); left_key.cmp(right_key) }); } } }
        manifest.sort_by(|left, right| { let left_key = left.as_object().and_then(|value| value.get("canonicalResourceKey")).and_then(Json::as_str).unwrap_or(""); let right_key = right.as_object().and_then(|value| value.get("canonicalResourceKey")).and_then(Json::as_str).unwrap_or(""); left_key.cmp(right_key) });
    }
    if let Some(Json::Array(frozen)) = normalized.get_mut("frozenNormativeConformanceResources") { frozen.sort_by(|left, right| left.as_str().unwrap_or("").cmp(right.as_str().unwrap_or(""))); }
    normalized
}

fn definition_preimage(definition: &BTreeMap<String, Json>) -> Result<String, String> {
    let preimage = object([("scheme".into(), string(SCF_DOMAIN)), ("definition".into(), Json::Object(normalized_definition(definition))) ]);
    let mut canonical = String::new();
    canonicalize_value(&preimage, &mut canonical)?;
    Ok(canonical)
}

fn scf(canonical: &str) -> String { format!("{SCF_SCHEME}:{}", digest(canonical.as_bytes()).trim_start_matches("sha256:")) }

fn validate_declared_fingerprint(definition: &BTreeMap<String, Json>, require_declared: bool, diagnostics: &mut Vec<Json>) -> Option<String> {
    let _ = parse_definition(definition, require_declared, diagnostics)?;
    let canonical = match definition_preimage(definition) { Ok(value) => value, Err(error) => { add_diagnostic(diagnostics, "semantic_contract.canonicalization_failed", error, None); return None; } };
    let expected = scf(&canonical);
    if require_declared {
        if let Some(declared) = definition.get("semanticContractFingerprint").and_then(Json::as_str) { if declared != expected { add_diagnostic(diagnostics, "semantic_contract.fingerprint_mismatch", "declared semantic contract fingerprint does not match the immutable definition", Some("semanticContractFingerprint".into())); } }
        else { add_diagnostic(diagnostics, "semantic_contract.missing_fingerprint", "verification requires a declared semanticContractFingerprint", Some("semanticContractFingerprint".into())); }
    }
    Some(canonical)
}

// A fragment-only reference points inside the resource that contains it and
// is therefore not a manifest edge.  A relative resource reference, in
// contrast, changes the meaning of the containing resource and must resolve
// to one exact canonical key.  `$schema` and `$id` are intentionally not
// interpreted here: they are metadata, not dependency edges.  Remote `$ref`
// values are rejected because a live network lookup cannot be part of an
// immutable semantic definition.
fn relative_resource_key(resource_key: &str, reference: &str) -> Result<Option<String>, (String, String)> {
    let (location, _) = reference.split_once('#').unwrap_or((reference, ""));
    if location.is_empty() { return Ok(None); }
    if reference.starts_with("//") || reference.contains("://") || reference.starts_with("urn:") {
        return Err(("semantic_contract.live_external_reference".into(), "remote resource references are not permitted in a semantic closure".into()));
    }
    if location.starts_with('/') {
        return Err(("semantic_contract.absolute_resource_reference".into(), "absolute resource references cannot be resolved from a semantic resource".into()));
    }
    let mut parts: Vec<String> = resource_key.split('/').map(str::to_owned).collect();
    parts.pop();
    for part in location.split('/') {
        if part.is_empty() || part == "." { continue; }
        if part == ".." {
            if parts.pop().is_none() {
                return Err(("semantic_contract.resource_reference_escape".into(), "relative resource reference escapes the canonical resource namespace".into()));
            }
        } else {
            parts.push(part.to_owned());
        }
    }
    let Some(last) = parts.last_mut() else {
        return Err(("semantic_contract.invalid_resource_reference".into(), "relative resource reference resolved to an empty key".into()));
    };
    if let Some(stripped) = last.strip_suffix(".json") { *last = stripped.to_owned(); }
    let key = parts.join("/");
    if !canonical_key(&key) {
        return Err(("semantic_contract.invalid_resource_reference".into(), "relative resource reference did not resolve to a canonical key".into()));
    }
    Ok(Some(key))
}

fn collect_resource_references(
    resource_key: &str,
    value: &Json,
    path: &str,
    references: &mut BTreeSet<String>,
    diagnostics: &mut Vec<Json>,
) {
    match value {
        Json::Object(values) => {
            if let Some(reference) = values.get("$ref") {
                let Some(reference) = reference.as_str() else {
                    add_diagnostic(diagnostics, "semantic_contract.invalid_resource_reference", "$ref must be a string", Some(path.to_owned()));
                    return;
                };
                match relative_resource_key(resource_key, reference) {
                    Ok(Some(key)) => { references.insert(key); }
                    Ok(None) => {}
                    Err((code, message)) => add_diagnostic(diagnostics, &code, message, Some(path.to_owned())),
                }
            }
            for (key, child) in values {
                if key != "$ref" { collect_resource_references(resource_key, child, &format!("{path}/{key}"), references, diagnostics); }
            }
        }
        Json::Array(values) => {
            for (index, child) in values.iter().enumerate() { collect_resource_references(resource_key, child, &format!("{path}[{index}]"), references, diagnostics); }
        }
        Json::Null | Json::Bool(_) | Json::Number(_) | Json::String(_) => {}
    }
}

fn collect_explicit_semantic_dependencies(resource_key: &str, value: &Json, diagnostics: &mut Vec<Json>) -> BTreeSet<String> {
    let Some(raw) = value.as_object().and_then(|object| object.get("semanticDependencies")) else { return BTreeSet::new(); };
    let Some(values) = raw.as_array() else {
        add_diagnostic(diagnostics, "semantic_contract.invalid_semantic_dependencies", "semanticDependencies must be an array of canonical resource keys", Some(resource_key.to_owned()));
        return BTreeSet::new();
    };
    let mut dependencies = BTreeSet::new();
    for (index, dependency) in values.iter().enumerate() {
        let path = format!("{resource_key}/semanticDependencies[{index}]");
        let Some(key) = dependency.as_str() else {
            add_diagnostic(diagnostics, "semantic_contract.invalid_semantic_dependency", "semantic dependency must be a string", Some(path));
            continue;
        };
        if !canonical_key(key) { add_diagnostic(diagnostics, "semantic_contract.invalid_semantic_dependency", "semantic dependency key is not canonical", Some(path)); }
        dependencies.insert(key.to_owned());
    }
    dependencies
}

fn validate_resource_contents(entries: &[ResourceEntry], resources: Option<&Vec<Json>>, diagnostics: &mut Vec<Json>) {
    let Some(resources) = resources else { add_diagnostic(diagnostics, "semantic_contract.missing_resource_contents", "resource closure requires explicit resource contents", Some("resources".into())); return; };
    if resources.is_empty() { add_diagnostic(diagnostics, "semantic_contract.empty_resource_contents", "resource closure contents must not be empty", Some("resources".into())); }
    let mut supplied: BTreeMap<String, Json> = BTreeMap::new();
    for (index, raw) in resources.iter().enumerate() {
        let path = format!("resources[{index}]");
        let Some(resource) = raw.as_object() else { add_diagnostic(diagnostics, "semantic_contract.invalid_resource_content", "resource content entry must be an object", Some(path)); continue; };
        for key in resource.keys() { if !["canonicalResourceKey", "content"].contains(&key.as_str()) { add_diagnostic(diagnostics, "semantic_contract.unknown_resource_content_field", format!("field is not allowed in supplied resource content: {key}"), Some(format!("{path}.{key}"))); } }
        let key = resource.get("canonicalResourceKey").and_then(Json::as_str).unwrap_or("").to_owned();
        if !canonical_key(&key) { add_diagnostic(diagnostics, "semantic_contract.invalid_supplied_resource_key", "supplied resource key is not canonical", Some(format!("{path}.canonicalResourceKey"))); }
        let content = resource.get("content").cloned().unwrap_or(Json::Null);
        if let Some(previous) = supplied.insert(key.clone(), content.clone()) {
            let mut previous_json = String::new(); let mut current_json = String::new();
            let same = canonicalize_value(&previous, &mut previous_json).is_ok() && canonicalize_value(&content, &mut current_json).is_ok() && previous_json == current_json;
            add_diagnostic(diagnostics, if same { "semantic_contract.duplicate_supplied_resource" } else { "semantic_contract.conflicting_resource_definition" }, "resource content key occurs more than once", Some(key));
        }
    }
    for entry in entries {
        match supplied.get(&entry.key) {
            None => add_diagnostic(diagnostics, "semantic_contract.missing_resource_content", format!("missing content for resource: {}", entry.key), Some(entry.key.clone())),
            Some(content) => {
                let mut canonical = String::new();
                if let Err(error) = canonicalize_value(content, &mut canonical) {
                    add_diagnostic(diagnostics, "semantic_contract.invalid_resource_content", error, Some(entry.key.clone()));
                } else if digest(canonical.as_bytes()) != entry.digest {
                    add_diagnostic(diagnostics, "semantic_contract.resource_digest_mismatch", format!("content digest does not match manifest for {}", entry.key), Some(entry.key.clone()));
                }

                let mut discovered = BTreeSet::new();
                collect_resource_references(&entry.key, content, &entry.key, &mut discovered, diagnostics);
                discovered.extend(collect_explicit_semantic_dependencies(&entry.key, content, diagnostics));
                let declared = entry.dependencies.iter().map(|(key, _)| key.clone()).collect::<BTreeSet<_>>();
                for key in discovered.difference(&declared) {
                    add_diagnostic(diagnostics, "semantic_contract.undeclared_dependency", format!("resource reference is not declared in the manifest: {key}"), Some(entry.key.clone()));
                }
                for key in declared.difference(&discovered) {
                    add_diagnostic(diagnostics, "semantic_contract.unjustified_dependency", format!("manifest dependency is not justified by the resource: {key}"), Some(entry.key.clone()));
                }
                for key in discovered {
                    if !entries.iter().any(|candidate| candidate.key == key) {
                        add_diagnostic(diagnostics, "semantic_contract.unresolved_resource_dependency", format!("resource dependency is not present in the manifest: {key}"), Some(entry.key.clone()));
                    }
                }
            }
        }
    }
    for key in supplied.keys() { if !entries.iter().any(|entry| entry.key == *key) { add_diagnostic(diagnostics, "semantic_contract.unlisted_resource", format!("resource content is not listed in the manifest: {key}"), Some(key.clone())); } }
}

pub fn canonicalize(request: &Json) -> Json {
    let Some(root) = request.as_object() else { return super::invalid("request must be an object"); };
    if root.contains_key("value") && root.contains_key("value_json") { return canonical_failure("canonicalize_semantic_json", vec![diagnostic("semantic_contract.ambiguous_value", "value and value_json are mutually exclusive", None)]); }
    let parsed_value;
    let value = if let Some(value) = root.get("value") { value } else if let Some(raw) = root.get("value_json").and_then(Json::as_str) { parsed_value = match serde_json::from_str::<Json>(raw) { Ok(value) => value, Err(error) => return canonical_failure("canonicalize_semantic_json", vec![diagnostic("semantic_contract.invalid_json", error.to_string(), Some("value_json".into()))]) }; &parsed_value } else { return super::invalid("value or value_json is required"); };
    let mut canonical = String::new();
    match canonicalize_value(value, &mut canonical) { Ok(()) => canonical_result("canonicalize_semantic_json", canonical.clone(), digest(canonical.as_bytes())), Err(error) => canonical_failure("canonicalize_semantic_json", vec![diagnostic("semantic_contract.unsafe_number", error, Some("value".into()))]) }
}

pub fn fingerprint(request: &Json) -> Json {
    let Some(root) = request.as_object() else { return super::invalid("request must be an object"); };
    let Some(definition) = root.get("definition").and_then(Json::as_object) else { return super::invalid("definition must be an object"); };
    let mode = root.get("mode").and_then(Json::as_str).unwrap_or("");
    if !matches!(mode, "calculate" | "verify") { return super::invalid("mode must be calculate or verify"); }
    let mut diagnostics = Vec::new();
    let Some(canonical) = validate_declared_fingerprint(definition, mode == "verify", &mut diagnostics) else { sort_diagnostics(&mut diagnostics); return canonical_failure("fingerprint_semantic_contract", diagnostics); };
    sort_diagnostics(&mut diagnostics);
    if !diagnostics.is_empty() { return canonical_failure("fingerprint_semantic_contract", diagnostics); }
    let fingerprint = scf(&canonical);
    let mut result = canonical_result("fingerprint_semantic_contract", canonical, fingerprint.clone());
    if let Json::Object(ref mut values) = result { values.insert("mode".into(), string(mode)); values.insert("semantic_contract_fingerprint".into(), string(fingerprint)); }
    result
}

pub fn validate_closure(request: &Json) -> Json {
    let Some(root) = request.as_object() else { return super::invalid("request must be an object"); };
    let Some(definition) = root.get("definition").and_then(Json::as_object) else { return super::invalid("definition must be an object"); };
    let mut diagnostics = Vec::new();
    let entries = parse_definition(definition, true, &mut diagnostics);
    if entries.is_some() {
        match definition_preimage(definition) {
            Ok(canonical) => {
                let expected = scf(&canonical);
                if let Some(declared) = definition.get("semanticContractFingerprint").and_then(Json::as_str) {
                    if declared != expected {
                        add_diagnostic(&mut diagnostics, "semantic_contract.fingerprint_mismatch", "declared semantic contract fingerprint does not match the immutable definition", Some("semanticContractFingerprint".into()));
                    }
                }
            }
            Err(error) => add_diagnostic(&mut diagnostics, "semantic_contract.canonicalization_failed", error, None),
        }
    }
    if let Some(entries) = entries { validate_resource_contents(entries.as_slice(), root.get("resources").and_then(Json::as_array), &mut diagnostics); }
    sort_diagnostics(&mut diagnostics);
    let closure_valid = diagnostics.is_empty();
    let mut result = match simple_result("validate_semantic_resource_closure", closure_valid, diagnostics) { Json::Object(value) => value, _ => unreachable!() };
    result.insert("closure_valid".into(), Json::Bool(closure_valid));
    Json::Object(result)
}

pub fn compose_set(request: &Json) -> Json {
    let Some(root) = request.as_object() else { return super::invalid("request must be an object"); };
    let Some(raw_contracts) = root.get("contracts").and_then(Json::as_array) else { return super::invalid("contracts must be an array"); };
    let mut diagnostics = Vec::new();
    if raw_contracts.is_empty() { add_diagnostic(&mut diagnostics, "semantic_contract.empty_set", "a semantic contract set must contain at least one member", Some("contracts".into())); }
    let mut references = Vec::new(); let mut families = BTreeSet::new();
    for (index, raw) in raw_contracts.iter().enumerate() {
        let path = format!("contracts[{index}]");
        let Some(contract) = raw.as_object() else { add_diagnostic(&mut diagnostics, "semantic_contract.invalid_set_member", "set member must be an object", Some(path)); continue; };
        for key in contract.keys() { if !["semanticContractFamily", "semanticContractVersion", "semanticContractFingerprint"].contains(&key.as_str()) { add_diagnostic(&mut diagnostics, "semantic_contract.unknown_member_field", format!("field is not allowed in a set member: {key}"), Some(format!("{path}.{key}"))); } }
        let family = contract.get("semanticContractFamily").and_then(Json::as_str).unwrap_or("").to_owned();
        let version = contract.get("semanticContractVersion").and_then(Json::as_str).unwrap_or("").to_owned();
        let fingerprint = contract.get("semanticContractFingerprint").and_then(Json::as_str).unwrap_or("").to_owned();
        if !is_family(&family) { add_diagnostic(&mut diagnostics, "semantic_contract.invalid_family", "set member family is invalid", Some(format!("{path}.semanticContractFamily"))); }
        if !is_version(&version) { add_diagnostic(&mut diagnostics, "semantic_contract.invalid_version", "set member version must be an exact major.minor value", Some(format!("{path}.semanticContractVersion"))); }
        if !is_scf(&fingerprint) { add_diagnostic(&mut diagnostics, "semantic_contract.invalid_member_fingerprint", "set member fingerprint must be an exact lowercase scf:v1:sha256 value", Some(format!("{path}.semanticContractFingerprint"))); }
        if !families.insert(family.clone()) { add_diagnostic(&mut diagnostics, "semantic_contract.duplicate_set_family", "a semantic contract set cannot contain duplicate families", Some(format!("{path}.semanticContractFamily"))); }
        references.push((family, version, fingerprint));
    }
    references.sort_by(|left, right| left.0.cmp(&right.0));
    let preimage = object([("scheme".into(), string(SCS_DOMAIN)), ("contracts".into(), Json::Array(references.iter().map(|(family, version, fingerprint)| object([(String::from("semanticContractFamily"), string(family.clone())), (String::from("semanticContractVersion"), string(version.clone())), (String::from("semanticContractFingerprint"), string(fingerprint.clone()))])).collect()))]);
    let mut canonical = String::new();
    if let Err(error) = canonicalize_value(&preimage, &mut canonical) { add_diagnostic(&mut diagnostics, "semantic_contract.canonicalization_failed", error, None); }
    sort_diagnostics(&mut diagnostics);
    if !diagnostics.is_empty() { return canonical_failure("compose_semantic_contract_set", diagnostics); }
    let set_id = format!("{SCS_SCHEME}:{}", digest(canonical.as_bytes()).trim_start_matches("sha256:"));
    let mut result = canonical_result("compose_semantic_contract_set", canonical, set_id.clone());
    if let Json::Object(ref mut values) = result { values.insert("semantic_contract_set_id".into(), string(set_id)); }
    result
}

#[cfg(test)]
mod tests {
    use super::{canonicalize_value, Json};

    #[test]
    fn ecmascript_number_spelling_matches_the_shared_known_answer() {
        let value = serde_json::from_str::<Json>(r#"{"a":333333333.33333329,"b":1e30,"c":4.50,"d":2e-3,"e":1e-27,"f":0.000001,"g":0.0000001,"h":1e20,"i":1e21,"j":-0,"k":5e-324,"l":1.7976931348623157e308,"m":1000000000000000100.0}"#).expect("known-answer JSON is valid");
        let Json::Object(values) = &value else { panic!("known-answer JSON must be an object") };
        // These assertions pin the parse step as well as the spelling step.
        // Without serde_json's `float_roundtrip` feature, both decimals are
        // rounded down before `canonicalize_value` can apply ECMAScript rules.
        let Json::Number(a) = values.get("a").expect("a is present") else { panic!("a must be a number") };
        let Json::Number(m) = values.get("m").expect("m is present") else { panic!("m must be a number") };
        assert_eq!(a.as_f64().expect("finite number").to_bits(), 4734372014072354133);
        assert_eq!(m.as_f64().expect("finite number").to_bits(), 4876203697187506177);
        let mut canonical = String::new();
        canonicalize_value(&value, &mut canonical).expect("known-answer numbers are in the supported domain");
        assert_eq!(canonical, r#"{"a":333333333.3333333,"b":1e+30,"c":4.5,"d":0.002,"e":1e-27,"f":0.000001,"g":1e-7,"h":100000000000000000000,"i":1e+21,"j":0,"k":5e-324,"l":1.7976931348623157e+308,"m":1000000000000000100}"#);
    }
}
