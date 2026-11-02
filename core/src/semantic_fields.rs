//! Private native-source semantic fields. Reuses the inherited field engine;
//! independent verification reads original inputs and checks inverse destinations.
use crate::architecture_interpretation_v13::{self as fields, Authority, ContextualFact, Unit};
use crate::candidate_authority::Qualification;
use crate::identity_representation::{
    self as identity, Finding, Inputs, SealedSources, Selection, Status,
};
use crate::{object, string, Json};
use std::collections::BTreeSet;

const FD: &str = "architecture-interpretation/1.3/field-dispositions-1.7-to-2.5";
const OWN: &str = "architecture-interpretation/1.3/lifecycle-ownership";
const CARRIER: &str = "architecture-interpretation/1.3/lifecycle-provenance.schema";
const FACTS: &str = "architecture-interpretation/1.3/contextual-facts";
const NM: &str = "normalized-model/2.5/schema/normalized-entity.schema";
fn get<'a>(v: &'a Json, k: &str) -> &'a Json {
    v.get(k).unwrap_or(&Json::Null)
}
fn text<'a>(v: &'a Json, k: &str) -> &'a str {
    v.get(k).and_then(Json::as_str).unwrap_or("")
}
fn array<'a>(v: &'a Json, k: &str) -> &'a [Json] {
    v.get(k)
        .and_then(Json::as_array)
        .map(Vec::as_slice)
        .unwrap_or(&[])
}
fn at<'a>(v: &'a Json, p: &str) -> Option<&'a Json> {
    if p.is_empty() {
        return Some(v);
    }
    p.strip_prefix('/')?.split('/').try_fold(v, |v, s| {
        let s = s.replace("~1", "/").replace("~0", "~");
        match v {
            Json::Object(o) => o.get(&s),
            Json::Array(a) => s.parse::<usize>().ok().and_then(|n| a.get(n)),
            _ => None,
        }
    })
}
fn issue(status: Status, key: &str, detail: impl Into<String>) -> Vec<Finding> {
    vec![Finding {
        status,
        key: key.into(),
        detail: detail.into(),
    }]
}
fn rejected(key: &str, detail: impl Into<String>) -> Vec<Finding> {
    issue(Status::Rejected, key, detail)
}
fn unavailable(key: &str, detail: impl Into<String>) -> Vec<Finding> {
    issue(Status::Unavailable, key, detail)
}
fn from_fields(s: fields::Status) -> Status {
    if s == fields::Status::Rejected {
        Status::Rejected
    } else {
        Status::Unavailable
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Projection {
    status: Status,
    findings: Vec<Finding>,
    units: Vec<Unit>,
    representations: Option<identity::Projection>,
    authorities: Vec<crate::candidate_authority::Authority>,
    basis_digest: String,
}
impl Projection {
    pub(crate) fn status(&self) -> Status {
        self.status
    }
    pub(crate) fn findings(&self) -> &[Finding] {
        &self.findings
    }
    pub(crate) fn units(&self) -> &[Unit] {
        &self.units
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
            units: vec![],
            representations: None,
            authorities: vec![],
            basis_digest: String::new(),
        }
    }
}
struct Prepared {
    q: Qualification,
    engine: Authority,
    all: Vec<identity::Unit>,
    selected: Vec<identity::Unit>,
    basis: String,
}
fn prepare(
    i: Inputs<'_>,
    s: Option<&SealedSources>,
    selected: &[Selection],
) -> Result<Prepared, Vec<Finding>> {
    let (q, all, units, basis) = identity::qualified_occurrences(i, s, selected)?;
    let engine = Authority::from_candidate(&q).map_err(|e| unavailable(FD, e))?;
    // Selecting a parent requires execution of every discovered child unit. A
    // membership list can never conceal omitted child semantics.
    for parent in &units {
        for child in &all {
            if child.selection.source_ref == parent.selection.source_ref
                && child
                    .selection
                    .pointer
                    .starts_with(&format!("{}/", parent.selection.pointer))
                && !units.iter().any(|u| u.selection == child.selection)
            {
                return Err(unavailable(
                    &child.selection.semantic_type,
                    "Selected parent has an unexecuted child semantic unit",
                ));
            }
        }
    }
    Ok(Prepared {
        q,
        engine,
        all,
        selected: units,
        basis,
    })
}
fn schema_error(e: crate::schema_validation::SchemaError) -> Vec<Finding> {
    rejected(&e.path, e.message)
}
fn check_reference(p: &Prepared, r: &Json) -> Result<(), Vec<Finding>> {
    let k = text(r, "canonical_resource_key");
    let value =
        p.q.resources()
            .get(k)
            .ok_or_else(|| unavailable(k, "Missing qualified resource"))?;
    if format!(
        "sha256:{}",
        crate::authoring_construction_v12::digest(value)
    ) != text(r, "content_digest")
    {
        return Err(rejected(
            k,
            "Reference digest differs from independently qualified resource",
        ));
    }
    at(value, text(r, "schema_pointer")).ok_or_else(|| rejected(k, "Wrong exact selector"))?;
    Ok(())
}
/// Derive native declaring evidence from schema-qualified source containment,
/// never from a composition request or a caller's asserted owner.
fn context(
    p: &Prepared,
    child: &identity::Unit,
) -> Result<Option<(Json, ContextualFact, Json)>, Vec<Finding>> {
    if text(&child.row, "output_branch") == "normative-proposition" {
        return Ok(None);
    }
    if child.selection.semantic_type.starts_with("adr/") {
        return Ok(None);
    }
    let Some((parent_type, parent_id, pattern)) = &child.owner else {
        return Err(unavailable("declaring_context", "No declaring ADR source"));
    };
    let parents: Vec<_> = p
        .all
        .iter()
        .filter(|u| {
            u.selection.source_ref == child.selection.source_ref
                && u.selection.pointer.is_empty()
                && u.selection.semantic_type == *parent_type
                && text(&u.value, "id") == parent_id
        })
        .collect();
    let [parent] = parents.as_slice() else {
        return Err(rejected(parent_id, "Missing or competing declaring ADR"));
    };
    let rows: Vec<_> = array(&p.q.resources()[OWN], "rows")
        .iter()
        .filter(|r| {
            text(r, "parent_semantic_type") == parent_type
                && text(r, "child_semantic_type") == child.selection.semantic_type
                && text(r, "source_instance_pattern") == pattern
        })
        .collect();
    let [rule] = rows.as_slice() else {
        return Err(unavailable(OWN, "No unique qualified ownership rule"));
    };
    if rule.get("source_schema") != parent.row.get("source_schema")
        || rule.get("child_schema") != child.row.get("source_schema")
        || text(rule, "governing_rule") != "literal_declaring_adr_status"
    {
        return Err(rejected(OWN, "Ownership schema or literal rule mismatch"));
    }
    for name in [
        "source_schema",
        "parent_schema",
        "child_schema",
        "status_source_authority",
    ] {
        check_reference(p, get(rule, name))?;
    }
    let map =
        fields::qualified_schema_map(p.q.resources()).map_err(|e| unavailable("schema", e))?;
    for r in array(rule, "ownership_schema_path") {
        check_reference(p, r)?;
        let key = text(r, "canonical_resource_key");
        let sp = text(r, "schema_pointer");
        // Exact schema path must resolve to this child's qualified schema, not
        // merely validate an identically shaped unowned object.
        let mut node = at(&map[key], sp).unwrap().clone();
        let mut k = key.to_owned();
        while let Some(r) = node.get("$ref").and_then(Json::as_str) {
            (k, node) =
                crate::schema_validation::resolve_reference(&map, &k, r).map_err(schema_error)?;
        }
        let cs = get(&child.row, "source_schema");
        if k != text(cs, "canonical_resource_key")
            || Some(&node) != at(&map[&k], text(cs, "schema_pointer"))
        {
            return Err(rejected(
                OWN,
                "Schema path does not establish child containment",
            ));
        }
    }
    let status_key = text(rule, "status_semantic_field_key");
    let sf = p
        .engine
        .field(parent_type, "/status")
        .map_err(|e| unavailable(status_key, e))?;
    if text(sf, "semantic_field_key") != status_key {
        return Err(rejected(status_key, "Wrong authored status identity"));
    }
    let lifecycle = p
        .engine
        .lifecycle(parent_type, get(&parent.value, "status"))
        .map_err(|e| rejected(status_key, e))?;
    // Actual inherited authority identity is preserved. The enclosing candidate
    // remains AI1.5; no fabricated AI1.5 ownership rule is introduced.
    let inherited = &p.q.resources()["architecture-interpretation/1.3/contract"];
    let carrier = fields::lifecycle_carrier(
        rule,
        get(&parent.value, "id"),
        text(inherited, "semanticContractFingerprint"),
        &format!(
            "sha256:{}",
            crate::authoring_construction_v12::digest(&p.q.resources()[OWN])
        ),
    );
    crate::schema_validation::preflight_fragment(&map, CARRIER, "")
        .map_err(|e| unavailable(CARRIER, e.message))?;
    crate::schema_validation::validate(&map, CARRIER, &carrier).map_err(schema_error)?;
    let facts = array(&p.q.resources()[FACTS], "facts");
    if facts.len() != 1 {
        return Err(rejected(FACTS, "Competing contextual facts"));
    }
    let fact = ContextualFact {
        semantic_field_key: text(&facts[0], "semantic_field_key").into(),
        semantic_identity: text(&child.value, "id").into(),
        value: carrier.clone(),
    };
    Ok(Some((carrier, fact, lifecycle)))
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
    let mut findings = vec![];
    let mut units = vec![];
    for u in &p.selected {
        let mut projected =
            fields::project_native_fields(&p.engine, &u.selection.semantic_type, &u.value);
        findings.extend(projected.findings.iter().map(|f| Finding {
            status: from_fields(f.status),
            key: f.key.clone(),
            detail: f.detail.clone(),
        }));
        if let Some(mut out) = projected.units.pop() {
            match context(&p, u) {
                Ok(Some((carrier, fact, value))) => {
                    out.lifecycle_provenance = Some(carrier);
                    out.contextual_fact = Some(fact);
                    if out
                        .placements
                        .insert("/lifecycle_stage".into(), value)
                        .is_some()
                    {
                        findings.extend(rejected(&out.id, "Competing lifecycle producers"));
                    }
                }
                Ok(None) => {}
                Err(mut e) => findings.append(&mut e),
            }
            units.push(out);
        }
    }
    if !findings.is_empty() {
        return Projection::failure(findings);
    }
    let representations = identity::execute(i, s, selected);
    if representations.status() != Status::Executed {
        return Projection::failure(representations.findings().to_vec());
    }
    Projection {
        status: Status::Executed,
        findings,
        units,
        representations: Some(representations),
        authorities: p.q.authorities().to_vec(),
        basis_digest: p.basis,
    }
}

fn equal_value(a: &Json, b: &Json, ordering: &str) -> bool {
    if ordering == "unordered_multiset" {
        match (a.as_array(), b.as_array()) {
            (Some(a), Some(b)) => {
                let mut a: Vec<_> = a
                    .iter()
                    .map(crate::authoring_construction_v12::canonical)
                    .collect();
                let mut b: Vec<_> = b
                    .iter()
                    .map(crate::authoring_construction_v12::canonical)
                    .collect();
                a.sort();
                b.sort();
                a == b
            }
            _ => a == b,
        }
    } else {
        a == b
    }
}
/// Inverse destination verification. Does not call execute/project_native_fields.
/// The original source enumerates required evidence; the receipt cannot choose
/// the fields, owner, disposition, output cardinality or representation rules.
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
    let mut findings = vec![];
    if supplied.status != Status::Executed
        || !supplied.findings.is_empty()
        || supplied.authorities != p.q.authorities()
        || supplied.basis_digest != p.basis
        || supplied.units.len() != p.selected.len()
    {
        findings.extend(rejected(
            "projection",
            "Forged or incomplete field envelope",
        ));
    }
    match &supplied.representations {
        Some(r) => {
            let checked = identity::verify(i, s, selected, r);
            if checked.status() != Status::Verified {
                findings.extend(checked.findings().to_vec());
            }
        }
        None => findings.extend(rejected(
            "representations",
            "Missing independently verifiable representation evidence",
        )),
    }
    let catalog = &p.q.resources()[FD];
    let map = match fields::qualified_schema_map(p.q.resources()) {
        Ok(m) => m,
        Err(e) => return Projection::failure(unavailable("schema", e)),
    };
    for original in &p.selected {
        let id = text(&original.value, "id");
        let ty = &original.selection.semantic_type;
        let matches: Vec<_> = supplied.units.iter().filter(|u| u.id == id).collect();
        let [out] = matches.as_slice() else {
            findings.extend(rejected(id, "Missing or duplicated unit"));
            continue;
        };
        let mut paths = BTreeSet::from(["/entity_type".to_owned()]);
        let mut extensions = BTreeSet::new();
        let expected_type = get(
            get(
                get(
                    &p.q.resources()["architecture-interpretation/1.3/source-mapping-1.7-to-2.5"],
                    "mappings",
                ),
                ty,
            ),
            "output",
        );
        if out.semantic_type != *ty
            || out.source_qualification
                != object([
                    ("family".into(), string("authoring")),
                    ("version".into(), string("1.7")),
                    (
                        "canonical_resource_key".into(),
                        get(
                            get(&original.row, "source_schema"),
                            "canonical_resource_key",
                        )
                        .clone(),
                    ),
                    (
                        "content_digest".into(),
                        get(get(&original.row, "source_schema"), "content_digest").clone(),
                    ),
                    (
                        "schema_pointer".into(),
                        get(get(&original.row, "source_schema"), "schema_pointer").clone(),
                    ),
                ])
            || out.placements.get("/entity_type") != Some(expected_type)
        {
            findings.extend(rejected(id, "Changed type/source/identity qualification"));
        }
        let mut count = 0;
        for (name, value) in original.value.as_object().into_iter().flatten() {
            count += 1;
            let path = format!("/{}", name.replace('~', "~0").replace('/', "~1"));
            let f = match p.engine.field(ty, &path) {
                Ok(f) => f,
                Err(e) => {
                    findings.extend(unavailable(&format!("{ty}#{path}"), e));
                    continue;
                }
            };
            let key = text(f, "semantic_field_key");
            let dest = get(
                get(catalog, "destination_catalog"),
                text(f, "destination_ref"),
            );
            let coverage: Vec<_> = out
                .coverage
                .iter()
                .filter(|c| c.semantic_field_key == key)
                .collect();
            if coverage.len() != 1
                || coverage[0].source_value != *value
                || coverage[0].disposition != *f
                || coverage[0].destination != *dest
            {
                findings.extend(rejected(key, "Missing, changed or duplicated field proof"));
            }
            match (text(f, "disposition"), text(dest, "kind")) {
                ("canonical_field_placement", "normalized_entity")
                | ("direct_semantic_value", "normalized_normative_proposition") => {
                    let path = text(dest, "path");
                    paths.insert(path.into());
                    if out.placements.get(path) != Some(value) {
                        findings.extend(rejected(
                            key,
                            "Original authored value differs at governed placement",
                        ));
                    }
                    let branch = if text(&original.row, "output_branch") == "normative-proposition"
                    {
                        1
                    } else {
                        0
                    };
                    if let Err(e) = crate::schema_validation::validate_fragment(
                        &map,
                        NM,
                        &format!("/oneOf/{branch}/properties{path}"),
                        value,
                    ) {
                        findings.extend(schema_error(e));
                    }
                }
                ("direct_semantic_value", "semantic_extension") => {
                    extensions.insert(key.into());
                    if !out
                        .semantic_extensions
                        .get(key)
                        .map(|v| equal_value(v, value, text(f, "ordering")))
                        .unwrap_or(false)
                    {
                        findings.extend(rejected(
                            key,
                            "Missing/changed complete typed semantic extension",
                        ));
                    }
                }
                ("direct_semantic_value", "child_membership") => {
                    extensions.insert(key.into());
                    let ids = Json::Array(
                        value
                            .as_array()
                            .into_iter()
                            .flatten()
                            .map(|c| get(c, "id").clone())
                            .collect(),
                    );
                    if !out
                        .semantic_extensions
                        .get(key)
                        .map(|v| equal_value(v, &ids, text(f, "ordering")))
                        .unwrap_or(false)
                    {
                        findings.extend(rejected(key, "Child identity/order/multiplicity differs"));
                    }
                }
                ("deterministic_ceremony", "no_normalized_value") => {}
                // No selected source in this slice can authorize compatibility
                // endpoint resolution or an invented declared-absence rule.
                _ => findings.extend(unavailable(
                    key,
                    "Disposition prerequisites are not executable for this source branch",
                )),
            }
        }
        if out.coverage.len() != count {
            findings.extend(rejected(id, "Additional or missing source field evidence"));
        }
        match context(&p, original) {
            Ok(Some((carrier, fact, value))) => {
                paths.insert("/lifecycle_stage".into());
                if out.lifecycle_provenance.as_ref() != Some(&carrier)
                    || out.contextual_fact.as_ref() != Some(&fact)
                    || out.placements.get("/lifecycle_stage") != Some(&value)
                {
                    findings.extend(rejected(
                        id,
                        "Forged owner, lifecycle or contextual provenance",
                    ));
                }
            }
            Ok(None) => {
                if out.lifecycle_provenance.is_some() || out.contextual_fact.is_some() {
                    findings.extend(rejected(
                        id,
                        "Unexpected contextual fact or inherited lifecycle",
                    ));
                }
            }
            Err(mut e) => findings.append(&mut e),
        }
        if out.placements.keys().cloned().collect::<BTreeSet<_>>() != paths
            || out
                .semantic_extensions
                .keys()
                .cloned()
                .collect::<BTreeSet<_>>()
                != extensions
        {
            findings.extend(rejected(
                id,
                "Missing/additional semantic destinations or fallback output",
            ));
        }
    }
    if !findings.is_empty() {
        return Projection::failure(findings);
    }
    let mut verified = supplied.clone();
    verified.status = Status::Verified;
    verified
}

#[cfg(test)]
#[path = "semantic_fields_tests.rs"]
mod tests;
