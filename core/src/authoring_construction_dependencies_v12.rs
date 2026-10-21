//! Read-only, proof-bound ACC 1.2 dependency qualification. No construction,
//! identity allocation, complete composition records or basis sealing.
use super::insertion::{self, InsertionResult};
use super::sources::{self, AccountingResult, AccountingStatus};
use super::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum DependencyStatus {
    Rejected,
    Unavailable,
    Unresolved,
    DependenciesQualified,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ReferenceCollection {
    pub source_request_key: String,
    pub source_canonical_uuid: String,
    /// ACC's inherited resolved_reference records, schema checked below.
    pub resolved_references: Json,
    pub governing_basis: Vec<Json>,
    pub explicitly_empty: bool,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PendingDependency {
    pub category: &'static str,
    pub key: String,
    /// Qualification of authority is distinct from executable capability.
    pub authority: Check,
    pub evidence: Json,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct DependencyResult {
    pub status: DependencyStatus,
    /// Verified authority availability is not executable dependency completion.
    pub authority: Option<Json>,
    pub references: Vec<ReferenceCollection>,
    pub relationships_explicitly_empty: bool,
    pub memberships_explicitly_empty: bool,
    /// Blocked obligations survive failure; usable resolution evidence does not.
    pub pending: Vec<PendingDependency>,
    pub diagnostics: Vec<Diagnostic>,
    pub outstanding_dependencies: BTreeSet<&'static str>,
}

impl DependencyResult {
    fn issue(&mut self, status: Status, code: &str, id: Option<&str>, key: &str, payload: &Json) {
        self.diagnostics.push(Diagnostic {
            status,
            code: code.into(),
            semantic_identity: id.map(str::to_owned),
            field_or_relation_key: key.into(),
            payload: payload.clone(),
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
        self.pending
            .sort_by_cached_key(|p| (p.category, p.key.clone(), canonical(&p.evidence)));
        self.references
            .sort_by(|a, b| a.source_canonical_uuid.cmp(&b.source_canonical_uuid));
        self.status = match self.diagnostics.iter().map(|d| d.status).min() {
            Some(Status::Rejected) => DependencyStatus::Rejected,
            Some(Status::Unavailable) => DependencyStatus::Unavailable,
            Some(Status::Unresolved) => DependencyStatus::Unresolved,
            _ => self.status,
        };
        if self.status != DependencyStatus::DependenciesQualified {
            self.references.clear();
            self.relationships_explicitly_empty = false;
            self.memberships_explicitly_empty = false;
        } else {
            self.outstanding_dependencies
                .remove("non_composition_reference_and_relationship_resolution");
        }
        self
    }
}

/// Checks only independently completed insertion and accounting. Unsupported
/// root accounting cannot suppress independently inspectable request violations.
pub(crate) fn qualify_dependencies(
    definition: &Json,
    resources: &[Json],
    proven: &InsertionResult,
    roots: &AccountingResult,
) -> DependencyResult {
    let mut result = DependencyResult {
        status: DependencyStatus::Unavailable,
        authority: None,
        references: Vec::new(),
        relationships_explicitly_empty: false,
        memberships_explicitly_empty: false,
        pending: Vec::new(),
        diagnostics: proven.qualification.diagnostics.clone(),
        outstanding_dependencies: proven.qualification.outstanding_dependencies.clone(),
    };
    let request = match insertion::recheck_preservation(definition, resources, proven) {
        Ok(request) => request,
        Err((status, message)) => {
            result.issue(
                status,
                "authoring_construction.composition.evidence_unavailable",
                None,
                "insertion",
                &string(message),
            );
            return result.finish();
        }
    };
    if roots.status == AccountingStatus::RootsAccounted {
        let checked = sources::qualify_accounting(
            definition,
            resources,
            proven,
            roots.artifacts.clone(),
            Some(&roots.selected_root_source_refs),
        );
        if &checked != roots || checked.status != AccountingStatus::RootsAccounted {
            result.diagnostics.extend(checked.diagnostics);
            result.issue(
                Status::Rejected,
                "authoring_construction.composition.containment_accounting",
                None,
                "source_roots",
                &string("Root-accounting evidence differs from independent verification"),
            );
        } else {
            result.outstanding_dependencies = checked.outstanding_dependencies;
        }
    } else {
        // A failed/mutated accounting result is not authority for diagnostics.
        // Re-inspect memberships below from the verified insertion receipt.
        result.issue(
            Status::Unavailable,
            "authoring_construction.dependency.capability_unavailable",
            None,
            "source_roots",
            &string("Independently verified RootsAccounted evidence is required"),
        );
    }
    let sealed = manifest_resources(definition, resources);
    if let Err(error) = schema_validation::preflight_fragment(
        &sealed,
        "authoring-construction/1.1/schema",
        "/$defs/resolved_reference",
    ) {
        result.issue(
            Status::Unavailable,
            "authoring_construction.dependency.capability_unavailable",
            None,
            "resolved_reference",
            &string(error.message),
        );
    }
    let request_basis = at(&request, &["basis"]);
    let mut ai = at(request_basis, &["architecture_interpretation"]).clone();
    if let Some(closure) = ai.as_object_mut().unwrap().get_mut("authority_closure") {
        *closure = normalized_qualification(closure);
    }
    result.authority = Some(object([
        ("acc".into(), at(request_basis, &["acc"]).clone()),
        (
            "adc".into(),
            normalized_qualification(at(request_basis, &["adc"])),
        ),
        (
            "authoring".into(),
            normalized_qualification(at(request_basis, &["authoring"])),
        ),
        ("architecture_interpretation".into(), ai),
    ]));
    let fragments = array(at(&request, &["request"]), "fragments");
    let entries = array(at(request_basis, &["reference_basis"]), "entries");
    // Optional descriptors are integrity evidence, not alternate lookup paths.
    for entry in entries {
        if entry.get("source_basis").is_some_and(|s| {
            !s.as_object()
                .is_some_and(crate::authoring_construction::source_descriptor_integrity)
        }) {
            result.issue(
                Status::Rejected,
                "authoring_construction.basis.exact_source_digest",
                None,
                text(entry, "reference_id"),
                &string("Optional exact source descriptor failed byte/digest integrity"),
            );
        }
    }
    let mut resolver_fragments = fragments.to_vec();
    let mut governing = BTreeMap::<String, Vec<Json>>::new();
    let selected = normalized_qualification(at(request_basis, &["authoring"]));
    for fragment in &mut resolver_fragments {
        let source_key = text(fragment, "request_key").to_owned();
        let source_id = text(at(fragment, &["fields"]), "id").to_owned();
        let refs = array(fragment, "references").to_vec();
        let mut counts = BTreeMap::new();
        for reference in &refs {
            *counts
                .entry(text(reference, "reference_key"))
                .or_insert(0usize) += 1;
        }
        let mut qualified = Vec::new();
        for reference in &refs {
            let key = text(reference, "reference_key");
            let start = result.diagnostics.len();
            if counts[key] != 1 {
                result.issue(
                    Status::Rejected,
                    "authoring_construction.reference.duplicate_key",
                    Some(&source_id),
                    key,
                    &string("reference_key must be unique within its source semantic unit"),
                );
            }
            let kind = text(reference, "reference_kind");
            let target = text(reference, "target");
            let matches: Vec<_> = if kind == "request" {
                fragments
                    .iter()
                    .filter(|f| text(f, "request_key") == target)
                    .collect()
            } else {
                entries
                    .iter()
                    .filter(|e| text(e, "reference_id") == target)
                    .collect()
            };
            if matches.len() != 1 {
                result.issue(
                    Status::Unresolved,
                    "authoring_construction.reference.unresolved",
                    Some(&source_id),
                    key,
                    &object([
                        ("reference_kind".into(), string(kind)),
                        ("target".into(), string(target)),
                        (
                            "matches".into(),
                            Json::Number(serde_json::Number::from(matches.len())),
                        ),
                    ]),
                );
                continue;
            }
            let resolved = matches[0];
            let target_type = text(resolved, "semantic_type");
            let qualification = normalized_qualification(at(
                resolved,
                &[if kind == "request" {
                    "contract_qualification"
                } else {
                    "qualification"
                }],
            ));
            let id = if kind == "request" {
                text(at(resolved, &["fields"]), "id")
            } else {
                text(resolved, "canonical_uuid")
            };
            // Expectations remain independently discoverable even if target
            // authority/state is unavailable; no early return hides violations.
            if reference
                .get("expected_semantic_type")
                .is_some_and(|v| v.as_str() != Some(target_type))
                || reference
                    .get("qualification")
                    .is_some_and(|q| normalized_qualification(q) != qualification)
            {
                result.issue(
                    Status::Rejected,
                    "authoring_construction.reference.expectation_mismatch",
                    Some(&source_id),
                    key,
                    &object([
                        ("target".into(), string(target)),
                        ("resolved_type".into(), string(target_type)),
                        (
                            "reason".into(),
                            string("Declared exact type or qualification differs from target"),
                        ),
                    ]),
                );
            }
            let descriptor = type_authority(&sealed, target_type);
            if descriptor
                .is_some_and(|d| text(at(d, &["key"]), "kind") != text(resolved, "semantic_kind"))
            {
                result.issue(
                    Status::Rejected,
                    "authoring_construction.reference.expectation_mismatch",
                    Some(&source_id),
                    key,
                    &string("Target kind contradicts its exact ADC type"),
                );
            }
            let supported = descriptor.is_some_and(|d| {
                matches!(text(at(d, &["key"]), "kind"), "adr" | "entity")
                    && text(d, "semantic_type_ownership") == "adr_kit"
                    && text(at(d, &["reference_policy"]), "mode") == "canonical_uuidv7"
                    && text(at(d, &["operation_posture", "reference"]), "permission") == "allowed"
            });
            if !basis::is_uuid_v7(id) || qualification != selected || !supported {
                result.issue(Status::Unavailable,"authoring_construction.reference.unqualified",Some(&source_id),key,&string("Target requires canonical UUIDv7, exact selected Authoring qualification and implemented ADC/AI reference policy"));
            }
            if kind == "existing" && text(resolved, "existence_state") != "active" {
                result.issue(Status::Unavailable,"authoring_construction.reference.unqualified",Some(&source_id),key,&string("Retired-target reuse is outside this active-target capability; no retirement policy is inferred"));
            }
            let intact = resolved.get("source_basis").is_none_or(|s| {
                s.as_object()
                    .is_some_and(crate::authoring_construction::source_descriptor_integrity)
            });
            if result.diagnostics.len() == start && intact {
                let mut reference = reference.clone();
                if let Some(q) = reference.as_object_mut().unwrap().get_mut("qualification") {
                    *q = normalized_qualification(q);
                }
                qualified.push(reference);
                governing.entry(source_key.clone()).or_default().push(object([
                    ("reference_key".into(),string(key)),("acc_fingerprint".into(),string(SCF)),
                    ("target_basis".into(),object([
                        ("selector".into(),string(target)),("reference_kind".into(),string(kind)),
                        ("canonical_uuid".into(),string(id)),("semantic_type".into(),string(target_type)),
                        ("semantic_kind".into(),string(text(resolved,"semantic_kind"))),
                        ("qualification".into(),qualification.clone()),
                        ("existence_state".into(),if kind=="existing" {string(text(resolved,"existence_state"))} else {Json::Null}),
                        ("source_basis".into(),resolved.get("source_basis").cloned().unwrap_or(Json::Null)),
                    ])),
                    ("authority_resources".into(),Json::Array(array(definition,"resourceManifest").iter().filter(|r|matches!(text(r,"canonicalResourceKey"),"authoring-domain/1.1/contract"|"architecture-interpretation/1.2/field-dispositions-1.7-to-2.4")).cloned().collect())),
                    ("adc_reference_policy".into(),at(descriptor.unwrap(),&["reference_policy"]).clone()),
                ]));
            }
        }
        qualified.sort_by_cached_key(canonical);
        fragment
            .as_object_mut()
            .unwrap()
            .insert("references".into(), Json::Array(qualified));
        fragment
            .as_object_mut()
            .unwrap()
            .insert("contract_qualification".into(), selected.clone());
    }
    let relationships = array(at(&request, &["request"]), "relationships");
    result.relationships_explicitly_empty = relationships.is_empty();
    for relationship in relationships {
        let key = text(relationship, "relationship_key");
        let descriptor = type_authority(&sealed, text(relationship, "relationship_type"));
        let authority = if descriptor.is_some_and(|d| {
            text(at(d, &["key"]), "kind") == "relationship"
                && text(d, "semantic_type_ownership") == "adr_kit"
        }) && normalized_qualification(at(relationship, &["qualification"]))
            == selected
        {
            Check::Qualified
        } else {
            Check::Unavailable
        };
        let mut intent = relationship.clone();
        if let Some(q) = intent.as_object_mut().unwrap().get_mut("qualification") {
            *q = normalized_qualification(q);
        }
        result.pending.push(PendingDependency {
            category: "relationship",
            key: key.into(),
            authority,
            evidence: object([
                ("intent".into(), intent),
                (
                    "adc_policy".into(),
                    descriptor.cloned().unwrap_or(Json::Null),
                ),
            ]),
        });
        result.issue(Status::Unavailable,"authoring_construction.dependency.capability_unavailable",None,key,&string("Relationship authority was inspected independently; complete relationship construction is unavailable"));
    }
    result.memberships_explicitly_empty = true;
    for (parent, field, values) in sources::additional_memberships(definition, resources, proven) {
        if !values.as_array().is_some_and(Vec::is_empty) {
            result.memberships_explicitly_empty = false;
            let key = text(&field, "semantic_field_key").to_owned();
            result.pending.push(PendingDependency {
                category: "membership",
                key: key.clone(),
                authority: Check::Qualified,
                evidence: object([
                    ("parent_request_key".into(), string(parent)),
                    ("field_disposition".into(), field),
                    ("authored_values".into(), values),
                ]),
            });
            result.issue(Status::Unavailable,"authoring_construction.dependency.capability_unavailable",None,&key,&string("AI field authority is qualified; additional membership ownership is not executable and is not a composition binding"));
        }
    }
    let mut resolver_basis = request_basis.as_object().unwrap().clone();
    resolver_basis.insert("authoring".into(), selected.clone());
    let mut reference_basis = at(request_basis, &["reference_basis"]).clone();
    for entry in reference_basis
        .as_object_mut()
        .unwrap()
        .get_mut("entries")
        .unwrap()
        .as_array_mut()
        .unwrap()
    {
        let q = entry
            .as_object_mut()
            .unwrap()
            .get_mut("qualification")
            .unwrap();
        *q = normalized_qualification(q);
    }
    resolver_basis.insert("reference_basis".into(), reference_basis);
    match basis::resolve_qualified_references(&resolver_fragments, &resolver_basis) {
        Ok(resolved) => {
            for fragment in fragments {
                let key = text(fragment, "request_key");
                let records = resolved
                    .get(key)
                    .cloned()
                    .unwrap_or(Json::Array(Vec::new()));
                for record in records.as_array().unwrap() {
                    if schema_validation::validate_fragment(
                        &sealed,
                        "authoring-construction/1.1/schema",
                        "/$defs/resolved_reference",
                        record,
                    )
                    .is_err()
                    {
                        result.issue(
                            Status::Unavailable,
                            "authoring_construction.dependency.capability_unavailable",
                            None,
                            key,
                            &string(
                                "Inherited resolved_reference evidence cannot be schema qualified",
                            ),
                        );
                    }
                }
                let mut basis = governing.remove(key).unwrap_or_default();
                basis.sort_by_cached_key(|b| text(b, "reference_key").to_owned());
                result.references.push(ReferenceCollection {
                    source_request_key: key.into(),
                    source_canonical_uuid: text(at(fragment, &["fields"]), "id").into(),
                    resolved_references: records,
                    governing_basis: basis,
                    explicitly_empty: array(fragment, "references").is_empty(),
                });
            }
        }
        Err(_) => result.issue(
            Status::Unavailable,
            "authoring_construction.dependency.capability_unavailable",
            None,
            "references",
            &string(
                "Inherited resolver could not execute the independently qualified reference set",
            ),
        ),
    }
    if result.diagnostics.is_empty() {
        result.status = DependencyStatus::DependenciesQualified;
    }
    result.finish()
}

fn normalized_qualification(value: &Json) -> Json {
    let mut value = value.clone();
    if let Some(resources) = value
        .as_object_mut()
        .and_then(|v| v.get_mut("resources"))
        .and_then(Json::as_array_mut)
    {
        resources.sort_by_cached_key(canonical);
    }
    value
}

/// Select only exact ADC + AI type authority, never schema/prose heuristics.
fn type_authority<'a>(sealed: &'a BTreeMap<String, Json>, semantic_type: &str) -> Option<&'a Json> {
    let types: Vec<_> = array(&sealed["authoring-domain/1.1/contract"], "types")
        .iter()
        .filter(|t| {
            format!(
                "{}/{}",
                text(at(t, &["key"]), "kind"),
                text(at(t, &["key"]), "name")
            ) == semantic_type
        })
        .collect();
    let ai = array(
        &sealed["architecture-interpretation/1.2/field-dispositions-1.7-to-2.4"],
        "semantic_types",
    )
    .iter()
    .filter(|t| text(t, "semantic_type") == semantic_type)
    .count();
    (types.len() == 1 && ai == 1).then(|| types[0])
}

#[cfg(test)]
#[path = "authoring_construction_dependencies_v12_tests.rs"]
mod tests;
