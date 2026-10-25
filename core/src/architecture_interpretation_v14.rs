//! Private static AI 1.4 output authority qualification, never instance materialization.
//! A definition selects rules; neither that selection nor a catalog count proves output.
use crate::authoring_construction_v12::{array, canonical, digest, manifest_resources, text};
use crate::{object, schema_validation as schema, semantic_contract, string, Json};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

const AI: &str = "architecture-interpretation/1.4/";
const BASE: &str = "architecture-interpretation/1.3/";
const CATALOG: &str = "architecture-interpretation/1.4/required-output-derivations";
const FIELDS: &str = "architecture-interpretation/1.3/field-dispositions-1.7-to-2.5";
const AI_SCF: &str =
    "scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7";
const ACC_SCF: &str =
    "scf:v1:sha256:19e267c5c77477a594414168bde9f733b1b9e547c06fc6836ad09392a248ea6d";
const NM_SCF: &str =
    "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7";
const INHERITED_SCF: &str =
    "scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167";

#[derive(Clone, Copy)]
pub(crate) struct Bundle<'a> {
    pub definition: &'a Json,
    pub resources: &'a [Json],
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum Status {
    Rejected,
    Unavailable,
    Unresolved,
    CatalogQualified,
}
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) struct Finding {
    status: Status,
    key: String,
    code: String,
    detail: String,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum Definition {
    Qualified { rule: Json },
    Blocked { code: String, reason: String },
}
/// There are deliberately no caller-supplied facts or inapplicability assertions.
/// A later independently qualified instance seam must prove applicability.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Applicability {
    Unknown,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Destination {
    path: String,
    definition: Definition,
    applicability: Applicability,
    declaration: Json,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct TypeCoverage {
    semantic_type: String,
    branch: String,
    source_schema: Json,
    requirements: Vec<Json>,
    destinations: Vec<Destination>,
    context_dependencies: Json,
}
/// Fields are private: consumers cannot promote a catalog declaration to instance proof.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Qualification {
    status: Status,
    authority_qualified: bool,
    selected_authorities: Vec<Json>,
    types: Vec<TypeCoverage>,
    blocker_register: BTreeMap<String, Json>,
    findings: Vec<Finding>,
    complete_interpretation: Status,
}
impl Qualification {
    fn new() -> Self {
        Self {
            status: Status::CatalogQualified,
            authority_qualified: false,
            selected_authorities: vec![],
            types: vec![],
            blocker_register: BTreeMap::new(),
            findings: vec![],
            complete_interpretation: Status::Unavailable,
        }
    }
    fn issue(&mut self, status: Status, key: &str, code: &str, detail: impl Into<String>) {
        self.findings.push(Finding {
            status,
            key: key.into(),
            code: code.into(),
            detail: detail.into(),
        });
    }
    fn finish(mut self) -> Self {
        self.findings.sort();
        self.findings.dedup();
        if let Some(f) = self.findings.first() {
            self.status = f.status;
            self.types.clear();
            self.blocker_register.clear();
        }
        self
    }
    pub(crate) fn status(&self) -> Status {
        self.status
    }
    pub(crate) fn types(&self) -> &[TypeCoverage] {
        &self.types
    }
    pub(crate) fn complete_interpretation(&self) -> Status {
        self.complete_interpretation
    }
    pub(crate) fn authority_qualified(&self) -> bool {
        self.authority_qualified
    }
    pub(crate) fn findings(&self) -> &[Finding] {
        &self.findings
    }
    pub(crate) fn selected_authorities(&self) -> &[Json] {
        &self.selected_authorities
    }
    pub(crate) fn blockers(&self) -> &BTreeMap<String, Json> {
        &self.blocker_register
    }
}
impl Finding {
    pub(crate) fn status(&self) -> Status {
        self.status
    }
    pub(crate) fn key(&self) -> &str {
        &self.key
    }
    pub(crate) fn code(&self) -> &str {
        &self.code
    }
    pub(crate) fn detail(&self) -> &str {
        &self.detail
    }
}
impl TypeCoverage {
    pub(crate) fn semantic_type(&self) -> &str {
        &self.semantic_type
    }
    pub(crate) fn branch(&self) -> &str {
        &self.branch
    }
    pub(crate) fn destinations(&self) -> &[Destination] {
        &self.destinations
    }
    pub(crate) fn requirements(&self) -> &[Json] {
        &self.requirements
    }
}
impl Destination {
    pub(crate) fn path(&self) -> &str {
        &self.path
    }
    pub(crate) fn definition(&self) -> &Definition {
        &self.definition
    }
    pub(crate) fn applicability(&self) -> Applicability {
        self.applicability
    }
    pub(crate) fn declaration(&self) -> &Json {
        &self.declaration
    }
}
fn j(v: Value) -> Json {
    serde_json::from_value(v).expect("JSON value")
}
fn v(j: &Json) -> Value {
    serde_json::to_value(j).expect("JSON value")
}
fn esc(s: &str) -> String {
    s.replace('~', "~0").replace('/', "~1")
}
fn err(e: schema::SchemaError) -> String {
    format!("{}: {}", e.path, e.message)
}
fn check(condition: bool, code: &str) -> Result<(), String> {
    if condition {
        Ok(())
    } else {
        Err(code.into())
    }
}
fn list<'a>(v: &'a Value, key: &str) -> &'a [Value] {
    v[key].as_array().map(Vec::as_slice).unwrap_or(&[])
}
fn st<'a>(v: &'a Value, key: &str) -> &'a str {
    v[key].as_str().unwrap_or("")
}

fn verify_bundle(
    b: Bundle<'_>,
    family: &str,
    version: &str,
    scf: &str,
) -> Result<BTreeMap<String, Json>, String> {
    check(
        text(b.definition, "semanticContractFamily") == family
            && text(b.definition, "semanticContractVersion") == version
            && text(b.definition, "semanticContractFingerprint") == scf,
        "exact_authority_identity",
    )?;
    let members = manifest_resources(b.definition, b.resources);
    let resources = array(b.definition, "resourceManifest")
        .iter()
        .map(|m| {
            let key = text(m, "canonicalResourceKey");
            object([
                ("canonicalResourceKey".into(), string(key)),
                (
                    "content".into(),
                    members.get(key).cloned().unwrap_or(Json::Null),
                ),
            ])
        })
        .collect();
    // Keep supplied duplicates visible to the shared verifier; extra unselected
    // resources are never put in the qualified map.
    let supplied: Vec<_> = b
        .resources
        .iter()
        .filter(|r| members.contains_key(text(r, "canonicalResourceKey")))
        .cloned()
        .collect();
    check(
        supplied.len() == members.len(),
        "duplicate_or_missing_resource",
    )?;
    let result = semantic_contract::validate_closure(&object([
        ("definition".into(), b.definition.clone()),
        ("resources".into(), Json::Array(resources)),
    ]));
    check(
        result.get("closure_valid").and_then(Json::as_bool) == Some(true),
        "exact_resource_closure",
    )?;
    check(
        v(b.definition)["frozenNormativeConformanceResources"]
            == json!([format!("{family}/{version}/conformance")]),
        "frozen_conformance_identity",
    )?;
    Ok(members)
}

struct Catalog<'a> {
    sealed: &'a BTreeMap<String, Json>,
    evaluation: BTreeMap<String, Json>,
    digests: BTreeMap<String, String>,
}
impl<'a> Catalog<'a> {
    fn new(sealed: &'a BTreeMap<String, Json>) -> Result<Self, String> {
        let mut evaluation = sealed.clone();
        for (key, value) in &mut evaluation {
            if !(key.contains("/schema/") || key.ends_with("schema")) {
                continue;
            }
            check(
                matches!(
                    text(value, "$schema"),
                    "http://json-schema.org/draft-07/schema#"
                        | "https://json-schema.org/draft-07/schema#"
                        | "https://json-schema.org/draft/2020-12/schema"
                ),
                "invalid_schema_dialect",
            )?;
            if let Some(edges) = value.get("semanticDependencies") {
                check(edges.as_array().is_some(), "invalid_dependency_annotation")?;
                for edge in edges.as_array().unwrap() {
                    check(
                        edge.as_str().is_some_and(|k| sealed.contains_key(k)),
                        "unqualified_schema_dependency",
                    )?;
                }
                value
                    .as_object_mut()
                    .unwrap()
                    .remove("semanticDependencies");
            }
        }
        let digests = sealed
            .iter()
            .map(|(k, v)| (k.clone(), format!("sha256:{}", digest(v))))
            .collect();
        Ok(Self {
            sealed,
            evaluation,
            digests,
        })
    }
    fn read(&self, key: &str) -> Result<Value, String> {
        self.sealed
            .get(key)
            .map(v)
            .ok_or_else(|| format!("missing_resource:{key}"))
    }
    fn select(&self, key: &str, pointer: &str) -> Result<Value, String> {
        schema::resolve_reference(self.sealed, key, &format!("#{pointer}"))
            .map(|(_, x)| v(&x))
            .map_err(err)
    }
    fn reference(&self, key: &str, pointer: &str) -> Result<Value, String> {
        self.select(key, pointer)?;
        Ok(
            json!({"canonical_resource_key":key,"content_digest":self.digests.get(key).ok_or("missing_resource")?,"schema_pointer":pointer}),
        )
    }
    fn selected(&self, q: &Value) -> Result<Value, String> {
        let key = st(q, "canonical_resource_key");
        let pointer = st(q, "schema_pointer");
        if q != &self.reference(key, pointer)? {
            return Err(format!(
                "resource_selector_digest_mismatch:{key}#{pointer}: {} != {}",
                q,
                self.reference(key, pointer)?
            ));
        }
        self.select(key, pointer)
    }
    fn qualified_refs(&self, node: &Value) -> Result<(), String> {
        match node {
            Value::Object(m) => {
                if m.contains_key("canonical_resource_key")
                    && m.contains_key("content_digest")
                    && m.contains_key("schema_pointer")
                {
                    self.selected(node)?;
                }
                for child in m.values() {
                    self.qualified_refs(child)?;
                }
            }
            Value::Array(a) => {
                for x in a {
                    self.qualified_refs(x)?;
                }
            }
            _ => {}
        }
        Ok(())
    }
    fn deref(
        &self,
        mut key: String,
        mut pointer: String,
    ) -> Result<(String, String, Value), String> {
        let mut seen = BTreeSet::new();
        loop {
            check(
                seen.insert((key.clone(), pointer.clone())),
                "recursive_schema",
            )?;
            let node = self.select(&key, &pointer)?;
            let Some(reference) = node["$ref"].as_str() else {
                return Ok((key, pointer, node));
            };
            let (target, _) =
                schema::resolve_reference(self.sealed, &key, reference).map_err(err)?;
            key = target;
            pointer = reference
                .split_once('#')
                .map(|(_, p)| p)
                .unwrap_or("")
                .into();
        }
    }
    fn source_ref(&self, selector: &str) -> Result<Value, String> {
        let (file, pointer) = selector.split_once('#').unwrap_or((selector, ""));
        self.reference(
            &format!("authoring/1.7/schema/{}", file.trim_end_matches(".json")),
            pointer,
        )
    }
    fn destination(&self, branch: &Value, path: &str) -> Result<Value, String> {
        let selected = &branch["schema"];
        self.selected(selected)?;
        if st(branch, "branch_id") == "proposition-owned-value" {
            return Ok(selected.clone());
        }
        let mut key = st(selected, "canonical_resource_key").to_owned();
        let mut pointer = st(selected, "schema_pointer").to_owned();
        let path = if path.starts_with("/metadata/") {
            if st(branch, "branch_id") == "owner-local-value" {
                ""
            } else {
                "/metadata"
            }
        } else {
            path
        };
        for token in path.split('/').skip(1) {
            let (k, p, node) = self.deref(key, pointer)?;
            key = k;
            pointer = p;
            check(
                node["properties"].get(token).is_some(),
                "unknown_destination",
            )?;
            pointer += &format!("/properties/{}", esc(token));
        }
        self.reference(&key, &pointer)
    }
    fn nested(&self, selected: &Value, path: &str) -> Result<Vec<Value>, String> {
        fn walk(
            c: &Catalog<'_>,
            key: &str,
            p: &str,
            path: &str,
            seen: &mut BTreeSet<(String, String)>,
            out: &mut Vec<Value>,
        ) -> Result<(), String> {
            check(
                seen.insert((key.into(), p.into())),
                "recursive_nested_requirement",
            )?;
            let n = c.select(key, p)?;
            if let Some(r) = n["$ref"].as_str() {
                let (k, _) = schema::resolve_reference(c.sealed, key, r).map_err(err)?;
                walk(
                    c,
                    &k,
                    r.split_once('#').map(|(_, p)| p).unwrap_or(""),
                    path,
                    seen,
                    out,
                )?;
            }
            for name in list(&n, "required") {
                let name = name.as_str().ok_or("invalid_required_property")?;
                let child = format!("{p}/properties/{}", esc(name));
                let dest = format!("{path}/{name}");
                out.push(json!({"destination":dest,"schema":c.reference(key,&child)?,"coverage":"same_complete_parent_value_no_second_producer"}));
                walk(c, key, &child, &dest, seen, out)?;
            }
            seen.remove(&(key.into(), p.into()));
            Ok(())
        }
        let mut out = vec![];
        walk(
            self,
            st(selected, "canonical_resource_key"),
            st(selected, "schema_pointer"),
            path,
            &mut BTreeSet::new(),
            &mut out,
        )?;
        Ok(out)
    }
    fn audit(&self, key: &str, pointer: &str) -> Result<Vec<Value>, String> {
        fn walk(
            c: &Catalog<'_>,
            node: &Value,
            key: &str,
            p: &str,
            seen: &mut BTreeSet<(String, String)>,
            out: &mut BTreeMap<String, Value>,
        ) -> Result<(), String> {
            match node {
                Value::Object(m) => {
                    if let Some(r) = node["$ref"].as_str() {
                        let (k, n) = schema::resolve_reference(c.sealed, key, r).map_err(err)?;
                        let f = r.split_once('#').map(|(_, p)| p).unwrap_or("");
                        check(seen.insert((k.clone(), f.into())), "recursive_requirement")?;
                        walk(c, &v(&n), &k, f, seen, out)?;
                        seen.remove(&(k, f.into()));
                    }
                    for keyword in [
                        "required",
                        "if",
                        "then",
                        "else",
                        "not",
                        "oneOf",
                        "anyOf",
                        "allOf",
                        "dependencies",
                        "dependentRequired",
                    ] {
                        if let Some(value) = m.get(keyword) {
                            let row = json!({"schema":c.reference(key,&format!("{p}/{keyword}"))?,"keyword":keyword,"constraint":value});
                            out.insert(canonical(&j(row.clone())), row);
                        }
                    }
                    for (name, n) in m {
                        if name != "$ref" {
                            walk(c, n, key, &format!("{p}/{}", esc(name)), seen, out)?;
                        }
                    }
                }
                Value::Array(a) => {
                    for (i, n) in a.iter().enumerate() {
                        walk(c, n, key, &format!("{p}/{i}"), seen, out)?;
                    }
                }
                _ => {}
            }
            Ok(())
        }
        let mut out = BTreeMap::new();
        walk(
            self,
            &self.select(key, pointer)?,
            key,
            pointer,
            &mut BTreeSet::from([(key.into(), pointer.into())]),
            &mut out,
        )?;
        Ok(out.into_values().collect())
    }
    fn preflight(&self, key: &str, pointer: &str) -> Result<(), String> {
        schema::preflight_fragment(&self.evaluation, key, pointer).map_err(err)
    }
    fn validate_companion(&self, key: &str, value: &Value) -> Result<(), String> {
        self.preflight(key, "")?;
        schema::validate(&self.evaluation, key, &j(value.clone())).map_err(err)
    }
}

/// Resolve named output branches by their actual NM discriminator/requirements,
/// not by trusting an arbitrary catalog selector or fixed array position.
fn qualify_branch_selectors(c: &Catalog<'_>, catalog: &Value) -> Result<(), String> {
    let entity = "normalized-model/2.5/schema/normalized-entity.schema";
    let relationship = "normalized-model/2.5/schema/relationship-record.schema";
    let mut expected = BTreeMap::new();
    for (key, kind) in [(entity, "entity"), (relationship, "relationship")] {
        let schema = c.read(key)?;
        for (i, node) in list(&schema, "oneOf").iter().enumerate() {
            let name = if kind == "entity" {
                if node["properties"]["entity_type"]["const"] == "normative_proposition" {
                    "normative-proposition"
                } else if list(node, "required").contains(&json!("lifecycle_stage")) {
                    "regular"
                } else {
                    return Err("unknown_NM_entity_branch".into());
                }
            } else {
                match node["properties"]["record_kind"]["const"].as_str() {
                    Some("canonical") => "canonical-relationship",
                    Some("compatibility") => "compatibility-relationship",
                    _ => return Err("unknown_NM_relationship_branch".into()),
                }
            };
            check(
                expected
                    .insert(name.to_owned(), c.reference(key, &format!("/oneOf/{i}"))?)
                    .is_none(),
                "ambiguous_NM_output_branch",
            )?;
        }
    }
    let normative =
        json!({"branch_id":"normative-proposition","schema":expected["normative-proposition"]});
    let regular = json!({"branch_id":"regular","schema":expected["regular"]});
    let fields = c.read(FIELDS)?;
    let force = st(&fields["destination_catalog"]["normative_force"], "path");
    expected.insert(
        "proposition-owned-value".into(),
        c.destination(&normative, force)?,
    );
    let topology = st(
        &fields["destination_catalog"]["topology_value"],
        "path_template",
    );
    let top = topology
        .split('/')
        .nth(1)
        .ok_or("missing_owner_value_destination")?;
    expected.insert(
        "owner-local-value".into(),
        c.destination(&regular, &format!("/{top}"))?,
    );
    let declared: BTreeMap<_, _> = list(catalog, "branches")
        .iter()
        .map(|b| (st(b, "branch_id").to_owned(), b["schema"].clone()))
        .collect();
    check(declared == expected, "wrong_NM_output_branch_selector")
}

fn expected_branch(mapping: &Value) -> &str {
    match st(mapping, "output") {
        "normative_proposition" => "normative-proposition",
        "canonical" => "canonical-relationship",
        "compatibility" => "compatibility-relationship",
        "component-reference" => "owner-local-value",
        "normative_force" => "proposition-owned-value",
        _ => "regular",
    }
}
fn sorted(mut a: Vec<Value>) -> Vec<Value> {
    a.sort_by_key(|x| canonical(&j(x.clone())));
    a
}

/// No source instance is accepted here: every applicability remains Unknown.
pub(crate) fn qualify(ai: Bundle<'_>, acc: Bundle<'_>, nm: Bundle<'_>) -> Qualification {
    let mut out = Qualification::new();
    let mut maps = vec![];
    for (b, family, version, scf) in [
        (ai, "architecture-interpretation", "1.4", AI_SCF),
        (acc, "authoring-construction", "1.4", ACC_SCF),
        (nm, "normalized-model", "2.5", NM_SCF),
    ] {
        match verify_bundle(b, family, version, scf) {
            Ok(map) => maps.push(map),
            Err(e) => out.issue(Status::Unavailable, family, "authority_unavailable", e),
        }
    }
    if !out.findings.is_empty() {
        return out.finish();
    }
    let ai_map = &maps[0];
    let acc_map = &maps[1];
    let linked = (|| -> Result<(), String> {
        check(
            acc_map.get("architecture-interpretation/1.4/contract") == Some(ai.definition),
            "ACC_selected_AI_definition",
        )?;
        for m in &maps {
            for (key, value) in m {
                check(
                    acc_map.get(key) == Some(value),
                    "cross_closure_substitution",
                )?;
            }
        }
        let inherited = ai_map
            .get("architecture-interpretation/1.3/contract")
            .ok_or("missing_inherited_definition")?;
        let resources: Vec<_> = array(inherited, "resourceManifest")
            .iter()
            .map(|m| {
                object([
                    (
                        "canonicalResourceKey".into(),
                        string(text(m, "canonicalResourceKey")),
                    ),
                    (
                        "content".into(),
                        ai_map
                            .get(text(m, "canonicalResourceKey"))
                            .cloned()
                            .unwrap_or(Json::Null),
                    ),
                ])
            })
            .collect();
        verify_bundle(
            Bundle {
                definition: inherited,
                resources: &resources,
            },
            "architecture-interpretation",
            "1.3",
            INHERITED_SCF,
        )?;
        Ok(())
    })();
    if let Err(e) = linked {
        out.issue(
            Status::Unavailable,
            "authority",
            "cross_authority_unavailable",
            e,
        );
        return out.finish();
    }
    out.authority_qualified = true;
    out.selected_authorities = vec![
        ai.definition.clone(),
        acc.definition.clone(),
        nm.definition.clone(),
    ];
    match Catalog::new(ai_map) {
        Ok(c) => qualify_catalog(&c, &mut out),
        Err(e) => out.issue(Status::Unavailable, "schema", "schema_unavailable", e),
    }
    out.finish()
}

pub(crate) fn verify(
    ai: Bundle<'_>,
    acc: Bundle<'_>,
    nm: Bundle<'_>,
    evidence: &Qualification,
) -> bool {
    let actual = qualify(ai, acc, nm);
    actual.status == Status::CatalogQualified && &actual == evidence
}

fn failure_status(e: &str) -> Status {
    if [
        "unsupported schema keyword",
        "invalid_schema_dialect",
        "missing_resource",
        "unresolved",
        "resource_selector_digest_mismatch",
        "unavailable",
    ]
    .iter()
    .any(|s| e.contains(s))
    {
        Status::Unavailable
    } else {
        Status::Rejected
    }
}
fn closed_companion(node: &Value) -> Result<(), String> {
    match node {
        Value::Object(m) => {
            if node["type"] == "object" {
                check(
                    node["additionalProperties"] == false,
                    "open_companion_schema",
                )?;
            }
            for n in m.values() {
                closed_companion(n)?;
            }
        }
        Value::Array(a) => {
            for n in a {
                closed_companion(n)?;
            }
        }
        _ => {}
    }
    Ok(())
}
fn qualify_catalog(c: &Catalog<'_>, out: &mut Qualification) {
    let result = (|| -> Result<(), String> {
        let catalog = c.read(CATALOG)?;
        c.qualified_refs(&catalog)?;
        let companion = c.read(&format!("{CATALOG}.schema"))?;
        closed_companion(&companion)?;
        check(companion["$id"]=="https://adr-kit.ste.systems/contracts/architecture-interpretation/v1.4/resources/required-output-derivations.schema.json","wrong_companion_schema_identity")?;
        c.validate_companion(&format!("{CATALOG}.schema"), &catalog)?;
        let fields = c.read(FIELDS)?;
        let mapping = c.read(&format!("{BASE}source-mapping-1.7-to-2.5"))?;
        c.validate_companion(&format!("{BASE}field-dispositions.schema"), &fields)?;
        let ownership = c.read(&format!("{BASE}lifecycle-ownership"))?;
        c.validate_companion(&format!("{BASE}lifecycle-ownership.schema"), &ownership)?;
        check(
            catalog["field_dispositions"] == c.reference(FIELDS, "")?,
            "wrong_inherited_field_qualification",
        )?;
        qualify_branch_selectors(c, &catalog)?;
        let mut branches = BTreeMap::new();
        for branch in list(&catalog, "branches") {
            let id = st(branch, "branch_id");
            check(branches.insert(id, branch).is_none(), "duplicate_branch")?;
            let sel = &branch["schema"];
            c.selected(sel)?;
            c.preflight(st(sel, "canonical_resource_key"), st(sel, "schema_pointer"))?;
            check(
                sorted(list(branch, "requirements").to_vec())
                    == sorted(
                        c.audit(st(sel, "canonical_resource_key"), st(sel, "schema_pointer"))?,
                    ),
                "incomplete_branch_requirements",
            )?;
        }
        let mut types = BTreeMap::new();
        for row in list(&fields, "semantic_types") {
            check(
                types.insert(st(row, "semantic_type"), row).is_none(),
                "duplicate_inherited_type",
            )?;
        }
        let rows = list(&catalog, "types");
        let found: BTreeSet<_> = rows.iter().map(|t| st(t, "semantic_type")).collect();
        check(
            found.len() == rows.len() && found == types.keys().copied().collect(),
            "missing_duplicate_or_unknown_type",
        )?;
        let expected_branches: BTreeSet<_> = types
            .keys()
            .map(|ty| expected_branch(&mapping["mappings"][*ty]))
            .collect();
        check(
            branches.keys().copied().collect::<BTreeSet<_>>() == expected_branches,
            "missing_or_unknown_output_branch",
        )?;
        let rules = c.read(&format!("{AI}rules"))?;
        check(
            rules["inherits"]["semantic_contract_fingerprint"] == INHERITED_SCF
                && rules["inherits"]["definition"]
                    == c.reference(&format!("{BASE}contract"), "")?,
            "wrong_inherited_definition_qualification",
        )?;
        let conformance = c.read(&format!("{AI}conformance"))?;
        let oracles: BTreeMap<_, _> = list(&conformance, "cases")
            .iter()
            .filter(|x| st(x, "category") == "label_policy")
            .map(|x| (st(x, "semantic_type"), &x["fixture"]))
            .collect();
        out.blocker_register = catalog["blockers"]
            .as_object()
            .ok_or("invalid_blocker_register")?
            .iter()
            .map(|(k, v)| (k.clone(), j(v.clone())))
            .collect();
        for row in rows {
            let ty = st(row, "semantic_type");
            let inherited = types[ty];
            let one = (|| -> Result<TypeCoverage, String> {
                let src = c.source_ref(st(inherited, "source_schema"))?;
                check(
                    row["source_schema"] == src
                        && row["identity_policy"] == inherited["identity_policy"],
                    "source_or_identity_policy",
                )?;
                c.preflight(
                    st(&src, "canonical_resource_key"),
                    st(&src, "schema_pointer"),
                )?;
                let branch_id = st(row, "output_branch");
                check(
                    branch_id == expected_branch(&mapping["mappings"][ty]),
                    "wrong_output_branch",
                )?;
                let branch = *branches.get(branch_id).ok_or("missing_branch")?;
                let shape = c.selected(&branch["schema"])?;
                let entries = list(row, "outputs");
                let paths: BTreeSet<_> = entries.iter().map(|e| st(e, "destination")).collect();
                check(
                    paths.len() == entries.len(),
                    "competing_destination_producers",
                )?;
                for name in list(&shape, "required") {
                    check(
                        paths.contains(
                            format!("/{}", name.as_str().ok_or("invalid_requirement")?).as_str(),
                        ),
                        "missing_required_destination",
                    )?;
                }
                for req in list(branch, "requirements") {
                    if st(req, "keyword") == "required"
                        && st(&req["schema"], "schema_pointer").contains("/then/required")
                    {
                        for name in req["constraint"].as_array().ok_or("invalid_requirement")? {
                            check(
                                paths.contains(
                                    format!("/{}", name.as_str().ok_or("invalid_requirement")?)
                                        .as_str(),
                                ),
                                "missing_conditional_destination",
                            )?;
                        }
                    }
                }
                for field in list(inherited, "field_dispositions") {
                    if !["canonical_field_placement", "direct_semantic_value"]
                        .contains(&st(field, "disposition"))
                    {
                        continue;
                    }
                    let dest = &fields["destination_catalog"][st(field, "destination_ref")];
                    let path = dest["path"]
                        .as_str()
                        .or(dest["path_template"].as_str())
                        .ok_or("unknown_semantic_destination")?;
                    let e = entries
                        .iter()
                        .find(|e| st(e, "destination") == path)
                        .ok_or("lost_original_semantic_destination")?;
                    if branch_id == "canonical-relationship"
                        && st(dest, "record") == "normalized_entity"
                    {
                        check(
                            st(e, "status") == "BLOCKED"
                                && st(&e["blocked"], "code") == "relationship_branch",
                            "unqualified_relationship_branch",
                        )?;
                    } else {
                        check(
                            st(e, "status") == "QUALIFIED",
                            "semantic_producer_replaced_by_blocker",
                        )?;
                    }
                }
                let mut destinations = vec![];
                for entry in entries {
                    qualify_entry(
                        c,
                        &catalog,
                        &fields,
                        &mapping,
                        &ownership,
                        oracles.get(ty).copied(),
                        row,
                        inherited,
                        branch,
                        entry,
                    )
                    .map_err(|e| format!("{ty}#{}: {e}", st(entry, "destination")))?;
                    if st(entry, "status") == "QUALIFIED" {
                        for child in list(entry, "required_subdestinations") {
                            check(
                                !entries.iter().any(|e| {
                                    st(e, "status") == "QUALIFIED"
                                        && e["destination"] == child["destination"]
                                }),
                                "nested_value_has_second_producer",
                            )?;
                        }
                    }
                    destinations.push(Destination {
                        path: st(entry, "destination").into(),
                        definition: if st(entry, "status") == "BLOCKED" {
                            Definition::Blocked {
                                code: st(&entry["blocked"], "code").into(),
                                reason: st(&entry["blocked"], "missing_authority").into(),
                            }
                        } else {
                            Definition::Qualified {
                                rule: j(entry["producer"].clone()),
                            }
                        },
                        applicability: Applicability::Unknown,
                        declaration: j(entry.clone()),
                    });
                }
                destinations.sort_by(|a, b| a.path.cmp(&b.path));
                Ok(TypeCoverage {
                    semantic_type: ty.into(),
                    branch: branch_id.into(),
                    source_schema: j(src),
                    requirements: list(branch, "requirements")
                        .iter()
                        .cloned()
                        .map(j)
                        .collect(),
                    destinations,
                    context_dependencies: j(row["context_dependencies"].clone()),
                })
            })();
            match one {
                Ok(t) => out.types.push(t),
                Err(e) => {
                    let key = e
                        .split_once(": ")
                        .map(|(key, _)| key)
                        .filter(|key| key.starts_with(&format!("{ty}#")))
                        .unwrap_or(ty)
                        .to_owned();
                    out.issue(failure_status(&e), &key, "output_catalog_invalid", e);
                }
            }
        }
        out.types
            .sort_by(|a, b| a.semantic_type.cmp(&b.semantic_type));
        Ok(())
    })();
    if let Err(e) = result {
        out.issue(
            failure_status(&e),
            CATALOG,
            "catalog_qualification_failed",
            e,
        );
    }
}

/// Closed execution vocabulary for interpreting the published obligations, not
/// a second type/field policy. No output value is created by recognizing it.
fn producer_obligations(e: &Value) -> Result<(), String> {
    let common = [
        "reconstruct_from_independently_verified_source_identity_and_exact_rule",
        "compare_complete_typed_output",
        "validate_complete_selected_NM_branch",
        "retain_original_authored_semantics_once",
    ];
    let labels = [
        "literal_string_equality_no_transformation_or_fallback",
        "source_presence_and_string_type",
        "original_field_disposition_retained",
    ];
    let declared: BTreeSet<_> = list(e, "verification")
        .iter()
        .filter_map(Value::as_str)
        .collect();
    check(
        common.iter().all(|o| declared.contains(o)),
        "missing_independent_verification_obligation",
    )?;
    check(
        declared.iter().all(|o| {
            common.contains(o)
                || labels.contains(o)
                || *o == "label_duplication_only_no_substantive_system_description"
        }),
        "unknown_verification_obligation",
    )?;
    if st(e, "status") == "BLOCKED" {
        return check(
            st(e, "classification") == "qualification_pending"
                && st(e, "semantic_equality") == "independent_semantic_ledger_required",
            "blocked_semantic_claim",
        );
    }
    let p = &e["producer"];
    let kind = st(p, "kind");
    let (equality,source)=match kind {
        "field_placement"=>("governed_field_identity_and_complete_typed_value",None),
        "literal_string_copy"=>("original_authored_input_once_not_generated_label",None),
        "field_inventory"=>("semantic_unit_identity_stable_field_key_complete_typed_value_and_declared_order_multiplicity",Some("semantic_field_key")),
        "type_mapping"=>("exact_selected_type_and_custom_qualification",Some("selected_semantic_type")),
        "schema_constant"=>("schema_envelope_not_independent_meaning",Some("exact_selected_authority_constant")),
        "mapping_constant"=>("governed_owner_local_ordered_topology_path",Some("exact_selected_authority_constant")),
        "contextual_rule"=>("literal_lifecycle_and_independently_qualified_contextual_fact",Some("unique_declaring_ADR_literal_status")),
        _=>return Err("unknown_output_operation".into())
    };
    check(
        st(e, "semantic_equality") == equality,
        "wrong_semantic_equality_obligation",
    )?;
    check(
        st(e, "classification")
            == if ["literal_string_copy", "schema_constant"].contains(&kind) {
                "representation_only"
            } else {
                "semantic"
            },
        "wrong_producer_classification",
    )?;
    if let Some(source) = source {
        check(
            st(p, "source_field") == source,
            "wrong_producer_input_meaning",
        )?;
    }
    if kind == "literal_string_copy" {
        check(
            labels.iter().all(|o| declared.contains(o)),
            "missing_literal_copy_verification",
        )?;
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn qualify_entry(
    c: &Catalog<'_>,
    catalog: &Value,
    fields: &Value,
    mapping: &Value,
    ownership: &Value,
    oracle: Option<&Value>,
    row: &Value,
    inherited: &Value,
    branch: &Value,
    e: &Value,
) -> Result<(), String> {
    producer_obligations(e)?;
    let ty = st(row, "semantic_type");
    let path = st(e, "destination");
    let p = &e["producer"];
    check(
        e["applicability"]["output_branch"] == row["output_branch"],
        "wrong_applicability_branch",
    )?;
    check(
        e["destination_schema"] == c.destination(branch, path)?,
        "wrong_destination_schema",
    )?;
    check(
        list(e, "required_subdestinations") == c.nested(&e["destination_schema"], path)?,
        "missing_or_forged_nested_destination",
    )?;
    c.qualified_refs(e)?;
    if st(e, "status") == "BLOCKED" {
        check(e.get("producer").is_none(), "BLOCKED_is_not_a_producer")?;
        let b = &e["blocked"];
        let code = st(b, "code");
        check(
            catalog["blockers"].get(code) == b.get("missing_authority")
                && b["allows_complete_materialization"] == false,
            "unknown_or_forged_blocker",
        )?;
        return Ok(());
    }
    check(st(e, "status") == "QUALIFIED", "unknown_definition_status")?;
    let inputs = list(p, "inputs")
        .iter()
        .map(|q| c.selected(q))
        .collect::<Result<Vec<_>, _>>()?;
    let rule = if st(p, "kind") == "literal_string_copy" {
        Value::Null
    } else {
        c.selected(&p["rule"])?
    };
    let field_rows = list(inherited, "field_dispositions");
    let dotted = ty.replace('/', ".");
    match st(p, "kind") {
        "literal_string_copy" => {
            check(
                p["rule"] == json!({"local_rule":"literal_string_copy"})
                    && st(&catalog["operation"], "id") == "literal_string_copy",
                "unknown_output_operation",
            )?;
            let target = path.strip_prefix('/').ok_or("invalid_label_destination")?;
            let oracle = oracle
                .and_then(|x| x.get(target))
                .ok_or("missing_qualified_label_oracle")?;
            check(
                st(oracle, "mode") == "representation"
                    && p["source_field"] == oracle["source_field"],
                "label_policy_disagreement",
            )?;
            check(
                st(p, "rule_id") == format!("required-output.{dotted}.{target}"),
                "wrong_label_rule_identity",
            )?;
            let source = c.selected(&row["source_schema"])?;
            let field = st(p, "source_field");
            check(
                list(&source, "required").contains(&json!(field)),
                "label_input_not_required",
            )?;
            let q = &row["source_schema"];
            let pointer = format!("{}/properties/{}", st(q, "schema_pointer"), esc(field));
            check(
                p["inputs"] == json!([c.reference(st(q, "canonical_resource_key"), &pointer)?]),
                "wrong_label_input_selector",
            )?;
            let (_, _, shape) = c.deref(st(q, "canonical_resource_key").into(), pointer.clone())?;
            check(shape["type"] == "string", "label_input_not_string")?;
            c.preflight(st(q, "canonical_resource_key"), &pointer)?;
            check(
                st(e, "classification") == "representation_only"
                    && st(e, "semantic_equality")
                        == "original_authored_input_once_not_generated_label",
                "representation_claims_semantic_ownership",
            )?;
            // Do not execute a label: retain the exact string schema, rule and
            // verification obligation, including empty/long/Unicode validity.
        }
        "field_placement" => {
            check(field_rows.contains(&rule), "foreign_inherited_field_rule")?;
            let d = &fields["destination_catalog"][st(&rule, "destination_ref")];
            check(
                d["path"].as_str().or(d["path_template"].as_str()) == Some(path),
                "wrong_field_destination",
            )?;
            check(
                p["inputs"] == json!([c.source_ref(st(&rule, "schema_selector"))?]),
                "wrong_field_input",
            )?;
            check(
                p["rule_id"] == rule["semantic_field_key"]
                    && st(p, "source_field")
                        == st(&rule, "semantic_field_key")
                            .split_once('#')
                            .map(|(_, p)| p)
                            .unwrap_or(""),
                "wrong_inherited_rule_identity",
            )?;
            check(
                st(e, "classification") == "semantic",
                "semantic_field_reclassified",
            )?;
        }
        "field_inventory" => {
            let expected: Vec<_> = field_rows
                .iter()
                .filter(|f| {
                    fields["destination_catalog"][st(f, "destination_ref")]["path_template"] == path
                })
                .cloned()
                .collect();
            check(
                &rule == inherited
                    && inputs == expected
                    && st(p, "rule_id") == format!("inherited-field-inventory.{dotted}"),
                "incomplete_field_inventory",
            )?;
            check(
                st(e, "classification") == "semantic",
                "semantic_inventory_reclassified",
            )?;
        }
        "type_mapping" => {
            check(
                rule == mapping["mappings"][ty]
                    && path == "/entity_type"
                    && p["inputs"] == json!([row["source_schema"]])
                    && st(p, "rule_id") == format!("inherited-type.{dotted}"),
                "unqualified_type_mapping",
            )?;
        }
        "schema_constant" => {
            let selected = c.selected(&e["destination_schema"])?;
            check(
                path == "/record_kind"
                    && selected.get("const").is_some()
                    && p["rule"] == e["destination_schema"]
                    && p["inputs"] == json!([row["source_schema"]])
                    && st(e, "classification") == "representation_only"
                    && st(p, "rule_id") == format!("inherited.{dotted}.record_kind"),
                "unqualified_schema_constant",
            )?;
        }
        "mapping_constant" => {
            check(
                p["rule"]
                    == c.reference(
                        &format!("{BASE}source-mapping-1.7-to-2.5"),
                        &format!(
                            "/mappings/{}/{}",
                            esc(ty),
                            esc(path.trim_start_matches('/'))
                        ),
                    )?
                    && c.selected(&e["destination_schema"])?["const"] == rule
                    && st(p, "rule_id")
                        == format!("inherited.{dotted}.{}", path.trim_start_matches('/')),
                "unqualified_mapping_constant",
            )?;
        }
        "contextual_rule" => {
            let owners: Vec<_> = list(ownership, "rows")
                .iter()
                .filter(|o| st(o, "child_semantic_type") == ty)
                .cloned()
                .collect();
            check(
                ["/lifecycle_stage", "/metadata/ai_lifecycle_provenance"].contains(&path)
                    && &rule == ownership
                    && inputs == owners
                    && !owners.is_empty(),
                "unqualified_declaring_owner_rule",
            )?;
            check(
                p["rule"] == c.reference(&format!("{BASE}lifecycle-ownership"), "")?
                    && st(p, "rule_id") == format!("inherited-declaring-lifecycle.{dotted}"),
                "wrong_ownership_rule_identity",
            )?;
            check(
                list(e, "prerequisites").contains(&json!("declaring_context"))
                    && list(row, "context_dependencies").contains(&json!("declaring_context")),
                "missing_declaring_context_prerequisite",
            )?;
        }
        _ => return Err("unknown_output_operation".into()),
    }
    if let Some(oracle) = oracle.and_then(|o| o.get(path.trim_start_matches('/'))) {
        if st(oracle, "mode") == "authored" {
            check(
                st(p, "kind") == "field_placement"
                    && st(&rule, "semantic_field_key")
                        == format!("{ty}#/{}", st(oracle, "source_field")),
                "authored_label_placement_replaced",
            )?;
        }
    }
    Ok(())
}

#[cfg(test)]
#[path = "architecture_interpretation_v14_tests.rs"]
mod tests;
