import test from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { executeSemanticCoreRequest, openProviderRegistry, validateArchitectureFacts, validateArchitectureReferences, validateContract, validateProjectMetadata } from "../dist/node/core.js";
import { calculateSemanticContractFingerprint, canonicalizeSemanticJson, composeSemanticContractSet, getSemanticContract, listSemanticContracts, loadSemanticResource, validateSemanticResourceClosure, verifySemanticContract } from "../dist/node/semantic-contract.js";
import { validateArchitecture } from "../dist/node/architecture.js";
import { fixtureRepository } from "./fixture-repository.mjs";
import { capabilities } from "../dist/index.js";

const vectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/contract-validation.json");
const metadataVectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/project-metadata-validation.json");
const linkageVectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/embodiment-linkage.json");
const repositoryVectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/repository-validation.json");
const artifactVectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/generated-artifact-classification.json");
const referenceVectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/architecture-reference-validation.json");
const architectureVectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/architecture-validation.json");
const capabilityContractPath = resolve("../../contracts/compatibility/host-capabilities.json");
const semanticContractVectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/semantic-contract.json");

test("Node capability manifest consumes the governed host capability contract", async () => {
  const contract = JSON.parse(await readFile(capabilityContractPath, "utf8"));
  const manifest = capabilities();
  assert.deepEqual(manifest.host_operations, contract.peer_host_operations);
  assert.deepEqual(manifest.pending_host_operations, contract.pending_host_operations);
  assert.deepEqual(manifest.browser_operations, contract.browser_operations);
});

test("Node binding executes the shared semantic-core conformance vectors", async () => {
  const document = JSON.parse(await readFile(vectorPath, "utf8"));
  for (const vector of document.cases) {
    const result = await executeSemanticCoreRequest(vector.request);
    assert.equal(result.success, vector.expected.success, vector.name);
    assert.equal(result.outcome, vector.expected.outcome, vector.name);
    if ("sentinel_field_count" in vector.expected) assert.equal(result.sentinel_field_count, vector.expected.sentinel_field_count, vector.name);
    if ("non_complete_entity_count" in vector.expected) assert.equal(result.non_complete_entity_count, vector.expected.non_complete_entity_count, vector.name);
    if ("issue_count" in vector.expected) assert.equal(result.issues.length, vector.expected.issue_count, vector.name);
    if ("issue_codes" in vector.expected) assert.deepEqual(result.diagnostics.filter((item) => item.code !== "contract.issue").map((item) => item.code), vector.expected.issue_codes, vector.name);
  }
});

test("Node semantic-contract binding matches the shared vectors", async () => {
  const document = JSON.parse(await readFile(semanticContractVectorPath, "utf8"));
  for (const vector of document.cases) {
    const result = await executeSemanticCoreRequest(vector.request);
    assert.equal(result.success, vector.expected.success, vector.name);
    for (const field of ["canonical_preimage_json", "fingerprint", "semantic_contract_fingerprint", "semantic_contract_set_id"]) {
      if (field in vector.expected) assert.equal(result[field], vector.expected[field], vector.name);
    }
    if (vector.expected.diagnostic_codes) assert.deepEqual(result.diagnostics.map((item) => item.code), vector.expected.diagnostic_codes, vector.name);
  }
});

test("Node public semantic-contract bindings expose the same immutable closure", async () => {
  const contracts = listSemanticContracts();
  assert.deepEqual(contracts.map((item) => item.semanticContractFamily), ["architecture-interpretation", "normalized-model", "normative-semantics"]);
  const contract = getSemanticContract("normative-semantics");
  const fingerprint = await calculateSemanticContractFingerprint(contract);
  assert.equal(fingerprint.semantic_contract_fingerprint, contract.semanticContractFingerprint);
  assert.equal((await verifySemanticContract(contract)).success, true);
  const resources = contract.resourceManifest.map((entry) => ({
    canonicalResourceKey: entry.canonicalResourceKey,
    content: loadSemanticResource(entry.canonicalResourceKey),
  }));
  const closure = await validateSemanticResourceClosure(contract, resources);
  assert.equal(closure.closure_valid, true);
  const set = await composeSemanticContractSet(contracts);
  assert.match(set.semantic_contract_set_id ?? "", /^scs:v1:sha256:[0-9a-f]{64}$/);
  const canonical = await canonicalizeSemanticJson('{"x":1,"x":2}');
  assert.equal(canonical.success, false);
  assert.equal(canonical.diagnostics[0]?.code, "semantic_contract.invalid_json");
});

test("Node binding matches shared project-metadata vectors", async () => {
  const document = JSON.parse(await readFile(metadataVectorPath, "utf8"));
  for (const vector of document.cases) {
    const result = await executeSemanticCoreRequest(vector.request);
    assert.equal(result.success, vector.expected.success, vector.name);
    assert.equal(result.diagnostics.length, vector.expected.diagnostic_count, vector.name);
    if (vector.expected.paths) assert.deepEqual(result.diagnostics.map((item) => item.path), vector.expected.paths, vector.name);
  }
});

test("Node binding matches shared linkage vectors", async () => {
  const document = JSON.parse(await readFile(linkageVectorPath, "utf8"));
  for (const vector of document.cases) {
    const result = await executeSemanticCoreRequest(vector.request);
    assert.equal(result.success, vector.expected.success, vector.name);
    assert.equal(result.links.length, vector.expected.link_count, vector.name);
    assert.equal(result.rejected_claims.length, vector.expected.rejected_count, vector.name);
    assert.equal(result.error_count, vector.expected.error_count, vector.name);
    assert.equal(result.warning_count, vector.expected.warning_count, vector.name);
  }
});

test("Node binding matches shared repository vectors", async () => {
  const document = JSON.parse(await readFile(repositoryVectorPath, "utf8"));
  for (const vector of document.cases) {
    const result = await executeSemanticCoreRequest(vector.request);
    assert.equal(result.success, vector.expected.success, vector.name);
    assert.equal(result.diagnostics.length, vector.expected.diagnostic_count, vector.name);
    assert.equal(result.entity_count, vector.expected.entity_count, vector.name);
    if (vector.expected.diagnostic_codes) {
      assert.deepEqual(result.diagnostics.map((item) => item.code), vector.expected.diagnostic_codes, vector.name);
    }
  }
});

test("Node binding matches shared generated-artifact vectors", async () => {
  const document = JSON.parse(await readFile(artifactVectorPath, "utf8"));
  for (const vector of document.cases) {
    const result = await executeSemanticCoreRequest(vector.request);
    assert.equal(result.success, vector.expected.success, vector.name);
    assert.equal(result.status, vector.expected.status, vector.name);
    assert.equal(result.reason_code, vector.expected.reason_code, vector.name);
  }
});

test("Node binding matches shared architecture-reference vectors", async () => {
  const document = JSON.parse(await readFile(referenceVectorPath, "utf8"));
  for (const vector of document.cases) {
    const result = await executeSemanticCoreRequest(vector.request);
    assert.equal(result.success, vector.expected.success, vector.name);
    assert.equal(result.error_count, vector.expected.error_count, vector.name);
    assert.equal(result.warning_count, vector.expected.warning_count, vector.name);
    assert.equal(result.diagnostics.length, vector.expected.diagnostic_count, vector.name);
  }
});

test("Node binding matches shared architecture-validation vectors", async () => {
  const document = JSON.parse(await readFile(architectureVectorPath, "utf8"));
  for (const vector of document.cases) {
    const result = await executeSemanticCoreRequest(vector.request);
    assert.equal(result.success, vector.expected.success, vector.name);
    assert.equal(result.error_count, vector.expected.error_count, vector.name);
    assert.equal(result.warning_count, vector.expected.warning_count, vector.name);
    assert.equal(result.diagnostics.length, vector.expected.diagnostic_count, vector.name);
    if (vector.expected.codes) assert.deepEqual(result.diagnostics.map((item) => item.code), vector.expected.codes, vector.name);
  }
});

test("Node normalized architecture adapter delegates business rules", async () => {
  const document = JSON.parse(await readFile(architectureVectorPath, "utf8"));
  const request = document.cases[1].request;
  const result = await validateArchitectureFacts({ records: request.records, mode: request.mode });
  assert.equal(result.success, false);
  assert.equal(result.error_count, 4);
  assert.equal(result.warning_count, 2);
});

test("Node architecture host adapter owns source loading and delegates normalized rules", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "adr-kit-architecture-"));
  await mkdir(resolve(root, "adrs/logical"), { recursive: true });
  await writeFile(resolve(root, "adrs/logical/ADR-L-9999.yaml"), `schema_version: "1.0"
adr_type: logical
id: ADR-L-9999
title: "Minimal Valid Logical ADR"
status: proposed
created_date: "2026-03-07"
authors: ["test.author"]
domains: ["test"]
context: "A conceptual boundary."
decisions:
  - id: DEC-0001
    summary: "Test decision"
    rationale: "A test rationale."
`, "utf8");
  const result = await validateArchitecture({ project_root: root, mode: "complete" });
  assert.equal(result.success, true);
  assert.deepEqual(result.validated_files, ["adrs/logical/ADR-L-9999.yaml"]);
  assert.deepEqual(result.diagnostics, []);
});

test("Node architecture-reference adapter delegates normalized facts", async () => {
  const document = JSON.parse(await readFile(referenceVectorPath, "utf8"));
  const request = document.cases[0].request;
  const result = await validateArchitectureReferences({
    records: request.records,
    reviews: request.reviews,
    overrides: request.overrides,
  });
  assert.equal(result.success, true);
  assert.equal(result.error_count, 0);
  assert.equal(result.warning_count, 0);
});

test("Node host contract validation loads a repository and delegates semantics", async () => {
  const root = await fixtureRepository();
  const result = await validateContract({ project_root: root });
  assert.equal(result.success, false);
  assert.equal(result.outcome, "non_compliant");
  assert.equal(result.issues[0].path, "entities[0].metadata.domains");
  assert.equal(result.api_contract_version, "1.0");
  assert.equal(typeof result.package_version, "string");
});

test("Node host project metadata validation delegates to the shared semantic core", async () => {
  const root = await fixtureRepository();
  await writeFile(resolve(root, "PROJECT.yaml"), [
    'schema_version: "1.0"',
    'type: project_metadata',
    'project:',
    '  name: fixture',
    '  description: fixture project',
    '  type: library',
    'ownership:',
    '  team: architecture',
    'repository:',
    '  url: local',
    '  primary_branch: main',
    'architecture_documentation:',
    '  adr_directory: adrs/',
    '  manifest_path: adrs/manifest.yaml',
    ''
  ].join("\n"), "utf8");
  const valid = await validateProjectMetadata({ project_root: root });
  assert.equal(valid.success, true);
  assert.deepEqual(valid.diagnostics, []);
  assert.equal(valid.api_contract_version, "1.0");
  assert.equal(typeof valid.package_version, "string");

  await writeFile(resolve(root, "PROJECT.yaml"), "project: [malformed\n", "utf8");
  const invalid = await validateProjectMetadata({ project_root: root });
  assert.equal(invalid.success, false);
  assert.equal(invalid.diagnostics[0].path, "PROJECT.yaml");
});

test("Node provider registry delegates routing validation to the shared semantic core", async () => {
  const root = await fixtureRepository();
  const registry = await openProviderRegistry({ fixture: root });
  assert.equal(registry.bindings.length, 1);
  assert.equal(registry.bindings[0].architecture_namespace, "fixture");
  assert.equal(registry.getRepository("fixture").architectureNamespace, "fixture");
  assert.equal(registry.getRepositoryByNamespace("fixture").project_root, root);
});
