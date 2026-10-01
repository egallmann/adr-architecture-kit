import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import {
  constructAuthoringSet,
  validateAuthoring,
} from "../dist/node/authoring.js";
import * as node from "../dist/node/index.js";

const root = resolve("../..");
const corpus = JSON.parse(await readFile(
  resolve(root, "contracts/authoring-construction/v1.0/resources/conformance.json"),
  "utf8",
));
const accContract = JSON.parse(await readFile(
  resolve(root, "contracts/authoring-construction/v1.0/contract.json"),
  "utf8",
));

function bindMarkers(value) {
  if (typeof value === "string") return value === "$enclosing_scf" ? accContract.semanticContractFingerprint : value;
  if (Array.isArray(value)) return value.map(bindMarkers);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, bindMarkers(child)]));
  }
  return value;
}

function caseById(id) {
  return bindMarkers(corpus.cases.find((item) => item.id === id));
}

function constructionFields(result) {
  return {
    operation: result.operation,
    outcome: result.outcome,
    diagnostic_codes: result.diagnostics.map((item) => item.code),
    candidate_fragment_count: result.candidate_fragments.length,
    candidate_artifact_count: result.candidate_artifacts.length,
    construction_map_count: result.construction_map.length,
    candidate_source_available: result.candidate_source_basis !== null,
    normalized_result_available: result.normalized_result !== null,
    round_trip: {
      qualified: result.round_trip.qualified,
      comparison: result.round_trip.comparison,
    },
  };
}

function expectedConstructionFields(result) {
  return {
    operation: result.operation,
    outcome: result.outcome,
    diagnostic_codes: result.diagnostics.map((item) => item.code),
    candidate_fragment_count: result.candidate_fragments.length,
    candidate_artifact_count: result.candidate_artifacts.length,
    construction_map_count: result.construction_map.length,
    candidate_source_available: result.candidate_source_basis !== null,
    normalized_result_available: result.normalized_result !== null,
    round_trip: {
      qualified: result.round_trip.qualified,
      comparison: result.round_trip.comparison,
    },
  };
}

function validationFields(result) {
  return {
    operation: result.operation,
    validation_status: result.validation_status,
    diagnostic_codes: result.diagnostics.map((item) => item.code),
  };
}

function expectedValidationFields(result) {
  return {
    operation: result.operation,
    validation_status: result.validation_status,
    diagnostic_codes: result.diagnostics.map((item) => item.code),
  };
}

test("Node exposes the intentional public construction exports", () => {
  assert.equal(typeof node.validateAuthoring, "function");
  assert.equal(typeof node.constructAuthoringSet, "function");
});

test("Node construction preserves shared ACC outcomes and governed result material", async () => {
  for (const id of ["C01", "C32", "C33", "C41"]) {
    const current = caseById(id);
    const result = await constructAuthoringSet(current.input);
    assert.deepEqual(constructionFields(result), expectedConstructionFields(current.expected.result), id);
    assert.equal(Object.isFrozen(result), true, id);
    assert.equal(Object.isFrozen(result.candidate_artifacts), true, id);
  }
});

test("Node validation preserves the shared invalid validation case", async () => {
  const current = caseById("C27");
  const result = await validateAuthoring(current.input);
  assert.deepEqual(validationFields(result), expectedValidationFields(current.expected.result));
});

test("Node host invocation and capability failures are exceptions", async () => {
  await assert.rejects(() => validateAuthoring({}), TypeError);
  await assert.rejects(() => constructAuthoringSet({}), TypeError);
});
