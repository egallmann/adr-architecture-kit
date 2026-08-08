# Phase 1 public surface inventory

Phase 1 adds one supported module, `adr_kit.api`, without removing, moving, or
deprecating any Phase 0 import. The package root remains version-only.

| Category | Supported symbols |
|---|---|
| Existing semantic seam | `ArchitectureRepository`, `NormalizedArchitectureModel` |
| Immutable requests/results | `ValidationRequest`, `ValidationResult`, `CompilationRequest`, `CompilationResult` |
| Immutable value objects | `ArtifactDescriptor`, `CapabilityManifest`, `Diagnostic` |
| Exceptions | `SDKError`, `InvalidRequestError`, `OperationError`, `RepositoryError` |
| Operations | `capabilities`, `validate_architecture`, `compile_architecture`, `open_repository` |

The API contract version is `1.0`. Compilation is intentionally restricted to
repository-owned authoring groups: `registries`, `manifest`, and `markdown`.
Compiler IR, graph output, recursive compilation, compiler modes, check mode,
contract profiles, raw parsers, filesystem loaders, and runtime evidence are
excluded.

Compatibility evidence:

- public inventory and annotations are executable contracts;
- returned object graphs are recursively checked for compiler-type leakage;
- the Phase 0 Python snapshot preserves every historical import and adds the new
  module without deletion;
- the CLI surface and a 16-case behavior/byte snapshot remain unchanged;
- source, editable, and retained-wheel consumers exercise the same facade;
- runtime, CLI, installed metadata, capability, and result versions agree.
