# Public Python SDK

`adr_kit.api` is the supported installed-package boundary for new Python
integrations. Python and TypeScript/Node are peer hosts over qualified
capabilities and consume the same semantic authority. The browser-safe
TypeScript profile is deliberately smaller because it cannot use filesystem
backed Node operations.

The facade returns immutable request, result, and diagnostic objects. It keeps
host concerns such as paths and YAML loading at the edge while the shared
semantic boundary supplies the governed meaning and validation behavior.

## Install and discover capabilities

```bash
pip install adr-architecture-kit
```

```python
from adr_kit.api import capabilities

manifest = capabilities()
print(manifest.package_version)
print(manifest.api_contract_version)
print(manifest.operations)
print(manifest.supported_adr_schema_versions)
print(manifest.supported_normalized_model_schema_versions)
print(manifest.supported_authoring_domain_versions)
print(manifest.authoring_capabilities)
```

Capability discovery is local and deterministic. It does not access the network,
discover a repository, compile, validate, or write. Treat the returned manifest
as the installed release's capability truth instead of copying version or
operation inventories into an integration.

## Validate one repository

```python
from pathlib import Path

from adr_kit.api import ValidationRequest, validate_architecture

result = validate_architecture(
    ValidationRequest(
        project_root=Path("/absolute/path/to/project"),
        mode="complete",
        cross_references=True,
    )
)
for diagnostic in result.diagnostics:
    print(diagnostic.severity, diagnostic.code, diagnostic.message)
if not result.success:
    raise SystemExit(1)
```

The project root must contain `PROJECT.yaml` and `adrs/`. `complete` and
`structural` are the supported validation modes. Schema, semantic, and
cross-reference findings are returned as immutable diagnostics. A completed
validation with errors returns `success=False`; a request or infrastructure
failure raises an SDK exception.

Use `validate_project_metadata()` when only `PROJECT.yaml` needs checking.
Use `validate_contract()` for a compiled contract bundle and
`validate_generated_docs()` for generated artifact integrity.

## Discover authoring contracts and types

ADC discovery is a descriptive, version-qualified public capability. It does
not construct, compose, mutate, allocate identity, persist, or write a
repository.

```python
from adr_kit.api import (
    describe_authoring_contract,
    describe_authoring_type,
    list_authoring_types,
)

contract = describe_authoring_contract("1.0")
types = list_authoring_types("1.0", kind="entity")
decision = describe_authoring_type("1.0", kind="entity", name="decision")

print(contract.defined_capabilities)
print([(item.key.kind, item.key.name) for item in types.types])
print(decision.input_contract.status)
```

Selectors are exact and case-sensitive. Unsupported versions, kinds, and names
raise `AuthoringDiscoveryError` with deterministic diagnostics. The ADC version
is independent of ADR persistence-schema versions; discover both through
`capabilities()` and use the [authoring contract reference](https://github.com/egallmann/adr-architecture-kit/tree/main/contracts/authoring-domain)
for exact canonical bytes.

## Work with semantic contracts

The SDK exposes the immutable semantic definitions used by both peer hosts.
They include resource manifests, conformance resources, and content identity;
they do not turn a contract definition into a lifecycle or catalog decision.

```python
from adr_kit.api import (
    get_semantic_contract,
    list_semantic_contracts,
    load_semantic_resource,
    validate_semantic_resource_closure,
)

print(list_semantic_contracts())
contract = get_semantic_contract("normative-semantics", "1.0")
resources = [
    {
        "canonicalResourceKey": item.canonical_resource_key,
        "content": load_semantic_resource(item.canonical_resource_key),
    }
    for item in contract.resource_manifest
]
assert validate_semantic_resource_closure(contract, resources).closure_valid
```

Canonicalization, fingerprinting, closure validation, and contract-set
composition are shared semantic operations. The Python and Node bindings adapt
inputs and freeze results; they do not create a second semantic authority.

## Inspect a repository model

```python
from pathlib import Path

from adr_kit.api import open_repository

repository = open_repository(Path("/absolute/path/to/project"))
model = repository.get_model()
print(repository.fingerprint())
print(model.entity_ids())
```

`open_repository()` returns the supported `ArchitectureRepository` seam. Its
normalized model is a read view of repository-owned artifacts, not an alternate
authoring source. Generated registries and manifests remain derived outputs.

## Preview or write derived projections

`compile_architecture()` previews by default. It supports the bounded artifact
groups `registries`, `manifest`, and `markdown`; it does not make graph,
Architecture IR, or runtime state into SDK write targets.

```python
from pathlib import Path

from adr_kit.api import CompilationRequest, compile_architecture

preview = compile_architecture(
    CompilationRequest(
        project_root=Path("/absolute/path/to/project"),
        timestamp="2026-01-01T00:00:00Z",
    )
)
for artifact in preview.artifacts:
    print(artifact.relative_path, artifact.sha256)
```

Set `write=True` only when the caller intends to update the selected
repository-owned projections. A pinned preview and write request produce the
same artifact bytes; writes are non-transactional. Use the CLI or contributor
guides for broader compatibility-preserved generation workflows.

## Materialize an exact qualified basis

The `materialize_architecture` operation is qualified for exact, caller-supplied
materialization requests. The caller provides the sealed source basis, source
contract closure, provider identity, and exact semantic contract-set identity;
the host does not resolve a current pointer or infer source meaning. The result
is either an immutable normalized-model result or a bounded rejection/unavailable
outcome. See the [materialization reference](https://github.com/egallmann/adr-architecture-kit/blob/main/packages/node/README.md)
for the Node request shape and host qualification.

## Work with implementation linkage

`build_embodiment_linkage()` consumes an explicit evidence file and returns
validated derived evidence. It does not write evidence, Architecture IR, or
graph state, and its result has `graph_admission_status="not_admitted"`.
Evidence attribution versions are separate from ADR authoring versions; use
`capabilities()` to discover the supported line and the [linkage guide](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/schema-v1.6.md)
for exact evidence semantics.

## Errors and stability

Invalid requests raise `InvalidRequestError`. Unexpected parser, compiler, or
I/O failures raise `OperationError`; repository-loading failures are reported as
`RepositoryError`. Public results are frozen and slotted dataclasses.

The exact Python symbol inventory is maintained by
`contracts/compatibility/python-surface.json`. This guide explains task recipes;
the compatibility contract is the precise source for inventory and shape. See
[public surface and stability](https://github.com/egallmann/adr-architecture-kit/blob/main/docs/public-surface-and-stability.md)
for compatibility categories and migration rules.
