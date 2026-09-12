use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

mod architecture;
mod attribution;
mod linkage;
mod materialization;
mod semantic_contract;
mod semantic_contract_set;

// This module is the canonical semantic execution boundary. Host SDKs are
// responsible for discovery, filesystem access, YAML parsing, and adapting
// their native inputs into this normalized JSON contract; they must not
// reimplement the rules evaluated below.
const VERSION: &str = "1.0";
const VERSION_1_1: &str = "1.1";
const SENTINELS: [&str; 3] = [
    "__LEGACY_UNSPECIFIED__",
    "__NOT_YET_MODELED__",
    "__MIGRATION_PLACEHOLDER__",
];
const GENERATED_ARTIFACT_KINDS: [&str; 5] = [
    "manifest",
    "architecture_graph",
    "legacy_entity_registry",
    "rendered_adr_markdown",
    "system_overview",
];

// The transport representation is an internal wire model, not a Rust type
// exposed as part of a public SDK surface. serde_json supplies the mature JSON
// parser/serializer; the resulting self-contained WASM artifact can still run
// from Python, Node, and browser/WASM hosts. Rust build dependencies are
// compiled into that artifact, while Python additionally depends on wasmtime
// to load it.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(untagged)]
enum Json {
    Null,
    Bool(bool),
    Number(serde_json::Number),
    String(String),
    Array(Vec<Json>),
    Object(BTreeMap<String, Json>),
}

// serde_json normally materializes objects into a map and lets a later member
// replace an earlier member. That is convenient for application data but is
// unsafe at a canonicalization boundary: two byte-distinct inputs would then
// acquire one indistinguishable meaning. The semantic boundary therefore
// parses objects with an explicit duplicate-member check before any map is
// constructed.
impl<'de> Deserialize<'de> for Json {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        use serde::de::{Error, MapAccess, SeqAccess, Visitor};
        use std::fmt;

        struct JsonVisitor;
        impl<'de> Visitor<'de> for JsonVisitor {
            type Value = Json;

            fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                formatter.write_str("a JSON value")
            }
            fn visit_unit<E>(self) -> Result<Self::Value, E>
            where
                E: Error,
            {
                Ok(Json::Null)
            }
            fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E>
            where
                E: Error,
            {
                Ok(Json::Bool(value))
            }
            fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
            where
                E: Error,
            {
                Ok(Json::Number(serde_json::Number::from(value)))
            }
            fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
            where
                E: Error,
            {
                Ok(Json::Number(serde_json::Number::from(value)))
            }
            fn visit_f64<E>(self, value: f64) -> Result<Self::Value, E>
            where
                E: Error,
            {
                serde_json::Number::from_f64(value)
                    .map(Json::Number)
                    .ok_or_else(|| E::custom("JSON number must be finite"))
            }
            fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
            where
                E: Error,
            {
                Ok(Json::String(value.to_owned()))
            }
            fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
            where
                E: Error,
            {
                Ok(Json::String(value))
            }
            fn visit_none<E>(self) -> Result<Self::Value, E>
            where
                E: Error,
            {
                Ok(Json::Null)
            }
            fn visit_seq<A>(self, mut access: A) -> Result<Self::Value, A::Error>
            where
                A: SeqAccess<'de>,
            {
                let mut values = Vec::new();
                while let Some(value) = access.next_element::<Json>()? {
                    values.push(value);
                }
                Ok(Json::Array(values))
            }
            fn visit_map<A>(self, mut access: A) -> Result<Self::Value, A::Error>
            where
                A: MapAccess<'de>,
            {
                let mut values = BTreeMap::new();
                while let Some(key) = access.next_key::<String>()? {
                    if values.contains_key(&key) {
                        return Err(A::Error::custom(format!("duplicate JSON member: {key}")));
                    }
                    let value = access.next_value::<Json>()?;
                    values.insert(key, value);
                }
                Ok(Json::Object(values))
            }
        }

        deserializer.deserialize_any(JsonVisitor)
    }
}

impl Json {
    fn object() -> BTreeMap<String, Json> {
        BTreeMap::new()
    }
    fn as_object(&self) -> Option<&BTreeMap<String, Json>> {
        if let Self::Object(value) = self {
            Some(value)
        } else {
            None
        }
    }
    fn as_array(&self) -> Option<&Vec<Json>> {
        if let Self::Array(value) = self {
            Some(value)
        } else {
            None
        }
    }
    fn as_str(&self) -> Option<&str> {
        if let Self::String(value) = self {
            Some(value)
        } else {
            None
        }
    }
    fn as_u64(&self) -> Option<u64> {
        if let Self::Number(value) = self {
            value.as_u64()
        } else {
            None
        }
    }
}
fn json(value: &Json) -> String {
    serde_json::to_string(value).expect("semantic core result must serialize as JSON")
}
fn number(value: impl Into<u64>) -> Json {
    Json::Number(serde_json::Number::from(value.into()))
}
fn string(value: impl Into<String>) -> Json {
    Json::String(value.into())
}
fn object(values: impl IntoIterator<Item = (String, Json)>) -> Json {
    Json::Object(values.into_iter().collect())
}
fn issue(path: impl Into<String>, message: impl Into<String>) -> Json {
    object([
        (String::from("path"), string(path)),
        (String::from("message"), string(message)),
    ])
}
fn diagnostic(code: impl Into<String>, message: impl Into<String>, path: Option<String>) -> Json {
    diagnostic_with_severity("error", code, message, path)
}

fn diagnostic_with_severity(
    severity: &str,
    code: impl Into<String>,
    message: impl Into<String>,
    path: Option<String>,
) -> Json {
    let mut values = Json::object();
    values.insert("severity".into(), string(severity));
    values.insert("code".into(), string(code));
    values.insert("message".into(), string(message));
    if let Some(path) = path {
        values.insert("path".into(), string(path));
    }
    Json::Object(values)
}

fn invalid(message: impl Into<String>) -> Json {
    result(
        false,
        String::new(),
        "invalid_request",
        0,
        0,
        BTreeMap::new(),
        Vec::new(),
        vec![diagnostic("core.invalid_request", message, None)],
    )
}

fn simple_result(operation: &str, success: bool, diagnostics: Vec<Json>) -> Json {
    object([
        (String::from("core_contract_version"), string(VERSION)),
        (String::from("operation"), string(operation)),
        (String::from("success"), Json::Bool(success)),
        (String::from("diagnostics"), Json::Array(diagnostics)),
    ])
}

/// Build a result for the additive 1.1 protocol without changing the v1.0
/// envelope. Keeping this helper separate is intentional: compatibility
/// callers must continue to observe the exact v1.0 wire version and fields.
pub(crate) fn simple_result_v11(operation: &str, success: bool, diagnostics: Vec<Json>) -> Json {
    object([
        (String::from("core_contract_version"), string(VERSION_1_1)),
        (String::from("operation"), string(operation)),
        (String::from("success"), Json::Bool(success)),
        (String::from("diagnostics"), Json::Array(diagnostics)),
    ])
}

/// Return a deterministic v1.1 protocol rejection. New operations use their
/// operation-specific result envelope when possible; malformed or unsupported
/// requests still retain the declared v1.1 version so host validators can
/// route the failure through the correct contract.
pub(crate) fn invalid_v11(operation: &str, message: impl Into<String>) -> Json {
    simple_result_v11(
        operation,
        false,
        vec![diagnostic("core.invalid_request", message, None)],
    )
}

fn optional_string_value(object: &BTreeMap<String, Json>, key: &str) -> Option<String> {
    object.get(key).and_then(|value| match value {
        Json::String(value) => Some(value.clone()),
        _ => None,
    })
}

fn classify_generated_artifact(request: &Json) -> Json {
    // Hosts inspect files, parse integrity headers, and compute hashes. The
    // shared core owns the meaning of those normalized facts: valid, stale,
    // tampered, malformed, or unsupported generated output.
    let Some(root) = request.as_object() else {
        return invalid("request must be an object");
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some(VERSION) {
        return invalid("unsupported core_contract_version; expected 1.0");
    }
    if root.get("operation").and_then(Json::as_str) != Some("classify_generated_artifact") {
        return invalid("unsupported semantic core operation");
    }
    let Some(artifact_kind) = root.get("artifact_kind").and_then(Json::as_str) else {
        return invalid("artifact_kind is required");
    };
    let header_valid = matches!(root.get("header_valid"), Some(Json::Bool(true)));
    let declared_kind = optional_string_value(root, "declared_artifact_kind");
    let mut values = BTreeMap::new();
    values.insert("core_contract_version".into(), string(VERSION));
    values.insert("operation".into(), string("classify_generated_artifact"));
    values.insert("artifact_kind".into(), string(artifact_kind));

    let mut set_result = |success: bool, status: &str, reason: &str| {
        values.insert("success".into(), Json::Bool(success));
        values.insert("status".into(), string(status));
        values.insert("reason_code".into(), string(reason));
        values.insert(
            "expected_source_hash".into(),
            optional_string_value(root, "expected_source_hash").map_or(Json::Null, Json::String),
        );
        values.insert(
            "actual_source_hash".into(),
            optional_string_value(root, "declared_source_hash").map_or(Json::Null, Json::String),
        );
        values.insert(
            "expected_rendered_hash".into(),
            optional_string_value(root, "expected_rendered_hash").map_or(Json::Null, Json::String),
        );
        values.insert(
            "actual_rendered_hash".into(),
            optional_string_value(root, "actual_rendered_hash").map_or(Json::Null, Json::String),
        );
    };

    // The order is contractual: malformed transport data is reported before
    // kind or hash comparisons, and rendered-output tampering is distinguished
    // from source staleness when both facts are available.
    if !header_valid {
        set_result(
            false,
            "missing_or_malformed_integrity_header",
            "malformed_header",
        );
    } else if !GENERATED_ARTIFACT_KINDS.contains(&declared_kind.as_deref().unwrap_or("")) {
        set_result(
            false,
            "unsupported_artifact_kind",
            "unsupported_artifact_kind",
        );
    } else if optional_string_value(root, "actual_rendered_hash")
        != optional_string_value(root, "declared_rendered_hash")
    {
        set_result(false, "tampered_generated_output", "rendered_hash_mismatch");
    } else if optional_string_value(root, "expected_source_hash")
        != optional_string_value(root, "declared_source_hash")
    {
        set_result(false, "stale_generated_output", "source_hash_mismatch");
    } else {
        set_result(true, "valid", "hashes_match");
    }
    values.insert("diagnostics".into(), Json::Array(Vec::new()));
    Json::Object(values)
}

fn metadata_issue(path: impl Into<String>, message: impl Into<String>) -> Json {
    diagnostic("project_metadata.issue", message, Some(path.into()))
}

fn has_object<'a>(
    value: Option<&'a Json>,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> Option<&'a BTreeMap<String, Json>> {
    match value {
        Some(Json::Object(object)) => Some(object),
        Some(_) => {
            diagnostics.push(metadata_issue(path, "value must be an object"));
            None
        }
        None => {
            diagnostics.push(metadata_issue(path, "required object is missing"));
            None
        }
    }
}

fn required_string(
    object: &BTreeMap<String, Json>,
    key: &str,
    path: &str,
    diagnostics: &mut Vec<Json>,
) -> Option<String> {
    match object.get(key) {
        Some(Json::String(value)) => Some(value.clone()),
        Some(_) => {
            diagnostics.push(metadata_issue(path, "value must be a string"));
            None
        }
        None => {
            diagnostics.push(metadata_issue(path, "required value is missing"));
            None
        }
    }
}

fn optional_string(
    object: &BTreeMap<String, Json>,
    key: &str,
    path: &str,
    diagnostics: &mut Vec<Json>,
) {
    if let Some(value) = object.get(key) {
        if !matches!(value, Json::String(_)) {
            diagnostics.push(metadata_issue(path, "value must be a string"));
        }
    }
}

fn one_of(value: &str, allowed: &[&str]) -> bool {
    allowed.iter().any(|item| *item == value)
}

fn project_name(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
}

fn validate_project_metadata(request: &Json) -> Json {
    // Project metadata is validated after the host has loaded the document.
    // Keeping this rule set here makes Python and Node consumers observe the
    // same contract without making the core aware of paths or filesystems.
    let Some(root) = request.as_object() else {
        return invalid("request must be an object");
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some(VERSION) {
        return invalid("unsupported core_contract_version; expected 1.0");
    }
    if root.get("operation").and_then(Json::as_str) != Some("validate_project_metadata") {
        return invalid("unsupported semantic core operation");
    }
    let Some(metadata) = has_object(
        root.get("project_metadata"),
        "project_metadata",
        &mut Vec::new(),
    ) else {
        return simple_result(
            "validate_project_metadata",
            false,
            vec![metadata_issue(
                "project_metadata",
                "required object is missing",
            )],
        );
    };
    let mut diagnostics = Vec::new();
    match required_string(
        metadata,
        "schema_version",
        "schema_version",
        &mut diagnostics,
    ) {
        Some(value) if value != "1.0" => {
            diagnostics.push(metadata_issue("schema_version", "must equal 1.0"))
        }
        _ => {}
    }
    match required_string(metadata, "type", "type", &mut diagnostics) {
        Some(value) if value != "project_metadata" => {
            diagnostics.push(metadata_issue("type", "must equal project_metadata"))
        }
        _ => {}
    }
    if let Some(project) = has_object(metadata.get("project"), "project", &mut diagnostics) {
        if let Some(value) = required_string(project, "name", "project.name", &mut diagnostics) {
            if !project_name(&value) {
                diagnostics.push(metadata_issue(
                    "project.name",
                    "must contain only lowercase letters, digits, and hyphens",
                ));
            }
        }
        required_string(
            project,
            "description",
            "project.description",
            &mut diagnostics,
        );
        if let Some(value) = required_string(project, "type", "project.type", &mut diagnostics) {
            // Project type is a shared semantic value; hosts must not invent
            // a local enum that diverges from the canonical contract.
            if !one_of(
                &value,
                &[
                    "service",
                    "library",
                    "platform",
                    "system",
                    "tool",
                    "specification",
                ],
            ) {
                diagnostics.push(metadata_issue("project.type", "unsupported project type"));
            }
        }
    }
    if let Some(ownership) = has_object(metadata.get("ownership"), "ownership", &mut diagnostics) {
        required_string(ownership, "team", "ownership.team", &mut diagnostics);
        if let Some(on_call) = ownership.get("on_call") {
            if let Some(on_call) = has_object(Some(on_call), "ownership.on_call", &mut diagnostics)
            {
                required_string(
                    on_call,
                    "schedule",
                    "ownership.on_call.schedule",
                    &mut diagnostics,
                );
                if let Some(value) = required_string(
                    on_call,
                    "rotation",
                    "ownership.on_call.rotation",
                    &mut diagnostics,
                ) {
                    if !one_of(&value, &["daily", "weekly", "biweekly", "monthly"]) {
                        diagnostics.push(metadata_issue(
                            "ownership.on_call.rotation",
                            "unsupported rotation",
                        ));
                    }
                }
                if !matches!(on_call.get("members"), Some(Json::Array(_))) {
                    diagnostics.push(metadata_issue(
                        "ownership.on_call.members",
                        "value must be an array",
                    ));
                }
                optional_string(
                    on_call,
                    "backup",
                    "ownership.on_call.backup",
                    &mut diagnostics,
                );
            }
        }
    }
    if let Some(repository) = has_object(metadata.get("repository"), "repository", &mut diagnostics)
    {
        required_string(repository, "url", "repository.url", &mut diagnostics);
        required_string(
            repository,
            "primary_branch",
            "repository.primary_branch",
            &mut diagnostics,
        );
    }
    if let Some(documentation) = has_object(
        metadata.get("architecture_documentation"),
        "architecture_documentation",
        &mut diagnostics,
    ) {
        optional_string(
            documentation,
            "adr_directory",
            "architecture_documentation.adr_directory",
            &mut diagnostics,
        );
        optional_string(
            documentation,
            "manifest_path",
            "architecture_documentation.manifest_path",
            &mut diagnostics,
        );
        optional_string(
            documentation,
            "architecture_namespace",
            "architecture_documentation.architecture_namespace",
            &mut diagnostics,
        );
    }
    if let Some(automation) = metadata.get("automation") {
        if let Some(automation) = has_object(Some(automation), "automation", &mut diagnostics) {
            for key in [
                "auto_merge_allowed",
                "auto_deploy_staging",
                "auto_deploy_production",
                "requires_human_review",
            ] {
                if let Some(value) = automation.get(key) {
                    if !matches!(value, Json::Bool(_)) {
                        diagnostics.push(metadata_issue(
                            format!("automation.{key}"),
                            "value must be a boolean",
                        ));
                    }
                }
            }
            if let Some(value) = automation.get("comfort_level").and_then(Json::as_str) {
                if !one_of(value, &["conservative", "moderate", "aggressive"]) {
                    diagnostics.push(metadata_issue(
                        "automation.comfort_level",
                        "unsupported comfort level",
                    ));
                }
            }
        }
    }
    simple_result(
        "validate_project_metadata",
        diagnostics.is_empty(),
        diagnostics,
    )
}
fn provider_text(object: &BTreeMap<String, Json>, key: &str) -> String {
    object
        .get(key)
        .and_then(Json::as_str)
        .unwrap_or("")
        .to_owned()
}

fn validate_provider_registry(request: &Json) -> Json {
    // Provider routing is a semantic registry operation. Resolution of the
    // actual provider remains a host concern; uniqueness, normalization, and
    // deterministic ordering belong to the shared contract.
    let Some(root) = request.as_object() else {
        return invalid("request must be an object");
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some(VERSION) {
        return invalid("unsupported core_contract_version; expected 1.0");
    }
    if root.get("operation").and_then(Json::as_str) != Some("open_provider_registry") {
        return invalid("unsupported semantic core operation");
    }
    let Some(bindings) = root.get("bindings").and_then(Json::as_array) else {
        return simple_result(
            "open_provider_registry",
            false,
            vec![diagnostic(
                "provider_registry.invalid",
                "bindings must be an array",
                Some("bindings".into()),
            )],
        );
    };
    let mut diagnostics = Vec::new();
    let mut normalized = Vec::new();
    let mut keys = BTreeSet::new();
    let mut namespaces = BTreeSet::new();
    for (index, value) in bindings.iter().enumerate() {
        let Some(binding) = value.as_object() else {
            diagnostics.push(diagnostic(
                "provider_registry.invalid",
                "binding must be an object",
                Some(format!("bindings[{index}]")),
            ));
            continue;
        };
        let key = provider_text(binding, "workspace_key");
        let namespace = provider_text(binding, "architecture_namespace");
        if key.is_empty() {
            diagnostics.push(diagnostic(
                "provider_registry.invalid",
                "workspace routing keys must be non-empty strings",
                Some(format!("bindings[{index}].workspace_key")),
            ));
        } else if !keys.insert(key.clone()) {
            diagnostics.push(diagnostic(
                "provider_registry.duplicate_workspace_key",
                format!("Duplicate workspace routing key: {key}"),
                Some(format!("bindings[{index}].workspace_key")),
            ));
        }
        if namespace.is_empty() {
            diagnostics.push(diagnostic(
                "provider_registry.invalid",
                "architecture_namespace must be a non-empty string",
                Some(format!("bindings[{index}].architecture_namespace")),
            ));
        } else if !namespaces.insert(namespace.clone()) {
            diagnostics.push(diagnostic(
                "provider_registry.duplicate_namespace",
                format!("Duplicate architecture_namespace across providers: {namespace}"),
                Some(format!("bindings[{index}].architecture_namespace")),
            ));
        }
        let mut output = Json::object();
        output.insert("workspace_key".into(), string(key));
        output.insert("architecture_namespace".into(), string(namespace));
        if let Some(project_root) = binding.get("project_root") {
            output.insert("project_root".into(), project_root.clone());
        }
        normalized.push(output);
    }
    normalized.sort_by_key(|binding| provider_text(binding, "workspace_key"));
    let success = diagnostics.is_empty() && !normalized.is_empty();
    let mut result = simple_result("open_provider_registry", success, diagnostics);
    if let Json::Object(ref mut result) = result {
        result.insert(
            "bindings".into(),
            Json::Array(normalized.into_iter().map(Json::Object).collect()),
        );
    }
    result
}

fn validate_repository(request: &Json) -> Json {
    // Repository identity is evaluated from normalized host facts. This
    // boundary deliberately does not open a repository or depend on a VCS
    // implementation.
    let Some(root) = request.as_object() else {
        return invalid("request must be an object");
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some(VERSION) {
        return invalid("unsupported core_contract_version; expected 1.0");
    }
    if root.get("operation").and_then(Json::as_str) != Some("open_repository") {
        return invalid("unsupported semantic core operation");
    }
    let model_version = root
        .get("model_version")
        .and_then(Json::as_str)
        .unwrap_or("");
    if !["2.0", "2.1", "2.2", "2.3"].contains(&model_version) {
        return simple_result(
            "open_repository",
            false,
            vec![diagnostic(
                "repository.unsupported_model_version",
                format!("unsupported normalized model version: {model_version}"),
                Some("model_version".into()),
            )],
        );
    }
    let namespace = root
        .get("architecture_namespace")
        .and_then(Json::as_str)
        .unwrap_or("");
    let Some(entities) = root.get("entities").and_then(Json::as_array) else {
        return simple_result(
            "open_repository",
            false,
            vec![diagnostic(
                "repository.invalid_entities",
                "entities must be an array",
                Some("entities".into()),
            )],
        );
    };
    let mut diagnostics = Vec::new();
    if namespace.is_empty() {
        diagnostics.push(diagnostic(
            "repository.invalid_namespace",
            "architecture_namespace must be a non-empty string",
            Some("architecture_namespace".into()),
        ));
    }
    let mut ids = BTreeSet::new();
    let mut aliases = BTreeSet::new();
    let mut alias_refs = BTreeSet::new();
    let mut uris = BTreeSet::new();
    for (index, value) in entities.iter().enumerate() {
        let Some(entity) = value.as_object() else {
            diagnostics.push(diagnostic(
                "repository.invalid_entity",
                "entity must be an object",
                Some(format!("entities[{index}]")),
            ));
            continue;
        };
        let fields = [
            ("id", &mut ids, "repository.duplicate_entity_id"),
            ("alias_id", &mut aliases, "repository.duplicate_alias_id"),
            (
                "alias_ref",
                &mut alias_refs,
                "repository.duplicate_alias_ref",
            ),
            ("uri", &mut uris, "repository.duplicate_uri"),
        ];
        for (field, seen, duplicate_code) in fields {
            let path = format!("entities[{index}].{field}");
            let Some(value) = entity.get(field).and_then(Json::as_str) else {
                diagnostics.push(diagnostic(
                    "repository.invalid_entity_field",
                    "identity field must be a string",
                    Some(path),
                ));
                continue;
            };
            if value.is_empty() {
                diagnostics.push(diagnostic(
                    "repository.invalid_entity_field",
                    "identity field must be non-empty",
                    Some(path),
                ));
            } else if !seen.insert(value.to_owned()) {
                diagnostics.push(diagnostic(
                    duplicate_code,
                    format!("duplicate entity identity value: {value}"),
                    Some(path),
                ));
            }
        }
        for field in ["alias_name", "entity_type", "name", "lifecycle_stage"] {
            if !matches!(entity.get(field), Some(Json::String(value)) if !value.is_empty()) {
                diagnostics.push(diagnostic(
                    "repository.invalid_entity_field",
                    "required normalized entity field must be a non-empty string",
                    Some(format!("entities[{index}].{field}")),
                ));
            }
        }
    }
    let mut result = simple_result("open_repository", diagnostics.is_empty(), diagnostics);
    if let Json::Object(ref mut values) = result {
        values.insert("model_version".into(), string(model_version));
        values.insert("architecture_namespace".into(), string(namespace));
        values.insert("entity_count".into(), number(entities.len() as u64));
    }
    result
}

fn required_metadata(entity_type: &str) -> &'static [&'static str] {
    match entity_type {
        "adr" => &["status", "domains", "tags"],
        "capability" => &[
            "adr_id",
            "domains",
            "implemented_by_components",
            "enabled_by_decisions",
        ],
        "decision" => &[
            "adr_id",
            "related_invariants",
            "enforces_invariants",
            "enables_capabilities",
            "governs_components",
            "supersedes",
            "refines",
        ],
        "invariant" => &[
            "scope",
            "statement",
            "enforcement_level",
            "declaration_mode",
            "upheld_by_decisions",
        ],
        "system" => &["adr_id", "implements_logical", "technologies"],
        "component" => &[
            "adr_id",
            "technologies",
            "module_path",
            "implements_capabilities",
            "implements_system",
        ],
        _ => &[],
    }
}
fn is_sentinel(value: &Json) -> bool {
    value
        .as_str()
        .map(|value| SENTINELS.contains(&value))
        .unwrap_or(false)
}
fn result(
    success: bool,
    profile: String,
    outcome: &str,
    sentinel: u64,
    incomplete: u64,
    counts: BTreeMap<String, u64>,
    issues: Vec<Json>,
    diagnostics: Vec<Json>,
) -> Json {
    let mut values = Json::object();
    values.insert("core_contract_version".into(), string(VERSION));
    values.insert("operation".into(), string("validate_contract"));
    values.insert("success".into(), Json::Bool(success));
    values.insert("profile".into(), string(profile));
    values.insert("outcome".into(), string(outcome));
    values.insert("sentinel_field_count".into(), number(sentinel as u64));
    values.insert(
        "non_complete_entity_count".into(),
        number(incomplete as u64),
    );
    values.insert(
        "completeness_counts".into(),
        object(
            counts
                .into_iter()
                .map(|(key, value)| (key, number(value as u64))),
        ),
    );
    values.insert("issues".into(), Json::Array(issues));
    values.insert("diagnostics".into(), Json::Array(diagnostics));
    Json::Object(values)
}

fn validate(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return invalid("request must be an object");
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some(VERSION) {
        return invalid("unsupported core_contract_version; expected 1.0");
    }
    if root.get("operation").and_then(Json::as_str) != Some("validate_contract") {
        return invalid("unsupported semantic core operation");
    }
    let Some(profile) = root.get("profile").and_then(Json::as_str) else {
        return invalid("profile is required");
    };
    if !["greenfield", "brownfield", "migration"].contains(&profile) {
        return invalid("unsupported contract profile");
    }
    let Some(entities) = root
        .get("entity_registry")
        .and_then(Json::as_object)
        .and_then(|value| value.get("entities"))
        .and_then(Json::as_array)
    else {
        return invalid("entity_registry.entities must be an array");
    };
    let mut issues = Vec::new();
    let mut diagnostics = Vec::new();
    let mut sentinel_hits: u64 = 0;
    let mut counts: BTreeMap<String, u64> = BTreeMap::new();
    let sentinels_allowed = profile != "greenfield";
    let mut field_values: BTreeMap<String, Json> = BTreeMap::new();
    for (index, raw) in entities.iter().enumerate() {
        let Some(entity) = raw.as_object() else {
            issues.push(issue(
                format!("entities[{index}]"),
                "entity must be an object",
            ));
            continue;
        };
        let entity_type = entity
            .get("entity_type")
            .and_then(Json::as_str)
            .unwrap_or("");
        let entity_id = entity.get("id").and_then(Json::as_str).unwrap_or("");
        let metadata = entity.get("metadata").and_then(Json::as_object);
        let mut required = required_metadata(entity_type).to_vec();
        required.sort_unstable();
        for key in required.iter().filter(|key| {
            metadata
                .map(|value| !value.contains_key(**key))
                .unwrap_or(true)
        }) {
            issues.push(issue(
                format!("entities[{index}].metadata.{key}"),
                format!("missing required metadata key for entity_type={entity_type}"),
            ));
        }
        let status = entity
            .get("completeness")
            .and_then(Json::as_object)
            .and_then(|value| value.get("status"))
            .and_then(Json::as_str)
            .unwrap_or("");
        *counts.entry(status.into()).or_insert(0) += 1;
        let allowed = match profile {
            "greenfield" => ["complete"].as_slice(),
            "migration" => ["complete", "partial"].as_slice(),
            _ => ["complete", "partial", "reference_only"].as_slice(),
        };
        if !allowed.contains(&status) {
            issues.push(issue(
                format!("entities[{index}].completeness.status"),
                if status == "conflicted" {
                    "conflicted completeness is not allowed in any contract profile".into()
                } else {
                    format!("completeness.status={status} is not allowed for profile={profile}")
                },
            ));
        }
        let mut check = |path: String, value: &Json, enabled: bool| {
            if !is_sentinel(value) {
                return;
            }
            if !sentinels_allowed {
                issues.push(issue(
                    path,
                    format!("sentinel-backed content is not allowed for profile={profile}"),
                ));
            } else if !enabled {
                issues.push(issue(
                    path,
                    "sentinel value is forbidden in this structural field",
                ));
            } else {
                sentinel_hits += 1;
            }
        };
        for key in ["id", "entity_type", "name"] {
            if let Some(value) = entity.get(key) {
                check(format!("entities[{index}].{key}"), value, false);
            }
        }
        if let Some(source) = entity.get("canonical_source").and_then(Json::as_object) {
            for key in ["source_ref", "artifact_path"] {
                if let Some(value) = source.get(key) {
                    check(
                        format!("entities[{index}].canonical_source.{key}"),
                        value,
                        false,
                    );
                }
            }
        }
        if let Some(value) = entity
            .get("completeness")
            .and_then(Json::as_object)
            .and_then(|value| value.get("status"))
        {
            check(
                format!("entities[{index}].completeness.status"),
                value,
                false,
            );
        }
        if let Some(value) = entity.get("summary") {
            check(format!("entities[{index}].summary"), value, true);
            field_values.insert(format!("entity:{entity_id}.summary"), value.clone());
        }
        if let Some(metadata) = metadata {
            for (key, value) in metadata {
                let enabled = (entity_type == "invariant" && key == "statement")
                    || (entity_type == "component" && key == "module_path");
                if enabled {
                    field_values
                        .insert(format!("entity:{entity_id}.metadata.{key}"), value.clone());
                }
                check(format!("entities[{index}].metadata.{key}"), value, enabled);
            }
        }
    }
    let incomplete: u64 = counts
        .iter()
        .filter(|(key, _)| key.as_str() != "complete")
        .map(|(_, value)| *value)
        .sum();
    if let Some(entries) = root
        .get("remediation_ledger")
        .and_then(Json::as_object)
        .and_then(|value| value.get("entries"))
        .and_then(Json::as_array)
    {
        let mut seen = BTreeSet::new();
        for (index, raw) in entries.iter().enumerate() {
            let Some(entry) = raw.as_object() else {
                continue;
            };
            let field = entry.get("field_ref").and_then(Json::as_str).unwrap_or("");
            let prefix = format!("remediation_ledger.entries[{index}]");
            if !seen.insert(field) {
                issues.push(issue(
                    format!("{prefix}.field_ref"),
                    "duplicate remediation ledger entry for field_ref",
                ));
                continue;
            }
            let Some(value) = field_values.get(field) else {
                issues.push(issue(
                    format!("{prefix}.field_ref"),
                    "field_ref does not resolve to a sentinel-capable contract field",
                ));
                continue;
            };
            let state = entry.get("state").and_then(Json::as_str).unwrap_or("");
            let message = match (state, is_sentinel(value)) {
                ("sentinel", false) => Some(
                    "sentinel ledger entry requires current field value to remain sentinel-backed",
                ),
                ("pending_approval", true) => Some(
                    "pending_approval ledger entry requires current field value to be non-sentinel",
                ),
                ("approved", true) => {
                    Some("approved field cannot regress to sentinel-backed content")
                }
                _ => None,
            };
            if let Some(message) = message {
                issues.push(issue(format!("{prefix}.state"), message));
            }
        }
    }
    for item in &issues {
        let path = item
            .as_object()
            .and_then(|value| value.get("path"))
            .and_then(Json::as_str)
            .map(str::to_owned);
        let message = item
            .as_object()
            .and_then(|value| value.get("message"))
            .and_then(Json::as_str)
            .unwrap_or("")
            .to_owned();
        diagnostics.push(diagnostic("contract.issue", message, path));
    }
    if let Some(max) = root.get("max_sentinel_fields").and_then(Json::as_u64) {
        if sentinel_hits > max {
            diagnostics.push(diagnostic(
                "contract.max_sentinel_fields",
                format!("sentinel_field_count={sentinel_hits} exceeds max_sentinel_fields={max}"),
                None,
            ));
        }
    }
    if let Some(max) = root.get("max_non_complete_entities").and_then(Json::as_u64) {
        if incomplete > max {
            diagnostics.push(diagnostic("contract.max_non_complete_entities", format!("non_complete_entity_count={incomplete} exceeds max_non_complete_entities={max}"), None));
        }
    }
    let outcome = if issues.is_empty() {
        if sentinel_hits > 0 {
            "sentinel_compliant"
        } else {
            "compliant"
        }
    } else {
        "non_compliant"
    };
    let success = issues.is_empty()
        && !diagnostics.iter().any(|item| {
            item.as_object()
                .and_then(|value| value.get("code"))
                .and_then(Json::as_str)
                .map(|code| code.starts_with("contract.max_"))
                .unwrap_or(false)
        });
    result(
        success,
        profile.into(),
        outcome,
        sentinel_hits,
        incomplete,
        counts,
        issues,
        diagnostics,
    )
}

fn string_list(object: &BTreeMap<String, Json>, key: &str) -> Vec<String> {
    let mut values = object
        .get(key)
        .and_then(Json::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(Json::as_str)
                .map(str::to_owned)
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    values.sort();
    values.dedup();
    values
}

fn string_field(object: &BTreeMap<String, Json>, key: &str) -> Option<String> {
    object.get(key).and_then(Json::as_str).map(str::to_owned)
}

fn validate_architecture_references(request: &Json) -> Json {
    // Source discovery and YAML parsing stay in the host adapter. Once ADRs,
    // reviews, overrides, and topology claims are normalized, reference
    // validity and topology membership are shared semantic rules.
    //
    // Records are sorted by ADR id before evaluation so diagnostics are stable
    // across Python, Node, and browser hosts regardless of filesystem order.
    let Some(root) = request.as_object() else {
        return invalid("request must be an object");
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some(VERSION) {
        return invalid("unsupported core_contract_version; expected 1.0");
    }
    if root.get("operation").and_then(Json::as_str) != Some("validate_architecture_references") {
        return invalid("unsupported semantic core operation");
    }
    let Some(raw_records) = root.get("records").and_then(Json::as_array) else {
        return invalid("records must be an array");
    };

    let mut records: Vec<(String, BTreeMap<String, Json>)> = Vec::new();
    let mut diagnostics = Vec::new();
    for (index, raw) in raw_records.iter().enumerate() {
        let Some(record) = raw.as_object() else {
            diagnostics.push(diagnostic(
                "architecture_reference.invalid_record",
                "record must be an object",
                Some(format!("records[{index}]")),
            ));
            continue;
        };
        let Some(id) = string_field(record, "id") else {
            diagnostics.push(diagnostic(
                "architecture_reference.invalid_record",
                "record id must be a string",
                Some(format!("records[{index}].id")),
            ));
            continue;
        };
        if string_field(record, "kind").is_none() {
            diagnostics.push(diagnostic(
                "architecture_reference.invalid_record",
                "record kind must be a string",
                Some(format!("records[{index}].kind")),
            ));
            continue;
        }
        records.push((id, record.clone()));
    }
    records.sort_by(|left, right| left.0.cmp(&right.0));

    let mut all_ids = BTreeSet::new();
    let mut logical_ids = BTreeSet::new();
    let mut system_ids = BTreeSet::new();
    let mut component_ids = BTreeSet::new();
    for (id, record) in &records {
        if !all_ids.insert(id.clone()) {
            diagnostics.push(diagnostic(
                "INV-0005",
                "Duplicate ADR IDs found across all ADR types",
                None,
            ));
        }
        match string_field(record, "kind").as_deref() {
            Some("logical") => {
                logical_ids.insert(id.clone());
            }
            Some("physical") => {}
            Some("physical-system") => {
                system_ids.insert(id.clone());
            }
            Some("physical-component") => {
                component_ids.insert(id.clone());
            }
            _ => {}
        }
    }

    // Resolve system identifiers before component claims. Physical-System ADRs
    // are referenced by ADR id, while v1.5 topology membership is expressed in
    // the authored system id vocabulary.
    let mut system_id_by_adr = BTreeMap::new();
    let mut component_systems: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for (id, record) in &records {
        if string_field(record, "kind").as_deref() == Some("physical-system") {
            if let Some(system_id) = string_field(record, "system_id") {
                system_id_by_adr.insert(id.clone(), system_id);
            }
        }
    }
    for (_id, record) in &records {
        if string_field(record, "kind").as_deref() == Some("physical-component") {
            let mut systems = BTreeSet::new();
            for system_ref in string_list(record, "implements_system") {
                systems.insert(
                    system_id_by_adr
                        .get(&system_ref)
                        .cloned()
                        .unwrap_or(system_ref),
                );
            }
            if let Some(specifications) = record
                .get("component_specifications")
                .and_then(Json::as_array)
            {
                for raw_specification in specifications {
                    let Some(specification) = raw_specification.as_object() else {
                        continue;
                    };
                    let component_id = string_field(specification, "id")
                        .or_else(|| string_field(specification, "component_id"));
                    if let Some(component_id) = component_id {
                        component_systems
                            .entry(component_id)
                            .or_default()
                            .extend(systems.iter().cloned());
                    }
                }
            }
        }
    }

    // Reviews and overrides are indexed once so every ADR reference is checked
    // against the same normalized target map and diagnostics remain ordered by
    // the already-sorted ADR records.
    let review_by_id = root
        .get("reviews")
        .and_then(Json::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(Json::as_object)
                .filter_map(|item| {
                    Some((string_field(item, "id")?, string_field(item, "target_adr")?))
                })
                .collect::<BTreeMap<_, _>>()
        })
        .unwrap_or_default();
    let override_by_id = root
        .get("overrides")
        .and_then(Json::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(Json::as_object)
                .filter_map(|item| Some((string_field(item, "id")?, item.clone())))
                .collect::<BTreeMap<_, _>>()
        })
        .unwrap_or_default();

    for (id, record) in &records {
        let kind = string_field(record, "kind").unwrap_or_default();
        let logical_refs = string_list(record, "implements_logical");
        if kind == "physical" || kind == "physical-system" || kind == "physical-component" {
            for reference in logical_refs {
                if !logical_ids.contains(&reference) {
                    diagnostics.push(diagnostic(
                        "cross_reference",
                        format!("{kind} ADR {id} references non-existent logical ADR {reference}"),
                        Some(format!("{id}.implements_logical")),
                    ));
                }
            }
        }
        if kind == "physical-system" {
            for reference in string_list(record, "references_components") {
                if !component_ids.contains(&reference) {
                    diagnostics.push(diagnostic(
                        "cross_reference",
                        format!("Physical-System ADR {id} references non-existent Physical-Component ADR {reference}"),
                        Some(format!("{id}.references_components")),
                    ));
                }
            }
        }
        if kind == "physical-component" {
            for reference in string_list(record, "implements_system") {
                if !system_ids.contains(&reference) {
                    diagnostics.push(diagnostic(
                        "cross_reference",
                        format!("Physical-Component ADR {id} references non-existent Physical-System ADR {reference}"),
                        Some(format!("{id}.implements_system")),
                    ));
                }
            }
        }
        for reference in string_list(record, "related_adrs") {
            if !all_ids.contains(&reference) {
                diagnostics.push(diagnostic_with_severity(
                    "warning",
                    "cross_reference",
                    format!("ADR {id} references non-existent related ADR {reference}"),
                    Some(format!("{id}.related_adrs")),
                ));
            }
        }

        for review_id in string_list(record, "related_reviews") {
            match review_by_id.get(&review_id) {
                None => diagnostics.push(diagnostic(
                    "review_reference",
                    format!("ADR {id} references non-existent steelman review {review_id}"),
                    Some(format!("{id}.related_reviews")),
                )),
                Some(target) if target != id => diagnostics.push(diagnostic(
                    "review_reference",
                    format!(
                        "Steelman review {review_id} targets {target} but is referenced by {id}"
                    ),
                    Some(format!("{id}.related_reviews")),
                )),
                Some(_) => {}
            }
        }

        for override_id in string_list(record, "related_overrides") {
            match override_by_id.get(&override_id) {
                None => diagnostics.push(diagnostic(
                    "override_reference",
                    format!("ADR {id} references non-existent objection override {override_id}"),
                    Some(format!("{id}.related_overrides")),
                )),
                Some(override_record) => {
                    if let Some(target) = string_field(override_record, "related_adr") {
                        if target != *id {
                            diagnostics.push(diagnostic(
                                "override_reference",
                                format!("Objection override {override_id} points to {target} but is referenced by {id}"),
                                Some(format!("{id}.related_overrides")),
                            ));
                        }
                    }
                }
            }
        }

        if kind == "physical-system"
            && string_field(record, "schema_version").as_deref() == Some("1.5")
        {
            if let Some(system_id) = string_field(record, "system_id") {
                for component_ref in string_list(record, "topology_components") {
                    if !component_systems
                        .get(&component_ref)
                        .map(|systems| systems.contains(&system_id))
                        .unwrap_or(false)
                    {
                        diagnostics.push(diagnostic(
                            "topology_membership",
                            format!("PS {id} topology member {component_ref} is not claimed by a PC implements_system for system {system_id}"),
                            Some(format!("{id}.component_topology")),
                        ));
                    }
                }
            }
        }
    }

    let review_records = root
        .get("reviews")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    for raw_review in review_records {
        let Some(review) = raw_review.as_object() else {
            continue;
        };
        let Some(review_id) = string_field(review, "id") else {
            continue;
        };
        let Some(target) = string_field(review, "target_adr") else {
            continue;
        };
        if !all_ids.contains(&target) {
            diagnostics.push(diagnostic(
                "review_reference",
                format!("Steelman review {review_id} references non-existent ADR {target}"),
                Some(format!("{review_id}.target_adr")),
            ));
        }
    }

    let override_records = root
        .get("overrides")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    for raw_override in override_records {
        let Some(override_record) = raw_override.as_object() else {
            continue;
        };
        let Some(override_id) = string_field(override_record, "id") else {
            continue;
        };
        let Some(target) = string_field(override_record, "related_adr") else {
            continue;
        };
        if !all_ids.contains(&target) {
            diagnostics.push(diagnostic(
                "override_reference",
                format!("Objection override {override_id} references non-existent ADR {target}"),
                Some(format!("{override_id}.related_adr")),
            ));
        }
    }

    let success = !diagnostics.iter().any(|item| {
        item.as_object()
            .and_then(|value| value.get("severity"))
            .and_then(Json::as_str)
            .unwrap_or("error")
            == "error"
    });
    let error_count = diagnostics
        .iter()
        .filter(|item| {
            item.as_object()
                .and_then(|value| value.get("severity"))
                .and_then(Json::as_str)
                .unwrap_or("error")
                == "error"
        })
        .count();
    let warning_count = diagnostics
        .iter()
        .filter(|item| {
            item.as_object()
                .and_then(|value| value.get("severity"))
                .and_then(Json::as_str)
                == Some("warning")
        })
        .count();
    let mut result = simple_result("validate_architecture_references", success, diagnostics);
    if let Json::Object(ref mut values) = result {
        values.insert("error_count".into(), number(error_count as u64));
        values.insert("warning_count".into(), number(warning_count as u64));
    }
    result
}

pub fn execute_json(input: &[u8]) -> Vec<u8> {
    // This dispatcher is the versioned execution boundary consumed by every
    // host. Adding an operation here means adding it to the semantic contract
    // and conformance vectors; it is not a license for a host to invent a
    // parallel implementation for the same operation.
    match serde_json::from_slice::<Json>(input) {
        Ok(value) => {
            let declared_version = value
                .as_object()
                .and_then(|object| object.get("core_contract_version"))
                .and_then(Json::as_str);
            let operation = value
                .as_object()
                .and_then(|object| object.get("operation"))
                .and_then(Json::as_str);
            let result = if declared_version == Some(VERSION_1_1) {
                match operation {
                    Some("resolve_semantic_contract_set") => {
                        semantic_contract_set::resolve_exact(&value)
                    }
                    Some("materialize_architecture") => materialization::execute(&value),
                    Some(operation) => invalid_v11(
                        operation,
                        "operation is not available in semantic-core protocol 1.1",
                    ),
                    None => invalid_v11("invalid_request", "operation is required"),
                }
            } else {
                match operation {
                    Some("validate_contract") => validate(&value),
                    Some("validate_project_metadata") => validate_project_metadata(&value),
                    Some("open_provider_registry") => validate_provider_registry(&value),
                    Some("open_repository") => validate_repository(&value),
                    Some("build_embodiment_linkage") => linkage::execute(&value),
                    Some("generate_attribution_shim") => attribution::execute(&value),
                    Some("classify_generated_artifact") => classify_generated_artifact(&value),
                    Some("validate_architecture_references") => {
                        validate_architecture_references(&value)
                    }
                    Some("validate_architecture") => architecture::execute(&value),
                    Some("canonicalize_semantic_json") => semantic_contract::canonicalize(&value),
                    Some("fingerprint_semantic_contract") => semantic_contract::fingerprint(&value),
                    Some("validate_semantic_resource_closure") => {
                        semantic_contract::validate_closure(&value)
                    }
                    Some("compose_semantic_contract_set") => semantic_contract::compose_set(&value),
                    Some("validate_semantic_contract_profile") => {
                        semantic_contract_set::validate_profile(&value)
                    }
                    Some("validate_semantic_contract_qualification") => {
                        semantic_contract_set::validate_qualification(&value)
                    }
                    Some("assemble_semantic_contract_set") => {
                        semantic_contract_set::assemble(&value)
                    }
                    Some("validate_semantic_contract_corpus") => {
                        semantic_contract_set::validate_corpus(&value)
                    }
                    Some("resolve_current_semantic_contract_set") => {
                        semantic_contract_set::resolve_current(&value)
                    }
                    Some(_) | None => invalid("unsupported semantic core operation"),
                }
            };
            json(&result).into_bytes()
        }
        Err(error) => json(&invalid(format!("malformed JSON: {error}"))).into_bytes(),
    }
}

static mut LAST_RESULT_LEN: usize = 0;

// These exports are only a byte-oriented transport ABI for the canonical
// semantic boundary. No Rust-native types, ownership model, lifecycle, or
// allocator behavior is part of the Python/Node/browser public API.
#[no_mangle]
pub extern "C" fn alloc(size: usize) -> *mut u8 {
    let mut buffer = Vec::with_capacity(size);
    let pointer = buffer.as_mut_ptr();
    std::mem::forget(buffer);
    pointer
}
#[no_mangle]
pub unsafe extern "C" fn dealloc(pointer: *mut u8, size: usize) {
    if !pointer.is_null() {
        drop(Vec::from_raw_parts(pointer, 0, size));
    }
}
#[no_mangle]
pub unsafe extern "C" fn execute(pointer: *const u8, size: usize) -> *mut u8 {
    let input = if pointer.is_null() {
        &[]
    } else {
        std::slice::from_raw_parts(pointer, size)
    };
    let result = execute_json(input);
    LAST_RESULT_LEN = result.len();
    let pointer = alloc(result.len());
    std::ptr::copy_nonoverlapping(result.as_ptr(), pointer, result.len());
    pointer
}
#[no_mangle]
pub unsafe extern "C" fn result_len() -> usize {
    LAST_RESULT_LEN
}

#[cfg(test)]
mod semantic_core_v11_tests {
    use super::Json;

    fn execute(request: Json) -> Json {
        let bytes = serde_json::to_vec(&request).expect("test request serializes");
        serde_json::from_slice(&super::execute_json(&bytes)).expect("core result is JSON")
    }

    #[test]
    fn v11_vector_inventory_covers_the_required_evidence_cases() {
        let vectors: Json = serde_json::from_str(include_str!(
            "../../contracts/semantic-core/v1.1/vectors/architecture-materialization.json"
        ))
        .expect("v1.1 vectors are valid JSON");
        let cases = vectors
            .as_object()
            .and_then(|value| value.get("cases"))
            .and_then(Json::as_array)
            .expect("v1.1 vectors contain cases");
        assert!(cases.len() >= 20);
    }

    #[test]
    fn v11_exact_resolution_is_routed_to_the_v11_boundary() {
        let result = execute(Json::Object(std::collections::BTreeMap::from([
            ("core_contract_version".into(), Json::String("1.1".into())),
            (
                "operation".into(),
                Json::String("resolve_semantic_contract_set".into()),
            ),
        ])));
        assert_eq!(
            result
                .as_object()
                .and_then(|value| value.get("core_contract_version"))
                .and_then(Json::as_str),
            Some("1.1")
        );
        assert_eq!(
            result.as_object().and_then(|value| value.get("success")),
            Some(&Json::Bool(false))
        );
    }

    #[test]
    fn v11_materialization_without_an_exact_set_id_is_rejected() {
        let result = execute(Json::Object(std::collections::BTreeMap::from([
            ("core_contract_version".into(), Json::String("1.1".into())),
            (
                "operation".into(),
                Json::String("materialize_architecture".into()),
            ),
        ])));
        assert_eq!(
            result
                .as_object()
                .and_then(|value| value.get("outcome"))
                .and_then(Json::as_str),
            Some("Rejected")
        );
    }
}
