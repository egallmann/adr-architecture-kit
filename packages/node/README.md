# `@system-of-thought/adr-kit`

TypeScript host and browser binding over ADR-Kit authority. The package is
framework-neutral and ESM-only; host capabilities are exposed through explicit
Node entry points and browser capabilities remain constrained.

The Node host consumes the same self-contained semantic-core WASM artifact as
the Python SDK. Rust build dependencies, including `serde` and `serde_json`,
are compiled into that artifact; the Python host additionally depends on
`wasmtime` to load it. The Python package itself is not dependency-free.

Browser-safe entry points:

```ts
import { capabilities } from "@system-of-thought/adr-kit";
import { createArchitectureModel } from "@system-of-thought/adr-kit/model";
import { validateContract } from "@system-of-thought/adr-kit/validation";
```

Node-only entry points:

```ts
import { openRepository } from "@system-of-thought/adr-kit/node";
import { buildEmbodimentLinkage, generateAttributionShim } from "@system-of-thought/adr-kit/node/linkage";
import { validateArchitecture, validateContract, validateProjectMetadata } from "@system-of-thought/adr-kit/node/governance";
```

TypeScript v1 supports normalized model 2.1, evidence attribution 1.5/1.6,
architecture discovery 1.1, canonical and compatibility relationships, and
qualified semantic extensions. Unsupported versions fail explicitly.

Browser-safe entry points do not create or mutate ADRs, allocate identity, write
repositories, admit graph records, access the network, or depend on Angular.
Node host capabilities are qualified separately against the Python host SDK.
The parity-qualified host operations are exposed in `capabilities().host_operations`;
including `validateArchitecture` and `validateProjectMetadata`; `pending_host_operations` makes the bounded
semantic-core migration visible.
Architecture, contract, project-metadata, normalized-repository identity,
provider-routing, and linkage rules execute through the packaged canonical
semantic core shared with the Python binding. Node performs only
filesystem/YAML loading and TypeScript result construction around that boundary.
Fingerprints are binding-local deterministic values; equality with Python
fingerprints is not a release gate.

`generateAttributionShim({ language: "python" | "typescript" })` is a
read-only, deterministic projection through the shared semantic core. Its
`content` and UTF-8 `sha256` are byte-compatible with the Python API and the
legacy CLI command; it does not load a repository or write a file.
