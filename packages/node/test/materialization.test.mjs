import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
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

test("public Node materialization returns normalized-model 2.3 from exact SCS", async () => {
  const result = await materializeArchitecture(publicRequest(vector));
  assert.equal(result.success, true);
  assert.equal(result.outcome, "Materialized");
  assert.equal(result.semanticBasis.semanticContractSetId, vector.semanticContractSetId);
  assert.equal(result.normalizedModel.schema_version, "2.3");
  assert.equal(Object.isFrozen(result), true);
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
});
