# Legacy Intent Attribution Audit

Date: 2026-03-14
Scope: `adr-architecture-kit`
Status: initial audit

## Purpose

Prevent decorator and attribution cleanup from expanding chaotically by making
the first onboarding boundary explicit before code annotation starts.

This document is planning material, not canonical architecture authority.
Canonical rule authority lives in `ADR-L-0004` and `INV-0006`.

## First-Wave In-Scope Surfaces

These are the highest-value public boundaries to annotate first once the
decorator library and downstream extraction path exist.

- `src/adr_kit/cli/main.py`
  - public CLI command entry points
  - high governance value because they expose user-facing architecture workflows
- `src/adr_kit/compiler/driver.py`
  - `ArchitectureCompiler`
  - authoritative compile orchestration surface
- `src/adr_kit/compiler/pipeline.py`
  - explicit compiler pipeline surfaces
- `src/adr_kit/parser/yaml_parser.py`
  - canonical ADR parsing boundary
- `src/adr_kit/projection.py`
  - integrity/inspection projection surface
- `src/adr_kit/schema/contract_validation.py`
  - contract validation entry surface

## Likely Second-Wave Surfaces

- compiler backend emitters and rendering helpers
- repository loader and registry resolution helpers
- system overview generator inputs that expose architecture workflow guidance
- test helpers that intentionally model public governance behavior

## Initial Exemptions

These should stay out of the first rollout to avoid noisy low-value annotation.

- private helper functions inside modules already covered by a module/class-level attribution
- golden fixtures and test data
- generated artifacts under `adrs/rendered/`, `adrs/index/`, and `adrs/entities/`
- one-off migration scripts unless they become maintained governance tooling
- packaging/build metadata that has no independent architectural behavior

## Onboarding Rules of Thumb

- Prefer module-, class-, or command-entry attribution at public boundaries first.
- Do not annotate every private helper function before the public boundary is covered.
- Infrastructure/config/schema/pipeline artifacts should use file-level metadata, not
  per-resource tags, unless a later ADR explicitly requires deeper granularity.
- Let RECON/decorator-inference fill obvious interior gaps later; do not block the
  first rollout on perfect interior coverage.

## Downstream Follow-On Work

- `ste-runtime`
  - extract `implements_adr` / metadata-level attribution
  - emit attribution evidence and slice claims with provenance
- `ste-rules-library`
  - encode optional reusable activation/evaluation rules after ADR-Kit authority is stable
- `ste-spec`
  - absorb the evidence contract only if it must become a shared normative schema
