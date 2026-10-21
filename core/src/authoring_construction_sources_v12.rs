//! Qualified artifacts and exact-property root accounting, never basis sealing.
use super::insertion::{self, InsertionResult, InsertionStatus};
use super::*;
use crate::candidate_source::{self, CandidateSourceArtifact, CandidateSourceContainment};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum AccountingStatus {
    Rejected,
    Unavailable,
    Unresolved,
    RootsAccounted,
}

/// Partial integrity evidence, not a complete ACC composition record.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct RootAccounting {
    pub binding: BindingDecision,
    pub parent_source_ref: String,
    pub child_source_ref: String,
    pub parent_content_digest: String,
    pub child_content_digest: String,
    pub induced_sequence_index: usize,
    pub exact_subtree: bool,
    pub child_candidate_artifact_retained: bool,
    pub child_source_root_omitted: bool,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct AccountingResult {
    pub status: AccountingStatus,
    pub artifacts: Vec<CandidateSourceArtifact>,
    pub selected_root_source_refs: Vec<String>,
    pub accounting: Vec<RootAccounting>,
    pub diagnostics: Vec<Diagnostic>,
    pub outstanding_dependencies: BTreeSet<&'static str>,
}

impl AccountingResult {
    fn new(insertion: &InsertionResult) -> Self {
        Self {
            status: AccountingStatus::Unavailable,
            artifacts: Vec::new(),
            selected_root_source_refs: Vec::new(),
            accounting: Vec::new(),
            diagnostics: insertion.qualification.diagnostics.clone(),
            outstanding_dependencies: insertion.qualification.outstanding_dependencies.clone(),
        }
    }
    fn issue(&mut self, status: Status, suffix: &str, key: &str, message: &str) {
        self.diagnostics.push(Diagnostic {
            status,
            code: format!("authoring_construction.composition.{suffix}"),
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
            Some(Status::Rejected) => AccountingStatus::Rejected,
            Some(Status::Unavailable) => AccountingStatus::Unavailable,
            Some(Status::Unresolved) => AccountingStatus::Unresolved,
            // Success is issued only after complete artifact/root accounting,
            // never merely because an early exit lacks failure diagnostics.
            _ => self.status,
        };
        if self.status != AccountingStatus::RootsAccounted {
            self.artifacts.clear();
            self.selected_root_source_refs.clear();
            self.accounting.clear();
        }
        self
    }
}

/// Source references are exact, opaque, nonempty integrity locators supplied by
/// the caller. No path parsing, identity derivation or persistence is implied.
pub(crate) fn prepare(
    definition: &Json,
    resources: &[Json],
    proven: &InsertionResult,
    source_refs: &BTreeMap<String, String>,
) -> AccountingResult {
    let mut result = AccountingResult::new(proven);
    let request = match receipt(definition, resources, proven, &mut result) {
        Some(request) => request,
        None => return result.finish(),
    };
    if source_refs.keys().ne(proven.materials.keys()) {
        result.issue(
            Status::Rejected,
            "containment_accounting",
            "source_refs",
            "Exactly one source reference is required for every retained artifact",
        );
        return result.finish();
    }
    let parents: BTreeSet<_> = proven
        .proofs
        .iter()
        .map(|p| p.binding.parent_request_key.as_str())
        .collect();
    let mut artifacts = Vec::new();
    for (key, material) in &proven.materials {
        let source = candidate_source::decode_canonical_candidate(&material.bytes)
            .expect("rechecked insertion bytes");
        match candidate_source::seal_candidate_artifact(
            key,
            &source_refs[key],
            if parents.contains(key.as_str()) {
                "authoring_document"
            } else {
                "authoring_fragment"
            },
            material.selector.clone(),
            at(&request, &["basis", "authoring"]).clone(),
            &source,
        ) {
            Ok(artifact) if artifact.bytes == material.bytes => artifacts.push(artifact),
            _ => result.issue(
                Status::Rejected,
                "containment_accounting",
                key,
                "Candidate artifact cannot preserve the exact insertion bytes and source reference",
            ),
        }
    }
    if !result.diagnostics.is_empty() {
        return result.finish();
    }
    qualify_accounting(definition, resources, proven, artifacts, None)
}

fn receipt(
    definition: &Json,
    resources: &[Json],
    proven: &InsertionResult,
    result: &mut AccountingResult,
) -> Option<Json> {
    if proven.status != InsertionStatus::PreservationProven {
        if result.diagnostics.is_empty() {
            let status = if proven.status == InsertionStatus::Rejected {
                Status::Rejected
            } else {
                Status::Unavailable
            };
            result.issue(
                status,
                if status == Status::Rejected {
                    "containment_accounting"
                } else {
                    "evidence_unavailable"
                },
                "insertion",
                "Completed insertion, not binding qualification, is required",
            );
        }
        return None;
    }
    match insertion::recheck_preservation(definition, resources, proven) {
        Ok(request) => Some(request),
        Err((status, message)) => {
            result.issue(
                status,
                if status == Status::Unavailable {
                    "evidence_unavailable"
                } else {
                    "containment_accounting"
                },
                "insertion",
                message,
            );
            None
        }
    }
}

/// Independent validation seam for supplied artifact evidence / proposed roots.
/// A successful result is deliberately not a CandidateSourceBasis and contains
/// no basis digest or detached NM context. References remain outstanding.
pub(crate) fn qualify_accounting(
    definition: &Json,
    resources: &[Json],
    proven: &InsertionResult,
    mut artifacts: Vec<CandidateSourceArtifact>,
    proposed_roots: Option<&[String]>,
) -> AccountingResult {
    let mut result = AccountingResult::new(proven);
    let request = match receipt(definition, resources, proven, &mut result) {
        Some(request) => request,
        None => return result.finish(),
    };
    artifacts.sort_by(|a, b| {
        a.source_ref
            .cmp(&b.source_ref)
            .then(a.request_key.cmp(&b.request_key))
    });
    let mut by_key = BTreeMap::new();
    let mut refs = BTreeSet::new();
    let parents: BTreeSet<_> = proven
        .proofs
        .iter()
        .map(|p| p.binding.parent_request_key.as_str())
        .collect();
    let mut identities = BTreeSet::new();
    for artifact in &artifacts {
        let key = artifact.request_key.as_str();
        if by_key.insert(key, artifact).is_some()
            || artifact.source_ref.is_empty()
            || !refs.insert(&artifact.source_ref)
        {
            result.issue(
                Status::Rejected,
                "containment_accounting",
                key,
                "Duplicate request key, duplicate source reference or empty source reference",
            );
        }
        let Some(material) = proven.materials.get(key) else {
            result.issue(
                Status::Rejected,
                "containment_accounting",
                key,
                "Artifact was not retained by verified insertion",
            );
            continue;
        };
        if !identities.insert(&material.identity) {
            result.issue(
                Status::Rejected,
                "duplicate_identity",
                key,
                "A canonical identity is defined by more than one candidate artifact",
            );
        }
        let kind = if parents.contains(key) {
            "authoring_document"
        } else {
            "authoring_fragment"
        };
        if artifact.bytes != material.bytes
            || artifact.source_schema != material.selector
            || artifact.artifact_kind != kind
            || artifact.source_contract != *at(&request, &["basis", "authoring"])
            || candidate_source::decode_and_validate_candidate(artifact).is_err()
        {
            result.issue(Status::Rejected, "containment_accounting", key, "Artifact bytes, digest, profile, kind, schema or authority differ from verified insertion");
        }
    }
    if by_key
        .keys()
        .copied()
        .ne(proven.materials.keys().map(String::as_str))
    {
        result.issue(
            Status::Rejected,
            "containment_accounting",
            "artifacts",
            "The complete retained parent and child artifact set is required",
        );
    }
    // Exact-property accounting is complete for the participating units only.
    // Other AI-governed authored memberships cannot silently evade the identity
    // union check; their ownership accounting is outside this bounded slice.
    for (_, field, values) in additional_memberships(definition, resources, proven) {
        if !values.as_array().is_some_and(Vec::is_empty) {
            result.issue(Status::Unavailable, "evidence_unavailable", text(&field, "semantic_field_key"), "Additional authored child membership requires independently qualified ownership accounting");
        }
    }
    if !result.diagnostics.is_empty() {
        return result.finish();
    }
    let mut containment = Vec::new();
    let mut positions = BTreeMap::<(String, String), usize>::new();
    for proof in &proven.proofs {
        let b = &proof.binding;
        let parent = by_key[b.parent_request_key.as_str()];
        let child = by_key[b.child_request_key.as_str()];
        let property = text(&b.binding, "parent_property");
        let index = positions
            .entry((b.parent_request_key.clone(), property.into()))
            .or_default();
        let parent_source = candidate_source::decode_and_validate_candidate(parent).unwrap();
        let child_source = candidate_source::decode_and_validate_candidate(child).unwrap();
        if array(&parent_source, property).get(*index) != Some(&proof.established_child)
            || child_source != proof.established_child
            || b.child_identity.as_deref() != Some(text(&child_source, "id"))
            || b.parent_identity.as_deref() != Some(text(&parent_source, "id"))
        {
            result.issue(Status::Rejected, "containment_accounting", &b.child_request_key, "Exact qualified property, membership position, identity and complete child subtree proof are required");
        } else {
            containment.push(CandidateSourceContainment {
                parent_request_key: b.parent_request_key.clone(),
                child_request_key: b.child_request_key.clone(),
            });
            result.accounting.push(RootAccounting {
                binding: b.clone(),
                parent_source_ref: parent.source_ref.clone(),
                child_source_ref: child.source_ref.clone(),
                parent_content_digest: parent.content_digest.clone(),
                child_content_digest: child.content_digest.clone(),
                induced_sequence_index: *index,
                exact_subtree: true,
                child_candidate_artifact_retained: true,
                child_source_root_omitted: true,
            });
        }
        *index += 1;
    }
    if !result.diagnostics.is_empty() {
        return result.finish();
    }
    // Pair-only generic containment is used only after the stronger ACC proof.
    match candidate_source::select_minimal_candidate_source_roots(artifacts.clone(), &containment) {
        Ok(roots) => {
            result.selected_root_source_refs = roots.iter().map(|a| a.source_ref.clone()).collect();
            if let Some(proposed) = proposed_roots {
                let mut proposed = proposed.to_vec();
                proposed.sort();
                if proposed != result.selected_root_source_refs {
                    result.issue(Status::Rejected, "containment_accounting", "source_roots", "Selected roots must contain exactly the parents, omitting each proved child once");
                }
            }
        }
        Err(message) => result.issue(
            Status::Rejected,
            "containment_accounting",
            "source_roots",
            &message,
        ),
    }
    result.accounting.sort_by_cached_key(|p| {
        (
            p.binding.parent_identity.clone(),
            p.binding.ordering.as_u64().unwrap_or(0),
            p.binding.child_identity.clone(),
        )
    });
    result.artifacts = artifacts;
    result.status = AccountingStatus::RootsAccounted;
    if result.diagnostics.is_empty() {
        result
            .outstanding_dependencies
            .remove("exact_subtree_and_minimal_root_accounting");
    }
    result.finish()
}

/// Inspect the exact AI-declared, nonselected memberships after insertion
/// receipt verification. Values are evidence only, never new binding authority.
pub(super) fn additional_memberships(
    definition: &Json,
    resources: &[Json],
    proven: &InsertionResult,
) -> Vec<(String, Json, Json)> {
    let mut inspections = BTreeMap::new();
    let sealed = manifest_resources(definition, resources);
    for p in &proven.proofs {
        let b = &p.binding;
        let ai = &sealed[text(at(&b.binding, &["ai_authority"]), "canonical_resource_key")];
        let source = serde_json::to_value(
            candidate_source::decode_canonical_candidate(
                &proven.materials[&b.parent_request_key].bytes,
            )
            .unwrap(),
        )
        .unwrap();
        let selected: BTreeSet<_> = proven
            .proofs
            .iter()
            .filter(|p| p.binding.parent_request_key == b.parent_request_key)
            .map(|p| text(&p.binding.binding, "semantic_field_key"))
            .collect();
        for field in array(ai, "semantic_types")
            .iter()
            .filter(|t| text(t, "semantic_type") == text(&b.binding, "parent_semantic_type"))
            .flat_map(|t| array(t, "field_dispositions"))
        {
            let field_key = text(field, "semantic_field_key");
            if text(field, "destination_ref") != "child_membership" || selected.contains(field_key)
            {
                continue;
            }
            let Some((_, pointer)) = field_key.split_once('#') else {
                continue;
            };
            let values = source
                .pointer(pointer)
                .cloned()
                .unwrap_or(serde_json::json!([]));
            inspections.insert(
                (b.parent_request_key.clone(), field_key.to_owned()),
                (
                    b.parent_request_key.clone(),
                    field.clone(),
                    serde_json::from_value(values).unwrap(),
                ),
            );
        }
    }
    inspections.into_values().collect()
}

#[cfg(test)]
#[path = "authoring_construction_sources_v12_tests.rs"]
mod tests;
