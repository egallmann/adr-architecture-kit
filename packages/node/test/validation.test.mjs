import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { capabilities } from "../dist/capabilities.js";
import { UnsupportedContractVersionError } from "../dist/errors.js";
import { validateAuthoringDocument, validateContract } from "../dist/validation/index.js";
import * as node from "../dist/node/index.js";
import { buildEmbodimentLinkage } from "../dist/node/linkage.js";
import * as nodeGovernance from "../dist/node/governance.js";

const root = resolve("../../contracts/conformance/consumer-binding-v1");
const hostCapabilityContract = JSON.parse(
  await readFile(resolve("../../contracts/compatibility/host-capabilities.json"), "utf8"),
);
const load = async (path) => JSON.parse(await readFile(resolve(root, path), "utf8"));

test("capability discovery is local and explicit", () => {
  const manifest = capabilities();
  assert.deepEqual(manifest.supported_normalized_model_versions, ["2.1"]);
  assert.deepEqual(manifest.host_operations, ["capabilities", "validate_architecture", "validate_project_metadata", "validate_contract", "open_repository", "open_provider_registry", "build_embodiment_linkage"]);
  assert.ok(manifest.pending_host_operations.includes("compile_architecture"));
  assert.deepEqual(manifest.browser_operations, ["capabilities"]);
  assert.equal("supported_authoring_domain_versions" in manifest, false);
  assert.equal("preferred_authoring_domain_version" in manifest, false);
  assert.equal("authoring_capabilities" in manifest, false);
  assert.deepEqual(manifest.browser_safe_entrypoints, [".", "./model", "./schemas", "./validation"]);
});

test("public Node governance entry point excludes internal semantic-core seams", () => {
  assert.equal("executeSemanticCoreRequest" in nodeGovernance, false);
  assert.equal("validateArchitectureReferences" in nodeGovernance, false);
  assert.equal(typeof nodeGovernance.validateArchitecture, "function");
  assert.equal(typeof nodeGovernance.validateContract, "function");
  assert.equal(typeof nodeGovernance.validateProjectMetadata, "function");
});

test("host capability contract maps to real Node exports and keeps pending work hidden", () => {
  const exportsByCapability = {
    capabilities,
    validate_architecture: nodeGovernance.validateArchitecture,
    validate_project_metadata: nodeGovernance.validateProjectMetadata,
    validate_contract: nodeGovernance.validateContract,
    open_repository: node.openRepository,
    open_provider_registry: nodeGovernance.openProviderRegistry,
    build_embodiment_linkage: buildEmbodimentLinkage,
  };
  for (const operation of hostCapabilityContract.peer_host_operations) {
    assert.equal(typeof exportsByCapability[operation], "function", operation);
  }
  for (const operation of hostCapabilityContract.pending_host_operations) {
    assert.equal(operation in exportsByCapability, false, operation);
  }
});

test("canonical normalized model validates and unsupported capability fails explicitly", async () => {
  const fixture = await load("repository/model-v21.json");
  assert.equal(validateContract(fixture.input, "normalized-model:2.1").valid, true);
  assert.throws(() => validateContract(fixture.input, "normalized-model:1.1"), UnsupportedContractVersionError);
});

test("v1.6 evidence structural restriction is observable", async () => {
  const fixture = await load("embodiment-linkage/evidence-v16-enforces-inferred.json");
  const result = validateContract(fixture.input, "evidence-attribution:1.6");
  assert.equal(result.valid, false);
});

test("authoring structural validation relaxes completeness without changing shape requirements", () => {
  const draft = {
    schema_version: "1.0",
    adr_type: "logical",
    id: "ADR-L-0001",
    title: "Draft",
    status: "proposed",
    created_date: "2026-01-01",
    authors: ["author"],
    domains: ["architecture"],
    context: "A conceptual boundary.",
    decisions: [],
    interaction_contracts: [{
      id: "CONTRACT-0001",
      parties: ["one"],
      protocol: "documented",
      guarantees: "The boundary is explicit.",
    }],
  };
  assert.equal(validateAuthoringDocument(draft, "logical", "1.0", "complete").valid, false);
  assert.equal(validateAuthoringDocument(draft, "logical", "1.0", "structural").valid, true);
  const missingRequired = { ...draft };
  delete missingRequired.decisions;
  assert.equal(validateAuthoringDocument(missingRequired, "logical", "1.0", "structural").valid, false);
});
