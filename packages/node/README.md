# `@system-of-thought/adr-kit`

Read-only TypeScript consumer binding over ADR-Kit authority. The package is
framework-neutral and ESM-only.

Browser-safe entry points:

```ts
import { capabilities } from "@system-of-thought/adr-kit";
import { createArchitectureModel } from "@system-of-thought/adr-kit/model";
import { validateContract } from "@system-of-thought/adr-kit/validation";
```

Node-only entry points:

```ts
import { openRepository } from "@system-of-thought/adr-kit/node";
import { buildEmbodimentLinkage } from "@system-of-thought/adr-kit/node/linkage";
```

TypeScript v1 supports normalized model 2.1, evidence attribution 1.5/1.6,
architecture discovery 1.1, canonical and compatibility relationships, and
qualified semantic extensions. Unsupported versions fail explicitly.

The package does not create or mutate ADRs, allocate identity, write repositories,
admit graph records, access the network, or depend on Angular. Fingerprints are
binding-local deterministic values; equality with Python fingerprints is not a
release gate.
