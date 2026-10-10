//! ACC 1.1 detached candidate-basis preparation.
//!
//! This operation stops before NM 2.4 interpretation and whole-ledger
//! qualification. It uses the ACC 1.1 request and evidence vocabulary, and
//! deliberately leaves composition-bearing requests unavailable until the
//! published result model can carry auditable composition-resolution proof.

use std::collections::{BTreeMap, BTreeSet};

use sha2::{Digest, Sha256};

use super::{
    authoring_construction_orchestration as orchestration, authoring_construction_v11,
    candidate_source, object, schema_validation, string, Json,
};

const OPERATION: &str = "prepare_authoring_construction_basis_1_1";
const ACC_FINGERPRINT: &str =
    "scf:v1:sha256:dcb38e2247396759ed3cbf0ee308ba4c02c087bf47599e72a342cc5efe6a79c5";
const AI12_FINGERPRINT: &str =
    "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a";
const SCHEMA_KEY: &str = "authoring-construction/1.1/schema";
const RULES_KEY: &str = "authoring-construction/1.1/rules";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum BasisStatus {
    Sealed,
    Rejected,
    Unavailable,
    Unresolved,
}

impl BasisStatus {
    fn as_str(self) -> &'static str {
        match self {
            Self::Sealed => "Sealed",
            Self::Rejected => "Rejected",
            Self::Unavailable => "Unavailable",
            Self::Unresolved => "Unresolved",
        }
    }
}

pub(crate) fn execute(request: &Json, minter: &mut dyn orchestration::IdentityMinter) -> Json {
    let Some(root) = request.as_object() else {
        return invalid_request("protocol 1.5 request payload must be an object");
    };
    if root.get("operation").and_then(Json::as_str) != Some(OPERATION) {
        return invalid_request("operation must be prepare_authoring_construction_basis_1_1");
    }

    let definition = root.get("definition").and_then(Json::as_object);
    let resources = root.get("resources").and_then(Json::as_array);
    let construction_request = root.get("construction_request");
    let mut authority_diagnostics = Vec::new();
    let authority_available = if let (Some(definition), Some(resources)) = (definition, resources) {
        authoring_construction_v11::qualify_authority(
            definition,
            resources,
            &mut authority_diagnostics,
        )
    } else {
        authority_diagnostics.push(core_diagnostic(
            "semantic_contract.invalid_request",
            "definition and resources are required for exact ACC 1.1 qualification",
            "authority",
        ));
        false
    };

    let mut diagnostics = Vec::new();
    let mut candidate_fragments = Vec::new();
    let mut candidate_artifacts = Vec::new();
    let mut construction_map = Vec::new();
    let mut source_basis = Json::Null;
    let mut detached_context = Json::Null;
    let mut status = BasisStatus::Unavailable;
    let mut request_schema_validated = false;
    let mut dependency_resolution_complete = false;

    if authority_available {
        match construction_request {
            Some(construction_request) => {
                if let Some(schema) =
                    resources.and_then(|items| resource_content(items, SCHEMA_KEY))
                {
                    let schema_resources =
                        BTreeMap::from([(SCHEMA_KEY.to_owned(), schema.clone())]);
                    match schema_validation::validate(
                        &schema_resources,
                        SCHEMA_KEY,
                        construction_request,
                    ) {
                        Ok(()) => {
                            request_schema_validated = true;
                            status = prepare(
                                construction_request,
                                definition.expect("authority was qualified from a definition"),
                                resources.expect("authority was qualified from resources"),
                                minter,
                                &mut diagnostics,
                                &mut candidate_fragments,
                                &mut candidate_artifacts,
                                &mut construction_map,
                                &mut source_basis,
                                &mut detached_context,
                                &mut dependency_resolution_complete,
                            );
                        }
                        Err(error) => {
                            status = BasisStatus::Rejected;
                            diagnostics.push(acc_diagnostic(
                                "authoring_construction.request.schema",
                                "violation",
                                &format!("/construction_request{}", error.path),
                                "schema-valid ACC 1.1 construction request",
                                &error.message,
                                "Correct the construction request using the exact ACC 1.1 schema.",
                            ));
                        }
                    }
                } else {
                    diagnostics.push(acc_diagnostic(
                        "authoring_construction.authority.unavailable",
                        "unavailable",
                        "/authority/resources",
                        "the schema resource in the verified ACC 1.1 closure",
                        "schema resource is unavailable",
                        "Supply the complete exact ACC 1.1 resource closure.",
                    ));
                }
            }
            None => {
                status = BasisStatus::Rejected;
                diagnostics.push(acc_diagnostic(
                    "authoring_construction.request.schema",
                    "violation",
                    "/construction_request",
                    "ACC 1.1 construction request",
                    "missing construction_request",
                    "Supply a construction request governed by ACC 1.1.",
                ));
            }
        }
    } else {
        diagnostics.push(acc_diagnostic(
            "authoring_construction.authority.unavailable",
            "unavailable",
            "/authority",
            "exact, integrity-qualified ACC 1.1 authority and dependency closure",
            "authority qualification failed",
            "Supply the exact ACC 1.1 authority and complete unmodified resource closure.",
        ));
    }

    sort_diagnostics(&mut diagnostics);
    sort_diagnostics(&mut authority_diagnostics);
    object([
        ("operation".into(), string(OPERATION)),
        ("contract_family".into(), string("authoring_construction")),
        ("contract_version".into(), string("1.1")),
        (
            "authority".into(),
            object([
                ("available".into(), Json::Bool(authority_available)),
                (
                    "fingerprint".into(),
                    definition
                        .and_then(|value| value.get("semanticContractFingerprint"))
                        .cloned()
                        .unwrap_or(Json::Null),
                ),
                (
                    "architecture_interpretation_fingerprint".into(),
                    definition
                        .and_then(|value| value.get("resourceManifest").and_then(Json::as_array))
                        .and_then(|_| resources)
                        .and_then(|items| {
                            resource_content(items, "architecture-interpretation/1.2/contract")
                        })
                        .and_then(Json::as_object)
                        .and_then(|contract| contract.get("semanticContractFingerprint"))
                        .cloned()
                        .unwrap_or(Json::Null),
                ),
            ]),
        ),
        (
            "capabilities".into(),
            capability_report(authority_available, request_schema_validated),
        ),
        ("success".into(), Json::Bool(status == BasisStatus::Sealed)),
        ("basis_status".into(), string(status.as_str())),
        ("diagnostics".into(), Json::Array(diagnostics)),
        (
            "authority_diagnostics".into(),
            Json::Array(authority_diagnostics),
        ),
        ("construction_map".into(), Json::Array(construction_map)),
        (
            "candidate_fragments".into(),
            Json::Array(candidate_fragments),
        ),
        (
            "candidate_artifacts".into(),
            Json::Array(candidate_artifacts),
        ),
        ("candidate_source_basis".into(), source_basis),
        ("detached_context".into(), detached_context),
        (
            "dependency_resolution_complete".into(),
            Json::Bool(dependency_resolution_complete),
        ),
    ])
}

#[allow(clippy::too_many_arguments)]
fn prepare(
    request: &Json,
    definition: &BTreeMap<String, Json>,
    resources: &[Json],
    minter: &mut dyn orchestration::IdentityMinter,
    diagnostics: &mut Vec<Json>,
    candidate_fragments: &mut Vec<Json>,
    candidate_artifacts: &mut Vec<Json>,
    construction_map: &mut Vec<Json>,
    source_basis: &mut Json,
    detached_context: &mut Json,
    dependency_resolution_complete: &mut bool,
) -> BasisStatus {
    let Some(request_root) = request.as_object() else {
        return BasisStatus::Rejected;
    };
    let Some(basis) = request_root.get("basis").and_then(Json::as_object) else {
        diagnostics.push(acc_diagnostic(
            "authoring_construction.authority.unavailable",
            "unavailable",
            "/construction_request/basis",
            "exact ACC 1.1 dependency qualifications",
            "request basis is missing",
            "Supply the exact version-qualified ACC 1.1 basis and resource closures.",
        ));
        return BasisStatus::Unavailable;
    };
    if !qualify_request_basis(basis, definition, resources) {
        diagnostics.push(acc_diagnostic(
            "authoring_construction.authority.unavailable",
            "unavailable",
            "/construction_request/basis",
            "exact ACC 1.1, AI 1.2, Authoring Domain 1.1, Authoring 1.7, and NM 2.4 identities and closures",
            "request basis does not match the exact selected authority",
            "Supply the exact authority identities and manifest-derived resource closures.",
        ));
        return BasisStatus::Unavailable;
    }

    let request_body = request_root.get("request").and_then(Json::as_object);
    let fragments = request_body
        .and_then(|body| body.get("fragments"))
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    let relationships = request_body
        .and_then(|body| body.get("relationships"))
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    let compositions = request_body
        .and_then(|body| body.get("compositions"))
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default();
    let fragment_composition_keys = fragments.iter().any(|fragment| {
        fragment
            .as_object()
            .and_then(|item| item.get("composition_keys"))
            .and_then(Json::as_array)
            .is_some_and(|keys| !keys.is_empty())
    });

    let mut status = BasisStatus::Sealed;
    if !compositions.is_empty() || fragment_composition_keys {
        status = BasisStatus::Unavailable;
        diagnostics.push(acc_diagnostic(
            "authoring_construction.composition.evidence_unavailable",
            "unavailable",
            "/construction_request/request/compositions",
            "complete ACC-shaped composition resolution evidence",
            "ACC 1.1 does not define a composition-resolution evidence record for this intermediate result",
            "Composition-bearing bases remain unavailable until accepted ACC evidence can preserve both endpoint identities and the governing basis.",
        ));
    }
    if !relationships.is_empty()
        || fragments.iter().any(|fragment| {
            fragment
                .as_object()
                .and_then(|item| item.get("semantic_type"))
                .and_then(Json::as_str)
                .is_some_and(|semantic_type| semantic_type.contains(':'))
        })
    {
        status = max_status(status, BasisStatus::Unavailable);
        diagnostics.push(acc_diagnostic(
            "authoring_construction.dependency.capability_unavailable",
            "unavailable",
            "/construction_request/request",
            "qualified canonical/custom relationship and CEC 1.0 dependency handling",
            "relationship or custom semantic execution is outside this independently complete sub-capability",
            "Use only supported built-in create fragments and request-local or exact reference-basis references.",
        ));
    }
    if basis
        .get("custom_entity")
        .is_some_and(|value| !matches!(value, Json::Null))
    {
        status = max_status(status, BasisStatus::Unavailable);
        diagnostics.push(acc_diagnostic(
            "authoring_construction.custom.authority_unavailable",
            "unavailable",
            "/construction_request/basis/custom_entity",
            "complete exact CEC 1.0 qualified registry execution",
            "custom entity qualification is not executable in this slice",
            "Use a built-in Authoring 1.7 semantic type or wait for CEC-qualified execution support.",
        ));
    }

    let mut fragment_by_key = BTreeMap::<String, &Json>::new();
    let mut identity_order = fragments
        .iter()
        .enumerate()
        .filter_map(|(index, fragment)| {
            let key = fragment
                .as_object()?
                .get("request_key")?
                .as_str()?
                .to_owned();
            Some((key, index))
        })
        .collect::<Vec<_>>();
    identity_order.sort_by(|left, right| left.0.cmp(&right.0));
    for (_, index) in identity_order {
        let fragment = &fragments[index];
        let Some(value) = fragment.as_object() else {
            continue;
        };
        let Some(key) = value.get("request_key").and_then(Json::as_str) else {
            continue;
        };
        if fragment_by_key.insert(key.to_owned(), fragment).is_some() {
            status = max_status(status, BasisStatus::Rejected);
            diagnostics.push(acc_diagnostic(
                "authoring_construction.request.duplicate_key",
                "violation",
                &format!("/construction_request/request/fragments/{index}/request_key"),
                "unique request_key for each semantic unit",
                key,
                "Assign a unique request_key to every fragment.",
            ));
        }
    }

    let mut identities = BTreeMap::<String, orchestration::Identity>::new();
    let mut identity_index = BTreeMap::<String, String>::new();
    let authoring_qualification = basis.get("authoring").cloned().unwrap_or(Json::Null);
    let mut identity_order = fragments
        .iter()
        .enumerate()
        .filter_map(|(index, fragment)| {
            let key = fragment
                .as_object()?
                .get("request_key")?
                .as_str()?
                .to_owned();
            Some((key, index))
        })
        .collect::<Vec<_>>();
    identity_order.sort_by(|left, right| left.0.cmp(&right.0));
    for (_, index) in identity_order {
        let fragment = &fragments[index];
        let Some(value) = fragment.as_object() else {
            continue;
        };
        let Some(key) = value.get("request_key").and_then(Json::as_str) else {
            continue;
        };
        let operation = value
            .get("operation")
            .and_then(Json::as_str)
            .unwrap_or("create");
        if value.get("contract_qualification") != Some(&authoring_qualification) {
            status = max_status(status, BasisStatus::Unavailable);
            diagnostics.push(acc_diagnostic(
                "authoring_construction.fragment.authority_unavailable",
                "unavailable",
                &format!("/construction_request/request/fragments/{index}/contract_qualification"),
                "the exact selected Authoring 1.7 resource-set qualification",
                "fragment qualification is absent or differs from the selected Authoring basis",
                "Qualify the fragment against the exact Authoring 1.7 closure.",
            ));
        }
        let supplied = value
            .get("fields")
            .and_then(Json::as_object)
            .and_then(|fields| fields.get("id"))
            .and_then(Json::as_str);
        if supplied.is_some_and(|identity| !is_uuid_v7(identity)) {
            status = max_status(status, BasisStatus::Rejected);
            diagnostics.push(acc_diagnostic(
                "authoring_construction.identity.invalid",
                "violation",
                &format!("/construction_request/request/fragments/{index}/fields/id"),
                "canonical lower-case UUIDv7",
                supplied.unwrap_or_default(),
                "Supply a valid canonical UUIDv7 identity.",
            ));
            continue;
        }
        if operation != "create" && supplied.is_none() {
            let is_update = operation == "update";
            let next = if is_update {
                BasisStatus::Rejected
            } else {
                BasisStatus::Unavailable
            };
            status = max_status(status, next);
            diagnostics.push(acc_diagnostic(
                if is_update {
                    "authoring_construction.identity.update_missing"
                } else {
                    "authoring_construction.identity.operation_unavailable"
                },
                if is_update {
                    "violation"
                } else {
                    "unavailable"
                },
                &format!("/construction_request/request/fragments/{index}/fields/id"),
                "preserved UUIDv7 for a non-create operation",
                "identity is absent",
                "Supply a preserved identity or use the supported create operation.",
            ));
            continue;
        }
        if operation != "create" {
            status = max_status(status, BasisStatus::Unavailable);
            diagnostics.push(acc_diagnostic(
                "authoring_construction.operation.unavailable",
                "unavailable",
                &format!("/construction_request/request/fragments/{index}/operation"),
                "create operation in the supported detached-basis slice",
                operation,
                "Use create or wait for update, reference, and retire execution support.",
            ));
            continue;
        }
        match orchestration::establish_identity(key, operation, supplied, minter) {
            Ok(identity) => {
                if let Some(first) = identity_index.insert(identity.id.clone(), key.to_owned()) {
                    status = max_status(status, BasisStatus::Rejected);
                    diagnostics.push(acc_diagnostic(
                        "authoring_construction.identity.duplicate",
                        "violation",
                        &format!("/construction_request/request/fragments/{index}/fields/id"),
                        "one canonical UUIDv7 per semantic unit",
                        format!("duplicate identity {} is also used by {first}", identity.id),
                        "Assign distinct canonical UUIDv7 identities.",
                    ));
                }
                identities.insert(key.to_owned(), identity);
            }
            Err(error) => {
                status = max_status(status, BasisStatus::Unavailable);
                diagnostics.push(acc_diagnostic(
                    "authoring_construction.identity.unavailable",
                    "unavailable",
                    &format!("/construction_request/request/fragments/{index}/fields/id"),
                    "ACC-governed UUIDv7 identity establishment",
                    error,
                    "Retry identity minting or supply a valid UUIDv7 for a create fragment.",
                ));
            }
        }
    }

    let resolved_by_fragment = resolve_references(
        &fragments,
        &fragment_by_key,
        &identities,
        basis,
        diagnostics,
        &mut status,
    );
    *dependency_resolution_complete = status == BasisStatus::Sealed;
    if status != BasisStatus::Sealed {
        return status;
    }

    let mut artifacts = Vec::new();
    let empty_compositions = Vec::new();
    for (index, fragment) in fragments.iter().enumerate() {
        let Some(value) = fragment.as_object() else {
            continue;
        };
        let Some(key) = value.get("request_key").and_then(Json::as_str) else {
            continue;
        };
        let Some(identity) = identities.get(key) else {
            continue;
        };
        let semantic_type = value
            .get("semantic_type")
            .and_then(Json::as_str)
            .unwrap_or_default();
        let fields = value
            .get("fields")
            .and_then(Json::as_object)
            .cloned()
            .unwrap_or_default();
        let mut embedded_children = Vec::new();
        let source = orchestration::build_fragment_source(
            value,
            &fields,
            identity,
            semantic_type,
            key,
            &identities,
            &fragments,
            &empty_compositions,
            &mut embedded_children,
        );
        let selector = orchestration::selector_for(semantic_type, &source);
        let artifact_kind = if value.get("semantic_kind").and_then(Json::as_str) == Some("adr") {
            "authoring_document"
        } else {
            "authoring_fragment"
        };
        let source_ref = format!("candidate/{key}");
        match candidate_source::seal_candidate_artifact(
            key,
            &source_ref,
            artifact_kind,
            selector,
            authoring_qualification.clone(),
            &source,
        ) {
            Ok(artifact) => match candidate_source::decode_and_validate_candidate(&artifact) {
                Ok(_) => {
                    let fragment_qualification = value
                        .get("contract_qualification")
                        .unwrap_or(&authoring_qualification);
                    let resolved_references = resolved_by_fragment
                        .get(key)
                        .cloned()
                        .unwrap_or_else(|| Json::Array(Vec::new()));
                    let output = candidate_fragment(
                        value,
                        source.as_object().unwrap_or(&fields),
                        identity,
                        fragment_qualification,
                        &authoring_qualification,
                        &resolved_references,
                    );
                    candidate_fragments.push(output);
                    construction_map.push(map_entry(
                        key,
                        semantic_type,
                        identity,
                        &authoring_qualification,
                        &source_ref,
                    ));
                    candidate_artifacts.push(orchestration::artifact_to_json(&artifact));
                    artifacts.push(artifact);
                }
                Err(error) => {
                    status = max_status(status, BasisStatus::Rejected);
                    diagnostics.push(acc_diagnostic(
                        "authoring_construction.authoring.invalid",
                        "violation",
                        &format!("/construction_request/request/fragments/{index}/fields"),
                        "Authoring 1.7 schema-valid candidate source",
                        error,
                        "Correct the fragment using its exact Authoring 1.7 schema.",
                    ));
                }
            },
            Err(error) => {
                status = max_status(status, BasisStatus::Unavailable);
                diagnostics.push(acc_diagnostic(
                    "authoring_construction.candidate_source.unavailable",
                    "unavailable",
                    &format!("/construction_request/request/fragments/{index}"),
                    "deterministically serializable Authoring 1.7 candidate source",
                    error,
                    "Supply source fields that the exact Authoring 1.7 serializer can qualify.",
                ));
            }
        }
    }
    if status != BasisStatus::Sealed {
        return status;
    }
    sort_json_by_string(candidate_fragments, "request_key");
    sort_json_by_string(candidate_artifacts, "request_key");
    sort_json_by_string(construction_map, "request_key");
    if artifacts.len() != fragments.len() || artifacts.is_empty() {
        diagnostics.push(acc_diagnostic(
            "authoring_construction.candidate_source.incomplete",
            "unavailable",
            "/construction_request/request/fragments",
            "one integrity-qualified artifact for every candidate fragment",
            "candidate artifact set is incomplete or empty",
            "Supply a non-empty candidate set whose every fragment serializes and validates.",
        ));
        return BasisStatus::Unavailable;
    }
    let roots = match candidate_source::select_minimal_candidate_source_roots(artifacts, &[]) {
        Ok(roots) => roots,
        Err(error) => {
            diagnostics.push(acc_diagnostic(
                "authoring_construction.candidate_source.roots_unavailable",
                "unavailable",
                "/construction_request/request/fragments",
                "complete minimal non-overlapping candidate roots",
                error,
                "Supply a candidate set with one unambiguous native root per standalone unit.",
            ));
            return BasisStatus::Unavailable;
        }
    };
    let sealed = match candidate_source::seal_candidate_source_basis(roots) {
        Ok(sealed) => sealed,
        Err(error) => {
            diagnostics.push(acc_diagnostic(
                "authoring_construction.candidate_source.seal_unavailable",
                "unavailable",
                "/construction_request/request/fragments",
                "integrity-qualified deterministic candidate source basis",
                error,
                "Correct source references and exact serialized bytes before sealing.",
            ));
            return BasisStatus::Unavailable;
        }
    };
    let roots_json = Json::Array(
        sealed
            .artifacts
            .iter()
            .map(|artifact| string(artifact.source_ref.clone()))
            .collect(),
    );
    let root = format!(
        "urn:adr-kit:detached-candidate:v1:source-basis:sha256:{}",
        sealed.basis_digest.trim_start_matches("sha256:")
    );
    let locators = sealed
        .artifacts
        .iter()
        .map(|artifact| {
            string(format!(
                "{root}/root:sha256:{}",
                sha256_hex(artifact.source_ref.as_bytes())
            ))
        })
        .collect::<Vec<_>>();
    *source_basis = basis_to_json(&sealed, &authoring_qualification);
    *detached_context = object([
        ("scope_root".into(), string(root)),
        ("root_artifact_locators".into(), Json::Array(locators)),
        ("selected_root_source_refs".into(), roots_json),
    ]);
    BasisStatus::Sealed
}

fn resolve_references(
    fragments: &[Json],
    fragment_by_key: &BTreeMap<String, &Json>,
    identities: &BTreeMap<String, orchestration::Identity>,
    basis: &BTreeMap<String, Json>,
    diagnostics: &mut Vec<Json>,
    status: &mut BasisStatus,
) -> BTreeMap<String, Json> {
    let mut result = BTreeMap::new();
    for (fragment_index, fragment) in fragments.iter().enumerate() {
        let Some(value) = fragment.as_object() else {
            continue;
        };
        let Some(source_key) = value.get("request_key").and_then(Json::as_str) else {
            continue;
        };
        let mut records = Vec::new();
        let mut reference_keys = BTreeSet::new();
        for (reference_index, reference) in value
            .get("references")
            .and_then(Json::as_array)
            .into_iter()
            .flatten()
            .enumerate()
        {
            let Some(reference) = reference.as_object() else {
                continue;
            };
            let reference_key = reference
                .get("reference_key")
                .and_then(Json::as_str)
                .unwrap_or_default();
            let location = format!(
                "/construction_request/request/fragments/{fragment_index}/references/{reference_index}"
            );
            if !reference_keys.insert(reference_key.to_owned()) {
                *status = max_status(*status, BasisStatus::Rejected);
                diagnostics.push(acc_diagnostic(
                    "authoring_construction.reference.duplicate_key",
                    "violation",
                    &format!("{location}/reference_key"),
                    "unique reference_key within its source semantic unit",
                    reference_key,
                    "Assign a unique reference_key to every governed dependency.",
                ));
                continue;
            }
            let target = reference
                .get("target")
                .and_then(Json::as_str)
                .unwrap_or_default();
            let kind = reference
                .get("reference_kind")
                .and_then(Json::as_str)
                .unwrap_or_default();
            let resolved = if kind == "request" {
                match (fragment_by_key.get(target), identities.get(target)) {
                    (Some(target_fragment), Some(identity)) => {
                        let target_object = target_fragment.as_object().expect("indexed object");
                        Some((
                            identity.id.clone(),
                            target_object
                                .get("semantic_type")
                                .cloned()
                                .unwrap_or(Json::Null),
                            target_object
                                .get("contract_qualification")
                                .cloned()
                                .unwrap_or(Json::Null),
                            "resolved",
                        ))
                    }
                    _ => None,
                }
            } else {
                let matches = basis
                    .get("reference_basis")
                    .and_then(Json::as_object)
                    .and_then(|reference_basis| reference_basis.get("entries"))
                    .and_then(Json::as_array)
                    .into_iter()
                    .flatten()
                    .filter_map(Json::as_object)
                    .filter(|entry| {
                        entry.get("reference_id").and_then(Json::as_str) == Some(target)
                    })
                    .collect::<Vec<_>>();
                if matches.len() == 1 {
                    let entry = matches[0];
                    Some((
                        entry
                            .get("canonical_uuid")
                            .and_then(Json::as_str)
                            .unwrap_or_default()
                            .to_owned(),
                        entry.get("semantic_type").cloned().unwrap_or(Json::Null),
                        entry.get("qualification").cloned().unwrap_or(Json::Null),
                        "reused",
                    ))
                } else {
                    None
                }
            };
            let Some((canonical_uuid, semantic_type, qualification, disposition)) = resolved else {
                *status = max_status(*status, BasisStatus::Unresolved);
                diagnostics.push(acc_diagnostic(
                    "authoring_construction.reference.unresolved",
                    "unresolved",
                    &location,
                    "one governed request-local or sealed reference-basis target",
                    format!("{kind} target {target:?} has no unique qualified semantic identity"),
                    "Supply exactly one target in the governed candidate or sealed reference basis.",
                ));
                continue;
            };
            if !is_uuid_v7(&canonical_uuid) {
                *status = max_status(*status, BasisStatus::Unavailable);
                diagnostics.push(acc_diagnostic(
                    "authoring_construction.reference.unqualified",
                    "unavailable",
                    &location,
                    "canonical UUIDv7 and exact target qualification",
                    "resolved target does not carry a valid canonical identity",
                    "Qualify the dependency with an exact UUIDv7 identity and semantic authority.",
                ));
                continue;
            }
            if qualification != *basis.get("authoring").unwrap_or(&Json::Null) {
                *status = max_status(*status, BasisStatus::Unavailable);
                diagnostics.push(acc_diagnostic(
                    "authoring_construction.reference.unqualified",
                    "unavailable",
                    &location,
                    "target qualification in the exact selected Authoring 1.7 closure",
                    "target qualification is outside the selected dependency basis",
                    "Supply a target qualified by the exact selected Authoring 1.7 closure.",
                ));
                continue;
            }
            let target_type = semantic_type.as_str().unwrap_or_default();
            let target_qualification = &qualification;
            let expected_type = reference
                .get("expected_semantic_type")
                .and_then(Json::as_str);
            let requested_qualification = reference.get("qualification");
            if expected_type.is_some_and(|expected| expected != target_type)
                || requested_qualification.is_some_and(|expected| expected != target_qualification)
            {
                *status = max_status(*status, BasisStatus::Rejected);
                diagnostics.push(acc_diagnostic(
                    "authoring_construction.reference.expectation_mismatch",
                    "violation",
                    &location,
                    "target semantic type and qualification match the declared expectation",
                    format!(
                        "resolved {target_type} with qualification {}",
                        serde_json::to_string(target_qualification).unwrap_or_default()
                    ),
                    "Correct the reference expectation or its qualified target.",
                ));
                continue;
            }
            records.push(object([
                ("reference_key".into(), string(reference_key)),
                ("reference_kind".into(), string(kind)),
                ("target".into(), string(target)),
                ("canonical_uuid".into(), string(canonical_uuid)),
                ("semantic_type".into(), semantic_type),
                ("qualification".into(), qualification),
                ("disposition".into(), string(disposition)),
            ]));
        }
        records.sort_by_key(|record| {
            record
                .get("reference_key")
                .and_then(Json::as_str)
                .unwrap_or_default()
                .to_owned()
        });
        result.insert(source_key.to_owned(), Json::Array(records));
    }
    result
}

fn qualify_request_basis(
    basis: &BTreeMap<String, Json>,
    definition: &BTreeMap<String, Json>,
    resources: &[Json],
) -> bool {
    let Some(acc) = basis.get("acc").and_then(Json::as_object) else {
        return false;
    };
    let exact_acc = acc.get("family").and_then(Json::as_str) == Some("authoring-construction")
        && acc.get("version").and_then(Json::as_str) == Some("1.1")
        && acc
            .get("semantic_contract_fingerprint")
            .and_then(Json::as_str)
            == Some(ACC_FINGERPRINT);
    let Some(rules) = resource_content(resources, RULES_KEY).and_then(Json::as_object) else {
        return false;
    };
    let Some(authority) = rules.get("authority").and_then(Json::as_object) else {
        return false;
    };
    let exact = exact_acc
        && exact_resource_set(
            basis.get("adc"),
            "authoring-domain",
            "1.1",
            definition,
            "authoring-domain/1.1/",
        )
        && exact_resource_set(
            basis.get("authoring"),
            "authoring",
            "1.7",
            definition,
            "authoring/1.7/schema/",
        )
        && exact_resource_set(
            basis.get("normalized_model"),
            "normalized-model",
            "2.4",
            definition,
            "normalized-model/2.4/schema/",
        )
        && exact_ai12(
            basis.get("architecture_interpretation"),
            definition,
            resources,
        )
        && authority
            .get("architecture_interpretation")
            .and_then(Json::as_object)
            .and_then(|value| value.get("fingerprint"))
            .and_then(Json::as_str)
            == Some(AI12_FINGERPRINT);
    exact
}

fn exact_ai12(
    value: Option<&Json>,
    definition: &BTreeMap<String, Json>,
    resources: &[Json],
) -> bool {
    let Some(value) = value.and_then(Json::as_object) else {
        return false;
    };
    if value.get("family").and_then(Json::as_str) != Some("architecture-interpretation")
        || value.get("version").and_then(Json::as_str) != Some("1.2")
        || value
            .get("semantic_contract_fingerprint")
            .and_then(Json::as_str)
            != Some(AI12_FINGERPRINT)
    {
        return false;
    }
    let ai_contract = resource_content(resources, "architecture-interpretation/1.2/contract")
        .and_then(Json::as_object);
    let expected = ai_contract.and_then(|contract| contract.get("resourceManifest"));
    let Some(expected) = expected.and_then(Json::as_array) else {
        return false;
    };
    let Some(closure) = value.get("authority_closure").and_then(Json::as_object) else {
        return false;
    };
    closure.get("family").and_then(Json::as_str) == Some("architecture-interpretation")
        && closure.get("version").and_then(Json::as_str) == Some("1.2")
        && resource_members_match(closure.get("resources"), expected)
        && definition
            .get("semanticContractFingerprint")
            .and_then(Json::as_str)
            == Some(ACC_FINGERPRINT)
}

fn exact_resource_set(
    value: Option<&Json>,
    family: &str,
    version: &str,
    definition: &BTreeMap<String, Json>,
    prefix: &str,
) -> bool {
    let Some(value) = value.and_then(Json::as_object) else {
        return false;
    };
    if value.get("family").and_then(Json::as_str) != Some(family)
        || value.get("version").and_then(Json::as_str) != Some(version)
    {
        return false;
    }
    let Some(manifest) = definition.get("resourceManifest").and_then(Json::as_array) else {
        return false;
    };
    let expected = manifest
        .iter()
        .filter_map(Json::as_object)
        .filter(|entry| {
            entry
                .get("canonicalResourceKey")
                .and_then(Json::as_str)
                .is_some_and(|key| key.starts_with(prefix))
        })
        .cloned()
        .map(|entry| {
            object([
                (
                    "canonicalResourceKey".into(),
                    entry
                        .get("canonicalResourceKey")
                        .cloned()
                        .unwrap_or(Json::Null),
                ),
                (
                    "contentDigest".into(),
                    entry.get("contentDigest").cloned().unwrap_or(Json::Null),
                ),
            ])
        })
        .collect::<Vec<_>>();
    !expected.is_empty() && resource_members_match(value.get("resources"), &expected)
}

fn resource_members_match(value: Option<&Json>, expected: &[Json]) -> bool {
    let Some(actual) = value.and_then(Json::as_array) else {
        return false;
    };
    fn key(value: &Json) -> Option<(&str, &str)> {
        let value = value.as_object()?;
        Some((
            value.get("canonical_resource_key")?.as_str()?,
            value.get("content_digest")?.as_str()?,
        ))
    }
    let mut actual_map = BTreeMap::new();
    for item in actual {
        let Some((name, digest)) = key(item) else {
            return false;
        };
        if actual_map.insert(name, digest).is_some() {
            return false;
        }
    }
    let mut expected_map = BTreeMap::new();
    for item in expected {
        let Some(value) = item.as_object() else {
            return false;
        };
        let Some((name, digest)) = value
            .get("canonicalResourceKey")
            .and_then(Json::as_str)
            .zip(value.get("contentDigest").and_then(Json::as_str))
        else {
            return false;
        };
        expected_map.insert(name, digest);
    }
    !expected_map.is_empty() && actual_map == expected_map
}

fn candidate_fragment(
    fragment: &BTreeMap<String, Json>,
    fields: &BTreeMap<String, Json>,
    identity: &orchestration::Identity,
    qualification: &Json,
    source_contract: &Json,
    resolved_references: &Json,
) -> Json {
    object([
        (
            "request_key".into(),
            fragment.get("request_key").cloned().unwrap_or(Json::Null),
        ),
        (
            "semantic_kind".into(),
            fragment.get("semantic_kind").cloned().unwrap_or(Json::Null),
        ),
        (
            "semantic_type".into(),
            fragment.get("semantic_type").cloned().unwrap_or(Json::Null),
        ),
        ("identity".into(), string(identity.id.clone())),
        ("contract_qualification".into(), qualification.clone()),
        ("fields".into(), Json::Object(fields.clone())),
        ("resolved_references".into(), resolved_references.clone()),
        ("source_contract".into(), source_contract.clone()),
    ])
}

fn map_entry(
    key: &str,
    semantic_type: &str,
    identity: &orchestration::Identity,
    qualification: &Json,
    source_ref: &str,
) -> Json {
    object([
        ("request_key".into(), string(key)),
        ("operation".into(), string("create")),
        ("semantic_type".into(), string(semantic_type)),
        ("canonical_uuid".into(), string(identity.id.clone())),
        ("identity_disposition".into(), string(identity.disposition)),
        ("candidate_source_ref".into(), string(source_ref)),
        ("contract_qualification".into(), qualification.clone()),
        ("resulting_state".into(), string("active")),
        ("diagnostic_codes".into(), Json::Array(Vec::new())),
    ])
}

fn basis_to_json(basis: &candidate_source::CandidateSourceBasis, source_contract: &Json) -> Json {
    object([
        ("sealed".into(), Json::Bool(true)),
        ("basis_digest".into(), string(basis.basis_digest.clone())),
        (
            "artifacts".into(),
            Json::Array(
                basis
                    .artifacts
                    .iter()
                    .map(orchestration::artifact_to_json)
                    .collect(),
            ),
        ),
        ("source_contract".into(), source_contract.clone()),
    ])
}

fn resource_content<'a>(resources: &'a [Json], key: &str) -> Option<&'a Json> {
    resources.iter().find_map(|resource| {
        let value = resource.as_object()?;
        (value.get("canonicalResourceKey").and_then(Json::as_str) == Some(key))
            .then(|| value.get("content"))
            .flatten()
    })
}

fn is_uuid_v7(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 36
        && [8, 13, 18, 23].iter().all(|index| bytes[*index] == b'-')
        && bytes
            .iter()
            .enumerate()
            .all(|(index, byte)| [8, 13, 18, 23].contains(&index) || byte.is_ascii_hexdigit())
        && bytes[14] == b'7'
        && matches!(bytes[19], b'8'..=b'b')
        && value.bytes().all(|byte| !byte.is_ascii_uppercase())
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn max_status(left: BasisStatus, right: BasisStatus) -> BasisStatus {
    fn rank(status: BasisStatus) -> u8 {
        match status {
            BasisStatus::Sealed => 0,
            BasisStatus::Unresolved => 1,
            BasisStatus::Unavailable => 2,
            BasisStatus::Rejected => 3,
        }
    }
    if rank(left) >= rank(right) {
        left
    } else {
        right
    }
}

fn sort_diagnostics(diagnostics: &mut [Json]) {
    diagnostics.sort_by_key(|value| serde_json::to_string(value).unwrap_or_default());
}

fn sort_json_by_string(values: &mut [Json], property: &str) {
    values.sort_by(|left, right| {
        left.get(property)
            .and_then(Json::as_str)
            .cmp(&right.get(property).and_then(Json::as_str))
    });
}

fn capability_report(authority_available: bool, request_schema_validated: bool) -> Json {
    object([
        (
            "exact_authority_qualification".into(),
            Json::Bool(authority_available),
        ),
        (
            "request_schema_validation".into(),
            Json::Bool(request_schema_validated),
        ),
        (
            "authoring_validation".into(),
            Json::Bool(authority_available),
        ),
        (
            "identity_establishment".into(),
            Json::Bool(authority_available),
        ),
        (
            "request_local_reference_resolution".into(),
            Json::Bool(authority_available),
        ),
        (
            "reference_basis_resolution".into(),
            Json::Bool(authority_available),
        ),
        ("composition_resolution".into(), Json::Bool(false)),
        (
            "candidate_source_basis_sealing".into(),
            Json::Bool(authority_available),
        ),
        ("complete_nm24_interpretation".into(), Json::Bool(false)),
        ("expected_ledger_derivation".into(), Json::Bool(false)),
        ("observed_ledger_derivation".into(), Json::Bool(false)),
        ("whole_ledger_comparison".into(), Json::Bool(false)),
        ("complete_acc11_qualification".into(), Json::Bool(false)),
        ("construct_authoring_set".into(), Json::Bool(false)),
    ])
}

fn core_diagnostic(code: &str, message: &str, path: &str) -> Json {
    object([
        ("code".into(), string(code)),
        ("message".into(), string(message)),
        ("path".into(), string(path)),
    ])
}

fn acc_diagnostic(
    code: &str,
    status: &str,
    location: &str,
    expected: &str,
    observed: impl Into<String>,
    remediation: &str,
) -> Json {
    object([
        ("code".into(), string(code)),
        ("severity".into(), string("error")),
        ("status".into(), string(status)),
        ("request_key".into(), Json::Null),
        ("location".into(), string(location)),
        ("semantic_type".into(), Json::Null),
        (
            "rule".into(),
            string("ACC 1.1 detached candidate-basis qualification"),
        ),
        ("expected".into(), string(expected)),
        ("observed".into(), string(observed)),
        ("remediation".into(), string(remediation)),
    ])
}

pub(crate) fn invalid_request(message: &str) -> Json {
    object([
        ("operation".into(), string(OPERATION)),
        ("contract_family".into(), string("authoring_construction")),
        ("contract_version".into(), string("1.1")),
        (
            "authority".into(),
            object([
                ("available".into(), Json::Bool(false)),
                ("fingerprint".into(), Json::Null),
                (
                    "architecture_interpretation_fingerprint".into(),
                    string(AI12_FINGERPRINT),
                ),
            ]),
        ),
        ("capabilities".into(), capability_report(false, false)),
        ("success".into(), Json::Bool(false)),
        ("basis_status".into(), string("Rejected")),
        (
            "diagnostics".into(),
            Json::Array(vec![acc_diagnostic(
                "authoring_construction.request.schema",
                "violation",
                "/request",
                "ACC 1.1 basis preparation request",
                message,
                "Supply an exact version-qualified ACC 1.1 basis preparation request.",
            )]),
        ),
        ("authority_diagnostics".into(), Json::Array(Vec::new())),
        ("construction_map".into(), Json::Array(Vec::new())),
        ("candidate_fragments".into(), Json::Array(Vec::new())),
        ("candidate_artifacts".into(), Json::Array(Vec::new())),
        ("candidate_source_basis".into(), Json::Null),
        ("detached_context".into(), Json::Null),
        ("dependency_resolution_complete".into(), Json::Bool(false)),
    ])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Default)]
    struct TestMinter(u16);

    impl orchestration::IdentityMinter for TestMinter {
        fn mint_uuidv7(&mut self) -> Result<String, String> {
            let index = self.0;
            self.0 += 1;
            Ok(format!("018f0000-0000-7000-8000-{index:012x}"))
        }
    }

    #[test]
    fn operation_does_not_advertise_complete_construction() {
        let request = object([("operation".into(), string(OPERATION))]);
        let result = execute(&request, &mut TestMinter::default());
        assert_eq!(
            result.get("basis_status").and_then(Json::as_str),
            Some("Unavailable")
        );
        assert_eq!(result.get("success").and_then(Json::as_bool), Some(false));
        assert_eq!(
            result
                .get("capabilities")
                .and_then(Json::as_object)
                .and_then(|value| value.get("construct_authoring_set"))
                .and_then(Json::as_bool),
            Some(false)
        );
        assert!(result.get("outcome").is_none());
    }

    #[test]
    fn uuidv7_qualification_is_canonical() {
        assert!(is_uuid_v7("018f0000-0000-7000-8000-000000000001"));
        assert!(!is_uuid_v7("018f0000-0000-4000-8000-000000000001"));
        assert!(!is_uuid_v7("018F0000-0000-7000-8000-000000000001"));
        assert!(!is_uuid_v7("018f0000-0000-7000-7000-000000000001"));
    }

    #[test]
    fn outcome_precedence_matches_acc11() {
        assert_eq!(
            max_status(BasisStatus::Unresolved, BasisStatus::Unavailable),
            BasisStatus::Unavailable
        );
        assert_eq!(
            max_status(BasisStatus::Unavailable, BasisStatus::Rejected),
            BasisStatus::Rejected
        );
        assert_eq!(
            max_status(BasisStatus::Sealed, BasisStatus::Unresolved),
            BasisStatus::Unresolved
        );
    }
}
