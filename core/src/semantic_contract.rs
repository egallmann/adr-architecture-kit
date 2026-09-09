//! Canonical semantic-contract identity and resource-closure rules.
//!
//! This module is the only meaning-affecting implementation of Slice B. The
//! Python and Node hosts pass ordinary JSON values to this boundary and only
//! construct idiomatic immutable views around the result. In particular, no
//! host is allowed to sort keys, normalize Unicode, or calculate a digest on
//! its own and still claim semantic parity.

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
    dependencies: Vec<(String, String)>,
}

fn is_family(value: &str) -> bool {
    let bytes = value.as_bytes();
    if bytes.is_empty() || !bytes[0].is_ascii_lowercase() {
        return false;
    }
    let mut previous_hyphen = false;
    for byte in bytes {
        if byte.is_ascii_lowercase() || byte.is_ascii_digit() {
            previous_hyphen = false;
        } else if *byte == b'-' && !previous_hyphen {
            previous_hyphen = true;
        } else {
            return false;
        }
    }
    !previous_hyphen
}

fn is_version(value: &str) -> bool {
    let mut parts = value.split('.');
    let Some(major) = parts.next() else { return false; };
    let Some(minor) = parts.next() else { return false; };
    parts.next().is_none()
        && !major.is_empty()
        && !minor.is_empty()
        && major.bytes().all(|byte| byte.is_ascii_digit())
        && minor.bytes().all(|byte| byte.is_ascii_digit())
}

fn is_sha256(value: &str) -> bool {
    let Some(hex) = value.strip_prefix("sha256:") else {
        return false;
    };
    hex.len() == 64 && hex.bytes().all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn canonical_key(value: &str) -> bool {
    !value.is_empty()
        && !value.starts_with('/')
        && !value.contains('\\')
        && !value.split('/').any(|part| part.is_empty() || part == "." || part == "..")
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || b"._/-".contains(&byte))
}

// RFC 8785 orders object keys by their UTF-16 code units, not Rust's Unicode
// scalar-value ordering. The distinction matters for supplementary-plane
// characters and is deliberately covered by the canonicalization vectors.
fn utf16_cmp(left: &str, right: &str) -> Ordering {
    left.encode_utf16().cmp(right.encode_utf16())
}

fn canonical_string(value: &str) -> String {
    // serde_json's string serializer emits JSON escapes without applying any
    // Unicode normalization, which is exactly the JCS string rule.
    serde_json::to_string(value).expect("JSON strings must serialize")
}

fn canonical_number(value: &serde_json::Number) -> Result<String, String> {
    let raw = value.to_string();
    if !raw.contains('.') && !raw.contains('e') && !raw.contains('E') {
        let integer = raw
            .parse::<i128>()
            .map_err(|_| "integer is outside the supported safe range".to_owned())?;
        if integer.abs() > MAX_SAFE_INTEGER {
            return Err("unsafe integer input; values beyond IEEE-754 safe range are rejected".into());
        }
    }
    let number = value
        .as_f64()
        .ok_or_else(|| "JSON number must be finite".to_owned())?;
    if !number.is_finite() {
        return Err("JSON number must be finite".into());
    }

    // ryu produces the shortest round-tripping IEEE-754 representation. JCS
    // uses ECMAScript's decimal/exponent thresholds, so normalize only the
    // presentation around that exact binary value.
    let mut buffer = ryu::Buffer::new();
    let rendered = buffer.format_finite(number);
    let (mantissa, exponent) = match rendered.split_once('e') {
        Some((mantissa, exponent)) => (mantissa, exponent.parse::<i32>().unwrap_or(0)),
        None => (rendered, 0),
    };
    let negative = mantissa.starts_with('-');
    let unsigned = mantissa.strip_prefix('-').unwrap_or(mantissa);
    let mut digits = unsigned.replace('.', "");
    if digits.ends_with('0') && unsigned.contains('.') {
        while digits.ends_with('0') {
            digits.pop();
        }
    }
    let decimal_index = unsigned.find('.').unwrap_or(unsigned.len()) as i32 + exponent;
    if number == 0.0 {
        return Ok("0".into());
    }
    let sign = if negative { "-" } else { "" };
    if (-6..=21).contains(&decimal_index) {
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
        let tail = &digits[1..];
        let exponent = decimal_index - 1;
        let exponent_text = if exponent >= 0 {
            format!("+{exponent}")
        } else {
            exponent.to_string()
        };
        let body = if tail.is_empty() {
            first.to_owned()
        } else {
            format!("{first}.{tail}")
        };
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
                if index != 0 {
                    output.push(',');
                }
                canonicalize_value(value, output)?;
            }
            output.push(']');
        }
        Json::Object(values) => {
            output.push('{');
            let mut entries: Vec<_> = values.iter().collect();
            entries.sort_by(|left, right| utf16_cmp(left.0, right.0));
            for (index, (key, value)) in entries.iter().enumerate() {
                if index != 0 {
                    output.push(',');
                }
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
    let hex = result.iter().map(|byte| format!("{byte:02x}")).collect::<String>();
    format!("sha256:{hex}")
}

fn canonical_result(operation: &str, canonical: String, fingerprint: String) -> Json {
    let bytes = canonical.as_bytes();
    let hex = bytes.iter().map(|byte| format!("{byte:02x}")).collect::<String>();
    let mut result = match simple_result(operation, true, Vec::new()) {
        Json::Object(value) => value,
        _ => unreachable!(),
    };
    result.insert("canonical_preimage_json".into(), string(canonical));
    result.insert("canonical_preimage_hex".into(), string(hex));
    result.insert("fingerprint".into(), string(fingerprint));
    Json::Object(result)
}

fn canonical_failure(operation: &str, diagnostics: Vec<Json>) -> Json {
    let mut result = match simple_result(operation, false, diagnostics) {
        Json::Object(value) => value,
        _ => unreachable!(),
    };
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

fn parse_definition<'a>(
    definition: &'a BTreeMap<String, Json>,
    diagnostics: &mut Vec<Json>,
) -> Option<Vec<ResourceEntry>> {
    let allowed = [
        "semanticContractFamily",
        "semanticContractVersion",
        "fingerprintScheme",
        "resourceManifest",
        "frozenNormativeConformanceResources",
        "semanticContractFingerprint",
    ];
    for key in definition.keys() {
        if !allowed.contains(&key.as_str()) {
            let code = if ["deprecated", "newUsePolicy", "executable", "historicalSupport", "catalogRevision", "currentSelection", "policy"].contains(&key.as_str()) {
                "semantic_contract.mutable_policy_field"
            } else {
                "semantic_contract.unknown_field"
            };
            add_diagnostic(diagnostics, code, format!("field is outside the immutable definition: {key}"), Some(key.clone()));
        }
    }
    let family = definition.get("semanticContractFamily").and_then(Json::as_str);
    if family.is_none() || !is_family(family.unwrap_or("")) {
        add_diagnostic(diagnostics, "semantic_contract.invalid_family", "family must match the approved lower-case grammar", Some("semanticContractFamily".into()));
    }
    if definition.get("semanticContractVersion").and_then(Json::as_str).filter(|value| is_version(value)).is_none() {
        add_diagnostic(diagnostics, "semantic_contract.invalid_version", "version must be an exact major.minor value", Some("semanticContractVersion".into()));
    }
    if definition.get("fingerprintScheme").and_then(Json::as_str) != Some(SCF_SCHEME) {
        add_diagnostic(diagnostics, "semantic_contract.invalid_fingerprint_scheme", format!("fingerprintScheme must be {SCF_SCHEME}"), Some("fingerprintScheme".into()));
    }
    let Some(raw_manifest) = definition.get("resourceManifest").and_then(Json::as_array) else {
        add_diagnostic(diagnostics, "semantic_contract.missing_resource_manifest", "resourceManifest must be an array", Some("resourceManifest".into()));
        return None;
    };
    let mut entries = Vec::new();
    let mut keys = BTreeSet::new();
    for (index, raw) in raw_manifest.iter().enumerate() {
        let path = format!("resourceManifest[{index}]");
        let Some(item) = raw.as_object() else {
            add_diagnostic(diagnostics, "semantic_contract.invalid_resource", "resource manifest entry must be an object", Some(path));
            continue;
        };
        for key in item.keys() {
            if !["canonicalResourceKey", "contentDigest", "role", "dependencies"].contains(&key.as_str()) {
                add_diagnostic(diagnostics, "semantic_contract.unknown_resource_field", format!("field is not allowed in a resource manifest entry: {key}"), Some(format!("{path}.{key}")));
            }
        }
        let key = item.get("canonicalResourceKey").and_then(Json::as_str).unwrap_or("").to_owned();
        if !canonical_key(&key) {
            add_diagnostic(diagnostics, "semantic_contract.invalid_resource_key", "resource key is not canonical", Some(format!("{path}.canonicalResourceKey")));
        }
        if !keys.insert(key.clone()) {
            add_diagnostic(diagnostics, "semantic_contract.duplicate_resource_key", "resource key occurs more than once", Some(format!("{path}.canonicalResourceKey")));
        }
        let digest = item.get("contentDigest").and_then(Json::as_str).unwrap_or("").to_owned();
        if !is_sha256(&digest) {
            add_diagnostic(diagnostics, "semantic_contract.invalid_resource_digest", "resource digest must be sha256:<64 lowercase hex characters>", Some(format!("{path}.contentDigest")));
        }
        if !matches!(item.get("role").and_then(Json::as_str), Some("normative-definition" | "normative-conformance" | "interpretation-rule" | "interpretation-conformance")) {
            add_diagnostic(diagnostics, "semantic_contract.missing_resource_role", "resource role is required", Some(format!("{path}.role")));
        }
        let mut dependencies = Vec::new();
        if let Some(raw_dependencies) = item.get("dependencies").and_then(Json::as_array) {
            for (dependency_index, raw_dependency) in raw_dependencies.iter().enumerate() {
                let dependency_path = format!("{path}.dependencies[{dependency_index}]");
                let Some(dependency) = raw_dependency.as_object() else {
                    add_diagnostic(diagnostics, "semantic_contract.invalid_dependency", "dependency must be an object", Some(dependency_path));
                    continue;
                };
                for key in dependency.keys() {
                    if !["canonicalResourceKey", "contentDigest"].contains(&key.as_str()) {
                        add_diagnostic(diagnostics, "semantic_contract.unknown_dependency_field", format!("field is not allowed in a dependency: {key}"), Some(format!("{dependency_path}.{key}")));
                    }
                }
                let dependency_key = dependency.get("canonicalResourceKey").and_then(Json::as_str).unwrap_or("").to_owned();
                let dependency_digest = dependency.get("contentDigest").and_then(Json::as_str).unwrap_or("").to_owned();
                if !canonical_key(&dependency_key) {
                    add_diagnostic(diagnostics, "semantic_contract.invalid_dependency_key", "dependency resource key is not canonical", Some(format!("{dependency_path}.canonicalResourceKey")));
                }
                if !is_sha256(&dependency_digest) {
                    add_diagnostic(diagnostics, "semantic_contract.invalid_dependency_digest", "dependency digest is invalid", Some(format!("{dependency_path}.contentDigest")));
                }
                dependencies.push((dependency_key, dependency_digest));
            }
        } else {
            add_diagnostic(diagnostics, "semantic_contract.missing_dependencies", "dependencies must be explicit, including when empty", Some(format!("{path}.dependencies")));
        }
        entries.push(ResourceEntry { key, digest, dependencies });
    }

    let by_key = entries.iter().map(|entry| (entry.key.clone(), entry)).collect::<BTreeMap<_, _>>();
    for entry in &entries {
        for (dependency_key, dependency_digest) in &entry.dependencies {
            match by_key.get(dependency_key) {
                None => add_diagnostic(diagnostics, "semantic_contract.dangling_dependency", format!("dependency does not exist: {dependency_key}"), Some(entry.key.clone())),
                Some(target) if target.digest != *dependency_digest => add_diagnostic(diagnostics, "semantic_contract.conflicting_dependency_digest", format!("dependency digest does not match resource manifest: {dependency_key}"), Some(entry.key.clone())),
                Some(_) => {}
            }
        }
    }
    let mut frozen = BTreeSet::new();
    match definition.get("frozenNormativeConformanceResources").and_then(Json::as_array) {
        Some(values) => for (index, value) in values.iter().enumerate() {
            let Some(key) = value.as_str() else {
                add_diagnostic(diagnostics, "semantic_contract.invalid_frozen_resource", "frozen resource key must be a string", Some(format!("frozenNormativeConformanceResources[{index}]")));
                continue;
            };
            if !frozen.insert(key.to_owned()) {
                add_diagnostic(diagnostics, "semantic_contract.duplicate_frozen_resource", "frozen resource key occurs more than once", Some(key.to_owned()));
            }
            match by_key.get(key) {
                None => add_diagnostic(diagnostics, "semantic_contract.dangling_frozen_resource", "frozen resource is absent from resourceManifest", Some(key.to_owned())),
                Some(entry) if !entry.key.ends_with("conformance") => add_diagnostic(diagnostics, "semantic_contract.invalid_frozen_resource_role", "frozen resource must be a conformance resource", Some(key.to_owned())),
                Some(_) => {}
            }
        },
        None => add_diagnostic(diagnostics, "semantic_contract.missing_frozen_resources", "frozenNormativeConformanceResources must be an array", Some("frozenNormativeConformanceResources".into())),
    }
    let mut visiting = BTreeSet::new();
    let mut visited = BTreeSet::new();
    for entry in &entries {
        detect_cycle(&entry.key, &by_key, &mut visiting, &mut visited, diagnostics);
    }
    Some(entries)
}

fn detect_cycle(
    key: &str,
    by_key: &BTreeMap<String, &ResourceEntry>,
    visiting: &mut BTreeSet<String>,
    visited: &mut BTreeSet<String>,
    diagnostics: &mut Vec<Json>,
) {
    if visited.contains(key) {
        return;
    }
    if !visiting.insert(key.to_owned()) {
        add_diagnostic(diagnostics, "semantic_contract.dependency_cycle", "resource dependency cycle detected", Some(key.to_owned()));
        return;
    }
    if let Some(entry) = by_key.get(key) {
        for (dependency, _) in &entry.dependencies {
            if by_key.contains_key(dependency) {
                detect_cycle(dependency, by_key, visiting, visited, diagnostics);
            }
        }
    }
    visiting.remove(key);
    visited.insert(key.to_owned());
}

fn validate_resource_contents(
    entries: &[ResourceEntry],
    resources: Option<&Vec<Json>>,
    diagnostics: &mut Vec<Json>,
) {
    let Some(resources) = resources else {
        add_diagnostic(diagnostics, "semantic_contract.missing_resource_contents", "resource closure requires explicit resource contents", Some("resources".into()));
        return;
    };
    let mut supplied: BTreeMap<String, Json> = BTreeMap::new();
    for (index, raw) in resources.iter().enumerate() {
        let Some(resource) = raw.as_object() else {
            add_diagnostic(diagnostics, "semantic_contract.invalid_resource_content", "resource content entry must be an object", Some(format!("resources[{index}]")));
            continue;
        };
        let key = resource.get("canonicalResourceKey").and_then(Json::as_str).unwrap_or("").to_owned();
        if supplied.insert(key.clone(), resource.get("content").cloned().unwrap_or(Json::Null)).is_some() {
            add_diagnostic(diagnostics, "semantic_contract.duplicate_supplied_resource", "resource content key occurs more than once", Some(key));
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
            }
        }
    }
    for key in supplied.keys() {
        if !entries.iter().any(|entry| entry.key == *key) {
            add_diagnostic(diagnostics, "semantic_contract.unlisted_resource", format!("resource content is not listed in the manifest: {key}"), Some(key.clone()));
        }
    }
}

pub fn canonicalize(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    let parsed_value;
    let value = if let Some(value) = root.get("value") {
        value
    } else if let Some(raw) = root.get("value_json").and_then(Json::as_str) {
        parsed_value = match serde_json::from_str::<Json>(raw) {
            Ok(value) => value,
            Err(error) => return canonical_failure("canonicalize_semantic_json", vec![diagnostic("semantic_contract.invalid_json", error.to_string(), Some("value_json".into()))]),
        };
        &parsed_value
    } else {
        return super::invalid("value or value_json is required");
    };
    let mut canonical = String::new();
    match canonicalize_value(value, &mut canonical) {
        Ok(()) => {
            let mut result = canonical_result("canonicalize_semantic_json", canonical.clone(), digest(canonical.as_bytes()));
            if let Json::Object(ref mut values) = result {
                values.insert("sha256".into(), values.get("fingerprint").cloned().unwrap_or(Json::Null));
            }
            result
        }
        Err(error) => canonical_failure("canonicalize_semantic_json", vec![diagnostic("semantic_contract.unsafe_number", error, Some("value".into()))]),
    }
}

pub fn fingerprint(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    let Some(definition) = root.get("definition").and_then(Json::as_object) else {
        return super::invalid("definition must be an object");
    };
    let mut diagnostics = Vec::new();
    let _entries = parse_definition(definition, &mut diagnostics);
    let mut preimage_definition = definition.clone();
    let declared = preimage_definition.remove("semanticContractFingerprint");
    let preimage = object([
        ("scheme".into(), string(SCF_DOMAIN)),
        ("definition".into(), Json::Object(preimage_definition)),
    ]);
    let mut canonical = String::new();
    if let Err(error) = canonicalize_value(&preimage, &mut canonical) {
        add_diagnostic(&mut diagnostics, "semantic_contract.canonicalization_failed", error, None);
    }
    if let Some(Json::String(value)) = declared {
        let expected = format!("scf:v1:sha256:{}", digest(canonical.as_bytes()).trim_start_matches("sha256:"));
        if value != expected {
            add_diagnostic(&mut diagnostics, "semantic_contract.fingerprint_mismatch", "declared semantic contract fingerprint does not match the immutable definition", Some("semanticContractFingerprint".into()));
        }
    }
    sort_diagnostics(&mut diagnostics);
    if !diagnostics.is_empty() {
        return canonical_failure("fingerprint_semantic_contract", diagnostics);
    }
    let fingerprint = format!("scf:v1:sha256:{}", digest(canonical.as_bytes()).trim_start_matches("sha256:"));
    let mut result = canonical_result("fingerprint_semantic_contract", canonical, fingerprint.clone());
    if let Json::Object(ref mut values) = result {
        values.insert("semantic_contract_fingerprint".into(), string(fingerprint));
    }
    result
}

pub fn validate_closure(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    let Some(definition) = root.get("definition").and_then(Json::as_object) else {
        return super::invalid("definition must be an object");
    };
    let mut diagnostics = Vec::new();
    if let Some(entries) = parse_definition(definition, &mut diagnostics) {
        validate_resource_contents(entries.as_slice(), root.get("resources").and_then(Json::as_array), &mut diagnostics);
    }
    sort_diagnostics(&mut diagnostics);
    let closure_valid = diagnostics.is_empty();
    let mut result = match simple_result("validate_semantic_resource_closure", closure_valid, diagnostics) {
        Json::Object(value) => value,
        _ => unreachable!(),
    };
    result.insert("closure_valid".into(), Json::Bool(closure_valid));
    Json::Object(result)
}

pub fn compose_set(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    let Some(raw_contracts) = root.get("contracts").and_then(Json::as_array) else {
        return super::invalid("contracts must be an array");
    };
    let mut diagnostics = Vec::new();
    let mut references = Vec::new();
    let mut families = BTreeSet::new();
    for (index, raw) in raw_contracts.iter().enumerate() {
        let path = format!("contracts[{index}]");
        let Some(contract) = raw.as_object() else {
            add_diagnostic(&mut diagnostics, "semantic_contract.invalid_set_member", "set member must be an object", Some(path));
            continue;
        };
        let family = contract.get("semanticContractFamily").and_then(Json::as_str).unwrap_or("").to_owned();
        let version = contract.get("semanticContractVersion").and_then(Json::as_str).unwrap_or("").to_owned();
        let fingerprint = contract.get("semanticContractFingerprint").and_then(Json::as_str).unwrap_or("").to_owned();
        if !is_family(&family) {
            add_diagnostic(&mut diagnostics, "semantic_contract.invalid_family", "set member family is invalid", Some(format!("{path}.semanticContractFamily")));
        }
        if !is_version(&version) {
            add_diagnostic(&mut diagnostics, "semantic_contract.invalid_version", "set member version must be an exact major.minor value", Some(format!("{path}.semanticContractVersion")));
        }
        if !fingerprint.starts_with("scf:v1:sha256:") || fingerprint.len() != 78 {
            add_diagnostic(&mut diagnostics, "semantic_contract.invalid_member_fingerprint", "set member fingerprint must be an exact scf:v1:sha256 value", Some(format!("{path}.semanticContractFingerprint")));
        }
        if !families.insert(family.clone()) {
            add_diagnostic(&mut diagnostics, "semantic_contract.duplicate_set_family", "a semantic contract set cannot contain duplicate families", Some(format!("{path}.semanticContractFamily")));
        }
        references.push((family, version, fingerprint));
    }
    references.sort_by(|left, right| left.0.cmp(&right.0));
    let preimage = object([
        ("scheme".into(), string(SCS_DOMAIN)),
        ("contracts".into(), Json::Array(references.iter().map(|(family, version, fingerprint)| object([
            ("semanticContractFamily".into(), string(family.clone())),
            ("semanticContractVersion".into(), string(version.clone())),
            ("semanticContractFingerprint".into(), string(fingerprint.clone())),
        ])).collect())),
    ]);
    let mut canonical = String::new();
    if let Err(error) = canonicalize_value(&preimage, &mut canonical) {
        add_diagnostic(&mut diagnostics, "semantic_contract.canonicalization_failed", error, None);
    }
    sort_diagnostics(&mut diagnostics);
    if !diagnostics.is_empty() {
        return canonical_failure("compose_semantic_contract_set", diagnostics);
    }
    let fingerprint = format!("scs:v1:sha256:{}", digest(canonical.as_bytes()).trim_start_matches("sha256:"));
    let mut result = canonical_result("compose_semantic_contract_set", canonical, fingerprint);
    if let Json::Object(ref mut values) = result {
        let set_fingerprint = values.remove("fingerprint").unwrap_or(Json::Null);
        values.insert("semantic_contract_set_fingerprint".into(), set_fingerprint);
    }
    result
}
