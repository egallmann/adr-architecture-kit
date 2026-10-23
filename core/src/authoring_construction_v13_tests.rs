//! Property tests, not claims that complete ACC13 construction executes.
use super::*;
use crate::authoring_construction_orchestration::EntropyUuidV7Minter;
use serde_json::{json, Value};
use std::{fs, path::PathBuf, sync::OnceLock};

fn read(path: &str) -> Value {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_owned();
    serde_json::from_slice(&fs::read(root.join(path)).unwrap()).unwrap()
}
fn j(v: &Value) -> Json {
    serde_json::from_value(v.clone()).unwrap()
}
fn value(v: &Json) -> Value {
    serde_json::to_value(v).unwrap()
}
pub(crate) fn bundle() -> &'static (Json, Vec<Json>, Json) {
    static BUNDLE: OnceLock<(Json, Vec<Json>, Json)> = OnceLock::new();
    BUNDLE.get_or_init(|| {
        let d = read("contracts/authoring-construction/v1.3/contract.json");
        let resources = d["resourceManifest"].as_array().unwrap().iter().map(|m| {
            let key = m["canonicalResourceKey"].as_str().unwrap();
            let filename = key.replace("architecture-interpretation/1.0/source-", "architecture-interpretation/source-").replace('/', "-");
            j(&json!({"canonicalResourceKey":key,"content":read(&format!("contracts/semantic-contract/v1.0/resources/{filename}.json"))}))
        }).collect();
        (j(&d), resources, j(&read("contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json")))
    })
}
fn qualification(family: &str, version: &str, prefix: &str) -> Value {
    let resources: Vec<_> = array(&bundle().0,"resourceManifest").iter().filter(|m|text(m,"canonicalResourceKey").starts_with(prefix)).map(|m|json!({"canonical_resource_key":text(m,"canonicalResourceKey"),"content_digest":text(m,"contentDigest")})).collect();
    let mut result = json!({"family":family,"version":version,"resources":resources});
    if family == "normalized-model" && version == "2.5" {
        result["semantic_contract_fingerprint"] = json!(PROFILE.expected().nm_scf);
    }
    result
}
pub(crate) fn request(case: usize) -> Value {
    let input = read("contracts/authoring-construction/v1.3/resources/conformance.json")["cases"]
        [case - 1]["fixture"]["input"]
        .clone();
    let mut fragments = input["fragments"].clone();
    for f in fragments.as_array_mut().unwrap() {
        f["semantic_kind"] = json!(f["semantic_type"]
            .as_str()
            .unwrap()
            .split('/')
            .next()
            .unwrap());
        f["contract_qualification"] = qualification("authoring", "1.7", "authoring/1.7/schema/");
        f["references"] = json!([]);
    }
    let schema = read("contracts/authoring-construction/v1.1/schema.json");
    let identity: serde_json::Map<String, Value> = schema["$defs"]["identity_establishment_policy"]
        ["properties"]
        .as_object()
        .unwrap()
        .iter()
        .map(|(k, v)| (k.clone(), v["const"].clone()))
        .collect();
    let sealed = manifest_resources(&bundle().0, &bundle().1);
    let members:Vec<_>=array(&sealed[PROFILE.expected().ai_contract],"resourceManifest").iter().map(|m|json!({"canonical_resource_key":text(m,"canonicalResourceKey"),"content_digest":text(m,"contentDigest")})).collect();
    json!({"contract_family":"authoring_construction","contract_version":"1.3","operation":"construct_authoring_set",
        "request":{"request_id":"seal-test","fragments":fragments,"compositions":input["compositions"],"relationships":[]},
        "basis":{
            "acc":{"family":"authoring-construction","version":"1.3","semantic_contract_fingerprint":PROFILE.expected().acc_scf},
            "adc":qualification("authoring-domain","1.1","authoring-domain/1.1/"),
            "authoring":qualification("authoring","1.7","authoring/1.7/schema/"),
            "normalized_model":qualification("normalized-model","2.5","normalized-model/2.5/"),
            "architecture_interpretation":{"family":"architecture-interpretation","version":"1.3","semantic_contract_fingerprint":PROFILE.expected().ai_scf,"authority_closure":{"family":"architecture-interpretation","version":"1.3","resources":members}},
            "custom_entity":null,"reference_basis":{"sealed":true,"entries":[]},"existing_source_basis":{"sealed":true,"entries":[]},"identity_establishment":identity,"provenance":{}}})
}
pub(crate) fn refs(input: &Value) -> BTreeMap<String, String> {
    input["request"]["fragments"]
        .as_array()
        .unwrap()
        .iter()
        .map(|f| {
            let k = f["request_key"].as_str().unwrap();
            (k.into(), format!("opaque:candidate/{k}"))
        })
        .collect()
}
struct NoMint;
impl IdentityMinter for NoMint {
    fn mint_uuidv7(&mut self) -> Result<String, String> {
        panic!("supplied identities and replay must not mint")
    }
}
pub(crate) fn run(input: &Value) -> SealResult {
    prepare(
        &bundle().0,
        &bundle().1,
        &bundle().2,
        &j(input),
        &refs(input),
        &mut NoMint,
    )
}
fn replay(input: &Value, result: &SealResult) -> SealResult {
    verify(
        &bundle().0,
        &bundle().1,
        &bundle().2,
        &j(input),
        &refs(input),
        result,
    )
}
fn passed(r: &SealResult) {
    assert_eq!(r.status, SealStatus::Sealed, "{r:#?}");
    assert_eq!(r.authority, Check::Qualified);
    assert!(r.evidence.is_some() && r.diagnostics.is_empty());
    for key in [
        "complete_nm_2_5_interpretation",
        "expected_and_observed_ledgers",
        "whole_ledger_equivalence",
        "complete_construction_qualification",
    ] {
        assert!(r.outstanding_dependencies.contains(key), "{key}");
    }
    assert!(!r
        .outstanding_dependencies
        .contains("complete_nm_2_4_interpretation"));
}
fn failed(r: &SealResult) {
    assert_ne!(r.status, SealStatus::Sealed, "{r:#?}");
    assert!(r.evidence.is_none() && r.composition_records.is_empty() && r.receipts.is_none());
    assert!(!r.diagnostics.is_empty());
}

#[test]
fn acc13_001_002_source_properties_exact_authority_and_replay() {
    for case in [1, 2] {
        let input = request(case);
        let r = run(&input);
        passed(&r);
        assert_eq!(replay(&input, &r), r);
        let e = r.evidence.as_ref().unwrap();
        assert_eq!(e.retained_artifacts.len(), case + 1);
        assert_eq!(e.basis.artifacts.len(), 1);
        assert_eq!(r.composition_records.len(), case);
        let q = value(&e.context.qualification);
        assert_eq!(q["architecture_interpretation"]["version"], "1.3");
        assert_eq!(q["normalized_model"]["version"], "2.5");
        assert_eq!(
            q["detached_context"]["canonical_resource_key"],
            PROFILE.expected().context
        );
        assert!(e
            .context
            .scope_root
            .ends_with(e.basis.basis_digest.strip_prefix("sha256:").unwrap()));
        assert_eq!(
            e.basis,
            crate::candidate_source::seal_candidate_source_basis(e.basis.artifacts.clone())
                .unwrap()
        );
    }
}

#[test]
fn literal_lifecycle_and_fixed_identities_survive_permutations() {
    for status in ["proposed", "accepted", "deprecated", "superseded"] {
        let mut input = request(2);
        input["request"]["fragments"][0]["fields"]["status"] = json!(status);
        let first = run(&input);
        passed(&first);
        let source = crate::candidate_source::decode_canonical_candidate(
            &first.evidence.as_ref().unwrap().basis.artifacts[0].bytes,
        )
        .unwrap();
        assert_eq!(text(&source, "status"), status);
        input["request"]["fragments"]
            .as_array_mut()
            .unwrap()
            .reverse();
        input["request"]["compositions"]
            .as_array_mut()
            .unwrap()
            .reverse();
        let mut resources = bundle().1.clone();
        resources.reverse();
        let result = prepare(
            &bundle().0,
            &resources,
            &bundle().2,
            &j(&input),
            &refs(&input),
            &mut NoMint,
        );
        passed(&result);
        assert_eq!(result.evidence, first.evidence);
        assert_eq!(result.composition_records, first.composition_records);
        assert_eq!(result.diagnostics, first.diagnostics);
    }
}

#[test]
fn identities_allocate_once_and_replay_has_no_minter() {
    struct Count {
        count: usize,
        inner: EntropyUuidV7Minter,
    }
    impl IdentityMinter for Count {
        fn mint_uuidv7(&mut self) -> Result<String, String> {
            self.count += 1;
            self.inner.mint_uuidv7()
        }
    }
    let mut input = request(2);
    for f in input["request"]["fragments"].as_array_mut().unwrap() {
        f["fields"].as_object_mut().unwrap().remove("id");
    }
    let mut minter = Count {
        count: 0,
        inner: EntropyUuidV7Minter::new(Some(1_767_000_000_123), Some([0x35; 32])),
    };
    let result = prepare(
        &bundle().0,
        &bundle().1,
        &bundle().2,
        &j(&input),
        &refs(&input),
        &mut minter,
    );
    passed(&result);
    assert_eq!(minter.count, 3);
    assert_eq!(replay(&input, &result), result);
    assert_eq!(minter.count, 3);
}

#[test]
fn invalid_or_duplicate_supplied_identity_is_rejected_without_minting() {
    for id in [
        json!("not-a-uuid"),
        json!(null),
        json!("01900000-0000-7000-8000-000000000001"),
    ] {
        let mut input = request(1);
        input["request"]["fragments"][1]["fields"]["id"] = id;
        let result = run(&input);
        failed(&result);
        assert_eq!(result.status, SealStatus::Rejected);
    }
}

#[test]
fn predecessor_selection_never_qualifies() {
    for (member, replacement) in [
        (
            "acc",
            json!({"family":"authoring-construction","version":"1.2","semantic_contract_fingerprint":Profile::Acc12.expected().acc_scf}),
        ),
        (
            "architecture_interpretation",
            json!({"family":"architecture-interpretation","version":"1.2","semantic_contract_fingerprint":Profile::Acc12.expected().ai_scf}),
        ),
        (
            "normalized_model",
            qualification("normalized-model", "2.4", "normalized-model/2.4/schema/"),
        ),
    ] {
        let mut input = request(1);
        input["basis"][member] = replacement;
        failed(&run(&input));
    }
    let input = request(1);
    let historical = j(&read("contracts/authoring-construction/v1.2/contract.json"));
    let bad = prepare(
        &historical,
        &bundle().1,
        &bundle().2,
        &j(&input),
        &refs(&input),
        &mut NoMint,
    );
    failed(&bad);
    assert_eq!(bad.status, SealStatus::Unavailable);
}

#[test]
fn acc13_030_031_authority_mismatch_is_unavailable_and_retains_shape_violations() {
    for field in ["version", "semantic_contract_fingerprint"] {
        let mut input = request(1);
        input["basis"]["acc"][field] = if field == "version" {
            json!("1.2")
        } else {
            json!(format!("scf:v1:sha256:{}", "0".repeat(64)))
        };
        let unavailable = run(&input);
        failed(&unavailable);
        assert_eq!(
            unavailable.status,
            SealStatus::Unavailable,
            "{unavailable:#?}"
        );
        assert!(unavailable
            .diagnostics
            .iter()
            .any(|d| d.code == "semantic_contract.exact_authority_mismatch"));
        input["request"]["fragments"][0]["fields"] = json!("invalid prepared object");
        let rejected = run(&input);
        failed(&rejected);
        assert_eq!(rejected.status, SealStatus::Rejected);
        assert!(rejected
            .diagnostics
            .iter()
            .any(|d| d.status == Status::Unavailable));
    }
}

#[test]
fn missing_tampered_authority_or_definition_fails_closed() {
    let input = request(1);
    for key in [
        PROFILE.expected().table,
        PROFILE.expected().table_schema,
        PROFILE.expected().ai_contract,
        OWNERSHIP,
        OWNERSHIP_SCHEMA,
        PROFILE.expected().context,
        "normalized-model/2.5/schema/normalized-entity.schema",
        "authoring/1.7/schema/adr-common.schema",
    ] {
        for missing in [false, true] {
            let mut resources = bundle().1.clone();
            let i = resources
                .iter()
                .position(|r| text(r, "canonicalResourceKey") == key)
                .unwrap();
            if missing {
                resources.remove(i);
            } else {
                let mut v = value(&resources[i]);
                v["content"] = json!({"forged":true});
                resources[i] = j(&v);
            }
            let bad = prepare(
                &bundle().0,
                &resources,
                &bundle().2,
                &j(&input),
                &refs(&input),
                &mut NoMint,
            );
            failed(&bad);
            assert_eq!(bad.status, SealStatus::Unavailable);
        }
    }
    for field in ["semanticContractFingerprint", "semanticContractVersion"] {
        let mut d = value(&bundle().0);
        d[field] = json!("forged");
        failed(&prepare(
            &j(&d),
            &bundle().1,
            &bundle().2,
            &j(&input),
            &refs(&input),
            &mut NoMint,
        ));
    }
    let mut nm = value(&bundle().2);
    nm["semanticContractFingerprint"] = json!(Profile::Acc12.expected().nm_scf);
    failed(&prepare(
        &bundle().0,
        &bundle().1,
        &j(&nm),
        &j(&input),
        &refs(&input),
        &mut NoMint,
    ));
}

#[test]
fn ownership_and_schema_dialect_are_independently_qualified() {
    let mut sealed = manifest_resources(&bundle().0, &bundle().1);
    let row = array(&sealed[PROFILE.expected().table], "rows")[0].clone();
    assert!(qualify_ownership(&bundle().0, &sealed, &row));
    for (field, v) in [
        ("rule_id", json!("other")),
        ("content_digest", json!("sha256:00")),
        ("version", json!("1.2")),
    ] {
        let mut bad = value(&row);
        bad["ai_ownership_authority"][field] = v;
        assert!(!qualify_ownership(&bundle().0, &sealed, &j(&bad)));
    }
    let mut schema = value(&sealed[PROFILE.expected().schema]);
    schema["$schema"] = json!("https://example.invalid/schema");
    sealed.insert(PROFILE.expected().schema.into(), j(&schema));
    assert!(!schema_dialects(&sealed));
}

#[test]
fn forged_seal_proofs_and_changed_request_release_no_evidence() {
    let input = request(1);
    let good = run(&input);
    passed(&good);
    for variant in 0..12 {
        let mut bad = good.clone();
        match variant {
            0 => bad.receipts = None,
            1 => bad.authority = Check::Unavailable,
            2 => bad.evidence.as_mut().unwrap().basis.basis_digest = "sha256:00".into(),
            3 => bad.evidence.as_mut().unwrap().context.scope_root = "repository:path".into(),
            4 => {
                bad.evidence.as_mut().unwrap().context.roots[0].canonical_uuid =
                    "01900000-0000-7000-8000-000000000099".into()
            }
            5 => {
                bad.evidence.as_mut().unwrap().context.roots[0]
                    .output
                    .artifact_path = "other".into()
            }
            6 => bad
                .receipts
                .as_mut()
                .unwrap()
                .roots
                .selected_root_source_refs
                .push("other".into()),
            7 => bad.receipts.as_mut().unwrap().records.records.clear(),
            8 => {
                bad.receipts
                    .as_mut()
                    .unwrap()
                    .dependencies
                    .relationships_explicitly_empty = false
            }
            9 => bad.composition_records.clear(),
            10 => {
                bad.evidence.as_mut().unwrap().retained_artifacts.pop();
            }
            _ => {
                bad.receipts
                    .as_mut()
                    .unwrap()
                    .insertion
                    .materials
                    .get_mut("child")
                    .unwrap()
                    .identity = "01900000-0000-7000-8000-000000000099".into()
            }
        }
        let checked = replay(&input, &bad);
        failed(&checked);
        assert_eq!(checked.status, SealStatus::Rejected, "variant {variant}");
    }
    let mut changed = input.clone();
    changed["request"]["fragments"][1]["fields"]["summary"] = json!("rewritten");
    failed(&replay(&changed, &good));
    let mut source_refs = refs(&input);
    source_refs.insert("child".into(), "different".into());
    failed(&verify(
        &bundle().0,
        &bundle().1,
        &bundle().2,
        &j(&input),
        &source_refs,
        &good,
    ));
}

#[test]
fn mixed_diagnostics_and_unsupported_standalone() {
    let mut input = request(2);
    input["request"]["compositions"][0]["relation"] = json!("unknown");
    input["request"]["compositions"][1]["child"] = json!("absent");
    let first = run(&input);
    failed(&first);
    assert_eq!(first.status, SealStatus::Rejected);
    assert!(first
        .diagnostics
        .iter()
        .any(|d| d.status == Status::Unresolved));
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    assert_eq!(run(&input).diagnostics, first.diagnostics);
    let mut standalone = request(1);
    standalone["request"]["compositions"] = json!([]);
    let bad = run(&standalone);
    failed(&bad);
    assert_eq!(bad.status, SealStatus::Unavailable);
}

#[test]
fn rewritten_sources_with_new_digests_cannot_replace_request_commitments() {
    use sha2::{Digest, Sha256};
    let input = request(1);
    let mut bad = run(&input);
    passed(&bad);
    let receipt = bad.receipts.as_mut().unwrap();
    for (key, material) in &mut receipt.insertion.materials {
        let mut decoded =
            value(&crate::candidate_source::decode_canonical_candidate(&material.bytes).unwrap());
        if key == "parent" {
            decoded["decisions"][0]["summary"] = json!("replaced");
        } else {
            decoded["summary"] = json!("replaced");
        }
        material.bytes =
            crate::candidate_source::render_source(&material.selector, &j(&decoded)).unwrap();
    }
    for artifact in &mut receipt.roots.artifacts {
        artifact.bytes = receipt.insertion.materials[&artifact.request_key]
            .bytes
            .clone();
        artifact.content_digest = format!("sha256:{:x}", Sha256::digest(&artifact.bytes));
    }
    let e = bad.evidence.as_mut().unwrap();
    e.retained_artifacts = receipt.roots.artifacts.clone();
    e.basis = crate::candidate_source::seal_candidate_source_basis(
        receipt
            .roots
            .artifacts
            .iter()
            .filter(|a| a.request_key == "parent")
            .cloned()
            .collect(),
    )
    .unwrap();
    failed(&replay(&input, &bad));
}

#[test]
fn cross_version_receipts_are_rejected_by_both_producer_profiles() {
    let input = request(1);
    let good = run(&input);
    passed(&good);
    let receipts = good.receipts.as_ref().unwrap();
    assert!(insertion::recheck_preservation(
        Profile::Acc12,
        &bundle().0,
        &bundle().1,
        &receipts.insertion
    )
    .is_err());
    assert_eq!(
        sealing::prepare(
            &bundle().0,
            &bundle().1,
            &receipts.insertion,
            &receipts.roots,
            &receipts.dependencies,
            &receipts.records
        )
        .status,
        sealing::SealingStatus::Rejected
    );
}

#[test]
fn duplicate_source_refs_and_pending_relationships_are_not_sealable() {
    let input = request(1);
    let mut source_refs = refs(&input);
    source_refs.insert("child".into(), source_refs["parent"].clone());
    let bad = prepare(
        &bundle().0,
        &bundle().1,
        &bundle().2,
        &j(&input),
        &source_refs,
        &mut NoMint,
    );
    failed(&bad);
    assert_eq!(bad.status, SealStatus::Rejected);
    let mut pending = input.clone();
    pending["request"]["relationships"] = json!([{"relationship_key":"calls","relationship_type":"relationship/calls","source":{"kind":"request","target":"parent"},"target":{"kind":"request","target":"child"},"fields":{},"qualification":input["basis"]["authoring"]}]);
    let bad = run(&pending);
    failed(&bad);
    assert_eq!(bad.status, SealStatus::Unavailable);
}

#[test]
fn multiple_independent_parent_roots_and_request_local_references() {
    let mut input = request(1);
    let mut parent = input["request"]["fragments"][0].clone();
    parent["request_key"] = json!("parent2");
    parent["fields"]["id"] = json!("01900000-0000-7000-8000-000000000003");
    let mut child = input["request"]["fragments"][1].clone();
    child["request_key"] = json!("child2");
    child["fields"]["id"] = json!("01900000-0000-7000-8000-000000000004");
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .extend([parent, child]);
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .push(json!({"parent":"parent2","child":"child2","relation":"contains","ordering":10}));
    input["request"]["fragments"][0]["references"] = json!([{"reference_key":"other","reference_kind":"request","target":"child2","expected_semantic_type":"entity/decision"}]);
    let first = run(&input);
    passed(&first);
    assert_eq!(first.evidence.as_ref().unwrap().retained_artifacts.len(), 4);
    assert_eq!(first.evidence.as_ref().unwrap().basis.artifacts.len(), 2);
    assert_eq!(replay(&input, &first), first);
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    let second = run(&input);
    passed(&second);
    assert_eq!(second.evidence, first.evidence);
    assert_eq!(second.composition_records, first.composition_records);
}

#[test]
fn sealed_existing_references_and_unresolved_vs_unavailable_dependencies() {
    let mut input = request(1);
    input["basis"]["reference_basis"]["entries"] = json!([{"reference_id":"external","canonical_uuid":"01900000-0000-7000-8000-000000000099","semantic_kind":"entity","semantic_type":"entity/decision","qualification":input["basis"]["authoring"],"existence_state":"active"}]);
    input["request"]["fragments"][0]["references"] = json!([{"reference_key":"external","reference_kind":"existing","target":"external","expected_semantic_type":"entity/decision"}]);
    let good = run(&input);
    passed(&good);
    assert_eq!(replay(&input, &good), good);
    let mut missing = input.clone();
    missing["request"]["fragments"][0]["references"][0]["target"] = json!("absent");
    let unresolved = run(&missing);
    failed(&unresolved);
    assert_eq!(unresolved.status, SealStatus::Unresolved);
    input["basis"]["reference_basis"]["entries"][0]["existence_state"] = json!("retired");
    let unavailable = run(&input);
    failed(&unavailable);
    assert_eq!(
        unavailable.status,
        SealStatus::Unavailable,
        "{unavailable:#?}"
    );
}
