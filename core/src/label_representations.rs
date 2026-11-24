//! Private representation-only labels over independently verified semantic fields.
//! Existing catalog declarations select inputs; this module owns no mapping policy.
use super::{array, at, get, rejected, text, unavailable};
use crate::architecture_interpretation_v13::{self as fields, Authority};
use crate::candidate_authority::{self as authority, Qualification};
use crate::identity_representation::{Finding, Inputs, SealedSources, Selection, Status};
use crate::{schema_validation as schema, string, Json};
use std::collections::{BTreeMap, BTreeSet};

const CATALOG: &str = "architecture-interpretation/1.5/required-output-derivations";
const COMPANION: &str = "architecture-interpretation/1.5/required-output-derivations.schema";

/// Definition evidence, not instance applicability or a new normative catalog.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Definition {
    pub semantic_type: String,
    pub branch: String,
    pub destination: String,
    pub rule_id: String,
    pub source_field: String,
    pub semantic_field_key: String,
    declaration: Json,
    source_schema: Json,
    rule_authority: Json,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Label {
    pub id: String,
    pub value: String,
    pub definition: Definition,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Projection {
    status: Status,
    findings: Vec<Finding>,
    values: Vec<Label>,
    semantic_evidence: Option<super::Projection>,
    authorities: Vec<authority::Authority>,
    basis: String,
}
impl Projection {
    pub(crate) fn status(&self) -> Status {
        self.status
    }
    pub(crate) fn findings(&self) -> &[Finding] {
        &self.findings
    }
    pub(crate) fn values(&self) -> &[Label] {
        &self.values
    }
    pub(crate) fn semantics(&self) -> Option<&super::Projection> {
        self.semantic_evidence.as_ref()
    }
    pub(crate) fn complete_interpretation(&self) -> Status {
        Status::Unavailable
    }
    fn failure(mut findings: Vec<Finding>) -> Self {
        findings.sort();
        findings.dedup();
        Self {
            status: findings
                .first()
                .map(|f| f.status)
                .unwrap_or(Status::Unavailable),
            findings,
            values: vec![],
            semantic_evidence: None,
            authorities: vec![],
            basis: String::new(),
        }
    }
}
fn reference<'a>(
    resources: &'a BTreeMap<String, Json>,
    r: &Json,
) -> Result<&'a Json, Vec<Finding>> {
    let key = text(r, "canonical_resource_key");
    let doc = resources
        .get(key)
        .ok_or_else(|| unavailable(key, "Selected resource is missing"))?;
    if text(r, "content_digest")
        != format!("sha256:{}", crate::authoring_construction_v12::digest(doc))
    {
        return Err(rejected(
            key,
            "Reference does not qualify exact resource content",
        ));
    }
    at(doc, text(r, "schema_pointer"))
        .ok_or_else(|| rejected(key, "Invalid exact schema/rule selector"))
}
fn check_value(map: &BTreeMap<String, Json>, r: &Json, v: &Json) -> Result<(), Vec<Finding>> {
    let key = text(r, "canonical_resource_key");
    let p = text(r, "schema_pointer");
    schema::preflight_fragment(map, key, p).map_err(|e| unavailable(key, e.message))?;
    schema::validate_fragment(map, key, p, v).map_err(|e| rejected(&e.path, e.message))
}
fn string_schema(
    resources: &BTreeMap<String, Json>,
    map: &BTreeMap<String, Json>,
    r: &Json,
) -> Result<(), Vec<Finding>> {
    let mut key = text(r, "canonical_resource_key").to_owned();
    let mut node = reference(resources, r)?.clone();
    let mut seen = BTreeSet::new();
    while let Some(link) = node.get("$ref").and_then(Json::as_str) {
        if !seen.insert((key.clone(), link.to_owned())) {
            return Err(unavailable(&key, "Recursive string type qualification"));
        }
        (key, node) =
            schema::resolve_reference(map, &key, link).map_err(|e| unavailable(&key, e.message))?;
    }
    if text(&node, "type") != "string" {
        return Err(unavailable(
            &key,
            "Exclusive string input type cannot be established",
        ));
    }
    Ok(())
}
fn inventory(q: &Qualification, engine: &Authority) -> Result<Vec<Definition>, Vec<Finding>> {
    compile_inventory(q.resources(), engine)
}
// Pure bounded data checks, called only after authority qualification in production.
// Tests may fault-inject untrusted copies here; no authority token is constructed.
fn compile_inventory(
    resources: &BTreeMap<String, Json>,
    engine: &Authority,
) -> Result<Vec<Definition>, Vec<Finding>> {
    let map = fields::qualified_schema_map(resources).map_err(|e| unavailable("schema", e))?;
    let c = resources
        .get(CATALOG)
        .ok_or_else(|| unavailable(CATALOG, "Required output authority missing"))?;
    schema::preflight_fragment(&map, COMPANION, "")
        .map_err(|e| unavailable(COMPANION, e.message))?;
    schema::validate(&map, COMPANION, c).map_err(|e| rejected(CATALOG, e.message))?;
    let binding = get(
        get(get(c, "inherited_output_authority"), "local_rule_bindings"),
        "literal_string_copy",
    );
    let operation = reference(resources, binding)?;
    if operation != get(c, "operation")
        || text(operation, "id") != "literal_string_copy"
        || text(operation, "input_type") != "string"
        || text(operation, "output_type") != "string"
        || get(operation, "input_count") != &Json::Number(1u64.into())
        || get(operation, "fallback") != &Json::Bool(false)
        || get(operation, "formatting") != &Json::Bool(false)
        || text(operation, "presence") != "required_authored_input"
        || text(operation, "semantic_ownership")
            != "none_original_authored_field_remains_significant_once"
    {
        return Err(rejected(
            CATALOG,
            "Unsupported operation, fallback or semantic ownership",
        ));
    }
    let mut definitions = vec![];
    let mut identities = BTreeSet::new();
    let mut types = BTreeSet::new();
    for t in array(c, "types") {
        let ty = text(t, "semantic_type");
        let branch = text(t, "output_branch");
        if !types.insert(ty) {
            return Err(rejected(ty, "Duplicate type declaration"));
        }
        for o in array(t, "outputs")
            .iter()
            .filter(|o| text(get(o, "producer"), "kind") == "literal_string_copy")
        {
            let dest = text(o, "destination");
            let producer = get(o, "producer");
            let field = text(producer, "source_field");
            let rid = text(producer, "rule_id");
            if array(t, "outputs")
                .iter()
                .filter(|other| text(other, "destination") == dest)
                .count()
                != 1
                || !identities.insert(rid.to_owned())
            {
                return Err(rejected(
                    dest,
                    "Missing unique producer or competing rule identity",
                ));
            }
            if text(o, "status") != "QUALIFIED"
                || text(o, "classification") != "representation_only"
                || text(o, "semantic_equality")
                    != "original_authored_input_once_not_generated_label"
                || text(get(producer, "rule"), "local_rule") != "literal_string_copy"
                || !["regular", "normative-proposition"].contains(&branch)
                || !["/name", "/summary"].contains(&dest)
                || rid.is_empty()
                || !array(o, "prerequisites").is_empty()
            {
                return Err(unavailable(
                    dest,
                    "No admitted literal label producer with complete applicability authority",
                ));
            }
            let roots: Vec<_> = array(c, "branches")
                .iter()
                .filter(|b| text(b, "branch_id") == branch)
                .collect();
            let [root] = roots.as_slice() else {
                return Err(rejected(branch, "Ambiguous output branch"));
            };
            let root_schema = get(root, "schema");
            reference(resources, root_schema)?;
            let target = get(o, "destination_schema");
            reference(resources, target)?;
            if text(target, "canonical_resource_key") != text(root_schema, "canonical_resource_key")
                || text(target, "schema_pointer")
                    != format!("{}/properties{dest}", text(root_schema, "schema_pointer"))
            {
                return Err(rejected(
                    dest,
                    "Destination does not select its exact governed branch",
                ));
            }
            schema::preflight_fragment(
                &map,
                text(target, "canonical_resource_key"),
                text(target, "schema_pointer"),
            )
            .map_err(|e| unavailable(dest, e.message))?;
            let source = get(t, "source_schema");
            let parent = reference(resources, source)?;
            let [input] = array(producer, "inputs") else {
                return Err(rejected(rid, "Exactly one input required"));
            };
            reference(resources, input)?;
            let escaped = field.replace('~', "~0").replace('/', "~1");
            if field.is_empty()
                || text(input, "canonical_resource_key") != text(source, "canonical_resource_key")
                || text(input, "schema_pointer")
                    != format!("{}/properties/{escaped}", text(source, "schema_pointer"))
                || !array(parent, "required")
                    .iter()
                    .any(|v| v.as_str() == Some(field))
            {
                return Err(rejected(
                    rid,
                    "Input selector/presence is not the exact required authored property",
                ));
            }
            schema::preflight_fragment(
                &map,
                text(input, "canonical_resource_key"),
                text(input, "schema_pointer"),
            )
            .map_err(|e| unavailable(field, e.message))?;
            string_schema(resources, &map, input)?;
            let f = engine
                .field(ty, &format!("/{escaped}"))
                .map_err(|e| unavailable(rid, e))?;
            let selector = text(f, "schema_selector");
            let (key, _) =
                schema::resolve_reference(&map, "authoring/1.7/schema/adr-common.schema", selector)
                    .map_err(|e| unavailable(field, e.message))?;
            if key != text(input, "canonical_resource_key")
                || selector.split_once('#').map(|(_, p)| p).unwrap_or("")
                    != text(input, "schema_pointer")
                || !["canonical_field_placement", "direct_semantic_value"]
                    .contains(&text(f, "disposition"))
            {
                return Err(rejected(
                    rid,
                    "Original semantic field authority would be lost or substituted",
                ));
            }
            definitions.push(Definition {
                semantic_type: ty.into(),
                branch: branch.into(),
                destination: dest.into(),
                rule_id: rid.into(),
                source_field: field.into(),
                semantic_field_key: text(f, "semantic_field_key").into(),
                declaration: o.clone(),
                source_schema: source.clone(),
                rule_authority: binding.clone(),
            });
        }
    }
    definitions.sort_by(|a, b| {
        (&a.semantic_type, &a.destination).cmp(&(&b.semantic_type, &b.destination))
    });
    Ok(definitions)
}
/// Static definitions only; no source instance or output is qualified here.
pub(crate) fn qualify_catalog(i: Inputs<'_>) -> Result<Vec<Definition>, Vec<Finding>> {
    let q = authority::qualify(i.nm, i.ai, i.acc);
    if q.status() != authority::Status::AuthorityQualified {
        return Err(q
            .findings()
            .iter()
            .map(|f| Finding {
                status: if f.status == authority::Status::Rejected {
                    Status::Rejected
                } else {
                    Status::Unavailable
                },
                key: f.key.clone(),
                detail: f.detail.clone(),
            })
            .collect());
    }
    let engine = Authority::from_candidate(&q).map_err(|e| unavailable(CATALOG, e))?;
    inventory(&q, &engine)
}
struct Prepared {
    source: super::Prepared,
    values: Vec<(usize, Definition)>,
    schemas: BTreeMap<String, Json>,
}
fn prepare(
    i: Inputs<'_>,
    s: Option<&SealedSources>,
    selected: &[Selection],
) -> Result<Prepared, Vec<Finding>> {
    let source = super::prepare(i, s, selected)?;
    let defs = inventory(&source.q, &source.engine)?;
    let schemas =
        fields::qualified_schema_map(source.q.resources()).map_err(|e| unavailable("schema", e))?;
    let mut values = vec![];
    for (n, u) in source.selected.iter().enumerate() {
        let applicable: Vec<_> = defs
            .iter()
            .filter(|d| d.semantic_type == u.selection.semantic_type)
            .collect();
        if applicable.is_empty() {
            return Err(unavailable(
                &u.selection.semantic_type,
                "No qualified literal label definition for this source branch",
            ));
        }
        for d in applicable {
            if d.branch != text(&u.row, "output_branch")
                || Some(&d.source_schema) != u.row.get("source_schema")
            {
                return Err(rejected(
                    &d.rule_id,
                    "Source occurrence and label branch qualification differ",
                ));
            }
            let input = u.value.get(&d.source_field).ok_or_else(|| {
                rejected(
                    &d.semantic_field_key,
                    "Required authored label input missing",
                )
            })?;
            if input.as_str().is_none() {
                return Err(rejected(
                    &d.semantic_field_key,
                    "Authored label input is not a string",
                ));
            }
            check_value(
                &schemas,
                &array(get(&d.declaration, "producer"), "inputs")[0],
                input,
            )?;
            check_value(&schemas, get(&d.declaration, "destination_schema"), input)?;
            values.push((n, d.clone()));
        }
    }
    Ok(Prepared {
        source,
        values,
        schemas,
    })
}
fn semantic_failure(p: &super::Projection) -> Vec<Finding> {
    p.findings().to_vec()
}
pub(crate) fn execute(
    i: Inputs<'_>,
    s: Option<&SealedSources>,
    selected: &[Selection],
) -> Projection {
    let p = match prepare(i, s, selected) {
        Ok(p) => p,
        Err(e) => return Projection::failure(e),
    };
    let semantic = super::execute(i, s, selected);
    if semantic.status() != Status::Executed {
        return Projection::failure(semantic_failure(&semantic));
    }
    let verified = super::verify(i, s, selected, &semantic);
    if verified.status() != Status::Verified {
        return Projection::failure(semantic_failure(&verified));
    }
    let mut values = vec![];
    for (n, d) in p.values {
        let u = &p.source.selected[n];
        let original = semantic
            .units()
            .iter()
            .find(|v| v.id == text(&u.value, "id"))
            .unwrap();
        if original.placements.contains_key(&d.destination) {
            return Projection::failure(rejected(
                &d.rule_id,
                "Representation competes with an authored destination",
            ));
        }
        let value = u
            .value
            .get(&d.source_field)
            .and_then(Json::as_str)
            .unwrap()
            .to_owned();
        values.push(Label {
            id: text(&u.value, "id").into(),
            value,
            definition: d,
        });
    }
    Projection {
        status: Status::Executed,
        findings: vec![],
        values,
        semantic_evidence: Some(semantic),
        authorities: p.source.q.authorities().to_vec(),
        basis: p.source.basis,
    }
}
/// Inverse byte verification. No invocation of the label or semantic producer.
pub(crate) fn verify(
    i: Inputs<'_>,
    s: Option<&SealedSources>,
    selected: &[Selection],
    supplied: &Projection,
) -> Projection {
    let p = match prepare(i, s, selected) {
        Ok(p) => p,
        Err(e) => return Projection::failure(e),
    };
    if supplied.status == Status::Unavailable
        && supplied.values.is_empty()
        && supplied.semantic_evidence.is_none()
        && supplied.authorities.is_empty()
        && supplied.basis.is_empty()
    {
        return Projection::failure(unavailable(
            "labels",
            "No executed label/semantic evidence supplied",
        ));
    }
    let mut findings = vec![];
    if supplied.status != Status::Executed
        || !supplied.findings.is_empty()
        || supplied.values.len() != p.values.len()
        || supplied.authorities != p.source.q.authorities()
        || supplied.basis != p.source.basis
    {
        findings.extend(rejected(
            "labels",
            "Forged, partial or stale label envelope",
        ));
    }
    let checked = match &supplied.semantic_evidence {
        Some(semantic) => super::verify(i, s, selected, semantic),
        None => {
            return Projection::failure(rejected(
                "semantic_fields",
                "Original semantic-field evidence is missing",
            ))
        }
    };
    if checked.status() != Status::Verified {
        findings.extend(semantic_failure(&checked));
    }
    let mut seen = BTreeSet::new();
    for label in &supplied.values {
        if !seen.insert((&label.id, &label.definition.destination)) {
            findings.extend(rejected(&label.id, "Duplicate label producer"));
        }
    }
    for (n, d) in &p.values {
        let original = &p.source.selected[*n];
        let id = text(&original.value, "id");
        let matches: Vec<_> = supplied
            .values
            .iter()
            .filter(|v| v.id == id && v.definition.destination == d.destination)
            .collect();
        let [label] = matches.as_slice() else {
            findings.extend(rejected(&d.rule_id, "Missing or competing label outputs"));
            continue;
        };
        if label.definition != *d {
            findings.extend(rejected(
                &d.rule_id,
                "Wrong source, rule or destination qualification",
            ));
        }
        let value = original
            .value
            .get(&d.source_field)
            .and_then(Json::as_str)
            .unwrap();
        if !value.as_bytes().iter().eq(label.value.as_bytes().iter()) {
            findings.extend(rejected(
                &d.rule_id,
                "Complete output bytes differ from the qualified original authored string",
            ));
        }
        if let Err(mut e) = check_value(
            &p.schemas,
            get(&d.declaration, "destination_schema"),
            &string(&label.value),
        ) {
            findings.append(&mut e);
        }
        if let Some(unit) = checked.units().iter().find(|u| u.id == id) {
            if unit.placements.contains_key(&d.destination) {
                findings.extend(rejected(
                    &d.rule_id,
                    "Competing authored and derived producers",
                ));
            }
        }
    }
    if !findings.is_empty() {
        return Projection::failure(findings);
    }
    let mut result = supplied.clone();
    result.status = Status::Verified;
    result
}

#[cfg(test)]
#[path = "label_representations_tests.rs"]
mod tests;

#[cfg(test)]
#[path = "nested_semantic_fields_tests.rs"]
mod nested_tests;

#[cfg(test)]
#[path = "physical_system_fields_tests.rs"]
mod physical_system_tests;
