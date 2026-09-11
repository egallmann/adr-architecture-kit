import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import { executeSemanticCoreRequest } from "../dist/node/core.js";

const vectorPath = resolve("../../contracts/semantic-core/v1.0/vectors/semantic-contract-set-governance.json");

test("Node binding matches the shared semantic-contract-set governance vectors", async () => {
  const document = JSON.parse(await readFile(vectorPath, "utf8"));
  for (const testCase of document.cases) {
    const result = await executeSemanticCoreRequest(testCase.request);
    const expected = testCase.expected;
    assert.equal(result.success, expected.success, testCase.name);
    if ("noOp" in expected) assert.equal(result.noOp, expected.noOp, testCase.name);
    if ("semanticContractSetId" in expected) assert.equal(result.semanticContractSetId, expected.semanticContractSetId, testCase.name);
    if ("resolved" in expected) assert.equal(result.resolved.semanticContractSetId, expected.resolved.semanticContractSetId, testCase.name);
    if ("diagnostic_codes" in expected) assert.deepEqual(result.diagnostics.map((item) => item.code), expected.diagnostic_codes, testCase.name);
  }
});
