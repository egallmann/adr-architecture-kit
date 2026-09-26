//! Internal Architecture Interpretation 1.1 semantic authority.
//!
//! This module is the forward interpreter for authoring 1.7 semantic source.
//! It intentionally does not construct requests, select source roots, mint
//! identity, persist anything, or participate in semantic-core protocol 1.2.
//! The contract resources remain the authority; this Rust code is only their
//! deterministic execution mechanism.

use std::collections::BTreeMap;

use sha2::{Digest, Sha256};

use super::{candidate_source, semantic_contract, Json};

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

fn stable_digest(parts: &[&str]) -> String {
    let mut hasher = Sha256::new();
    for part in parts {
        hasher.update(part.as_bytes());
        hasher.update([0]);
    }
    hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn compatibility_record(
    relationship_type: &str,
    from_entity_id: &str,
    to_entity_id: &str,
    source_pointer: &str,
    from_key: Option<&str>,
    to_key: Option<&str>,
    provenance_classification: &str,
) -> Json {
    let digest = stable_digest(&[
        relationship_type,
        from_entity_id,
        to_entity_id,
        source_pointer,
        from_key.unwrap_or(""),
        to_key.unwrap_or(""),
    ]);
    let mut source_provenance = BTreeMap::from([
        ("source_contract".into(), string("authoring@1.7")),
        ("source_pointer".into(), string(source_pointer)),
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
        ("relationship_id".into(), string(format!("compatibility:{digest}"))),
        ("assertion_id".into(), string(format!("asrt-{digest}"))),
        ("relationship_type".into(), string(relationship_type)),
        ("from_entity_id".into(), string(from_entity_id)),
        ("to_entity_id".into(), string(to_entity_id)),
        ("provenance_classification".into(), string(provenance_classification)),
        ("evidence".into(), Json::Array(Vec::new())),
        (
            "canonical_source_ref".into(),
            string(format!("authoring@1.7#{source_pointer}")),
        ),
        ("source_provenance".into(), Json::Object(source_provenance)),
    ]))
}

fn canonical_relationship_record(
    fragment: &Json,
    qualification: &Json,
    source_pointer: &str,
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
            string(format!("authoring@1.7#{source_pointer}")),
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
    source_pointer: &str,
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
                string(source_pointer),
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
        source_pointer,
        Some(&from_key),
        Some(&to_key),
        "explicit",
    )))
}

fn composition_relationship(
    fragment: &Json,
    basis: &Json,
    source_pointer: &str,
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
        source_pointer,
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
    source_pointer: &str,
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
        canonical_relationship_record(fragment, &record_qualification, source_pointer)
    else {
        return Ok(InterpretationResult::rejected(
            "normalized_relationship_incomplete",
            "custom relationship lacks the required normalized-model fields",
        ));
    };
    Ok(result.with_normalized_record(normalized_record))
}

fn fragment_result(fragment: &Json, basis: &Json, source_pointer: &str) -> Result<InterpretationResult, String> {
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
        return topology_relationship(fragment, basis, source_pointer);
    }
    if basis_kind(basis) == Some("composition_context") {
        return composition_relationship(fragment, basis, source_pointer);
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
        return custom_relationship_result(fragment, basis, source_pointer);
    }
    if field(fragment, "entity_type").is_some() {
        return custom_entity_result(fragment);
    }
    let kind = schema_name(basis).or_else(|| {
        field_text(fragment, "alias_id").as_deref().and_then(|alias| {
            alias.split('-').next().map(|value| match value {
                "DEC" => "decision",
                "INV" => "invariant",
                "NP" => "normative_proposition",
                "CAP" => "capability",
                "BOUND" => "boundary",
                "GAP" => "gap",
                "FLOW" => "data_flow",
                "COMP" => "component",
                "IFACE" => "interface",
                "IMPL" => "implementation_decision",
                "EVID" => "evidence_expectation",
                "SYSBOUND" => "system_boundary",
                _ => "",
            })
        })
    });
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
    source_pointer: &str,
) -> Result<InterpretationResult, String> {
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
    fragment_result(fragment, basis, source_pointer)
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
    interpret(&source, &Json::Object(basis), &artifact.source_schema.json_pointer)
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

    fn assert_vector(case: &Json, result: &InterpretationResult) {
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

    #[test]
    fn i01_to_i38_execute_as_semantic_assertion_vectors() {
        let root = parsed(include_str!(
            "../../contracts/architecture-interpretation/v1.1/resources/conformance.json"
        ));
        let cases = value(&root, "cases").as_array().expect("conformance cases");
        assert_eq!(cases.len(), 38);
        for case in cases {
            let input = object(value(case, "input"));
            let result = interpret(
                map_value(input, "fragment"),
                map_value(input, "basis"),
                map_value(input, "source_pointer").as_str().expect("source pointer"),
            )
            .unwrap_or_else(|error| panic!("{} failed: {error}", value(case, "id").as_str().unwrap()));
            assert_vector(case, &result);
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
        let results = selected
            .iter()
            .map(|case| {
                let input = object(value(case, "input"));
                interpret(
                map_value(input, "fragment"),
                map_value(input, "basis"),
                map_value(input, "source_pointer").as_str().unwrap(),
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
                interpret_candidate_artifact(&artifact)
                    .unwrap_or_else(|error| panic!("{} failed: {error}", artifact.source_ref));
                count += 1;
            }
        }
        assert_eq!(count, 32);
    }
}
