//! Internal Architecture Interpretation 1.1 semantic authority.
//!
//! This module is the forward interpreter for authoring 1.7 semantic source.
//! It intentionally does not construct requests, select source roots, mint
//! identity, persist anything, or participate in semantic-core protocol 1.2.
//! The contract resources remain the authority; this Rust code is only their
//! deterministic execution mechanism.

use std::collections::BTreeMap;

use sha2::{Digest, Sha256};

use super::{candidate_source, materialization, schema_validation, semantic_contract, Json};

const FORWARD_RELATIONSHIPS: &[&str] = &[
    "calls",
    "depends_on",
    "publishes_to",
    "reads_from",
    "subscribes_to",
    "writes_to",
];
const FORWARD_FORBIDDEN_ENTITIES: &[&str] = &["constraint", "nfr", "requirement", "integration"];
const FORWARD_FORBIDDEN_RELATIONSHIPS: &[&str] = &[
    "consumes_interface",
    "composed_of",
    "binds_substrate",
    "binds_rule",
    "expects_evidence",
];

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct InterpretationSourceContext {
    pub(crate) canonical_source_ref: String,
    pub(crate) source_pointer: String,
}

impl InterpretationSourceContext {
    fn validate(&self) -> Result<(), String> {
        if self.canonical_source_ref.is_empty() {
            return Err("interpretation source context requires canonical_source_ref".into());
        }
        if self.source_pointer.is_empty() {
            return Err("interpretation source context requires source_pointer".into());
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum InterpretationDisposition {
    Accepted,
    Unresolved,
    Rejected,
    HistoricalCompatibility,
}

impl InterpretationDisposition {
    fn as_str(self) -> &'static str {
        match self {
            Self::Accepted => "accepted",
            Self::Unresolved => "unresolved",
            Self::Rejected => "rejected",
            Self::HistoricalCompatibility => "historical_compatibility",
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct InterpretationResult {
    pub(crate) disposition: InterpretationDisposition,
    pub(crate) normalized_type: Option<String>,
    pub(crate) identity: Option<String>,
    pub(crate) fields: Json,
    pub(crate) top_level: BTreeMap<String, Json>,
    /// The governed normalized-model record when this interpretation produces
    /// a relationship or other schema-backed normalized structure.  This is
    /// deliberately separate from the conformance vector's assertion fields.
    pub(crate) normalized_record: Option<Json>,
    pub(crate) reason_code: Option<String>,
    pub(crate) reason: Option<String>,
}

impl InterpretationResult {
    fn accepted(normalized_type: &str, identity: &str, fields: BTreeMap<String, Json>) -> Self {
        Self {
            disposition: InterpretationDisposition::Accepted,
            normalized_type: Some(normalized_type.to_owned()),
            identity: Some(identity.to_owned()),
            fields: Json::Object(fields),
            top_level: BTreeMap::new(),
            normalized_record: None,
            reason_code: None,
            reason: None,
        }
    }

    fn unresolved(fields: BTreeMap<String, Json>) -> Self {
        Self {
            disposition: InterpretationDisposition::Unresolved,
            normalized_type: Some("unresolved".into()),
            identity: Some("none".into()),
            fields: Json::Object(fields),
            top_level: BTreeMap::new(),
            normalized_record: None,
            reason_code: None,
            reason: None,
        }
    }

    fn rejected(reason_code: &str, reason: &str) -> Self {
        Self {
            disposition: InterpretationDisposition::Rejected,
            normalized_type: None,
            identity: None,
            fields: Json::Object(BTreeMap::new()),
            top_level: BTreeMap::new(),
            normalized_record: None,
            reason_code: Some(reason_code.into()),
            reason: Some(reason.into()),
        }
    }

    fn historical(normalized_type: &str, identity: &str, fields: BTreeMap<String, Json>) -> Self {
        Self {
            disposition: InterpretationDisposition::HistoricalCompatibility,
            normalized_type: Some(normalized_type.into()),
            identity: Some(identity.into()),
            fields: Json::Object(fields),
            top_level: BTreeMap::new(),
            normalized_record: None,
            reason_code: None,
            reason: None,
        }
    }

    fn with_normalized_record(mut self, record: Json) -> Self {
        self.normalized_record = Some(record);
        self
    }

    pub(crate) fn to_json(&self) -> Json {
        let mut values = BTreeMap::new();
        values.insert(
            "disposition".into(),
            Json::String(self.disposition.as_str().into()),
        );
        if let Some(value) = &self.normalized_type {
            values.insert("normalized_type".into(), Json::String(value.clone()));
        }
        if let Some(value) = &self.identity {
            values.insert("identity".into(), Json::String(value.clone()));
        }
        if self.disposition == InterpretationDisposition::Rejected {
            if let Some(value) = &self.reason_code {
                values.insert("reason_code".into(), Json::String(value.clone()));
            }
            if let Some(value) = &self.reason {
                values.insert("reason".into(), Json::String(value.clone()));
            }
        } else {
            values.insert("fields".into(), self.fields.clone());
        }
        if let Some(record) = &self.normalized_record {
            values.insert("normalized_record".into(), record.clone());
        }
        values.extend(self.top_level.clone());
        Json::Object(values)
    }
}

fn object(entries: impl IntoIterator<Item = (&'static str, Json)>) -> Json {
    Json::Object(
        entries
            .into_iter()
            .map(|(key, value)| (key.to_owned(), value))
            .collect(),
    )
}

fn string(value: impl Into<String>) -> Json {
    Json::String(value.into())
}

fn compatibility_record(
    relationship_type: &str,
    from_entity_id: &str,
    to_entity_id: &str,
    source_context: &InterpretationSourceContext,
    from_key: Option<&str>,
    to_key: Option<&str>,
    provenance_classification: &str,
) -> Json {
    let digest = materialization::compatibility_assertion_digest(
        relationship_type,
        from_entity_id,
        to_entity_id,
        &source_context.canonical_source_ref,
        &source_context.source_pointer,
    );
    let mut source_provenance = BTreeMap::from([
        ("source_contract".into(), string("authoring@1.7")),
        (
            "source_pointer".into(),
            string(source_context.source_pointer.clone()),
        ),
    ]);
    if let (Some(from_key), Some(to_key)) = (from_key, to_key) {
        source_provenance.insert(
            "topology_key_endpoints".into(),
            object([
                ("from_key", string(from_key)),
                ("to_key", string(to_key)),
            ]),
        );
    }
    Json::Object(BTreeMap::from([
        ("record_kind".into(), string("compatibility")),
        ("relationship_id".into(), string(format!("assertion:{digest}"))),
        ("assertion_id".into(), string(format!("asrt-{digest}"))),
        ("relationship_type".into(), string(relationship_type)),
        ("from_entity_id".into(), string(from_entity_id)),
        ("to_entity_id".into(), string(to_entity_id)),
        ("provenance_classification".into(), string(provenance_classification)),
        ("evidence".into(), Json::Array(Vec::new())),
        (
            "source_pointer".into(),
            string(source_context.source_pointer.clone()),
        ),
        (
            "canonical_source_ref".into(),
            string(source_context.canonical_source_ref.clone()),
        ),
        ("source_provenance".into(), Json::Object(source_provenance)),
    ]))
}

fn canonical_relationship_record(
    fragment: &Json,
    qualification: &Json,
    source_context: &InterpretationSourceContext,
) -> Option<Json> {
    let id = field_text(fragment, "id")?;
    let alias_id = field_text(fragment, "alias_id")?;
    let alias_name = field_text(fragment, "alias_name")?;
    let relationship_type = field_text(fragment, "relationship_type")?;
    let from_entity_id = field_text(fragment, "from_entity_id")?;
    let to_entity_id = field_text(fragment, "to_entity_id")?;
    let properties = field(fragment, "properties")?.clone();
    let rationale = field_text(fragment, "rationale")?;
    Some(Json::Object(BTreeMap::from([
        ("record_kind".into(), string("canonical")),
        ("id".into(), string(id)),
        ("alias_id".into(), string(alias_id)),
        ("alias_name".into(), string(alias_name)),
        ("relationship_type".into(), string(relationship_type)),
        ("from_entity_id".into(), string(from_entity_id)),
        ("to_entity_id".into(), string(to_entity_id)),
        (
            "canonical_source_ref".into(),
            string(source_context.canonical_source_ref.clone()),
        ),
        (
            "source_pointer".into(),
            string(source_context.source_pointer.clone()),
        ),
        ("custom_qualification".into(), qualification.clone()),
        ("properties".into(), properties),
        ("rationale".into(), string(rationale)),
    ])))
}

fn text(value: Option<&Json>) -> Option<&str> {
    value.and_then(Json::as_str)
}

fn field<'a>(fragment: &'a Json, name: &str) -> Option<&'a Json> {
    fragment.as_object()?.get(name)
}

fn field_text(fragment: &Json, name: &str) -> Option<String> {
    text(field(fragment, name)).map(ToOwned::to_owned)
}

fn schema_name(basis: &Json) -> Option<&str> {
    let schema = text(field(basis, "schema"))?;
    schema
        .split("#/definitions/")
        .nth(1)
        .or_else(|| schema.rsplit('/').next())
}

fn basis_kind(basis: &Json) -> Option<&str> {
    text(field(basis, "kind"))
}

fn copy_fields(
    fragment: &Json,
    names: &[(&str, &str)],
) -> BTreeMap<String, Json> {
    names
        .iter()
        .filter_map(|(source, target)| field(fragment, source).cloned().map(|value| ((*target).into(), value)))
        .collect()
}

fn ids_from_objects(fragment: &Json, source: &str, target: &str) -> Option<(String, Json)> {
    let values = field(fragment, source)?.as_array()?;
    let ids = values
        .iter()
        .filter_map(|value| field(value, "id").cloned())
        .collect::<Vec<_>>();
    Some((target.into(), Json::Array(ids)))
}

fn namespace_of(semantic_type: &str) -> Option<&str> {
    semantic_type.split_once(':').map(|(namespace, _)| namespace)
}

fn valid_semantic_type(value: &str) -> bool {
    let Some((namespace, name)) = value.split_once(':') else {
        return false;
    };
    !namespace.is_empty()
        && !name.is_empty()
        && namespace
            .as_bytes()
            .first()
            .is_some_and(|byte| byte.is_ascii_lowercase())
        && name.len() >= 2
        && namespace.bytes().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || b"._-".contains(&byte)
        })
        && name.bytes().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || b"_".contains(&byte)
        })
}

fn valid_cecf(value: &str) -> bool {
    let Some(hex) = value.strip_prefix("cecf:v1:sha256:") else {
        return false;
    };
    hex.len() == 64 && hex.bytes().all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn custom_qualification(
    fragment: &Json,
    expected_kind: &str,
    semantic_type: &str,
) -> Result<Json, &'static str> {
    let Some(qualification) = field(fragment, "qualification").and_then(Json::as_object) else {
        return Err("custom_qualification_missing");
    };
    let required = [
        "semantic_kind",
        "semantic_type",
        "consumer_namespace",
        "contract_version",
        "contract_fingerprint",
    ];
    if required.iter().any(|key| !qualification.contains_key(*key)) {
        return Err("custom_qualification_missing");
    }
    if qualification.len() != required.len()
        || text(qualification.get("semantic_kind")) != Some(expected_kind)
        || text(qualification.get("semantic_type")) != Some(semantic_type)
        || !valid_semantic_type(semantic_type)
        || text(qualification.get("consumer_namespace")) != namespace_of(semantic_type)
        || !text(qualification.get("contract_version")).is_some_and(semantic_contract::is_version)
        || !text(qualification.get("contract_fingerprint")).is_some_and(valid_cecf)
    {
        return Err("custom_qualification_mismatch");
    }
    Ok(Json::Object(qualification.clone()))
}

#[cfg(test)]
fn qualified_endpoint_semantics(basis: &Json) -> Option<String> {
    let endpoints = field(basis, "endpoint_entities")?.as_array()?;
    let from = endpoints.first()?.as_object()?.get("classification")?.as_str()?;
    let to = endpoints.get(1)?.as_object()?.get("classification")?.as_str()?;
    Some(match (from, to) {
        ("qualified_custom", "canonical") => "qualified_custom entity to canonical entity".into(),
        ("canonical", "qualified_custom") => "canonical entity to qualified_custom entity".into(),
        ("qualified_custom", "qualified_custom") => {
            "qualified_custom entity to qualified_custom entity".into()
        }
        _ => "UUIDv7 references classified by explicit endpoint basis".into(),
    })
}

fn endpoint_classifications_are_governed(fragment: &Json, basis: &Json) -> bool {
    let Some(endpoints) = field(basis, "endpoint_entities").and_then(Json::as_array) else {
        return true;
    };
    let Some(from_id) = field_text(fragment, "from_entity_id") else {
        return false;
    };
    let Some(to_id) = field_text(fragment, "to_entity_id") else {
        return false;
    };
    [from_id, to_id].iter().all(|id| {
        endpoints.iter().any(|endpoint| {
            field_text(endpoint, "id").as_deref() == Some(id.as_str())
                && matches!(
                    field_text(endpoint, "classification").as_deref(),
                    Some("canonical") | Some("qualified_custom")
                )
        })
    })
}

fn topology_index(basis: &Json) -> Result<(BTreeMap<String, String>, Vec<String>), String> {
    let components = field(basis, "components")
        .and_then(Json::as_array)
        .ok_or_else(|| "topology basis must contain components".to_owned())?;
    let mut index = BTreeMap::new();
    let mut order = Vec::new();
    for component in components {
        let key = field_text(component, "topology_key")
            .ok_or_else(|| "topology component lacks topology_key".to_owned())?;
        let reference = field_text(component, "component_ref")
            .ok_or_else(|| "topology component lacks component_ref".to_owned())?;
        if index.insert(key.clone(), reference).is_some() {
            return Err(format!("duplicate owner-local topology key: {key}"));
        }
        order.push(key);
    }
    Ok((index, order))
}

fn topology_relationship(
    fragment: &Json,
    basis: &Json,
    source_context: &InterpretationSourceContext,
) -> Result<InterpretationResult, String> {
    let relationship_type = field_text(fragment, "type").unwrap_or_default();
    if !FORWARD_RELATIONSHIPS.contains(&relationship_type.as_str()) {
        return Ok(InterpretationResult::rejected(
            "forward_relationship_forbidden",
            if relationship_type == "consumes_interface" {
                "consumes_interface remains deferred"
            } else {
                "relationship type is not authorable in 1.7"
            },
        ));
    }
    let (index, order) = topology_index(basis)?;
    let from_key = field_text(fragment, "from_key").unwrap_or_default();
    let to_key = field_text(fragment, "to_key").unwrap_or_default();
    let mut missing = Vec::new();
    for key in [&from_key, &to_key] {
        if !index.contains_key(key.as_str()) && !missing.contains(key) {
            missing.push(key.clone());
        }
    }
    if !missing.is_empty() {
        let resolved_keys = order
            .into_iter()
            .filter(|key| key == &from_key || key == &to_key)
            .filter(|key| !missing.contains(key))
            .collect::<Vec<_>>();
        return Ok(InterpretationResult::unresolved(BTreeMap::from([
            ("reason_code".into(), string("topology_key_unresolved")),
            (
                "source_pointer".into(),
                string(source_context.source_pointer.clone()),
            ),
            ("resolved_keys".into(), Json::Array(resolved_keys.into_iter().map(string).collect())),
            ("missing_keys".into(), Json::Array(missing.into_iter().map(string).collect())),
        ])));
    }
    let from = index.get(&from_key).cloned().unwrap_or_default();
    let to = index.get(&to_key).cloned().unwrap_or_default();
    let fields = BTreeMap::from([
        ("from_entity_id".into(), string(from.clone())),
        ("to_entity_id".into(), string(to.clone())),
        ("relationship_type".into(), string(relationship_type.clone())),
        (
            "source_provenance".into(),
            object([
                ("topology_scope", string("owning physical-system ADR")),
                ("from_key", string(from_key.clone())),
                ("to_key", string(to_key.clone())),
            ]),
        ),
    ]);
    let mut result = InterpretationResult::accepted("compatibility", "noncanonical", fields);
    result.top_level.insert(
        "relationship_mode".into(),
        string("compatibility_projection"),
    );
    Ok(result.with_normalized_record(compatibility_record(
        &relationship_type,
        &from,
        &to,
        source_context,
        Some(&from_key),
        Some(&to_key),
        "explicit",
    )))
}

fn composition_relationship(
    fragment: &Json,
    basis: &Json,
    source_context: &InterpretationSourceContext,
) -> Result<InterpretationResult, String> {
    let system_id = field_text(fragment, "system_id")
        .or_else(|| field_text(basis, "system_id"))
        .ok_or_else(|| "composition context lacks system_id".to_owned())?;
    let components = field(fragment, "components")
        .or_else(|| field(basis, "components"))
        .and_then(Json::as_array)
        .ok_or_else(|| "composition context lacks components".to_owned())?;
    let component = components
        .first()
        .ok_or_else(|| "composition context has no component".to_owned())?;
    let component_ref = field_text(component, "component_ref")
        .ok_or_else(|| "composition component lacks component_ref".to_owned())?;
    let result = InterpretationResult::accepted(
        "composed_of",
        "noncanonical",
        BTreeMap::from([
            ("from_entity_id".into(), string(system_id)),
            ("to_entity_id".into(), string(component_ref)),
            ("relationship_mode".into(), string("composition_derived")),
        ]),
    );
    Ok(result.with_normalized_record(compatibility_record(
        "composed_of",
        field_text(fragment, "system_id")
            .or_else(|| field_text(basis, "system_id"))
            .as_deref()
            .unwrap_or_default(),
        field(fragment, "components")
            .or_else(|| field(basis, "components"))
            .and_then(Json::as_array)
            .and_then(|components| components.first())
            .and_then(|component| field_text(component, "component_ref"))
            .as_deref()
            .unwrap_or_default(),
        source_context,
        None,
        None,
        "derived",
    )))
}

fn document_result(fragment: &Json) -> Result<InterpretationResult, String> {
    let adr_type = field_text(fragment, "adr_type")
        .ok_or_else(|| "authoring ADR lacks adr_type".to_owned())?;
    if !["logical", "physical-system", "physical-component"].contains(&adr_type.as_str()) {
        return Ok(InterpretationResult::rejected(
            "forward_type_forbidden",
            "ADR family is not authorable in 1.7",
        ));
    }
    let mut fields = BTreeMap::new();
    if adr_type == "logical" {
        if let Some(value) = field(fragment, "schema_version") {
            fields.insert("schema_version".into(), value.clone());
        }
    }
    fields.insert("adr_type".into(), string(adr_type.clone()));
    if adr_type == "physical-system" {
        if let Some(system_id) = field(fragment, "system").and_then(|system| field_text(system, "id")) {
            fields.insert("system_id".into(), string(system_id));
        }
    }
    Ok(InterpretationResult::accepted("adr", "canonical_uuidv7", fields))
}

fn custom_entity_result(fragment: &Json) -> Result<InterpretationResult, String> {
    let entity_type = field_text(fragment, "entity_type").unwrap_or_default();
    if FORWARD_FORBIDDEN_ENTITIES.contains(&entity_type.as_str()) {
        return Ok(InterpretationResult::rejected(
            "forward_type_forbidden",
            "legacy entity family is not authorable in 1.7",
        ));
    }
    let qualification = match custom_qualification(fragment, "entity", &entity_type) {
        Ok(value) => value,
        Err("custom_qualification_missing") => {
            return Ok(InterpretationResult::rejected(
                "custom_qualification_missing",
                "exact CECF authority is absent",
            ))
        }
        Err(_) => {
            return Ok(InterpretationResult::rejected(
                "custom_qualification_mismatch",
                "custom qualification does not exactly qualify the entity",
            ))
        }
    };
    let mut fields = BTreeMap::from([
        ("semantic_type".into(), string(entity_type)),
        ("qualification".into(), qualification.clone()),
    ]);
    if let Some(properties) = field(fragment, "properties") {
        fields.insert("properties".into(), properties.clone());
    }
    Ok({
        let mut result = InterpretationResult::accepted(
            "qualified_custom_entity",
            "canonical_uuidv7",
            fields,
        );
        result.top_level.insert("custom_qualification".into(), qualification);
        result
    })
}

fn custom_relationship_result(
    fragment: &Json,
    basis: &Json,
    source_context: &InterpretationSourceContext,
) -> Result<InterpretationResult, String> {
    let relationship_type = field_text(fragment, "relationship_type").unwrap_or_default();
    if FORWARD_FORBIDDEN_RELATIONSHIPS.contains(&relationship_type.as_str()) {
        return Ok(InterpretationResult::rejected(
            "forward_relationship_forbidden",
            "relationship type is not authorable in 1.7",
        ));
    }
    if !endpoint_classifications_are_governed(fragment, basis) {
        return Ok(InterpretationResult::rejected(
            "custom_endpoint_classification_invalid",
            "custom relationship endpoints are not classified by the interpretation basis",
        ));
    }
    let qualification = match custom_qualification(fragment, "relationship", &relationship_type) {
        Ok(value) => value,
        Err("custom_qualification_missing") => {
            return Ok(InterpretationResult::rejected(
                "custom_qualification_missing",
                "exact CECF authority is absent",
            ))
        }
        Err(_) => {
            return Ok(InterpretationResult::rejected(
                "custom_qualification_mismatch",
                "custom qualification does not exactly qualify the relationship",
            ))
        }
    };
    let mut fields = BTreeMap::from([
        ("relationship_type".into(), string(relationship_type)),
        (
            "from_entity_id".into(),
            string(field_text(fragment, "from_entity_id").unwrap_or_default()),
        ),
        (
            "to_entity_id".into(),
            string(field_text(fragment, "to_entity_id").unwrap_or_default()),
        ),
        (
            "relationship_mode".into(),
            string("custom_explicit"),
        ),
        ("qualification".into(), qualification.clone()),
    ]);
    if let Some(properties) = field(fragment, "properties") {
        fields.insert("properties".into(), properties.clone());
    }
    let mut result = InterpretationResult::accepted(
        "qualified_custom_relationship",
        "canonical_uuidv7",
        fields,
    );
    let record_qualification = qualification.clone();
    result.top_level.insert("custom_qualification".into(), qualification);
    result.top_level.insert(
        "relationship_mode".into(),
        string("custom_explicit"),
    );
    let Some(normalized_record) =
        canonical_relationship_record(fragment, &record_qualification, source_context)
    else {
        return Ok(InterpretationResult::rejected(
            "normalized_relationship_incomplete",
            "custom relationship lacks the required normalized-model fields",
        ));
    };
    Ok(result.with_normalized_record(normalized_record))
}

fn fragment_result(
    fragment: &Json,
    basis: &Json,
    source_context: &InterpretationSourceContext,
) -> Result<InterpretationResult, String> {
    if let Some(lifecycle) = field(fragment, "lifecycle_stage") {
        if schema_name(basis) == Some("normative_proposition") || field(fragment, "normative_force").is_some() {
            let _ = lifecycle;
            return Ok(InterpretationResult::rejected(
                "np_lifecycle_forbidden",
                "NP is lifecycle-free",
            ));
        }
    }
    if basis_kind(basis) == Some("topology_resolution") {
        return topology_relationship(fragment, basis, source_context);
    }
    if basis_kind(basis) == Some("composition_context") {
        return composition_relationship(fragment, basis, source_context);
    }
    if basis_kind(basis) == Some("forward_type_disposition") {
        return Ok(InterpretationResult::rejected(
            "forward_type_forbidden",
            "legacy entity family is not authorable in 1.7",
        ));
    }
    if basis_kind(basis) == Some("historical_compatibility") {
        return Ok(InterpretationResult::historical(
            "normalized-model@2.3",
            "preserved_by_frozen_1.0_resources",
            BTreeMap::from([("forward_authority".into(), Json::Bool(false))]),
        ));
    }
    if field(fragment, "topology_key").is_some() && field(fragment, "component_ref").is_some() {
        return Ok(InterpretationResult::accepted(
            "component-reference",
            "owner_local",
            copy_fields(
                fragment,
                &[
                    ("topology_key", "topology_key"),
                    ("component_ref", "component_ref"),
                    ("purpose", "purpose"),
                    ("name", "name"),
                    ("type", "type"),
                ],
            ),
        ));
    }
    if field(fragment, "schema_version").is_some() && field(fragment, "adr_type").is_some() {
        return document_result(fragment);
    }
    if field(fragment, "relationship_type").is_some() {
        return custom_relationship_result(fragment, basis, source_context);
    }
    if field(fragment, "entity_type").is_some() {
        return custom_entity_result(fragment);
    }
    let kind = schema_name(basis);
    let Some(kind) = kind else {
        return Ok(InterpretationResult::rejected(
            "forward_type_forbidden",
            "source fragment type is not authorable in 1.7",
        ));
    };
    let fields = match kind {
        "decision" | "implementation_decision" => copy_fields(fragment, &[("summary", "summary"), ("rationale", "rationale")]),
        "invariant" => copy_fields(fragment, &[("statement", "statement"), ("scope", "scope")]),
        "normative_proposition" => copy_fields(fragment, &[("statement", "statement"), ("normative_force", "normative_force"), ("scope", "scope")]),
        "capability" => copy_fields(fragment, &[("name", "name"), ("description", "description")]),
        "boundary" => copy_fields(fragment, &[("name", "name"), ("description", "description"), ("rationale", "rationale")]),
        "contract" => copy_fields(fragment, &[("parties", "parties"), ("protocol", "protocol"), ("guarantees", "guarantees")]),
        "gap" => copy_fields(fragment, &[("question", "question"), ("blocking", "blocking")]),
        "evidence_expectation" => copy_fields(
            fragment,
            &[
                ("kind", "evidence_kind"),
                ("description", "description"),
                ("related_entities", "related_entity_ids"),
            ],
        ),
        "system_boundary" => copy_fields(fragment, &[("name", "name"), ("description", "description"), ("external_dependencies", "external_dependencies"), ("exposed_interfaces", "exposed_interfaces")]),
        "data_flow" => {
            let mut fields = copy_fields(fragment, &[("name", "name"), ("description", "description"), ("path", "path"), ("data_type", "data_type"), ("volume", "volume"), ("latency_requirements", "latency_requirements")]);
            fields.insert(
                "path_semantics".into(),
                string("owner_local_ordered_topology_path"),
            );
            fields
        }
        "interface" => copy_fields(fragment, &[("type", "type"), ("specification", "specification")]),
        "component" => {
            let mut fields = copy_fields(fragment, &[("name", "name")]);
            if let Some(value) = ids_from_objects(fragment, "interfaces", "interfaces") {
                fields.insert(value.0, value.1);
            }
            fields
        }
        "system" => copy_fields(fragment, &[("id", "id")]),
        "extension" => return custom_entity_result(fragment),
        _ => {
            return Ok(InterpretationResult::rejected(
                "forward_type_forbidden",
                "source fragment type is not authorable in 1.7",
            ))
        }
    };
    Ok(InterpretationResult::accepted(kind, "canonical_uuidv7", fields))
}

pub(crate) fn interpret(
    fragment: &Json,
    basis: &Json,
    source_context: &InterpretationSourceContext,
) -> Result<InterpretationResult, String> {
    source_context.validate()?;
    if basis_kind(basis) == Some("absence_semantics") {
        return Ok(InterpretationResult::accepted(
            "absence-semantics",
            "none",
            BTreeMap::from([
                ("absent".into(), string("no-declaration")),
                ("present_empty".into(), string("declared-empty")),
                ("present_populated".into(), string("each-member-declared")),
            ]),
        ));
    }
    fragment_result(fragment, basis, source_context)
}

pub(crate) fn interpret_candidate_artifact(
    artifact: &candidate_source::CandidateSourceArtifact,
) -> Result<InterpretationResult, String> {
    let source = candidate_source::decode_and_validate_candidate(artifact)?;
    let mut basis = BTreeMap::new();
    basis.insert(
        "kind".into(),
        string(if artifact.artifact_kind == "authoring_document" {
            "authoring_document"
        } else {
            "authoring_fragment"
        }),
    );
    basis.insert(
        "schema".into(),
        string(format!(
            "{}#{}",
            artifact.source_schema.canonical_resource_key, artifact.source_schema.json_pointer
        )),
    );
    basis.insert(
        "source_schema".into(),
        object([
            (
                "canonical_resource_key",
                string(artifact.source_schema.canonical_resource_key.clone()),
            ),
            (
                "json_pointer",
                string(artifact.source_schema.json_pointer.clone()),
            ),
        ]),
    );
    let source_context = InterpretationSourceContext {
        canonical_source_ref: artifact.source_ref.clone(),
        source_pointer: "/".into(),
    };
    if artifact.artifact_kind == "authoring_document" {
        interpret_document(
            &source,
            &source_context,
            &artifact.source_contract,
            &format!(
                "{}#{}",
                artifact.source_schema.canonical_resource_key, artifact.source_schema.json_pointer
            ),
            &artifact.content_digest,
        )?;
    }
    interpret(&source, &Json::Object(basis), &source_context)
}

/// The complete internal result of interpreting one qualified authoring ADR.
///
/// This is intentionally not a protocol DTO. The public semantic-core
/// dispatcher does not route to this type; it exists so the Rust interpreter
/// can assemble and validate the complete normalized-model result before any
/// later host/protocol accretion is considered.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct NormalizedInterpretation {
    pub(crate) model: Json,
    pub(crate) entity_registry: Json,
    pub(crate) relationship_registry: Json,
    pub(crate) unresolved_registry: Json,
}

#[derive(Clone, Debug)]
struct DocumentFragment {
    value: Json,
    schema: String,
    pointer: String,
}

fn is_uuid_v7(value: &str) -> bool {
    let parts = value.split('-').collect::<Vec<_>>();
    parts.len() == 5
        && [8, 4, 4, 4, 12]
            .into_iter()
            .zip(parts.iter())
            .all(|(length, part)| {
                part.len() == length
                    && part
                        .bytes()
                        .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
            })
        && parts[2].starts_with('7')
        && parts[3]
            .as_bytes()
            .first()
            .is_some_and(|byte| matches!(byte, b'8' | b'9' | b'a' | b'b'))
}

fn source_object<'a>(value: &'a Json, label: &str) -> Result<&'a BTreeMap<String, Json>, String> {
    value
        .as_object()
        .ok_or_else(|| format!("{label} must be an object"))
}

fn source_text(value: &BTreeMap<String, Json>, key: &str, label: &str) -> Result<String, String> {
    value
        .get(key)
        .and_then(Json::as_str)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
        .ok_or_else(|| format!("{label}.{key} must be a non-empty string"))
}

fn source_contract_projection(source_contract: &Json) -> Json {
    let source_object = source_contract.as_object();
    let family = source_object
        .and_then(|value| value.get("family"))
        .and_then(Json::as_str)
        .unwrap_or_default();
    let version = source_object
        .and_then(|value| value.get("version"))
        .and_then(Json::as_str)
        .unwrap_or_default();
    let fingerprint = source_object
        .and_then(|value| value.get("fingerprint").or_else(|| value.get("content_digest")))
        .and_then(Json::as_str)
        .or_else(|| {
            source_object
                .and_then(|value| value.get("schemaResource").or_else(|| value.get("schema_resource")))
                .and_then(Json::as_object)
                .and_then(|value| value.get("contentDigest").or_else(|| value.get("content_digest")))
                .and_then(Json::as_str)
        })
        .unwrap_or_default();
    object([
        ("family", string(family)),
        ("version", string(version)),
        ("fingerprint", string(fingerprint)),
    ])
}

fn number(value: u64) -> Json {
    Json::Number(serde_json::Number::from(value))
}

fn normalized_digest(value: &Json) -> String {
    let mut canonical = String::new();
    semantic_contract::canonicalize_value(value, &mut canonical)
        .expect("normalized interpretation JSON must be canonicalizable");
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    let digest = hasher.finalize();
    format!(
        "sha256:{}",
        digest
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    )
}

fn add_nested_fragments(
    source: &BTreeMap<String, Json>,
    field_name: &str,
    schema_name: &str,
    fragments: &mut Vec<DocumentFragment>,
) {
    let Some(values) = source.get(field_name).and_then(Json::as_array) else {
        return;
    };
    for (index, value) in values.iter().enumerate() {
        fragments.push(DocumentFragment {
            value: value.clone(),
            schema: format!("authoring/1.7/schema/adr-common.schema#/definitions/{schema_name}"),
            pointer: format!("/{field_name}/{index}"),
        });
    }
}

fn collect_document_fragments(source: &Json) -> Result<Vec<DocumentFragment>, String> {
    let source = source_object(source, "authoring document")?;
    let mut fragments = Vec::new();
    for (field_name, schema_name) in [
        ("decisions", "decision"),
        ("capabilities", "capability"),
        ("architectural_boundaries", "boundary"),
        ("contracts", "contract"),
        ("invariants", "invariant"),
        ("gaps", "gap"),
        ("normative_propositions", "normative_proposition"),
        ("evidence_expectations", "evidence_expectation"),
        ("extension_entities", "custom_entity"),
        ("system_boundaries", "system_boundary"),
        ("data_flows", "data_flow"),
        ("implementation_decisions", "implementation_decision"),
    ] {
        add_nested_fragments(source, field_name, schema_name, &mut fragments);
    }
    if let Some(system) = source.get("system") {
        fragments.push(DocumentFragment {
            value: system.clone(),
            schema: "authoring/1.7/schema/adr-common.schema#/definitions/system".into(),
            pointer: "/system".into(),
        });
    }
    if let Some(specifications) = source
        .get("component_specifications")
        .and_then(Json::as_array)
    {
        for (index, specification) in specifications.iter().enumerate() {
            fragments.push(DocumentFragment {
                value: specification.clone(),
                schema: "authoring/1.7/schema/adr-common.schema#/definitions/component".into(),
                pointer: format!("/component_specifications/{index}"),
            });
            if let Some(interfaces) = specification.get("interfaces").and_then(Json::as_array) {
                for (interface_index, interface) in interfaces.iter().enumerate() {
                    fragments.push(DocumentFragment {
                        value: interface.clone(),
                        schema: "authoring/1.7/schema/adr-common.schema#/definitions/interface".into(),
                        pointer: format!("/component_specifications/{index}/interfaces/{interface_index}"),
                    });
                }
            }
        }
    }
    Ok(fragments)
}

fn entity_semantic_fields(
    result: &InterpretationResult,
    fragment: &BTreeMap<String, Json>,
) -> BTreeMap<String, Json> {
    let mut fields = BTreeMap::new();
    let result_fields = result.fields.as_object().cloned().unwrap_or_default();
    for key in [
        "description",
        "external_dependencies",
        "exposed_interfaces",
        "path",
        "path_semantics",
        "data_type",
        "volume",
        "latency_requirements",
        "evidence_kind",
        "related_entity_ids",
    ] {
        if let Some(value) = result_fields.get(key) {
            fields.insert(key.into(), value.clone());
        }
    }
    if result.normalized_type.as_deref() == Some("normative_proposition") {
        for key in ["statement", "normative_force", "scope"] {
            if let Some(value) = result_fields.get(key) {
                fields.insert(key.into(), value.clone());
            }
        }
        if let Some(value) = fragment.get("rationale") {
            fields.insert("rationale".into(), value.clone());
        }
    }
    fields
}

fn normalized_entity(
    fragment: &Json,
    result: &InterpretationResult,
    root: &BTreeMap<String, Json>,
    source_context: &InterpretationSourceContext,
    source_contract: &Json,
    content_digest: &str,
) -> Result<Json, String> {
    let fragment = source_object(fragment, "interpreted fragment")?;
    let id = source_text(fragment, "id", "interpreted fragment")?;
    if !is_uuid_v7(&id) {
        return Err(format!("interpreted fragment id is not UUIDv7: {id}"));
    }
    let alias_id = source_text(fragment, "alias_id", "interpreted fragment")?;
    let alias_name = source_text(fragment, "alias_name", "interpreted fragment")?;
    let normalized_type = result
        .normalized_type
        .as_deref()
        .ok_or_else(|| "accepted interpretation lacks normalized type".to_owned())?;
    let name = ["title", "name", "summary", "description", "statement"]
        .into_iter()
        .find_map(|key| fragment.get(key).and_then(Json::as_str))
        .unwrap_or(alias_name.as_str())
        .to_owned();
    let summary = ["summary", "description", "statement", "rationale", "context", "name"]
        .into_iter()
        .find_map(|key| fragment.get(key).and_then(Json::as_str))
        .unwrap_or(name.as_str())
        .to_owned();
    let created_at = fragment
        .get("created_date")
        .or_else(|| root.get("created_date"))
        .and_then(Json::as_str)
        .unwrap_or("source-basis")
        .to_owned();
    let mut values = BTreeMap::from([
        ("id".into(), string(id.clone())),
        ("alias_id".into(), string(alias_id.clone())),
        ("alias_name".into(), string(alias_name.clone())),
        ("alias_ref".into(), string(format!("{alias_id}:{alias_name}"))),
        ("entity_type".into(), string(normalized_type)),
        ("name".into(), string(name)),
        ("summary".into(), string(summary)),
        ("uri".into(), string(format!("source://{}/entities/{id}", source_context.canonical_source_ref))),
        ("created_at".into(), string(created_at)),
        (
            "canonical_source".into(),
            object([
                ("source_ref", string(source_context.canonical_source_ref.clone())),
                ("source_pointer", string(source_context.source_pointer.clone())),
                ("content_digest", string(content_digest)),
            ]),
        ),
        (
            "source_refs".into(),
            Json::Array(vec![string(source_context.canonical_source_ref.clone())]),
        ),
        (
            "metadata".into(),
            object([
                ("source_pointer", string(source_context.source_pointer.clone())),
                ("source_semantics", Json::Object(fragment.clone())),
            ]),
        ),
        ("relationships".into(), Json::Object(BTreeMap::new())),
        (
            "completeness".into(),
            object([
                ("status", string("complete")),
                ("missing_fields", Json::Array(Vec::new())),
            ]),
        ),
        (
            "provenance".into(),
            object([
                ("source_ref", string(source_context.canonical_source_ref.clone())),
                ("source_pointer", string(source_context.source_pointer.clone())),
                ("source_contract", source_contract_projection(source_contract)),
                ("classification", string("explicit")),
            ]),
        ),
    ]);
    for (key, value) in entity_semantic_fields(result, fragment) {
        values.insert(key, value);
    }
    if normalized_type == "normative_proposition" {
        let parent_id = source_text(root, "id", "authoring document")?;
        let parent_alias_id = source_text(root, "alias_id", "authoring document")?;
        let parent_alias_name = source_text(root, "alias_name", "authoring document")?;
        let fields = result.fields.as_object().cloned().unwrap_or_default();
        values.insert(
            "declaring_adr".into(),
            object([
                ("provider", string("authoring@1.7")),
                ("id", string(parent_id)),
                ("alias_id", string(parent_alias_id)),
                ("alias_name", string(parent_alias_name)),
            ]),
        );
        values.insert(
            "source_artifact".into(),
            object([
                ("source_type", string("authoring_adr")),
                ("source_ref", string(source_context.canonical_source_ref.clone())),
                ("artifact_path", string(source_context.canonical_source_ref.clone())),
                ("content_digest", string(content_digest)),
            ]),
        );
        values.insert("source_contract".into(), source_contract_projection(source_contract));
        for key in ["statement", "normative_force", "scope", "rationale"] {
            if let Some(value) = fields.get(key) {
                values.insert(key.into(), value.clone());
            }
        }
    } else {
        values.insert(
            "lifecycle_stage".into(),
            string(
                root.get("status")
                    .and_then(Json::as_str)
                    .filter(|status| matches!(*status, "proposed" | "active" | "deprecated" | "superseded"))
                    .unwrap_or("proposed"),
            ),
        );
        if normalized_type == "qualified_custom_entity" {
            let fields = result.fields.as_object().cloned().unwrap_or_default();
            values.insert(
                "extension".into(),
                object([
                    ("qualification", fields.get("qualification").cloned().unwrap_or(Json::Null)),
                    ("properties", fields.get("properties").cloned().unwrap_or(Json::Object(BTreeMap::new()))),
                    ("rationale", fragment.get("rationale").cloned().unwrap_or_else(|| string("qualified custom entity"))),
                ]),
            );
            values.insert(
                "entity_type".into(),
                fields.get("semantic_type").cloned().unwrap_or_else(|| string(normalized_type)),
            );
        }
    }
    let preimage = Json::Object(values.clone());
    values.insert("entity_fingerprint".into(), string(normalized_digest(&preimage)));
    Ok(Json::Object(values))
}

fn normalized_schema_resources() -> Result<BTreeMap<String, Json>, String> {
    [
        ("normalized-model/2.4/schema/normalized-architecture-model.schema", include_str!("../../schema/normalized-model/v2.4/normalized-architecture-model.schema.json")),
        ("normalized-model/2.4/schema/normalized-entity-registry.schema", include_str!("../../schema/normalized-model/v2.4/normalized-entity-registry.schema.json")),
        ("normalized-model/2.4/schema/normalized-entity.schema", include_str!("../../schema/normalized-model/v2.4/normalized-entity.schema.json")),
        ("normalized-model/2.4/schema/relationship-record.schema", include_str!("../../schema/normalized-model/v2.4/relationship-record.schema.json")),
        ("normalized-model/2.4/schema/relationship-registry.schema", include_str!("../../schema/normalized-model/v2.4/relationship-registry.schema.json")),
        ("normalized-model/2.4/schema/unresolved-registry.schema", include_str!("../../schema/normalized-model/v2.4/unresolved-registry.schema.json")),
    ]
    .into_iter()
    .map(|(key, value)| {
        serde_json::from_str::<Json>(value)
            .map(|value| (key.to_owned(), value))
            .map_err(|error| format!("normalized-model schema {key} is invalid JSON: {error}"))
    })
    .collect()
}

fn unresolved_from_result(result: &InterpretationResult, context: &InterpretationSourceContext) -> Json {
    let fields = result.fields.as_object().cloned().unwrap_or_default();
    let code = fields
        .get("reason_code")
        .and_then(Json::as_str)
        .unwrap_or("interpretation_unresolved");
    let missing = fields
        .get("missing_keys")
        .and_then(Json::as_array)
        .map(|keys| keys.iter().filter_map(Json::as_str).collect::<Vec<_>>().join(", "))
        .unwrap_or_else(|| "semantic source could not be resolved".into());
    object([
        ("code", string(code)),
        ("message", string(format!("unresolved interpretation: {missing}"))),
        ("source_pointer", string(context.source_pointer.clone())),
        ("resolution", string("unresolved")),
        ("details", Json::Object(fields)),
    ])
}

/// Interpret a complete, already-qualified authoring 1.7 document into the
/// canonical normalized-model 2.4 result. This function is crate-internal;
/// it is deliberately not a semantic-core protocol operation.
pub(crate) fn interpret_document(
    source: &Json,
    source_context: &InterpretationSourceContext,
    source_contract: &Json,
    source_schema: &str,
    content_digest: &str,
) -> Result<NormalizedInterpretation, String> {
    source_context.validate()?;
    let root = source_object(source, "authoring document")?;
    let root_basis = object([
        ("kind", string("authoring_document")),
        ("schema", string(source_schema)),
    ]);
    let root_result = interpret(source, &root_basis, source_context)?;
    if root_result.disposition != InterpretationDisposition::Accepted {
        return Err(format!("authoring document was not accepted: {:?}", root_result.to_json()));
    }
    let mut entities = vec![normalized_entity(
        source,
        &root_result,
        root,
        source_context,
        source_contract,
        content_digest,
    )?];
    let mut entity_classifications = BTreeMap::new();
    entity_classifications.insert(source_text(root, "id", "authoring document")?, "canonical".to_owned());
    for fragment in collect_document_fragments(source)? {
        // Physical-system authoring embeds the owning system descriptor under
        // `/system` and intentionally reuses the document identity.  It is a
        // structural projection of the root ADR, not a second normalized
        // entity; preserve one canonical entity per authored identity.
        if fragment.pointer == "/system"
            && fragment.value.get("id") == root.get("id")
        {
            continue;
        }
        let basis = object([
            ("kind", string("authoring_fragment")),
            ("schema", string(fragment.schema.clone())),
        ]);
        let context = InterpretationSourceContext {
            canonical_source_ref: source_context.canonical_source_ref.clone(),
            source_pointer: fragment.pointer.clone(),
        };
        let result = interpret(&fragment.value, &basis, &context)?;
        match result.disposition {
            InterpretationDisposition::Accepted => {
                let entity = normalized_entity(
                    &fragment.value,
                    &result,
                    root,
                    &context,
                    source_contract,
                    content_digest,
                )?;
                let id = entity
                    .get("id")
                    .and_then(Json::as_str)
                    .ok_or_else(|| "normalized entity lacks id".to_owned())?;
                if entity_classifications.insert(
                    id.to_owned(),
                    if result.normalized_type.as_deref() == Some("qualified_custom_entity") {
                        "qualified_custom".into()
                    } else {
                        "canonical".into()
                    },
                ).is_some() {
                    return Err(format!("duplicate canonical entity identity: {id}"));
                }
                entities.push(entity);
            }
            InterpretationDisposition::Rejected => {
                return Err(format!("authoring fragment was rejected: {:?}", result.to_json()));
            }
            InterpretationDisposition::Unresolved | InterpretationDisposition::HistoricalCompatibility => {
                return Err(format!("authoring fragment did not produce canonical semantics: {:?}", result.to_json()));
            }
        }
    }
    let mut relationships = Vec::new();
    let mut unresolved = Vec::new();
    if let Some(topology) = root.get("component_topology").and_then(Json::as_object) {
        let components = topology.get("components").cloned().unwrap_or(Json::Array(Vec::new()));
        if let Some(topology_relationships) = topology.get("relationships").and_then(Json::as_array) {
            for (index, relationship) in topology_relationships.iter().enumerate() {
                let basis = object([
                    ("kind", string("topology_resolution")),
                    ("components", components.clone()),
                ]);
                let context = InterpretationSourceContext {
                    canonical_source_ref: source_context.canonical_source_ref.clone(),
                    source_pointer: format!("/component_topology/relationships/{index}"),
                };
                let result = interpret(relationship, &basis, &context)?;
                match result.disposition {
                    InterpretationDisposition::Accepted => {
                        relationships.push(result.normalized_record.ok_or_else(|| "accepted topology relationship lacks normalized record".to_owned())?);
                    }
                    InterpretationDisposition::Unresolved => unresolved.push(unresolved_from_result(&result, &context)),
                    InterpretationDisposition::Rejected => return Err(format!("topology relationship was rejected: {:?}", result.to_json())),
                    InterpretationDisposition::HistoricalCompatibility => return Err("historical topology compatibility cannot enter a 2.4 normalized result".into()),
                }
            }
        }
        if let Some(components) = topology.get("components").and_then(Json::as_array) {
            let system = root
                .get("system")
                .and_then(Json::as_object)
                .ok_or_else(|| "physical-system document lacks system".to_owned())?;
            let system_id = source_text(system, "id", "system")?;
            for (index, component) in components.iter().enumerate() {
                let basis = object([
                    ("kind", string("composition_context")),
                    ("system_id", string(system_id.clone())),
                    ("components", Json::Array(vec![component.clone()])),
                ]);
                let context = InterpretationSourceContext {
                    canonical_source_ref: source_context.canonical_source_ref.clone(),
                    source_pointer: format!("/component_topology/components/{index}"),
                };
                let result = interpret(&Json::Object(BTreeMap::new()), &basis, &context)?;
                if result.disposition == InterpretationDisposition::Accepted {
                    relationships.push(result.normalized_record.ok_or_else(|| "composition relationship lacks normalized record".to_owned())?);
                } else {
                    return Err(format!("composition relationship was not accepted: {:?}", result.to_json()));
                }
            }
        }
    }
    if let Some(extension_relationships) = root.get("extension_relationships").and_then(Json::as_array) {
        for (index, relationship) in extension_relationships.iter().enumerate() {
            let endpoint_entities = relationship
                .as_object()
                .into_iter()
                .flat_map(|object| ["from_entity_id", "to_entity_id"].into_iter().filter_map(move |key| object.get(key).and_then(Json::as_str)))
                .map(|id| object([
                    ("id", string(id)),
                    ("classification", string(entity_classifications.get(id).map(String::as_str).unwrap_or("unknown"))),
                ]))
                .collect::<Vec<_>>();
            let basis = object([
                ("kind", string("endpoint_classification")),
                ("endpoint_entities", Json::Array(endpoint_entities)),
            ]);
            let context = InterpretationSourceContext {
                canonical_source_ref: source_context.canonical_source_ref.clone(),
                source_pointer: format!("/extension_relationships/{index}"),
            };
            let result = interpret(relationship, &basis, &context)?;
            if result.disposition != InterpretationDisposition::Accepted {
                return Err(format!("custom relationship was not accepted: {:?}", result.to_json()));
            }
            relationships.push(result.normalized_record.ok_or_else(|| "custom relationship lacks normalized record".to_owned())?);
        }
    }
    entities.sort_by_key(|entity| entity.get("id").and_then(Json::as_str).unwrap_or_default().to_owned());
    relationships.sort_by_key(|relationship| (
        relationship.get("record_kind").and_then(Json::as_str).unwrap_or_default().to_owned(),
        relationship.get("id").or_else(|| relationship.get("assertion_id")).and_then(Json::as_str).unwrap_or_default().to_owned(),
    ));
    unresolved.sort_by_key(|item| (
        item.get("code").and_then(Json::as_str).unwrap_or_default().to_owned(),
        item.get("source_pointer").and_then(Json::as_str).unwrap_or_default().to_owned(),
    ));
    let entity_registry = object([
        ("schema_version", string("2.4")),
        ("type", string("normalized_entity_registry")),
        ("entities", Json::Array(entities.clone())),
    ]);
    let relationship_registry = object([
        ("schema_version", string("2.4")),
        ("type", string("relationship_registry")),
        ("relationships", Json::Array(relationships.clone())),
    ]);
    let unresolved_registry = object([
        ("schema_version", string("2.4")),
        ("type", string("unresolved_registry")),
        ("unresolved", Json::Array(unresolved.clone())),
    ]);
    let model_without_fingerprint = object([
        ("schema_version", string("2.4")),
        ("type", string("normalized_architecture_model")),
        ("mode", string("normalized")),
        ("scope_root", string(source_context.canonical_source_ref.clone())),
        ("architecture_namespace", Json::Null),
        ("entities", Json::Array(entities)),
        ("relationships", Json::Array(relationships)),
        ("unresolved", Json::Array(unresolved)),
        (
            "validation_summary",
            object([
                ("entity_count", number(entity_registry.get("entities").and_then(Json::as_array).map_or(0, Vec::len) as u64)),
                ("relationship_count", number(relationship_registry.get("relationships").and_then(Json::as_array).map_or(0, Vec::len) as u64)),
                ("unresolved_count", number(unresolved_registry.get("unresolved").and_then(Json::as_array).map_or(0, Vec::len) as u64)),
            ]),
        ),
        (
            "source_coverage",
            object([
                ("source_contract", source_contract.clone()),
                ("source_schema", string(source_schema)),
                ("content_digest", string(content_digest)),
            ]),
        ),
    ]);
    let mut model_values = model_without_fingerprint
        .as_object()
        .cloned()
        .ok_or_else(|| "normalized model assembly failed".to_owned())?;
    model_values.insert("fingerprint".into(), string(normalized_digest(&model_without_fingerprint)));
    let model = Json::Object(model_values);
    let resources = normalized_schema_resources()?;
    for (key, value) in [
        ("normalized-model/2.4/schema/normalized-architecture-model.schema", &model),
        ("normalized-model/2.4/schema/normalized-entity-registry.schema", &entity_registry),
        ("normalized-model/2.4/schema/relationship-registry.schema", &relationship_registry),
        ("normalized-model/2.4/schema/unresolved-registry.schema", &unresolved_registry),
    ] {
        schema_validation::validate(&resources, key, value)
            .map_err(|error| format!("{key} validation failed at {}: {}", error.path, error.message))?;
    }
    Ok(NormalizedInterpretation {
        model,
        entity_registry,
        relationship_registry,
        unresolved_registry,
    })
}

#[cfg(test)]
mod tests {
    use crate::schema_validation;
    use super::*;
    use std::collections::BTreeMap;

    fn parsed(value: &str) -> Json {
        serde_json::from_str(value).expect("fixture JSON is valid")
    }

    fn base64_decode(input: &str) -> Vec<u8> {
        fn value(byte: u8) -> u8 {
            match byte {
                b'A'..=b'Z' => byte - b'A',
                b'a'..=b'z' => byte - b'a' + 26,
                b'0'..=b'9' => byte - b'0' + 52,
                b'+' => 62,
                b'/' => 63,
                _ => panic!("invalid base64 byte"),
            }
        }
        let bytes = input.as_bytes();
        assert_eq!(bytes.len() % 4, 0);
        let mut result = Vec::new();
        for chunk in bytes.chunks_exact(4) {
            let a = value(chunk[0]) as u32;
            let b = value(chunk[1]) as u32;
            let c = if chunk[2] == b'=' { 0 } else { value(chunk[2]) as u32 };
            let d = if chunk[3] == b'=' { 0 } else { value(chunk[3]) as u32 };
            result.push(((a << 2) | (b >> 4)) as u8);
            if chunk[2] != b'=' {
                result.push((((b & 0xf) << 4) | (c >> 2)) as u8);
            }
            if chunk[3] != b'=' {
                result.push((((c & 0x3) << 6) | d) as u8);
            }
        }
        result
    }

    fn object<'a>(value: &'a Json) -> &'a BTreeMap<String, Json> {
        value.as_object().expect("object")
    }

    fn value<'a>(value: &'a Json, key: &str) -> &'a Json {
        object(value).get(key).unwrap_or_else(|| panic!("missing {key}"))
    }

    fn map_value<'a>(value: &'a BTreeMap<String, Json>, key: &str) -> &'a Json {
        value.get(key).unwrap_or_else(|| panic!("missing {key}"))
    }

    fn assert_subset(expected: &Json, actual: &Json, path: &str) {
        match (expected, actual) {
            (Json::Object(expected), Json::Object(actual)) => {
                for (key, expected_value) in expected {
                    let actual_value = actual
                        .get(key)
                        .unwrap_or_else(|| panic!("missing {path}.{key}: {actual:?}"));
                    assert_subset(expected_value, actual_value, &format!("{path}.{key}"));
                }
            }
            (Json::Array(expected), Json::Array(actual)) => {
                assert_eq!(expected, actual, "array mismatch at {path}");
            }
            _ => assert_eq!(expected, actual, "value mismatch at {path}"),
        }
    }

    fn normalized_record<'a>(result: &'a InterpretationResult) -> &'a BTreeMap<String, Json> {
        result
            .normalized_record
            .as_ref()
            .and_then(Json::as_object)
            .expect("schema-backed normalized record")
    }

    fn assert_endpoint_semantics(
        expected: &str,
        result: &InterpretationResult,
        basis: &Json,
        source_pointer: &str,
    ) {
        if result.normalized_type.as_deref() == Some("compatibility") {
            let record = normalized_record(result);
            assert_eq!(record.get("record_kind").and_then(Json::as_str), Some("compatibility"));
            assert!(record.contains_key("assertion_id"));
            assert_eq!(
                record.get("from_entity_id").and_then(Json::as_str),
                result.fields.as_object().and_then(|fields| fields.get("from_entity_id")).and_then(Json::as_str)
            );
            assert_eq!(
                record.get("to_entity_id").and_then(Json::as_str),
                result.fields.as_object().and_then(|fields| fields.get("to_entity_id")).and_then(Json::as_str)
            );
            if expected.contains("topology_key") || expected.contains("component_ref") {
                let provenance = record
                    .get("source_provenance")
                    .and_then(Json::as_object)
                    .expect("topology source provenance");
                assert_eq!(
                    provenance.get("source_pointer").and_then(Json::as_str),
                    Some(source_pointer)
                );
                assert!(provenance.get("topology_key_endpoints").is_some());
            }
            return;
        }
        if source_pointer == "/" {
            assert_eq!(
                expected,
                "UUIDv7 references classified by explicit endpoint basis",
                "root-level custom endpoint assertion"
            );
            assert!(field(basis, "endpoint_entities").is_some());
            return;
        }
        assert_eq!(
            qualified_endpoint_semantics(basis).as_deref(),
            Some(expected),
            "custom endpoint classification assertion"
        );
    }

    fn assert_normalized_relationship_schema(result: &InterpretationResult) {
        let Some(record) = &result.normalized_record else {
            return;
        };
        let resources = BTreeMap::from([(
            "relationship-record.schema.json".to_owned(),
            parsed(include_str!(
                "../../schema/normalized-model/v2.4/relationship-record.schema.json"
            )),
        )]);
        schema_validation::validate(&resources, "relationship-record.schema.json", record)
            .unwrap_or_else(|error| panic!("normalized relationship schema failed: {error:?}"));
    }

    fn assert_vector(
        case: &Json,
        result: &InterpretationResult,
        source_context: &InterpretationSourceContext,
    ) {
        let case_id = value(case, "id").as_str().expect("case id");
        let input = object(value(case, "input"));
        let expected = object(value(case, "expected"));
        let actual_json = result.to_json();
        let actual = object(&actual_json);

        assert_eq!(
            actual.get("disposition"),
            expected.get("disposition"),
            "{case_id} disposition"
        );
        if let Some(normalized_type) = expected.get("normalized_type") {
            assert_eq!(actual.get("normalized_type"), Some(normalized_type), "{case_id} type");
        }
        if let Some(identity) = expected.get("identity") {
            assert_eq!(actual.get("identity"), Some(identity), "{case_id} identity");
        }

        if expected.get("disposition").and_then(Json::as_str) == Some("rejected") {
            assert_eq!(actual.get("reason_code"), expected.get("reason_code"), "{case_id} reason");
            assert_eq!(actual.get("reason"), expected.get("reason"), "{case_id} rejection");
            return;
        }

        assert_normalized_relationship_schema(result);
        if let Some(record) = result.normalized_record.as_ref().and_then(Json::as_object) {
            assert_eq!(
                record.get("canonical_source_ref").and_then(Json::as_str),
                Some(source_context.canonical_source_ref.as_str()),
                "{case_id} source identity",
            );
            if let Some(source_pointer) = record.get("source_pointer").and_then(Json::as_str) {
                assert_eq!(
                    source_pointer,
                    source_context.source_pointer,
                    "{case_id} semantic source pointer",
                );
            }
            if let Some(provenance) = record.get("source_provenance").and_then(Json::as_object) {
                assert_eq!(
                    provenance.get("source_pointer").and_then(Json::as_str),
                    Some(source_context.source_pointer.as_str()),
                    "{case_id} provenance source pointer",
                );
            }
        }
        let actual_fields = object(value(&actual_json, "fields"));
        let expected_fields = expected.get("fields").map(object).unwrap_or_else(|| panic!("{case_id} fields"));
        for (key, expected_value) in expected_fields {
            match key.as_str() {
                "record_kind" => assert_eq!(normalized_record(result).get("record_kind"), Some(expected_value), "{case_id} record kind"),
                "canonical_relationship_uuid" => {
                    assert_eq!(expected_value.as_bool(), Some(false), "{case_id} canonical identity assertion");
                    assert!(!normalized_record(result).contains_key("id"), "{case_id} compatibility gained canonical id");
                }
                "assertion_identity" => {
                    assert_eq!(expected_value.as_str(), Some("noncanonical compatibility assertion"), "{case_id} assertion identity");
                    assert_eq!(result.identity.as_deref(), Some("noncanonical"));
                    assert!(normalized_record(result).contains_key("assertion_id"));
                }
                "identity_is_not_qualification" => {
                    assert_eq!(expected_value.as_bool(), Some(true), "{case_id} qualification identity assertion");
                    assert_eq!(result.identity.as_deref(), Some("canonical_uuidv7"));
                    assert!(normalized_record(result).contains_key("id"));
                }
                "authorable" => {
                    assert_eq!(expected_value.as_bool(), Some(false), "{case_id} derived-only assertion");
                    let mode = actual
                        .get("relationship_mode")
                        .or_else(|| actual_fields.get("relationship_mode"))
                        .and_then(Json::as_str);
                    assert_eq!(mode, Some("composition_derived"));
                    assert_eq!(normalized_record(result).get("provenance_classification").and_then(Json::as_str), Some("derived"));
                }
                "forbidden_fields" => {
                    for forbidden in expected_value.as_array().expect("forbidden fields") {
                        let name = forbidden.as_str().expect("forbidden field name");
                        assert!(!actual_fields.contains_key(name), "{case_id} preserved forbidden field {name}");
                        if let Some(record) = result.normalized_record.as_ref().and_then(Json::as_object) {
                            assert!(!record.contains_key(name), "{case_id} normalized forbidden field {name}");
                        }
                    }
                }
                "endpoint_semantics" => assert_endpoint_semantics(
                    expected_value.as_str().expect("endpoint semantics"),
                    result,
                    map_value(input, "basis"),
                    map_value(input, "source_pointer").as_str().expect("source pointer"),
                ),
                _ => {
                    let actual_value = actual_fields
                        .get(key)
                        .unwrap_or_else(|| panic!("missing {case_id}.fields.{key}: {actual_fields:?}"));
                    assert_subset(expected_value, actual_value, &format!("{case_id}.fields.{key}"));
                }
            }
        }

        if let Some(relationship_mode) = expected.get("relationship_mode") {
            assert_eq!(actual.get("relationship_mode"), Some(relationship_mode), "{case_id} relationship mode");
        }
        if let Some(custom_qualification) = expected.get("custom_qualification") {
            assert_eq!(actual.get("custom_qualification"), Some(custom_qualification), "{case_id} qualification");
        }
        if let Some(endpoint_semantics) = expected.get("endpoint_semantics") {
            assert_endpoint_semantics(
                endpoint_semantics.as_str().expect("endpoint semantics"),
                result,
                map_value(input, "basis"),
                map_value(input, "source_pointer").as_str().expect("source pointer"),
            );
        }
    }

    fn conformance_source_context(case_id: &str, source_pointer: &str) -> InterpretationSourceContext {
        InterpretationSourceContext {
            canonical_source_ref: format!("test://architecture-interpretation/1.1/{case_id}"),
            source_pointer: source_pointer.to_owned(),
        }
    }

    #[test]
    fn i01_to_i38_execute_as_semantic_assertion_vectors() {
        let root = parsed(include_str!(
            "../../contracts/architecture-interpretation/v1.1/resources/conformance.json"
        ));
        let cases = value(&root, "cases").as_array().expect("conformance cases");
        assert_eq!(cases.len(), 38);
        for case in cases {
            let input = object(value(case, "input"));
            let case_id = value(case, "id").as_str().expect("case id");
            let source_context = conformance_source_context(
                case_id,
                map_value(input, "source_pointer").as_str().expect("source pointer"),
            );
            let result = interpret(
                map_value(input, "fragment"),
                map_value(input, "basis"),
                &source_context,
            )
            .unwrap_or_else(|error| panic!("{case_id} failed: {error}"));
            assert_vector(case, &result, &source_context);
        }
    }

    #[test]
    fn duplicate_topology_vectors_converge_to_one_result() {
        let root = parsed(include_str!(
            "../../contracts/architecture-interpretation/v1.1/resources/conformance.json"
        ));
        let cases = value(&root, "cases").as_array().expect("conformance cases");
        let selected = ["I12", "I18", "I37"]
            .iter()
            .map(|id| cases.iter().find(|case| value(case, "id").as_str() == Some(id)).expect("vector"))
            .collect::<Vec<_>>();
        let first_input = object(value(selected[0], "input"));
        for case in selected.iter().skip(1) {
            let input = object(value(case, "input"));
            assert_eq!(input.get("fragment"), first_input.get("fragment"));
            assert_eq!(input.get("basis"), first_input.get("basis"));
            assert_eq!(input.get("source_pointer"), first_input.get("source_pointer"));
        }
        let source_context = InterpretationSourceContext {
            canonical_source_ref: "test://architecture-interpretation/1.1/duplicate-topology".into(),
            source_pointer: map_value(first_input, "source_pointer")
                .as_str()
                .expect("source pointer")
                .into(),
        };
        let results = selected
            .iter()
            .map(|case| {
                let input = object(value(case, "input"));
                interpret(
                    map_value(input, "fragment"),
                    map_value(input, "basis"),
                    &source_context,
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        assert_eq!(results[0], results[1]);
        assert_eq!(results[1], results[2]);
    }

    #[test]
    fn candidate_artifacts_decode_validate_and_enter_interpretation() {
        let root = parsed(include_str!(
            "../../contracts/authoring-construction/v1.0/resources/conformance.json"
        ));
        let mut count = 0;
        for case in value(&root, "cases").as_array().unwrap() {
            let artifacts = case
                .as_object()
                .and_then(|case| case.get("expected"))
                .and_then(Json::as_object)
                .and_then(|expected| expected.get("result"))
                .and_then(Json::as_object)
                .and_then(|result| result.get("candidate_artifacts"))
                .and_then(Json::as_array)
                .map_or(&[][..], |values| values.as_slice());
            for value in artifacts {
                let artifact_object = object(value);
                let schema = object(artifact_object.get("source_schema").unwrap());
                let artifact = candidate_source::CandidateSourceArtifact {
                    request_key: artifact_object.get("request_key").unwrap().as_str().unwrap().into(),
                    source_ref: artifact_object.get("source_ref").unwrap().as_str().unwrap().into(),
                    artifact_kind: artifact_object.get("artifact_kind").unwrap().as_str().unwrap().into(),
                    source_schema: candidate_source::CandidateSourceSelector {
                        canonical_resource_key: schema.get("canonical_resource_key").unwrap().as_str().unwrap().into(),
                        json_pointer: schema.get("json_pointer").unwrap().as_str().unwrap().into(),
                    },
                    serialization_profile: artifact_object.get("serialization_profile").unwrap().as_str().unwrap().into(),
                    content_digest: artifact_object.get("content_digest").unwrap().as_str().unwrap().into(),
                    bytes: base64_decode(artifact_object.get("bytes").unwrap().as_str().unwrap()),
                    source_contract: artifact_object.get("source_contract").unwrap().clone(),
                };
                let result = interpret_candidate_artifact(&artifact)
                    .unwrap_or_else(|error| panic!("{} failed: {error}", artifact.source_ref));
                if let Some(record) = result.normalized_record.as_ref().and_then(Json::as_object) {
                    assert_eq!(
                        record.get("canonical_source_ref").and_then(Json::as_str),
                        Some(artifact.source_ref.as_str()),
                    );
                    assert_eq!(record.get("source_pointer").and_then(Json::as_str), Some("/"));
                }
                count += 1;
            }
        }
        assert_eq!(count, 32);
    }

    #[test]
    fn complete_normalized_result_is_deterministic_and_schema_valid() {
        let root = parsed(include_str!(
            "../../contracts/architecture-interpretation/v1.1/resources/conformance.json"
        ));
        let case = value(&root, "cases")
            .as_array()
            .expect("conformance cases")
            .iter()
            .find(|case| value(case, "id").as_str() == Some("I01"))
            .expect("I01");
        let input = object(value(case, "input"));
        let source = map_value(&input, "fragment");
        let source_context = InterpretationSourceContext {
            canonical_source_ref: "test://architecture-interpretation/1.1/I01".into(),
            source_pointer: "/".into(),
        };
        let source_contract = parsed(
            r#"{
                "family": "authoring",
                "version": "1.7",
                "schemaResource": {
                    "canonicalResourceKey": "authoring/1.7/schema/adr-logical.schema",
                    "contentDigest": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
                }
            }"#,
        );
        let first = interpret_document(
            source,
            &source_context,
            &source_contract,
            "authoring/1.7/schema/adr-logical.schema",
            "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        )
        .expect("complete I01 interpretation");
        let second = interpret_document(
            source,
            &source_context,
            &source_contract,
            "authoring/1.7/schema/adr-logical.schema",
            "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        )
        .expect("repeat complete I01 interpretation");
        assert_eq!(first, second);
        assert_eq!(
            first.model.get("schema_version").and_then(Json::as_str),
            Some("2.4")
        );
        assert_eq!(
            first.model.get("type").and_then(Json::as_str),
            Some("normalized_architecture_model")
        );
        assert_eq!(
            first.model
                .get("entities")
                .and_then(Json::as_array)
                .map(Vec::len),
            Some(2)
        );
        assert!(
            first
                .model
                .get("fingerprint")
                .and_then(Json::as_str)
                .is_some_and(|value| value.starts_with("sha256:"))
        );
    }

    #[test]
    fn ordinary_fragment_alias_does_not_supply_semantic_schema_authority() {
        let fragment = parsed(
            r#"{
                "alias_id": "DEC-0001",
                "summary": "alias is not schema authority"
            }"#,
        );
        let basis = parsed(r#"{"kind":"authoring_fragment"}"#);
        let source_context = InterpretationSourceContext {
            canonical_source_ref: "test://architecture-interpretation/1.1/alias-negative".into(),
            source_pointer: "/".into(),
        };
        let result = interpret(&fragment, &basis, &source_context).expect("interpretation result");
        assert_eq!(result.disposition, InterpretationDisposition::Rejected);
        assert_eq!(result.reason_code.as_deref(), Some("forward_type_forbidden"));
    }

    #[test]
    fn exact_schema_authority_wins_over_alias_spelling() {
        let fragment = parsed(
            r#"{
                "alias_id": "INV-0001",
                "summary": "schema selects decision"
            }"#,
        );
        let basis = parsed(
            r#"{
                "kind":"authoring_fragment",
                "schema":"adr-common.schema.json#/definitions/decision"
            }"#,
        );
        let source_context = InterpretationSourceContext {
            canonical_source_ref: "test://architecture-interpretation/1.1/schema-authority".into(),
            source_pointer: "/".into(),
        };
        let result = interpret(&fragment, &basis, &source_context).expect("interpretation result");
        assert_eq!(result.disposition, InterpretationDisposition::Accepted);
        assert_eq!(result.normalized_type.as_deref(), Some("decision"));
    }

    #[test]
    fn source_context_is_required_and_source_sensitive() {
        let fragment = parsed(
            r#"{
                "type":"calls",
                "from_key":"TOPO-A",
                "to_key":"TOPO-B"
            }"#,
        );
        let basis = parsed(
            r#"{
                "kind":"topology_resolution",
                "components":[
                    {"topology_key":"TOPO-A","component_ref":"019109a0-b1c2-7def-8a00-112233445566"},
                    {"topology_key":"TOPO-B","component_ref":"019109a0-b1c2-7def-8a00-112233445567"}
                ]
            }"#,
        );
        let missing_ref = InterpretationSourceContext {
            canonical_source_ref: String::new(),
            source_pointer: "/relationships/0".into(),
        };
        assert!(interpret(&fragment, &basis, &missing_ref).is_err());

        let result = |source_ref: &str, source_pointer: &str| {
            interpret(
                &fragment,
                &basis,
                &InterpretationSourceContext {
                    canonical_source_ref: source_ref.into(),
                    source_pointer: source_pointer.into(),
                },
            )
            .expect("topology interpretation")
        };
        let first = result("test://source-a", "/relationships/0");
        let same = result("test://source-a", "/relationships/0");
        let different_ref = result("test://source-b", "/relationships/0");
        let different_pointer = result("test://source-a", "/relationships/1");
        assert_eq!(first, same);
        assert_ne!(
            normalized_record(&first).get("assertion_id"),
            normalized_record(&different_ref).get("assertion_id")
        );
        assert_ne!(
            normalized_record(&first).get("assertion_id"),
            normalized_record(&different_pointer).get("assertion_id")
        );
    }
}
