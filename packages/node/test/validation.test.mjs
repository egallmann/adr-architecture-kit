import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { capabilities } from "../dist/capabilities.js";
import { UnsupportedContractVersionError } from "../dist/errors.js";
import { validateAuthoringDocument, validateContract } from "../dist/validation/index.js";
import { schemaManifest } from "../dist/schemas/index.js";
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
  assert.deepEqual(manifest.supported_adr_schema_versions, ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"]);
  assert.deepEqual(manifest.stable_adr_schema_versions, ["1.0"]);
  assert.deepEqual(manifest.provisional_adr_schema_versions, ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"]);
  assert.deepEqual(manifest.supported_normalized_model_versions, ["2.1", "2.2", "2.3", "2.4"]);
  assert.deepEqual(manifest.host_operations, ["capabilities", "validate_authoring", "construct_authoring_set", "validate_architecture", "validate_project_metadata", "validate_contract", "open_repository", "open_provider_registry", "build_embodiment_linkage", "generate_attribution_shim", "materialize_architecture", "list_semantic_contracts", "get_semantic_contract", "canonicalize_semantic_json", "calculate_semantic_contract_fingerprint", "verify_semantic_contract", "validate_semantic_resource_closure", "compose_semantic_contract_set", "list_semantic_contract_profiles", "get_semantic_contract_profile", "validate_semantic_contract_profile", "validate_semantic_contract_qualification", "preview_semantic_contract_set_assembly", "apply_semantic_contract_set_assembly", "validate_semantic_contract_corpus", "list_semantic_contract_sets", "resolve_current_semantic_contract_set"]);
  assert.ok(manifest.pending_host_operations.includes("compile_architecture"));
  assert.deepEqual(manifest.browser_operations, ["capabilities", "describe_contract", "list_types", "describe_type"]);
  assert.deepEqual(manifest.supported_authoring_domain_versions, ["1.0"]);
  assert.equal(manifest.preferred_authoring_domain_version, "1.0");
  assert.deepEqual(manifest.authoring_capabilities, ["authoring.discovery"]);
  assert.deepEqual(manifest.browser_safe_entrypoints, [".", "./model", "./schemas", "./validation", "./authoring"]);
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
    validate_authoring: node.validateAuthoring,
    construct_authoring_set: node.constructAuthoringSet,
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

test("normalized model 2.4 and its registries validate from packaged canonical schemas", () => {
  const id = "019109a0-b1c2-7def-8a00-112233445566";
  const relationshipId = "019109a0-b1c2-7def-8a00-223344556677";
  const entity = {
    id,
    alias_id: "SYS-0001",
    alias_name: "platform-system",
    alias_ref: "SYS-0001:platform-system",
    entity_type: "system",
    name: "Platform system",
    summary: "A platform system.",
    uri: `adr://kit/entities/${id}`,
    created_at: "2026-09-27T00:00:00Z",
    entity_fingerprint: `sha256:${"0".repeat(64)}`,
    lifecycle_stage: "active",
    canonical_source: { source_type: "test", source_ref: "test#system" },
    completeness: { status: "complete" },
    provenance: { source_type: "test", source_ref: "test#system" },
  };
  const relationship = {
    record_kind: "canonical",
    id: relationshipId,
    alias_id: "REL-0001",
    alias_name: "platform-calls-platform",
    relationship_type: "calls",
    from_entity_id: id,
    to_entity_id: relationshipId,
    canonical_source_ref: "test#relationship",
  };
  const root = {
    schema_version: "2.4",
    type: "normalized_architecture_model",
    mode: "normalized",
    scope_root: "test",
    fingerprint: `sha256:${"1".repeat(64)}`,
    entities: [entity],
    relationships: [relationship],
    unresolved: [{ code: "missing-source", message: "Source is unavailable." }],
  };
  assert.equal(validateContract(root, "normalized-model:2.4").valid, true);
  assert.equal(validateContract({ schema_version: "2.4", type: "normalized_entity_registry", entities: [entity] }, "normalized-entity-registry:2.4").valid, true);
  assert.equal(validateContract({ schema_version: "2.4", type: "relationship_registry", relationships: [relationship] }, "relationship-registry:2.4").valid, true);
  assert.equal(validateContract({ schema_version: "2.4", type: "unresolved_registry", unresolved: [{ code: "missing-source", message: "Source is unavailable." }] }, "unresolved-registry:2.4").valid, true);
  assert.equal(validateContract({ ...root, schema_version: "2.3" }, "normalized-model:2.4").valid, false);
  assert.equal(validateContract({ schema_version: "2.4", type: "unresolved_registry", unresolved: [{ code: "Bad Code", message: "bad" }] }, "unresolved-registry:2.4").valid, false);
});

test("Node v2.4 schema manifest preserves canonical source bytes", async () => {
  const names = [
    "normalized-architecture-model.schema.json",
    "normalized-entity-registry.schema.json",
    "normalized-entity.schema.json",
    "relationship-record.schema.json",
    "relationship-registry.schema.json",
    "unresolved-registry.schema.json",
  ];
  for (const name of names) {
    const bytes = await readFile(resolve("../../schema/normalized-model/v2.4", name));
    const entry = schemaManifest.schemas.find((item) => item.path === `normalized-model/v2.4/${name}`);
    assert.ok(entry, name);
    assert.equal(entry.sha256, `sha256:${createHash("sha256").update(bytes).digest("hex")}`, name);
  }
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

test("authoring v1.7 validates through the packaged canonical schema", () => {
  const document = {
    schema_version: "1.7",
    adr_type: "logical",
    id: "01940000-0000-7000-8000-000000000001",
    alias_id: "ADR-L-0001",
    alias_name: "authoring-v17",
    title: "Authoring v1.7 contract",
    status: "accepted",
    created_date: "2026-01-01",
    authors: ["test"],
    context: "A complete v1.7 logical document.",
    decisions: [{
      id: "01940000-0000-7000-8000-000000000002",
      alias_id: "DEC-0001",
      alias_name: "choose-v17",
      summary: "Use authoring v1.7",
      rationale: "The accepted ACC source contract requires it.",
    }],
  };
  assert.equal(validateAuthoringDocument(document, "logical", "1.7").valid, true);
});

test("authoring v1.7 resolves cross-file decision references in Node", () => {
  const logical = {
    schema_version: "1.7",
    adr_type: "logical",
    id: "01940000-0000-7000-8000-000000000001",
    alias_id: "ADR-L-0001",
    alias_name: "authoring-v17",
    title: "Authoring v1.7 contract",
    status: "accepted",
    created_date: "2026-01-01",
    authors: ["test"],
    context: "A complete v1.7 logical document.",
    decisions: [{
      id: "01940000-0000-7000-8000-000000000002",
      alias_id: "DEC-0001",
      alias_name: "choose-v17",
      summary: "Use authoring v1.7",
      rationale: "The accepted ACC source contract requires it.",
      alternatives_considered: [{ name: "Authoring v1.6", rejected_because: "The accepted source contract is v1.7." }],
      consequences: { positive: ["The source contract is explicit."], negative: ["Consumers resolve v1.7."] },
    }],
  };
  const physical = {
    schema_version: "1.7",
    adr_type: "physical-component",
    id: "01940000-0000-7000-8000-000000000011",
    alias_id: "ADR-PC-0001",
    alias_name: "authoring-v17-component",
    title: "Authoring v1.7 component",
    status: "accepted",
    created_date: "2026-01-01",
    authors: ["test"],
    implements_logical: ["01940000-0000-7000-8000-000000000001"],
    implements_system: ["01940000-0000-7000-8000-000000000003"],
    context: "A complete v1.7 physical component document.",
    technology_stack: [{ category: "framework", name: "Test", version: "1", rationale: "Test fixture." }],
    component_specifications: [{
      id: "01940000-0000-7000-8000-000000000012",
      alias_id: "COMP-0001",
      alias_name: "test-component",
      name: "Test component",
      type: "service",
      responsibilities: "Validates authoring v1.7.",
      generation_context: { purpose: "Test", key_responsibilities: ["Validate"] },
      interfaces: [{ id: "01940000-0000-7000-8000-000000000013", alias_id: "IFACE-0001", alias_name: "test-interface", type: "REST", specification: "Test interface." }],
    }],
    implementation_decisions: [{
      id: "01940000-0000-7000-8000-000000000014",
      alias_id: "IMPL-0001",
      alias_name: "choose-v17",
      summary: "Use the v1.7 schema.",
      rationale: "It is the accepted source contract.",
      alternatives_considered: [{ name: "An older schema", rejected_because: "It lacks the accepted contract." }],
    }],
  };
  assert.equal(validateAuthoringDocument(logical, "logical", "1.7").valid, true);
  assert.equal(validateAuthoringDocument(physical, "physical-component", "1.7").valid, true);
  assert.equal(validateAuthoringDocument({ ...logical, decisions: [{ ...logical.decisions[0], consequences: { positive: [7] } }] }, "logical", "1.7").valid, false);
  assert.equal(validateAuthoringDocument({ ...physical, implementation_decisions: [{ ...physical.implementation_decisions[0], alternatives_considered: [{ name: 7, rejected_because: "bad" }] }] }, "physical-component", "1.7").valid, false);
});
