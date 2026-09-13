# TypeScript Consumer Binding

`@system-of-thought/adr-kit` is the TypeScript host/browser binding governed by
Consumer Binding Contract 1.0, ADR-L-0024, and ADR-L-0027. The Node host profile
is a peer to the Python SDK for supported filesystem-backed capabilities. The
browser profile is deliberately constrained by its execution environment.

## Entry points

The root, `model`, `schemas`, and `validation` entry points are browser-safe and
framework-neutral. The `node`, `node/linkage`, `node/governance`, and
`node/materialization` entry points are explicitly
Node-only because they use filesystem, path, YAML, and cryptographic APIs.
Angular applications may use the browser-safe entry points from Angular
services or other application code, but the package does not provide Angular
modules, dependency-injection providers, zone integration, or browser-side
repository discovery.

## Version and capability rules

The binding advertises its supported capability versions through
`capabilities()`. `host_operations` identifies the parity-qualified peer-host
surface, including exact architecture materialization plus architecture and project-metadata validation, and `pending_host_operations`
makes staged migration visible.
The parity-qualified contract, project-metadata, normalized-repository identity,
provider-routing, linkage, generated-artifact classification, and normalized
architecture source-validation/reference/topology and exact architecture
materialization execute through the same packaged semantic core consumed by
Python. Filesystem discovery, path safety, source parsing, sealed request
construction, and language-native result views remain host adapter responsibilities.
Projection rendering and compilation remain staged until their semantic
dependencies are extracted through that boundary.
Unsupported normalized-model, evidence, and manifest versions fail explicitly.
Authoring discovery is now a qualified ADC 1.0 compatibility surface. Its
contract version is independent of persistence-schema and package versions;
selectors are exact and case-sensitive, and policy descriptors preserve
defined, deferred, and not-applicable status. Discovery is descriptive only:
it does not construct, compose, mutate, allocate identity, persist, or write to
repositories. The Node repository loader is index-first:
it requires the architecture index and its primary registries, validates the
primary v2.1 bundle, and treats missing additive subset registries as empty.
It does not reinterpret an older generated bundle as v2.1.

The root capability manifest advertises ADC 1.0 and `authoring.discovery`.
Both the Python SDK and the browser-safe TypeScript `./authoring` subpath
project the same canonical ADC artifact and shared conformance corpus. The
root TypeScript surface re-exports the discovery operations, while the
subpath is the explicit browser capability boundary.

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
