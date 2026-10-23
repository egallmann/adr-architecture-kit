//! Internal compiler insertion and exact-subtree proof, not source sealing.
//!
//! Authority, endpoint selection, ownership and ordering belong to `qualify`.
//! No protocol operation invokes this module. Material is released atomically
//! only after schema validation, canonical serialization and preservation proof.

use super::*;
use crate::{
    authoring_construction_orchestration::{establish_identity, IdentityMinter},
    candidate_source::{self, CandidateSourceSelector},
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum InsertionStatus {
    Rejected,
    Unavailable,
    Unresolved,
    PreservationProven,
}

/// Unsealed material: no source reference, root disposition or composition record.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Material {
    pub selector: CandidateSourceSelector,
    pub bytes: Vec<u8>,
    pub identity: String,
    pub identity_disposition: &'static str,
}

/// Internal implementation failures, not additions to ACC's wire vocabulary.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum PreservationFailure {
    MaterialSetChanged,
    InvalidSerialization(String),
    ParentFieldsChanged(String),
    MembershipChanged(String, String),
    ChildIdentityChanged(String),
    ChildFieldsChanged(String),
    RetainedChildChanged(String),
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SubtreeProof {
    pub binding: BindingDecision,
    /// Independent retained child material is deeply equal to this embedded child.
    pub established_child: Json,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct InsertionResult {
    pub status: InsertionStatus,
    pub qualification: Qualification,
    pub preservation_failures: Vec<PreservationFailure>,
    pub materials: BTreeMap<String, Material>,
    pub proofs: Vec<SubtreeProof>,
    // Not a transport field. Only successful insertion can issue this receipt.
    established_request: Option<Json>,
    profile: Profile,
    original_request: Option<Json>,
    authority_commitment: Option<String>,
    identity_dispositions: BTreeMap<String, &'static str>,
}

impl InsertionResult {
    pub(crate) fn matches_request(&self, request: &Json) -> bool {
        self.original_request.as_ref() == Some(&normalized_request(request))
    }

    fn blocked(qualification: Qualification) -> Self {
        let status = match qualification.status {
            Status::Rejected => InsertionStatus::Rejected,
            Status::Unresolved => InsertionStatus::Unresolved,
            _ => InsertionStatus::Unavailable,
        };
        Self {
            status,
            qualification,
            preservation_failures: Vec::new(),
            materials: BTreeMap::new(),
            proofs: Vec::new(),
            established_request: None,
            profile: Profile::Acc12,
            original_request: None,
            authority_commitment: None,
            identity_dispositions: BTreeMap::new(),
        }
    }
}

fn normalized_request(request: &Json) -> Json {
    let mut normalized = request.clone();
    if let Some(body) = normalized
        .as_object_mut()
        .and_then(|v| v.get_mut("request"))
        .and_then(Json::as_object_mut)
    {
        for key in ["fragments", "compositions"] {
            if let Some(values) = body.get_mut(key).and_then(Json::as_array_mut) {
                if key == "fragments" {
                    values.sort_by_cached_key(|f| text(f, "request_key").to_owned());
                } else {
                    values.sort_by_cached_key(canonical);
                }
            }
        }
    }
    normalized
}

fn selector(row: &Json, role: &str) -> CandidateSourceSelector {
    let value = row.get(role).unwrap_or(&Json::Null);
    CandidateSourceSelector {
        canonical_resource_key: text(value, "canonical_resource_key").into(),
        json_pointer: text(value, "schema_pointer").into(),
    }
}

fn report(q: &mut Qualification, status: Status, code: &str, key: &str, message: &str) {
    q.diagnostic(status, code, None, key, &string(message));
}

/// Establishes identity once per supported fragment, never once per membership.
/// Unbound/native aggregation is deliberately unavailable in this bounded seam.
pub(crate) fn insert(
    definition: &Json,
    resources: &[Json],
    request: &Json,
    minter: &mut dyn IdentityMinter,
) -> InsertionResult {
    insert_for(Profile::Acc12, definition, resources, request, minter)
}

pub(crate) fn insert_for(
    profile: Profile,
    definition: &Json,
    resources: &[Json],
    request: &Json,
    minter: &mut dyn IdentityMinter,
) -> InsertionResult {
    let mut q = qualify_for(profile, definition, resources, request);
    if q.status != Status::Qualified {
        return InsertionResult::blocked(q);
    }
    // Project only manifest members, after the existing qualifier verified closure.
    let sealed = manifest_resources(definition, resources);
    let mut selectors = BTreeMap::new();
    for b in &q.bindings.clone() {
        for (key, role) in [
            (&b.parent_request_key, "parent_schema"),
            (&b.child_request_key, "child_schema"),
        ] {
            let selected = selector(&b.binding, role);
            if selectors
                .insert(key.clone(), selected.clone())
                .is_some_and(|old| old != selected)
            {
                report(
                    &mut q,
                    Status::Unavailable,
                    "authoring_construction.authority.unavailable",
                    key,
                    "Conflicting qualified schema selectors",
                );
                return InsertionResult::blocked(q.finish());
            }
        }
    }
    let fragments = array(at(request, &["request"]), "fragments");
    if selectors.is_empty()
        || fragments
            .iter()
            .any(|f| !selectors.contains_key(text(f, "request_key")))
    {
        report(
            &mut q,
            Status::Unavailable,
            "authoring_construction.execution_capability.unavailable",
            "fragments",
            "This internal slice requires every fragment to participate in a qualified composition",
        );
    }
    // The governed serializer's compiled schemas must match supplied authority;
    // compiled schema resources cannot act as ambient fallback authority.
    match candidate_source::authoring_schema_resources() {
        Ok(catalog)
            if catalog
                .iter()
                .all(|(key, schema)| sealed.get(key) == Some(schema)) => {}
        _ => report(
            &mut q,
            Status::Unavailable,
            "authoring_construction.authority.unavailable",
            "serialization",
            "Governed serializer schema catalog differs from the verified closure",
        ),
    }
    for (key, s) in &selectors {
        if let Err(error) = schema_validation::preflight_fragment(
            &sealed,
            &s.canonical_resource_key,
            &s.json_pointer,
        ) {
            report(
                &mut q,
                Status::Unavailable,
                "authoring_construction.authority.unavailable",
                key,
                &error.message,
            );
        }
    }
    q = q.finish();
    if q.status != Status::Qualified {
        return InsertionResult::blocked(q);
    }

    let mut established = request.clone();
    let mut identities = BTreeMap::new();
    // Sorting allocates environmental identities predictably within this call;
    // request keys are scheduling locators, never inputs to the identity minter.
    for key in selectors.keys() {
        let fragment = fragments
            .iter()
            .find(|f| text(f, "request_key") == key)
            .unwrap();
        let supplied = at(fragment, &["fields", "id"]).as_str();
        match establish_identity(key, "create", supplied, minter) {
            Ok(identity) if basis::is_uuid_v7(&identity.id) => {
                identities.insert(key.clone(), identity);
            }
            _ => report(
                &mut q,
                Status::Unavailable,
                "authoring_construction.identity.unavailable",
                key,
                "Canonical UUIDv7 allocation unavailable or invalid",
            ),
        }
    }
    q = q.finish();
    if q.status != Status::Qualified {
        return InsertionResult::blocked(q);
    }
    let established_fragments = established
        .as_object_mut()
        .unwrap()
        .get_mut("request")
        .unwrap()
        .as_object_mut()
        .unwrap()
        .get_mut("fragments")
        .unwrap()
        .as_array_mut()
        .unwrap();
    let mut expected = BTreeMap::new();
    for f in established_fragments {
        let key = text(f, "request_key").to_owned();
        let fields = f.as_object_mut().unwrap().get_mut("fields").unwrap();
        fields
            .as_object_mut()
            .unwrap()
            .insert("id".into(), string(&identities[&key].id));
        expected.insert(key, fields.clone());
    }
    // Reuse all duplicate identity/ownership checks with the established IDs.
    q = qualify_for(profile, definition, resources, &established);
    if q.status != Status::Qualified {
        return InsertionResult::blocked(q);
    }
    let mut composed = expected.clone();
    // Binding order is produced exclusively by the existing qualifier.
    for b in &q.bindings {
        let fields = composed
            .get_mut(&b.parent_request_key)
            .unwrap()
            .as_object_mut()
            .unwrap();
        fields
            .entry(text(&b.binding, "parent_property").into())
            .or_insert_with(|| Json::Array(Vec::new()))
            .as_array_mut()
            .unwrap()
            .push(expected[&b.child_request_key].clone());
    }
    let mut materials = BTreeMap::new();
    for (key, source) in &composed {
        let selected = &selectors[key];
        if let Err(error) = schema_validation::validate_fragment(
            &sealed,
            &selected.canonical_resource_key,
            &selected.json_pointer,
            source,
        ) {
            q.diagnostic(
                Status::Rejected,
                "authoring_construction.authoring.invalid",
                Some(&identities[key].id),
                key,
                &string(format!("{}: {}", error.path, error.message)),
            );
            continue;
        }
        match candidate_source::render_source(selected, source) {
            Ok(bytes) => {
                materials.insert(
                    key.clone(),
                    Material {
                        selector: selected.clone(),
                        bytes,
                        identity: identities[key].id.clone(),
                        identity_disposition: identities[key].disposition,
                    },
                );
            }
            Err(message) => report(
                &mut q,
                Status::Unavailable,
                "authoring_construction.execution_capability.unavailable",
                key,
                &message,
            ),
        }
    }
    q = q.finish();
    if q.status != Status::Qualified {
        return InsertionResult::blocked(q);
    }
    let mut result = finish_proof(q, &expected, materials);
    if result.status == InsertionStatus::PreservationProven {
        // Request list order is nonsemantic; normalize only private replay
        // evidence, retaining authored ordering values and every source field.
        let body = established
            .as_object_mut()
            .unwrap()
            .get_mut("request")
            .unwrap()
            .as_object_mut()
            .unwrap();
        body.get_mut("fragments")
            .unwrap()
            .as_array_mut()
            .unwrap()
            .sort_by_cached_key(|f| text(f, "request_key").to_owned());
        body.get_mut("compositions")
            .unwrap()
            .as_array_mut()
            .unwrap()
            .sort_by_cached_key(canonical);
        result.profile = profile;
        result.original_request = Some(normalized_request(request));
        result.authority_commitment = Some(digest(definition));
        result.established_request = Some(established);
        result.identity_dispositions = identities
            .into_iter()
            .map(|(key, identity)| (key, identity.disposition))
            .collect();
    }
    result
}

/// Recheck the actual material and exact proof set against insertion's private
/// receipt. Neither a caller-set status nor a qualifier-only result is proof.
pub(crate) fn recheck_preservation(
    profile: Profile,
    definition: &Json,
    resources: &[Json],
    result: &InsertionResult,
) -> Result<Json, (Status, &'static str)> {
    if result.status != InsertionStatus::PreservationProven
        || !result.preservation_failures.is_empty()
    {
        return Err((
            Status::Rejected,
            "completed insertion and preservation proof are required",
        ));
    }
    let request = result
        .established_request
        .as_ref()
        .ok_or((Status::Rejected, "private insertion receipt is absent"))?;
    if result.profile != profile
        || (profile == Profile::Acc13
            && result.authority_commitment.as_deref() != Some(digest(definition).as_str()))
    {
        return Err((
            Status::Rejected,
            "insertion receipt belongs to another authority or version",
        ));
    }
    if result.materials.iter().any(|(key, material)| {
        result.identity_dispositions.get(key) != Some(&material.identity_disposition)
    }) {
        return Err((
            Status::Rejected,
            "identity disposition differs from insertion receipt",
        ));
    }
    if profile == Profile::Acc13 {
        let mut original = result
            .original_request
            .clone()
            .ok_or((Status::Rejected, "original request receipt absent"))?;
        let body = original
            .as_object_mut()
            .unwrap()
            .get_mut("request")
            .unwrap()
            .as_object_mut()
            .unwrap();
        let fragments = body.get_mut("fragments").unwrap().as_array_mut().unwrap();
        for fragment in fragments.iter_mut() {
            let key = text(fragment, "request_key").to_owned();
            let material = result
                .materials
                .get(&key)
                .ok_or((Status::Rejected, "established identity missing"))?;
            let supplied = at(fragment, &["fields", "id"]).as_str();
            let expected_disposition = if supplied.is_some() {
                "preserved"
            } else {
                "minted"
            };
            if supplied.is_some_and(|id| id != material.identity)
                || material.identity_disposition != expected_disposition
            {
                return Err((
                    Status::Rejected,
                    "identity differs from original request commitment",
                ));
            }
            fragment
                .as_object_mut()
                .unwrap()
                .get_mut("fields")
                .unwrap()
                .as_object_mut()
                .unwrap()
                .insert("id".into(), string(&material.identity));
        }
        fragments.sort_by_cached_key(|f| text(f, "request_key").to_owned());
        body.get_mut("compositions")
            .unwrap()
            .as_array_mut()
            .unwrap()
            .sort_by_cached_key(canonical);
        if &original != request {
            return Err((
                Status::Rejected,
                "established request differs from original request",
            ));
        }
    }
    let qualification = qualify_for(profile, definition, resources, request);
    if qualification.status != Status::Qualified {
        return Err((
            qualification.status,
            "insertion receipt no longer qualifies under exact authority",
        ));
    }
    let expected = array(at(request, &["request"]), "fragments")
        .iter()
        .map(|f| {
            (
                text(f, "request_key").to_owned(),
                at(f, &["fields"]).clone(),
            )
        })
        .collect();
    let checked = finish_proof(qualification, &expected, result.materials.clone());
    if checked.status != InsertionStatus::PreservationProven
        || checked.qualification != result.qualification
        || checked.proofs != result.proofs
    {
        return Err((
            Status::Rejected,
            "material, qualifications or subtree proofs differ from verified insertion",
        ));
    }
    Ok(request.clone())
}

/// Independent proof gate over actual serialized bytes. The immutable expected
/// objects are prepared fields plus established IDs, not reconstructed output.
fn finish_proof(
    mut q: Qualification,
    expected: &BTreeMap<String, Json>,
    materials: BTreeMap<String, Material>,
) -> InsertionResult {
    let mut failures = BTreeSet::new();
    if expected.keys().ne(materials.keys()) {
        failures.insert(PreservationFailure::MaterialSetChanged);
    }
    let mut decoded = BTreeMap::new();
    for (key, m) in &materials {
        match candidate_source::decode_canonical_candidate(&m.bytes) {
            Ok(source)
                if source.as_object().is_some()
                    && text(&source, "id") == m.identity
                    && candidate_source::render_source(&m.selector, &source)
                        .ok()
                        .as_deref()
                        == Some(m.bytes.as_slice()) =>
            {
                decoded.insert(key.clone(), source);
            }
            _ => {
                failures.insert(PreservationFailure::InvalidSerialization(key.clone()));
            }
        }
    }
    let mut parent_properties: BTreeMap<String, BTreeMap<String, Vec<&BindingDecision>>> =
        BTreeMap::new();
    let bindings = q.bindings.clone();
    for b in &bindings {
        for (key, role) in [
            (&b.parent_request_key, "parent_schema"),
            (&b.child_request_key, "child_schema"),
        ] {
            if materials.get(key).map(|m| &m.selector) != Some(&selector(&b.binding, role)) {
                failures.insert(PreservationFailure::InvalidSerialization(key.clone()));
            }
        }
        parent_properties
            .entry(b.parent_request_key.clone())
            .or_default()
            .entry(text(&b.binding, "parent_property").into())
            .or_default()
            .push(b);
        let child = &expected[&b.child_request_key];
        if decoded.get(&b.child_request_key) != Some(child) {
            failures.insert(PreservationFailure::RetainedChildChanged(
                b.child_request_key.clone(),
            ));
        }
    }
    let mut proofs = Vec::new();
    for (parent, properties) in parent_properties {
        let Some(observed) = decoded.get(&parent) else {
            continue;
        };
        let mut unchanged = observed.clone();
        for (property, bindings) in properties {
            let children = array(observed, &property);
            if children.len() != bindings.len() {
                failures.insert(PreservationFailure::MembershipChanged(
                    parent.clone(),
                    property.clone(),
                ));
            }
            for (b, embedded) in bindings.iter().zip(children) {
                let child = &expected[&b.child_request_key];
                if embedded.get("id") != child.get("id") {
                    failures.insert(PreservationFailure::ChildIdentityChanged(
                        b.child_request_key.clone(),
                    ));
                    q.diagnostic(
                        Status::Rejected,
                        "authoring_construction.composition.identity_mutation",
                        b.child_identity.as_deref(),
                        text(&b.binding, "semantic_field_key"),
                        embedded,
                    );
                }
                let mut non_identity = embedded.clone();
                if let Some(fields) = non_identity.as_object_mut() {
                    fields.insert("id".into(), child.get("id").unwrap().clone());
                }
                if &non_identity != child {
                    failures.insert(PreservationFailure::ChildFieldsChanged(
                        b.child_request_key.clone(),
                    ));
                    q.diagnostic(
                        Status::Rejected,
                        "authoring_construction.composition.child_mutation",
                        b.child_identity.as_deref(),
                        text(&b.binding, "semantic_field_key"),
                        embedded,
                    );
                }
                proofs.push(SubtreeProof {
                    binding: (*b).clone(),
                    established_child: child.clone(),
                });
            }
            unchanged.as_object_mut().unwrap().remove(&property);
        }
        if expected.get(&parent) != Some(&unchanged) {
            failures.insert(PreservationFailure::ParentFieldsChanged(parent));
        }
    }
    q = q.finish();
    if !failures.is_empty() {
        return InsertionResult {
            status: InsertionStatus::Rejected,
            qualification: q,
            preservation_failures: failures.into_iter().collect(),
            materials: BTreeMap::new(),
            proofs: Vec::new(),
            established_request: None,
            profile: Profile::Acc12,
            original_request: None,
            authority_commitment: None,
            identity_dispositions: BTreeMap::new(),
        };
    }
    for completed in [
        "prepared_authoring_field_validation",
        "compiler_child_insertion",
        "complete_child_field_and_identity_preservation",
    ] {
        q.outstanding_dependencies.remove(completed);
    }
    InsertionResult {
        status: InsertionStatus::PreservationProven,
        qualification: q,
        preservation_failures: Vec::new(),
        materials,
        proofs,
        established_request: None,
        profile: Profile::Acc12,
        original_request: None,
        authority_commitment: None,
        identity_dispositions: BTreeMap::new(),
    }
}

#[cfg(test)]
#[path = "authoring_construction_insertion_v12_tests.rs"]
mod tests;
