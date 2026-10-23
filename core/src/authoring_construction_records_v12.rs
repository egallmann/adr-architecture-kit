//! Complete ACC-shaped records, independently replayed from private insertion
//! and artifact/root/dependency evidence. No source sealing or transport API.
use super::dependencies::{self, DependencyResult, DependencyStatus};
use super::insertion::{self, InsertionResult};
use super::sources::AccountingResult;
use super::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum RecordStatus {
    Rejected,
    Unavailable,
    Unresolved,
    RecordsQualified,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct RecordResult {
    pub status: RecordStatus,
    /// Exact published composition_record objects, never a composed basis.
    pub records: Vec<Json>,
    pub diagnostics: Vec<Diagnostic>,
    pub outstanding_dependencies: BTreeSet<&'static str>,
}

impl RecordResult {
    fn issue(&mut self, status: Status, key: &str, message: &str) {
        self.diagnostics.push(Diagnostic {
            status,
            code: if status == Status::Unavailable {
                "authoring_construction.composition.evidence_unavailable"
            } else {
                "authoring_construction.composition.containment_accounting"
            }
            .into(),
            semantic_identity: None,
            field_or_relation_key: key.into(),
            payload: string(message),
        });
    }
    fn finish(mut self) -> Self {
        self.diagnostics.sort_by_cached_key(|d| {
            (
                d.status,
                d.semantic_identity.clone(),
                d.field_or_relation_key.clone(),
                d.code.clone(),
                digest(&d.payload),
            )
        });
        self.diagnostics.dedup();
        self.status = match self.diagnostics.iter().map(|d| d.status).min() {
            Some(Status::Rejected) => RecordStatus::Rejected,
            Some(Status::Unavailable) => RecordStatus::Unavailable,
            Some(Status::Unresolved) => RecordStatus::Unresolved,
            _ => self.status,
        };
        if self.status != RecordStatus::RecordsQualified {
            self.records.clear();
        } else {
            self.outstanding_dependencies
                .remove("complete_composition_evidence");
        }
        self
    }
}

pub(crate) fn assemble(
    definition: &Json,
    resources: &[Json],
    insertion: &InsertionResult,
    roots: &AccountingResult,
    dependencies: &DependencyResult,
) -> RecordResult {
    assemble_for(
        Profile::Acc12,
        definition,
        resources,
        insertion,
        roots,
        dependencies,
    )
}

pub(crate) fn assemble_for(
    profile: Profile,
    definition: &Json,
    resources: &[Json],
    insertion: &InsertionResult,
    roots: &AccountingResult,
    dependencies: &DependencyResult,
) -> RecordResult {
    verify(
        profile,
        definition,
        resources,
        insertion,
        roots,
        dependencies,
        None,
    )
}

/// Replays every producer and checks both schema and deep semantic/integrity
/// equality. A caller-supplied record or success flag is never a proof receipt.
pub(crate) fn qualify_records(
    definition: &Json,
    resources: &[Json],
    insertion: &InsertionResult,
    roots: &AccountingResult,
    dependencies: &DependencyResult,
    records: &[Json],
) -> RecordResult {
    qualify_records_for(
        Profile::Acc12,
        definition,
        resources,
        insertion,
        roots,
        dependencies,
        records,
    )
}

pub(crate) fn qualify_records_for(
    profile: Profile,
    definition: &Json,
    resources: &[Json],
    insertion: &InsertionResult,
    roots: &AccountingResult,
    dependencies: &DependencyResult,
    records: &[Json],
) -> RecordResult {
    verify(
        profile,
        definition,
        resources,
        insertion,
        roots,
        dependencies,
        Some(records),
    )
}

fn verify(
    profile: Profile,
    definition: &Json,
    resources: &[Json],
    proven: &InsertionResult,
    roots: &AccountingResult,
    supplied_dependencies: &DependencyResult,
    supplied: Option<&[Json]>,
) -> RecordResult {
    let mut result = RecordResult {
        status: RecordStatus::Unavailable,
        records: Vec::new(),
        diagnostics: Vec::new(),
        outstanding_dependencies: proven.qualification.outstanding_dependencies.clone(),
    };
    let request = match insertion::recheck_preservation(profile, definition, resources, proven) {
        Ok(request) => request,
        Err((status, message)) => {
            result.issue(status, "insertion", message);
            return result.finish();
        }
    };
    // This producer independently recomputes and compares the complete root
    // result. It also rechecks the exact closure, schema and dependency set.
    let checked =
        dependencies::qualify_dependencies_for(profile, definition, resources, proven, roots);
    result.diagnostics.extend(checked.diagnostics.clone());
    result.outstanding_dependencies = checked.outstanding_dependencies.clone();
    if &checked != supplied_dependencies {
        result.issue(
            Status::Rejected,
            "dependencies",
            "Dependency evidence differs from independent qualification",
        );
    }
    if checked.status != DependencyStatus::DependenciesQualified {
        if result.diagnostics.is_empty() {
            result.issue(
                Status::Unavailable,
                "dependencies",
                "Complete dependency qualification is required",
            );
        }
        return result.finish();
    }
    let sealed = manifest_resources(definition, resources);
    if let Err(error) = schema_validation::preflight_fragment(
        &sealed,
        profile.expected().schema,
        "/$defs/composition_record",
    ) {
        result.issue(Status::Unavailable, "composition_record", &error.message);
        return result.finish();
    }
    let intents = array(at(&request, &["request"]), "compositions");
    if intents.len() != roots.accounting.len()
        || roots.accounting.len() != proven.proofs.len()
        || proven.proofs.len() != proven.qualification.bindings.len()
    {
        result.issue(Status::Rejected, "composition_records", "Every bound intent requires exactly one insertion proof, root-accounting entry and complete record");
        return result.finish();
    }
    let authority = composition_authority(profile, definition, &request);
    let fragments = array(at(&request, &["request"]), "fragments");
    let mut expected = Vec::new();
    for accounting in &roots.accounting {
        let b = &accounting.binding;
        let parent = &proven.materials[&b.parent_request_key];
        let child = &proven.materials[&b.child_request_key];
        let prepared_parent = fragments
            .iter()
            .find(|f| text(f, "request_key") == b.parent_request_key)
            .unwrap();
        let prepared_property_absent = at(prepared_parent, &["fields"])
            .get(text(&b.binding, "parent_property"))
            .is_none();
        // All flags originate in independently replayed evidence; none are
        // inferred from the desired record shape or serialization digest alone.
        let record = object([
            (
                "semantic".into(),
                object([
                    ("parent_canonical_uuid".into(), string(&parent.identity)),
                    ("child_canonical_uuid".into(), string(&child.identity)),
                    (
                        "parent_semantic_type".into(),
                        at(&b.binding, &["parent_semantic_type"]).clone(),
                    ),
                    (
                        "child_semantic_type".into(),
                        at(&b.binding, &["child_semantic_type"]).clone(),
                    ),
                    ("relation".into(), at(&b.binding, &["relation"]).clone()),
                    (
                        "semantic_field_key".into(),
                        at(&b.binding, &["semantic_field_key"]).clone(),
                    ),
                    ("binding_id".into(), at(&b.binding, &["binding_id"]).clone()),
                    (
                        "authoring_property".into(),
                        at(&b.binding, &["parent_property"]).clone(),
                    ),
                    ("ordering".into(), b.ordering.clone()),
                    // Exact same-request endpoint qualification was replayed above.
                    ("resolution_kind".into(), string("request")),
                ]),
            ),
            (
                "integrity".into(),
                object([
                    ("parent_request_key".into(), string(&b.parent_request_key)),
                    ("child_request_key".into(), string(&b.child_request_key)),
                    (
                        "parent_source_ref".into(),
                        string(&accounting.parent_source_ref),
                    ),
                    (
                        "child_source_ref".into(),
                        string(&accounting.child_source_ref),
                    ),
                    (
                        "parent_content_digest".into(),
                        string(&accounting.parent_content_digest),
                    ),
                    (
                        "child_content_digest".into(),
                        string(&accounting.child_content_digest),
                    ),
                    (
                        "composition_binding_resource_key".into(),
                        string(&b.binding_resource_key),
                    ),
                    (
                        "composition_binding_content_digest".into(),
                        string(&b.binding_content_digest),
                    ),
                    (
                        "prepared_property_absent".into(),
                        Json::Bool(prepared_property_absent),
                    ),
                    ("exact_subtree".into(), Json::Bool(accounting.exact_subtree)),
                    (
                        "child_candidate_artifact_retained".into(),
                        Json::Bool(accounting.child_candidate_artifact_retained),
                    ),
                    (
                        "child_source_root_omitted".into(),
                        Json::Bool(accounting.child_source_root_omitted),
                    ),
                    (
                        "induced_sequence_index".into(),
                        Json::Number(accounting.induced_sequence_index.into()),
                    ),
                    (
                        "identity_disposition".into(),
                        object([
                            ("parent".into(), string(parent.identity_disposition)),
                            ("child".into(), string(child.identity_disposition)),
                        ]),
                    ),
                ]),
            ),
            ("qualification".into(), authority.clone()),
        ]);
        expected.push(record);
    }
    expected.sort_by_cached_key(record_key);
    let mut records = supplied
        .map(<[Json]>::to_vec)
        .unwrap_or_else(|| expected.clone());
    for record in &mut records {
        if let Err(error) = schema_validation::validate_fragment(
            &sealed,
            profile.expected().schema,
            "/$defs/composition_record",
            record,
        ) {
            result.issue(
                Status::Rejected,
                "composition_record",
                &format!("{}: {}", error.path, error.message),
            );
        } else {
            // Only schema-qualified resource members may reach the canonical
            // set normalizer. Malformed proposed records remain ordinary
            // deterministic failures, never a qualified-boundary panic.
            normalize_record(record);
        }
    }
    records.sort_by_cached_key(record_key);
    if records != expected {
        result.issue(Status::Rejected, "composition_records", "Record cardinality or semantic, integrity or qualification fields differ from independently proven inputs");
    }
    if result.diagnostics.is_empty() {
        result.status = RecordStatus::RecordsQualified;
        result.records = records;
    }
    result.finish()
}

fn record_key(record: &Json) -> (String, u64, String) {
    let semantic = at(record, &["semantic"]);
    (
        text(semantic, "parent_canonical_uuid").into(),
        at(semantic, &["ordering"]).as_u64().unwrap_or(0),
        text(semantic, "child_canonical_uuid").into(),
    )
}

fn composition_authority(profile: Profile, definition: &Json, request: &Json) -> Json {
    let basis = at(request, &["basis"]);
    let adc = array(definition, "resourceManifest")
        .iter()
        .find(|m| text(m, "canonicalResourceKey") == "authoring-domain/1.1/contract")
        .unwrap();
    let mut record = object([(
        "qualification".into(),
        object([
            (
                "architecture_interpretation".into(),
                at(basis, &["architecture_interpretation"]).clone(),
            ),
            (
                "authoring_domain".into(),
                object([
                    ("contract_id".into(), string("adr-kit.authoring-domain")),
                    ("version".into(), string("1.1")),
                    ("content_digest".into(), at(adc, &["contentDigest"]).clone()),
                ]),
            ),
            ("authoring".into(), at(basis, &["authoring"]).clone()),
            (
                "normalized_model".into(),
                at(basis, &["normalized_model"]).clone(),
            ),
            // This is CEC contract authority, NOT request.custom_entity registry
            // selection. The exact ACC closure supplies these immutable resources.
            (
                "custom_entity".into(),
                object([
                    ("family".into(), string("custom-entity")),
                    ("version".into(), string("1.0")),
                    (
                        "resources".into(),
                        Json::Array(
                            array(definition, "resourceManifest")
                                .iter()
                                .filter(|m| {
                                    text(m, "canonicalResourceKey")
                                        .starts_with("custom-entity/1.0/")
                                })
                                .map(|m| {
                                    object([
                                        (
                                            "canonical_resource_key".into(),
                                            at(m, &["canonicalResourceKey"]).clone(),
                                        ),
                                        (
                                            "content_digest".into(),
                                            at(m, &["contentDigest"]).clone(),
                                        ),
                                    ])
                                })
                                .collect(),
                        ),
                    ),
                ]),
            ),
            ("acc".into(), at(basis, &["acc"]).clone()),
            ("composition_binding".into(), {
                let member = array(definition, "resourceManifest")
                    .iter()
                    .find(|m| text(m, "canonicalResourceKey") == profile.expected().table)
                    .unwrap();
                object([
                    (
                        "canonical_resource_key".into(),
                        string(profile.expected().table),
                    ),
                    (
                        "content_digest".into(),
                        at(member, &["contentDigest"]).clone(),
                    ),
                ])
            }),
        ]),
    )]);
    // The binding selector was checked against verified rules and manifest.
    normalize_record(&mut record);
    at(&record, &["qualification"]).clone()
}

fn normalize_record(record: &mut Json) {
    // Qualification resource lists are sets. No other arrays are reordered.
    for pointer in [
        "/qualification/architecture_interpretation/authority_closure/resources",
        "/qualification/authoring/resources",
        "/qualification/normalized_model/resources",
        "/qualification/custom_entity/resources",
    ] {
        if let Some(resources) = field_mut(record, &pointer[1..]).and_then(Json::as_array_mut) {
            resources.sort_by_cached_key(canonical);
        }
    }
}

fn field_mut<'a>(value: &'a mut Json, path: &str) -> Option<&'a mut Json> {
    let mut value = value;
    for key in path.split('/') {
        value = value.as_object_mut()?.get_mut(key)?;
    }
    Some(value)
}

#[cfg(test)]
#[path = "authoring_construction_records_v12_tests.rs"]
mod tests;
