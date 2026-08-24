import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, writeFile, cp } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(packageRoot, "../..");
const canonicalRoot = resolve(repoRoot, "schema");
const generatedRoot = resolve(packageRoot, "src/generated");

const families = [
  ["normalized-model", "v2.1"],
  ["evidence-attribution", "v1.5"],
  ["evidence-attribution", "v1.6"],
  ["architecture-discovery", "v1.1"],
  ["v1.0", null]
];

const assets = {};
const canonicalBytes = {};
for (const [family, version] of families) {
  const source = version ? resolve(canonicalRoot, family, version) : resolve(canonicalRoot, family);
  const target = version ? resolve(generatedRoot, "schemas", family, version) : resolve(generatedRoot, "schemas", family);
  await mkdir(target, { recursive: true });
  for (const name of await readdir(source)) {
    if (!name.endsWith(".json")) continue;
    const sourcePath = resolve(source, name);
    const bytes = await readFile(sourcePath);
    const targetPath = resolve(target, name);
    await writeFile(targetPath, bytes);
    const key = version ? `${family}/${version}/${name}` : `${family}/${name}`;
    assets[key] = JSON.parse(bytes.toString("utf8"));
    canonicalBytes[key] = bytes;
  }
}

const packageJson = JSON.parse(await readFile(resolve(packageRoot, "package.json"), "utf8"));
const pyproject = await readFile(resolve(repoRoot, "pyproject.toml"), "utf8");
const packageVersion = pyproject.match(/^version\s*=\s*"([^"]+)"/m)?.[1];
if (!packageVersion) throw new Error("pyproject.toml package version is unavailable");
if (packageJson.version !== packageVersion) throw new Error(`package.json version ${packageJson.version} does not match pyproject.toml ${packageVersion}`);
const manifest = Object.entries(assets).sort(([left], [right]) => left.localeCompare(right)).map(([path, schema]) => ({
  path,
  family: path.split("/")[0],
  version: path.split("/")[1]?.match(/^v\d/)?.[0] ?? null,
  sha256: `sha256:${createHash("sha256").update(canonicalBytes[path]).digest("hex")}`
}));

await mkdir(generatedRoot, { recursive: true });
await writeFile(resolve(generatedRoot, "schema-manifest.ts"), `export const schemaManifest = ${JSON.stringify({ package_version: packageVersion, schemas: manifest }, null, 2)} as const;\n`);
await writeFile(resolve(generatedRoot, "package-metadata.ts"), `export const packageVersion = ${JSON.stringify(packageVersion)} as const;\n`);
await writeFile(resolve(generatedRoot, "schema-assets.ts"), `export const schemaAssets = ${JSON.stringify(assets, null, 2)} as const;\n`);
