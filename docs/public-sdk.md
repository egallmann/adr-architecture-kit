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

## Exact public inventory

`adr_kit.api.__all__` contains only:

```text
ArchitectureRepository, NormalizedArchitectureModel,
ArtifactDescriptor, CapabilityManifest, ValidationRequest, ValidationResult,
CompilationRequest, CompilationResult, Diagnostic,
SDKError, InvalidRequestError, OperationError, RepositoryError,
capabilities, validate_architecture, compile_architecture, open_repository
```

Nothing is re-exported from the `adr_kit` package root except `__version__`.
Historical imports remain compatible, but new production integrations should use
this facade. See [public surface and stability](public-surface-and-stability.md)
and the executable [consumer example](../examples/public_sdk_consumer.py).
