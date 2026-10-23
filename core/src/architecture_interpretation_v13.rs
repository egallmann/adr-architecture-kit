//! Private AI 1.3 field/context projection. Never a complete NM model or an ACC outcome.
//! Only the ACC verifier may open the source handoff; the historical interpreter
//! is deliberately not used for successor meaning.
use crate::authoring_construction_authority::Profile;
use crate::authoring_construction_v12::{array, at, canonical, digest, manifest_resources, text};
use crate::authoring_construction_v13::{self as acc, SealResult, SealStatus};
use crate::{candidate_source, object, schema_validation, string, Json};
use std::collections::{BTreeMap, BTreeSet};

const AI: &str = "architecture-interpretation/1.3/";
const FD: &str = "architecture-interpretation/1.3/field-dispositions-1.7-to-2.5";
const OWNER: &str = "architecture-interpretation/1.3/lifecycle-ownership";
const CARRIER: &str = "architecture-interpretation/1.3/lifecycle-provenance.schema";
const NM: &str = "normalized-model/2.5/schema/normalized-entity.schema";
const DECISION_OWNER: &str = "declaring-lifecycle.adr-logical.decisions";

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum Status {
    Rejected,
    Unavailable,
    Unresolved,
    DispositionsQualified,
}

/// Internal findings, not a new transport diagnostic vocabulary.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) struct Finding {
    pub status: Status,
    pub key: String,
    pub detail: String,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Coverage {
    pub semantic_field_key: String,
    pub disposition: Json,
    /// Coverage proof only; embedded child payload is not parent-owned meaning.
    pub source_value: Json,
    pub destination: Json,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Unit {
    pub id: String,
    pub semantic_type: String,
    /// Exact source schema authority; evidence, not semantic identity.
    pub source_qualification: Json,
    /// Exact catalog paths, not a schema-complete normalized entity.
    pub placements: BTreeMap<String, Json>,
    pub semantic_extensions: BTreeMap<String, Json>,
    pub coverage: Vec<Coverage>,
    pub lifecycle_provenance: Option<Json>,
    pub contextual_fact: Option<ContextualFact>,
}

/// The value is the exact published contextual_fact_value (the qualified
/// provenance carrier). Semantic comparison must select the catalog's declared
/// equality fields; integrity qualifiers are not substitute owner identities.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ContextualFact {
    pub semantic_field_key: String,
    pub semantic_identity: String,
    pub value: Json,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Projection {
    pub status: Status,
    pub authority_qualified: bool,
    pub complete_interpretation: Status,
    pub units: Vec<Unit>,
    pub findings: Vec<Finding>,
    pub outstanding: BTreeSet<String>,
    /// Integrity/provenance only. Never a semantic-unit identity.
    pub source_commitment: Option<Json>,
}
impl Projection {
    fn new() -> Self {
        Self {
            status: Status::Unavailable,
            authority_qualified: false,
            complete_interpretation: Status::Unavailable,
            units: vec![],
            findings: vec![],
            outstanding: [
                "complete_nm_2_5_assembly",
                "remaining_semantic_types",
                "whole_result_qualification",
            ]
            .into_iter()
            .map(str::to_owned)
            .collect(),
            source_commitment: None,
        }
    }
    fn issue(&mut self, status: Status, key: &str, detail: impl Into<String>) {
        self.findings.push(Finding {
            status,
            key: key.into(),
            detail: detail.into(),
        });
    }
    fn finish(mut self) -> Self {
        self.findings.sort();
        self.findings.dedup();
        self.status = self
            .findings
            .iter()
            .map(|x| x.status)
            .min()
            .unwrap_or(Status::DispositionsQualified);
        self.units.sort_by(|a, b| a.id.cmp(&b.id));
        if self.status != Status::DispositionsQualified {
            self.units.clear();
            self.source_commitment = None;
        }
        self
    }
}

/// This capability is private and can only be obtained from verified closures.
struct Authority {
    sealed: BTreeMap<String, Json>,
    evaluation: BTreeMap<String, Json>,
    types: BTreeMap<String, Json>,
}

fn error(e: schema_validation::SchemaError) -> String {
    format!("{}: {}", e.path, e.message)
}
fn resolve(
    sealed: &BTreeMap<String, Json>,
    key: &str,
    reference: &str,
) -> Result<(String, Json), String> {
    schema_validation::resolve_reference(sealed, key, reference).map_err(error)
}
fn source_selector(
    sealed: &BTreeMap<String, Json>,
    selector: &str,
) -> Result<(String, Json), String> {
    // Catalog selectors are relative to the exact Authoring schema namespace.
    let (key, node) = resolve(sealed, "authoring/1.7/schema/adr-common.schema", selector)?;
    if !key.starts_with("authoring/1.7/schema/") {
        return Err("Source selector escaped exact Authoring 1.7 schema authority".into());
    }
    Ok((key, node))
}
fn deref(
    sealed: &BTreeMap<String, Json>,
    mut key: String,
    mut schema: Json,
) -> Result<(String, Json), String> {
    let mut seen = BTreeSet::new();
    while let Some(reference) = schema.get("$ref").and_then(Json::as_str) {
        if !seen.insert((key.clone(), reference.to_owned())) {
            return Err("recursive schema selector".into());
        }
        (key, schema) = resolve(sealed, &key, reference)?;
    }
    Ok((key, schema))
}
fn properties(
    sealed: &BTreeMap<String, Json>,
    key: &str,
    schema: &Json,
) -> Result<BTreeMap<String, Json>, String> {
    let (key, schema) = deref(sealed, key.into(), schema.clone())?;
    let mut fields = at(&schema, &["properties"])
        .as_object()
        .cloned()
        .unwrap_or_default();
    for branch in array(&schema, "allOf") {
        for (name, value) in properties(sealed, &key, branch)? {
            if let Some(previous) = fields.get(&name) {
                if previous != &value {
                    fields.insert(
                        name,
                        object([("allOf".into(), Json::Array(vec![previous.clone(), value]))]),
                    );
                }
            } else {
                fields.insert(name, value);
            }
        }
    }
    Ok(fields)
}

/// semanticDependencies is an integrity annotation, not an instance-validation
/// keyword. Qualify every declared edge before projecting schema documents into
/// the existing evaluator. Original bytes remain the authority for all digests.
/// This is isolated to AI 1.3; the historical evaluator is unchanged.
fn qualified_schema_map(sealed: &BTreeMap<String, Json>) -> Result<BTreeMap<String, Json>, String> {
    let mut evaluation = sealed.clone();
    for (key, value) in &mut evaluation {
        if !(key.contains("/schema/") || key.ends_with("/schema") || key.ends_with(".schema")) {
            continue;
        }
        if let Some(dependencies) = value.get("semanticDependencies") {
            let Some(edges) = dependencies.as_array() else {
                return Err("invalid schema dependency annotation".into());
            };
            for edge in edges {
                let Some(name) = edge.as_str() else {
                    return Err("invalid schema dependency edge".into());
                };
                if !sealed.contains_key(name) {
                    return Err(format!("unqualified schema dependency {name}"));
                }
            }
            value
                .as_object_mut()
                .unwrap()
                .remove("semanticDependencies");
        }
    }
    Ok(evaluation)
}

/// Stop at an explicitly governed complete value or child-unit boundary.
/// Otherwise descend schema properties (e.g. the topology container), never
/// runtime array positions. Every schema leaf must have exactly one owner.
fn cover_schema(
    sealed: &BTreeMap<String, Json>,
    key: &str,
    schema: &Json,
    path: &str,
    covered: &BTreeSet<String>,
    found: &mut BTreeSet<String>,
) -> Result<(), String> {
    if covered.contains(path) {
        found.insert(path.into());
        return Ok(());
    }
    let fields = properties(sealed, key, schema)?;
    if fields.is_empty() {
        return Err(format!("unclassified schema field {path}"));
    }
    for (name, node) in fields {
        cover_schema(
            sealed,
            key,
            &node,
            &format!("{path}/{}", escape(&name)),
            covered,
            found,
        )?;
    }
    Ok(())
}

impl Authority {
    fn qualify(
        definition: &Json,
        resources: &[Json],
        nm_definition: &Json,
    ) -> Result<Self, String> {
        if !acc::authority_qualifies(definition, resources, nm_definition) {
            return Err("Exact ACC 1.3 / AI 1.3 / NM 2.5 authority unavailable".into());
        }
        let sealed = manifest_resources(definition, resources);
        let evaluation = qualified_schema_map(&sealed)?;
        for (value, schema) in [
            ("field-dispositions-1.7-to-2.5", "field-dispositions.schema"),
            ("lifecycle-ownership", "lifecycle-ownership.schema"),
            ("contextual-facts", "contextual-facts.schema"),
        ] {
            let sk = format!("{AI}{schema}");
            schema_validation::preflight_fragment(&evaluation, &sk, "").map_err(error)?;
            schema_validation::validate(&evaluation, &sk, &sealed[&format!("{AI}{value}")])
                .map_err(error)?;
        }
        schema_validation::preflight_fragment(&evaluation, CARRIER, "").map_err(error)?;
        let catalog = &sealed[FD];
        let destinations = at(catalog, &["destination_catalog"]);
        let mut types: BTreeMap<String, Json> = BTreeMap::new();
        let mut keys = BTreeSet::new();
        for ty in array(catalog, "semantic_types") {
            let name = text(ty, "semantic_type");
            if types.insert(name.into(), ty.clone()).is_some() {
                return Err("duplicate semantic type".into());
            }
            let (key, schema) = source_selector(&sealed, text(ty, "source_schema"))?;
            let mut covered = BTreeSet::new();
            for field in array(ty, "field_dispositions") {
                let fk = text(field, "semantic_field_key");
                let Some(pointer) = fk.strip_prefix(&format!("{name}#")) else {
                    return Err("field key has wrong semantic owner".into());
                };
                if !keys.insert(fk.to_owned()) || !covered.insert(pointer.to_owned()) {
                    return Err("duplicate field disposition".into());
                }
                source_selector(&sealed, text(field, "schema_selector"))?;
                let dest = destinations
                    .get(text(field, "destination_ref"))
                    .ok_or("unknown destination")?;
                if at(catalog, &["matching_identity_catalog"])
                    .get(text(field, "matching_identity_ref"))
                    .is_none()
                {
                    return Err("unknown matching identity".into());
                }
                if let Some(companion) = field.get("companion_destination_ref") {
                    if destinations
                        .get(companion.as_str().ok_or("invalid companion destination")?)
                        .is_none()
                    {
                        return Err("unknown companion destination".into());
                    }
                }
                match text(field, "disposition") {
                    "canonical_field_placement"
                        if [
                            "normalized_entity",
                            "normalized_custom_extension",
                            "canonical_relationship",
                            "normalized_normative_proposition",
                        ]
                        .contains(&text(dest, "kind")) => {}
                    "direct_semantic_value" => {}
                    "compatibility_projection"
                        if text(dest, "kind") == "compatibility_projection" => {}
                    "declared_absence" => {}
                    "deterministic_ceremony" => {
                        let rule = at(catalog, &["derivation_rules"])
                            .get(text(field, "derivation_rule_ref"))
                            .ok_or("unknown ceremony derivation")?;
                        if at(rule, &["semantic_choice"]) != &Json::Bool(false)
                            || text(dest, "kind") != "no_normalized_value"
                        {
                            return Err("non-deterministic ceremony".into());
                        }
                    }
                    _ => return Err("inconsistent disposition class/destination".into()),
                }
                let target = match text(dest, "kind") {
                    "normalized_entity" | "normalized_custom_extension" => Some((NM, "/oneOf/0")),
                    "normalized_normative_proposition" => Some((NM, "/oneOf/1")),
                    "canonical_relationship" => Some((
                        "normalized-model/2.5/schema/relationship-record.schema",
                        "/oneOf/0",
                    )),
                    _ => None,
                };
                if let Some((target, branch)) = target {
                    let (mut k, mut node) = resolve(&sealed, target, &format!("#{branch}"))?;
                    for part in text(dest, "path").split('/').skip(1) {
                        (k, node) = deref(&sealed, k, node)?;
                        node = properties(&sealed, &k, &node)?
                            .remove(part)
                            .ok_or("unknown normalized destination property")?;
                    }
                }
            }
            let mut expected = BTreeSet::new();
            cover_schema(&sealed, &key, &schema, "", &covered, &mut expected)?;
            if expected != covered {
                return Err(format!("incomplete schema field catalog for {name}"));
            }
        }
        if types.len() != 27 {
            return Err("closed semantic catalog cardinality differs".into());
        }
        let mapping = &sealed[&format!("{AI}source-mapping-1.7-to-2.5")];
        if text(mapping, "source_contract") != "authoring@1.7"
            || text(mapping, "output_contract") != "normalized-model@2.5"
            || text(mapping, "field_dispositions") != FD
        {
            return Err("incorrect source mapping authority".into());
        }
        for name in types.keys() {
            if at(mapping, &["mappings"]).get(name).is_none() {
                return Err("missing semantic type mapping".into());
            }
        }
        let this = Self {
            sealed,
            evaluation,
            types,
        };
        for ty in [
            "adr/logical",
            "adr/physical-system",
            "adr/physical-component",
        ] {
            this.lifecycle_domain(ty)?;
        }
        Ok(this)
    }
    fn field(&self, ty: &str, pointer: &str) -> Result<&Json, String> {
        let t = self.types.get(ty).ok_or("unsupported semantic type")?;
        let matches: Vec<_> = array(t, "field_dispositions")
            .iter()
            .filter(|f| text(f, "semantic_field_key") == format!("{ty}#{pointer}"))
            .collect();
        match matches.as_slice() {
            [field] => Ok(field),
            _ => Err("field must have exactly one disposition".into()),
        }
    }
    fn lifecycle_domain(&self, ty: &str) -> Result<Vec<Json>, String> {
        let field = self.field(ty, "/status")?;
        if text(field, "disposition") != "canonical_field_placement"
            || text(field, "value_semantics") != "exact_typed_value"
        {
            return Err("literal lifecycle placement required".into());
        }
        let (key, schema) = source_selector(&self.sealed, text(field, "schema_selector"))?;
        let (_, source) = deref(&self.sealed, key, schema)?;
        let values = array(&source, "enum");
        if values.is_empty() {
            return Err("finite source status domain unavailable".into());
        }
        let destination = at(
            &self.sealed[&format!("{AI}rules")],
            &["lifecycle_authority", "destination_schema"],
        );
        let target_key = text(destination, "canonical_resource_key");
        if self
            .sealed
            .get(target_key)
            .map(|v| format!("sha256:{}", digest(v)))
            .as_deref()
            != Some(text(destination, "content_digest"))
        {
            return Err("unqualified lifecycle destination".into());
        }
        for value in values {
            schema_validation::validate_fragment(
                &self.evaluation,
                target_key,
                text(destination, "schema_pointer"),
                value,
            )
            .map_err(error)?;
            if at(
                &self.sealed[&format!("{AI}rules")],
                &["lifecycle_authority", "authored_to_normalized"],
            )
            .get(value.as_str().ok_or("non-string status")?)
                != Some(value)
            {
                return Err("nonliteral lifecycle rule".into());
            }
        }
        Ok(values.to_vec())
    }
    fn lifecycle(&self, ty: &str, value: &Json) -> Result<Json, String> {
        if !self.lifecycle_domain(ty)?.contains(value) {
            return Err("invalid authored lifecycle; no defaults or inverse active mapping".into());
        }
        Ok(value.clone())
    }

    /// Root-only lifecycle fact; physical root field/ownership execution remains
    /// outside this slice. The complete source is schema-qualified first.
    fn root_lifecycle(&self, ty: &str, source: &Json) -> Result<Json, String> {
        let t = self.types.get(ty).ok_or("unknown root type")?;
        let (key, _) = source_selector(&self.sealed, text(t, "source_schema"))?;
        schema_validation::preflight_fragment(&self.evaluation, &key, "").map_err(error)?;
        schema_validation::validate(&self.evaluation, &key, source).map_err(error)?;
        self.lifecycle(ty, at(source, &["status"]))
    }
}

fn escape(s: &str) -> String {
    s.replace('~', "~0").replace('/', "~1")
}

fn project_fields(
    authority: &Authority,
    ty: &str,
    source: &Json,
    result: &mut Projection,
) -> Option<Unit> {
    let Some(t) = authority.types.get(ty) else {
        result.issue(Status::Unavailable, ty, "Unimplemented semantic type");
        return None;
    };
    let (key, _) = match source_selector(&authority.sealed, text(t, "source_schema")) {
        Ok(v) => v,
        Err(e) => {
            result.issue(Status::Unavailable, ty, e);
            return None;
        }
    };
    // Validate all prepared source fields against the exact selected schema.
    let pointer = text(t, "source_schema")
        .split_once('#')
        .map(|(_, p)| p)
        .unwrap_or("");
    if let Err(e) =
        schema_validation::validate_fragment(&authority.evaluation, &key, pointer, source)
    {
        result.issue(Status::Rejected, ty, error(e));
    }
    let mut unit = Unit {
        id: text(source, "id").into(),
        semantic_type: ty.into(),
        source_qualification: object([
            ("family".into(), string("authoring")),
            ("version".into(), string("1.7")),
            ("canonical_resource_key".into(), string(&key)),
            (
                "content_digest".into(),
                string(format!("sha256:{}", digest(&authority.sealed[&key]))),
            ),
            ("schema_pointer".into(), string(pointer)),
        ]),
        placements: BTreeMap::new(),
        semantic_extensions: BTreeMap::new(),
        coverage: vec![],
        lifecycle_provenance: None,
        contextual_fact: None,
    };
    let mapping = at(
        &authority.sealed[&format!("{AI}source-mapping-1.7-to-2.5")],
        &["mappings", ty],
    );
    let entity_type = at(mapping, &["output"]).clone();
    if let Err(e) = schema_validation::validate_fragment(
        &authority.evaluation,
        NM,
        "/oneOf/0/properties/entity_type",
        &entity_type,
    ) {
        result.issue(Status::Unavailable, ty, error(e));
    }
    unit.placements.insert("/entity_type".into(), entity_type);
    let Some(fields) = source.as_object() else {
        result.issue(Status::Rejected, ty, "Object source required");
        return None;
    };
    for (name, value) in fields {
        let pointer = format!("/{}", escape(name));
        let f = match authority.field(ty, &pointer) {
            Ok(f) => f,
            Err(e) => {
                result.issue(Status::Unavailable, &format!("{ty}#{pointer}"), e);
                continue;
            }
        };
        let dest = at(&authority.sealed[FD], &["destination_catalog"])
            .get(text(f, "destination_ref"))
            .unwrap();
        let fk = text(f, "semantic_field_key");
        match (text(f, "disposition"), text(dest, "kind")) {
            ("canonical_field_placement", "normalized_entity") => {
                if text(dest, "path") == "/lifecycle_stage" {
                    if let Err(e) = authority.lifecycle(ty, value) {
                        result.issue(Status::Rejected, fk, e);
                        continue;
                    }
                }
                if let Err(e) = schema_validation::validate_fragment(
                    &authority.evaluation,
                    NM,
                    &format!("/oneOf/0/properties{}", text(dest, "path")),
                    value,
                ) {
                    result.issue(Status::Rejected, fk, error(e));
                }
                if unit
                    .placements
                    .insert(text(dest, "path").into(), value.clone())
                    .is_some()
                {
                    result.issue(
                        Status::Rejected,
                        fk,
                        "Multiple fields select one destination",
                    );
                }
            }
            ("direct_semantic_value", "semantic_extension") => {
                unit.semantic_extensions.insert(fk.into(), value.clone());
            }
            ("direct_semantic_value", "child_membership") => {
                let mut ids = vec![];
                let mut unique = BTreeSet::new();
                for child in value.as_array().into_iter().flatten() {
                    let id = text(child, "id");
                    if id.is_empty() || !unique.insert(id) {
                        result.issue(Status::Rejected, fk, "Missing or duplicated child identity");
                    }
                    ids.push(string(id));
                }
                if value.as_array().is_none() {
                    result.issue(Status::Rejected, fk, "Child membership is not an array");
                }
                if name != "decisions" && !ids.is_empty() {
                    result.issue(
                        Status::Unavailable,
                        fk,
                        "Child semantic type execution is outside this slice",
                    );
                }
                unit.semantic_extensions.insert(fk.into(), Json::Array(ids));
            }
            ("deterministic_ceremony", "no_normalized_value") => {}
            _ => result.issue(
                Status::Unavailable,
                fk,
                "Selected disposition execution is not implemented",
            ),
        }
        unit.coverage.push(Coverage {
            semantic_field_key: fk.into(),
            disposition: f.clone(),
            source_value: value.clone(),
            destination: dest.clone(),
        });
    }
    Some(unit)
}

/// No minter and no insertion producer: verification replays already established identities.
pub(crate) fn interpret(
    definition: &Json,
    resources: &[Json],
    nm_definition: &Json,
    request: &Json,
    source_refs: &BTreeMap<String, String>,
    supplied: &SealResult,
) -> Projection {
    let mut result = Projection::new();
    let authority = match Authority::qualify(definition, resources, nm_definition) {
        Ok(a) => a,
        Err(e) => {
            result.issue(Status::Unavailable, "authority", e);
            return result.finish();
        }
    };
    result.authority_qualified = true;
    let verified = acc::verify(
        definition,
        resources,
        nm_definition,
        request,
        source_refs,
        supplied,
    );
    if verified.status != SealStatus::Sealed {
        for finding in verified.diagnostics {
            // A producer that released no seal supplies no interpretation
            // prerequisite. A forged Sealed claim still fails as invalid proof.
            // The negative status gate can deny execution, never qualify it;
            // independent request/authority violations from verify remain intact.
            let status = if finding.field_or_relation_key == "receipts"
                && supplied.status != SealStatus::Sealed
            {
                Status::Unavailable
            } else {
                match finding.status {
                    crate::authoring_construction_v12::Status::Rejected => Status::Rejected,
                    crate::authoring_construction_v12::Status::Unresolved => Status::Unresolved,
                    _ => Status::Unavailable,
                }
            };
            result.issue(
                status,
                &finding.field_or_relation_key,
                canonical(&finding.payload),
            );
        }
        if result.findings.is_empty() {
            result.issue(
                Status::Unavailable,
                "sealed_source",
                "Independently verified ACC 1.3 source handoff required",
            );
        }
        return result.finish();
    }
    let evidence = verified.evidence.as_ref().unwrap();
    let mut identities = BTreeSet::new();
    let mut owners = BTreeMap::new();
    let mut used_records = BTreeSet::new();
    for artifact in &evidence.basis.artifacts {
        let source = match candidate_source::decode_canonical_candidate(&artifact.bytes) {
            Ok(s) => s,
            Err(e) => {
                result.issue(Status::Rejected, &artifact.source_ref, e);
                continue;
            }
        };
        if artifact.source_schema.canonical_resource_key
            != "authoring/1.7/schema/adr-logical.schema"
            || !artifact.source_schema.json_pointer.is_empty()
        {
            result.issue(Status::Unavailable,&artifact.source_ref,"Native root remains represented; complete lifecycle/context interpretation is unavailable for this root");
            continue;
        }
        let Some(parent) = project_fields(&authority, "adr/logical", &source, &mut result) else {
            continue;
        };
        if !identities.insert(parent.id.clone()) {
            result.issue(
                Status::Rejected,
                &parent.id,
                "Semantic unit interpreted more than once",
            );
        }
        for child in array(&source, "decisions") {
            let Some(mut unit) = project_fields(&authority, "entity/decision", child, &mut result)
            else {
                continue;
            };
            if !identities.insert(unit.id.clone())
                || owners.insert(unit.id.clone(), parent.id.clone()).is_some()
            {
                result.issue(
                    Status::Rejected,
                    &unit.id,
                    "Competing or duplicated declaring ownership",
                );
            }
            match ownership(
                &authority,
                &source,
                child,
                artifact,
                &verified.composition_records,
                &evidence.retained_artifacts,
            ) {
                Ok((carrier, fact, index)) => {
                    unit.placements
                        .insert("/lifecycle_stage".into(), at(&source, &["status"]).clone());
                    unit.lifecycle_provenance = Some(carrier);
                    unit.contextual_fact = Some(fact);
                    if !used_records.insert(index) {
                        result.issue(Status::Rejected, &unit.id, "Duplicate record ownership");
                    }
                }
                Err((status, e)) => result.issue(status, &unit.id, e),
            }
            result.units.push(unit);
        }
        result.units.push(parent);
    }
    if used_records.len() != verified.composition_records.len() {
        result.issue(Status::Rejected,"composition_records","Every verified composition must have one independently interpreted ownership association");
    }
    result.source_commitment = Some(object([
        ("basis_digest".into(), string(&evidence.basis.basis_digest)),
        (
            "context_qualification".into(),
            evidence.context.qualification.clone(),
        ),
    ]));
    result.finish()
}

fn ownership(
    a: &Authority,
    parent: &Json,
    child: &Json,
    parent_artifact: &candidate_source::CandidateSourceArtifact,
    records: &[Json],
    retained: &[candidate_source::CandidateSourceArtifact],
) -> Result<(Json, ContextualFact, usize), (Status, String)> {
    let unavailable = |s: &str| (Status::Unavailable, s.to_owned());
    let rejected = |s: &str| (Status::Rejected, s.to_owned());
    let rows: Vec<_> = array(&a.sealed[OWNER], "rows")
        .iter()
        .filter(|r| text(r, "rule_id") == DECISION_OWNER)
        .collect();
    let [rule] = rows.as_slice() else {
        return Err(unavailable("Exact declaring ownership rule unavailable"));
    };
    let source_schema = at(rule, &["source_schema"]);
    let status_source = at(rule, &["status_source_authority"]);
    if text(source_schema, "canonical_resource_key")
        != parent_artifact.source_schema.canonical_resource_key
        || text(source_schema, "schema_pointer") != parent_artifact.source_schema.json_pointer
        || text(status_source, "canonical_resource_key")
            != text(source_schema, "canonical_resource_key")
        || a.sealed
            .get(text(status_source, "canonical_resource_key"))
            .map(|v| format!("sha256:{}", digest(v)))
            .as_deref()
            != Some(text(status_source, "content_digest"))
        || text(rule, "status_semantic_field_key")
            != text(
                a.field("adr/logical", "/status")
                    .map_err(|e| (Status::Unavailable, e))?,
                "semantic_field_key",
            )
    {
        return Err(unavailable(
            "Declaring status/source schema qualification differs",
        ));
    }
    // Establish schema containment independently of composition intent/record.
    for q in array(rule, "ownership_schema_path") {
        let key = text(q, "canonical_resource_key");
        if a.sealed
            .get(key)
            .map(|v| format!("sha256:{}", digest(v)))
            .as_deref()
            != Some(text(q, "content_digest"))
        {
            return Err(unavailable("Ownership schema qualification mismatch"));
        }
        let (target_key, node) =
            resolve(&a.sealed, key, &format!("#{}", text(q, "schema_pointer")))
                .map_err(|e| (Status::Unavailable, e))?;
        let (target_key, node) =
            deref(&a.sealed, target_key, node).map_err(|e| (Status::Unavailable, e))?;
        let (child_key, child_schema) = source_selector(
            &a.sealed,
            text(&a.types["entity/decision"], "source_schema"),
        )
        .map_err(|e| (Status::Unavailable, e))?;
        if target_key != child_key || node != child_schema {
            return Err(unavailable("Schema containment does not select Decision"));
        }
    }
    if text(rule, "source_instance_pattern") != "/decisions/*"
        || text(rule, "parent_semantic_type") != "adr/logical"
        || text(rule, "child_semantic_type") != "entity/decision"
    {
        return Err(unavailable("Ownership path execution not implemented"));
    }
    let matches: Vec<_> = array(parent, "decisions")
        .iter()
        .filter(|v| text(v, "id") == text(child, "id"))
        .collect();
    if matches.len() != 1 || matches[0] != child {
        return Err(rejected("Unique exact child subtree required"));
    }
    let rr: Vec<_> = records
        .iter()
        .enumerate()
        .filter(|(_, r)| {
            text(at(r, &["semantic"]), "parent_canonical_uuid") == text(parent, "id")
                && text(at(r, &["semantic"]), "child_canonical_uuid") == text(child, "id")
        })
        .collect();
    let [(index, record)] = rr.as_slice() else {
        return Err(rejected("Unique verified composition linkage required"));
    };
    let integrity = at(record, &["integrity"]);
    if text(integrity, "parent_source_ref") != parent_artifact.source_ref
        || text(at(record, &["semantic"]), "authoring_property") != "decisions"
    {
        return Err(rejected("Source-to-record association differs"));
    }
    let child_artifacts: Vec<_> = retained
        .iter()
        .filter(|v| v.source_ref == text(integrity, "child_source_ref"))
        .collect();
    let [child_artifact] = child_artifacts.as_slice() else {
        return Err(rejected("Independent retained child artifact required"));
    };
    if candidate_source::decode_canonical_candidate(&child_artifact.bytes)
        .map_err(|e| (Status::Rejected, e))?
        != *child
    {
        return Err(rejected(
            "Retained child differs from exact embedded subtree",
        ));
    }
    a.root_lifecycle("adr/logical", parent)
        .map_err(|e| (Status::Rejected, e))?;
    let carrier = object([
        ("declaring_adr_id".into(), at(parent, &["id"]).clone()),
        (
            "declaring_adr_semantic_type".into(),
            at(rule, &["declaring_adr_semantic_type"]).clone(),
        ),
        (
            "status_semantic_field_key".into(),
            at(rule, &["status_semantic_field_key"]).clone(),
        ),
        (
            "status_source_authority".into(),
            at(rule, &["status_source_authority"]).clone(),
        ),
        (
            "ownership_rule".into(),
            object([
                ("family".into(), string("architecture-interpretation")),
                ("version".into(), string("1.3")),
                (
                    "semantic_contract_fingerprint".into(),
                    string(Profile::Acc13.expected().ai_scf),
                ),
                ("canonical_resource_key".into(), string(OWNER)),
                (
                    "content_digest".into(),
                    string(format!("sha256:{}", digest(&a.sealed[OWNER]))),
                ),
                ("rule_id".into(), at(rule, &["rule_id"]).clone()),
            ]),
        ),
        (
            "value_destination".into(),
            at(rule, &["value_destination"]).clone(),
        ),
    ]);
    schema_validation::validate(&a.evaluation, CARRIER, &carrier)
        .map_err(|e| (Status::Unavailable, error(e)))?;
    let fact = &array(&a.sealed[&format!("{AI}contextual-facts")], "facts")[0];
    schema_validation::validate_fragment(
        &a.evaluation,
        &format!("{AI}contextual-facts.schema"),
        "/$defs/contextual_fact_value",
        &carrier,
    )
    .map_err(|e| (Status::Unavailable, error(e)))?;
    let context = ContextualFact {
        semantic_field_key: text(fact, "semantic_field_key").into(),
        semantic_identity: text(child, "id").into(),
        value: carrier.clone(),
    };
    Ok((carrier, context, *index))
}

/// Independently recompute all facts and compare complete evidence, including
/// extra/missing contextual facts and placement/coverage mutations.
pub(crate) fn verify_projection(
    definition: &Json,
    resources: &[Json],
    nm_definition: &Json,
    request: &Json,
    source_refs: &BTreeMap<String, String>,
    sealed: &SealResult,
    supplied: &Projection,
) -> Projection {
    let mut result = interpret(
        definition,
        resources,
        nm_definition,
        request,
        source_refs,
        sealed,
    );
    if result.status == Status::DispositionsQualified && &result != supplied {
        result.issue(
            Status::Rejected,
            "projection",
            "Projection differs from independently derived source/authority meaning",
        );
    }
    result.finish()
}

#[cfg(test)]
#[path = "architecture_interpretation_v13_tests.rs"]
mod tests;
