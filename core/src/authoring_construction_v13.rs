//! Internal ACC 1.3 producer boundary. No dispatch, interpretation or construction outcome.
use crate::authoring_construction_authority::Profile;
use crate::authoring_construction_orchestration::IdentityMinter;
use crate::authoring_construction_v12::{
    self as producer, array, at, dependencies, digest, insertion, manifest_resources,
    qualified_resource, records, sealing, sources, text, Check, Diagnostic, Status,
};
use crate::{object, schema_validation, semantic_contract, string, Json};
use std::collections::{BTreeMap, BTreeSet};

const PROFILE: Profile = Profile::Acc13;
const OWNERSHIP: &str = "architecture-interpretation/1.3/lifecycle-ownership";
const OWNERSHIP_SCHEMA: &str = "architecture-interpretation/1.3/lifecycle-ownership.schema";

/// Exact selector/resource mismatches establish missing authority, not a
/// semantic violation. Malformed value types remain ordinary schema failures.
pub(crate) fn authority_selector_error(error: &schema_validation::SchemaError) -> bool {
    let basis_authority = [
        "basis.acc",
        "basis.architecture_interpretation",
        "basis.normalized_model",
    ]
    .iter()
    .any(|prefix| error.path == *prefix || error.path.starts_with(&format!("{prefix}.")));
    let value_mismatch = error
        .message
        .starts_with("schema validation failed: value must equal ")
        || error.message == "schema validation failed: value is outside the governed enum";
    let missing_identity = [
        "family",
        "version",
        "semantic_contract_fingerprint",
        "authority_closure",
        "resources",
    ]
    .iter()
    .any(|key| {
        error.message == format!("schema validation failed: required property '{key}' is missing")
    });
    (basis_authority && (value_mismatch || missing_identity))
        || (error.path == "contract_version" && value_mismatch)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum SealStatus {
    Rejected,
    Unavailable,
    Unresolved,
    Sealed,
}

/// Private producer receipts are not transported and cannot be supplied by a host.
#[derive(Clone, Debug, PartialEq)]
struct Receipts {
    insertion: insertion::InsertionResult,
    roots: sources::AccountingResult,
    dependencies: dependencies::DependencyResult,
    records: records::RecordResult,
    source_refs: BTreeMap<String, String>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SealResult {
    pub authority: Check,
    pub status: SealStatus,
    pub evidence: Option<sealing::SealedEvidence>,
    pub composition_records: Vec<Json>,
    pub diagnostics: Vec<Diagnostic>,
    pub outstanding_dependencies: BTreeSet<&'static str>,
    receipts: Option<Receipts>,
}

impl SealResult {
    fn issue(&mut self, status: Status, key: &str, message: &str) {
        self.diagnostics.push(Diagnostic {
            status,
            semantic_identity: None,
            code: if status == Status::Unavailable {
                "authoring_construction.authority.unavailable"
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
            Some(Status::Rejected) => SealStatus::Rejected,
            Some(Status::Unavailable) => SealStatus::Unavailable,
            Some(Status::Unresolved) => SealStatus::Unresolved,
            _ => self.status,
        };
        if self.status != SealStatus::Sealed {
            self.evidence = None;
            self.composition_records.clear();
            self.receipts = None;
            self.outstanding_dependencies
                .insert("composed_candidate_basis_sealing");
        }
        self
    }
}

/// An independently pinned definition must verify against the exact subset of
/// the already verified ACC closure. Extra caller resources never participate.
fn definition_qualifies(
    definition: &Json,
    family: &str,
    version: &str,
    scf: &str,
    sealed: &BTreeMap<String, Json>,
) -> bool {
    if text(definition, "semanticContractFamily") != family
        || text(definition, "semanticContractVersion") != version
        || text(definition, "semanticContractFingerprint") != scf
    {
        return false;
    }
    let resources = array(definition, "resourceManifest")
        .iter()
        .map(|m| {
            let key = text(m, "canonicalResourceKey");
            object([
                ("canonicalResourceKey".into(), string(key)),
                (
                    "content".into(),
                    sealed.get(key).cloned().unwrap_or(Json::Null),
                ),
            ])
        })
        .collect();
    semantic_contract::validate_closure(&object([
        ("definition".into(), definition.clone()),
        ("resources".into(), Json::Array(resources)),
    ]))
    .get("closure_valid")
    .and_then(Json::as_bool)
        == Some(true)
}

pub(crate) fn authority_qualifies(definition: &Json, resources: &[Json], nm_definition: &Json) -> bool {
    let expected = PROFILE.expected();
    if !definition_qualifies(
        definition,
        "authoring-construction",
        expected.acc_version,
        expected.acc_scf,
        &manifest_resources(definition, resources),
    ) {
        return false;
    }
    let sealed = manifest_resources(definition, resources);
    let ai = sealed.get(expected.ai_contract).unwrap_or(&Json::Null);
    definition_qualifies(
        ai,
        "architecture-interpretation",
        expected.ai_version,
        expected.ai_scf,
        &sealed,
    ) && definition_qualifies(
        nm_definition,
        "normalized-model",
        expected.nm_version,
        expected.nm_scf,
        &sealed,
    ) && schema_dialects(&sealed)
}

/// Inspect schema resources, not arbitrary JSON instance fields named $schema.
fn schema_dialects(sealed: &BTreeMap<String, Json>) -> bool {
    sealed
        .iter()
        .filter(|(key, _)| {
            key.contains("/schema/") || key.ends_with("/schema") || key.ends_with(".schema")
        })
        .all(|(_, schema)| {
            matches!(
                text(schema, "$schema"),
                "http://json-schema.org/draft-07/schema#"
                    | "https://json-schema.org/draft-07/schema#"
                    | "https://json-schema.org/draft/2020-12/schema"
            )
        })
}

/// Qualifies governing ownership only. Produces no inherited lifecycle value,
/// contextual fact, normalized entity or provenance carrier.
pub(crate) fn qualify_ownership(
    definition: &Json,
    sealed: &BTreeMap<String, Json>,
    row: &Json,
) -> bool {
    let authority = at(row, &["ai_ownership_authority"]);
    let expected = PROFILE.expected();
    let Some(ownership) = sealed.get(OWNERSHIP) else {
        return false;
    };
    if text(authority, "family") != "architecture-interpretation"
        || text(authority, "version") != expected.ai_version
        || text(authority, "semantic_contract_fingerprint") != expected.ai_scf
        || text(authority, "canonical_resource_key") != OWNERSHIP
        || !qualified_resource(definition, sealed, authority)
        || !definition_qualifies(
            sealed.get(expected.ai_contract).unwrap_or(&Json::Null),
            "architecture-interpretation",
            expected.ai_version,
            expected.ai_scf,
            sealed,
        )
        || schema_validation::preflight_fragment(sealed, OWNERSHIP_SCHEMA, "").is_err()
        || schema_validation::validate(sealed, OWNERSHIP_SCHEMA, ownership).is_err()
    {
        return false;
    }
    let rules: Vec<_> = array(ownership, "rows")
        .iter()
        .filter(|r| text(r, "rule_id") == text(authority, "rule_id"))
        .collect();
    let [rule] = rules.as_slice() else {
        return false;
    };
    if at(rule, &["parent_schema"]) != at(row, &["parent_schema"])
        || at(rule, &["child_schema"]) != at(row, &["child_schema"])
        || text(rule, "parent_semantic_type") != text(row, "parent_semantic_type")
        || text(rule, "declaring_adr_semantic_type") != text(row, "parent_semantic_type")
        || text(rule, "child_semantic_type") != text(row, "child_semantic_type")
        || text(rule, "source_instance_pattern") != format!("{}/*", text(row, "parent_pointer"))
        || text(rule, "declaring_adr_identity_selector") != "/id"
        || text(rule, "parent_identity_selector") != "/id"
        || text(rule, "child_identity_selector") != "/id"
        || text(rule, "governing_rule") != text(at(ownership, &["rules"]), "lifecycle")
        || text(rule, "canonical_identity") != "preserve_established_uuidv7"
    {
        return false;
    }
    let status = at(rule, &["status_source_authority"]);
    if text(status, "family") != "authoring"
        || text(status, "version") != "1.7"
        || !qualified_resource(definition, sealed, status)
        || text(status, "canonical_resource_key")
            != text(at(rule, &["source_schema"]), "canonical_resource_key")
    {
        return false;
    }
    let key = text(status, "canonical_resource_key");
    let selector = format!("#{}", text(status, "schema_pointer"));
    schema_validation::resolve_reference(sealed, key, &selector).is_ok()
        && array(rule, "ownership_schema_path").iter().all(|step| {
            qualified_resource(definition, sealed, step)
                && schema_validation::resolve_reference(
                    sealed,
                    text(step, "canonical_resource_key"),
                    &format!("#{}", text(step, "schema_pointer")),
                )
                .is_ok()
        })
}

fn initial(
    definition: &Json,
    resources: &[Json],
    nm_definition: &Json,
    request: &Json,
) -> SealResult {
    let q = producer::qualify_for(PROFILE, definition, resources, request);
    let authority_ok = authority_qualifies(definition, resources, nm_definition);
    let mut result = SealResult {
        authority: if authority_ok
            && q.authority == Check::Qualified
            && q.binding_table == Check::Qualified
        {
            Check::Qualified
        } else {
            Check::Unavailable
        },
        status: SealStatus::Unavailable,
        evidence: None,
        composition_records: Vec::new(),
        diagnostics: q.diagnostics,
        outstanding_dependencies: q.outstanding_dependencies,
        receipts: None,
    };
    if !authority_ok {
        result.issue(
            Status::Unavailable,
            "authority",
            "Exact ACC 1.3, AI 1.3, NM 2.5 closures or schema dialects unavailable",
        );
    }
    if authority_ok && result.diagnostics.is_empty() {
        if let Err(error) = schema_validation::preflight_fragment(
            &manifest_resources(definition, resources),
            PROFILE.expected().schema,
            "/$defs/uuid_v7",
        ) {
            result.issue(Status::Unavailable, "identity", &error.message);
        } else {
            for fragment in array(at(request, &["request"]), "fragments") {
                if let Some(id) = at(fragment, &["fields"]).get("id") {
                    if let Err(error) = schema_validation::validate_fragment(
                        &manifest_resources(definition, resources),
                        PROFILE.expected().schema,
                        "/$defs/uuid_v7",
                        id,
                    ) {
                        result.diagnostics.push(Diagnostic {
                            status: Status::Rejected,
                            code: "authoring_construction.authoring.invalid".into(),
                            semantic_identity: None,
                            field_or_relation_key: format!("{}.id", text(fragment, "request_key")),
                            payload: string(error.message),
                        });
                    }
                }
            }
        }
    }
    result
}

pub(crate) fn prepare(
    definition: &Json,
    resources: &[Json],
    nm_definition: &Json,
    request: &Json,
    source_refs: &BTreeMap<String, String>,
    minter: &mut dyn IdentityMinter,
) -> SealResult {
    let mut result = initial(definition, resources, nm_definition, request);
    if !result.diagnostics.is_empty() || result.authority != Check::Qualified {
        return result.finish();
    }
    let insertion = insertion::insert_for(PROFILE, definition, resources, request, minter);
    if insertion.status != insertion::InsertionStatus::PreservationProven {
        result
            .diagnostics
            .extend(insertion.qualification.diagnostics.clone());
        if result.diagnostics.is_empty() {
            result.issue(
                Status::Rejected,
                "insertion",
                "Independently established child or parent preservation violation",
            );
        }
        return result.finish();
    }
    let roots = sources::prepare_for(PROFILE, definition, resources, &insertion, source_refs);
    if roots.status != sources::AccountingStatus::RootsAccounted {
        result.diagnostics.extend(roots.diagnostics);
        return result.finish();
    }
    let dependencies =
        dependencies::qualify_dependencies_for(PROFILE, definition, resources, &insertion, &roots);
    if dependencies.status != dependencies::DependencyStatus::DependenciesQualified {
        result.diagnostics.extend(dependencies.diagnostics);
        return result.finish();
    }
    let records = records::assemble_for(
        PROFILE,
        definition,
        resources,
        &insertion,
        &roots,
        &dependencies,
    );
    let sealed = sealing::prepare_for(
        PROFILE,
        definition,
        resources,
        &insertion,
        &roots,
        &dependencies,
        &records,
    );
    result.diagnostics.extend(sealed.diagnostics);
    result.outstanding_dependencies = sealed.outstanding_dependencies;
    if sealed.status == sealing::SealingStatus::Sealed {
        result.status = SealStatus::Sealed;
        result.evidence = sealed.evidence;
        result.composition_records = records.records.clone();
        result.receipts = Some(Receipts {
            insertion,
            roots,
            dependencies,
            records,
            source_refs: source_refs.clone(),
        });
    }
    result.finish()
}

/// Replay with established identities only. There is deliberately no minter.
pub(crate) fn verify(
    definition: &Json,
    resources: &[Json],
    nm_definition: &Json,
    request: &Json,
    source_refs: &BTreeMap<String, String>,
    supplied: &SealResult,
) -> SealResult {
    let mut result = initial(definition, resources, nm_definition, request);
    if !result.diagnostics.is_empty() || result.authority != Check::Qualified {
        return result.finish();
    }
    let Some(receipts) = &supplied.receipts else {
        result.issue(
            Status::Rejected,
            "receipts",
            "Private successor producer receipts are required",
        );
        return result.finish();
    };
    if !receipts.insertion.matches_request(request) || &receipts.source_refs != source_refs {
        result.issue(
            Status::Rejected,
            "request",
            "Request or source references differ from producer commitments",
        );
    }
    let checked = sealing::prepare_for(
        PROFILE,
        definition,
        resources,
        &receipts.insertion,
        &receipts.roots,
        &receipts.dependencies,
        &receipts.records,
    );
    result.diagnostics.extend(checked.diagnostics);
    result.outstanding_dependencies = checked.outstanding_dependencies;
    if checked.status == sealing::SealingStatus::Sealed {
        result.status = SealStatus::Sealed;
        result.evidence = checked.evidence;
        result.composition_records = receipts.records.records.clone();
        result.receipts = Some(receipts.clone());
        if &result != supplied {
            result.issue(
                Status::Rejected,
                "sealed_evidence",
                "Supplied seal, authority, records or context differs from independent replay",
            );
        }
    }
    result.finish()
}

#[cfg(test)]
#[path = "authoring_construction_v13_tests.rs"]
pub(crate) mod tests;
