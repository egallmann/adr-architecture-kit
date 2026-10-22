//! Internal composed-source seal and AI 1.2 detached context. Neither a model
//! nor an ACC Constructed outcome. No protocol operation invokes this seam.
use super::dependencies::DependencyResult;
use super::insertion::InsertionResult;
use super::records::{self, RecordResult, RecordStatus};
use super::sources::AccountingResult;
use super::*;
use crate::architecture_interpretation::{InterpretationSourceContext, NormalizedOutputContext};
use crate::candidate_source::{self, CandidateSourceArtifact, CandidateSourceBasis};

const CONTEXT: &str = "architecture-interpretation/1.2/detached-context";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum SealingStatus {
    Rejected,
    Unavailable,
    Unresolved,
    Sealed,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct RootContext {
    pub request_key: String,
    pub canonical_uuid: String,
    pub source_contract: Json,
    pub source: InterpretationSourceContext,
    pub output: NormalizedOutputContext,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct DetachedContext {
    pub domain: String,
    pub scope_root: String,
    /// Exact AI/NM identities and resource key/digest, not a custom registry.
    pub qualification: Json,
    /// One context per minimal root, in exact source_ref order. Embedded units
    /// retain their identities/fields in source bytes and composition records;
    /// their interpretation pointers remain AI's responsibility.
    pub roots: Vec<RootContext>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SealedEvidence {
    /// Complete retained set, including children omitted from the root basis.
    pub retained_artifacts: Vec<CandidateSourceArtifact>,
    /// Only independently proved minimal roots participate in this commitment.
    pub basis: CandidateSourceBasis,
    pub candidate_source_basis: Json,
    pub context: DetachedContext,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SealingResult {
    pub status: SealingStatus,
    pub evidence: Option<SealedEvidence>,
    pub diagnostics: Vec<Diagnostic>,
    pub outstanding_dependencies: BTreeSet<&'static str>,
}

impl SealingResult {
    fn issue(&mut self, status: Status, key: &str, message: &str) {
        self.diagnostics.push(Diagnostic {
            status,
            semantic_identity: None,
            code: if status == Status::Unavailable {
                "authoring_construction.composition.evidence_unavailable"
            } else {
                "authoring_construction.composition.containment_accounting"
            }
            .into(),
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
            Some(Status::Rejected) => SealingStatus::Rejected,
            Some(Status::Unavailable) => SealingStatus::Unavailable,
            Some(Status::Unresolved) => SealingStatus::Unresolved,
            _ => self.status,
        };
        if self.status != SealingStatus::Sealed {
            self.evidence = None;
        } else {
            self.outstanding_dependencies
                .remove("composed_candidate_basis_sealing");
        }
        self
    }
}

/// Replays the complete existing producer chain; supplied success, digest and
/// sealed assertions confer no authority. Does not allocate identities/bytes.
pub(crate) fn prepare(
    definition: &Json,
    resources: &[Json],
    insertion: &InsertionResult,
    roots: &AccountingResult,
    dependencies: &DependencyResult,
    records: &RecordResult,
) -> SealingResult {
    let checked = records::qualify_records(
        definition,
        resources,
        insertion,
        roots,
        dependencies,
        &records.records,
    );
    let mut result = SealingResult {
        status: SealingStatus::Unavailable,
        evidence: None,
        diagnostics: checked.diagnostics.clone(),
        outstanding_dependencies: checked.outstanding_dependencies.clone(),
    };
    if checked.status != RecordStatus::RecordsQualified {
        return result.finish();
    }
    if &checked != records {
        result.issue(
            Status::Rejected,
            "composition_records",
            "Complete record evidence differs from independent producer replay",
        );
        return result.finish();
    }
    // RecordsQualified independently reverified insertion, complete artifact
    // membership, exact-property root omission and every applicable dependency.
    // The list is a selection over that complete set, not a replacement for it.
    let selected: BTreeSet<_> = roots
        .selected_root_source_refs
        .iter()
        .map(String::as_str)
        .collect();
    let minimal_roots: Vec<_> = roots
        .artifacts
        .iter()
        .filter(|a| selected.contains(a.source_ref.as_str()))
        .cloned()
        .collect();
    if minimal_roots.len() != selected.len()
        || selected.len() != roots.selected_root_source_refs.len()
    {
        result.issue(
            Status::Rejected,
            "source_roots",
            "Every verified selected root must be present exactly once",
        );
        return result.finish();
    }
    let basis = match candidate_source::seal_candidate_source_basis(minimal_roots) {
        Ok(basis) => basis,
        Err(message) => {
            result.issue(Status::Rejected, "candidate_source_basis", &message);
            return result.finish();
        }
    };
    let source_contract = &basis.artifacts[0].source_contract;
    let candidate_source_basis = basis::qualified_basis_to_json(&basis, source_contract);
    let sealed = manifest_resources(definition, resources);
    if let Err(error) =
        schema_validation::preflight_fragment(&sealed, SCHEMA, "/$defs/candidate_source_basis")
    {
        result.issue(
            Status::Unavailable,
            "candidate_source_basis",
            &error.message,
        );
        return result.finish();
    }
    if let Err(error) = schema_validation::validate_fragment(
        &sealed,
        SCHEMA,
        "/$defs/candidate_source_basis",
        &candidate_source_basis,
    ) {
        result.issue(
            Status::Rejected,
            "candidate_source_basis",
            &format!("{}: {}", error.path, error.message),
        );
        return result.finish();
    }
    let context = match derive_context(definition, &sealed, &basis, insertion, records) {
        Ok(context) => context,
        Err(message) => {
            result.issue(Status::Unavailable, "detached_context", &message);
            return result.finish();
        }
    };
    result.evidence = Some(SealedEvidence {
        retained_artifacts: roots.artifacts.clone(),
        basis,
        candidate_source_basis,
        context,
    });
    result.status = SealingStatus::Sealed;
    result.finish()
}

/// Recompute the native descriptor/digest, exact record-to-source association,
/// complete retained/root sets and context. No caller-set Sealed is accepted.
pub(crate) fn qualify_seal(
    definition: &Json,
    resources: &[Json],
    insertion: &InsertionResult,
    roots: &AccountingResult,
    dependencies: &DependencyResult,
    records: &RecordResult,
    supplied: &SealingResult,
) -> SealingResult {
    let mut expected = prepare(
        definition,
        resources,
        insertion,
        roots,
        dependencies,
        records,
    );
    if expected.status == SealingStatus::Sealed && &expected != supplied {
        expected.issue(Status::Rejected,"sealed_evidence","Basis commitment, retained/root membership, record linkage or detached context differs from independent replay");
        // Restore the obligation: failed verification releases no sealed basis.
        expected
            .outstanding_dependencies
            .insert("composed_candidate_basis_sealing");
    }
    expected.finish()
}

fn derive_context(
    definition: &Json,
    sealed: &BTreeMap<String, Json>,
    basis: &CandidateSourceBasis,
    insertion: &InsertionResult,
    records: &RecordResult,
) -> Result<DetachedContext, String> {
    let authority = sealed
        .get(CONTEXT)
        .ok_or("Exact AI 1.2 detached-context authority unavailable")?;
    let member = array(definition, "resourceManifest")
        .iter()
        .find(|m| text(m, "canonicalResourceKey") == CONTEXT)
        .ok_or("Detached-context manifest member unavailable")?;
    let hex = basis
        .basis_digest
        .strip_prefix("sha256:")
        .ok_or("Invalid native basis digest")?;
    if hex.len() != 64
        || !hex
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("Invalid native basis digest".into());
    }
    let scope_root = text(authority, "scope_root_form").replace("<lowercase-basis-digest>", hex);
    let mut contexts = Vec::new();
    for artifact in &basis.artifacts {
        let source_ref_hex = format!("{:x}", Sha256::digest(artifact.source_ref.as_bytes()));
        let locator = text(authority, "root_artifact_locator_form")
            .replace("<lowercase-basis-digest>", hex)
            .replace("<SHA-256-of-UTF-8-source_ref>", &source_ref_hex);
        if !locator.starts_with(&format!("{scope_root}/root:sha256:")) {
            return Err("Inconsistent qualified detached-context locator forms".into());
        }
        contexts.push(RootContext {
            request_key: artifact.request_key.clone(),
            canonical_uuid: insertion.materials[&artifact.request_key].identity.clone(),
            source_contract: artifact.source_contract.clone(),
            source: InterpretationSourceContext {
                canonical_source_ref: artifact.source_ref.clone(),
                source_pointer: "/".into(),
            },
            output: NormalizedOutputContext {
                architecture_namespace: text(authority, "architecture_namespace").into(),
                provider_kind: text(authority, "provider_kind").into(),
                artifact_path: locator,
            },
        });
    }
    // Exact contract identities qualify the context without participating in
    // locator derivation. No NM model or custom registry is selected here.
    let qualification = at(&records.records[0], &["qualification"]);
    Ok(DetachedContext {
        domain: text(authority, "domain").into(),
        scope_root,
        qualification: object([
            (
                "architecture_interpretation".into(),
                at(qualification, &["architecture_interpretation"]).clone(),
            ),
            (
                "normalized_model".into(),
                at(qualification, &["normalized_model"]).clone(),
            ),
            (
                "detached_context".into(),
                object([
                    ("canonical_resource_key".into(), string(CONTEXT)),
                    (
                        "content_digest".into(),
                        at(member, &["contentDigest"]).clone(),
                    ),
                ]),
            ),
        ]),
        roots: contexts,
    })
}

#[cfg(test)]
#[path = "authoring_construction_sealing_v12_tests.rs"]
mod tests;
