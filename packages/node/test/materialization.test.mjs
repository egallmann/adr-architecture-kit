import test from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { delimiter } from "node:path";
import { materializeArchitecture } from "../dist/node/materialization.js";

const vector = JSON.parse(await readFile(
  resolve("../../contracts/semantic-core/v1.1/vectors/architecture-materialization.json"),
  "utf8",
)).cases[0].request;

function publicRequest(request) {
  return {
    semantic_contract_set_id: request.semanticContractSetId,
    authority_provider: {
      kind: request.authorityProvider.kind,
      architecture_namespace: request.authorityProvider.architectureNamespace,
    },
    source_basis: {
      provider_source_identity: request.sourceBasis.providerSourceIdentity,
      source_revision: request.sourceBasis.sourceRevision,
      artifacts: request.sourceBasis.artifacts.map((artifact) => ({
        source_ref: artifact.sourceRef,
        artifact_path: artifact.artifactPath,
        content_digest: artifact.contentDigest,
        source_contract: {
          version: artifact.sourceContract.version,
          schema_resource: {
            canonical_resource_key: artifact.sourceContract.schemaResource.canonicalResourceKey,
            content_digest: artifact.sourceContract.schemaResource.contentDigest,
          },
          resource_closure: artifact.sourceContract.resourceClosure.map((item) => ({
            canonical_resource_key: item.canonicalResourceKey,
            content_digest: item.contentDigest,
          })),
        },
        document: artifact.document,
      })),
    },
    direction: "none",
    use_mode: "new",
    profile_id: "architecture-materialization@1.0",
  };
}

function contractSummary(contract) {
  return {
    family: contract.family,
    version: contract.version,
    schema_resource: contract.schema_resource,
    resource_closure: contract.resource_closure,
  };
}

function publicSummary(result) {
  return {
    success: result.success,
    outcome: result.outcome,
    authority_provider: result.authorityProvider,
    source_basis: result.sourceBasis === null ? null : {
      sealed: result.sourceBasis.sealed,
      provider_source_identity: result.sourceBasis.provider_source_identity,
      source_revision: result.sourceBasis.source_revision,
      artifacts: result.sourceBasis.artifacts.map((artifact) => ({
        source_ref: artifact.source_ref,
        artifact_path: artifact.artifact_path,
        content_digest: artifact.content_digest,
        source_contract: contractSummary(artifact.source_contract),
        document: artifact.document,
      })),
      legacy_identity_map: result.sourceBasis.legacy_identity_map ?? null,
    },
    source_contract_closure: result.sourceContractClosure.map(contractSummary),
    semantic_basis: {
      semantic_contract_set_id: result.semanticBasis.semanticContractSetId,
      authority_state_fingerprint: result.semanticBasis.authorityStateFingerprint,
    },
    normalized_model: result.normalizedModel,
    source_capability_limitations: result.sourceCapabilityLimitations.map((limitation) => ({
      source_contract: contractSummary(limitation.sourceContractRef),
      semantic_capability: limitation.semanticCapability,
      classification: limitation.classification,
    })),
    provider_provenance: {
      semantic_core_contract_version: result.providerProvenance.semanticCoreContractVersion,
      package_version: result.providerProvenance.packageVersion,
      host_binding: result.providerProvenance.hostBinding,
    },
    diagnostics: result.diagnostics,
  };
}

function pythonPublicSummary(request) {
  const script = String.raw`
import json
import sys
from collections.abc import Mapping
from adr_kit.api import (
    ArchitectureMaterializationRequest,
    MaterializationAuthorityProvider,
    MaterializationSourceBasis,
    materialize_architecture,
)

wire = json.load(sys.stdin)
value = ArchitectureMaterializationRequest(
    semantic_contract_set_id=wire["semanticContractSetId"],
    authority_provider=MaterializationAuthorityProvider(
        kind=wire["authorityProvider"]["kind"],
        architecture_namespace=wire["authorityProvider"]["architectureNamespace"],
    ),
    source_basis=MaterializationSourceBasis.from_wire(wire["sourceBasis"]),
    direction="none",
    use_mode="new",
    profile_id="architecture-materialization@1.0",
)
result = materialize_architecture(value)

def contract_summary(contract):
    return {
        "family": contract.family,
        "version": contract.version,
        "schema_resource": {
            "canonical_resource_key": contract.schema_resource.canonical_resource_key,
            "content_digest": contract.schema_resource.content_digest,
        },
        "resource_closure": [
            {"canonical_resource_key": item.canonical_resource_key, "content_digest": item.content_digest}
            for item in contract.resource_closure
        ],
    }

def jsonable(value):
    if isinstance(value, Mapping): return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)): return [jsonable(item) for item in value]
    return value

summary = {
    "success": result.success,
    "outcome": result.outcome,
    "authority_provider": {
        "kind": result.authority_provider.kind,
        "architecture_namespace": result.authority_provider.architecture_namespace,
    },
    "source_basis": {
        "sealed": result.source_basis.sealed,
        "provider_source_identity": result.source_basis.provider_source_identity,
        "source_revision": result.source_basis.source_revision,
        "artifacts": [
            {
                "source_ref": item.source_ref,
                "artifact_path": item.artifact_path,
                "content_digest": item.content_digest,
                "source_contract": contract_summary(item.source_contract),
                "document": jsonable(item.document),
            }
            for item in result.source_basis.artifacts
        ],
        "legacy_identity_map": jsonable(result.source_basis.legacy_identity_map),
    },
    "source_contract_closure": [contract_summary(item) for item in result.source_contract_closure],
    "semantic_basis": {
        "semantic_contract_set_id": result.semantic_basis.semantic_contract_set_id,
        "authority_state_fingerprint": result.semantic_basis.authority_state_fingerprint,
    },
    "normalized_model": jsonable(result.normalized_model),
    "source_capability_limitations": [
        {
            "source_contract": contract_summary(item.source_contract),
            "semantic_capability": item.semantic_capability,
            "classification": item.classification,
        }
        for item in result.source_capability_limitations
    ],
    "provider_provenance": {
        "semantic_core_contract_version": result.provider_provenance.semantic_core_contract_version,
        "package_version": result.provider_provenance.package_version,
        "host_binding": result.provider_provenance.host_binding,
    },
    "diagnostics": [
        {"severity": item.severity, "code": item.code, "message": item.message, "path": item.path}
        for item in result.diagnostics
    ],
}
print(json.dumps(summary, sort_keys=True))
`;
  const repoRoot = resolve("../..");
  const localPython = process.platform === "win32"
    ? resolve(repoRoot, ".venv/Scripts/python.exe")
    : resolve(repoRoot, ".venv/bin/python");
  const python = existsSync(localPython) ? localPython : "python";
  const pythonPath = [repoRoot, resolve(repoRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(delimiter);
  const completed = spawnSync(python, ["-c", script], {
    cwd: repoRoot,
    input: JSON.stringify(request),
    encoding: "utf8",
    env: { ...process.env, PYTHONPATH: pythonPath },
  });
  assert.equal(completed.status, 0, completed.stderr || completed.stdout);
  return JSON.parse(completed.stdout);
}

test("public Node materialization returns normalized-model 2.3 from exact SCS", async () => {
  const result = await materializeArchitecture(publicRequest(vector));
  assert.equal(result.success, true);
  assert.equal(result.outcome, "Materialized");
  assert.deepEqual(result.authorityProvider, {
    kind: "fixture-provider",
    architecture_namespace: "example",
  });
  assert.equal("architectureNamespace" in result.authorityProvider, false);
  assert.equal(result.sourceBasis.sealed, true);
  assert.equal(result.sourceBasis.provider_source_identity, "fixture-provider:example");
  assert.equal(result.sourceBasis.source_revision, "revision-1");
  assert.equal(result.sourceBasis.artifacts.length, 1);
  assert.equal(result.sourceBasis.artifacts[0].source_ref, "logical-16");
  assert.equal(result.sourceBasis.artifacts[0].artifact_path, "architecture/logical-16.yaml");
  assert.equal(result.sourceBasis.artifacts[0].source_contract.family, "authoring");
  assert.equal(result.sourceBasis.artifacts[0].source_contract.version, "1.6");
  assert.equal(result.sourceBasis.artifacts[0].source_contract.schema_resource.canonical_resource_key, "authoring/1.6/schema/adr-logical.schema");
  assert.equal(result.sourceBasis.artifacts[0].source_contract.resource_closure.length, 3);
  assert.deepEqual(result.sourceContractClosure, [result.sourceBasis.artifacts[0].source_contract]);
  assert.equal(result.semanticBasis.semanticContractSetId, vector.semanticContractSetId);
  assert.match(result.semanticBasis.authorityStateFingerprint, /^asf:v1:sha256:[0-9a-f]{64}$/);
  assert.equal(result.normalizedModel.schema_version, "2.3");
  assert.deepEqual(result.sourceCapabilityLimitations, []);
  assert.deepEqual(result.providerProvenance, {
    semanticCoreContractVersion: "1.1",
    packageVersion: "0.11.0",
    hostBinding: "public-host",
  });
  assert.deepEqual(result.diagnostics, []);
  assert.equal(result.package_version, "0.11.0");
  assert.equal(result.api_contract_version, "1.0");
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.authorityProvider), true);
  assert.equal(Object.isFrozen(result.sourceBasis), true);
  assert.equal(Object.isFrozen(result.sourceBasis.artifacts[0].document), true);
  assert.equal(Object.isFrozen(result.sourceBasis.artifacts[0].source_contract.resource_closure), true);
  assert.equal(Object.isFrozen(result.normalizedModel), true);
});

test("public Node materialization preserves bounded unavailable and exact-set rejection", async () => {
  const request = publicRequest(vector);
  const unavailable = await materializeArchitecture({ ...request, source_basis: null });
  assert.equal(unavailable.success, false);
  assert.equal(unavailable.outcome, "Unavailable");

  const rejected = await materializeArchitecture({
    ...request,
    semantic_contract_set_id: `scs:v1:sha256:${"0".repeat(64)}`,
  });
  assert.equal(rejected.success, false);
  assert.equal(rejected.outcome, "Rejected");
  assert.ok(rejected.diagnostics.length > 0);

  const withLegacyIdentity = await materializeArchitecture({
    ...request,
    source_basis: {
      ...request.source_basis,
       legacy_identity_map: {
         sealed: true,
         provider: "fixture-provider:example",
         entries: [{ sourceId: "legacy:boundary", canonicalId: "canonical:boundary" }],
       },
    },
  });
   assert.deepEqual(withLegacyIdentity.sourceBasis.legacy_identity_map, {
     sealed: true,
     provider: "fixture-provider:example",
     entries: [{ sourceId: "legacy:boundary", canonicalId: "canonical:boundary" }],
   });
});

test("Python and Node public materialization expose equivalent DTO information", async () => {
  const nodeResult = await materializeArchitecture(publicRequest(vector));
  assert.deepEqual(publicSummary(nodeResult), pythonPublicSummary(vector));
});
