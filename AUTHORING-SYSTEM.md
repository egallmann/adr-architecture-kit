# Authoring system (adr-architecture-kit)

**adr-architecture-kit is an authoring-only system** for Architecture Decision Records: JSON Schema contracts, Pydantic models, parsers, validators, CLI workflows for humans, and optional human-facing generated views.

It is **not** the owner of public cross-repo schemas or of runtime/admission contracts. Public schemas live in **ste-spec**; runtime evidence is produced by **ste-runtime**; admission is emitted by **ste-kernel**.

## Guardrails

- **ADR Kit is the sole writer of its repository tree.** External runtime and workspace systems may read supported ADR Kit contracts, but they must never create, replace, or update files anywhere inside this repository.
- **Runtime-derived state is workspace state.** Runtime graphs, evidence, registries, manifests, and other derived runtime outputs belong beneath the workspace-root `.ste-workspace/` directory, outside every repository tree.
- **Do not emit authoritative runtime evidence** from this package. ADR Kit's repository-local registries, architecture index, manifest, and rendered views are authoring projections governed by this repository; they are not runtime workspace state.
- **Schema and validation** remain authoritative **for authoring correctness** (what contributors may check in).
- During migration, legacy compiler paths may remain for **golden parity** only; they must be deprecated and removed per the workspace migration plan.
- New Python consumers use the bounded `adr_kit.api` authoring facade. Its compile
  operation emits only repository-owned `registries`, `manifest`, and `markdown`
  projections; it does not expose graph, Architecture IR, recursive runtime, or
  workspace-state capabilities.

## Related

- See **ste-runtime** `COMPILER-AUTHORITY.md` for the compiler-of-record boundary.

## CLI note

`adr compile` emits a **deprecation warning** (stderr) for runtime use. Within this repository it remains an authoring compatibility path for deterministic, repository-owned projections. Runtime tooling must use workspace-aware output beneath `.ste-workspace/` and must never target this repository as an output directory.
