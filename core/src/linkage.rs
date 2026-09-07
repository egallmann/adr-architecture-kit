use std::collections::{BTreeMap, BTreeSet};

use super::{
    diagnostic, diagnostic_with_severity, invalid, object, simple_result, string, Json, VERSION,
};

fn text(object: &BTreeMap<String, Json>, key: &str) -> String {
    object
        .get(key)
        .and_then(Json::as_str)
        .unwrap_or("")
        .to_owned()
}

fn optional_text(object: &BTreeMap<String, Json>, key: &str) -> Option<String> {
    object.get(key).and_then(Json::as_str).map(str::to_owned)
}

fn provenance_key(value: Option<&Json>) -> String {
    let Some(value) = value.and_then(Json::as_object) else {
        return String::new();
    };
    [
        text(value, "source_file"),
        text(value, "source_pointer"),
        value.get("start_line").map(super::json).unwrap_or_default(),
        value.get("end_line").map(super::json).unwrap_or_default(),
        text(value, "extractor"),
        text(value, "commit"),
    ]
    .join("\u{1f}")
}

fn copy_provenance(value: Option<&Json>) -> Json {
    let Some(Json::Object(value)) = value else {
        return Json::Object(Json::object());
    };
    let mut output = Json::object();
    for key in [
        "source_file",
        "extractor",
        "commit",
        "source_pointer",
        "start_line",
        "end_line",
    ] {
        if let Some(value) = value.get(key) {
            output.insert(key.to_owned(), value.clone());
        }
    }
    Json::Object(output)
}

fn occurrence(record: &BTreeMap<String, Json>, claim: &BTreeMap<String, Json>) -> Json {
    let mut output = Json::object();
    output.insert("confidence".into(), string(text(claim, "confidence")));
    output.insert(
        "provenance".into(),
        copy_provenance(record.get("provenance")),
    );
    if let Some(language) = record.get("attribution_source_language") {
        output.insert("source_language".into(), language.clone());
    }
    Json::Object(output)
}

fn occurrence_key(value: &Json) -> String {
    let Some(value) = value.as_object() else {
        return String::new();
    };
    format!(
        "{}\u{1f}{}\u{1f}{}",
        provenance_key(value.get("provenance")),
        text(value, "confidence"),
        text(value, "source_language")
    )
}

fn relationship_rank(value: &str) -> u8 {
    match value {
        "implements" => 0,
        "enforces" => 1,
        "embodies" => 2,
        _ => 99,
    }
}

fn allowed_target(relationship: &str, entity_type: &str) -> bool {
    match relationship {
        "implements" => [
            "adr",
            "decision",
            "capability",
            "contract",
            "interface",
            "implementation_decision",
        ]
        .contains(&entity_type),
        "enforces" => entity_type == "invariant",
        "embodies" => ["system", "component", "boundary"].contains(&entity_type),
        _ => false,
    }
}

fn is_error(value: &Json) -> bool {
    value
        .as_object()
        .and_then(|object| object.get("severity"))
        .and_then(Json::as_str)
        == Some("error")
}

struct Group {
    implementation_type: String,
    entity: BTreeMap<String, Json>,
    occurrences: Vec<Json>,
    diagnostics: Vec<Json>,
}

pub(crate) fn execute(request: &Json) -> Json {
    // Linkage consumes normalized attribution records and produces the shared
    // evidence model. Hosts collect source/provenance facts; this function
    // owns relationship admissibility, deduplication, conflict handling, and
    // deterministic output ordering for every SDK.
    let Some(root) = request.as_object() else {
        return invalid("request must be an object");
    };
    if root.get("core_contract_version").and_then(Json::as_str) != Some(VERSION) {
        return invalid("unsupported core_contract_version; expected 1.0");
    }
    if root.get("operation").and_then(Json::as_str) != Some("build_embodiment_linkage") {
        return invalid("unsupported semantic core operation");
    }
    let profile = root
        .get("profile")
        .and_then(Json::as_str)
        .unwrap_or("greenfield");
    if !["greenfield", "brownfield", "migration"].contains(&profile) {
        return invalid("unsupported linkage profile");
    }
    let version = root
        .get("evidence_schema_version")
        .and_then(Json::as_str)
        .unwrap_or("");
    if !["1.5", "1.6"].contains(&version) {
        return invalid("unsupported evidence schema version");
    }
    let Some(records) = root.get("records").and_then(Json::as_array) else {
        return simple_result(
            "build_embodiment_linkage",
            false,
            vec![diagnostic(
                "attribution.invalid_records",
                "records must be an array",
                Some("records".into()),
            )],
        );
    };
    let Some(entities) = root.get("entities").and_then(Json::as_array) else {
        return simple_result(
            "build_embodiment_linkage",
            false,
            vec![diagnostic(
                "attribution.invalid_entities",
                "entities must be an array",
                Some("entities".into()),
            )],
        );
    };
    let mut entity_map = BTreeMap::new();
    for value in entities {
        if let Some(entity) = value.as_object() {
            let id = text(entity, "id");
            if !id.is_empty() {
                entity_map.insert(id, entity.clone());
            }
        }
    }

    let mut diagnostics = Vec::new();
    let mut rejected: Vec<(String, Json)> = Vec::new();
    let mut groups: BTreeMap<String, Group> = BTreeMap::new();
    let mut implementation_types = BTreeMap::new();
    let mut seen_occurrences: BTreeMap<String, (String, String, Option<String>)> = BTreeMap::new();

    for (record_index, raw_record) in records.iter().enumerate() {
        let Some(record) = raw_record.as_object() else {
            diagnostics.push(diagnostic(
                "attribution.invalid_record",
                "record must be an object",
                Some(format!("records[{record_index}]")),
            ));
            continue;
        };
        let implementation_id = text(record, "implementation_entity_id");
        let implementation_type = text(record, "implementation_entity_type");
        let source_language = optional_text(record, "attribution_source_language");
        let provenance_identity = provenance_key(record.get("provenance"));
        let claims = record
            .get("claims")
            .and_then(Json::as_array)
            .cloned()
            .unwrap_or_default();
        if claims.is_empty() {
            diagnostics.push(diagnostic_with_severity(
                if profile == "greenfield" {
                    "error"
                } else {
                    "warning"
                },
                "attribution.missing_claims",
                "implementation artifact is missing required architecture attribution",
                Some(format!("records[{record_index}].claims")),
            ));
        }
        let previous_type = implementation_types
            .entry(implementation_id.clone())
            .or_insert_with(|| implementation_type.clone())
            .clone();
        let type_conflict = previous_type != implementation_type;
        let mut seen_in_record = BTreeSet::new();

        // A claim is first checked for admissibility and duplicate evidence;
        // only accepted claims can contribute to the grouped output. Rejected
        // claims remain observable so callers can distinguish non-admission
        // from missing evidence.
        for (claim_index, raw_claim) in claims.iter().enumerate() {
            let Some(claim) = raw_claim.as_object() else {
                continue;
            };
            let relationship = text(claim, "relationship");
            let target_id = text(claim, "target_entity_id");
            let confidence = text(claim, "confidence");
            let path = format!("records[{record_index}].claims[{claim_index}]");
            let mut claim_diagnostics = Vec::new();
            if !seen_in_record.insert(format!("{relationship}\u{1f}{target_id}")) {
                claim_diagnostics.push(diagnostic(
                    "attribution.duplicate_claim",
                    "duplicate relationship/target claim within one record",
                    Some(path.clone()),
                ));
            }
            let occurrence_identity = format!(
                "{implementation_id}\u{1f}{relationship}\u{1f}{target_id}\u{1f}{provenance_identity}"
            );
            if let Some((previous_path, previous_confidence, previous_language)) =
                seen_occurrences.get(&occurrence_identity)
            {
                let (code, message) = if previous_confidence == &confidence
                    && previous_language == &source_language
                {
                    (
                        "attribution.duplicate_occurrence",
                        format!("exact evidence occurrence already declared at {previous_path}"),
                    )
                } else {
                    (
                        "attribution.conflicting_occurrence",
                        format!("evidence occurrence has conflicting confidence or source-language qualifiers relative to {previous_path}"),
                    )
                };
                claim_diagnostics.push(diagnostic(code, message, Some(path.clone())));
            } else {
                seen_occurrences.insert(
                    occurrence_identity,
                    (path.clone(), confidence.clone(), source_language.clone()),
                );
            }
            if type_conflict {
                claim_diagnostics.push(diagnostic(
                    "attribution.conflicting_implementation_type",
                    format!("implementation entity was previously typed {previous_type}"),
                    Some(path.clone()),
                ));
            }
            if version == "1.6" && relationship == "enforces" && confidence != "declared" {
                claim_diagnostics.push(diagnostic(
                    "attribution.v16_enforces_confidence",
                    "v1.6 enforces requires confidence declared",
                    Some(path.clone()),
                ));
            }
            let entity = entity_map.get(&target_id);
            if entity.is_none() {
                claim_diagnostics.push(diagnostic(
                    "attribution.unresolved_target",
                    format!("referenced architecture entity does not exist: {target_id}"),
                    Some(path.clone()),
                ));
            } else if let Some(entity) = entity {
                let entity_type = text(entity, "entity_type");
                if let Some(asserted) = optional_text(claim, "asserted_target_entity_type") {
                    if asserted != entity_type {
                        claim_diagnostics.push(diagnostic(
                            "attribution.asserted_type_mismatch",
                            format!("asserted target type {asserted} does not match {entity_type}"),
                            Some(path.clone()),
                        ));
                    }
                }
                if !allowed_target(&relationship, &entity_type) {
                    claim_diagnostics.push(diagnostic(
                        "attribution.illegal_target_type",
                        format!("{relationship} does not admit target type {entity_type}"),
                        Some(path.clone()),
                    ));
                }
            }
            diagnostics.extend(claim_diagnostics.clone());
            if claim_diagnostics.iter().any(is_error) || entity.is_none() {
                let mut rejected_value = Json::object();
                rejected_value.insert(
                    "implementation_entity_id".into(),
                    string(implementation_id.clone()),
                );
                rejected_value.insert(
                    "implementation_entity_type".into(),
                    string(implementation_type.clone()),
                );
                rejected_value.insert("relationship".into(), string(relationship.clone()));
                rejected_value.insert("target_entity_id".into(), string(target_id.clone()));
                rejected_value.insert("confidence".into(), string(confidence));
                rejected_value.insert(
                    "provenance".into(),
                    copy_provenance(record.get("provenance")),
                );
                rejected_value.insert("diagnostics".into(), Json::Array(claim_diagnostics));
                let key = format!(
                    "{implementation_id}\u{1f}{:02}\u{1f}{target_id}\u{1f}{provenance_identity}",
                    relationship_rank(&relationship)
                );
                rejected.push((key, Json::Object(rejected_value)));
                continue;
            }
            let entity = entity.expect("entity checked above");
            let mut link_diagnostics = Vec::new();
            let lifecycle = text(entity, "lifecycle_stage");
            if lifecycle == "deprecated" || lifecycle == "superseded" {
                let warning = diagnostic_with_severity(
                    "warning",
                    "attribution.target_lifecycle",
                    format!("referenced architecture entity is {lifecycle}"),
                    Some(path),
                );
                diagnostics.push(warning.clone());
                link_diagnostics.push(warning);
            }
            let group_key = format!("{implementation_id}\u{1f}{relationship}\u{1f}{target_id}");
            let group = groups.entry(group_key).or_insert_with(|| Group {
                implementation_type: implementation_type.clone(),
                entity: entity.clone(),
                occurrences: Vec::new(),
                diagnostics: Vec::new(),
            });
            group.occurrences.push(occurrence(record, claim));
            group.diagnostics.extend(link_diagnostics);
        }
    }

    let mut links: Vec<(String, Json)> = Vec::new();
    for (group_key, mut group) in groups {
        let mut parts = group_key.split('\u{1f}');
        let implementation_id = parts.next().unwrap_or("").to_owned();
        let relationship = parts.next().unwrap_or("").to_owned();
        let target_id = parts.next().unwrap_or("").to_owned();
        group.occurrences.sort_by_key(occurrence_key);
        let mut link = Json::object();
        link.insert(
            "implementation_entity_id".into(),
            string(implementation_id.clone()),
        );
        link.insert(
            "implementation_entity_type".into(),
            string(group.implementation_type),
        );
        link.insert("relationship".into(), string(relationship.clone()));
        link.insert("target_entity_id".into(), string(target_id.clone()));
        link.insert(
            "target_entity_type".into(),
            string(text(&group.entity, "entity_type")),
        );
        link.insert(
            "target_alias_id".into(),
            string(text(&group.entity, "alias_id")),
        );
        link.insert(
            "target_alias_name".into(),
            string(text(&group.entity, "alias_name")),
        );
        link.insert(
            "target_lifecycle".into(),
            string(text(&group.entity, "lifecycle_stage")),
        );
        link.insert("occurrences".into(), Json::Array(group.occurrences.clone()));
        link.insert(
            "validation_status".into(),
            string(if group.diagnostics.is_empty() {
                "valid"
            } else {
                "warning"
            }),
        );
        link.insert("diagnostics".into(), Json::Array(group.diagnostics));
        link.insert(
            "authority_ceiling".into(),
            string("validated_derived_evidence"),
        );
        link.insert("graph_admission_status".into(), string("not_admitted"));
        let occurrence_key = group
            .occurrences
            .first()
            .map(occurrence_key)
            .unwrap_or_default();
        links.push((
            format!(
                "{implementation_id}\u{1f}{:02}\u{1f}{target_id}\u{1f}{occurrence_key}",
                relationship_rank(&relationship)
            ),
            Json::Object(link),
        ));
    }
    links.sort_by(|left, right| left.0.cmp(&right.0));
    rejected.sort_by(|left, right| left.0.cmp(&right.0));
    let error_count = diagnostics.iter().filter(|value| is_error(value)).count();
    let warning_count = diagnostics
        .iter()
        .filter(|value| {
            value
                .as_object()
                .and_then(|object| object.get("severity"))
                .and_then(Json::as_str)
                == Some("warning")
        })
        .count();
    object([
        ("core_contract_version".into(), string(VERSION)),
        ("operation".into(), string("build_embodiment_linkage")),
        ("success".into(), Json::Bool(error_count == 0)),
        ("evidence_schema_version".into(), string(version)),
        (
            "architecture_fingerprint".into(),
            root.get("architecture_fingerprint")
                .cloned()
                .unwrap_or(Json::Null),
        ),
        (
            "links".into(),
            Json::Array(links.into_iter().map(|(_, value)| value).collect()),
        ),
        (
            "rejected_claims".into(),
            Json::Array(rejected.into_iter().map(|(_, value)| value).collect()),
        ),
        ("diagnostics".into(), Json::Array(diagnostics)),
        ("error_count".into(), super::number(error_count as u64)),
        ("warning_count".into(), super::number(warning_count as u64)),
        (
            "authority_ceiling".into(),
            string("validated_derived_evidence"),
        ),
        ("graph_admission_status".into(), string("not_admitted")),
    ])
}
