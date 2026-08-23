import { build } from "esbuild";
import { mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const out = resolve(packageRoot, ".browser-check");
await mkdir(out, { recursive: true });
const result = await build({ absWorkingDir: packageRoot, entryPoints: ["./dist/index.js", "./dist/model/index.js", "./dist/schemas/index.js", "./dist/validation/index.js"], bundle: true, format: "esm", platform: "browser", outdir: ".browser-check", metafile: true });
const meta = result.metafile;
const inputs = Object.keys(meta.inputs);
const forbidden = inputs.filter((input) => /(^|[\\/])node:|node_modules[\\/]yaml|node_modules[\\/]@types[\\/]node/.test(input));
if (forbidden.length) throw new Error(`Node-only dependency reached browser bundle: ${forbidden.join(", ")}`);
await rm(out, { recursive: true, force: true });
