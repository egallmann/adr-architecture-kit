//! Private current-candidate selection and exact supplied-bundle qualification.
//!
//! Maintained canonical definitions are the build's trust inputs. They are not
//! caller claims or perpetual SCF pins. Publication-semantic qualification of
//! those inputs remains a repository gate; this seam independently authenticates
//! supplied contents and cross-contract selection, never interprets instances.
use crate::{object, semantic_contract, string, Json};
use std::collections::{BTreeMap, BTreeSet};

const TARGETS: [(&str, &str); 3] = [
    ("normalized-model", "2.5"),
    ("architecture-interpretation", "1.5"),
    ("authoring-construction", "1.5"),
];
const CANONICAL: [&str; 3] = [
    include_str!("../../contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json"),
    include_str!("../../contracts/architecture-interpretation/v1.5/contract.json"),
    include_str!("../../contracts/authoring-construction/v1.5/contract.json"),
];

#[derive(Clone, Copy)]
pub(crate) struct Bundle<'a> {
    pub(crate) definition: &'a Json,
    pub(crate) resources: &'a [Json],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum Status {
    Rejected,
    Unavailable,
    AuthorityQualified,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) struct Finding {
    pub(crate) status: Status,
    pub(crate) authority: String,
    pub(crate) key: String,
    pub(crate) code: String,
    pub(crate) detail: String,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Authority {
    pub(crate) family: String,
    pub(crate) version: String,
    pub(crate) fingerprint: String,
    pub(crate) resource_count: usize,
}

/// No fields or constructor are exposed to consumers. Failed qualification
/// releases neither selected authority evidence nor partially trusted resources.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Qualification {
    status: Status,
    findings: Vec<Finding>,
    authorities: Vec<Authority>,
    resources: BTreeMap<String, Json>,
}

impl Qualification {
    pub(crate) fn status(&self) -> Status {
        self.status
    }
    pub(crate) fn findings(&self) -> &[Finding] {
        &self.findings
    }
    pub(crate) fn authorities(&self) -> &[Authority] {
        &self.authorities
    }
    pub(crate) fn resources(&self) -> &BTreeMap<String, Json> {
        &self.resources
    }
    pub(crate) fn complete_interpretation(&self) -> Status {
        Status::Unavailable
    }
    pub(crate) fn instance_applicability(&self) -> &'static str {
        "Unknown"
    }

    fn issue(&mut self, status: Status, authority: &str, key: &str, code: &str, detail: &str) {
        self.findings.push(Finding {
            status,
            authority: authority.into(),
            key: key.into(),
            code: code.into(),
            detail: detail.into(),
        });
    }
    fn finish(mut self) -> Self {
        self.findings.sort();
        self.findings.dedup();
        if let Some(first) = self.findings.first() {
            self.status = first.status;
            self.authorities.clear();
            self.resources.clear();
        }
        self
    }
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
fn at<'a>(value: &'a Json, path: &[&str]) -> &'a Json {
    path.iter()
        .fold(value, |v, k| v.get(k).unwrap_or(&Json::Null))
}
fn verify_definition(definition: &Json) -> Json {
    semantic_contract::fingerprint(&object([
        ("definition".into(), definition.clone()),
        ("mode".into(), string("verify")),
    ]))
}
fn success(result: &Json) -> bool {
    result.get("success").and_then(Json::as_bool) == Some(true)
}
fn equivalent_definition(left: &Json, right: &Json) -> bool {
    let l = verify_definition(left);
    let r = verify_definition(right);
    success(&l)
        && success(&r)
        && l.get("canonical_preimage_json") == r.get("canonical_preimage_json")
}
fn canonical(value: &Json) -> String {
    let mut out = String::new();
    // Used only as an ordering key for deterministic diagnostics. Failure stays
    // visible to the shared verifier; this does not authenticate the value.
    if semantic_contract::canonicalize_value(value, &mut out).is_err() {
        return serde_json::to_string(value).unwrap_or_default();
    }
    out
}

/// The sole production selection factory has no parameters. Supplied profiles,
/// SCFs, packaged mirrors and filesystem paths cannot select trusted authority.
pub(crate) fn qualify(nm: Bundle<'_>, ai: Bundle<'_>, acc: Bundle<'_>) -> Qualification {
    let selected: Result<Vec<Json>, _> =
        CANONICAL.iter().map(|s| serde_json::from_str(s)).collect();
    match selected {
        Ok(selected) => qualify_selected(&selected, [nm, ai, acc]),
        Err(error) => {
            let mut out = empty();
            out.issue(
                Status::Unavailable,
                "canonical",
                "",
                "canonical_input_unavailable",
                &error.to_string(),
            );
            out.finish()
        }
    }
}

fn empty() -> Qualification {
    Qualification {
        status: Status::AuthorityQualified,
        findings: vec![],
        authorities: vec![],
        resources: BTreeMap::new(),
    }
}

// Private implementation detail, not a second caller-selected authority API.
// Unit tests can model a rebuilt, independently qualified maintained revision.
fn qualify_selected(selected: &[Json], supplied: [Bundle<'_>; 3]) -> Qualification {
    let mut out = empty();
    for (index, (family, version)) in TARGETS.iter().enumerate() {
        let expected = &selected[index];
        let bundle = supplied[index];
        let source = verify_definition(expected);
        let source_valid = success(&source)
            && text(expected, "semanticContractFamily") == *family
            && text(expected, "semanticContractVersion") == *version;
        if !source_valid {
            out.issue(
                Status::Unavailable,
                family,
                "definition",
                "canonical_input_invalid",
                "Maintained definition must be independently qualified before use",
            );
        }
        if text(bundle.definition, "semanticContractFamily") != *family
            || text(bundle.definition, "semanticContractVersion") != *version
        {
            out.issue(
                Status::Rejected,
                family,
                "definition",
                "wrong_family_or_version",
                "No predecessor, successor or ambient substitution is permitted",
            );
        }
        if source_valid && !equivalent_definition(expected, bundle.definition) {
            out.issue(
                Status::Rejected,
                family,
                "definition",
                "unselected_definition",
                "Supplied commitment differs from the maintained canonical selection",
            );
        }
        let conformance = Json::Array(vec![string(&format!("{family}/{version}/conformance"))]);
        if expected.get("frozenNormativeConformanceResources") != Some(&conformance) {
            out.issue(
                Status::Unavailable,
                family,
                "conformance",
                "canonical_conformance_invalid",
                "Exactly the selected normative conformance resource is required",
            );
        }
        // Do not filter, deduplicate or fill missing supplied resources. The
        // shared closure verifier checks keys, roles, digests and actual edges.
        let mut resources = bundle.resources.to_vec();
        resources
            .sort_by_cached_key(|r| (text(r, "canonicalResourceKey").to_owned(), canonical(r)));
        let validation = semantic_contract::validate_closure(&object([
            ("definition".into(), bundle.definition.clone()),
            ("resources".into(), Json::Array(resources.clone())),
        ]));
        for diagnostic in array(&validation, "diagnostics") {
            out.issue(
                Status::Rejected,
                family,
                text(diagnostic, "path"),
                text(diagnostic, "code"),
                text(diagnostic, "message"),
            );
        }
        if !success(&validation) && array(&validation, "diagnostics").is_empty() {
            out.issue(
                Status::Rejected,
                family,
                "resources",
                "invalid_closure",
                "Shared closure qualification failed",
            );
        }
        for resource in resources {
            let key = text(&resource, "canonicalResourceKey");
            let supplied_content = resource.get("content").unwrap_or(&Json::Null);
            // Authenticated resources use the same representation as their
            // governed canonical content identity. This is not authored-source
            // normalization and never establishes authority on its own.
            let mut encoded = String::new();
            let normalized = semantic_contract::canonicalize_value(supplied_content, &mut encoded)
                .and_then(|()| serde_json::from_str::<Json>(&encoded).map_err(|e| e.to_string()));
            let content = match normalized {
                Ok(content) => content,
                Err(error) => {
                    out.issue(
                        Status::Rejected,
                        family,
                        key,
                        "invalid_canonical_resource_content",
                        &error,
                    );
                    continue;
                }
            };
            if let Some(previous) = out.resources.get(key) {
                if previous != &content {
                    out.issue(
                        Status::Rejected,
                        family,
                        key,
                        "cross_authority_content_conflict",
                        "One canonical key cannot identify different selected contents",
                    );
                }
            } else {
                out.resources.insert(key.into(), content);
            }
        }
        out.authorities.push(Authority {
            family: (*family).into(),
            version: (*version).into(),
            fingerprint: text(expected, "semanticContractFingerprint").into(),
            resource_count: array(expected, "resourceManifest").len(),
        });
    }
    if out.findings.is_empty() {
        cross_selection(selected, &mut out);
    }
    out.finish()
}

fn cross_selection(selected: &[Json], out: &mut Qualification) {
    let nm_key = "normalized-model/2.5/contract";
    let ai_key = "architecture-interpretation/1.5/contract";
    for (key, definition) in [(nm_key, &selected[0]), (ai_key, &selected[1])] {
        if !out
            .resources
            .get(key)
            .is_some_and(|r| equivalent_definition(r, definition))
        {
            out.issue(
                Status::Rejected,
                "cohort",
                key,
                "wrong_selected_definition",
                "Enclosing resource must select the independently qualified current definition",
            );
        }
    }
    let ai_rules = out
        .resources
        .get("architecture-interpretation/1.5/rules")
        .cloned()
        .unwrap_or(Json::Null);
    let acc_rules = out
        .resources
        .get("authoring-construction/1.5/rules")
        .cloned()
        .unwrap_or(Json::Null);
    let ai_selection = at(&acc_rules, &["authority", "architecture_interpretation"]);
    let nm_selection = at(&acc_rules, &["authority", "normalized_model"]);
    if text(ai_selection, "family") != TARGETS[1].0
        || text(ai_selection, "version") != TARGETS[1].1
        || text(ai_selection, "fingerprint") != text(&selected[1], "semanticContractFingerprint")
        || text(ai_selection, "closure_source") != ai_key
    {
        out.issue(
            Status::Rejected,
            "authoring-construction",
            "authority/architecture_interpretation",
            "wrong_AI_selection",
            "ACC must select this qualified AI definition and closure",
        );
    }
    if text(nm_selection, "family") != TARGETS[0].0
        || text(nm_selection, "version") != TARGETS[0].1
        || text(nm_selection, "fingerprint") != text(&selected[0], "semanticContractFingerprint")
        || text(nm_selection, "schema_family") != "normalized-model/2.5/schema"
    {
        out.issue(
            Status::Rejected,
            "authoring-construction",
            "authority/normalized_model",
            "wrong_NM_selection",
            "ACC must select the same qualified NM authority",
        );
    }
    if text(
        at(&ai_rules, &["destination_authority"]),
        "semantic_contract_fingerprint",
    ) != text(&selected[0], "semanticContractFingerprint")
    {
        out.issue(
            Status::Rejected,
            "architecture-interpretation",
            "destination_authority",
            "wrong_NM_selection",
            "AI must select the qualified NM definition",
        );
    }
    let nm_reference = at(&ai_rules, &["destination_authority", "definition"]);
    let expected_nm_digest = array(&selected[1], "resourceManifest")
        .iter()
        .find(|m| text(m, "canonicalResourceKey") == nm_key)
        .map(|m| text(m, "contentDigest"));
    if text(nm_reference, "canonical_resource_key") != nm_key
        || text(nm_reference, "schema_pointer") != ""
        || expected_nm_digest != Some(text(nm_reference, "content_digest"))
    {
        out.issue(
            Status::Rejected,
            "architecture-interpretation",
            "destination_authority/definition",
            "wrong_NM_resource_selection",
            "NM selection requires its actual resource key and qualified digest",
        );
    }
    // Actual normative identities, not relabeled 1.5 copies. Their contents and
    // digests have already qualified against the maintained exact manifests.
    for key in [
        "architecture-interpretation/1.3/rules",
        "architecture-interpretation/1.3/field-dispositions-1.7-to-2.5",
        "architecture-interpretation/1.3/lifecycle-ownership",
        "architecture-interpretation/1.3/contextual-facts",
        "architecture-interpretation/1.3/detached-context",
        "architecture-interpretation/1.4/required-output-derivations",
        "authoring-construction/1.3/ledger.schema",
    ] {
        if !out.resources.contains_key(key) {
            out.issue(
                Status::Rejected,
                "cohort",
                key,
                "missing_inherited_normative_authority",
                "Inherited rule retains its actual historical identity",
            );
        }
    }
    // An embedded historical definition is provenance, not a request to import
    // its whole manifest. Only the exact current manifests select resources.
    let keys: BTreeSet<_> = selected
        .iter()
        .flat_map(|d| array(d, "resourceManifest"))
        .map(|m| text(m, "canonicalResourceKey").to_owned())
        .collect();
    if out.resources.keys().cloned().collect::<BTreeSet<_>>() != keys {
        out.issue(
            Status::Rejected,
            "cohort",
            "resources",
            "inconsistent_selected_membership",
            "Only the union of independently qualified current closures is selected",
        );
    }
}

#[cfg(test)]
#[path = "candidate_authority_tests.rs"]
mod tests;
