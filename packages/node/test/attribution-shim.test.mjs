import assert from "node:assert/strict";
import test from "node:test";
import { AttributionShimError, generateAttributionShim } from "../dist/node/linkage.js";

const expected = {
  python: { length: 7043, sha256: "f73973e57552e4a1fe11d3a849c7e69d1f69efd6234dba1722143277250e8779" },
  typescript: { length: 1474, sha256: "e678b77b69c777d8e44fb063141db040e5153e36768e73da7911e9e8d4da0449" },
};

for (const language of ["python", "typescript"]) {
  test(`Node attribution shim matches the stable ${language} bytes`, async () => {
    const result = await generateAttributionShim({ language });
    assert.equal(result.success, true);
    assert.equal(result.language, language);
    assert.equal(result.content.length, expected[language].length);
    assert.equal(result.sha256, expected[language].sha256);
    assert.equal(Object.isFrozen(result), true);
  });
}

test("Node attribution shim rejects unsupported languages before execution", async () => {
  await assert.rejects(
    () => generateAttributionShim({ language: "rust" }),
    (error) => error instanceof AttributionShimError && error.code === "attribution_shim.invalid_request",
  );
});
