//! Internal ACC 1.2 composition qualification and its private insertion seam.
//!
//! Only the verified publication supplies binding rows. Inputs are borrowed:
//! the qualifier cannot insert children, mint identities, seal sources, or
//! produce a transport result. The separate insertion module consumes those
//! preconditions without changing the qualifier. `Qualified` describes binding
//! preconditions; outstanding interpretation obligations always remain.

use std::collections::{BTreeMap, BTreeSet};

use sha2::{Digest, Sha256};

use super::{
    authoring_construction_basis_v11 as basis, object, schema_validation, semantic_contract,
    string, Json,
};

#[path = "authoring_construction_insertion_v12.rs"]
pub(crate) mod insertion;

#[path = "authoring_construction_sources_v12.rs"]
pub(crate) mod sources;

#[path = "authoring_construction_dependencies_v12.rs"]
pub(crate) mod dependencies;

#[path = "authoring_construction_records_v12.rs"]
pub(crate) mod records;

const SCF: &str = "scf:v1:sha256:8da499420e996c446cbc416dc7db9b4bbb2692ea5039f14461f668aaa48b9e0c";
const AI_SCF: &str =
    "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a";
const SCHEMA: &str = "authoring-construction/1.2/schema";
const RULES: &str = "authoring-construction/1.2/rules";
const TABLE: &str = "authoring-construction/1.2/composition-bindings";
const TABLE_SCHEMA: &str = "authoring-construction/1.2/composition-bindings.schema";

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum Status {
    Rejected,
    Unavailable,
    Unresolved,
    Qualified,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Check {
    Qualified,
    Rejected,
    Unavailable,
    Blocked,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Diagnostic {
    pub status: Status,
    pub code: String,
    /// None is the unresolved identity sentinel, never a request locator.
    pub semantic_identity: Option<String>,
    pub field_or_relation_key: String,
    pub payload: Json,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct BindingDecision {
    pub parent_request_key: String,
    pub child_request_key: String,
    pub parent_identity: Option<String>,
    pub child_identity: Option<String>,
    pub ordering: Json,
    /// Exact verified row, including qualified semantic fields and authorities.
    pub binding: Json,
    pub qualified_semantic_field: Json,
    pub acc_fingerprint: String,
    pub binding_resource_key: String,
    pub binding_content_digest: String,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Qualification {
    pub authority: Check,
    pub request_schema: Check,
    pub binding_table: Check,
    pub endpoint_resolution: Check,
    pub status: Status,
    /// Empty on any failed qualification: no partial-success candidate basis.
    pub bindings: Vec<BindingDecision>,
    pub outstanding_dependencies: BTreeSet<&'static str>,
    pub diagnostics: Vec<Diagnostic>,
    pub authority_diagnostics: Vec<Json>,
}

impl Qualification {
    fn new() -> Self {
        Self {
            authority: Check::Unavailable,
            request_schema: Check::Blocked,
            binding_table: Check::Blocked,
            endpoint_resolution: Check::Blocked,
            status: Status::Unavailable,
            bindings: Vec::new(),
            diagnostics: Vec::new(),
            authority_diagnostics: Vec::new(),
            outstanding_dependencies: BTreeSet::from([
                "prepared_authoring_field_validation",
                "non_composition_reference_and_relationship_resolution",
                "compiler_child_insertion",
                "complete_child_field_and_identity_preservation",
                "exact_subtree_and_minimal_root_accounting",
                "complete_composition_evidence",
                "composed_candidate_basis_sealing",
                "complete_nm_2_4_interpretation",
                "expected_and_observed_ledgers",
                "whole_ledger_equivalence",
                "complete_construction_qualification",
            ]),
        }
    }

    fn diagnostic(
        &mut self,
        status: Status,
        code: &str,
        identity: Option<&str>,
        field: &str,
        payload: &Json,
    ) {
        self.diagnostics.push(Diagnostic {
            status,
            code: code.into(),
            semantic_identity: identity.map(str::to_owned),
            field_or_relation_key: field.into(),
            payload: payload.clone(),
        });
    }

    fn composition(
        &mut self,
        status: Status,
        suffix: &str,
        fragment: Option<&Json>,
        intent: &Json,
    ) {
        self.diagnostic(
            status,
            &format!("authoring_construction.composition.{suffix}"),
            fragment.and_then(identity),
            text(intent, "relation"),
            intent,
        );
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
        self.authority_diagnostics.sort_by_cached_key(digest);
        self.status = self
            .diagnostics
            .iter()
            .map(|d| d.status)
            .min()
            .unwrap_or(Status::Qualified);
        if self.status != Status::Qualified {
            self.bindings.clear();
        }
        self.bindings.sort_by_cached_key(|b| {
            (
                b.parent_request_key.clone(),
                text(&b.binding, "parent_property").to_owned(),
                b.ordering.as_u64().unwrap_or(0),
                b.child_request_key.clone(),
            )
        });
        self
    }
}

/// Accepts exactly the published definition/resource bundle and ACC request.
/// No host options, repository state, ADR prose, or ambient registry are read.
pub(crate) fn qualify(definition: &Json, resources: &[Json], request: &Json) -> Qualification {
    let mut result = Qualification::new();
    let closure = semantic_contract::validate_closure(&object([
        ("definition".into(), definition.clone()),
        ("resources".into(), Json::Array(resources.to_vec())),
    ]));
    result.authority_diagnostics = array(&closure, "diagnostics").to_vec();
    if closure.get("closure_valid").and_then(Json::as_bool) != Some(true)
        || text(definition, "semanticContractFamily") != "authoring-construction"
        || text(definition, "semanticContractVersion") != "1.2"
        || text(definition, "semanticContractFingerprint") != SCF
    {
        result.diagnostic(
            Status::Unavailable,
            "semantic_contract.exact_authority_mismatch",
            None,
            "authority",
            &Json::Null,
        );
        return result.finish();
    }
    result.authority = Check::Qualified;
    // Extra supplied resources are never authority, even if closure validation
    // permits them. Project the map to the verified manifest only.
    let sealed = manifest_resources(definition, resources);
    let rules = &sealed[RULES];
    let composition = rules.get("composition").unwrap_or(&Json::Null);
    let binding = composition.get("binding_authority").unwrap_or(&Json::Null);
    let table = sealed.get(TABLE).unwrap_or(&Json::Null);
    let table_ok = qualify_binding_authority(definition, &sealed);
    result.binding_table = if table_ok {
        Check::Qualified
    } else {
        Check::Unavailable
    };
    if !table_ok {
        result.composition(
            Status::Unavailable,
            "authority_inconsistent",
            None,
            &Json::Null,
        );
    }

    // Request binding mismatches are missing exact authority, not bad syntax.
    let mut canonical_request = String::new();
    let canonical_result = semantic_contract::canonicalize_value(request, &mut canonical_request);
    let acc = at(request, &["basis", "acc"]);
    let exact_request = text(request, "contract_version") == "1.2"
        && text(acc, "family") == "authoring-construction"
        && text(acc, "version") == "1.2"
        && text(acc, "semantic_contract_fingerprint") == SCF;
    if !exact_request {
        result.diagnostic(
            Status::Unavailable,
            "semantic_contract.exact_authority_mismatch",
            None,
            "basis.acc",
            if canonical_result.is_ok() {
                acc
            } else {
                &Json::Null
            },
        );
    }
    if let Err(error) = &canonical_result {
        // The shared canonicalizer cannot represent unsafe integer inputs.
        // That limitation is not a newly inferred composition violation.
        result.diagnostic(
            Status::Unavailable,
            "authoring_construction.execution_capability.unavailable",
            None,
            "canonical_request",
            &string(error.clone()),
        );
    }
    if let Err(error) =
        schema_validation::preflight_fragment(&sealed, SCHEMA, "/$defs/authoring_request")
    {
        result.diagnostic(
            Status::Unavailable,
            "authoring_construction.authority.unavailable",
            None,
            "schema",
            &string(error.message),
        );
        result.request_schema = Check::Unavailable;
        return result.finish();
    }
    // Inspect independent shape violations even when an ACC literal mismatches.
    // This local schema probe never becomes an execution request or authority.
    let mut schema_probe = request.clone();
    if !exact_request {
        replace_schema_literal(&mut schema_probe, &["contract_version"], "1.2");
        replace_schema_literal(
            &mut schema_probe,
            &["basis", "acc", "family"],
            "authoring-construction",
        );
        replace_schema_literal(&mut schema_probe, &["basis", "acc", "version"], "1.2");
        replace_schema_literal(
            &mut schema_probe,
            &["basis", "acc", "semantic_contract_fingerprint"],
            SCF,
        );
    }
    if let Err(error) = schema_validation::validate_fragment(
        &sealed,
        SCHEMA,
        "/$defs/authoring_request",
        &schema_probe,
    ) {
        result.diagnostic(
            Status::Rejected,
            "authoring_construction.request.schema",
            None,
            "request",
            &string(error.message),
        );
        result.request_schema = Check::Rejected;
        return result.finish();
    }
    result.request_schema = if exact_request {
        Check::Qualified
    } else {
        Check::Blocked
    };
    if canonical_result.is_err() {
        return result.finish();
    }
    if !qualify_basis(definition, &sealed, request) {
        result.diagnostic(
            Status::Unavailable,
            "semantic_contract.exact_authority_mismatch",
            None,
            "basis",
            &Json::Null,
        );
    }
    if table_ok && exact_request {
        qualify_intents(request, definition, &sealed, table, binding, &mut result);
    }
    result.finish()
}

fn qualified_resource(
    definition: &Json,
    sealed: &BTreeMap<String, Json>,
    qualification: &Json,
) -> bool {
    let key = text(qualification, "canonical_resource_key");
    let entries: Vec<_> = array(definition, "resourceManifest")
        .iter()
        .filter(|entry| text(entry, "canonicalResourceKey") == key)
        .collect();
    entries.len() == 1
        && sealed.contains_key(key)
        && text(entries[0], "contentDigest") == text(qualification, "content_digest")
}

fn qualify_binding_authority(definition: &Json, sealed: &BTreeMap<String, Json>) -> bool {
    let composition = at(sealed.get(RULES).unwrap_or(&Json::Null), &["composition"]);
    let binding = at(composition, &["binding_authority"]);
    let schema = at(composition, &["schema_authority"]);
    let table = sealed.get(TABLE).unwrap_or(&Json::Null);
    text(binding, "canonical_resource_key") == TABLE
        && text(schema, "canonical_resource_key") == TABLE_SCHEMA
        && qualified_resource(definition, sealed, binding)
        && qualified_resource(definition, sealed, schema)
        && schema_validation::preflight_fragment(sealed, TABLE_SCHEMA, "").is_ok()
        && schema_validation::validate(sealed, TABLE_SCHEMA, table).is_ok()
        && qualify_table(definition, sealed, table)
}

fn qualify_basis(definition: &Json, sealed: &BTreeMap<String, Json>, request: &Json) -> bool {
    let Some(definition) = definition.as_object() else {
        return false;
    };
    let request_basis = request.get("basis").unwrap_or(&Json::Null);
    let sets = [
        ("adc", "authoring-domain", "1.1", "authoring-domain/1.1/"),
        ("authoring", "authoring", "1.7", "authoring/1.7/schema/"),
        (
            "normalized_model",
            "normalized-model",
            "2.4",
            "normalized-model/2.4/schema/",
        ),
    ];
    let ai = request_basis
        .get("architecture_interpretation")
        .unwrap_or(&Json::Null);
    let ai_definition = sealed
        .get("architecture-interpretation/1.2/contract")
        .unwrap_or(&Json::Null);
    let ai_closure = ai.get("authority_closure").unwrap_or(&Json::Null);
    let exact = sets.iter().all(|(name, family, version, prefix)| {
        basis::exact_resource_set(request_basis.get(name), family, version, definition, prefix)
    }) && text(ai, "family") == "architecture-interpretation"
        && text(ai, "version") == "1.2"
        && text(ai, "semantic_contract_fingerprint") == AI_SCF
        && text(ai_definition, "semanticContractFingerprint") == AI_SCF
        && text(ai_closure, "family") == "architecture-interpretation"
        && text(ai_closure, "version") == "1.2"
        && basis::resource_members_match(
            ai_closure.get("resources"),
            array(ai_definition, "resourceManifest"),
        );
    exact
        && array(at(request, &["request"]), "fragments")
            .iter()
            .all(|fragment| {
                basis::exact_resource_set(
                    fragment.get("contract_qualification"),
                    "authoring",
                    "1.7",
                    definition,
                    "authoring/1.7/schema/",
                )
            })
}

/// Rechecks named semantic authorities, not ADC's compact input inventory.
fn qualify_table(definition: &Json, sealed: &BTreeMap<String, Json>, table: &Json) -> bool {
    let selection = table.get("selection").unwrap_or(&Json::Null);
    let keys: Vec<_> = array(selection, "key")
        .iter()
        .filter_map(Json::as_str)
        .collect();
    if keys != ["parent_semantic_type", "child_semantic_type", "relation"]
        || text(selection, "match") != "exact"
        || text(selection, "unknown_relation") != "Rejected"
        || text(selection, "known_relation_without_row") != "Unavailable"
        || text(selection, "multiple_rows") != "publication_invalid"
    {
        return false;
    }
    let mut tuples = BTreeSet::new();
    let mut ids = BTreeSet::new();
    !array(table, "rows").is_empty()
        && array(table, "rows").iter().all(|row| {
            ids.insert(text(row, "binding_id"))
                && tuples.insert(keys.iter().map(|key| text(row, key)).collect::<Vec<_>>())
                && array(table, "relation_vocabulary")
                    .iter()
                    .any(|relation| relation.as_str() == Some(text(row, "relation")))
                && qualify_row(definition, sealed, row)
        })
}

fn qualify_row(definition: &Json, sealed: &BTreeMap<String, Json>, row: &Json) -> bool {
    for name in [
        "ai_authority",
        "adc_authority",
        "parent_schema",
        "child_schema",
    ] {
        if !qualified_resource(definition, sealed, row.get(name).unwrap_or(&Json::Null)) {
            return false;
        }
    }
    let Some(field) = selected_ai_field(row, sealed) else {
        return false;
    };
    let required = at(row, &["required_ai_disposition"]);
    if !required.as_object().is_some_and(|expected| {
        expected
            .iter()
            .all(|(key, value)| field.get(key) == Some(value))
    }) {
        return false;
    }
    let adc = &sealed[text(at(row, &["adc_authority"]), "canonical_resource_key")];
    for role in ["parent", "child"] {
        let ty = text(row, &format!("{role}_semantic_type"));
        let Some((kind, name)) = ty.split_once('/') else {
            return false;
        };
        let types: Vec<_> = array(adc, "types")
            .iter()
            .filter(|ty| {
                text(at(ty, &["key"]), "kind") == kind && text(at(ty, &["key"]), "name") == name
            })
            .collect();
        if types.len() != 1 {
            return false;
        }
        let expected = at(row, &["required_adc_policy", role]);
        if !array(row, "adc_policies_consulted").iter().all(|policy| {
            policy
                .as_str()
                .is_some_and(|name| types[0].get(name) == expected.get(name))
        }) {
            return false;
        }
        if text(at(types[0], &["composition_policy"]), "child_identity") != "preserve"
            || text(at(types[0], &["identity_policy"]), "supplied_identity") != "preserve"
            || text(at(types[0], &["identity_policy"]), "composition_identity")
                != "does_not_manufacture"
        {
            return false;
        }
        if role == "child"
            && !array(at(types[0], &["composition_policy"]), "allowed_parents")
                .iter()
                .any(|p| {
                    format!("{}/{}", text(p, "kind"), text(p, "name"))
                        == text(row, "parent_semantic_type")
                })
        {
            return false;
        }
    }
    let parent = at(row, &["parent_schema"]);
    let child = at(row, &["child_schema"]);
    let parent_key = text(parent, "canonical_resource_key");
    let child_key = text(child, "canonical_resource_key");
    if !parent_key.starts_with("authoring/1.7/schema/")
        || !child_key.starts_with("authoring/1.7/schema/")
    {
        return false;
    }
    let Ok((_, parent_schema)) = schema_validation::resolve_reference(
        sealed,
        parent_key,
        &format!("#{}", text(parent, "schema_pointer")),
    ) else {
        return false;
    };
    let Ok(child_schema) = schema_validation::resolve_reference(
        sealed,
        child_key,
        &format!("#{}", text(child, "schema_pointer")),
    ) else {
        return false;
    };
    let property = text(row, "parent_property");
    let Some(reference) = at(&parent_schema, &["properties", property, "items", "$ref"]).as_str()
    else {
        return false;
    };
    if schema_validation::resolve_reference(sealed, parent_key, reference).ok()
        != Some(child_schema)
    {
        return false;
    }
    // These are supported interpreter vocabulary, never a semantic binding row.
    text(row, "parent_pointer") == format!("/{property}")
        && text(row, "semantic_field_key")
            == format!("{}#/{property}", text(row, "parent_semantic_type"))
        && text(row, "child_field_authority") == "child_schema"
        && text(row, "endpoint_resolution") == "same_request_create_fragment_request_key"
        && text(at(row, &["operations"]), "parent") == "create"
        && text(at(row, &["operations"]), "child") == "create"
        && array(row, "input_modes") == [string("prepared")]
        && text(row, "byte_owner") == "compiler"
        && text(row, "prepared_parent_property") == "absent"
        && text(row, "child_object") == "prepared_fields_plus_established_id"
        && text(at(row, &["ordering"]), "input") == "composition_intent.ordering"
        && text(at(row, &["ordering"]), "meaning") == "authored_parent_membership_sequence"
        && text(at(row, &["ordering"]), "sort") == "ascending_integer"
        && text(at(row, &["ordering"]), "unique_within") == "parent_property"
        && text(at(row, &["ordering"]), "semantic_value") == "ordered_child_canonical_uuids"
        && at(row, &["ordering", "dense_required"]).as_bool() == Some(false)
        && at(row, &["ordering", "written_to_child"]).as_bool() == Some(false)
        && at(row, &["ordering", "request_array_order_semantic"]).as_bool() == Some(false)
}

fn qualify_intents(
    request: &Json,
    definition: &Json,
    sealed: &BTreeMap<String, Json>,
    table: &Json,
    binding: &Json,
    result: &mut Qualification,
) {
    let fragments = array(at(request, &["request"]), "fragments");
    let mut intents: Vec<_> = array(at(request, &["request"]), "compositions")
        .iter()
        .collect();
    intents.sort_by_cached_key(|intent| canonical(intent));
    let mut index: BTreeMap<&str, Vec<&Json>> = BTreeMap::new();
    let mut identities: BTreeMap<&str, Vec<&Json>> = BTreeMap::new();
    let mut references = BTreeSet::new();
    for entry in array(at(request, &["basis", "reference_basis"]), "entries") {
        references.insert(text(entry, "reference_id"));
        references.insert(text(entry, "canonical_uuid"));
    }
    for fragment in fragments {
        index
            .entry(text(fragment, "request_key"))
            .or_default()
            .push(fragment);
        if let Some(id) = identity(fragment) {
            identities.entry(id).or_default().push(fragment);
        } else if text(fragment, "operation") == "create" {
            result
                .outstanding_dependencies
                .insert("canonical_identity_establishment");
            result
                .outstanding_dependencies
                .insert("duplicate_identity_after_identity_establishment");
        }
        for reference in array(fragment, "references") {
            references.insert(text(reference, "reference_key"));
            references.insert(text(reference, "target"));
        }
        if !array(fragment, "composition_keys").is_empty() {
            result.composition(Status::Unavailable, "key_unbound", Some(fragment), fragment);
        }
    }
    for duplicates in identities.values().filter(|items| items.len() > 1) {
        let mut keys: Vec<_> = duplicates
            .iter()
            .map(|f| string(text(f, "request_key")))
            .collect();
        keys.sort_by_cached_key(digest);
        result.diagnostic(
            Status::Rejected,
            "authoring_construction.composition.duplicate_identity",
            identity(duplicates[0]),
            "identity",
            &Json::Array(keys),
        );
    }
    let mut memberships = BTreeSet::new();
    let mut orderings = BTreeSet::new();
    let mut owners: BTreeMap<&str, &str> = BTreeMap::new();
    // Request locators distinguish already-resolved fragment objects. They
    // never supply canonical identity (including in diagnostic identity slots).
    let mut fragment_owners: BTreeMap<&str, &str> = BTreeMap::new();
    let mut edges: BTreeMap<&str, BTreeSet<&str>> = BTreeMap::new();
    let mut endpoints_complete = true;
    for intent in intents {
        let start = result.diagnostics.len();
        let relation = text(intent, "relation");
        let known_relation = array(table, "relation_vocabulary")
            .iter()
            .any(|r| r.as_str() == Some(relation));
        if !known_relation {
            result.composition(Status::Rejected, "relation_unknown", None, intent);
        }
        let mut endpoint = |name: &str| -> Option<&Json> {
            let key = text(intent, name);
            match index.get(key).map(Vec::as_slice) {
                Some([fragment]) => Some(*fragment),
                Some(_) => {
                    result.composition(Status::Rejected, "endpoint_ambiguous", None, intent);
                    endpoints_complete = false;
                    None
                }
                None => {
                    let (status, code) = if references.contains(key) {
                        (Status::Rejected, "reference_not_definition")
                    } else {
                        (Status::Unresolved, "endpoint_unresolved")
                    };
                    result.composition(status, code, None, intent);
                    endpoints_complete = false;
                    None
                }
            }
        };
        let parent = endpoint("parent");
        let child = endpoint("child");
        for fragment in [parent, child].into_iter().flatten() {
            if text(fragment, "operation") != "create" {
                endpoints_complete = false;
            }
            match text(fragment, "operation") {
                "retire" => result.composition(
                    Status::Rejected,
                    "operation_unsupported",
                    Some(fragment),
                    intent,
                ),
                "reference" => result.composition(
                    Status::Rejected,
                    "reference_not_definition",
                    Some(fragment),
                    intent,
                ),
                "update" => result.composition(
                    Status::Unavailable,
                    "update_unavailable",
                    Some(fragment),
                    intent,
                ),
                _ => (),
            }
            if text(fragment, "input_mode") != "prepared" {
                result.diagnostic(
                    Status::Unavailable,
                    "authoring_construction.fragment.compact_unavailable",
                    identity(fragment),
                    relation,
                    intent,
                );
            }
        }
        let (Some(parent), Some(child)) = (parent, child) else {
            continue;
        };
        let parent_key = text(parent, "request_key");
        let child_key = text(child, "request_key");
        if !memberships.insert((parent_key, child_key)) {
            result.composition(
                Status::Rejected,
                "duplicate_membership",
                Some(parent),
                intent,
            );
        }
        if governed_containment(table, relation, parent, child) {
            edges.entry(parent_key).or_default().insert(child_key);
            // DEC-0274: the same child fragment cannot acquire two owners,
            // even before its one eventual canonical UUID is established.
            let same_fragment_conflict = fragment_owners
                .insert(child_key, parent_key)
                .is_some_and(|previous| previous != parent_key);
            let canonical_conflict = identity(child).is_some_and(|child_identity| {
                owners
                    .insert(child_identity, parent_key)
                    .is_some_and(|previous| previous != parent_key)
            });
            if same_fragment_conflict || canonical_conflict {
                result.composition(Status::Rejected, "duplicate_identity", Some(child), intent);
            }
        }
        let values = BTreeMap::from([
            ("parent_semantic_type", text(parent, "semantic_type")),
            ("child_semantic_type", text(child, "semantic_type")),
            ("relation", relation),
        ]);
        let rows: Vec<_> = array(table, "rows")
            .iter()
            .filter(|row| {
                array(at(table, &["selection"]), "key").iter().all(|key| {
                    key.as_str()
                        .is_some_and(|key| values.get(key).copied() == Some(text(row, key)))
                })
            })
            .collect();
        if known_relation && rows.is_empty() {
            result.composition(
                Status::Unavailable,
                "binding_unavailable",
                Some(parent),
                intent,
            );
        }
        if rows.len() != 1 {
            continue;
        }
        let row = rows[0];
        if at(parent, &["fields"])
            .get(text(row, "parent_property"))
            .is_some()
        {
            result.composition(Status::Rejected, "ownership_conflict", Some(parent), intent);
        }
        let ordering = intent.get("ordering").unwrap_or(&Json::Null);
        if !orderings.insert((
            parent_key,
            text(row, "parent_property"),
            ordering
                .as_u64()
                .expect("schema-validated nonnegative integer"),
        )) {
            result.composition(Status::Rejected, "ordering_conflict", Some(parent), intent);
        }
        // Recheck per-fragment exact Authoring qualification before producing
        // a reusable decision; supplied UUIDs are preserved, absent IDs pending.
        if ![parent, child].iter().all(|fragment| {
            basis::exact_resource_set(
                fragment.get("contract_qualification"),
                "authoring",
                "1.7",
                definition.as_object().expect("qualified definition"),
                "authoring/1.7/schema/",
            )
        }) {
            result.composition(
                Status::Unavailable,
                "authority_inconsistent",
                Some(parent),
                intent,
            );
        }
        for fragment in [parent, child] {
            if let Some(id) = at(fragment, &["fields"]).get("id") {
                if !id.as_str().is_some_and(basis::is_uuid_v7) {
                    result.diagnostic(
                        Status::Rejected,
                        "authoring_construction.request.schema",
                        None,
                        "identity",
                        id,
                    );
                }
            }
        }
        if result.diagnostics.len() == start {
            result.bindings.push(BindingDecision {
                parent_request_key: parent_key.into(),
                child_request_key: child_key.into(),
                parent_identity: identity(parent).map(str::to_owned),
                child_identity: identity(child).map(str::to_owned),
                ordering: ordering.clone(),
                binding: row.clone(),
                qualified_semantic_field: selected_ai_field(row, sealed)
                    .expect("qualified unique AI field")
                    .clone(),
                acc_fingerprint: SCF.into(),
                binding_resource_key: TABLE.into(),
                binding_content_digest: text(binding, "content_digest").into(),
            });
        }
    }
    // Cycle evidence is the set of participating request keys, not traversal
    // positions. Compute reachability per vertex for deterministic diagnostics.
    let cyclic: Vec<_> = edges
        .keys()
        .filter(|start| reaches(start, &edges))
        .map(|key| string(*key))
        .collect();
    if !cyclic.is_empty() {
        result.diagnostic(
            Status::Rejected,
            "authoring_construction.composition.cycle",
            None,
            "contains",
            &Json::Array(cyclic),
        );
    }
    result.endpoint_resolution = if endpoints_complete {
        Check::Qualified
    } else {
        Check::Blocked
    };
}

/// Structural containment meaning comes from the qualified table, not an
/// arbitrary relation string or a successful full binding decision. ACC12-20
/// requires recognizing a cycle of containment intents even when one semantic
/// type pair is unsupported. Endpoint-policy failures do not establish an edge.
fn governed_containment(table: &Json, relation: &str, parent: &Json, child: &Json) -> bool {
    array(table, "relation_vocabulary")
        .iter()
        .any(|r| r.as_str() == Some(relation))
        && array(table, "rows").iter().any(|row| {
            text(row, "relation") == relation
                && text(at(row, &["required_ai_disposition"]), "destination_ref")
                    == "child_membership"
                && [("parent", parent), ("child", child)]
                    .into_iter()
                    .all(|(role, fragment)| {
                        text(fragment, "operation") == text(at(row, &["operations"]), role)
                            && array(row, "input_modes")
                                .iter()
                                .any(|mode| mode.as_str() == Some(text(fragment, "input_mode")))
                    })
        })
}

fn reaches<'a>(start: &'a str, edges: &BTreeMap<&'a str, BTreeSet<&'a str>>) -> bool {
    let mut pending = vec![start];
    let mut seen = BTreeSet::new();
    while let Some(node) = pending.pop() {
        if !seen.insert(node) {
            continue;
        }
        if let Some(next) = edges.get(node) {
            for target in next {
                if *target == start {
                    return true;
                }
                pending.push(*target);
            }
        }
    }
    false
}

fn identity(fragment: &Json) -> Option<&str> {
    at(fragment, &["fields", "id"])
        .as_str()
        .filter(|id| basis::is_uuid_v7(id))
}
fn selected_ai_field<'a>(row: &Json, sealed: &'a BTreeMap<String, Json>) -> Option<&'a Json> {
    let ai = sealed.get(text(at(row, &["ai_authority"]), "canonical_resource_key"))?;
    let mut fields = array(ai, "semantic_types")
        .iter()
        .flat_map(|ty| array(ty, "field_dispositions"))
        .filter(|field| text(field, "semantic_field_key") == text(row, "semantic_field_key"));
    let field = fields.next()?;
    if fields.next().is_some() {
        None
    } else {
        Some(field)
    }
}
fn replace_schema_literal(value: &mut Json, path: &[&str], literal: &str) {
    let Some((key, rest)) = path.split_first() else {
        return;
    };
    let Some(child) = value
        .as_object_mut()
        .and_then(|object| object.get_mut(*key))
    else {
        return;
    };
    if rest.is_empty() {
        if child.as_str().is_some() {
            *child = string(literal);
        }
    } else {
        replace_schema_literal(child, rest, literal);
    }
}
/// Projection only, never verification. Call only after exact closure succeeds.
fn manifest_resources(definition: &Json, resources: &[Json]) -> BTreeMap<String, Json> {
    let names: BTreeSet<_> = array(definition, "resourceManifest")
        .iter()
        .map(|entry| text(entry, "canonicalResourceKey"))
        .collect();
    resources
        .iter()
        .filter(|entry| names.contains(text(entry, "canonicalResourceKey")))
        .map(|entry| {
            (
                text(entry, "canonicalResourceKey").to_owned(),
                entry.get("content").cloned().unwrap_or(Json::Null),
            )
        })
        .collect()
}

fn at<'a>(value: &'a Json, path: &[&str]) -> &'a Json {
    path.iter()
        .fold(value, |v, key| v.get(key).unwrap_or(&Json::Null))
}
fn text<'a>(value: &'a Json, key: &str) -> &'a str {
    value.get(key).and_then(Json::as_str).unwrap_or("")
}
fn array<'a>(value: &'a Json, key: &str) -> &'a [Json] {
    value
        .get(key)
        .and_then(Json::as_array)
        .map(Vec::as_slice)
        .unwrap_or(&[])
}
fn canonical(value: &Json) -> String {
    let mut out = String::new();
    semantic_contract::canonicalize_value(value, &mut out).expect("JSON from a qualified boundary");
    out
}
fn digest(value: &Json) -> String {
    format!("{:x}", Sha256::digest(canonical(value).as_bytes()))
}

#[cfg(test)]
#[path = "authoring_construction_v12_tests.rs"]
mod tests;
