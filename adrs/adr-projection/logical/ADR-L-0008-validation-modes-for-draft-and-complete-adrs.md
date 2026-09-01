<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: bac119a6321d2813f11411dceb1ce89c8565149eece8bc8164316cbf80f536bf
rendered_hash: 52f2eccdd3ba90af2dae34619847d7140476e9237afcf0a6e35d829b135a1a23
-->

# ADR-L-0008: Validation Modes for Draft and Complete ADRs

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0008  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-13  
**Authors:** adr-architecture-kit  
**Domains:** validation, adr, workflow, governance  
**Tags:** draft, completeness, schema, steelman  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0008 |
| Status | accepted |
| Decisions | 5 |
| Capabilities | 2 |
| Invariants | 3 |
| Physical realizations | [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md), [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md) |


## Context

The ADR Architecture Kit currently couples schema validation to completeness for
several ADR types. That behavior is useful for acceptance gates, but it is too
strict for the actual design workflow used in this workspace.

The intended workflow is:
1. Generate or author partially pinned ADRs while a design is still forming
2. Preserve explicit empty sections so missing content remains visible
3. Validate structural alignment separately from completeness
4. Run steelman review as a correctness pass over the draft
5. Enforce complete population only when the artifact is ready for stronger gates

Today the implementation prunes empty collections during generation and relies on
strict schema/model requirements for validation. That collapses two distinct
states into one:
- structurally aligned draft
- complete artifact ready for stronger downstream use

This makes draft ADR authoring less transparent and prevents empty sections from
acting as fast review signals.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0013 | Use one validator with explicit validation modes | — |
| DEC-0020 | Define structural mode for schema-aligned drafts | — |
| DEC-0027 | Define complete mode for population readiness | — |
| DEC-0032 | Keep steelman review separate from deterministic validation | — |
| DEC-0035 | Allow generators to preserve explicit empty sections when requested | — |

### DEC-0013 — Use one validator with explicit validation modes

**Rationale**

The artifact type does not change across the workflow; only the validation
gate changes. A single validator with an explicit mode argument keeps the
API coherent and avoids duplicating parsing and reporting logic.

**Consequences**

Positive:
- One validation entrypoint for all workflow stages
- CLI and API semantics stay consistent
- Different gates can share reporting structures

### DEC-0020 — Define structural mode for schema-aligned drafts

**Rationale**

Structural validation should answer whether an ADR is shaped correctly
enough to participate in review, even if required sections are intentionally
empty while decisions are still being pinned down.

Structural mode keeps section presence and schema shape checks, but it does
not fail solely because a required collection is empty.

**Consequences**

Positive:
- Draft ADRs can validate without pretending to be complete
- Empty sections remain visible as review targets
- Tooling can distinguish malformed artifacts from incomplete ones

### DEC-0027 — Define complete mode for population readiness

**Rationale**

Complete validation should answer whether the ADR is sufficiently populated
for stricter downstream use. This is still a structural/content-presence
gate, not a correctness gate.

**Consequences**

Positive:
- Current strict validation behavior remains available
- Downstream generation and acceptance gates can depend on populated inputs
- Completeness remains deterministic and non-LLM-based

### DEC-0032 — Keep steelman review separate from deterministic validation

**Rationale**

Steelman review evaluates correctness, coherence, missing reasoning, and
architectural quality. That is not the same concern as schema alignment or
section population, and it should remain a separate LLM-backed review pass.

**Consequences**

Positive:
- Deterministic validation remains deterministic
- Steelman review can focus on correctness rather than syntax
- Failure modes are easier to interpret

### DEC-0035 — Allow generators to preserve explicit empty sections when requested

**Rationale**

If draft ADRs are expected to surface incompleteness, generators must not
erase those signals unconditionally. Empty sections should be preservable
when the author is intentionally emitting a draft artifact.

**Consequences**

Positive:
- Generated drafts remain inspectable
- Review tooling can use empties as fast signals
- Complete-mode generation can still emit pruned, stricter artifacts when desired


## Capabilities

### CAP-0015 — Mode-Aware ADR Validation

The validator accepts a mode argument and returns findings appropriate to
structural or complete validation.

**Acceptance criteria**
- Structural mode accepts explicit empty required collections
- Complete mode preserves strict population checks
- Result format remains consistent across modes

### CAP-0016 — Draft-Preserving Source Generation

Source ADR generators can preserve explicit empty sections when generating
draft artifacts for review.

**Acceptance criteria**
- Empty arrays and objects can be preserved on request
- Preserved drafts can be validated in structural mode
- Existing strict generation workflows remain available




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0040 | ADR validation MUST support a structural mode that accepts intentionally incomplete drafts when their schema shape… | MUST / design | automated |
| INV-0041 | Complete validation MUST remain deterministic and MUST NOT depend on LLM reasoning. | MUST / design | automated |
| INV-0042 | Steelman review MUST remain a separate correctness-oriented review layer and MUST NOT be conflated with schema… | MUST / design | manual |

### INV-0040

**Statement**

ADR validation MUST support a structural mode that accepts intentionally
incomplete drafts when their schema shape is otherwise valid.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Draft ADRs are first-class artifacts in the design workflow and must be
distinguishable from malformed YAML or invalid schemas.

### INV-0041

**Statement**

Complete validation MUST remain deterministic and MUST NOT depend on LLM
reasoning.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Completeness is a workflow gate, not a correctness judgment.

### INV-0042

**Statement**

Steelman review MUST remain a separate correctness-oriented review layer
and MUST NOT be conflated with schema validation.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Correctness and coherence require semantic judgment that differs from
deterministic structural validation.




## Physical Realization

**Systems**
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**Components**
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)

**References**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0011](ADR-L-0011-metadata-schemas-and-remediation-ledger-enforcement.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0015](ADR-L-0015-adr-governance-state-and-override-semantics.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0002 — Schema and Contract Validation](../physical-component/ADR-PC-0002-schema-and-contract-validation.md) | implements this logical authority | `ADR-PC-0002 -[:implements_logical]-> ADR-L-0008` |
| [ADR-PS-0002 — ADR Kit Authoring Compiler and Validation System](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md) | implements this logical authority | `ADR-PS-0002 -[:implements_logical]-> ADR-L-0008` |





---

*Generated from ADR-L-0008 by ADR Architecture Kit (projection v3)*