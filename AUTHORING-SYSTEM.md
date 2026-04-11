# Authoring system (adr-architecture-kit)

**adr-architecture-kit is an authoring-only system** for Architecture Decision Records: JSON Schema contracts, Pydantic models, parsers, validators, CLI workflows for humans, and optional human-facing generated views.

It is **not** the owner of public cross-repo schemas or of runtime/admission contracts. Public schemas live in **ste-spec**; runtime evidence is produced by **ste-runtime**; admission is emitted by **ste-kernel**.

## Guardrails

- **Do not emit authoritative machine graphs** for the runtime/kernel trust boundary from this package once the ste-runtime migration completes. Registry bundles, architecture index, and manifest intended for **runtime evidence** must be produced by **ste-runtime**, not duplicated here as a second source of truth.
- **Schema and validation** remain authoritative **for authoring correctness** (what contributors may check in).
- During migration, legacy compiler paths may remain for **golden parity** only; they must be deprecated and removed per the workspace migration plan.

## Related

- See **ste-runtime** `COMPILER-AUTHORITY.md` for the compiler-of-record boundary.

## CLI note

`adr compile` emits a **deprecation warning** (stderr) and must not be treated as the authoritative producer of runtime machine artifacts. Prefer **`ste architecture compile --project-root <repo>`** from **ste-runtime**.
