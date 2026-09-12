//! Semantic-contract profiles, qualification, and retained-set rules.
//!
//! This module deliberately operates on the byte-oriented JSON boundary.  The
//! profile, catalog, policy, and current pointer are inputs to the canonical
//! semantic operation; none of them becomes part of an SCF or SCS identity.
//! Hosts may persist the returned immutable artifact, but they may not replace
//! these checks with Python- or TypeScript-local policy interpretation.

use std::collections::{BTreeMap, BTreeSet};

use super::semantic_contract::{
    canonical_contract_set, contract_set_member_wire, is_scf, parse_contract_set_members,
    ContractSetMember, ContractSetMemberDiagnosticContext, SCS_SCHEME,
};
use super::{diagnostic, object, simple_result, string, Json};

const PROFILE_ID: &str = "architecture-materialization@1.0";
const PROFILE_FAMILY: &str = "architecture-materialization";
const PROFILE_VERSION: &str = "1.0";
const QUALIFICATION_VERSION: &str = "1.0";

fn is_scs(value: &str) -> bool {
    let Some(hex) = value.strip_prefix("scs:v1:sha256:") else {
        return false;
    };
    hex.len() == 64
        && hex
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn text(value: Option<&Json>) -> Option<String> {
    value.and_then(Json::as_str).map(str::to_owned)
}

fn array<'a>(value: Option<&'a Json>) -> Option<&'a Vec<Json>> {
    match value {
        Some(Json::Array(values)) => Some(values),
        _ => None,
    }
}

fn bool_value(value: Option<&Json>) -> Option<bool> {
    match value {
        Some(Json::Bool(value)) => Some(*value),
        _ => None,
    }
}

fn result_success(value: &Json) -> bool {
    value
        .as_object()
        .and_then(|object| object.get("success"))
        .and_then(|value| match value {
            Json::Bool(value) => Some(*value),
            _ => None,
        })
        .unwrap_or(false)
}

fn failure(operation: &str, diagnostics: &mut Vec<Json>) -> Json {
    super::semantic_contract::sort_diagnostics(diagnostics);
    simple_result(operation, false, diagnostics.clone())
}

fn success(operation: &str, mut values: BTreeMap<String, Json>) -> Json {
    values.insert("core_contract_version".into(), string("1.0"));
    values.insert("operation".into(), string(operation));
    values.insert("success".into(), Json::Bool(true));
    values
        .entry("diagnostics".into())
        .or_insert_with(|| Json::Array(Vec::new()));
    Json::Object(values)
}

fn expected_families() -> BTreeMap<String, String> {
    BTreeMap::from([
        ("architecture-interpretation".into(), "1.0".into()),
        ("normalized-model".into(), "2.3".into()),
        ("normative-semantics".into(), "1.0".into()),
    ])
}

fn validate_profile_value(profile: Option<&Json>, diagnostics: &mut Vec<Json>) {
    let Some(value) = profile.and_then(Json::as_object) else {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_failure",
            "profile must be an object",
            Some("profile".into()),
        ));
        return;
    };
    let allowed = [
        "$schema",
        "profileFamily",
        "profileVersion",
        "profileId",
        "participatingFamilies",
        "operations",
        "selectionPurposes",
    ];
    for key in value.keys() {
        if !allowed.contains(&key.as_str()) {
            diagnostics.push(diagnostic(
                "semantic_contract.profile_failure",
                format!("profile field is not governed: {key}"),
                Some(format!("profile.{key}")),
            ));
        }
    }
    if text(value.get("profileFamily")).as_deref() != Some(PROFILE_FAMILY) {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_failure",
            "profileFamily must be architecture-materialization",
            Some("profile.profileFamily".into()),
        ));
    }
    if text(value.get("profileVersion")).as_deref() != Some(PROFILE_VERSION) {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_failure",
            "profileVersion must be 1.0",
            Some("profile.profileVersion".into()),
        ));
    }
    if text(value.get("profileId")).as_deref() != Some(PROFILE_ID) {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_failure",
            "profileId must be architecture-materialization@1.0",
            Some("profile.profileId".into()),
        ));
    }
    let mut actual = BTreeMap::new();
    match array(value.get("participatingFamilies")) {
        Some(families) => {
            for (index, family) in families.iter().enumerate() {
                let path = format!("profile.participatingFamilies[{index}]");
                let Some(family) = family.as_object() else {
                    diagnostics.push(diagnostic(
                        "semantic_contract.profile_failure",
                        "participating family must be an object",
                        Some(path),
                    ));
                    continue;
                };
                let name = text(family.get("semanticContractFamily")).unwrap_or_default();
                let version = text(family.get("semanticContractVersion")).unwrap_or_default();
                if !matches!(
                    family.get("cardinality"),
                    Some(Json::Number(number)) if number.as_u64() == Some(1)
                ) {
                    diagnostics.push(diagnostic(
                        "semantic_contract.profile_failure",
                        "each participating family must have cardinality 1",
                        Some(format!("{path}.cardinality")),
                    ));
                }
                if actual.insert(name.clone(), version.clone()).is_some() {
                    diagnostics.push(diagnostic(
                        "semantic_contract.duplicate_profile_family",
                        "profile cannot declare a participating family twice",
                        Some(format!("{path}.semanticContractFamily")),
                    ));
                }
            }
        }
        None => diagnostics.push(diagnostic(
            "semantic_contract.profile_failure",
            "participatingFamilies must be an array",
            Some("profile.participatingFamilies".into()),
        )),
    }
    let expected = expected_families();
    if actual != expected {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_family_mismatch",
            "architecture-materialization@1.0 requires exactly the landed three semantic families and versions",
            Some("profile.participatingFamilies".into()),
        ));
    }
    let operations = array(value.get("operations"))
        .map(|values| values.iter().filter_map(Json::as_str).collect::<Vec<_>>());
    let legacy_operations = Some(
        &[
            "validate_profile",
            "qualify_tuple",
            "assemble_set",
            "validate_corpus",
            "resolve_current",
        ][..],
    );
    let materialization_operations = Some(
        &[
            "validate_profile",
            "qualify_tuple",
            "assemble_set",
            "validate_corpus",
            "resolve_current",
            "resolve_semantic_contract_set",
            "materialize_architecture",
        ][..],
    );
    if operations.as_deref() != legacy_operations
        && operations.as_deref() != materialization_operations
    {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_operation_mismatch",
            "profile operations must advertise only the implemented semantic-contract-set operations",
            Some("profile.operations".into()),
        ));
    }
    let purposes = array(value.get("selectionPurposes"))
        .map(|values| values.iter().filter_map(Json::as_str).collect::<Vec<_>>());
    if purposes.as_deref() != Some(&["architecture-materialization"]) {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_operation_mismatch",
            "profile selectionPurposes must contain architecture-materialization",
            Some("profile.selectionPurposes".into()),
        ));
    }
}

pub fn validate_profile(request: &Json) -> Json {
    let mut diagnostics = Vec::new();
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    validate_profile_value(root.get("profile"), &mut diagnostics);
    if diagnostics.is_empty() {
        success("validate_semantic_contract_profile", BTreeMap::new())
    } else {
        failure("validate_semantic_contract_profile", &mut diagnostics)
    }
}

fn verify_definition_bundles(
    raw: Option<&Json>,
    diagnostics: &mut Vec<Json>,
) -> VerifiedDefinitionBundles {
    let Some(bundles) = array(raw) else {
        diagnostics.push(diagnostic(
            "semantic_contract.integrity_failure",
            "definitions must be an array of exact definition/resource bundles",
            Some("definitions".into()),
        ));
        return VerifiedDefinitionBundles::default();
    };
    let mut definitions = VerifiedDefinitionBundles::default();
    for (index, raw_bundle) in bundles.iter().enumerate() {
        let path = format!("definitions[{index}]");
        let Some(bundle) = raw_bundle.as_object() else {
            diagnostics.push(diagnostic(
                "semantic_contract.integrity_failure",
                "definition bundle must be an object",
                Some(path),
            ));
            continue;
        };
        let Some(definition) = bundle.get("definition").and_then(Json::as_object) else {
            diagnostics.push(diagnostic(
                "semantic_contract.integrity_failure",
                "definition bundle is missing definition",
                Some(format!("{path}.definition")),
            ));
            continue;
        };
        let family = text(definition.get("semanticContractFamily")).unwrap_or_default();
        let version = text(definition.get("semanticContractVersion")).unwrap_or_default();
        let key = (family, version);
        let fingerprint = text(definition.get("semanticContractFingerprint")).unwrap_or_default();
        let member = ContractSetMember {
            family: key.0.clone(),
            version: key.1.clone(),
            fingerprint: fingerprint.clone(),
        };
        if !is_scf(&fingerprint) {
            diagnostics.push(diagnostic(
                "semantic_contract.invalid_scf",
                "definition must contain a valid declared SCF",
                Some(format!("{path}.definition.semanticContractFingerprint")),
            ));
        }
        let verify_request = object([
            ("core_contract_version".into(), string("1.0")),
            ("operation".into(), string("fingerprint_semantic_contract")),
            ("mode".into(), string("verify")),
            ("definition".into(), Json::Object(definition.clone())),
        ]);
        if !result_success(&super::semantic_contract::fingerprint(&verify_request)) {
            diagnostics.push(diagnostic(
                "semantic_contract.scf_mismatch",
                "declared SCF does not match the immutable definition",
                Some(format!("{path}.definition")),
            ));
        }
        let resources = bundle
            .get("resources")
            .cloned()
            .unwrap_or(Json::Array(Vec::new()));
        let closure_request = object([
            ("core_contract_version".into(), string("1.0")),
            (
                "operation".into(),
                string("validate_semantic_resource_closure"),
            ),
            ("definition".into(), Json::Object(definition.clone())),
            ("resources".into(), resources.clone()),
        ]);
        if !result_success(&super::semantic_contract::validate_closure(
            &closure_request,
        )) {
            diagnostics.push(diagnostic(
                "semantic_contract.integrity_failure",
                "definition resource closure is incomplete or invalid",
                Some(format!("{path}.resources")),
            ));
        }
        let verified_bundle = DefinitionBundle {
            member: member.clone(),
            definition: Json::Object(definition.clone()),
            resources: resources.clone().as_array().cloned().unwrap_or_default(),
        };
        if let Some(previous) = definitions
            .by_family_version
            .insert(key.clone(), verified_bundle.clone())
        {
            let mut previous_json = String::new();
            let mut current_json = String::new();
            let same = super::semantic_contract::canonicalize_value(
                &previous.definition,
                &mut previous_json,
            )
                .is_ok()
                && super::semantic_contract::canonicalize_value(
                    &verified_bundle.definition,
                    &mut current_json,
                )
                .is_ok()
                && previous_json == current_json;
            diagnostics.push(diagnostic(
                if same {
                    "semantic_contract.duplicate_definition"
                } else {
                    "semantic_contract.conflicting_definition"
                },
                "one SCV identity cannot be supplied more than once",
                Some(format!("{path}.definition")),
            ));
        }
        // Duplicate identities are already diagnosed through the stable
        // family/version index above; emitting a second diagnostic here would
        // make error multiplicity depend on the indexing strategy.
        definitions.by_identity.insert(member, verified_bundle);
    }
    definitions
}

fn profile_members_match(
    profile: &Json,
    members: &[ContractSetMember],
    diagnostics: &mut Vec<Json>,
) {
    validate_profile_value(Some(profile), diagnostics);
    let expected = expected_families();
    let actual = members
        .iter()
        .map(|member| (member.family.as_str(), member.version.as_str()))
        .collect::<BTreeSet<_>>();
    let expected_set = expected
        .iter()
        .map(|(family, version)| (family.as_str(), version.as_str()))
        .collect::<BTreeSet<_>>();
    if actual != expected_set {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_family_mismatch",
            "requested tuple must contain exactly one member from every participating family",
            Some("members".into()),
        ));
    }
}

fn validate_set_definition_refs(
    members: &[ContractSetMember],
    definitions: &VerifiedDefinitionBundles,
    path: &str,
    diagnostics: &mut Vec<Json>,
) {
    for member in members {
        let key = (member.family.clone(), member.version.clone());
        let Some(bundle) = definitions.family_version(member) else {
            diagnostics.push(diagnostic(
                "semantic_contract.missing_definition",
                "SCS member has no retained immutable definition",
                Some(format!("{path}.members")),
            ));
            continue;
        };
        let actual = text(
            bundle
                .definition
                .as_object()
                .and_then(|value| value.get("semanticContractFingerprint")),
        )
        .unwrap_or_default();
        if actual != member.fingerprint {
            diagnostics.push(diagnostic(
                "semantic_contract.member_fingerprint_mismatch",
                "SCS member fingerprint does not match the retained immutable definition",
                Some(format!("{path}.members")),
            ));
        }
    }
}

fn qualification_key(value: &BTreeMap<String, Json>) -> (String, String, String, String) {
    (
        text(value.get("semanticContractSetId")).unwrap_or_default(),
        text(value.get("operation")).unwrap_or_default(),
        text(value.get("direction")).unwrap_or_else(|| "none".into()),
        text(value.get("profileId")).unwrap_or_default(),
    )
}

fn validate_qualification_value(
    _profile: &Json,
    qualification: &Json,
    expected_set_id: Option<&str>,
    expected_members: Option<&[ContractSetMember]>,
    operation: Option<&str>,
    direction: Option<&str>,
    diagnostics: &mut Vec<Json>,
) {
    let Some(value) = qualification.as_object() else {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "qualification must be an object",
            Some("qualification".into()),
        ));
        return;
    };
    let allowed = [
        "$schema",
        "qualificationRecordId",
        "qualificationSchemaVersion",
        "operation",
        "direction",
        "profileId",
        "semanticContractSetId",
        "members",
        "outcome",
        "installedExecutionSupport",
        "newUsePolicy",
        "historicalInterpretationSupport",
        "qualificationRevision",
        "reasonCode",
    ];
    for key in value.keys() {
        if !allowed.contains(&key.as_str()) {
            diagnostics.push(diagnostic(
                "semantic_contract.qualification_failure",
                format!("qualification field is not governed: {key}"),
                Some(format!("qualification.{key}")),
            ));
        }
    }
    let required = [
        "qualificationRecordId",
        "qualificationSchemaVersion",
        "operation",
        "direction",
        "profileId",
        "semanticContractSetId",
        "members",
        "outcome",
        "installedExecutionSupport",
        "newUsePolicy",
        "historicalInterpretationSupport",
        "qualificationRevision",
    ];
    for key in required {
        if !value.contains_key(key) {
            diagnostics.push(diagnostic(
                "semantic_contract.qualification_failure",
                format!("required qualification field is missing: {key}"),
                Some(format!("qualification.{key}")),
            ));
        }
    }
    let id = text(value.get("qualificationRecordId")).unwrap_or_default();
    if id.is_empty() {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "qualificationRecordId must be non-empty",
            Some("qualification.qualificationRecordId".into()),
        ));
    }
    if text(value.get("qualificationSchemaVersion")).as_deref() != Some(QUALIFICATION_VERSION) {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "qualificationSchemaVersion must be 1.0",
            Some("qualification.qualificationSchemaVersion".into()),
        ));
    }
    if text(value.get("profileId")).as_deref() != Some(PROFILE_ID) {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "qualification must use architecture-materialization@1.0",
            Some("qualification.profileId".into()),
        ));
    }
    let actual_set_id = text(value.get("semanticContractSetId")).unwrap_or_default();
    if !is_scs(&actual_set_id) {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "semanticContractSetId must be an exact SCS identity",
            Some("qualification.semanticContractSetId".into()),
        ));
    }
    if let Some(expected) = expected_set_id {
        if actual_set_id != expected {
            diagnostics.push(diagnostic(
                "semantic_contract.qualification_set_mismatch",
                "qualification points to a different SCS",
                Some("qualification.semanticContractSetId".into()),
            ));
        }
    }
    let actual_operation = text(value.get("operation")).unwrap_or_default();
    if actual_operation.is_empty() {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "operation must be non-empty",
            Some("qualification.operation".into()),
        ));
    }
    if operation.is_some_and(|expected| actual_operation != expected) {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_operation_mismatch",
            "qualification does not cover the requested operation",
            Some("qualification.operation".into()),
        ));
    }
    let actual_direction = text(value.get("direction")).unwrap_or_else(|| "none".into());
    if !matches!(actual_direction.as_str(), "none" | "forward" | "reverse") {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "direction must be none, forward, or reverse",
            Some("qualification.direction".into()),
        ));
    }
    if direction.is_some_and(|expected| actual_direction != expected) {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_direction_mismatch",
            "qualification direction is not the requested direction",
            Some("qualification.direction".into()),
        ));
    }
    let members = parse_contract_set_members(
        value.get("members"),
        "qualification.members",
        diagnostics,
        ContractSetMemberDiagnosticContext::Governance,
    );
    if let Some(expected) = expected_members {
        if members != expected {
            diagnostics.push(diagnostic(
                "semantic_contract.qualification_members_mismatch",
                "qualification members do not exactly match the SCS composition",
                Some("qualification.members".into()),
            ));
        }
    }
    if !matches!(
        text(value.get("outcome")).as_deref(),
        Some("qualified" | "rejected" | "prohibited")
    ) {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "outcome must be qualified, rejected, or prohibited",
            Some("qualification.outcome".into()),
        ));
    }
    if bool_value(value.get("installedExecutionSupport")).is_none() {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "installedExecutionSupport must be boolean",
            Some("qualification.installedExecutionSupport".into()),
        ));
    }
    if !matches!(
        text(value.get("newUsePolicy")).as_deref(),
        Some("permitted" | "prohibited")
    ) {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "newUsePolicy must be permitted or prohibited",
            Some("qualification.newUsePolicy".into()),
        ));
    }
    if bool_value(value.get("historicalInterpretationSupport")).is_none() {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "historicalInterpretationSupport must be boolean",
            Some("qualification.historicalInterpretationSupport".into()),
        ));
    }
    if text(value.get("qualificationRevision"))
        .unwrap_or_default()
        .is_empty()
    {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "qualificationRevision must be non-empty",
            Some("qualification.qualificationRevision".into()),
        ));
    }
}

fn validate_set_artifact(
    value: &Json,
    diagnostics: &mut Vec<Json>,
) -> Option<(String, Vec<ContractSetMember>, String)> {
    let Some(artifact) = value.as_object() else {
        diagnostics.push(diagnostic(
            "semantic_contract.integrity_failure",
            "SCS artifact must be an object",
            Some("sets".into()),
        ));
        return None;
    };
    for key in artifact.keys() {
        if !["$schema", "scsScheme", "semanticContractSetId", "members"].contains(&key.as_str()) {
            diagnostics.push(diagnostic(
                "semantic_contract.integrity_failure",
                format!("immutable SCS field is not allowed: {key}"),
                Some(format!("sets.{key}")),
            ));
        }
    }
    if text(artifact.get("scsScheme")).as_deref() != Some(SCS_SCHEME) {
        diagnostics.push(diagnostic(
            "semantic_contract.integrity_failure",
            "scsScheme is invalid",
            Some("sets.scsScheme".into()),
        ));
    }
    let members = parse_contract_set_members(
        artifact.get("members"),
        "sets.members",
        diagnostics,
        ContractSetMemberDiagnosticContext::Governance,
    );
    if members.is_empty() {
        return None;
    }
    let (canonical, expected_id) = match canonical_contract_set(&members) {
        Ok(value) => value,
        Err(error) => {
            diagnostics.push(diagnostic(
                "semantic_contract.integrity_failure",
                error,
                Some("sets.members".into()),
            ));
            return None;
        }
    };
    let actual_id = text(artifact.get("semanticContractSetId")).unwrap_or_default();
    if !is_scs(&actual_id) || actual_id != expected_id {
        diagnostics.push(diagnostic(
            "semantic_contract.scs_id_mismatch",
            "SCS ID does not match the canonical composition",
            Some("sets.semanticContractSetId".into()),
        ));
    }
    Some((actual_id, members, canonical))
}

fn find_qualified<'a>(
    qualifications: &'a [Json],
    set_id: &str,
    operation: &str,
    direction: &str,
    members: &[ContractSetMember],
) -> Option<&'a BTreeMap<String, Json>> {
    qualifications
        .iter()
        .filter_map(Json::as_object)
        .find(|value| {
            qualification_key(value).0 == set_id
                && qualification_key(value).1 == operation
                && qualification_key(value).2 == direction
                && text(value.get("profileId")).as_deref() == Some(PROFILE_ID)
                && text(value.get("outcome")).as_deref() == Some("qualified")
                && bool_value(value.get("installedExecutionSupport")) == Some(true)
                && text(value.get("newUsePolicy")).as_deref() == Some("permitted")
                && parse_contract_set_members(
                    value.get("members"),
                    "qualification.members",
                    &mut Vec::new(),
                    ContractSetMemberDiagnosticContext::Governance,
                ) == members
        })
}

pub fn validate_qualification(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    let mut diagnostics = Vec::new();
    let Some(profile) = root.get("profile") else {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_failure",
            "profile is required",
            Some("profile".into()),
        ));
        return failure("validate_semantic_contract_qualification", &mut diagnostics);
    };
    let members = parse_contract_set_members(
        root.get("members"),
        "members",
        &mut diagnostics,
        ContractSetMemberDiagnosticContext::Governance,
    );
    profile_members_match(profile, &members, &mut diagnostics);
    let expected_set_id = canonical_contract_set(&members).ok().map(|(_, id)| id);
    let operation = text(root.get("targetOperation"));
    let direction = text(root.get("direction")).unwrap_or_else(|| "none".into());
    if operation.as_deref().is_none_or(str::is_empty) {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "operation is required",
            Some("operation".into()),
        ));
    }
    validate_qualification_value(
        profile,
        root.get("qualification").unwrap_or(&Json::Null),
        expected_set_id.as_deref(),
        Some(&members),
        operation.as_deref(),
        Some(&direction),
        &mut diagnostics,
    );
    if diagnostics.is_empty() {
        let mut values = BTreeMap::new();
        values.insert("qualification_valid".into(), Json::Bool(true));
        success("validate_semantic_contract_qualification", values)
    } else {
        failure("validate_semantic_contract_qualification", &mut diagnostics)
    }
}

fn validate_catalog_policy(
    catalog: Option<&Json>,
    policy: Option<&Json>,
    known_sets: &BTreeMap<String, String>,
    diagnostics: &mut Vec<Json>,
) {
    let Some(catalog) = catalog.and_then(Json::as_object) else {
        diagnostics.push(diagnostic(
            "semantic_contract.policy_failure",
            "catalog must be an object",
            Some("catalog".into()),
        ));
        return;
    };
    let Some(policy) = policy.and_then(Json::as_object) else {
        diagnostics.push(diagnostic(
            "semantic_contract.policy_failure",
            "policy must be an object",
            Some("policy".into()),
        ));
        return;
    };
    for (key, _) in catalog {
        if ![
            "$schema",
            "catalogSchemaVersion",
            "catalogRevision",
            "entries",
        ]
        .contains(&key.as_str())
        {
            diagnostics.push(diagnostic(
                "semantic_contract.policy_failure",
                format!("catalog field is not governed: {key}"),
                Some(format!("catalog.{key}")),
            ));
        }
    }
    for (key, _) in policy {
        if ![
            "$schema",
            "policySchemaVersion",
            "policyRevision",
            "entries",
        ]
        .contains(&key.as_str())
        {
            diagnostics.push(diagnostic(
                "semantic_contract.policy_failure",
                format!("policy field is not governed: {key}"),
                Some(format!("policy.{key}")),
            ));
        }
    }
    if text(catalog.get("catalogSchemaVersion")).as_deref() != Some("1.0") {
        diagnostics.push(diagnostic(
            "semantic_contract.policy_failure",
            "catalogSchemaVersion must be 1.0",
            Some("catalog.catalogSchemaVersion".into()),
        ));
    }
    if text(catalog.get("catalogRevision"))
        .unwrap_or_default()
        .is_empty()
    {
        diagnostics.push(diagnostic(
            "semantic_contract.policy_failure",
            "catalogRevision must be non-empty",
            Some("catalog.catalogRevision".into()),
        ));
    }
    if text(policy.get("policySchemaVersion")).as_deref() != Some("1.0") {
        diagnostics.push(diagnostic(
            "semantic_contract.policy_failure",
            "policySchemaVersion must be 1.0",
            Some("policy.policySchemaVersion".into()),
        ));
    }
    if text(policy.get("policyRevision"))
        .unwrap_or_default()
        .is_empty()
    {
        diagnostics.push(diagnostic(
            "semantic_contract.policy_failure",
            "policyRevision must be non-empty",
            Some("policy.policyRevision".into()),
        ));
    }
    let mut catalog_ids = BTreeSet::new();
    if let Some(entries) = array(catalog.get("entries")) {
        for (index, entry) in entries.iter().enumerate() {
            let path = format!("catalog.entries[{index}]");
            let Some(entry) = entry.as_object() else {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "catalog entry must be an object",
                    Some(path.clone()),
                ));
                continue;
            };
            for key in entry.keys() {
                if ![
                    "semanticContractSetId",
                    "catalogued",
                    "lifecycle",
                    "historicalAddressable",
                ]
                .contains(&key.as_str())
                {
                    diagnostics.push(diagnostic(
                        "semantic_contract.policy_failure",
                        format!("catalog entry field is not governed: {key}"),
                        Some(format!("{path}.{key}")),
                    ));
                }
            }
            let id = text(entry.get("semanticContractSetId")).unwrap_or_default();
            if !catalog_ids.insert(id.clone()) {
                diagnostics.push(diagnostic(
                    "semantic_contract.duplicate_catalog_entry",
                    "catalog identity occurs more than once",
                    Some(path.clone()),
                ));
            }
            if !known_sets.contains_key(&id) {
                diagnostics.push(diagnostic(
                    "semantic_contract.dangling_catalog_set",
                    "catalog points to a missing SCS",
                    Some(format!("{path}.semanticContractSetId")),
                ));
            }
            if !is_scs(&id) {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "catalog semanticContractSetId must be an exact SCS identity",
                    Some(format!("{path}.semanticContractSetId")),
                ));
            }
            if bool_value(entry.get("catalogued")).is_none() {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "catalogued must be boolean",
                    Some(format!("{path}.catalogued")),
                ));
            }
            if !matches!(
                text(entry.get("lifecycle")).as_deref(),
                Some("active" | "deprecated" | "historical")
            ) {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "lifecycle must be active, deprecated, or historical",
                    Some(format!("{path}.lifecycle")),
                ));
            }
            if bool_value(entry.get("historicalAddressable")).is_none() {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "historicalAddressable must be boolean",
                    Some(format!("{path}.historicalAddressable")),
                ));
            }
        }
    } else {
        diagnostics.push(diagnostic(
            "semantic_contract.policy_failure",
            "catalog.entries must be an array",
            Some("catalog.entries".into()),
        ));
    }
    let mut policy_keys = BTreeSet::new();
    if let Some(entries) = array(policy.get("entries")) {
        for (index, entry) in entries.iter().enumerate() {
            let path = format!("policy.entries[{index}]");
            let Some(entry) = entry.as_object() else {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "policy entry must be an object",
                    Some(path),
                ));
                continue;
            };
            for key in entry.keys() {
                if ![
                    "semanticContractSetId",
                    "operation",
                    "direction",
                    "newUsePolicy",
                    "installedExecutionSupport",
                    "historicalInterpretationSupport",
                ]
                .contains(&key.as_str())
                {
                    diagnostics.push(diagnostic(
                        "semantic_contract.policy_failure",
                        format!("policy entry field is not governed: {key}"),
                        Some(format!("{path}.{key}")),
                    ));
                }
            }
            let id = text(entry.get("semanticContractSetId")).unwrap_or_default();
            let key = (
                id.clone(),
                text(entry.get("operation")).unwrap_or_default(),
                text(entry.get("direction")).unwrap_or_else(|| "none".into()),
            );
            if !policy_keys.insert(key) {
                diagnostics.push(diagnostic(
                    "semantic_contract.conflicting_policy",
                    "policy contains duplicate operation status",
                    Some(path.clone()),
                ));
            }
            if !known_sets.contains_key(&id) {
                diagnostics.push(diagnostic(
                    "semantic_contract.dangling_policy_set",
                    "policy points to a missing SCS",
                    Some(format!("{path}.semanticContractSetId")),
                ));
            }
            if !is_scs(&id) {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "policy semanticContractSetId must be an exact SCS identity",
                    Some(format!("{path}.semanticContractSetId")),
                ));
            }
            if text(entry.get("operation")).unwrap_or_default().is_empty() {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "policy operation must be non-empty",
                    Some(format!("{path}.operation")),
                ));
            }
            if !matches!(
                text(entry.get("direction")).as_deref(),
                Some("none" | "forward" | "reverse")
            ) {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "direction must be none, forward, or reverse",
                    Some(format!("{path}.direction")),
                ));
            }
            if !matches!(
                text(entry.get("newUsePolicy")).as_deref(),
                Some("permitted" | "prohibited")
            ) {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "newUsePolicy must be permitted or prohibited",
                    Some(format!("{path}.newUsePolicy")),
                ));
            }
            if bool_value(entry.get("installedExecutionSupport")).is_none()
                || bool_value(entry.get("historicalInterpretationSupport")).is_none()
            {
                diagnostics.push(diagnostic(
                    "semantic_contract.policy_failure",
                    "support axes must be boolean",
                    Some(path),
                ));
            }
        }
    } else {
        diagnostics.push(diagnostic(
            "semantic_contract.policy_failure",
            "policy.entries must be an array",
            Some("policy.entries".into()),
        ));
    }
}

fn policy_supports(policy: Option<&Json>, set_id: &str, operation: &str, direction: &str) -> bool {
    array(
        policy
            .and_then(Json::as_object)
            .and_then(|value| value.get("entries")),
    )
    .is_some_and(|entries| {
        entries.iter().filter_map(Json::as_object).any(|entry| {
            text(entry.get("semanticContractSetId")).as_deref() == Some(set_id)
                && text(entry.get("operation")).as_deref() == Some(operation)
                && text(entry.get("direction")).unwrap_or_else(|| "none".into()) == direction
                && text(entry.get("newUsePolicy")).as_deref() == Some("permitted")
                && bool_value(entry.get("installedExecutionSupport")) == Some(true)
        })
    })
}

fn catalog_supports(catalog: Option<&Json>, set_id: &str) -> bool {
    array(
        catalog
            .and_then(Json::as_object)
            .and_then(|value| value.get("entries")),
    )
    .is_some_and(|entries| {
        entries.iter().filter_map(Json::as_object).any(|entry| {
            text(entry.get("semanticContractSetId")).as_deref() == Some(set_id)
                && bool_value(entry.get("catalogued")) == Some(true)
                && text(entry.get("lifecycle")).as_deref() == Some("active")
        })
    })
}

/// A retained definition together with the sealed resource content that was
/// verified against its manifest.  The member identity is carried alongside
/// the payload so callers cannot accidentally turn a family/version lookup
/// back into an authority decision after exact resolution has completed.
#[derive(Clone, Debug)]
pub(crate) struct DefinitionBundle {
    pub(crate) member: ContractSetMember,
    pub(crate) definition: Json,
    pub(crate) resources: Vec<Json>,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct VerifiedDefinitionBundles {
    by_family_version: BTreeMap<(String, String), DefinitionBundle>,
    by_identity: BTreeMap<ContractSetMember, DefinitionBundle>,
}

impl VerifiedDefinitionBundles {
    fn family_version(&self, member: &ContractSetMember) -> Option<&DefinitionBundle> {
        self.by_family_version
            .get(&(member.family.clone(), member.version.clone()))
    }

    pub(crate) fn exact(&self, member: &ContractSetMember) -> Option<&DefinitionBundle> {
        self.by_identity.get(member)
    }
}

/// The internal result of exact resolution. It deliberately contains the
/// retained members and qualification evidence needed by materialization, not
/// a current pointer or a host-selected default. The structure never crosses
/// the byte-oriented boundary as a Rust type.
#[derive(Clone, Debug)]
pub(crate) struct ExactResolution {
    pub(crate) set_id: String,
    pub(crate) members: Vec<ContractSetMember>,
    /// Only bundles whose complete family/version/SCF identity is a member of
    /// the requested SCS are exposed to materialization.
    pub(crate) definitions: BTreeMap<String, DefinitionBundle>,
    pub(crate) qualification: Json,
    pub(crate) operation: String,
    pub(crate) direction: String,
    pub(crate) use_mode: String,
    pub(crate) catalog_revision: String,
    pub(crate) policy_revision: String,
}

fn failure_v11(operation: &str, diagnostics: &mut Vec<Json>) -> Json {
    super::semantic_contract::sort_diagnostics(diagnostics);
    super::simple_result_v11(operation, false, diagnostics.clone())
}

fn success_v11(operation: &str, mut values: BTreeMap<String, Json>) -> Json {
    values.insert("core_contract_version".into(), string("1.1"));
    values.insert("operation".into(), string(operation));
    values.insert("success".into(), Json::Bool(true));
    values
        .entry("diagnostics".into())
        .or_insert_with(|| Json::Array(Vec::new()));
    Json::Object(values)
}

fn append_result_diagnostics(result: &Json, diagnostics: &mut Vec<Json>) {
    if let Some(values) = result
        .as_object()
        .and_then(|value| value.get("diagnostics"))
        .and_then(Json::as_array)
    {
        diagnostics.extend(values.iter().cloned());
    }
}

fn profile_declares_operation(profile: Option<&Json>, operation: &str) -> bool {
    array(
        profile
            .and_then(Json::as_object)
            .and_then(|value| value.get("operations")),
    )
    .is_some_and(|operations| {
        operations
            .iter()
            .any(|value| value.as_str() == Some(operation))
    })
}

fn exact_catalog_supports(
    catalog: Option<&Json>,
    set_id: &str,
    use_mode: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let Some(entries) = array(
        catalog
            .and_then(Json::as_object)
            .and_then(|value| value.get("entries")),
    ) else {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_catalog_failure",
            "catalog entries are required for exact semantic-contract-set resolution",
            Some("catalog.entries".into()),
        ));
        return false;
    };
    let Some(entry) = entries
        .iter()
        .filter_map(Json::as_object)
        .find(|entry| text(entry.get("semanticContractSetId")).as_deref() == Some(set_id))
    else {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_catalog_failure",
            "the requested SCS is not retained in the supplied catalog",
            Some("semanticContractSetId".into()),
        ));
        return false;
    };
    if bool_value(entry.get("catalogued")) != Some(true) {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_catalog_failure",
            "the requested SCS is not catalogued",
            Some("catalog.entries.semanticContractSetId".into()),
        ));
        return false;
    }
    let historical = bool_value(entry.get("historicalAddressable")) == Some(true);
    let lifecycle = text(entry.get("lifecycle")).unwrap_or_default();
    let supported = if use_mode == "historical" {
        historical
    } else {
        lifecycle == "active"
    };
    if !supported {
        diagnostics.push(diagnostic(
            if use_mode == "historical" {
                "semantic_contract.historical_use_not_addressable"
            } else {
                "semantic_contract.new_use_not_permitted"
            },
            "the requested SCS is not permitted for the selected use mode",
            Some("catalog.entries.semanticContractSetId".into()),
        ));
    }
    supported
}

fn exact_policy_supports(
    policy: Option<&Json>,
    set_id: &str,
    operation: &str,
    direction: &str,
    use_mode: &str,
    diagnostics: &mut Vec<Json>,
) -> bool {
    let Some(entries) = array(
        policy
            .and_then(Json::as_object)
            .and_then(|value| value.get("entries")),
    ) else {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_policy_failure",
            "policy entries are required for exact semantic-contract-set resolution",
            Some("policy.entries".into()),
        ));
        return false;
    };
    let matching = entries.iter().filter_map(Json::as_object).find(|entry| {
        text(entry.get("semanticContractSetId")).as_deref() == Some(set_id)
            && text(entry.get("operation")).as_deref() == Some(operation)
            && text(entry.get("direction")).unwrap_or_else(|| "none".into()) == direction
    });
    let Some(entry) = matching else {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_policy_failure",
            "no exact policy entry exists for the requested SCS, operation, and direction",
            Some("policy.entries".into()),
        ));
        return false;
    };
    let installed = bool_value(entry.get("installedExecutionSupport")) == Some(true);
    let supported = if use_mode == "historical" {
        installed && bool_value(entry.get("historicalInterpretationSupport")) == Some(true)
    } else {
        installed && text(entry.get("newUsePolicy")).as_deref() == Some("permitted")
    };
    if !installed {
        diagnostics.push(diagnostic(
            "semantic_contract.installed_execution_support_unavailable",
            "the exact SCS operation has no installed execution support",
            Some("policy.entries.installedExecutionSupport".into()),
        ));
    } else if !supported {
        diagnostics.push(diagnostic(
            if use_mode == "historical" {
                "semantic_contract.historical_interpretation_unsupported"
            } else {
                "semantic_contract.new_use_prohibited"
            },
            "the exact SCS operation is not permitted for the selected use mode",
            Some("policy.entries".into()),
        ));
    }
    supported
}

fn exact_qualification<'a>(
    qualifications: &'a [Json],
    set_id: &str,
    operation: &str,
    direction: &str,
    use_mode: &str,
    members: &[ContractSetMember],
) -> Option<&'a BTreeMap<String, Json>> {
    qualifications
        .iter()
        .filter_map(Json::as_object)
        .find(|value| {
            qualification_key(value).0 == set_id
                && qualification_key(value).1 == operation
                && qualification_key(value).2 == direction
                && text(value.get("profileId")).as_deref() == Some(PROFILE_ID)
                && text(value.get("outcome")).as_deref() == Some("qualified")
                && bool_value(value.get("installedExecutionSupport")) == Some(true)
                && (use_mode == "historical"
                    && bool_value(value.get("historicalInterpretationSupport")) == Some(true)
                    || use_mode == "new"
                        && text(value.get("newUsePolicy")).as_deref() == Some("permitted"))
                && parse_contract_set_members(
                    value.get("members"),
                    "qualification.members",
                    &mut Vec::new(),
                    ContractSetMemberDiagnosticContext::Governance,
                ) == members
        })
}

/// Resolve exactly one retained SCS for a requested operation.  Notice that
/// `current` is not read anywhere in this function: exact resolution is an
/// identity operation over the supplied retained corpus, not a current-state
/// convenience selector.
pub(crate) fn resolve_exact_set(
    request: &Json,
    target_operation: &str,
) -> Result<ExactResolution, Vec<Json>> {
    let Some(root) = request.as_object() else {
        return Err(vec![diagnostic(
            "semantic_contract.exact_resolution_failure",
            "request must be an object",
            None,
        )]);
    };
    let mut diagnostics = Vec::new();
    let requested_id = text(root.get("semanticContractSetId")).unwrap_or_default();
    if !is_scs(&requested_id) {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_scs_identity",
            "semanticContractSetId must be a valid exact SCS identity",
            Some("semanticContractSetId".into()),
        ));
    }
    let operation = text(root.get("targetOperation")).unwrap_or_else(|| target_operation.into());
    if operation != target_operation {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_operation_mismatch",
            "targetOperation does not match the canonical operation",
            Some("targetOperation".into()),
        ));
    }
    let direction = text(root.get("direction")).unwrap_or_else(|| "none".into());
    if !matches!(direction.as_str(), "none" | "forward" | "reverse") {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_failure",
            "direction must be none, forward, or reverse",
            Some("direction".into()),
        ));
    }
    let use_mode = text(root.get("useMode")).unwrap_or_else(|| "new".into());
    if !matches!(use_mode.as_str(), "new" | "historical") {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_failure",
            "useMode must be new or historical",
            Some("useMode".into()),
        ));
    }
    let profile = root.get("profile").unwrap_or(&Json::Null);
    validate_profile_value(Some(profile), &mut diagnostics);
    if !profile_declares_operation(Some(profile), target_operation) {
        diagnostics.push(diagnostic(
            "semantic_contract.profile_operation_mismatch",
            "the supplied profile does not explicitly declare the requested operation",
            Some("profile.operations".into()),
        ));
    }

    // The retained corpus validation is repeated at this boundary so a
    // caller cannot make a tampered set appear valid by selecting only one
    // apparently well-formed member or qualification record.
    append_result_diagnostics(&validate_corpus(request), &mut diagnostics);
    let definitions = verify_definition_bundles(root.get("definitions"), &mut diagnostics);
    let mut selected_members: Option<Vec<ContractSetMember>> = None;
    let mut selected_canonical: Option<String> = None;
    let Some(sets) = array(root.get("sets")) else {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_resolution_failure",
            "sets must be an array of retained immutable SCS artifacts",
            Some("sets".into()),
        ));
        return Err(diagnostics);
    };
    for (_index, set) in sets.iter().enumerate() {
        if let Some((id, members, canonical)) = validate_set_artifact(set, &mut diagnostics) {
            if id == requested_id {
                selected_members = Some(members);
                selected_canonical = Some(canonical);
            }
        }
    }
    let Some(members) = selected_members else {
        diagnostics.push(diagnostic(
            "semantic_contract.exact_set_not_retained",
            "the explicitly requested SCS is not present in the retained corpus",
            Some("semanticContractSetId".into()),
        ));
        return Err(diagnostics);
    };
    if let Some(canonical) = selected_canonical {
        if canonical.is_empty() {
            diagnostics.push(diagnostic(
                "semantic_contract.scs_id_mismatch",
                "the requested SCS has no valid canonical preimage",
                Some("sets".into()),
            ));
        }
    }
    profile_members_match(profile, &members, &mut diagnostics);
    validate_set_definition_refs(&members, &definitions, "sets", &mut diagnostics);

    let empty_qualifications = Vec::new();
    let qualifications = array(root.get("qualifications")).unwrap_or(&empty_qualifications);
    let qualification = exact_qualification(
        qualifications,
        &requested_id,
        target_operation,
        &direction,
        &use_mode,
        &members,
    );
    if qualification.is_none() {
        diagnostics.push(diagnostic(
            "semantic_contract.missing_whole_tuple_qualification",
            "the exact retained SCS is not qualified as a whole for the requested operation and use mode",
            Some("qualifications".into()),
        ));
    }
    exact_catalog_supports(
        root.get("catalog"),
        &requested_id,
        &use_mode,
        &mut diagnostics,
    );
    exact_policy_supports(
        root.get("policy"),
        &requested_id,
        target_operation,
        &direction,
        &use_mode,
        &mut diagnostics,
    );
    if !diagnostics.is_empty() {
        return Err(diagnostics);
    }
    let qualification = qualification.expect("qualification checked above");
    let definitions = members
        .iter()
        .filter_map(|member| {
            definitions
                .exact(member)
                .cloned()
                .map(|bundle| (member.family.clone(), bundle))
        })
        .collect();
    Ok(ExactResolution {
        set_id: requested_id,
        members,
        definitions,
        qualification: Json::Object(qualification.clone()),
        operation,
        direction,
        use_mode,
        catalog_revision: text(
            root.get("catalog")
                .and_then(Json::as_object)
                .and_then(|value| value.get("catalogRevision")),
        )
        .unwrap_or_default(),
        policy_revision: text(
            root.get("policy")
                .and_then(Json::as_object)
                .and_then(|value| value.get("policyRevision")),
        )
        .unwrap_or_default(),
    })
}

/// Version 1.1 wire operation for exact retained-set resolution.
pub fn resolve_exact(request: &Json) -> Json {
    let target_operation = request
        .as_object()
        .and_then(|value| text(value.get("targetOperation")))
        .unwrap_or_default();
    if target_operation.is_empty() {
        let mut diagnostics = vec![diagnostic(
            "semantic_contract.exact_resolution_failure",
            "targetOperation is required for exact semantic-contract-set resolution",
            Some("targetOperation".into()),
        )];
        return failure_v11("resolve_semantic_contract_set", &mut diagnostics);
    }
    match resolve_exact_set(request, &target_operation) {
        Ok(resolution) => {
            let mut values = BTreeMap::new();
            values.insert(
                "resolved".into(),
                object([
                    ("profileId".into(), string(PROFILE_ID)),
                    ("operation".into(), string(resolution.operation)),
                    ("direction".into(), string(resolution.direction)),
                    ("useMode".into(), string(resolution.use_mode)),
                    ("semanticContractSetId".into(), string(resolution.set_id)),
                    (
                        "qualificationRecordId".into(),
                        string(
                            text(
                                resolution
                                    .qualification
                                    .as_object()
                                    .and_then(|value| value.get("qualificationRecordId")),
                            )
                            .unwrap_or_default(),
                        ),
                    ),
                    (
                        "qualificationRevision".into(),
                        string(
                            text(
                                resolution
                                    .qualification
                                    .as_object()
                                    .and_then(|value| value.get("qualificationRevision")),
                            )
                            .unwrap_or_default(),
                        ),
                    ),
                    (
                        "catalogRevision".into(),
                        string(resolution.catalog_revision),
                    ),
                    ("policyRevision".into(), string(resolution.policy_revision)),
                    (
                        "members".into(),
                        Json::Array(
                            resolution
                                .members
                                .iter()
                                .map(contract_set_member_wire)
                                .collect(),
                        ),
                    ),
                ]),
            );
            success_v11("resolve_semantic_contract_set", values)
        }
        Err(mut diagnostics) => failure_v11("resolve_semantic_contract_set", &mut diagnostics),
    }
}

pub fn validate_corpus(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    let mut diagnostics = Vec::new();
    if let Some(profile) = root.get("profile") {
        validate_profile_value(Some(profile), &mut diagnostics);
    }
    let definitions = verify_definition_bundles(root.get("definitions"), &mut diagnostics);
    let mut known_sets = BTreeMap::new();
    let mut set_members = BTreeMap::new();
    if let Some(sets) = array(root.get("sets")) {
        for (index, set) in sets.iter().enumerate() {
            let path = format!("sets[{index}]");
            if let Some((id, members, canonical)) = validate_set_artifact(set, &mut diagnostics) {
                set_members.insert(id.clone(), members);
                if let Some(previous) = known_sets.insert(id.clone(), canonical.clone()) {
                    if previous != canonical {
                        diagnostics.push(diagnostic(
                            "semantic_contract.conflicting_scs_preimage",
                            "different compositions were stored under one SCS ID",
                            Some(path.clone()),
                        ));
                    } else {
                        diagnostics.push(diagnostic(
                            "semantic_contract.duplicate_stored_composition",
                            "an immutable SCS composition is stored more than once",
                            Some(path.clone()),
                        ));
                    }
                }
                if let Some(members) = set_members.get(&id) {
                    validate_set_definition_refs(members, &definitions, &path, &mut diagnostics);
                }
            }
        }
    } else {
        diagnostics.push(diagnostic(
            "semantic_contract.integrity_failure",
            "sets must be an array",
            Some("sets".into()),
        ));
    }
    if let Some(qualifications) = array(root.get("qualifications")) {
        let mut ids = BTreeSet::new();
        for (index, qualification) in qualifications.iter().enumerate() {
            let path = format!("qualifications[{index}]");
            if let Some(value) = qualification.as_object() {
                let id = text(value.get("qualificationRecordId")).unwrap_or_default();
                if !ids.insert(id) {
                    diagnostics.push(diagnostic(
                        "semantic_contract.conflicting_qualification",
                        "qualification record identity occurs more than once",
                        Some(path.clone()),
                    ));
                }
                let set_id = text(value.get("semanticContractSetId")).unwrap_or_default();
                if !known_sets.contains_key(&set_id) {
                    diagnostics.push(diagnostic(
                        "semantic_contract.dangling_qualification_set",
                        "qualification points to a missing SCS",
                        Some(format!("{path}.semanticContractSetId")),
                    ));
                }
                validate_qualification_value(
                    root.get("profile").unwrap_or(&Json::Null),
                    qualification,
                    None,
                    set_members.get(&set_id).map(Vec::as_slice),
                    None,
                    None,
                    &mut diagnostics,
                );
            } else {
                diagnostics.push(diagnostic(
                    "semantic_contract.qualification_failure",
                    "qualification must be an object",
                    Some(path),
                ));
            }
        }
    } else {
        diagnostics.push(diagnostic(
            "semantic_contract.qualification_failure",
            "qualifications must be an array",
            Some("qualifications".into()),
        ));
    }
    validate_catalog_policy(
        root.get("catalog"),
        root.get("policy"),
        &known_sets,
        &mut diagnostics,
    );
    if diagnostics.is_empty() {
        let mut values = BTreeMap::new();
        values.insert("corpus_valid".into(), Json::Bool(true));
        success("validate_semantic_contract_corpus", values)
    } else {
        failure("validate_semantic_contract_corpus", &mut diagnostics)
    }
}

fn artifact_for(members: &[ContractSetMember], id: &str) -> Json {
    object([
        ("scsScheme".into(), string(SCS_SCHEME)),
        ("semanticContractSetId".into(), string(id)),
        (
            "members".into(),
            Json::Array(members.iter().map(contract_set_member_wire).collect()),
        ),
    ])
}

pub fn assemble(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    let mut diagnostics = Vec::new();
    let profile = root.get("profile").unwrap_or(&Json::Null);
    let members = parse_contract_set_members(
        root.get("requestedMembers"),
        "requestedMembers",
        &mut diagnostics,
        ContractSetMemberDiagnosticContext::Governance,
    );
    profile_members_match(profile, &members, &mut diagnostics);
    let operation = text(root.get("targetOperation")).unwrap_or_default();
    let direction = text(root.get("direction")).unwrap_or_else(|| "none".into());
    let (_canonical, set_id) = match canonical_contract_set(&members) {
        Ok(value) => value,
        Err(error) => {
            diagnostics.push(diagnostic(
                "semantic_contract.integrity_failure",
                error,
                Some("requestedMembers".into()),
            ));
            (String::new(), String::new())
        }
    };
    let definitions = verify_definition_bundles(root.get("definitions"), &mut diagnostics);
    for member in &members {
        match definitions.family_version(member) {
            Some(definition) if definition.member == *member => {}
            Some(_) => diagnostics.push(diagnostic(
                "semantic_contract.member_fingerprint_mismatch",
                "requested member SCF does not match the landed definition",
                Some("requestedMembers".into()),
            )),
            None => diagnostics.push(diagnostic(
                "semantic_contract.missing_definition",
                "requested member definition is missing",
                Some(member.family.clone()),
            )),
        }
    }
    let qualification = root.get("qualification").unwrap_or(&Json::Null);
    validate_qualification_value(
        profile,
        qualification,
        Some(&set_id),
        Some(&members),
        Some(&operation),
        Some(&direction),
        &mut diagnostics,
    );
    if find_qualified(
        std::slice::from_ref(qualification),
        &set_id,
        &operation,
        &direction,
        &members,
    )
    .is_none()
    {
        diagnostics.push(diagnostic(
            "semantic_contract.assembly_qualification_not_supported",
            "assembly requires a qualified, executable, new-use-permitted whole-tuple record",
            Some("qualification".into()),
        ));
    }
    let mut known_sets = BTreeMap::new();
    let mut retained_members = BTreeMap::new();
    let mut existing = false;
    if let Some(sets) = array(root.get("retainedSets")) {
        for (index, set) in sets.iter().enumerate() {
            if let Some((id, members, canonical)) = validate_set_artifact(set, &mut diagnostics) {
                validate_set_definition_refs(
                    &members,
                    &definitions,
                    &format!("retainedSets[{index}]"),
                    &mut diagnostics,
                );
                retained_members.insert(id.clone(), members);
                if let Some(previous) = known_sets.insert(id.clone(), canonical.clone()) {
                    if previous != canonical {
                        diagnostics.push(diagnostic(
                            "semantic_contract.conflicting_scs_preimage",
                            "conflicting retained SCS compositions cannot be reconciled",
                            Some("retainedSets".into()),
                        ));
                    }
                }
                if id == set_id {
                    existing = true;
                }
            }
        }
    } else {
        diagnostics.push(diagnostic(
            "semantic_contract.integrity_failure",
            "retainedSets must be supplied as an array",
            Some("retainedSets".into()),
        ));
    }
    // Validate catalog/policy against the retained corpus plus the candidate
    // composition. The candidate is not persisted until the host applies the
    // successful result, but its governed catalog entry may already exist in
    // an authoritative input revision.
    if !set_id.is_empty() {
        if let Ok((canonical, _)) = canonical_contract_set(&members) {
            known_sets.entry(set_id.clone()).or_insert(canonical);
        }
    }
    if let Some(qualifications) = array(root.get("retainedQualifications")) {
        let mut qualification_ids = BTreeSet::new();
        for (index, qualification) in qualifications.iter().enumerate() {
            let path = format!("retainedQualifications[{index}]");
            let Some(value) = qualification.as_object() else {
                diagnostics.push(diagnostic(
                    "semantic_contract.qualification_failure",
                    "qualification must be an object",
                    Some(path),
                ));
                continue;
            };
            let id = text(value.get("qualificationRecordId")).unwrap_or_default();
            if !qualification_ids.insert(id) {
                diagnostics.push(diagnostic(
                    "semantic_contract.conflicting_qualification",
                    "qualification record identity occurs more than once",
                    Some(path.clone()),
                ));
            }
            let retained_set_id = text(value.get("semanticContractSetId")).unwrap_or_default();
            validate_qualification_value(
                profile,
                qualification,
                Some(&retained_set_id),
                retained_members.get(&retained_set_id).map(Vec::as_slice),
                None,
                None,
                &mut diagnostics,
            );
        }
        if find_qualified(qualifications, &set_id, &operation, &direction, &members).is_none() {
            diagnostics.push(diagnostic(
                "semantic_contract.missing_whole_tuple_qualification",
                "the exact tuple and operation are not explicitly qualified",
                Some("qualification".into()),
            ));
        }
    } else {
        diagnostics.push(diagnostic(
            "semantic_contract.missing_whole_tuple_qualification",
            "retainedQualifications must be supplied",
            Some("retainedQualifications".into()),
        ));
    }
    validate_catalog_policy(
        root.get("catalog"),
        root.get("policy"),
        &known_sets,
        &mut diagnostics,
    );
    if !diagnostics.is_empty() {
        return failure("assemble_semantic_contract_set", &mut diagnostics);
    }
    let artifact = artifact_for(&members, &set_id);
    let mut values = BTreeMap::new();
    values.insert("semanticContractSetId".into(), string(set_id));
    values.insert("noOp".into(), Json::Bool(existing));
    values.insert(
        "emittedImmutableArtifacts".into(),
        if existing {
            Json::Array(Vec::new())
        } else {
            Json::Array(vec![artifact])
        },
    );
    values.insert("mutableChanges".into(), Json::Array(Vec::new()));
    success("assemble_semantic_contract_set", values)
}

pub fn resolve_current(request: &Json) -> Json {
    let Some(root) = request.as_object() else {
        return super::invalid("request must be an object");
    };
    let mut diagnostics = Vec::new();
    let operation = text(root.get("targetOperation")).unwrap_or_default();
    let direction = text(root.get("direction")).unwrap_or_else(|| "none".into());
    let current_id = root
        .get("current")
        .and_then(Json::as_object)
        .and_then(|value| text(value.get("semanticContractSetId")))
        .unwrap_or_default();
    let _profile = root.get("profile").unwrap_or(&Json::Null);
    let _definitions = verify_definition_bundles(root.get("definitions"), &mut diagnostics);
    let _corpus = validate_corpus(request);
    let current_set_present = array(root.get("sets")).is_some_and(|sets| {
        sets.iter().filter_map(Json::as_object).any(|set| {
            text(set.get("semanticContractSetId")).as_deref() == Some(current_id.as_str())
        })
    });
    if !result_success(&_corpus) && current_set_present {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_current_selection",
            "retained corpus is not valid for current resolution",
            Some("current".into()),
        ));
    }
    let Some(current) = root.get("current").and_then(Json::as_object) else {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_current_selection",
            "current selection must be an object",
            Some("current".into()),
        ));
        return failure("resolve_current_semantic_contract_set", &mut diagnostics);
    };
    for key in current.keys() {
        if ![
            "$schema",
            "currentSelectionSchemaVersion",
            "currentSelectionRevision",
            "profileId",
            "operation",
            "direction",
            "semanticContractSetId",
            "qualificationRecordId",
            "catalogRevision",
            "policyRevision",
        ]
        .contains(&key.as_str())
        {
            diagnostics.push(diagnostic(
                "semantic_contract.invalid_current_selection",
                format!("current selection field is not governed: {key}"),
                Some(format!("current.{key}")),
            ));
        }
    }
    for key in [
        "currentSelectionSchemaVersion",
        "currentSelectionRevision",
        "profileId",
        "operation",
        "direction",
        "semanticContractSetId",
        "qualificationRecordId",
        "catalogRevision",
        "policyRevision",
    ] {
        if !current.contains_key(key) {
            diagnostics.push(diagnostic(
                "semantic_contract.invalid_current_selection",
                format!("current selection field is missing: {key}"),
                Some(format!("current.{key}")),
            ));
        }
    }
    if text(current.get("currentSelectionSchemaVersion")).as_deref() != Some("1.0") {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_current_selection",
            "currentSelectionSchemaVersion must be 1.0",
            Some("current.currentSelectionSchemaVersion".into()),
        ));
    }
    if text(current.get("profileId")).as_deref() != Some(PROFILE_ID)
        || text(current.get("operation")).as_deref() != Some(operation.as_str())
        || text(current.get("direction")).unwrap_or_else(|| "none".into()) != direction
    {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_current_selection",
            "current pointer does not match the requested profile, operation, or direction",
            Some("current".into()),
        ));
    }
    let catalog_revision = text(
        root.get("catalog")
            .and_then(Json::as_object)
            .and_then(|value| value.get("catalogRevision")),
    );
    let policy_revision = text(
        root.get("policy")
            .and_then(Json::as_object)
            .and_then(|value| value.get("policyRevision")),
    );
    if text(current.get("catalogRevision")).as_deref() != catalog_revision.as_deref()
        || text(current.get("policyRevision")).as_deref() != policy_revision.as_deref()
    {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_current_selection",
            "current pointer revisions do not match the supplied catalog and policy revisions",
            Some("current".into()),
        ));
    }
    let empty_sets = Vec::new();
    let sets = array(root.get("sets")).unwrap_or(&empty_sets);
    let mut selected_members = None;
    for set in sets {
        if let Some((id, members, _)) = validate_set_artifact(set, &mut diagnostics) {
            if id == current_id {
                selected_members = Some(members);
            }
        }
    }
    let Some(members) = selected_members else {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_current_selection",
            "current pointer references a missing SCS",
            Some("current.semanticContractSetId".into()),
        ));
        return failure("resolve_current_semantic_contract_set", &mut diagnostics);
    };
    let empty_qualifications = Vec::new();
    let qualifications = array(root.get("qualifications")).unwrap_or(&empty_qualifications);
    let Some(qualification) = find_qualified(
        qualifications,
        &current_id,
        &operation,
        &direction,
        &members,
    ) else {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_current_selection",
            "current pointer references an unqualified or unsupported SCS",
            Some("current.semanticContractSetId".into()),
        ));
        return failure("resolve_current_semantic_contract_set", &mut diagnostics);
    };
    if text(current.get("qualificationRecordId")).as_deref()
        != text(qualification.get("qualificationRecordId")).as_deref()
        || !catalog_supports(root.get("catalog"), &current_id)
        || !policy_supports(root.get("policy"), &current_id, &operation, &direction)
    {
        diagnostics.push(diagnostic(
            "semantic_contract.invalid_current_selection",
            "current pointer is not supported by the exact qualification and current policy",
            Some("current".into()),
        ));
        return failure("resolve_current_semantic_contract_set", &mut diagnostics);
    }
    let mut values = BTreeMap::new();
    values.insert(
        "resolved".into(),
        object([
            ("profileId".into(), string(PROFILE_ID)),
            ("operation".into(), string(operation)),
            ("direction".into(), string(direction)),
            ("semanticContractSetId".into(), string(current_id)),
            (
                "qualificationRecordId".into(),
                string(text(qualification.get("qualificationRecordId")).unwrap_or_default()),
            ),
            (
                "qualificationRevision".into(),
                string(text(qualification.get("qualificationRevision")).unwrap_or_default()),
            ),
            (
                "catalogRevision".into(),
                string(
                    text(
                        root.get("catalog")
                            .and_then(Json::as_object)
                            .and_then(|value| value.get("catalogRevision")),
                    )
                    .unwrap_or_default(),
                ),
            ),
            (
                "policyRevision".into(),
                string(
                    text(
                        root.get("policy")
                            .and_then(Json::as_object)
                            .and_then(|value| value.get("policyRevision")),
                    )
                    .unwrap_or_default(),
                ),
            ),
        ]),
    );
    success("resolve_current_semantic_contract_set", values)
}

#[cfg(test)]
mod tests {
    use super::{assemble, Json};

    #[test]
    fn governed_assembly_and_direct_composition_share_the_scs_identity() {
        let vectors: Json = serde_json::from_str(include_str!(
            "../../contracts/semantic-core/v1.0/vectors/semantic-contract-set-governance.json"
        ))
        .expect("governance vectors are valid JSON");
        let cases = vectors
            .as_object()
            .and_then(|value| value.get("cases"))
            .and_then(Json::as_array)
            .expect("governance vectors contain cases");
        let assembly_request = cases
            .iter()
            .find(|case_value| {
                case_value
                    .as_object()
                    .and_then(|value| value.get("name"))
                    .and_then(Json::as_str)
                    == Some("assembly_is_deterministic_no_op_for_retained_set")
            })
            .and_then(|case_value| case_value.as_object())
            .and_then(|value| value.get("request"))
            .expect("assembly vector is present");
        let requested_members = assembly_request
            .as_object()
            .and_then(|value| value.get("requestedMembers"))
            .cloned()
            .expect("assembly request contains requested members");
        let direct_request = Json::Object(std::collections::BTreeMap::from([(
            "contracts".into(),
            requested_members,
        )]));

        let direct = super::super::semantic_contract::compose_set(&direct_request);
        let governed = assemble(assembly_request);
        let direct_id = direct
            .as_object()
            .and_then(|value| value.get("semantic_contract_set_id"))
            .and_then(Json::as_str)
            .expect("direct composition returns an SCS identity");
        let governed_id = governed
            .as_object()
            .and_then(|value| value.get("semanticContractSetId"))
            .and_then(Json::as_str)
            .expect("governed assembly returns an SCS identity");
        assert_eq!(direct_id, governed_id);
        assert_eq!(
            direct_id,
            "scs:v1:sha256:d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6"
        );
    }
}
