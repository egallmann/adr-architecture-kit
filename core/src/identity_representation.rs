//! Bounded AI-owned representation facts from native, already-authored sources.
//! No identity allocation, compact construction, model assembly or public route.
use crate::candidate_authority::{self as authority, Bundle, Qualification};
use crate::candidate_source::{self as source, CandidateSourceBasis, CandidateSourceSelector};
use crate::{object, schema_validation as schema, string, Json};
use std::collections::{BTreeMap, BTreeSet};

const CATALOG: &str = "architecture-interpretation/1.5/required-output-derivations";
const RECIPES: &str = "architecture-interpretation/1.5/identity-representation-recipes";
const CONTEXT: &str = "architecture-interpretation/1.3/detached-context";
const OWNERSHIP: &str = "architecture-interpretation/1.3/lifecycle-ownership";

#[derive(Clone, Copy)]
pub(crate) struct Inputs<'a> {
    pub nm: Bundle<'a>,
    pub ai: Bundle<'a>,
    pub acc: Bundle<'a>,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum Status {
    Rejected,
    Unavailable,
    Executed,
    Verified,
}
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) struct Finding {
    pub status: Status,
    pub key: String,
    pub detail: String,
}
type Failure = Vec<Finding>;
fn fail(status: Status, key: &str, detail: impl Into<String>) -> Failure {
    vec![Finding {
        status,
        key: key.into(),
        detail: detail.into(),
    }]
}
fn rejected(key: &str, detail: impl Into<String>) -> Failure {
    fail(Status::Rejected, key, detail)
}
fn unavailable(key: &str, detail: impl Into<String>) -> Failure {
    fail(Status::Unavailable, key, detail)
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
fn pointer<'a>(v: &'a Json, p: &str) -> Option<&'a Json> {
    if p.is_empty() {
        return Some(v);
    }
    p.strip_prefix('/')?.split('/').try_fold(v, |node, token| {
        let token = token.replace("~1", "/").replace("~0", "~");
        match node {
            Json::Object(o) => o.get(&token),
            Json::Array(a) => token.parse::<usize>().ok().and_then(|n| a.get(n)),
            _ => None,
        }
    })
}
fn field<'a>(v: &'a Json, p: &str) -> &'a Json {
    pointer(v, p).unwrap_or(&Json::Null)
}
fn qualify(i: Inputs<'_>) -> Result<Qualification, Failure> {
    let q = authority::qualify(i.nm, i.ai, i.acc);
    if q.status() == authority::Status::AuthorityQualified {
        for key in [CATALOG, RECIPES, CONTEXT, OWNERSHIP] {
            if !q.resources().contains_key(key) {
                return Err(unavailable(
                    key,
                    "Required current recipe authority is absent",
                ));
            }
        }
        Ok(q)
    } else {
        Err(q
            .findings()
            .iter()
            .map(|d| Finding {
                status: if d.status == authority::Status::Rejected {
                    Status::Rejected
                } else {
                    Status::Unavailable
                },
                key: d.key.clone(),
                detail: d.detail.clone(),
            })
            .collect())
    }
}

/// Raw native source input, not an asserted proof or a construction request.
/// The authored UUID is already present. No argument can replace that identity.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct OriginalSource {
    pub source_ref: String,
    pub artifact_kind: String,
    pub selector: CandidateSourceSelector,
    pub bytes: Vec<u8>,
}
/// Immutable source anchor. Only the checked native-source binding constructs it.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SealedSources {
    originals: Vec<OriginalSource>,
    authorities: Vec<authority::Authority>,
    basis: CandidateSourceBasis,
    context: Json,
}
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) struct Selection {
    pub source_ref: String,
    pub pointer: String,
    pub semantic_type: String,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Representation {
    pub id: String,
    pub namespace: String,
    pub semantic_type: String,
    pub branch: String,
    pub source_ref: String,
    pub source_pointer: String,
    pub alias_ref: String,
    pub uri: String,
    pub created_at: String,
    rules: Vec<Json>,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Projection {
    status: Status,
    findings: Failure,
    values: Vec<Representation>,
    authorities: Vec<authority::Authority>,
    basis_digest: String,
}
impl Projection {
    pub(crate) fn status(&self) -> Status {
        self.status
    }
    pub(crate) fn findings(&self) -> &[Finding] {
        &self.findings
    }
    pub(crate) fn values(&self) -> &[Representation] {
        &self.values
    }
    pub(crate) fn complete_interpretation(&self) -> Status {
        Status::Unavailable
    }
    fn failure(mut findings: Failure) -> Self {
        findings.sort();
        findings.dedup();
        Self {
            status: findings
                .first()
                .map(|x| x.status)
                .unwrap_or(Status::Unavailable),
            findings,
            values: vec![],
            authorities: vec![],
            basis_digest: String::new(),
        }
    }
}
fn manifest_digest<'a>(i: Inputs<'a>, key: &str) -> Option<&'a str> {
    [i.acc.definition, i.ai.definition, i.nm.definition]
        .iter()
        .flat_map(|d| array(d, "resourceManifest"))
        .find(|m| text(m, "canonicalResourceKey") == key)
        .map(|m| text(m, "contentDigest"))
}
fn reference<'a>(i: Inputs<'_>, q: &'a Qualification, r: &Json) -> Result<&'a Json, Failure> {
    let key = text(r, "canonical_resource_key");
    if manifest_digest(i, key) != Some(text(r, "content_digest")) {
        return Err(rejected(key, "Unqualified selector digest"));
    }
    q.resources()
        .get(key)
        .and_then(|v| pointer(v, text(r, "schema_pointer")))
        .ok_or_else(|| unavailable(key, "Exact selected schema/rule fragment unavailable"))
}
fn schema_map(q: &Qualification) -> Result<BTreeMap<String, Json>, Failure> {
    crate::architecture_interpretation_v13::qualified_schema_map(q.resources())
        .map_err(|e| unavailable("schema", e))
}
fn validate(
    map: &BTreeMap<String, Json>,
    key: &str,
    pointer: &str,
    value: &Json,
) -> Result<(), Failure> {
    schema::preflight_fragment(map, key, pointer).map_err(|e| unavailable(key, e.message))?;
    schema::validate_fragment(map, key, pointer, value)
        .map_err(|e| rejected(key, format!("{}: {}", e.path, e.message)))
}
fn source_contract(i: Inputs<'_>) -> Json {
    let mut resources: Vec<_> = array(i.acc.definition, "resourceManifest")
        .iter()
        .filter(|m| text(m, "canonicalResourceKey").starts_with("authoring/1.7/schema/"))
        .map(|m| {
            object([
                (
                    "canonical_resource_key".into(),
                    string(text(m, "canonicalResourceKey")),
                ),
                ("content_digest".into(), string(text(m, "contentDigest"))),
            ])
        })
        .collect();
    resources
        .sort_by(|a, b| text(a, "canonical_resource_key").cmp(text(b, "canonical_resource_key")));
    object([
        ("family".into(), string("authoring")),
        ("version".into(), string("1.7")),
        ("resources".into(), Json::Array(resources)),
    ])
}
fn type_row<'a>(q: &'a Qualification, key: &str, pointer: &str) -> Result<&'a Json, Failure> {
    let rows: Vec<_> = array(&q.resources()[CATALOG], "types")
        .iter()
        .filter(|r| {
            text(field(r, "/source_schema"), "canonical_resource_key") == key
                && text(field(r, "/source_schema"), "schema_pointer") == pointer
        })
        .collect();
    if rows.len() != 1 {
        return Err(unavailable(
            key,
            "No unique catalog/source occurrence qualification",
        ));
    }
    Ok(rows[0])
}
fn reconstruct_basis(
    i: Inputs<'_>,
    q: &Qualification,
    originals: &[OriginalSource],
) -> Result<CandidateSourceBasis, Failure> {
    let map = schema_map(q)?;
    // The native renderer's compiled schema catalog must be actual selected authority.
    let compiled = source::authoring_schema_resources().map_err(|e| unavailable("source", e))?;
    if compiled
        .iter()
        .any(|(k, v)| q.resources().get(k) != Some(v))
    {
        return Err(unavailable(
            "source",
            "Native source schema catalog differs from qualified authority",
        ));
    }
    let mut artifacts = vec![];
    let mut findings = vec![];
    for o in originals {
        let checked = (|| {
            let key = &o.selector.canonical_resource_key;
            let pointer = &o.selector.json_pointer;
            let row = type_row(q, key, pointer)?;
            if !matches!(
                text(row, "output_branch"),
                "regular" | "normative-proposition"
            ) {
                return Err(unavailable(&o.source_ref,"Relationship/value branches do not establish an independent entity recipe source"));
            }
            reference(i, q, field(row, "/source_schema"))?;
            if text(row, "semantic_type").starts_with("adr/")
                && o.artifact_kind != "authoring_document"
            {
                return Err(rejected(
                    &o.source_ref,
                    "A native ADR document cannot be relabeled as a fragment",
                ));
            }
            if o.artifact_kind == "authoring_document"
                && (!text(row, "semantic_type").starts_with("adr/") || !pointer.is_empty())
            {
                return Err(unavailable(
                    &o.source_ref,
                    "Catalog membership cannot grant a native ADR root",
                ));
            }
            let value = source::decode_canonical_candidate(&o.bytes)
                .map_err(|e| rejected(&o.source_ref, e))?;
            validate(&map, key, pointer, &value)?;
            if !crate::authoring_construction_basis_v11::is_uuid_v7(text(&value, "id")) {
                return Err(rejected(
                    &o.source_ref,
                    "An existing canonical lowercase UUIDv7 is required",
                ));
            }
            let artifact = source::seal_candidate_artifact(
                &o.source_ref,
                &o.source_ref,
                &o.artifact_kind,
                o.selector.clone(),
                source_contract(i),
                &value,
            )
            .map_err(|e| rejected(&o.source_ref, e))?;
            if artifact.bytes != o.bytes {
                return Err(rejected(
                    &o.source_ref,
                    "Original bytes cannot be rewritten or normalized",
                ));
            }
            source::decode_and_validate_candidate(&artifact)
                .map_err(|e| rejected(&o.source_ref, e))?;
            Ok(artifact)
        })();
        match checked {
            Ok(a) => artifacts.push(a),
            Err(mut e) => findings.append(&mut e),
        }
    }
    if !findings.is_empty() {
        return Err(findings);
    }
    source::seal_candidate_source_basis(artifacts).map_err(|e| rejected("basis", e))
}
fn detached(
    i: Inputs<'_>,
    q: &Qualification,
    basis: &CandidateSourceBasis,
    selection: Option<&str>,
) -> Result<Json, Failure> {
    if selection != Some(CONTEXT) {
        return Err(unavailable(
            "provider",
            "Missing or unsupported independently qualified provider selection",
        ));
    }
    let recipes = &q.resources()[RECIPES];
    let selected = field(recipes, "/context_authority/qualification");
    let r = reference(i, q, selected)?;
    if text(selected, "canonical_resource_key") != CONTEXT
        || text(r, "provider_kind").is_empty()
        || text(r, "architecture_namespace").is_empty()
    {
        return Err(unavailable(
            "provider",
            "Detached provider authority unavailable",
        ));
    }
    let hex = basis
        .basis_digest
        .strip_prefix("sha256:")
        .ok_or_else(|| rejected("basis", "Invalid native basis digest"))?;
    let scope = text(r, "scope_root_form").replace("<lowercase-basis-digest>", hex);
    let roots = basis
        .artifacts
        .iter()
        .map(|a| {
            use sha2::{Digest, Sha256};
            let locator = text(r, "root_artifact_locator_form")
                .replace("<lowercase-basis-digest>", hex)
                .replace(
                    "<SHA-256-of-UTF-8-source_ref>",
                    &format!("{:x}", Sha256::digest(a.source_ref.as_bytes())),
                );
            object([
                ("source_ref".into(), string(&a.source_ref)),
                ("source_pointer".into(), string("/")),
                ("artifact_locator".into(), string(locator)),
            ])
        })
        .collect::<Vec<_>>();
    Ok(object([
        (
            "domain".into(),
            r.get("domain").cloned().unwrap_or(Json::Null),
        ),
        ("provider_kind".into(), string(text(r, "provider_kind"))),
        (
            "architecture_namespace".into(),
            string(text(r, "architecture_namespace")),
        ),
        ("scope_root".into(), string(scope)),
        ("roots".into(), Json::Array(roots)),
        (
            "qualification".into(),
            field(recipes, "/context_authority").clone(),
        ),
        (
            "authorities".into(),
            Json::Array(
                q.authorities()
                    .iter()
                    .map(|a| {
                        object([
                            ("family".into(), string(&a.family)),
                            ("version".into(), string(&a.version)),
                            ("fingerprint".into(), string(&a.fingerprint)),
                        ])
                    })
                    .collect(),
            ),
        ),
    ]))
}

/// Bind already-authored native bytes, not ACC construction receipts. All supplied
/// native artifacts remain roots; this seam never omits a separately retained child.
pub(crate) fn seal_sources(
    i: Inputs<'_>,
    originals: &[OriginalSource],
    provider: Option<&str>,
) -> Result<SealedSources, Failure> {
    let q = qualify(i)?;
    if originals.is_empty() {
        return Err(unavailable(
            "source",
            "Original native source evidence is missing",
        ));
    }
    let mut originals = originals.to_vec();
    originals.sort_by(|a, b| a.source_ref.cmp(&b.source_ref));
    let basis = reconstruct_basis(i, &q, &originals)?;
    let context = detached(i, &q, &basis, provider)?;
    Ok(SealedSources {
        originals,
        authorities: q.authorities().to_vec(),
        basis,
        context,
    })
}
fn replay_sources(
    i: Inputs<'_>,
    s: &SealedSources,
) -> Result<(Qualification, BTreeMap<String, Json>), Failure> {
    let q = qualify(i)?;
    let basis = reconstruct_basis(i, &q, &s.originals)?;
    let context = detached(i, &q, &basis, Some(CONTEXT))?;
    if q.authorities() != s.authorities || basis != s.basis || context != s.context {
        return Err(rejected(
            "sealed_source",
            "Source, identity, authority, basis or context differs from original evidence",
        ));
    }
    let values = basis
        .artifacts
        .iter()
        .map(|a| {
            source::decode_and_validate_candidate(a)
                .map(|v| (a.source_ref.clone(), v))
                .map_err(|e| rejected(&a.source_ref, e))
        })
        .collect::<Result<_, _>>()?;
    Ok((q, values))
}

/// Independently checked source occurrences, with no recipe execution and no
/// caller-supplied qualification token. Consumers must invoke this themselves.
pub(crate) fn qualified_occurrences(
    i: Inputs<'_>, s: Option<&SealedSources>, selected: &[Selection],
) -> Result<(Qualification, Vec<Unit>, Vec<Unit>, String), Vec<Finding>> {
    let (q, prepared) = prepare(i, s, selected)?;
    // This source handoff is for consumers of all three representation facts.
    // Qualify the existing timestamp domain without executing a representation
    // or trusting a failed producer receipt. Valid out-of-range UUIDs are not
    // malformed canonical identities.
    for p in &prepared {
        if uuid_ms(text(&p.unit.value, "id"))? > 253402300799999 {
            return Err(unavailable("created_at", "Valid UUID timestamp exceeds four-digit-year representation"));
        }
    }
    let s = s.unwrap(); // prepare proved the original source anchor exists.
    let decoded = s.basis.artifacts.iter().map(|a| {
        source::decode_and_validate_candidate(a)
            .map(|v| (a.source_ref.clone(), v)).map_err(|e| rejected(&a.source_ref, e))
    }).collect::<Result<BTreeMap<_, _>, _>>()?;
    let all = units(&q, s, &decoded)?;
    let mut selected: Vec<_> = prepared.into_iter().map(|p| p.unit).collect();
    selected.sort_by(|a,b| text(&a.value, "id").cmp(text(&b.value, "id")));
    Ok((q, all, selected, s.basis.basis_digest.clone()))
}

#[derive(Clone)]
pub(crate) struct Unit {
    pub(crate) selection: Selection,
    pub(crate) value: Json,
    pub(crate) row: Json,
    // Declaring ADR, retained independently of the immediate semantic parent.
    pub(crate) owner: Option<(String, String, String)>,
    pub(crate) parent: Option<Occurrence>,
}
fn escape(s: &str) -> String {
    s.replace('~', "~0").replace('/', "~1")
}
// Locate source occurrences through actual qualified schema references. This
// does not validate schemas itself: full preflight/validation already ran.
fn units(
    q: &Qualification,
    s: &SealedSources,
    decoded: &BTreeMap<String, Json>,
) -> Result<Vec<Unit>, Failure> {
    fn walk(
        q: &Qualification,
        map: &BTreeMap<String, Json>,
        key: &str,
        sp: &str,
        value: &Json,
        location: &str,
        pattern: &str,
        source_ref: &str,
        declaring: Option<(&str, &str)>,
        nearest: Option<Occurrence>,
        seen: &mut BTreeSet<(String, String, String)>,
        out: &mut Vec<Unit>,
    ) -> Result<(), Failure> {
        if !seen.insert((key.into(), sp.into(), location.into())) {
            return Ok(());
        }
        let mut nearest = nearest;
        let node = pointer(&map[key], sp)
            .ok_or_else(|| unavailable(key, "Source schema occurrence unavailable"))?;
        if let Ok(row) = type_row(q, key, sp) {
            if matches!(
                text(row, "output_branch"),
                "regular" | "normative-proposition" | "canonical-relationship"
            ) {
                let selection = Selection {
                    source_ref: source_ref.into(),
                    pointer: location.into(),
                    semantic_type: text(row, "semantic_type").into(),
                };
                if let Some(previous) = out.iter().find(|u| {
                    u.selection.source_ref == source_ref && u.selection.pointer == location
                }) {
                    if previous.selection != selection || previous.value != *value {
                        return Err(rejected(
                            location,
                            "Competing schema identities for one source occurrence",
                        ));
                    }
                } else {
                    out.push(Unit {
                        selection: selection.clone(),
                        parent: nearest.clone(),
                        value: value.clone(),
                        row: row.clone(),
                        owner: if location.is_empty() {
                            None
                        } else {
                            declaring.map(|(t, id)| (t.into(), id.into(), pattern.into()))
                        },
                    });
                }
                nearest = Some(Occurrence {
                    selection,
                    id: text(value, "id").into(),
                });
            }
        }
        if let Some(r) = node.get("$ref").and_then(Json::as_str) {
            let (target, _) =
                schema::resolve_reference(map, key, r).map_err(|e| unavailable(key, e.message))?;
            let p = r.split_once('#').map(|(_, p)| p).unwrap_or("");
            walk(
                q,
                map,
                &target,
                p,
                value,
                location,
                pattern,
                source_ref,
                declaring,
                nearest.clone(),
                seen,
                out,
            )?;
        }
        for (name, _) in field(node, "/properties").as_object().into_iter().flatten() {
            if let Some(child) = value.get(name) {
                let name = escape(name);
                walk(
                    q,
                    map,
                    key,
                    &format!("{sp}/properties/{name}"),
                    child,
                    &format!("{location}/{name}"),
                    &format!("{pattern}/{name}"),
                    source_ref,
                    declaring,
                    nearest.clone(),
                    seen,
                    out,
                )?;
            }
        }
        if let Some(values) = value.as_array() {
            if node.get("items").and_then(Json::as_object).is_some() {
                for (n, child) in values.iter().enumerate() {
                    walk(
                        q,
                        map,
                        key,
                        &format!("{sp}/items"),
                        child,
                        &format!("{location}/{n}"),
                        &format!("{pattern}/*"),
                        source_ref,
                        declaring,
                        nearest.clone(),
                        seen,
                        out,
                    )?;
                }
            }
        }
        for branch in ["allOf", "oneOf", "anyOf"] {
            for (n, _) in array(node, branch).iter().enumerate() {
                let child = format!("{sp}/{branch}/{n}");
                if branch == "allOf" || schema::validate_fragment(map, key, &child, value).is_ok() {
                    walk(
                        q,
                        map,
                        key,
                        &child,
                        value,
                        location,
                        pattern,
                        source_ref,
                        declaring,
                        nearest.clone(),
                        seen,
                        out,
                    )?;
                }
            }
        }
        Ok(())
    }
    let map = schema_map(q)?;
    let mut out = vec![];
    for artifact in &s.basis.artifacts {
        let root = &decoded[&artifact.source_ref];
        let k = &artifact.source_schema.canonical_resource_key;
        let p = &artifact.source_schema.json_pointer;
        let row = type_row(q, k, p)?;
        let declaring = if artifact.artifact_kind == "authoring_document" {
            Some((text(row, "semantic_type"), text(root, "id")))
        } else {
            None
        };
        walk(
            q,
            &map,
            k,
            p,
            root,
            "",
            "",
            &artifact.source_ref,
            declaring,
            None,
            &mut BTreeSet::new(),
            &mut out,
        )?;
    }
    Ok(out)
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Occurrence {
    pub(crate) selection: Selection,
    pub(crate) id: String,
}
impl Occurrence {
    fn of(u: &Unit) -> Self {
        Self {
            selection: u.selection.clone(),
            id: text(&u.value, "id").into(),
        }
    }
}
/// Private source-containment witness, separate from the closed lifecycle carrier.
/// Production callers reconstruct all occurrences from sealed original bytes.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct NativeOwnership {
    pub(crate) declaring: Occurrence,
    pub(crate) parent: Occurrence,
    pub(crate) child: Occurrence,
    pub(crate) rule: Json,
}
fn ownership_reference<'a>(q: &'a Qualification, r: &Json) -> Result<&'a Json, Failure> {
    let key = text(r, "canonical_resource_key");
    let raw = q
        .resources()
        .get(key)
        .ok_or_else(|| unavailable(key, "Missing ownership schema authority"))?;
    if text(r, "content_digest")
        != format!("sha256:{}", crate::authoring_construction_v12::digest(raw))
    {
        return Err(rejected(
            key,
            "Ownership reference digest does not qualify selected content",
        ));
    }
    pointer(raw, text(r, "schema_pointer"))
        .ok_or_else(|| rejected(key, "Invalid ownership schema selector"))
}
/// Qualifies selected direct-object or one/two-hop array containment, not arbitrary nesting.
/// Source locators locate original objects; selectors establish their UUIDs.
pub(crate) fn native_ownership(
    q: &Qualification,
    all: &[Unit],
    child: &Unit,
) -> Result<NativeOwnership, Failure> {
    let Some((declaring_type, declaring_id, pattern)) = &child.owner else {
        return Err(unavailable(
            "declaring_context",
            "No declaring ADR evidence",
        ));
    };
    let roots: Vec<_> = all
        .iter()
        .filter(|u| {
            u.selection.source_ref == child.selection.source_ref && u.selection.pointer.is_empty()
        })
        .collect();
    let [declaring] = roots.as_slice() else {
        return Err(if roots.is_empty() {
            unavailable("declaring_context", "Missing declaring source")
        } else {
            rejected("declaring_context", "Ambiguous declaring source")
        });
    };
    if declaring.selection.semantic_type != *declaring_type
        || text(&declaring.value, "id") != declaring_id
        || ![
            "adr/logical",
            "adr/physical-system",
            "adr/physical-component",
        ]
        .contains(&declaring_type.as_str())
    {
        return Err(rejected(
            "declaring_context",
            "Established declaring identity/type conflicts with source",
        ));
    }
    let Some(parent_occurrence) = &child.parent else {
        return Err(unavailable(
            "parent_context",
            "No immediate semantic parent evidence",
        ));
    };
    let parents: Vec<_> = all
        .iter()
        .filter(|u| {
            u.selection.source_ref == parent_occurrence.selection.source_ref
                && u.selection.pointer == parent_occurrence.selection.pointer
        })
        .collect();
    let [parent] = parents.as_slice() else {
        return Err(if parents.is_empty() {
            unavailable("parent_context", "Missing immediate parent")
        } else {
            rejected("parent_context", "Ambiguous immediate parent")
        });
    };
    if Occurrence::of(parent) != *parent_occurrence
        || parent.selection.source_ref != child.selection.source_ref
    {
        return Err(rejected(
            "parent_context",
            "Established immediate parent identity conflicts with source",
        ));
    }
    let rows: Vec<_> = array(&q.resources()[OWNERSHIP], "rows")
        .iter()
        .filter(|r| {
            text(r, "declaring_adr_semantic_type") == declaring_type
                && text(r, "child_semantic_type") == child.selection.semantic_type
                && text(r, "source_instance_pattern") == pattern
        })
        .collect();
    let [rule] = rows.as_slice() else {
        return Err(if rows.is_empty() {
            unavailable(OWNERSHIP, "No selected ownership rule for this occurrence")
        } else {
            rejected(OWNERSHIP, "Competing ownership rows")
        });
    };
    if text(rule, "parent_semantic_type") != parent.selection.semantic_type
        || rule.get("source_schema") != declaring.row.get("source_schema")
        || rule.get("parent_schema") != parent.row.get("source_schema")
        || rule.get("child_schema") != child.row.get("source_schema")
        || text(rule, "governing_rule") != "literal_declaring_adr_status"
        || text(rule, "canonical_identity") != "preserve_established_uuidv7"
        || text(rule, "value_destination") != "/lifecycle_stage"
    {
        return Err(rejected(
            OWNERSHIP,
            "Ownership role, schema or governing rule mismatch",
        ));
    }
    let map = schema_map(q)?;
    for (unit, role, selector) in [
        (
            *declaring,
            "source_schema",
            "declaring_adr_identity_selector",
        ),
        (*parent, "parent_schema", "parent_identity_selector"),
        (child, "child_schema", "child_identity_selector"),
    ] {
        let r = field(rule, &format!("/{role}"));
        ownership_reference(q, r)?;
        let key = text(r, "canonical_resource_key");
        let sp = text(r, "schema_pointer");
        validate(&map, key, sp, &unit.value)?;
        let id = pointer(&unit.value, text(rule, selector)).and_then(Json::as_str);
        if id != Some(text(&unit.value, "id"))
            || !id
                .map(crate::authoring_construction_basis_v11::is_uuid_v7)
                .unwrap_or(false)
        {
            return Err(rejected(
                selector,
                "Identity selector does not preserve established canonical UUIDv7",
            ));
        }
    }
    let same_parent = parent.selection == declaring.selection;
    let chain: Vec<&Unit> = if same_parent {
        vec![declaring, child]
    } else {
        vec![declaring, parent, child]
    };
    let ids: BTreeSet<_> = chain.iter().map(|u| text(&u.value, "id")).collect();
    // The selected shared descriptor rule permits coincident source roles.
    // This validates containment only; it cannot select a System producer.
    let shared_roles = same_parent
        && text(rule, "shared_system_descriptor")
            == "reuse_existing_semantic_unit_if_same_canonical_identity";
    if ids.len() != chain.len() && !shared_roles {
        return Err(rejected("id", "Parent/child canonical identity collision"));
    }
    let parts: Vec<_> = pattern.strip_prefix('/').unwrap_or("").split('/').collect();
    let hops = array(rule, "ownership_schema_path");
    let direct = parts.len() == 1
        && !parts[0].is_empty()
        && parts[0] != "*"
        && hops.len() == 1
        && chain.len() == 2;
    if (!direct
        && (parts.len() != 2 * hops.len()
            || parts.chunks(2).any(|p| p[0].is_empty() || p[1] != "*")))
        || hops.len() != chain.len() - 1
        || hops.is_empty()
        || hops.len() > 2
    {
        return Err(unavailable(
            OWNERSHIP,
            "Selected containment shape is not an executable direct-object or one/two-hop array path",
        ));
    }
    for (n, hop) in hops.iter().enumerate() {
        let from = chain[n];
        let to = chain[n + 1];
        let property = parts[if direct { n } else { 2 * n }];
        let item_suffix = if direct { "" } else { "/items" };
        let from_schema = field(&from.row, "/source_schema");
        let to_schema = field(&to.row, "/source_schema");
        ownership_reference(q, hop)?;
        if text(hop, "canonical_resource_key") != text(from_schema, "canonical_resource_key")
            || text(hop, "schema_pointer")
                != format!(
                    "{}/properties/{property}{item_suffix}",
                    text(from_schema, "schema_pointer")
                )
        {
            return Err(rejected(
                OWNERSHIP,
                "Ownership schema hop starts from the wrong semantic parent",
            ));
        }
        let mut key = text(hop, "canonical_resource_key").to_owned();
        let mut sp = text(hop, "schema_pointer").to_owned();
        let mut node = pointer(&map[&key], &sp).unwrap().clone();
        let mut visited = BTreeSet::new();
        while let Some(link) = node.get("$ref").and_then(Json::as_str) {
            if !visited.insert((key.clone(), sp.clone())) {
                return Err(unavailable(OWNERSHIP, "Recursive ownership schema path"));
            }
            sp = link
                .split_once('#')
                .map(|(_, p)| p)
                .unwrap_or("")
                .to_owned();
            (key, node) = schema::resolve_reference(&map, &key, link)
                .map_err(|e| unavailable(OWNERSHIP, e.message))?;
        }
        if key != text(to_schema, "canonical_resource_key")
            || sp != text(to_schema, "schema_pointer")
            || Some(&node) != pointer(&map[&key], text(to_schema, "schema_pointer"))
        {
            return Err(rejected(
                OWNERSHIP,
                "Ownership hop does not select the exact next schema occurrence",
            ));
        }
        if direct {
            if to.selection.source_ref != from.selection.source_ref
                || to.selection.pointer != format!("{}/{property}", from.selection.pointer)
                || !matches!(to.value, Json::Object(_))
                || pointer(&from.value, &format!("/{property}")) != Some(&to.value)
            {
                return Err(rejected(
                    OWNERSHIP,
                    "Original direct-object containment does not preserve the complete child",
                ));
            }
            continue;
        }
        let prefix = format!("{}/{property}/", from.selection.pointer);
        let tail = to.selection.pointer.strip_prefix(&prefix).ok_or_else(|| {
            rejected(
                OWNERSHIP,
                "Child is not under its claimed parent occurrence",
            )
        })?;
        let index = tail
            .parse::<usize>()
            .map_err(|_| rejected(OWNERSHIP, "Invalid child occurrence index"))?;
        if tail != index.to_string()
            || to.selection.source_ref != from.selection.source_ref
            || pointer(&from.value, &format!("/{property}/{index}")) != Some(&to.value)
        {
            return Err(rejected(
                OWNERSHIP,
                "Original source subtree does not preserve the complete child",
            ));
        }
    }
    Ok(NativeOwnership {
        declaring: Occurrence::of(declaring),
        parent: Occurrence::of(parent),
        child: Occurrence::of(child),
        rule: (*rule).clone(),
    })
}

/// Account for actual same-identity descriptor claims in the retained basis.
/// Neither this finite basis nor equal values proves provider-wide completeness
/// or an established unique semantic producer. No election or coalescence occurs.
fn system_claims(q: &Qualification, unit: &Unit, all: &[Unit]) -> Result<(), Failure> {
    let engine = crate::architecture_interpretation_v13::Authority::from_candidate(q)
        .map_err(|e| unavailable(OWNERSHIP, e))?;
    let mut findings = unavailable("shared_identity",
        "Missing independently qualified provider-complete source scope and established unique System unit/producer binding");
    let id = text(&unit.value, "id");
    for other in all.iter().filter(|p| {
        text(&p.value, "id") == id
            && p.selection.semantic_type != unit.selection.semantic_type
            && p.selection.semantic_type != "adr/physical-system"
    }) {
        findings.extend(rejected(
            id,
            format!(
                "Canonical System identity conflicts with {}",
                other.selection.semantic_type
            ),
        ));
    }
    for peer in all.iter().filter(|p| {
        p.selection.semantic_type == unit.selection.semantic_type && text(&p.value, "id") == id
    }) {
        native_ownership(q, all, peer)?;
        for (name, value) in unit.value.as_object().into_iter().flatten() {
            let path = format!("/{}", name.replace('~', "~0").replace('/', "~1"));
            let rule = engine
                .field(&unit.selection.semantic_type, &path)
                .map_err(|e| unavailable(&path, e))?;
            if text(rule, "disposition") != "canonical_field_placement"
                || !matches!(
                    text(rule, "value_semantics"),
                    "exact_identity_value" | "exact_typed_value"
                )
            {
                return Err(unavailable(
                    &path,
                    "No exact canonical field authority for comparing System claims",
                ));
            }
            if peer.value.get(name) != Some(value) {
                findings.extend(rejected(
                    text(rule, "semantic_field_key"),
                    "Same canonical System identity has contradictory authored canonical values",
                ));
            }
        }
    }
    Err(findings)
}

fn applicable(q: &Qualification, u: &Unit, all: &[Unit]) -> Result<(), Failure> {
    let branch = text(&u.row, "output_branch");
    if !matches!(branch, "regular" | "normative-proposition") {
        return Err(unavailable(
            &u.selection.semantic_type,
            "No entity/proposition recipe branch",
        ));
    }
    for dependency in array(&u.row, "context_dependencies") {
        match dependency.as_str().unwrap_or("") {
            "declaring_context" => {
                let Some((_declaring, id, _pattern)) = &u.owner else {
                    return Err(unavailable(
                        "declaring_context",
                        "Native fragment has no qualified declaring source",
                    ));
                };
                if !crate::authoring_construction_basis_v11::is_uuid_v7(id) {
                    return Err(rejected("declaring_context", "Invalid declaring identity"));
                }
                if branch == "regular" {
                    native_ownership(q, all, u)?;
                }
                // Propositions use exact schema containment, never lifecycle inheritance.
            }
            "shared_identity" => system_claims(q, u, all)?,
            other => {
                return Err(unavailable(
                    other,
                    "Instance prerequisite is not implemented by this bounded source handoff",
                ))
            }
        }
    }
    Ok(())
}
#[derive(Clone)]
struct Prepared {
    unit: Unit,
    witness: Vec<Json>,
    namespace: String,
}
fn prepare(
    i: Inputs<'_>,
    s: Option<&SealedSources>,
    selections: &[Selection],
) -> Result<(Qualification, Vec<Prepared>), Failure> {
    let Some(s) = s else {
        let mut findings = qualify(i).err().unwrap_or_default();
        findings.extend(unavailable(
            "source",
            "Original sealed source evidence is missing",
        ));
        return Err(findings);
    };
    let (q, decoded) = replay_sources(i, s)?;
    let all = units(&q, s, &decoded)?;
    let map = schema_map(&q)?;
    let mut findings = vec![];
    let mut prepared = vec![];
    let mut selected = BTreeSet::new();
    if selections.is_empty() {
        findings.extend(unavailable("selection", "No semantic units selected"))
    }
    let mut identities: BTreeMap<&str, Vec<&Unit>> = BTreeMap::new();
    for u in &all {
        let id = text(&u.value, "id");
        if !id.is_empty() {
            identities.entry(id).or_default().push(u)
        }
    }
    for (id, occurrences) in identities {
        let systems: Vec<_> = occurrences
            .iter()
            .copied()
            .filter(|u| u.selection.semantic_type == "entity/system")
            .collect();
        let others: Vec<_> = occurrences
            .iter()
            .copied()
            .filter(|u| u.selection.semantic_type != "entity/system")
            .collect();
        if others.len() > 1 {
            findings.extend(rejected(
                id,
                "Duplicate canonical semantic identities in the source basis",
            ));
        }
        // Unrequested shared descriptors cannot poison independent sibling facts.
        // An ADR and its own descriptor may share source-role identity, without
        // qualifying either role as the unique existing System semantic producer.
        for u in others.iter().filter(|u| selections.contains(&u.selection)) {
            for system in &systems {
                if u.selection.semantic_type != "adr/physical-system" {
                    findings.extend(rejected(
                        id,
                        "Canonical identity conflicts with a System source claim",
                    ));
                } else if system.parent.as_ref().map(|p| &p.selection) != Some(&u.selection)
                    || system.owner.as_ref().map(|o| o.1.as_str()) != Some(id)
                    || native_ownership(&q, &all, system).is_err()
                {
                    findings.extend(unavailable(
                        "shared_identity",
                        "Foreign System claim lacks qualified existing-unit/producer binding",
                    ));
                }
            }
        }
    }
    for selection in selections {
        let checked = (|| {
            let matches: Vec<_> = all
                .iter()
                .filter(|u| {
                    u.selection.source_ref == selection.source_ref
                        && u.selection.pointer == selection.pointer
                })
                .collect();
            if matches.len() != 1 {
                return Err(unavailable(
                    &selection.pointer,
                    "No uniquely qualified native semantic occurrence",
                ));
            }
            let u = matches[0];
            if u.selection.semantic_type != selection.semantic_type {
                return Err(rejected(
                    &selection.pointer,
                    "Claimed semantic type differs from the source schema occurrence",
                ));
            }
            applicable(&q, u, &all)?;
            let id = text(&u.value, "id");
            if !selected.insert(id.to_owned()) {
                return Err(rejected(
                    id,
                    "Competing selected producers for one canonical semantic unit",
                ));
            }
            let mut witnesses = vec![];
            reference(i, &q, field(&u.row, "/source_schema"))?;
            for (destination, operation) in [
                ("/alias_ref", "literal_alias_join"),
                ("/uri", "literal_entity_uri"),
                ("/created_at", "uuidv7_unix_milliseconds_to_rfc3339_utc"),
            ] {
                let outputs: Vec<_> = array(&u.row, "outputs")
                    .iter()
                    .filter(|o| text(o, "destination") == destination)
                    .collect();
                if outputs.len() != 1 {
                    return Err(rejected(
                        destination,
                        "Missing or competing output producer definitions",
                    ));
                }
                let o = outputs[0];
                let producer = field(o, "/producer");
                if text(o, "status") != "QUALIFIED"
                    || text(o, "classification") != "representation_only"
                    || text(producer, "kind") != operation
                {
                    return Err(unavailable(
                        destination,
                        "No exact qualified representation producer",
                    ));
                }
                let rule = reference(i, &q, field(producer, "/rule"))?;
                if text(field(producer, "/rule"), "canonical_resource_key") != RECIPES
                    || text(rule, "id") != text(producer, "rule_id")
                    || text(field(rule, "/specification"), "operation") != operation
                    || text(field(rule, "/specification"), "destination") != destination
                    || rule
                        .get("independent_semantic_owner")
                        .and_then(Json::as_bool)
                        != Some(false)
                {
                    return Err(rejected(
                        destination,
                        "Rule identity/operation/destination/ownership mismatch",
                    ));
                }
                for r in array(producer, "inputs") {
                    reference(i, &q, r)?;
                }
                reference(i, &q, field(o, "/destination_schema"))?;
                let ds = field(o, "/destination_schema");
                schema::preflight_fragment(
                    &map,
                    text(ds, "canonical_resource_key"),
                    text(ds, "schema_pointer"),
                )
                .map_err(|e| unavailable(destination, e.message))?;
                witnesses.push(o.clone());
            }
            if ["id", "alias_id", "alias_name"]
                .iter()
                .any(|k| u.value.get(k).and_then(Json::as_str).is_none())
            {
                return Err(unavailable(
                    id,
                    "Exact original authored string inputs missing",
                ));
            }
            Ok(Prepared {
                unit: u.clone(),
                witness: witnesses,
                namespace: text(&s.context, "architecture_namespace").into(),
            })
        })();
        match checked {
            Ok(p) => prepared.push(p),
            Err(mut e) => findings.append(&mut e),
        }
    }
    if !findings.is_empty() {
        return Err(findings);
    }
    prepared.sort_by(|a, b| text(&a.unit.value, "id").cmp(text(&b.unit.value, "id")));
    Ok((q, prepared))
}
fn uuid_ms(id: &str) -> Result<u64, Failure> {
    if !crate::authoring_construction_basis_v11::is_uuid_v7(id) {
        return Err(rejected("id", "Malformed or noncanonical UUIDv7"));
    }
    u64::from_str_radix(&format!("{}{}", &id[..8], &id[9..13]), 16)
        .map_err(|_| rejected("id", "Invalid UUID timestamp"))
}
fn created_at(id: &str) -> Result<String, Failure> {
    let ms = uuid_ms(id)?;
    if ms > 253402300799999 {
        return Err(unavailable(
            "created_at",
            "Valid UUID timestamp exceeds the four-digit-year representation",
        ));
    }
    // Integer civil-from-days (400-year Gregorian eras), not a host clock/date API.
    let z = (ms / 86400000) as i64 + 719468;
    let era = z / 146097;
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let mut y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = mp + if mp < 10 { 3 } else { -9 };
    y += i64::from(m <= 2);
    let seconds = ms / 1000;
    Ok(format!(
        "{y:04}-{m:02}-{d:02}T{:02}:{:02}:{:02}.{:03}Z",
        seconds / 3600 % 24,
        seconds / 60 % 60,
        seconds % 60,
        ms % 1000
    ))
}
fn skeleton(p: &Prepared) -> Representation {
    Representation {
        id: text(&p.unit.value, "id").into(),
        namespace: p.namespace.clone(),
        semantic_type: p.unit.selection.semantic_type.clone(),
        branch: text(&p.unit.row, "output_branch").into(),
        source_ref: p.unit.selection.source_ref.clone(),
        source_pointer: p.unit.selection.pointer.clone(),
        alias_ref: String::new(),
        uri: String::new(),
        created_at: String::new(),
        rules: p.witness.clone(),
    }
}
fn destination_values(q: &Qualification, p: &Prepared, r: &Representation) -> Result<(), Failure> {
    let map = schema_map(q)?;
    for (w, value) in p.witness.iter().zip([&r.alias_ref, &r.uri, &r.created_at]) {
        let d = field(w, "/destination_schema");
        validate(
            &map,
            text(d, "canonical_resource_key"),
            text(d, "schema_pointer"),
            &Json::String(value.clone()),
        )?;
    }
    Ok(())
}
pub(crate) fn execute(
    i: Inputs<'_>,
    sources: Option<&SealedSources>,
    selections: &[Selection],
) -> Projection {
    let (q, prepared) = match prepare(i, sources, selections) {
        Ok(p) => p,
        Err(e) => return Projection::failure(e),
    };
    let mut values = vec![];
    let mut findings = vec![];
    for p in prepared {
        let mut r = skeleton(&p);
        r.alias_ref = format!(
            "{}:{}",
            text(&p.unit.value, "alias_id"),
            text(&p.unit.value, "alias_name")
        );
        r.uri = format!("adr://{}/entities/{}", p.namespace, r.id);
        match created_at(&r.id).and_then(|time| {
            r.created_at = time;
            destination_values(&q, &p, &r)
        }) {
            Ok(()) => values.push(r),
            Err(mut e) => findings.append(&mut e),
        }
    }
    if !findings.is_empty() {
        return Projection::failure(findings);
    }
    Projection {
        status: Status::Executed,
        findings,
        values,
        authorities: q.authorities().to_vec(),
        basis_digest: sources.unwrap().basis.basis_digest.clone(),
    }
}
fn leap(y: u64) -> bool {
    y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)
}
/// Independent inverse: validate exact RFC3339 spelling, then Gregorian date ->
/// Unix milliseconds. Does not call the producer's civil-from-days conversion.
fn verify_time(id: &str, time: &str) -> bool {
    let b = time.as_bytes();
    if b.len() != 24
        || [
            (4, b'-'),
            (7, b'-'),
            (10, b'T'),
            (13, b':'),
            (16, b':'),
            (19, b'.'),
            (23, b'Z'),
        ]
        .iter()
        .any(|(i, c)| b[*i] != *c)
    {
        return false;
    }
    let number = |start, end| {
        std::str::from_utf8(&b[start..end])
            .ok()
            .filter(|s| s.bytes().all(|c| c.is_ascii_digit()))
            .and_then(|s| s.parse::<u64>().ok())
    };
    let (Some(y), Some(m), Some(d), Some(h), Some(min), Some(sec), Some(f)) = (
        number(0, 4),
        number(5, 7),
        number(8, 10),
        number(11, 13),
        number(14, 16),
        number(17, 19),
        number(20, 23),
    ) else {
        return false;
    };
    if !(1970..=9999).contains(&y) || !(1..=12).contains(&m) || h > 23 || min > 59 || sec > 59 {
        return false;
    }
    let months = [
        31,
        if leap(y) { 29 } else { 28 },
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ];
    if d == 0 || d > months[m as usize - 1] {
        return false;
    }
    let before = |year: u64| year / 4 - year / 100 + year / 400;
    let days = 365 * (y - 1970) + before(y - 1) - before(1969)
        + months[..m as usize - 1].iter().sum::<u64>()
        + d
        - 1;
    let timestamp = (((days * 24 + h) * 60 + min) * 60 + sec) * 1000 + f;
    // Independently decode the twelve timestamp hex digits as a byte stream.
    if !crate::authoring_construction_basis_v11::is_uuid_v7(id) {
        return false;
    }
    let mut original = 0u64;
    for c in id.bytes().take(13).filter(|c| *c != b'-') {
        let n = if c <= b'9' { c - b'0' } else { c - b'a' + 10 };
        original = (original << 4) | u64::from(n);
    }
    original == timestamp
}
pub(crate) fn verify(
    i: Inputs<'_>,
    sources: Option<&SealedSources>,
    selections: &[Selection],
    supplied: &Projection,
) -> Projection {
    // No invocation of execute, no success flag/digest/receipt as source proof.
    let (q, prepared) = match prepare(i, sources, selections) {
        Ok(p) => p,
        Err(e) => return Projection::failure(e),
    };
    if supplied.status == Status::Unavailable && supplied.values.is_empty() {
        // A failed producer result proves nothing. Re-established source facts
        // can still independently explain unavailable output, never success.
        let mut findings = vec![];
        for p in &prepared {
            match uuid_ms(text(&p.unit.value, "id")) {
                Ok(ms) if ms > 253402300799999 => findings.extend(unavailable(
                    "created_at",
                    "Valid UUID timestamp exceeds four-digit-year representation",
                )),
                Err(mut e) => findings.append(&mut e),
                _ => {}
            }
        }
        if findings.is_empty() {
            findings.extend(unavailable(
                "representation",
                "No executed representation values supplied",
            ))
        }
        return Projection::failure(findings);
    }
    let mut findings = vec![];
    if supplied.status != Status::Executed
        || !supplied.findings.is_empty()
        || supplied.authorities != q.authorities()
        || supplied.basis_digest != sources.unwrap().basis.basis_digest
        || supplied.values.len() != prepared.len()
    {
        findings.extend(rejected(
            "projection",
            "Forged, incomplete or stale representation envelope",
        ))
    }
    for (p, r) in prepared.iter().zip(&supplied.values) {
        let mut original = skeleton(p);
        original.alias_ref = r.alias_ref.clone();
        original.uri = r.uri.clone();
        original.created_at = r.created_at.clone();
        if &original != r {
            findings.extend(rejected(
                &r.id,
                "Source identity, occurrence, namespace, branch or rule evidence changed",
            ))
        }
        let alias = text(&p.unit.value, "alias_id")
            .bytes()
            .chain([b':'])
            .chain(text(&p.unit.value, "alias_name").bytes());
        if !alias.eq(r.alias_ref.bytes()) {
            findings.extend(rejected(
                "alias_ref",
                "Exact original authored aliases do not reconstruct this output",
            ))
        }
        let uri = b"adr://"
            .iter()
            .copied()
            .chain(p.namespace.bytes())
            .chain(b"/entities/".iter().copied())
            .chain(text(&p.unit.value, "id").bytes());
        if !uri.eq(r.uri.bytes()) {
            findings.extend(rejected(
                "uri",
                "Qualified context and established identity do not reconstruct this output",
            ))
        }
        let ms = match uuid_ms(text(&p.unit.value, "id")) {
            Ok(ms) => ms,
            Err(mut e) => {
                findings.append(&mut e);
                continue;
            }
        };
        if ms > 253402300799999 {
            findings.extend(unavailable(
                "created_at",
                "Valid UUID timestamp exceeds four-digit-year representation",
            ))
        } else if !verify_time(text(&p.unit.value, "id"), &r.created_at) {
            findings.extend(rejected(
                "created_at",
                "Independent inverse calendar check does not match UUID milliseconds",
            ))
        }
        if let Err(mut e) = destination_values(&q, p, r) {
            findings.append(&mut e)
        }
    }
    if !findings.is_empty() {
        return Projection::failure(findings);
    }
    Projection {
        status: Status::Verified,
        findings,
        values: supplied.values.clone(),
        authorities: q.authorities().to_vec(),
        basis_digest: sources.unwrap().basis.basis_digest.clone(),
    }
}

#[cfg(test)]
#[path = "identity_representation_tests.rs"]
pub(crate) mod tests;
