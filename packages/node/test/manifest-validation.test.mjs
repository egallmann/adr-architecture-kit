import test from "node:test";
import assert from "node:assert/strict";
import { validateContract } from "../dist/validation/index.js";

function baseManifest(overlays = {}) {
  return {
    schema_version: "1.0",
    type: "manifest",
    generated_date: "2026-09-05T00:00:00Z",
    generated_from: "adrs/**/*.yaml",
    adrs: [],
    statistics: {
      total_adrs: 0,
      logical_adrs: 0,
      physical_adrs: 0
    },
    gaps_summary: { total: 0, blocking: 0, by_adr: {} },
    ...overlays
  };
}

function assertAccepts(physicalId) {
  for (const overlays of [
    { by_technology: { python: [physicalId] } },
    { logical_to_physical_map: { "ADR-L-0001": [physicalId] } },
    {
      invariants: [
        {
          id: "INV-9999",
          statement: "fixture invariant",
          defined_in: "ADR-L-0001",
          enforced_by: [physicalId],
          enforcement_level: "must"
        }
      ]
    }
  ]) {
    const result = validateContract(baseManifest(overlays), "manifest:1.0");
    assert.equal(result.valid, true, `expected ${physicalId} accepted: ${JSON.stringify(result.diagnostics)}`);
  }
}

function assertRejects(physicalId) {
  for (const overlays of [
    { by_technology: { python: [physicalId] } },
    { logical_to_physical_map: { "ADR-L-0001": [physicalId] } },
    {
      invariants: [
        {
          id: "INV-9999",
          statement: "fixture invariant",
          defined_in: "ADR-L-0001",
          enforced_by: [physicalId],
          enforcement_level: "must"
        }
      ]
    }
  ]) {
    const result = validateContract(baseManifest(overlays), "manifest:1.0");
    assert.equal(result.valid, false, `expected ${physicalId} rejected`);
  }
}

test("F: ADR-PS and ADR-PC accepted in physical-only manifest slots", () => {
  assertAccepts("ADR-PS-0001");
  assertAccepts("ADR-PC-0001");
  assertAccepts("ADR-P-0001");
});

test("F: non-physical and malformed IDs rejected in physical-only slots", () => {
  assertRejects("ADR-L-0001");
  assertRejects("ADR-V-0001");
  assertRejects("ADR-D-0001");
  assertRejects("ADR-P-1");
  assertRejects("ADR-PS-1");
  assertRejects("ADR-PC-ABCD");
});
