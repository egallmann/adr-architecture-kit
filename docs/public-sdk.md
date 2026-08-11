# Public Python SDK

`adr_kit.api` is the supported installed-package boundary for new Python
integrations. Its API contract version is `1.0`; the package remains pre-1.0 and
currently reports package version `0.1.0`.

## Install and discover capabilities

```bash
pip install adr-architecture-kit
```

```python
from adr_kit.api import capabilities

manifest = capabilities()
print(manifest.package_version)
print(manifest.api_contract_version)  # 1.0
print(manifest.supported_adr_schema_versions)  # ('1.0', '1.1', '1.2', '1.3')
print(manifest.normalized_model_schema_version)  # 1.1 (native default)
print(manifest.supported_normalized_model_schema_versions)  # ('1.1', '2.0')
print(manifest.as_dict())
```

Capability discovery is local and deterministic. It performs no network access,
repository discovery, validation, compilation, or writes.

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

The project root is resolved to an absolute path and must contain `PROJECT.yaml`
and `adrs/`. Validation modes are `complete` and `structural`. Schema, semantic,
and cross-reference findings are returned as immutable diagnostics; a completed
validation with errors has `success=False`. Failures that prevent the operation
from completing raise `OperationError`.

## Preview and write authoring projections

Preview is the default and performs no writes:

```python
from pathlib import Path
from adr_kit.api import CompilationRequest, compile_architecture

request = CompilationRequest(
    project_root=Path("/absolute/path/to/project"),
    artifact_groups=("registries", "manifest", "markdown"),
    timestamp="2026-01-01T00:00:00Z",
)
result = compile_architecture(request)
for artifact in result.artifacts:
    print(artifact.artifact_id, artifact.relative_path, artifact.sha256)
```

To write, set `write=True`. The default output root is the project root; an
explicit output root is permitted only for a write request:

```python
written = compile_architecture(
    CompilationRequest(
        project_root=Path("/absolute/path/to/project"),
        write=True,
        output_root=Path("/absolute/path/to/output"),
        timestamp="2026-01-01T00:00:00Z",
    )
)
```

Equivalent pinned preview and write requests return identical artifact bytes.
Descriptors are sorted by POSIX relative path and include stable IDs, content,
size, lowercase SHA-256, an absolute `written_path` only after a write, and any
integrity header supplied by the existing emitter. Writes are non-transactional.

The supported artifact groups are exactly `registries`, `manifest`, and
`markdown`. Graph output, Architecture IR, recursive workspace compilation,
compiler modes, check mode, and contract profiles remain compatibility-preserved
CLI/deep-import features; they are not part of this SDK contract.

## Open the stable repository model

```python
from pathlib import Path
from adr_kit.api import open_repository

repository = open_repository(Path("/absolute/path/to/project"))
model = repository.get_model()
print(repository.fingerprint())
print(model.entity_ids())
```

The expanded normalized model exposes `boundary`, `contract`, `interface`, and
`implementation_decision` in addition to the existing six entity types. The
repository provides explicit `get_boundaries()`, `get_contracts()`,
`get_interfaces()`, and `get_implementation_decisions()` queries. Existing
queries such as `get_decisions()` retain their previous selection semantics.

`open_repository()` eagerly loads and returns the existing
`ArchitectureRepository`. Compilation results expose a detached
`NormalizedArchitectureModel` only when registry projection succeeds. For an
equivalent written bundle, its fingerprint equals the repository fingerprint.

## Diagnostics and errors

Public result objects and diagnostics are frozen, slotted dataclasses. No
`adr_kit.compiler` object is present in public annotations or returned object
graphs.

The supported exception hierarchy is:

```text
SDKError
├── InvalidRequestError (also ValueError)
└── OperationError
    └── RepositoryError
```

Invalid roots, modes, artifact groups, timestamps, and write/output combinations
raise `InvalidRequestError` before an operation starts. Unexpected parser,
compiler, or I/O failures raise a chained `OperationError`.
`open_repository()` chains repository-loading failures as `RepositoryError`.

## Capability metadata

`capabilities()` reports supported Promotion Contract versions separately from
ADR authoring schema versions and the normalized model version. The current
provider supports:

```text
ste.design_journal.promotion_contract/v0.1
```

This Promotion Contract version is not an ADR schema version and does not
advertise ADR schema 1.3 or normalized model 2.0.

## Exact public inventory

`adr_kit.api.__all__` contains only:

```text
ArchitectureRepository, NormalizedArchitectureModel,
ArtifactDescriptor, CapabilityManifest, ValidationRequest, ValidationResult,
CompilationRequest, CompilationResult,
PromotionPrepareRequest, PromotionPrepareResult,
PromotionCheckRequest, PromotionCheckResult,
PromotionApplyRequest, PromotionApplyResult,
PromotionMutationDescriptor, PromotionBindingDescriptor,
PromotionValidationEvidenceDescriptor, PromotionBlockerDescriptor,
PromotionBaselineDescriptor, PromotionExecutionEvidenceDescriptor,
Diagnostic,
SDKError, InvalidRequestError, OperationError, RepositoryError,
capabilities, validate_architecture, compile_architecture, open_repository,
prepare_promotion, check_promotion, apply_promotion
```

Nothing is re-exported from the `adr_kit` package root except `__version__`.
Historical imports remain compatible, but new production integrations should use
this facade. See [public surface and stability](public-surface-and-stability.md),
the [promotion provider guide](promotion-provider.md), and the executable
[consumer example](../examples/public_sdk_consumer.py).

Additive API contract `1.0` symbols also include `NormalizedArchitectureModelV2`,
`ProviderRegistry`, and `open_provider_registry` for UUID-era model 2.0 / federation
lookup. Schema v1.3 and identity migration are provisional package surfaces. See
[schema v1.3](schema-v1.3.md), [identity migration](identity-v13-migration.md),
[schema v1.2](schema-v1.2.md), [external bindings](external-bindings.md), and
[topology migration](topology-identity-migration.md).
