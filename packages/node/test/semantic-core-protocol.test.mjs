import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import AjvModule from "ajv/dist/2020.js";
import Ajv7Module from "ajv";
import { semanticCoreContract } from "../dist/generated/semantic-core-contract.js";
import { semanticCoreContractV11 } from "../dist/generated/semantic-core-contract-v1.1.js";
import { validateSemanticCoreProtocol } from "../dist/node/protocol.js";
import { executeSemanticCoreRequest } from "../dist/node/core.js";

const Ajv = AjvModule.default ?? AjvModule;
const Ajv7 = Ajv7Module.default ?? Ajv7Module;
const validator = new Ajv({ allErrors: true, strict: false }).compile(semanticCoreContract);
const vectorDirectory = resolve("../../contracts/semantic-core/v1.0/vectors");
const vectorDirectoryV11 = resolve("../../contracts/semantic-core/v1.1/vectors");
const normalizedSchemaDirectoryV23 = resolve("../../schema/normalized-model/v2.3");

test("Node protocol validator accepts every valid shared vector request and result", async () => {
  let checked = 0;
  let rawOnly = 0;
  for (const name of (await (await import("node:fs/promises")).readdir(vectorDirectory)).filter((item) => item.endsWith(".json")).sort()) {
    const document = JSON.parse(await readFile(resolve(vectorDirectory, name), "utf8"));
    for (const vector of document.cases) {
      if (vector.request.core_contract_version !== "1.0") continue;
      if (vector.executionBoundary === "raw-core") {
        rawOnly += 1;
        assert.equal(validator(vector.request), false, `${name}:${vector.name} raw-core request must fail the validated schema`);
        assert.throws(
          () => validateSemanticCoreProtocol(vector.request),
          /semantic-core protocol violation/,
        );
        continue;
      }
      assert.equal(validator(vector.request), true, `${name}:${vector.name} request: ${JSON.stringify(validator.errors)}`);
      const result = await executeSemanticCoreRequest(vector.request);
      assert.equal(validator(result), true, `${name}:${vector.name} result: ${JSON.stringify(validator.errors)}`);
      checked += 1;
    }
  }
  assert.equal(checked, 42);
  assert.equal(rawOnly, 1);
});

test("Node protocol validator rejects an undeclared operation field", () => {
  const valid = validator({
    core_contract_version: "1.0",
    operation: "validate_architecture",
    mode: "complete",
    records: [],
    undeclared: true,
  });
  assert.equal(valid, false);
});

test("Node protocol routes v1.1 results to the additive contract", () => {
  const v11 = new Ajv({ allErrors: true, strict: false }).compile(semanticCoreContractV11);
  const result = {
    core_contract_version: "1.1",
    operation: "resolve_semantic_contract_set",
    success: false,
    diagnostics: [{
      severity: "error",
      code: "semantic_contract.exact_set_not_retained",
      message: "the explicitly requested SCS is not present in the retained corpus",
      path: "semanticContractSetId",
    }],
  };
  assert.equal(v11(result), true, JSON.stringify(v11.errors));
  assert.doesNotThrow(() => validateSemanticCoreProtocol(result));
});

test("Node keeps a v1.1-only operation rejected on the v1.0 boundary", async () => {
  const result = await executeSemanticCoreRequest({
    core_contract_version: "1.0",
    operation: "materialize_architecture",
  });
  assert.equal(result.core_contract_version, "1.0");
  assert.equal(result.success, false);
  assert.doesNotThrow(() => validateSemanticCoreProtocol(result));
});

test("Node executes v1.1 operations through the packaged WASM boundary", async () => {
  for (const operation of ["resolve_semantic_contract_set", "materialize_architecture"]) {
    const result = await executeSemanticCoreRequest({
      core_contract_version: "1.1",
      operation,
    });
    assert.equal(result.core_contract_version, "1.1");
    assert.equal(result.success, false);
    assert.doesNotThrow(() => validateSemanticCoreProtocol(result));
  }
});

function assertV11Vector(vector, v11Validator, normalizedValidator) {
  if (vector.executionBoundary !== "raw-core") {
    assert.equal(v11Validator(vector.request), true, `${vector.name} request: ${JSON.stringify(v11Validator.errors)}`);
  }
  return executeSemanticCoreRequest(vector.request).then((result) => {
    assert.equal(v11Validator(result), true, `${vector.name} result: ${JSON.stringify(v11Validator.errors)}`);
    assert.equal(result.success, vector.expected.success, vector.name);
    if (Object.hasOwn(vector.expected, "outcome")) assert.equal(result.outcome, vector.expected.outcome, vector.name);
    if (vector.expected.resolved) assert.equal(result.resolved?.semanticContractSetId, vector.expected.resolved.semanticContractSetId, vector.name);
    if (result.outcome === "Materialized") assert.equal(normalizedValidator(result.normalizedModel), true, `${vector.name} normalized model: ${JSON.stringify(normalizedValidator.errors)}`);
    const actualDiagnosticCodes = (result.diagnostics ?? []).map((diagnostic) => diagnostic.code);
    assert.deepEqual(actualDiagnosticCodes, vector.expected.diagnostic_codes ?? [], vector.name);
    const actualCodes = {};
    for (const code of actualDiagnosticCodes) actualCodes[code] = (actualCodes[code] ?? 0) + 1;
    assert.deepEqual(actualCodes, vector.expected.diagnostic_code_counts ?? {}, vector.name);
    assert.deepEqual((result.diagnostics ?? []).map((diagnostic) => diagnostic.message), vector.expected.diagnostic_messages ?? [], vector.name);
    assert.deepEqual((result.diagnostics ?? []).map((diagnostic) => diagnostic.path), vector.expected.diagnostic_paths ?? [], vector.name);
    assert.deepEqual((result.diagnostics ?? []).map((diagnostic) => diagnostic.severity), vector.expected.diagnostic_severities ?? [], vector.name);
    const assertions = vector.expected.assertions ?? {};
    if (assertions.normalized_schema_version) assert.equal(result.normalizedModel.schema_version, assertions.normalized_schema_version);
    if (assertions.source_contract_versions) assert.deepEqual(result.sourceContractClosure.map((item) => item.version), assertions.source_contract_versions);
    if (assertions.normalized_entity_type) assert.equal(result.normalizedModel.entities.some((item) => item.entity_type === assertions.normalized_entity_type), true);
    if (assertions.limitation_capability) assert.equal(result.sourceCapabilityLimitations.some((item) => item.semanticCapability === assertions.limitation_capability), true);
    if (assertions.unresolved_count !== undefined) assert.equal(result.normalizedModel.unresolved.length, assertions.unresolved_count);
    if (assertions.entity_ids) {
      const actualEntityIds = new Set(result.normalizedModel.entities.map((item) => item.id));
      for (const id of assertions.entity_ids) assert.equal(actualEntityIds.has(id), true, vector.name);
    }
    if (assertions.relationship_count !== undefined) assert.equal(result.normalizedModel.relationships.length, assertions.relationship_count, vector.name);
    if (assertions.relationship_type_counts) {
      const actualRelationshipTypes = {};
      for (const relationship of result.normalizedModel.relationships) {
        actualRelationshipTypes[relationship.relationship_type] = (actualRelationshipTypes[relationship.relationship_type] ?? 0) + 1;
      }
      assert.deepEqual(actualRelationshipTypes, assertions.relationship_type_counts, vector.name);
    }
    if (assertions.source_coverage_fields) {
      const actualFields = new Set(result.normalizedModel.source_coverage.physical_fields.flatMap((coverage) => coverage.fields.map((field) => field.source_field)));
      for (const field of assertions.source_coverage_fields) assert.equal(actualFields.has(field), true, vector.name);
    }
    if (assertions.closure_resource_keys_are_sorted) {
      for (const binding of result.sourceContractClosure) {
        const keys = binding.resourceClosure.map((item) => item.canonicalResourceKey);
        assert.deepEqual(keys, [...keys].sort());
      }
    }
    if (assertions.no_runtime_identity) assert.equal(JSON.stringify(result).toLowerCase().includes("runtime"), false);
    return result;
  });
}

test("Node executes the shared v1.1 materialization vector corpus", async () => {
  const v11Validator = new Ajv({ allErrors: true, strict: false }).compile(semanticCoreContractV11);
  const normalizedAjv = new Ajv7({ allErrors: true, strict: false });
  const normalizedEntity = JSON.parse(await readFile(resolve(normalizedSchemaDirectoryV23, "normalized-entity.schema.json"), "utf8"));
  const relationshipRecord = JSON.parse(await readFile(resolve(normalizedSchemaDirectoryV23, "relationship-record.schema.json"), "utf8"));
  const normalizedRoot = JSON.parse(await readFile(resolve(normalizedSchemaDirectoryV23, "normalized-architecture-model.schema.json"), "utf8"));
  for (const branch of relationshipRecord.oneOf) {
    if (branch.properties?.extension?.$ref === "normalized-entity.schema.json#/properties/extension") {
      branch.properties.extension = normalizedEntity.oneOf[0].properties.extension;
    }
  }
  normalizedAjv.addSchema(normalizedEntity);
  normalizedAjv.addSchema(relationshipRecord);
  const normalizedValidator = normalizedAjv.compile(normalizedRoot);
  let checked = 0;
  for (const name of (await (await import("node:fs/promises")).readdir(vectorDirectoryV11)).filter((item) => item.endsWith(".json")).sort()) {
    const document = JSON.parse(await readFile(resolve(vectorDirectoryV11, name), "utf8"));
    for (const vector of document.cases) {
      const result = await assertV11Vector(vector, v11Validator, normalizedValidator);
      if (vector.expected.pairedRequest) {
        const paired = await assertV11Vector({
          name: `${vector.name}:pair`,
          request: vector.expected.pairedRequest,
          expected: { success: true, outcome: "Materialized", diagnostic_code_counts: {} },
        }, v11Validator, normalizedValidator);
        const pairedAssertions = vector.expected.pairedAssertions ?? {};
        if (pairedAssertions.same_normalized_model) assert.deepEqual(result.normalizedModel, paired.normalizedModel, vector.name);
        if (pairedAssertions.same_source_contract_closure) assert.deepEqual(result.sourceContractClosure, paired.sourceContractClosure, vector.name);
        if (pairedAssertions.same_authority_state_fingerprint) assert.equal(result.semanticBasis.authorityStateFingerprint, paired.semanticBasis.authorityStateFingerprint, vector.name);
        if (pairedAssertions.different_authority_state_fingerprint) assert.notEqual(result.semanticBasis.authorityStateFingerprint, paired.semanticBasis.authorityStateFingerprint, vector.name);
      }
      checked += 1;
    }
  }
  assert.equal(checked >= 50, true);
});

async function canonicalAuthoringValidation(source) {
  const schemaDirectory = resolve("../../schema/authoring", `v${source.schema_version}`);
  const names = (await (await import("node:fs/promises")).readdir(schemaDirectory)).filter((name) => name.endsWith(".schema.json")).sort();
  const ajv = new Ajv7({ allErrors: true, strict: false });
  const resources = [];
  for (const name of names) resources.push(JSON.parse(await readFile(resolve(schemaDirectory, name), "utf8")));
  for (const resource of resources) if (resource.$id) ajv.addSchema(resource);
  const topLevel = resources.find((resource) => resource.$id?.endsWith(`adr-${source.adr_type}.schema.json`));
  assert.ok(topLevel, `missing canonical schema for ${source.adr_type}`);
  const validate = ajv.getSchema(topLevel.$id) ?? ajv.compile(topLevel);
  return validate(source);
}

test("Node source validation differentially agrees with the canonical authoring schemas", async () => {
  for (const name of (await (await import("node:fs/promises")).readdir(vectorDirectoryV11)).filter((item) => item.endsWith(".json")).sort()) {
    const document = JSON.parse(await readFile(resolve(vectorDirectoryV11, name), "utf8"));
    for (const vector of document.cases) {
      const artifacts = vector.request.sourceBasis?.artifacts;
      if (!Array.isArray(artifacts)) continue;
      const canonicalValid = [];
      for (const artifact of artifacts) canonicalValid.push(await canonicalAuthoringValidation(artifact.document));
      const result = await executeSemanticCoreRequest(vector.request);
      if (canonicalValid.some((valid) => !valid)) {
        assert.equal(vector.expected.success, false, vector.name);
        assert.equal(result.outcome, "Rejected", vector.name);
      } else if (vector.expected.outcome === "Materialized") {
        assert.equal(result.success, true, vector.name);
      }
    }
  }
});
