import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { getSemanticContract, loadSemanticResource } from "../dist/node/semantic-contract.js";

const repositoryRoot = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const lifecycle = JSON.parse(
  readFileSync(
    resolve(repositoryRoot, "adrs/migrations/semantic-contract-lifecycle-classification.json"),
    "utf8",
  ),
);
const released = new Set(
  lifecycle.released_contracts.map((entry) => `${entry.family}/${entry.version}`),
);
const definitionsDirectory = resolve(repositoryRoot, "contracts/semantic-contract/v1.0/definitions");
const candidates = new Set();
for (const name of readdirSync(definitionsDirectory)) {
  if (!name.endsWith(".json")) continue;
  const value = JSON.parse(readFileSync(resolve(definitionsDirectory, name), "utf8"));
  const identity = `${value.semanticContractFamily}/${value.semanticContractVersion}`;
  if (!released.has(identity)) candidates.add(identity);
}

function canonicalCandidateResource(key) {
  const parts = key.split("/");
  const identity = `${parts[0]}/${parts[1]}`;
  const [family, version, ...rest] = parts;
  if (!rest.length || rest.some((part) => !part || part === "." || part === "..")) {
    throw new Error(`Missing bundled semantic resource: ${key}`);
  }
  if (rest.join("/") === "contract") {
    const familySource = resolve(repositoryRoot, "contracts", family, `v${version}`, "contract.json");
    if (existsSync(familySource)) {
      return JSON.parse(readFileSync(familySource, "utf8"));
    }
    const defaultName = version === "1.0" || version === "2.3" ? family : `${family}-${version}`;
    return JSON.parse(readFileSync(resolve(definitionsDirectory, `${defaultName}.json`), "utf8"));
  }
  if (rest[0] === "schema") {
    if (rest.length === 1) {
      const contractSchema = resolve(
        repositoryRoot,
        "contracts",
        family,
        `v${version}`,
        "schema.json",
      );
      if (existsSync(contractSchema)) return JSON.parse(readFileSync(contractSchema, "utf8"));
    }
    const path = resolve(repositoryRoot, "schema", family, `v${version}`, `${rest.at(-1)}.json`);
    return JSON.parse(readFileSync(path, "utf8"));
  }
  const name = rest.join("/");
  const familyResource = resolve(
    repositoryRoot,
    "contracts",
    family,
    `v${version}`,
    "resources",
    `${name}.json`,
  );
  if (existsSync(familyResource)) {
    return JSON.parse(readFileSync(familyResource, "utf8"));
  }
  const flatName = `${key.replaceAll("/", "-")}.json`;
  const flatPath = resolve(repositoryRoot, "contracts/semantic-contract/v1.0/resources", flatName);
  if (existsSync(flatPath)) {
    return JSON.parse(readFileSync(flatPath, "utf8"));
  }
  if (parts.length === 3) {
    const legacyPath = resolve(
      repositoryRoot,
      "contracts/semantic-contract/v1.0/resources",
      `${family}-${rest.at(-1)}.json`,
    );
    if (existsSync(legacyPath)) {
      const value = JSON.parse(readFileSync(legacyPath, "utf8"));
      if (value.semanticContractFamily === family && value.semanticContractVersion === version) {
        return value;
      }
    }
  }
  const missing = new Error(`Missing canonical candidate resource: ${key}`);
  missing.code = "ENOENT";
  throw missing;
}

export function getContractForQualification(family, version) {
  return candidates.has(`${family}/${version}`)
    ? canonicalCandidateResource(`${family}/${version}/contract`)
    : getSemanticContract(family, version);
}

export function getResourceForQualification(key) {
  const [family, version] = key.split("/");
  const candidate = candidates.has(`${family}/${version}`);
  if (candidate) {
    try {
      return canonicalCandidateResource(key);
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      throw new Error(`Missing canonical candidate resource: ${key}`, { cause: error });
    }
  }
  if (key.split("/").length < 3 || key.split("/").some((part) => !part || part === "." || part === "..")) {
    return loadSemanticResource(key);
  }
  try {
    return canonicalCandidateResource(key);
  } catch (error) {
    if (error.code === "ENOENT") return loadSemanticResource(key);
    throw error;
  }
}
