<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 30c3d7dc7acff4f6a6c33a3603a8aea2976488e46071e6033641711d4212524f
rendered_hash: 51345f836b24b90f8ef494e7a53c14ea5892c6a58676b878717e519f9d18eafc
-->

# ADR-L-0011: Metadata Schemas and Remediation Ledger Enforcement

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0011  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-14  
**Authors:** erik.gallmann  
**Domains:** governance, metadata, migration, brownfield  
**Tags:** metadata, remediation-ledger, sentinel, approval  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0011 |
| Status | accepted |
| Decisions | 4 |
| Capabilities | 2 |
| Invariants | 3 |
| Physical realizations | [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md), [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md), [ADR-PC-0006](../physical-component/ADR-PC-0006-brownfield-onboarding-and-canonical-normalization.md) |


## Context

The compiler contract now distinguishes fully compliant bundles from
sentinel-backed brownfield and migration bundles. That boundary is only safe
if sentinel use is narrow, explicitly tracked, and moved toward approved
canonical content through a monotonic workflow.

The plan work established several key rules:
1. Sentinel values are allowed only in narrative content fields
2. Structural, referential, and governance fields may never contain sentinels
3. Remediation state should live in a separate governance artifact rather than
   be embedded in ADR content
4. Approved content must not regress back to sentinel-backed state

What remains is to formalize those rules as an architectural decision that
binds metadata schema work, sentinel usage, and remediation workflow together.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0040 | Define per-entity metadata through typed schemas rather than an unconstrained metadata bag | — |
| DEC-0041 | Restrict sentinel values to narrative fields and sections only | — |
| DEC-0042 | Enforce remediation through a separate canonical remediation ledger | — |
| DEC-0043 | Require staged approval before replacement content becomes protected canonical content | — |

### DEC-0040 — Define per-entity metadata through typed schemas rather than an unconstrained metadata bag

**Rationale**

Registry metadata is currently too weak as a contract surface. Different
entity types carry different keys, and without typed expectations the kernel
and compiler can drift silently.

**Consequences**

Positive:
- Metadata becomes part of the contract rather than convention
- Profile-aware validation can reason about missingness explicitly
- Kernel consumers gain predictable field expectations
- The initial 0.x contract can be anchored to currently generated metadata keys

### DEC-0041 — Restrict sentinel values to narrative fields and sections only

**Rationale**

Sentinel values are useful for preserving structure where knowledge is
missing, but they are dangerous in identifiers, references, enums, or
governance fields. Narrow placement keeps them honest and machine-safe.

**Consequences**

Positive:
- Referential integrity remains trustworthy
- Brownfield tolerance does not degrade structural meaning
- Validator behavior stays deterministic

### DEC-0042 — Enforce remediation through a separate canonical remediation ledger

**Rationale**

Current architecture content and remediation workflow state should not be
mixed. A separate remediation ledger preserves auditability, avoids process
leakage into ADR text, and provides a stable mechanism for no-regression
enforcement.

**Consequences**

Positive:
- Approval state is queryable without mutating architecture semantics
- Legacy recovery history remains visible
- The system can prove changes were not shaped solely by encoding pressure

### DEC-0043 — Require staged approval before replacement content becomes protected canonical content

**Rationale**

Non-sentinel replacement content may be better than a sentinel without yet
being authoritative. Staged approval prevents accidental promotion and keeps
the no-regression rule tied to explicit governance.

**Consequences**

Positive:
- Replacement content can be introduced before final approval
- Approval remains explicit and auditable
- Monotonic remediation protects only governed content


## Capabilities

### CAP-0036 — Typed Metadata Contract Enforcement

Validate entity metadata against entity-type-specific schema expectations
under the active enforcement profile.

**Acceptance criteria**
- Metadata keys are evaluated by entity type
- Brownfield and migration can represent missing narrative content explicitly
- Structural metadata fields remain sentinel-forbidden

### CAP-0037 — Remediation Ledger Governance

Track sentinel usage, replacement, approval, and no-regression state in a
canonical governance artifact.

**Acceptance criteria**
- Ledger state supports sentinel, pending_approval, and approved
- Approved content cannot regress to sentinel without explicit override
- Authority reference, approver, and approval timestamp are recorded for approved state




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0055 | Reserved sentinel values MUST be allowed only in narrative fields or sections explicitly designated as… | MUST / policy | automated |
| INV-0056 | Remediation workflow state MUST be recorded in a separate canonical remediation ledger rather than in ADR content… | MUST / design | automated |
| INV-0057 | Once a field or section has an approved remediation-ledger entry for non-sentinel canonical content, that field or… | MUST / policy | automated |

### INV-0055

**Statement**

Reserved sentinel values MUST be allowed only in narrative fields or
sections explicitly designated as sentinel-capable by schema or policy.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Sentinel tolerance must preserve narrative structure without weakening
structural semantics.

### INV-0056

**Statement**

Remediation workflow state MUST be recorded in a separate canonical
remediation ledger rather than in ADR content fields.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Workflow state and architecture state must remain distinct.

### INV-0057

**Statement**

Once a field or section has an approved remediation-ledger entry for
non-sentinel canonical content, that field or section MUST NOT regress to a
sentinel state under normal validation.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Brownfield tolerance must ratchet toward stronger compliance rather than
remain a permanent escape hatch.




## Physical Realization

**Systems**
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**Components**
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0006](../physical-component/ADR-PC-0006-brownfield-onboarding-and-canonical-normalization.md)




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)

**References**
- [ADR-L-0014](ADR-L-0014-brownfield-onboarding-and-canonicalization-workflow.md)
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0015](ADR-L-0015-adr-governance-state-and-override-semantics.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0002 — Schema and Contract Validation](../physical-component/ADR-PC-0002-schema-and-contract-validation.md) | implements this logical authority | `ADR-PC-0002 -[:implements_logical]-> ADR-L-0011` |
| [ADR-PC-0006 — Brownfield Onboarding and Canonical Normalization](../physical-component/ADR-PC-0006-brownfield-onboarding-and-canonical-normalization.md) | implements this logical authority | `ADR-PC-0006 -[:implements_logical]-> ADR-L-0011` |
| [ADR-PS-0002 — ADR Kit Authoring Compiler and Validation System](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md) | implements this logical authority | `ADR-PS-0002 -[:implements_logical]-> ADR-L-0011` |





---

*Generated from ADR-L-0011 by ADR Architecture Kit (projection v3)*