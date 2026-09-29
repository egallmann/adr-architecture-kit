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

fn execute(value: Json) -> Json {
    let bytes = serde_json::to_vec(&value).expect("request serializes");
    serde_json::from_slice(&super::execute_json(&bytes)).expect("result is JSON")
}

#[test]
fn protocol_1_3_accepts_the_forward_authoring_1_7_shape_but_stays_unavailable() {
    let result = execute(request("1.7"));
    assert_eq!(result["core_contract_version"], "1.3");
    assert_eq!(result["operation"], "materialize_architecture");
    assert_eq!(result["result"]["outcome"], "Unavailable");
    assert_eq!(result["result"]["materializationContractVersion"], "1.1");
    assert_eq!(result["result"]["normalizedModel"], Json::Null);
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
    let malformed = execute(json!({"core_contract_version": "1.3", "operation": "materialize_architecture"}));
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
