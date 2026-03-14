# ADR Architecture Kit - Roadmap

**Last Updated**: 2026-03-14

## Summary

adr-architecture-kit has moved from a generator-oriented ADR toolkit into an
explicit architecture compiler with contract-aware governance. The current
roadmap is no longer centered on prompt translation or decorator-first
automation. The near-term focus is finishing compiler/governance integration,
stabilizing the kernel-facing contract surface, and preparing cleanly for
federation and qualified multi-repository identity.

This roadmap is a manual planning/orientation document. It is not a generated
artifact.

## Completed Foundations

### Canonical ADR and governance system

- Structured ADR and invariant models with schema validation
- Scope-aware ADR architecture with explicit project root resolution
- Deterministic manifest generation and rendered ADR markdown generation
- Generated-artifact integrity validation for manifest, rendered ADRs,
  `SYSTEM-OVERVIEW.md`, and the legacy compatibility registry
- Meaningful-boundary commit governance formalized as an invariant

### Compiler and contract foundations

- Unified compiler driver with `adr compile`
- Explicit discovery compiler pipeline over parse, normalization, extraction,
  inference, unresolved detection, validation, and emission
- Fixed-order compiler pass runner over extracted compiler steps
- Compiler-owned registry bundle assembly from `ArchModel`
- Compiler-authoritative emission of normalized registries, subset registries,
  legacy compatibility registry, manifest, and rendered ADR markdown
- Additive architecture graph emission from the compiler IR without changing current registry authority
- Public compile modes: `normal`, `strict`, `lenient`
- Recursive multi-scope compilation through `adr compile --recursive`

### Kernel contract and migration governance

- Four-file kernel contract surface
- Profile-aware contract validation for `greenfield`, `brownfield`, and `migration`
- `sentinel_compliant` enforcement semantics
- Metadata schema baseline and remediation-ledger enforcement
- Monotonic sentinel remediation and production-safe kernel admission rules

### New canonicalized design guarantees

- Deterministic, contract-valid registry projection
- Scope-isolated recursive compilation
- Federation authority and qualified identity model formalized in ADR form

## Current Focus

### 1. Recursive governance integration

Goal: make workspace-level governance use the same scope-aware model as the
compiler while preserving per-scope isolation.

In progress:

- Recursive `adr governance-checks`
- Recursive contract validation
- Recursive project metadata validation
- Root-scoped test execution with per-scope validation reporting

Success criteria:

- `adr governance-checks --recursive` validates all detected scopes
- Per-scope failures are explicit and deterministic
- No cross-scope merged validation bundle is introduced

### 2. Compiler-governance convergence

Goal: make the compiler path the authoritative operational surface, with
governance layered on top rather than parallel to it.

Next steps:

- Keep legacy validation paths only where they are still the right abstraction
- Keep compatibility wrappers thin while the explicit compiler pipeline owns
  discovery orchestration
- Align contributor docs with compiler-backed workflows
- Reduce remaining split-brain behavior between older command shapes and the
  compiler/governance surface

Success criteria:

- Local workflow guidance points to `adr compile`, `adr governance-checks`,
  and explicit validation commands without contradiction
- Recursive and single-scope flows behave consistently

### 3. Federation preparation

Goal: prepare for multi-repository architecture reasoning without collapsing
repository authority boundaries.

Next steps:

- Turn qualified identity and federation authority decisions into implementation
  work only after compiler and governance surfaces are stable
- Keep federation read-only over per-repo canonical registries
- Preserve local bare-ID ergonomics while enabling qualified cross-repo identity

Success criteria:

- Federation work starts from canonical ADR and invariant authority already in place
- No ad hoc cross-repo identity rules leak into compiler code first

## Deferred Work

These remain valid future directions, but they are no longer the active roadmap
for this repository right now.

### Prompt translation and implementation-prompt automation

- `ADR-L-0005` and `ADR-P-0004` remain relevant design material
- Prompt generation can be resumed later as a focused subsystem
- It is not the mainline delivery path for the current compiler/governance work

### Decorator and traceability stack

- `ADR-L-0004` remains accepted logical direction
- Decorator libraries, verification tooling, and RECON extraction are deferred
- They should resume only after the compiler/governance surface is sufficiently stable

### Rules-library and broader autonomous governance services

- Still valuable future ecosystem work
- Not the controlling roadmap for adr-architecture-kit’s current implementation phase

## Near-Term Implementation Order

1. Finish recursive governance integration.
2. Keep roadmap, README, and generated overview aligned with actual workflows.
3. Continue compiler-governance convergence work, not unrelated subsystem expansion.
4. Begin federation/qualified-identity implementation only after the governance
   and compiler operational surfaces are stable enough to serve as canonical inputs.

## Acceptance Markers

The current compiler/governance phase can be considered largely complete when:

- compiler-backed single-scope and recursive flows are stable
- governance bundles work in both single-scope and recursive modes
- generated artifact freshness is enforced consistently
- contract validation and remediation rules are part of ordinary workflows
- contributor-facing docs no longer describe obsolete implementation priorities
- remaining work shifts from core compiler migration to federation and broader ecosystem integration
