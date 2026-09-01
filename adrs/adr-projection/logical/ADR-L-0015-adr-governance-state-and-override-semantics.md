<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 472c7248e60689eb306042e9e9396373f7a33e3900855efee9aad1adc1d7fbd4
rendered_hash: a5568869c11556c8f6fbdfa2e791b31a5cd48203de2cb01e780057094384e9ce
-->

# ADR-L-0015: ADR Governance State and Override Semantics

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0015  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-18  
**Authors:** adr-architecture-kit  
**Domains:** governance, validation, approval, overrides  
**Tags:** governance, override, steelman, approval  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0015 |
| Status | accepted |
| Decisions | 4 |
| Capabilities | 2 |
| Invariants | 3 |


## Context

The repository now has a first-pass governance block on ADRs and a canonical
objection override artifact. That initial implementation made the metadata
available, but it left several important questions under-specified:

1. whether implementation authority is boolean or tiered
2. how approval metadata is paired and interpreted
3. how overrides relate to ADR meaning versus implementation allowance
4. how override validity is coupled to later ADR revision
5. how projections may expose governance state without inventing meaning

Those questions materially affect acceptance gating, implementation behavior,
and deterministic validation. They need a single canonical decision so schema,
validator, and projection behavior stay aligned.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0063 | Define ADR governance as a canonical nested metadata block with explicit implementation-authority levels | — |
| DEC-0064 | Record implementation exceptions in separate objection override artifacts | — |
| DEC-0065 | Bind override review validity to ADR modified_date and warn on stale coupling | — |
| DEC-0066 | Allow projections to expose governance references and summary metadata only | — |

### DEC-0063 — Define ADR governance as a canonical nested metadata block with explicit implementation-authority levels

**Rationale**

Governance state is part of canonical ADR meaning, but it is not the same
thing as ADR lifecycle or architecture intent. A nested governance block
keeps approval and implementation gating explicit without turning derived
projections into authority.

**Consequences**

Positive:
- Approval and implementation status become machine-detectable
- Authority stays on the ADR rather than migrating into indexes
- Future governance fields can be extended without overloading lifecycle status

### DEC-0064 — Record implementation exceptions in separate objection override artifacts

**Rationale**

Override rationale, risk, and exception posture should remain canonical, but
they should not bloat ADR text or rewrite architecture intent. Separate
override artifacts keep exception handling explicit and auditable.

**Consequences**

Positive:
- ADR meaning remains stable while implementation exceptions are recorded separately
- Override approval and accepted risk are queryable
- ADRs can reference overrides by ID without carrying inline exception prose

### DEC-0065 — Bind override review validity to ADR modified_date and warn on stale coupling

**Rationale**

Overrides should not silently continue applying after the ADR they depend on
has materially changed. Using ADR modified_date provides a minimal canonical
coupling point that works with the current schema line.

**Consequences**

Positive:
- Validators can detect likely stale exceptions deterministically
- The MVP avoids inventing a new ADR revision field prematurely
- Governance review remains visible when ADR meaning evolves

### DEC-0066 — Allow projections to expose governance references and summary metadata only

**Rationale**

Projections need to support lookup and orchestration, but they must not
synthesize approvals, risks, or override semantics beyond what the canonical
artifacts explicitly say.

**Consequences**

Positive:
- Manifests and indexes stay useful for tooling
- Projections do not become alternate governance authority
- Validation can compare projection output directly to canonical sources


## Capabilities

### CAP-0042 — Deterministic ADR Governance Validation

Validate ADR governance metadata, approval pairings, implementation
authority, override references, and stale revision coupling through
deterministic rules.

### CAP-0043 — Governance Summary Projection

Expose ADR governance references and override summaries in manifest and
discovery surfaces without leaking rationale or accepted risk text.




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0064 | Absence of ADR governance approval fields MUST NOT be interpreted as approval or implementation authority. | MUST / policy | automated |
| INV-0065 | Objection override artifacts MUST NOT change ADR architectural meaning and MUST govern implementation allowance only. | MUST / design | automated |
| INV-0066 | Derived projections MUST expose only governance IDs and summary metadata and MUST NOT invent approvals, risks, or… | MUST / policy | automated |

### INV-0064

**Statement**

Absence of ADR governance approval fields MUST NOT be interpreted as
approval or implementation authority.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Governance state must be explicit, not inferred by omission.

### INV-0065

**Statement**

Objection override artifacts MUST NOT change ADR architectural meaning and
MUST govern implementation allowance only.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Override records are exception control, not alternate architecture authority.

### INV-0066

**Statement**

Derived projections MUST expose only governance IDs and summary metadata and
MUST NOT invent approvals, risks, or authority-altering interpretations.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Lookup surfaces must remain projections over canonical governance state.






## Governance / Bindings / Evidence

### Governance

**Implementation authority:** ImplementationAuthority.ADVISORY
**Related reviews:** REVIEW-0001
**Steelman review completed:** true
**Steelman review required:** true


## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0011](ADR-L-0011-metadata-schemas-and-remediation-ledger-enforcement.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)

**References**
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0011](ADR-L-0011-metadata-schemas-and-remediation-ledger-enforcement.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)






---

*Generated from ADR-L-0015 by ADR Architecture Kit (projection v3)*