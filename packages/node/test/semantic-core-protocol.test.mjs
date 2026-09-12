import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import AjvModule from "ajv/dist/2020.js";
import { semanticCoreContract } from "../dist/generated/semantic-core-contract.js";
import { semanticCoreContractV11 } from "../dist/generated/semantic-core-contract-v1.1.js";
import { validateSemanticCoreProtocol } from "../dist/node/protocol.js";
import { executeSemanticCoreRequest } from "../dist/node/core.js";

const Ajv = AjvModule.default ?? AjvModule;
const validator = new Ajv({ allErrors: true, strict: false }).compile(semanticCoreContract);
const vectorDirectory = resolve("../../contracts/semantic-core/v1.0/vectors");
const vectorDirectoryV11 = resolve("../../contracts/semantic-core/v1.1/vectors");

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
  assert.equal(v11Validator(vector.request), true, `${vector.name} request: ${JSON.stringify(v11Validator.errors)}`);
  return executeSemanticCoreRequest(vector.request).then((result) => {
    assert.equal(v11Validator(result), true, `${vector.name} result: ${JSON.stringify(v11Validator.errors)}`);
    assert.equal(result.success, vector.expected.success, vector.name);
    assert.equal(result.outcome, vector.expected.outcome, vector.name);
    if (result.outcome === "Materialized") assert.equal(normalizedValidator(result.normalizedModel), true, `${vector.name} normalized model: ${JSON.stringify(normalizedValidator.errors)}`);
    const actualDiagnosticCodes = (result.diagnostics ?? []).map((diagnostic) => diagnostic.code);
    assert.deepEqual(actualDiagnosticCodes, vector.expected.diagnostic_codes ?? [], vector.name);
    const actualCodes = {};
    for (const code of actualDiagnosticCodes) actualCodes[code] = (actualCodes[code] ?? 0) + 1;
    assert.deepEqual(actualCodes, vector.expected.diagnostic_code_counts ?? {}, vector.name);
    const assertions = vector.expected.assertions ?? {};
    if (assertions.normalized_schema_version) assert.equal(result.normalizedModel.schema_version, assertions.normalized_schema_version);
    if (assertions.source_contract_versions) assert.deepEqual(result.sourceContractClosure.map((item) => item.version), assertions.source_contract_versions);
    if (assertions.normalized_entity_type) assert.equal(result.normalizedModel.entities.some((item) => item.entity_type === assertions.normalized_entity_type), true);
    if (assertions.limitation_capability) assert.equal(result.sourceCapabilityLimitations.some((item) => item.semanticCapability === assertions.limitation_capability), true);
    if (assertions.unresolved_count !== undefined) assert.equal(result.normalizedModel.unresolved.length, assertions.unresolved_count);
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
  const normalizedAjv = new Ajv({ allErrors: true, strict: false });
  const normalizedEntity = JSON.parse(await readFile(resolve("schema/normalized-model/v2.3/normalized-entity.schema.json"), "utf8"));
  const relationshipRecord = JSON.parse(await readFile(resolve("schema/normalized-model/v2.3/relationship-record.schema.json"), "utf8"));
  const normalizedRoot = JSON.parse(await readFile(resolve("schema/normalized-model/v2.3/normalized-architecture-model.schema.json"), "utf8"));
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
        assert.deepEqual(result.normalizedModel, paired.normalizedModel, vector.name);
        assert.deepEqual(result.sourceContractClosure, paired.sourceContractClosure, vector.name);
      }
      checked += 1;
    }
  }
  assert.equal(checked >= 28, true);
});
