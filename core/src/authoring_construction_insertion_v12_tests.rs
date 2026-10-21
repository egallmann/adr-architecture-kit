use super::super::tests::{bundle, fixture, j, request};
use super::*;
use crate::authoring_construction_orchestration::EntropyUuidV7Minter;
use serde_json::{json, Value};

struct Minter {
    inner: EntropyUuidV7Minter,
    calls: usize,
}
impl Minter {
    fn new() -> Self {
        Self {
            inner: EntropyUuidV7Minter::new(Some(1_767_000_000_123), Some([0x51; 32])),
            calls: 0,
        }
    }
}
impl IdentityMinter for Minter {
    fn mint_uuidv7(&mut self) -> Result<String, String> {
        self.calls += 1;
        self.inner.mint_uuidv7()
    }
}
fn run(input: &Value, minter: &mut dyn IdentityMinter) -> InsertionResult {
    insert(
        &j(&bundle().0),
        &bundle().1.iter().map(j).collect::<Vec<_>>(),
        &j(input),
        minter,
    )
}
fn decode(result: &InsertionResult, key: &str) -> Value {
    serde_json::to_value(
        candidate_source::decode_canonical_candidate(&result.materials[key].bytes).unwrap(),
    )
    .unwrap()
}
fn passed(result: &InsertionResult) {
    assert_eq!(
        result.status,
        InsertionStatus::PreservationProven,
        "{result:#?}"
    );
    assert!(result.preservation_failures.is_empty());
    for deferred in [
        "exact_subtree_and_minimal_root_accounting",
        "complete_composition_evidence",
        "composed_candidate_basis_sealing",
        "complete_construction_qualification",
    ] {
        assert!(result
            .qualification
            .outstanding_dependencies
            .contains(deferred));
    }
}
fn blocked(result: &InsertionResult, status: InsertionStatus) {
    assert_eq!(result.status, status, "{result:#?}");
    assert!(result.materials.is_empty());
    assert!(result.proofs.is_empty());
}

#[test]
fn acc12_01_02_04_complete_fields_and_retained_native_material() {
    for case in [1, 2, 4] {
        let input = request(&fixture(case));
        let mut minter = Minter::new();
        let result = run(&input, &mut minter);
        passed(&result);
        assert_eq!(minter.calls, 0);
        let mut parent = decode(&result, "parent");
        let embedded = parent.as_object_mut().unwrap().remove("decisions").unwrap();
        assert_eq!(parent, input["request"]["fragments"][0]["fields"]);
        let frozen: Value = serde_json::from_str(include_str!(
            "../../contracts/authoring-construction/v1.2/resources/conformance.json"
        ))
        .unwrap();
        for assertion in frozen["cases"][case - 1]["assertions"].as_array().unwrap() {
            match assertion["path"].as_str().unwrap() {
                "semantic.membership" => assert_eq!(
                    embedded
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|c| c["id"].clone())
                        .collect::<Vec<_>>(),
                    *assertion["expected"].as_array().unwrap()
                ),
                "embedded_child" => assert_eq!(embedded[0], assertion["expected"]),
                _ => {}
            }
        }
        assert_eq!(
            result.materials.len(),
            input["request"]["fragments"].as_array().unwrap().len()
        );
        for proof in &result.proofs {
            let child = &proof.binding.child_request_key;
            let supplied = input["request"]["fragments"]
                .as_array()
                .unwrap()
                .iter()
                .find(|f| f["request_key"] == *child)
                .unwrap();
            assert_eq!(decode(&result, child), supplied["fields"]);
            assert_eq!(result.materials[child].identity_disposition, "preserved");
        }
        assert!(!decode(&result, "child").get("ordering").is_some());
    }
}

#[test]
fn acc12_03_fixed_id_request_permutations_have_identical_bytes_and_proofs() {
    let fixture = fixture(3);
    let left = run(&request(&fixture["left"]), &mut Minter::new());
    let right = run(&request(&fixture["right"]), &mut Minter::new());
    passed(&left);
    passed(&right);
    assert_eq!(left, right);
}

#[test]
fn acc12_05_identity_allocation_once_per_fragment_not_edge() {
    let mut input = request(&fixture(2));
    for f in input["request"]["fragments"].as_array_mut().unwrap() {
        f["fields"].as_object_mut().unwrap().remove("id");
    }
    let original = input.clone();
    let mut minter = Minter::new();
    let result = run(&input, &mut minter);
    passed(&result);
    assert_eq!(input, original);
    assert_eq!(minter.calls, result.materials.len());
    let ids: BTreeSet<_> = result.materials.values().map(|m| &m.identity).collect();
    assert_eq!(ids.len(), result.materials.len());
    for m in result.materials.values() {
        assert!(basis::is_uuid_v7(&m.identity));
        assert_eq!(m.identity_disposition, "minted");
    }
    let fixture = run(&request(&fixture(5)), &mut Minter::new());
    passed(&fixture);
}

#[test]
fn omitted_optional_fields_are_not_manufactured_and_authoring_inventory_is_exact() {
    let mut input = request(&fixture(1));
    let child = input["request"]["fragments"][1]["fields"]
        .as_object_mut()
        .unwrap();
    for optional in [
        "alternatives_considered",
        "consequences",
        "related_invariants",
    ] {
        child.remove(optional);
    }
    let result = run(&input, &mut Minter::new());
    passed(&result);
    assert_eq!(
        decode(&result, "child"),
        input["request"]["fragments"][1]["fields"]
    );
    for (index, field) in [(1, "rationale"), (0, "context")] {
        let mut invalid = input.clone();
        invalid["request"]["fragments"][index]["fields"]
            .as_object_mut()
            .unwrap()
            .remove(field);
        let result = run(&invalid, &mut Minter::new());
        blocked(&result, InsertionStatus::Rejected);
        assert!(result
            .qualification
            .diagnostics
            .iter()
            .any(|d| d.code == "authoring_construction.authoring.invalid"));
    }
    input["request"]["fragments"][1]["fields"]["invented_field"] = json!(true);
    blocked(&run(&input, &mut Minter::new()), InsertionStatus::Rejected);
}

// The proof checker is independently exercised with changed actual serialized
// bytes. No fixture mutation changes the frozen authority or production inputs.
fn mutation(
    input: &Value,
    change: impl FnOnce(&mut BTreeMap<String, Material>),
) -> InsertionResult {
    let good = run(input, &mut Minter::new());
    passed(&good);
    let expected = input["request"]["fragments"]
        .as_array()
        .unwrap()
        .iter()
        .map(|f| {
            (
                f["request_key"].as_str().unwrap().to_owned(),
                j(&f["fields"]),
            )
        })
        .collect();
    let mut material = good.materials;
    change(&mut material);
    finish_proof(good.qualification, &expected, material)
}
fn rewrite(material: &mut BTreeMap<String, Material>, key: &str, change: impl FnOnce(&mut Value)) {
    let m = material.get_mut(key).unwrap();
    let mut source =
        serde_json::to_value(candidate_source::decode_canonical_candidate(&m.bytes).unwrap())
            .unwrap();
    change(&mut source);
    m.bytes = candidate_source::render_source(&m.selector, &j(&source)).unwrap();
}

#[test]
fn acc12_23_24_frozen_mutations_are_rejected() {
    for (case, suffix) in [(23, "child_mutation"), (24, "identity_mutation")] {
        let fixture = fixture(case);
        let result = mutation(&request(&fixture["candidate"]), |materials| {
            rewrite(materials, "parent", |parent| {
                parent["decisions"][0] = fixture["observed_embedded_child"].clone()
            })
        });
        blocked(&result, InsertionStatus::Rejected);
        assert!(result
            .qualification
            .diagnostics
            .iter()
            .any(|d| d.code == format!("authoring_construction.composition.{suffix}")));
    }
}

#[test]
fn exact_subtree_proof_rejects_loss_rewrite_identity_and_parent_mutations() {
    let input = request(&fixture(1));
    for variant in 0..7 {
        let result = mutation(&input, |materials| match variant {
            0 => rewrite(materials, "parent", |p| {
                p["decisions"][0]
                    .as_object_mut()
                    .unwrap()
                    .remove("consequences");
            }),
            1 => rewrite(materials, "parent", |p| {
                p["decisions"][0]["consequences"]["positive"] = json!(["Rewritten"])
            }),
            2 => rewrite(materials, "parent", |p| {
                p["decisions"][0]["id"] = json!("01900000-0000-7000-8000-000000000099")
            }),
            3 => rewrite(materials, "parent", |p| {
                p["title"] = json!("Changed parent")
            }),
            4 => rewrite(materials, "child", |p| {
                p["summary"] = json!("Changed retained child")
            }),
            5 => rewrite(materials, "parent", |p| p["decisions"] = json!([])),
            _ => {
                materials.remove("child");
            }
        });
        blocked(&result, InsertionStatus::Rejected);
        assert!(!result.preservation_failures.is_empty());
    }
}

#[test]
fn unavailable_entropy_and_duplicate_minter_output_fail_closed() {
    let mut input = request(&fixture(1));
    for f in input["request"]["fragments"].as_array_mut().unwrap() {
        f["fields"].as_object_mut().unwrap().remove("id");
    }
    blocked(
        &run(&input, &mut EntropyUuidV7Minter::new(Some(1), None)),
        InsertionStatus::Unavailable,
    );
    struct Repeated(&'static str);
    impl IdentityMinter for Repeated {
        fn mint_uuidv7(&mut self) -> Result<String, String> {
            Ok(self.0.into())
        }
    }
    blocked(
        &run(&input, &mut Repeated("invalid")),
        InsertionStatus::Unavailable,
    );
    blocked(
        &run(
            &input,
            &mut Repeated("01900000-0000-7000-8000-000000000099"),
        ),
        InsertionStatus::Rejected,
    );
}

#[test]
fn structural_failures_preserve_diagnostics_without_allocating_or_mutating() {
    for case in [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20] {
        let input = request(&fixture(case));
        let mut minter = Minter::new();
        let result = run(&input, &mut minter);
        assert_ne!(
            result.status,
            InsertionStatus::PreservationProven,
            "case {case}"
        );
        assert_eq!(minter.calls, 0);
        assert!(result.materials.is_empty());
        let baseline = qualify(
            &j(&bundle().0),
            &bundle().1.iter().map(j).collect::<Vec<_>>(),
            &j(&input),
        );
        assert_eq!(result.qualification, baseline);
    }
}

#[test]
fn independent_schema_and_proof_failures_are_stable_under_permutations() {
    let mut input = request(&fixture(2));
    let failure = |material: &mut BTreeMap<String, Material>| {
        rewrite(material, "parent", |p| {
            for child in p["decisions"].as_array_mut().unwrap() {
                child["id"] = json!("01900000-0000-7000-8000-000000000099");
                child["rationale"] = json!("Rewritten");
            }
            p["context"] = json!("Changed parent");
        });
    };
    let left = mutation(&input, failure);
    blocked(&left, InsertionStatus::Rejected);
    assert_eq!(left.qualification.diagnostics.len(), 4);
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    input["request"]["compositions"]
        .as_array_mut()
        .unwrap()
        .reverse();
    assert_eq!(left, mutation(&input, failure));
    for f in input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .filter(|f| f["semantic_type"] == "entity/decision")
    {
        f["fields"].as_object_mut().unwrap().remove("rationale");
    }
    let left = run(&input, &mut Minter::new());
    blocked(&left, InsertionStatus::Rejected);
    // Both native children and the complete parent independently fail validation.
    assert_eq!(left.qualification.diagnostics.len(), 3);
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .reverse();
    assert_eq!(left, run(&input, &mut Minter::new()));
}

#[test]
fn unsupported_unbound_fragments_and_missing_update_id_allocate_nothing() {
    let mut input = request(&fixture(1));
    let mut unbound = input["request"]["fragments"][1].clone();
    unbound["request_key"] = json!("unbound");
    unbound["fields"].as_object_mut().unwrap().remove("id");
    input["request"]["fragments"]
        .as_array_mut()
        .unwrap()
        .push(unbound);
    let mut minter = Minter::new();
    blocked(&run(&input, &mut minter), InsertionStatus::Unavailable);
    assert_eq!(minter.calls, 0);
    let mut input = request(&fixture(1));
    input["request"]["fragments"][1]["operation"] = json!("update");
    input["request"]["fragments"][1]["fields"]
        .as_object_mut()
        .unwrap()
        .remove("id");
    // The unchanged qualifier blocks update composition before identity work.
    blocked(&run(&input, &mut minter), InsertionStatus::Unavailable);
    assert_eq!(minter.calls, 0);
    passed(&run(
        &request(&fixture(1)),
        &mut EntropyUuidV7Minter::new(None, None),
    ));
}

#[test]
fn malformed_or_wrong_selector_material_and_parent_identity_changes_are_rejected() {
    let input = request(&fixture(1));
    for variant in 0..4 {
        let result = mutation(&input, |material| match variant {
            0 => material.get_mut("child").unwrap().bytes = b"not: [canonical".to_vec(),
            1 => material.get_mut("child").unwrap().selector.json_pointer = String::new(),
            2 => rewrite(material, "parent", |p| {
                p["id"] = json!("01900000-0000-7000-8000-000000000099")
            }),
            _ => rewrite(material, "parent", |p| {
                p["decisions"][0]["enables_capabilities"] = json!([])
            }),
        });
        blocked(&result, InsertionStatus::Rejected);
    }
}
