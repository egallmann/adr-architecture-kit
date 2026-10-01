# ADR Architecture Kit

ADR Architecture Kit helps teams keep architecture decisions as validated,
machine-readable records and gives tools a dependable way to inspect them.
Python and TypeScript/Node are peer public hosts over the same language-neutral
semantic authority. Choose the host that fits your application; the installed
capability manifest is the current source of truth for what that release supports.

## Install

Python 3.14+:

```bash
pip install adr-architecture-kit
```

TypeScript/Node 20+:

```bash
npm install @system-of-thought/adr-kit
```

## Validate an architecture repository

Both hosts can validate a project containing `PROJECT.yaml` and `adrs/`.

Python:

```python
from pathlib import Path

from adr_kit.api import ValidationRequest, capabilities, validate_architecture

project_root = Path("/absolute/path/to/project")
print(capabilities().as_dict())

result = validate_architecture(ValidationRequest(project_root, cross_references=True))
for diagnostic in result.diagnostics:
    print(diagnostic.severity, diagnostic.code, diagnostic.message)
if not result.success:
    raise SystemExit(1)
```

Node:

```js
import { capabilities } from "@system-of-thought/adr-kit";
import { validateArchitecture } from "@system-of-thought/adr-kit/node/governance";

const projectRoot = process.argv[2] ?? process.cwd();
console.log(capabilities());

const result = await validateArchitecture({
  project_root: projectRoot,
  cross_references: true,
});
for (const diagnostic of result.diagnostics) {
  console.log(diagnostic.severity, diagnostic.code, diagnostic.message);
}
process.exitCode = result.success ? 0 : 1;
```

The Python facade is `adr_kit.api`. The Node package exposes browser-safe
entry points at its root and explicit filesystem-backed Node entry points under
`@system-of-thought/adr-kit/node`. The browser profile is deliberately
constrained: it does not provide filesystem-backed repository operations and is
not a third peer filesystem host.

## Discover the installed capability surface

Do not copy a version or operation inventory into an integration. Ask the
installed package:

```python
from adr_kit.api import capabilities

manifest = capabilities()
print(manifest.package_version)
print(manifest.operations)
print(manifest.supported_authoring_domain_versions)
print(manifest.authoring_capabilities)
```

```js
import { capabilities } from "@system-of-thought/adr-kit";

const manifest = capabilities();
console.log(manifest.package_version);
console.log(manifest.host_operations);
console.log(manifest.supported_authoring_domain_versions);
console.log(manifest.authoring_capabilities);
```

Capability discovery is local and deterministic. It reports supported schema,
contract, host, and browser surfaces for the installed release. ADC 1.0
discovery is descriptive, while ACC 1.0 construction is a detached,
read-only candidate operation. Neither API persists files, mutates Git, or
writes a repository.

## Construct detached authoring candidates

Both public hosts accept the exact governed ACC 1.0 request and return the
complete Rust/WASM-produced result. The request below assumes `acc_request` and
`qualified_basis` were supplied by the consumer from the frozen ACC contract.

Python:

```python
from adr_kit.api import AuthoringRequest, construct_authoring_set

request = AuthoringRequest(
    request=acc_request,
    basis=qualified_basis,
    operation="construct_authoring_set",
)
result = construct_authoring_set(request)
print(result.outcome)
for diagnostic in result.diagnostics:
    print(diagnostic.severity, diagnostic.code)
print(result.candidate_artifacts)  # detached candidate bytes; no files are written
```

Node:

```ts
import { constructAuthoringSet } from "@system-of-thought/adr-kit/node";

const result = await constructAuthoringSet({
  contract_family: "authoring_construction",
  contract_version: "1.0",
  operation: "construct_authoring_set",
  request: accRequest,
  basis: qualifiedBasis,
});
console.log(result.outcome);
for (const diagnostic of result.diagnostics) console.log(diagnostic.severity, diagnostic.code);
console.log(result.candidate_artifacts); // detached candidate bytes; no files are written
```

`Rejected`, `Unavailable`, and `Unresolved` are returned as governed results;
host and protocol failures raise exceptions. Validation is exposed as
`validate_authoring` / `validateAuthoring` with the same request shape.

## Choose the next guide

- [Python SDK recipes](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/public-sdk.md) — validate, discover authoring contracts, inspect repositories, work with semantic contracts, and materialize an exact qualified basis.
- [Node package guide](https://github.com/egallmann/adr-architecture-kit/blob/main/packages/node/README.md) — Node usage, package entry points, browser qualification, and cross-language distribution.
- [Documentation router](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/README.md) — choose a task-oriented path for usage, authoring, contracts, or contribution.
- [Schema taxonomy](https://github.com/egallmann/adr-architecture-kit/blob/main/schema/README.md) — exact schema families and authority boundaries.
- [Public stability policy](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/public-surface-and-stability.md) — stable, provisional, and internal surfaces.

The checked-in [`examples/public-v1`](https://github.com/egallmann/adr-architecture-kit/tree/main/examples/public-v1)
tree is retained as stable ADR v1.0 compatibility evidence. It is not the
recommended modern first-use path; start with the host examples above and the
public SDK guides.

## Authority and contribution

Accepted ADRs, canonical schemas, and promoted contracts define ADR-Kit meaning.
Generated indexes and normalized models are derived views. The kit owns
authoring validation and repository-facing projections; `ste-spec` owns assigned
cross-repository contracts, `ste-runtime` owns runtime observation and evidence,
and `ste-kernel` owns admission.

For contributor and AI-first repository orientation, read the generated
[`SYSTEM-OVERVIEW.md`](https://github.com/egallmann/adr-architecture-kit/blob/main/SYSTEM-OVERVIEW.md)
and [`CONTRIBUTING.md`](https://github.com/egallmann/adr-architecture-kit/blob/main/CONTRIBUTING.md).
For authoring-time versus runtime boundaries, see
[`AUTHORING-SYSTEM.md`](https://github.com/egallmann/adr-architecture-kit/blob/main/AUTHORING-SYSTEM.md).

ADR-Kit is pre-1.0 Alpha. Python and npm packages share one release lineage;
individual operations remain governed by their compatibility contracts and
qualified host profiles.
