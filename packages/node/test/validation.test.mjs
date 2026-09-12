import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { capabilities } from "../dist/capabilities.js";
import { UnsupportedContractVersionError } from "../dist/errors.js";
import { validateAuthoringDocument, validateContract } from "../dist/validation/index.js";
import * as node from "../dist/node/index.js";
import { buildEmbodimentLinkage, generateAttributionShim } from "../dist/node/linkage.js";
import { materializeArchitecture } from "../dist/node/materialization.js";
import * as nodeGovernance from "../dist/node/governance.js";

const root = resolve("../../contracts/conformance/consumer-binding-v1");
const hostCapabilityContract = JSON.parse(
  await readFile(resolve("../../contracts/compatibility/host-capabilities.json"), "utf8"),
);
const load = async (path) => JSON.parse(await readFile(resolve(root, path), "utf8"));

test("capability discovery is local and explicit", () => {
  const manifest = capabilities();
  assert.deepEqual(manifest.supported_normalized_model_versions, ["2.1", "2.2", "2.3"]);
  assert.deepEqual(manifest.host_operations, ["capabilities", "validate_architecture", "validate_project_metadata", "validate_contract", "open_repository", "open_provider_registry", "build_embodiment_linkage", "generate_attribution_shim", "materialize_architecture", "list_semantic_contracts", "get_semantic_contract", "canonicalize_semantic_json", "calculate_semantic_contract_fingerprint", "verify_semantic_contract", "validate_semantic_resource_closure", "compose_semantic_contract_set", "list_semantic_contract_profiles", "get_semantic_contract_profile", "validate_semantic_contract_profile", "validate_semantic_contract_qualification", "preview_semantic_contract_set_assembly", "apply_semantic_contract_set_assembly", "validate_semantic_contract_corpus", "list_semantic_contract_sets", "resolve_current_semantic_contract_set"]);
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
    generate_attribution_shim: generateAttributionShim,
    materialize_architecture: materializeArchitecture,
    list_semantic_contracts: node.listSemanticContracts,
    get_semantic_contract: node.getSemanticContract,
    canonicalize_semantic_json: node.canonicalizeSemanticJson,
    calculate_semantic_contract_fingerprint: node.calculateSemanticContractFingerprint,
    verify_semantic_contract: node.verifySemanticContract,
    validate_semantic_resource_closure: node.validateSemanticResourceClosure,
    compose_semantic_contract_set: node.composeSemanticContractSet,
    list_semantic_contract_profiles: node.listSemanticContractProfiles,
    get_semantic_contract_profile: node.getSemanticContractProfile,
    validate_semantic_contract_profile: node.validateSemanticContractProfile,
    validate_semantic_contract_qualification: node.validateSemanticContractQualification,
    preview_semantic_contract_set_assembly: node.previewSemanticContractSetAssembly,
    apply_semantic_contract_set_assembly: node.applySemanticContractSetAssembly,
    validate_semantic_contract_corpus: node.validateSemanticContractCorpus,
    list_semantic_contract_sets: node.listSemanticContractSets,
    resolve_current_semantic_contract_set: node.resolveCurrentSemanticContractSet,
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

test("normalized model 2.3 accepts the lifecycle-free NP variant", () => {
  const id = "019109a0-b1c2-7def-8a00-112233445566";
  const np = {
    id,
    alias_id: "NP-0001",
    alias_name: "explicit-contract",
    alias_ref: "NP-0001:explicit-contract",
    entity_type: "normative_proposition",
    name: "The contract MUST remain explicit.",
    summary: "The contract MUST remain explicit.",
    uri: `adr://kit/entities/${id}`,
    created_at: "2026-08-28T00:00:00Z",
    entity_fingerprint: `sha256:${"0".repeat(64)}`,
    statement: "The contract MUST remain explicit.",
    normative_force: "MUST",
    scope: "global",
    declaring_adr: { provider: "adr-kit", id, alias_id: "ADR-L-0001", alias_name: "normative-authority" },
    source_artifact: { source_type: "logical_adr", source_ref: "adr#np", artifact_path: "adrs/logical/ADR-L-0001.yaml", content_digest: `sha256:${"1".repeat(64)}` },
    source_contract: { family: "authoring", version: "1.6", fingerprint: `sha256:${"2".repeat(64)}` },
    canonical_source: { source_type: "logical_adr", source_ref: "adr#np", artifact_path: "adrs/logical/ADR-L-0001.yaml" },
    completeness: { status: "complete", missing_fields: [] },
    provenance: { source_type: "authoring", source_ref: "1.6", extraction_phase: "projection", classification: "explicit", generator: "test" },
  };
  const registry = { schema_version: "2.3", type: "normalized_entity_registry", entities: [np] };
  assert.equal(validateContract(registry, "normalized-entity-registry:2.3").valid, true);
  assert.equal(validateContract({ ...np, lifecycle_stage: "active" }, "normalized-entity-registry:2.3").valid, false);
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
