import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { capabilities } from "../dist/capabilities.js";
import { UnsupportedContractVersionError } from "../dist/errors.js";
import { validateContract } from "../dist/validation/index.js";

const root = resolve("../../contracts/conformance/consumer-binding-v1");
const load = async (path) => JSON.parse(await readFile(resolve(root, path), "utf8"));

test("capability discovery is local and explicit", () => {
  const manifest = capabilities();
  assert.deepEqual(manifest.supported_normalized_model_versions, ["2.1"]);
  assert.equal("supported_authoring_domain_versions" in manifest, false);
  assert.equal("preferred_authoring_domain_version" in manifest, false);
  assert.equal("authoring_capabilities" in manifest, false);
  assert.deepEqual(manifest.browser_safe_entrypoints, [".", "./model", "./schemas", "./validation"]);
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
