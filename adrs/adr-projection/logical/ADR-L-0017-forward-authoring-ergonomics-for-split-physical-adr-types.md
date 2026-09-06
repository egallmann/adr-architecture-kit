<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 9dffb27800d091b38b05311c12e4e0ddb023aed180410963f301b7c78e3c1cd8
rendered_hash: dabdb1e674df9bb7215b9465d6836c85cf9353072806c0d49b05ecc2ee7110fe
-->

# ADR-L-0017: Forward Authoring Ergonomics for Split Physical ADR Types

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0017  
**Authoring contract:** authoring v1.5  
**Created:** 2026-04-14  
**Authors:** erik.gallmann  
**Domains:** authoring, adr-taxonomy  
**Tags:** scaffolding, next-id, physical-types  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0017 |
| Status | accepted |
| Decisions | 3 |
| Invariants | 2 |


## Context

adr-architecture-kit now supports multiple physical ADR shapes:
legacy `ADR-P-*`, current `ADR-PS-*`, and current `ADR-PC-*`. Upstream
authoring workflows need structured scaffolds, schema discovery, and next-ID
allocation that reinforce the current split physical taxonomy without breaking
existing legacy parsing and validation.

If new ergonomics continue treating legacy `ADR-P-*` as a first-class
creation path, upstream tools will keep steering new authoring toward an
outdated taxonomy even while the repository supports more precise
physical-system and physical-component artifacts.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0071 | Provide scaffold and schema-surface ergonomics for logical, physical-system, and physical-component ADRs only | — |
| DEC-0072 | Retain legacy ADR-P parsing and validation but exclude it from new creation ergonomics | — |
| DEC-0074 | Reserve ADR IDs 9000-9999 for exceptional allocation and exclude that range from normal forward allocation | — |

### DEC-0071 — Provide scaffold and schema-surface ergonomics for logical, physical-system, and physical-component ADRs only

**Rationale**

New authoring ergonomics should reinforce the forward taxonomy and expose
deterministic structured inputs for the ADR types the repository wants new
work to use.

**Consequences**

Positive:
- New workflows are nudged toward `ADR-L-*`, `ADR-PS-*`, and `ADR-PC-*`
- Scaffold and schema discovery stay aligned with the current generator surface

### DEC-0072 — Retain legacy ADR-P parsing and validation but exclude it from new creation ergonomics

**Rationale**

Existing repositories and tests still contain `ADR-P-*` artifacts, so
backward compatibility remains necessary. That compatibility does not
require adding new forward-authoring affordances for the legacy type.

**Consequences**

Positive:
- Existing legacy artifacts remain readable and validatable
- New ergonomic surfaces do not regress the taxonomy split

### DEC-0074 — Reserve ADR IDs 9000-9999 for exceptional allocation and exclude that range from normal forward allocation

**Rationale**

The high ADR ID range is needed for exceptional cases such as brownfield
imports, retained legacy artifacts pending migration, and other imported
records whose identity must be preserved. Normal authoring allocation
should stay below 9000 so it does not drift into that exceptional space.

**Consequences**

Positive:
- Normal authoring remains in a predictable ID range below 9000
- The reserved high range stays available for exceptional/manual use
- Imported or retained legacy identities do not advance normal allocation counters





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0068 | Forward authoring ergonomics in adr-architecture-kit MUST target logical, physical-system, and physical-component… | MUST / design | automated |
| INV-0070 | ADR IDs `9000-9999` MUST be treated as a reserved exceptional allocation range for cases such as brownfield imports,… | MUST / design | automated |

### INV-0068

**Statement**

Forward authoring ergonomics in adr-architecture-kit MUST target logical,
physical-system, and physical-component ADRs, while legacy `ADR-P-*`
support remains compatibility-only.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

The ergonomic surface must preserve the intended ADR taxonomy instead of
accidentally reopening the legacy flat physical path for new authoring.

### INV-0070

**Statement**

ADR IDs `9000-9999` MUST be treated as a reserved exceptional allocation
range for cases such as brownfield imports, retained legacy artifacts
pending migration, and other imported records requiring preserved
identity. Standard forward authoring allocation MUST exclude that range.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

The allocator must remain aware of the reserved namespace so normal
authoring does not collide with imported or exceptional identities.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0002](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
- [ADR-L-0016](ADR-L-0016-deterministic-corpus-query-and-authoring-orientation-apis.md)

**References**
- [ADR-L-0018](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)
- [ADR-L-0016](ADR-L-0016-deterministic-corpus-query-and-authoring-orientation-apis.md)
- [ADR-L-0002](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
- [ADR-L-0026](ADR-L-0026-authoring-domain-contract-discovery-authority.md)






---

*Generated from ADR-L-0017 by ADR Architecture Kit (projection v3)*