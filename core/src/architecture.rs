//! Canonical ADR business-rule validation over host-normalized source records.
//!
//! The hosts deliberately retain YAML parsing, schema dispatch, filesystem
//! discovery, and path-existence facts. This module is the semantic authority
//! for the rules that interpret those facts, so Python and Node cannot drift by
//! maintaining separate copies of the same governance checks.

use std::collections::BTreeSet;

use super::{diagnostic_with_severity, invalid, simple_result, string, Json, VERSION};

fn text(object: &std::collections::BTreeMap<String, Json>, key: &str) -> Option<String> {
    object.get(key).and_then(Json::as_str).map(str::to_owned)
}

fn values(object: &std::collections::BTreeMap<String, Json>, key: &str) -> Vec<String> {
    let mut result = object
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
    result.sort();
    result.dedup();
    result
}

fn non_empty(value: Option<&Json>) -> bool {
    match value {
        Some(Json::String(value)) => !value.is_empty(),
        Some(Json::Array(value)) => !value.is_empty(),
        Some(Json::Object(value)) => !value.is_empty(),
        Some(Json::Bool(value)) => *value,
        Some(Json::Number(value)) => !value.is_empty() && value != "0",
        Some(Json::Null) | None => false,
    }
}

fn word_present(value: &str, word: &str) -> bool {
    let bytes = value.as_bytes();
    let word_bytes = word.as_bytes();
    if word_bytes.is_empty() || word_bytes.len() > bytes.len() {
        return false;
    }
    for start in 0..=bytes.len() - word_bytes.len() {
        if !bytes[start..start + word_bytes.len()].eq_ignore_ascii_case(word_bytes) {
            continue;
        }
        let before = start.checked_sub(1).and_then(|index| bytes.get(index));
        let after = bytes.get(start + word_bytes.len());
        let boundary = |item: Option<&u8>| {
            item.map(|byte| !byte.is_ascii_alphanumeric() && *byte != b'_')
                .unwrap_or(true)
        };
        if !boundary(before) || !boundary(after) {
            continue;
        }
        if (word == "class" || word == "module") && before == Some(&b'-') {
            continue;
        }
        return true;
    }
    false
}

fn emit(
    diagnostics: &mut Vec<Json>,
    source_ref: &str,
    severity: &str,
    code: &str,
    message: impl Into<String>,
    field: Option<&str>,
) {
    let mut value = match severity {
        "warning" => diagnostic_with_severity("warning", code, message, field.map(str::to_owned)),
        _ => diagnostic_with_severity("error", code, message, field.map(str::to_owned)),
    };
    if let Json::Object(ref mut object) = value {
        object.insert("source_ref".into(), string(source_ref));
    }
    diagnostics.push(value);
}

fn validate_governance(
    document: &std::collections::BTreeMap<String, Json>,
    source_ref: &str,
    diagnostics: &mut Vec<Json>,
) {
    if document.contains_key("related_ledgers") {
        emit(
            diagnostics,
            source_ref,
            "warning",
            "governance_deprecation",
            "Top-level related_ledgers is deprecated; use governance.related_ledgers instead",
            Some("related_ledgers"),
        );
    }
    let Some(governance) = document.get("governance").and_then(Json::as_object) else {
        return;
    };
    let approved_by = non_empty(governance.get("approved_by"));
    let approved_date = non_empty(governance.get("approved_date"));
    if approved_by && !approved_date {
        emit(
            diagnostics,
            source_ref,
            "error",
            "governance_pairing",
            "governance.approved_by requires governance.approved_date",
            Some("governance.approved_date"),
        );
    }
    if approved_date && !approved_by {
        emit(
            diagnostics,
            source_ref,
            "error",
            "governance_pairing",
            "governance.approved_date requires governance.approved_by",
            Some("governance.approved_by"),
        );
    }
    let review_required = matches!(
        governance.get("steelman_review_required"),
        Some(Json::Bool(true))
    );
    let review_completed = matches!(
        governance.get("steelman_review_completed"),
        Some(Json::Bool(true))
    );
    if review_required && governance.get("steelman_review_completed").is_none() {
        emit(
            diagnostics,
            source_ref,
            "error",
            "governance_steelman",
            "governance.steelman_review_required=true requires an explicit governance.steelman_review_completed value",
            Some("governance.steelman_review_completed"),
        );
    }
    if matches!(
        governance.get("steelman_review_required"),
        Some(Json::Bool(false))
    ) && review_completed
    {
        emit(
            diagnostics,
            source_ref,
            "error",
            "governance_steelman",
            "governance.steelman_review_completed=true is invalid when governance.steelman_review_required=false",
            Some("governance.steelman_review_completed"),
        );
    }
    if review_completed && values(governance, "related_reviews").is_empty() {
        emit(
            diagnostics,
            source_ref,
            "error",
            "governance_steelman",
            "governance.steelman_review_completed=true requires at least one governance.related_reviews entry",
            Some("governance.related_reviews"),
        );
    }
    if text(governance, "implementation_authority").as_deref()
        == Some("implementation_authoritative")
    {
        if !approved_by || !approved_date {
            emit(
                diagnostics,
                source_ref,
                "error",
                "governance_implementation_authority",
                "governance.implementation_authority=implementation_authoritative requires approval metadata",
                Some("governance.implementation_authority"),
            );
        }
        if review_required && !review_completed {
            emit(
                diagnostics,
                source_ref,
                "error",
                "governance_implementation_authority",
                "implementation-authoritative ADRs requiring steelman review must set governance.steelman_review_completed=true",
                Some("governance.steelman_review_completed"),
            );
        }
    }
}

fn validate_logical(
    document: &std::collections::BTreeMap<String, Json>,
    source_ref: &str,
    diagnostics: &mut Vec<Json>,
) {
    let context = text(document, "context").unwrap_or_default().to_lowercase();
    for word in [
        "class", "function", "module", "package", "import", "npm", "pip",
    ] {
        if word_present(&context, word) {
            emit(
                diagnostics,
                source_ref,
                "warning",
                "INV-0002",
                format!("Logical ADR may contain implementation details (found '{word}')"),
                Some("context"),
            );
            break;
        }
    }
    if text(document, "id")
        .map(|value| value.starts_with("ADR-L-"))
        .unwrap_or(false)
        && document
            .get("decisions")
            .and_then(Json::as_array)
            .map(|items| items.is_empty())
            .unwrap_or(true)
    {
        emit(
            diagnostics,
            source_ref,
            "warning",
            "completeness",
            "Logical ADR has no decisions defined",
            Some("decisions"),
        );
    }
    let mut invariant_ids = BTreeSet::new();
    if let Some(invariants) = document.get("invariants").and_then(Json::as_array) {
        for invariant in invariants {
            if let Some(id) = invariant.as_object().and_then(|item| text(item, "id")) {
                if !invariant_ids.insert(id) {
                    emit(
                        diagnostics,
                        source_ref,
                        "error",
                        "INV-0005",
                        "Duplicate invariant IDs found",
                        Some("invariants"),
                    );
                    break;
                }
            }
        }
    }
}

fn validate_physical(
    document: &std::collections::BTreeMap<String, Json>,
    source_ref: &str,
    diagnostics: &mut Vec<Json>,
) {
    if values(document, "implements_logical").is_empty() {
        emit(
            diagnostics,
            source_ref,
            "error",
            "INV-0003",
            "Physical ADR must reference at least one logical ADR",
            Some("implements_logical"),
        );
    }
    if !non_empty(document.get("component_specifications")) {
        emit(
            diagnostics,
            source_ref,
            "warning",
            "completeness",
            "Physical ADR has no component specifications",
            Some("component_specifications"),
        );
    }
    if let Some(missing) = document
        .get("missing_implementation_identifiers")
        .and_then(Json::as_array)
    {
        for item in missing.iter().filter_map(Json::as_str) {
            emit(
                diagnostics,
                source_ref,
                "warning",
                "implementation_identifier",
                format!("Implementation identifier not found: {item}"),
                Some("component_specifications.implementation_identifiers"),
            );
        }
    }
}

fn validate_physical_system(
    document: &std::collections::BTreeMap<String, Json>,
    source_ref: &str,
    diagnostics: &mut Vec<Json>,
) {
    if values(document, "implements_logical").is_empty() {
        emit(
            diagnostics,
            source_ref,
            "error",
            "physical_system_logical_ref",
            "Physical-System ADR must reference at least one logical ADR",
            Some("implements_logical"),
        );
    }
    if !non_empty(document.get("system_boundaries")) {
        emit(
            diagnostics,
            source_ref,
            "warning",
            "completeness",
            "Physical-System ADR should define system boundaries",
            Some("system_boundaries"),
        );
    }
    if document
        .get("references_components")
        .and_then(Json::as_array)
        .map(|items| items.is_empty())
        .unwrap_or(false)
    {
        emit(
            diagnostics,
            source_ref,
            "warning",
            "completeness",
            "references_components is empty, consider removing or adding component references",
            Some("references_components"),
        );
    }
}

fn validate_physical_component(
    document: &std::collections::BTreeMap<String, Json>,
    source_ref: &str,
    diagnostics: &mut Vec<Json>,
) {
    if values(document, "implements_system").is_empty() {
        emit(
            diagnostics,
            source_ref,
            "error",
            "physical_component_system_ref",
            "Physical-Component ADR must reference at least one Physical-System ADR",
            Some("implements_system"),
        );
    }
    if values(document, "implements_logical").is_empty() {
        emit(
            diagnostics,
            source_ref,
            "error",
            "physical_component_logical_ref",
            "Physical-Component ADR must reference at least one logical ADR",
            Some("implements_logical"),
        );
    }
    let specifications = document
        .get("component_specifications")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    if specifications.is_empty() {
        emit(
            diagnostics,
            source_ref,
            "error",
            "completeness",
            "Physical-Component ADR must have at least one component specification",
            Some("component_specifications"),
        );
    }
    let schema_version = text(document, "schema_version").unwrap_or_default();
    if ["", "1.0", "1.2"].contains(&schema_version.as_str()) {
        for specification in &specifications {
            let Some(specification) = specification.as_object() else {
                continue;
            };
            let component_id = text(specification, "id")
                .or_else(|| text(specification, "alias_id"))
                .unwrap_or_else(|| "?".into());
            for field in [
                "implementation_identifiers",
                "interfaces",
                "generation_context",
                "implementation_requirements",
            ] {
                if !non_empty(specification.get(field)) {
                    emit(
                        diagnostics,
                        source_ref,
                        "error",
                        "ai_generation_readiness",
                        format!(
                            "Component {component_id} missing {field} (required for AI generation)"
                        ),
                        Some(&format!("component_specifications.{field}")),
                    );
                }
            }
        }
    }
    if specifications.len() > 10 {
        emit(
            diagnostics,
            source_ref,
            "warning",
            "granularity",
            format!(
                "Physical-Component ADR has {} components (>10). Ensure granularity is justified.",
                specifications.len()
            ),
            Some("component_specifications"),
        );
    }
    if let Some(compatibility) = document
        .get("interface_compatibility")
        .and_then(Json::as_object)
    {
        if let Some(supersedes_adr) = text(compatibility, "supersedes_adr") {
            if !values(document, "supersedes").contains(&supersedes_adr) {
                emit(
                    diagnostics,
                    source_ref,
                    "warning",
                    "interface_compatibility",
                    "interface_compatibility.supersedes_adr should be listed in supersedes field",
                    Some("interface_compatibility"),
                );
            }
        }
    }
}

pub(crate) fn execute(request: &Json) -> Json {
    // This operation owns normalized ADR business rules. YAML decoding,
    // schema-version dispatch, and path existence checks remain host facts;
    // Python and Node submit those facts to the same deterministic evaluator.
    let Some(root) = request.as_object() else {
        return invalid("request must be an object");
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some(VERSION) {
        return invalid("unsupported core_contract_version; expected 1.0");
    }
    if root.get("operation").and_then(Json::as_str) != Some("validate_architecture") {
        return invalid("unsupported semantic core operation");
    }
    let mode = root
        .get("mode")
        .and_then(Json::as_str)
        .unwrap_or("complete");
    let Some(records) = root.get("records").and_then(Json::as_array) else {
        return invalid("records must be an array");
    };
    let mut normalized = Vec::new();
    let mut diagnostics = Vec::new();
    // Validate the transport shape before evaluating ADR semantics. A malformed
    // host record is an execution-contract error, not an ADR business-rule
    // failure, and must remain visible at its transport location.
    for (index, raw) in records.iter().enumerate() {
        let Some(record) = raw.as_object() else {
            diagnostics.push(diagnostic_with_severity(
                "error",
                "architecture.invalid_record",
                "record must be an object",
                Some(format!("records[{index}]")),
            ));
            continue;
        };
        let Some(source_ref) = text(record, "path") else {
            diagnostics.push(diagnostic_with_severity(
                "error",
                "architecture.invalid_record",
                "record path must be a string",
                Some(format!("records[{index}].path")),
            ));
            continue;
        };
        let Some(document) = record.get("document").and_then(Json::as_object) else {
            diagnostics.push(diagnostic_with_severity(
                "error",
                "architecture.invalid_record",
                "record document must be an object",
                Some(format!("records[{index}].document")),
            ));
            continue;
        };
        normalized.push((source_ref, document.clone()));
    }
    // BTreeMap-backed JSON gives stable field order; sorting records here gives
    // stable diagnostic order even when a host discovers files differently.
    normalized.sort_by(|left, right| left.0.cmp(&right.0));
    if mode == "complete" {
        // Structural mode intentionally stops after host schema validation. It
        // is used for incomplete drafts and must not infer semantic failure from
        // fields the author has not supplied yet.
        for (source_ref, document) in normalized {
            validate_governance(&document, &source_ref, &mut diagnostics);
            match text(&document, "adr_type").as_deref() {
                Some("logical") => validate_logical(&document, &source_ref, &mut diagnostics),
                Some("physical") => validate_physical(&document, &source_ref, &mut diagnostics),
                Some("physical-system") => {
                    validate_physical_system(&document, &source_ref, &mut diagnostics)
                }
                Some("physical-component") => {
                    validate_physical_component(&document, &source_ref, &mut diagnostics)
                }
                _ => {}
            }
        }
    }
    let error_count = diagnostics
        .iter()
        .filter(|item| {
            item.as_object()
                .and_then(|value| value.get("severity"))
                .and_then(Json::as_str)
                != Some("warning")
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
    let mut result = simple_result("validate_architecture", error_count == 0, diagnostics);
    if let Json::Object(ref mut values) = result {
        values.insert("error_count".into(), Json::Number(error_count.to_string()));
        values.insert(
            "warning_count".into(),
            Json::Number(warning_count.to_string()),
        );
    }
    result
}
