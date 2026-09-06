# TypeScript Consumer Binding

`@system-of-thought/adr-kit` is the read-only TypeScript binding governed by
Consumer Binding Contract 1.0 and ADR-L-0024. It consumes the repository's
canonical schemas and normalized Architecture Model 2.1; it does not create
ADRs, allocate identity, write repository artifacts, or admit graph records.

## Entry points

The root, `model`, `schemas`, and `validation` entry points are browser-safe and
framework-neutral. The `node` and `node/linkage` entry points are explicitly
Node-only because they use filesystem, path, YAML, and cryptographic APIs.
Angular applications may use the browser-safe entry points from Angular
services or other application code, but the package does not provide Angular
modules, dependency-injection providers, zone integration, or browser-side
repository discovery.

## Version and capability rules

The binding advertises its supported capability versions through
`capabilities()`. Unsupported normalized-model, evidence, and manifest
versions fail explicitly. Authoring discovery remains a planned compatibility
surface until its operations are implemented and qualified. The Node repository loader is index-first:
it requires the architecture index and its primary registries, validates the
primary v2.1 bundle, and treats missing additive subset registries as empty.
It does not reinterpret an older generated bundle as v2.1.

The root capability manifest does not yet advertise ADC 1.0 or
`authoring.discovery` because the discovery operations are not implemented by
this binding. The browser-safe `./authoring` subpath and its
`describeContract`, `listTypes`, and `describeType` operations remain promoted
as planned compatibility authority, with status `promoted_authority_not_implemented`.
After implementation and qualification, those ADC version and capability
fields belong on the root capability surface.

Semantic attribution linkage accepts evidence v1.5 and v1.6 under their
version-specific vocabulary and confidence rules. Results are validated
derived evidence with `graph_admission_status: "not_admitted"`; linkage is
never persisted by this package.

Binding fingerprints are deterministic within the TypeScript binding. They are
not required to equal Python fingerprints; cross-language qualification is
structural, semantic, behavioral, and diagnostic for overlapping capabilities.

## Qualification

From `packages/node`, run:

```text
npm run typecheck
npm test
npm run browser:check
npm run pack:check
```

The build copies canonical schema bytes into the package and records their
SHA-256 manifest. The package version must match the repository version in
`pyproject.toml`.

The governance workflow runs these Node, browser, packaging, and overlapping
Consumer Binding Contract conformance gates alongside the existing Python and
governance gates. Release qualification builds the npm tarball once and
retains it with the Python release bundle. The tag-only npm promotion workflow
publishes that retained tarball through npm Trusted Publishing after resolving
the successful `main` qualification; it does not rebuild or publish from
`develop`.
