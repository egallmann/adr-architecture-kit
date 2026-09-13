# `@system-of-thought/adr-kit`

The official TypeScript/Node binding for ADR-Kit. Node and Python are peer
hosts over common semantic authority; this package is not a wrapper around a
Python runtime. The package is ESM-only and requires Node 20 or newer.

## Install

```bash
npm install @system-of-thought/adr-kit
```

## Validate a repository

The Node host reads a local project containing `PROJECT.yaml` and `adrs/`, then
returns immutable result data and diagnostics.

```js
import { capabilities } from "@system-of-thought/adr-kit";
import { validateArchitecture } from "@system-of-thought/adr-kit/node/governance";

const projectRoot = process.argv[2] ?? process.cwd();
console.log(capabilities());

const result = await validateArchitecture({
  project_root: projectRoot,
  mode: "complete",
  cross_references: true,
});
for (const diagnostic of result.diagnostics) {
  console.log(diagnostic.severity, diagnostic.code, diagnostic.message);
}
process.exitCode = result.success ? 0 : 1;
```

Other filesystem-backed Node operations are exposed from explicit entry points:

```ts
import { openRepository } from "@system-of-thought/adr-kit/node";
import { validateContract, validateProjectMetadata } from "@system-of-thought/adr-kit/node/governance";
import { materializeArchitecture } from "@system-of-thought/adr-kit/node/materialization";
import { buildEmbodimentLinkage } from "@system-of-thought/adr-kit/node/linkage";
```

## Discover capabilities and authoring contracts

Ask the installed package for its exact current surface:

```ts
import { capabilities } from "@system-of-thought/adr-kit";
import { describeContract, listTypes } from "@system-of-thought/adr-kit/authoring";

const manifest = capabilities();
console.log(manifest.package_version);
console.log(manifest.host_operations);
console.log(manifest.supported_authoring_domain_versions);
console.log(manifest.authoring_capabilities);

const contract = describeContract("1.0");
const entities = listTypes("1.0", "entity");
console.log(contract.definedCapabilities);
console.log(entities.types.map((item) => item.key));
```

ADC 1.0 discovery is descriptive and exact: it lists and describes the
contract's types and policies. It does not construct, compose, mutate, allocate
identity, persist, or write repositories. The ADC version is independent of
ADR persistence-schema versions.

## Browser-safe versus Node entry points

The root, `model`, `schemas`, `validation`, and `authoring` entry points are
browser-safe and framework-neutral. They do not access the filesystem, network,
repository state, or Node-only loaders.

The `node`, `node/governance`, `node/linkage`, `node/materialization`, and
`node/semantic-contract` entry points are explicitly Node-only. Browser-safe
TypeScript is a deliberately constrained execution profile, not a third peer
filesystem host. Use `capabilities().browser_operations` and
`capabilities().node_entrypoints` for the installed qualification.

## Semantic contracts and exact materialization

The binding exposes the same semantic-contract families and canonical operations
as the Python public seam. It also exposes qualified architecture materialization
through `materializeArchitecture`. Materialization requires an exact semantic
contract-set identity and a sealed, caller-supplied source basis; it does not
resolve current pointers or infer source meaning. Results are normalized-model
outputs or bounded rejection/unavailable outcomes.

Shared semantic-core execution is an implementation detail below these public
seams. The package includes its self-contained WASM artifact; consumers do not
need Rust, serde, Wasmtime, or compiler knowledge to use the supported APIs.

## Qualification from this directory

```bash
npm run typecheck
npm test
npm run browser:check
npm run pack:check
```

The build packages canonical schema mirrors and the semantic-core artifact. The
Node package version follows the Python release lineage. Unsupported contract
versions fail explicitly, and overlapping Python/Node capabilities are checked
through the repository's conformance tests.
