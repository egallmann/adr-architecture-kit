import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import AjvModule from "ajv/dist/2020.js";
import { semanticCoreContract } from "../dist/generated/semantic-core-contract.js";
import { validateSemanticCoreProtocol } from "../dist/node/protocol.js";
import { executeSemanticCoreRequest } from "../dist/node/core.js";

const Ajv = AjvModule.default ?? AjvModule;
const validator = new Ajv({ allErrors: true, strict: false }).compile(semanticCoreContract);
const vectorDirectory = resolve("../../contracts/semantic-core/v1.0/vectors");

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
