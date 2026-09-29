use serde_json::{json, Value as Json};

fn source_contract(version: &str) -> Json {
    json!({
        "family": "authoring",
        "version": version,
        "schemaResource": {
            "canonicalResourceKey": format!("authoring/{version}/schema/adr-logical.schema"),
            "contentDigest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        },
        "resourceClosure": [
            {"canonicalResourceKey": format!("authoring/{version}/schema/adr-common.schema"), "contentDigest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
            {"canonicalResourceKey": format!("authoring/{version}/schema/types.schema"), "contentDigest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},
            {"canonicalResourceKey": format!("authoring/{version}/schema/adr-logical.schema"), "contentDigest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
        ]
    })
}

fn request(version: &str) -> Json {
    json!({
        "core_contract_version": "1.3",
        "operation": "materialize_architecture",
        "request": {
            "operation": "materialize_architecture",
            "materializationContractVersion": "1.1",
            "semanticContractSetId": "scs:v1:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "authorityProvider": {"kind": "fixture-provider", "architectureNamespace": "example"},
            "sourceBasis": {
                "sealed": true,
                "providerSourceIdentity": "fixture-provider:example",
                "sourceRevision": "revision-1",
                "artifacts": [{
                    "sourceRef": "ADR-L-0001",
                    "artifactPath": "architecture/ADR-L-0001.yaml",
                    "contentDigest": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
                    "sourceContract": source_contract(version),
                    "document": {"schema_version": version, "adr_type": "logical"}
                }]
            },
            "providerProvenance": {"semanticCoreContractVersion": "1.3", "packageVersion": "0.11.1", "hostBinding": "test"},
            "targetOperation": "materialize_architecture",
            "direction": "forward",
            "useMode": "new",
            "profile": {
                "profileFamily": "architecture-materialization",
                "profileVersion": "1.1",
                "profileId": "architecture-materialization@1.1",
                "participatingFamilies": [
                    {"semanticContractFamily": "architecture-interpretation", "semanticContractVersion": "1.1", "cardinality": 1},
                    {"semanticContractFamily": "normalized-model", "semanticContractVersion": "2.4", "cardinality": 1},
                    {"semanticContractFamily": "normative-semantics", "semanticContractVersion": "1.0", "cardinality": 1}
                ],
                "operations": ["materialize_architecture"],
                "selectionPurposes": ["architecture-materialization"]
            },
            "definitions": [],
            "sets": [],
            "qualifications": [],
            "catalog": {},
            "policy": {}
        }
    })
}

fn parsed(raw: &str) -> Json {
    serde_json::from_str(raw).expect("fixture JSON is valid")
}

fn retained_resource(key: &str) -> Json {
    let raw = match key {
        "architecture-interpretation/1.1/source-decoding-1.7" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-source-decoding-1.7.json"
        ),
        "architecture-interpretation/1.1/source-mapping-1.7-to-2.4" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-source-mapping-1.7-to-2.4.json"
        ),
        "architecture-interpretation/1.1/rules" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-rules.json"
        ),
        "architecture-interpretation/1.1/legacy-compatibility" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-legacy-compatibility.json"
        ),
        "architecture-interpretation/1.1/conformance" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/architecture-interpretation-1.1-conformance.json"
        ),
        "normalized-model/2.4/conformance" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normalized-model-2.4-conformance.json"
        ),
        "normalized-model/2.4/schema/normalized-architecture-model.schema" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-architecture-model.schema.json"
        ),
        "normalized-model/2.4/schema/normalized-entity-registry.schema" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-entity-registry.schema.json"
        ),
        "normalized-model/2.4/schema/normalized-entity.schema" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-normalized-entity.schema.json"
        ),
        "normalized-model/2.4/schema/relationship-record.schema" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-relationship-record.schema.json"
        ),
        "normalized-model/2.4/schema/relationship-registry.schema" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-relationship-registry.schema.json"
        ),
        "normalized-model/2.4/schema/unresolved-registry.schema" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normalized-model-2.4-schema-unresolved-registry.schema.json"
        ),
        "normative-semantics/1.0/definition" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normative-semantics-definition.json"
        ),
        "normative-semantics/1.0/conformance" => include_str!(
            "../../contracts/semantic-contract/v1.0/resources/normative-semantics-conformance.json"
        ),
        _ => panic!("missing retained resource fixture: {key}"),
    };
    parsed(raw)
}

fn retained_definition(name: &str) -> Json {
    let raw = match name {
        "architecture-interpretation-1.1.json" => include_str!(
            "../../contracts/semantic-contract/v1.0/definitions/architecture-interpretation-1.1.json"
        ),
        "normalized-model-2.4.json" => include_str!(
            "../../contracts/semantic-contract/v1.0/definitions/normalized-model-2.4.json"
        ),
        "normative-semantics-1.0.json" => include_str!(
            "../../contracts/semantic-contract/v1.0/definitions/normative-semantics-1.0.json"
        ),
        _ => panic!("missing retained definition fixture: {name}"),
    };
    parsed(raw)
}

fn retained_bundle(name: &str) -> Json {
    let definition = retained_definition(name);
    let resources = definition["resourceManifest"]
        .as_array()
        .expect("definition resource manifest")
        .iter()
        .map(|entry| {
            json!({
                "canonicalResourceKey": entry["canonicalResourceKey"],
                "content": retained_resource(entry["canonicalResourceKey"].as_str().expect("resource key")),
            })
        })
        .collect::<Vec<_>>();
    json!({"definition": definition, "resources": resources})
}

fn source_binding() -> Json {
    json!({
        "family": "authoring",
        "version": "1.7",
        "schemaResource": {
            "canonicalResourceKey": "authoring/1.7/schema/adr-logical.schema",
            "contentDigest": "sha256:32f6058dd5efc77cf6612587304f9275aa3a66bb7270fdb0f7ef4b871c9f5731"
        },
        "resourceClosure": [
            {"canonicalResourceKey": "authoring/1.7/schema/adr-common.schema", "contentDigest": "sha256:f8d51b652285e8cdcefa19aa13c0cd76cb388fbdf86d3d32efe1470bd2606660"},
            {"canonicalResourceKey": "authoring/1.7/schema/adr-logical.schema", "contentDigest": "sha256:32f6058dd5efc77cf6612587304f9275aa3a66bb7270fdb0f7ef4b871c9f5731"},
            {"canonicalResourceKey": "authoring/1.7/schema/types.schema", "contentDigest": "sha256:037ad8a50ad48e0b19452795e4b0ffd710e5aecf1d93e6aa1d69db3745ef1b65"}
        ]
    })
}

fn successor_request() -> Json {
    let set: Json = parsed(include_str!(
        "../../contracts/semantic-contract/v1.0/sets/scs-v1-sha256-2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020.json"
    ));
    let profile: Json = parsed(include_str!(
        "../../contracts/semantic-contract/v1.0/profiles/architecture-materialization-1.1.json"
    ));
    let all_qualifications: Json = parsed(include_str!(
        "../../contracts/semantic-contract/v1.0/qualifications/architecture-materialization-1.1.json"
    ));
    let all_policy: Json = parsed(include_str!(
        "../../contracts/semantic-contract/v1.0/policy/semantic-contract-policy-1.0.json"
    ));
    let all_catalog: Json = parsed(include_str!(
        "../../contracts/semantic-contract/v1.0/catalog/semantic-contract-catalog-1.0.json"
    ));
    let qualification = all_qualifications
        .as_array()
        .expect("successor qualifications")
        .iter()
        .find(|value| value["operation"] == "materialize_architecture")
        .cloned()
        .expect("successor materialization qualification");
    let policy = all_policy.as_object().expect("policy object").clone();
    let policy = json!({
        "policySchemaVersion": policy["policySchemaVersion"],
        "policyRevision": policy["policyRevision"],
        "entries": policy["entries"].as_array().expect("policy entries").iter().filter(|value| value["semanticContractSetId"] == set["semanticContractSetId"] && value["operation"] == "materialize_architecture").cloned().collect::<Vec<_>>()
    });
    let catalog = json!({
        "catalogSchemaVersion": all_catalog["catalogSchemaVersion"],
        "catalogRevision": all_catalog["catalogRevision"],
        "entries": all_catalog["entries"].as_array().expect("catalog entries").iter().filter(|value| value["semanticContractSetId"] == set["semanticContractSetId"]).cloned().collect::<Vec<_>>()
    });
    let document = json!({
        "schema_version": "1.7",
        "adr_type": "logical",
        "id": "019109a0-b1c2-7def-8a00-112233445566",
        "alias_id": "ADR-L-0001",
        "alias_name": "sample-adr",
        "title": "Sample ADR",
        "status": "proposed",
        "created_date": "2026-09-15",
        "authors": ["test"],
        "context": "bounded context",
        "decisions": [{"id": "019109a0-b1c2-7def-8a00-112233445567", "alias_id": "DEC-0001", "alias_name": "sample-decision", "summary": "Use sample", "rationale": "Explicit"}]
    });
    json!({
        "core_contract_version": "1.3",
        "operation": "materialize_architecture",
        "request": {
            "operation": "materialize_architecture",
            "materializationContractVersion": "1.1",
            "semanticContractSetId": set["semanticContractSetId"],
            "authorityProvider": {"kind": "fixture-provider", "architectureNamespace": "example"},
            "sourceBasis": {
                "sealed": true,
                "providerSourceIdentity": "fixture-provider:example",
                "sourceRevision": "revision-1",
                "artifacts": [{"sourceRef": "ADR-L-0001", "artifactPath": "architecture/ADR-L-0001.yaml", "contentDigest": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "sourceContract": source_binding(), "document": document}]
            },
            "providerProvenance": {"semanticCoreContractVersion": "1.3", "packageVersion": "0.11.1", "hostBinding": "test"},
            "targetOperation": "materialize_architecture",
            "direction": "forward",
            "useMode": "new",
            "profile": profile,
            "definitions": [retained_bundle("architecture-interpretation-1.1.json"), retained_bundle("normalized-model-2.4.json"), retained_bundle("normative-semantics-1.0.json")],
            "sets": [set],
            "qualifications": [qualification],
            "catalog": catalog,
            "policy": policy
        }
    })
}

fn execute(value: Json) -> Json {
    let bytes = serde_json::to_vec(&value).expect("request serializes");
    serde_json::from_slice(&super::execute_json(&bytes)).expect("result is JSON")
}

#[test]
fn protocol_1_3_rejects_an_unqualified_forward_authoring_1_7_shape() {
    let result = execute(request("1.7"));
    assert_eq!(result["core_contract_version"], "1.3");
    assert_eq!(result["operation"], "materialize_architecture");
    assert_eq!(result["result"]["outcome"], "Rejected");
    assert_eq!(result["result"]["materializationContractVersion"], "1.1");
    assert_eq!(result["result"]["normalizedModel"], Json::Null);
}

fn assert_rejected(value: Json, expected_code: Option<&str>) {
    let result = execute(value);
    assert_eq!(result["result"]["outcome"], "Rejected");
    assert_eq!(result["result"]["success"], false);
    assert_eq!(result["result"]["normalizedModel"], Json::Null);
    if let Some(expected_code) = expected_code {
        assert!(
            result["result"]["diagnostics"]
                .as_array()
                .is_some_and(|items| items.iter().any(|item| item["code"] == expected_code)),
            "expected diagnostic {expected_code}: {}",
            result["result"]["diagnostics"]
        );
    }
}

#[test]
fn protocol_1_3_rejects_tampered_exact_authority_before_interpretation() {
    let mut wrong_ai = successor_request();
    wrong_ai["request"]["profile"]["participatingFamilies"][0]["semanticContractVersion"] =
        json!("1.0");
    assert_rejected(wrong_ai, Some("semantic_contract.profile_family_mismatch"));

    let mut wrong_normalized = successor_request();
    wrong_normalized["request"]["profile"]["participatingFamilies"][1]["semanticContractVersion"] =
        json!("2.3");
    assert_rejected(
        wrong_normalized,
        Some("semantic_contract.profile_family_mismatch"),
    );

    let mut wrong_normative = successor_request();
    wrong_normative["request"]["profile"]["participatingFamilies"][2]["semanticContractVersion"] =
        json!("0.9");
    assert_rejected(
        wrong_normative,
        Some("semantic_contract.profile_family_mismatch"),
    );

    let mut duplicate_family = successor_request();
    duplicate_family["request"]["profile"]["participatingFamilies"]
        .as_array_mut()
        .expect("profile families")
        .push(json!({
            "semanticContractFamily": "normalized-model",
            "semanticContractVersion": "2.4",
            "cardinality": 1
        }));
    assert_rejected(
        duplicate_family,
        Some("semantic_contract.duplicate_profile_family"),
    );

    let mut missing_family = successor_request();
    missing_family["request"]["profile"]["participatingFamilies"]
        .as_array_mut()
        .expect("profile families")
        .pop();
    assert_rejected(
        missing_family,
        Some("semantic_contract.profile_family_mismatch"),
    );

    let mut wrong_scf = successor_request();
    wrong_scf["request"]["sets"][0]["members"][0]["semanticContractFingerprint"] =
        json!("sha256:0000000000000000000000000000000000000000000000000000000000000000");
    assert_rejected(wrong_scf, Some("semantic_contract.scs_id_mismatch"));

    let mut altered_definition_resource = successor_request();
    altered_definition_resource["request"]["definitions"][0]["resources"][0]["content"] =
        json!({"tampered": true});
    assert_rejected(
        altered_definition_resource,
        Some("semantic_contract.integrity_failure"),
    );

    let mut incomplete_definition_closure = successor_request();
    incomplete_definition_closure["request"]["definitions"][0]["resources"]
        .as_array_mut()
        .expect("definition resources")
        .pop();
    assert_rejected(
        incomplete_definition_closure,
        Some("semantic_contract.integrity_failure"),
    );

    let mut altered_source_digest = successor_request();
    altered_source_digest["request"]["sourceBasis"]["artifacts"][0]["sourceContract"]
        ["schemaResource"]["contentDigest"] =
        json!("sha256:0000000000000000000000000000000000000000000000000000000000000000");
    assert_rejected(
        altered_source_digest,
        Some("semantic_contract.source_contract_schema_digest_mismatch"),
    );

    let mut incomplete_source_closure = successor_request();
    incomplete_source_closure["request"]["sourceBasis"]["artifacts"][0]["sourceContract"]
        ["resourceClosure"]
        .as_array_mut()
        .expect("source closure")
        .pop();
    assert_rejected(
        incomplete_source_closure,
        Some("semantic_contract.source_contract_closure_mismatch"),
    );

    let mut uncatalogued = successor_request();
    uncatalogued["request"]["catalog"]["entries"][0]["catalogued"] = json!(false);
    assert_rejected(
        uncatalogued,
        Some("semantic_contract.exact_resolution_catalog_failure"),
    );

    let mut prohibited = successor_request();
    prohibited["request"]["policy"]["entries"][0]["newUsePolicy"] = json!("prohibited");
    assert_rejected(prohibited, Some("semantic_contract.new_use_prohibited"));

    let mut unsupported = successor_request();
    unsupported["request"]["policy"]["entries"][0]["installedExecutionSupport"] = json!(false);
    let unsupported_result = execute(unsupported);
    assert_eq!(unsupported_result["result"]["outcome"], "Unavailable");
    assert_eq!(unsupported_result["result"]["success"], false);
    assert_eq!(unsupported_result["result"]["normalizedModel"], Json::Null);
    assert!(unsupported_result["result"]["diagnostics"]
        .as_array()
        .is_some_and(|items| {
            items.iter().any(|item| {
                item["code"] == "semantic_contract.installed_execution_support_unavailable"
            })
        }));

    let mut wrong_direction = successor_request();
    wrong_direction["request"]["direction"] = json!("reverse");
    assert_rejected(
        wrong_direction,
        Some("semantic_contract.missing_whole_tuple_qualification"),
    );

    let mut historical = successor_request();
    historical["request"]["useMode"] = json!("historical");
    assert_rejected(
        historical,
        Some("semantic_contract.missing_whole_tuple_qualification"),
    );

    let mut wrong_operation = successor_request();
    wrong_operation["request"]["targetOperation"] = json!("resolve_semantic_contract_set");
    assert_rejected(wrong_operation, Some("core.invalid_request"));
}

#[test]
fn protocol_1_3_materializes_the_exact_retained_successor() {
    let result = execute(successor_request());
    assert_eq!(result["core_contract_version"], "1.3");
    assert_eq!(result["result"]["outcome"], "Materialized");
    assert_eq!(result["result"]["success"], true);
    assert_eq!(result["result"]["materializationContractVersion"], "1.1");
    assert_eq!(
        result["result"]["semanticBasis"]["semanticContractSetId"],
        "scs:v1:sha256:2cf903fe80c50b97443645369b28443c7fa186ed758e2e22d7ce758ccb0d6020"
    );
    assert_eq!(result["result"]["normalizedModel"]["schema_version"], "2.4");
    assert!(result["result"]["normalizedModel"]["entities"]
        .as_array()
        .is_some_and(|items| !items.is_empty()));
    assert!(result["result"]["normalizedModel"]
        .get("entityRegistry")
        .is_none());
}

#[test]
fn protocol_1_3_wrong_exact_scs_rejects_before_interpretation() {
    let mut request = successor_request();
    request["request"]["semanticContractSetId"] =
        json!("scs:v1:sha256:0000000000000000000000000000000000000000000000000000000000000000");
    let result = execute(request);
    assert_eq!(result["result"]["outcome"], "Rejected");
    assert_eq!(result["result"]["normalizedModel"], Json::Null);
    assert!(result["result"]["diagnostics"]
        .as_array()
        .is_some_and(|items| items
            .iter()
            .any(|item| item["code"] == "semantic_contract.exact_set_not_retained")));
}

#[test]
fn protocol_1_3_rejects_historical_forward_bindings() {
    for version in ["1.5", "1.6"] {
        let result = execute(request(version));
        assert_eq!(result["core_contract_version"], "1.3");
        assert_eq!(result["result"]["outcome"], "Rejected");
        assert_eq!(result["result"]["success"], false);
    }
}

#[test]
fn protocol_1_3_rejects_malformed_and_undeclared_envelopes() {
    let malformed =
        execute(json!({"core_contract_version": "1.3", "operation": "materialize_architecture"}));
    assert_eq!(malformed["core_contract_version"], "1.3");
    assert_eq!(malformed["result"]["outcome"], "Rejected");

    let undeclared = execute(json!({
        "core_contract_version": "1.3",
        "operation": "materialize_architecture",
        "request": request("1.7")["request"].clone(),
        "provider_identity": "must-not-be-inferred"
    }));
    assert_eq!(undeclared["core_contract_version"], "1.3");
    assert_eq!(undeclared["success"], false);
}

#[test]
fn older_protocol_routing_remains_versioned() {
    let value = json!({
        "core_contract_version": "1.2",
        "operation": "validate_authoring",
        "request": {"operation": "validate_authoring"}
    });
    let result = execute(value);
    assert_eq!(result["core_contract_version"], "1.2");
    assert_eq!(result["operation"], "validate_authoring");
}
