<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: ee656888386a1b1e046e284f63fc98cc4f3978ad9458452cd03839d90eb1be19
rendered_hash: dfac9130c3d109f2cd21d6e04e27df4b6144dc6b696a53a07977bb938077e93a
-->

# ADR-L-0016: Deterministic Corpus Query and Authoring Orientation APIs

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0016  
**Authoring contract:** authoring v1.5  
**Created:** 2026-04-14  
**Authors:** adr-architecture-kit  
**Domains:** repository, discovery, authoring  
**Tags:** repository-api, corpus-query, authoring-orientation  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0016 |
| Status | accepted |
| Decisions | 4 |
| Capabilities | 1 |
| Invariants | 2 |


## Context

Upstream authoring workflows need deterministic ways to inspect the compiled
corpus, orient themselves within a scope, and allocate governed human-facing
ADR aliases without reparsing registry YAML or hand-implementing directory
scans.

ArchitectureRepository already exposes typed entity and relationship access,
but forward authoring also needs a compact orientation summary,
first-class manifest/index accessors, explicit UUID and alias resolution, and
a supported helper for monotonic ADR alias allocation.

Under v1.3, those allocation helpers govern `alias_id` recognition surfaces;
they do not allocate or replace canonical UUID machine identity.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0069 | Extend ArchitectureRepository with deterministic orientation helpers for UUID, alias_id, alias_ref, and URI lookup | — |
| DEC-0070 | Expose corpus summary and relationships through supported CLI commands | — |
| DEC-0073 | Make forward-authoring type-prefixed ADR alias_id allocation monotonic and non-reusable | — |
| DEC-0075 | Exclude reserved ADR alias IDs 9000-9999 from standard forward alias allocation | — |

### DEC-0069 — Extend ArchitectureRepository with deterministic orientation helpers for UUID, alias_id, alias_ref, and URI lookup

**Rationale**

Repository consumers use one in-process boundary for manifest/index/summary access, entity-reference lookup whose canonical result is UUID, explicit UUID/alias_id/alias_ref/URI resolve paths, alias inventory, and governed alias_id allocation for forward authoring.

**Consequences**

Positive:
- Upstream tools stop duplicating manifest and index loading logic
- Corpus orientation becomes one stable typed API instead of ad hoc YAML reads
- Alias-ID allocation stays scope-aware, deterministic, and monotonic

### DEC-0070 — Expose corpus summary and relationships through supported CLI commands

**Rationale**

Human and script consumers need stable CLI ergonomics that mirror the
repository boundary without treating raw registry files as the user-facing
interface.

**Consequences**

Positive:
- `adr entities summary` provides one deterministic orientation surface
- `adr entities relationships` exposes graph-level inspection without custom parsing
- CLI and Python APIs stay aligned around the same repository boundary

### DEC-0073 — Make forward-authoring type-prefixed ADR alias_id allocation monotonic and non-reusable

**Rationale**

Forward type-prefixed ADR IDs are governed alias_id allocation handles for human recognition, not canonical machine identity. UUID remains canonical entity identity. Alias allocation stays monotonic and non-reusable and must never replace UUIDs or rewrite UUID references.

**Consequences**

Positive:
- Historical traceability is preserved
- Allocation remains deterministic without gap filling
- Deleted artifacts cannot silently reactivate old identities

### DEC-0075 — Exclude reserved ADR alias IDs 9000-9999 from standard forward alias allocation

**Rationale**

The reserved 9000-9999 range preserves governed alias allocation history for exceptional records. It is not a UUID identity range and must not be treated as canonical machine-identity allocation.

**Consequences**

Positive:
- Standard allocation remains predictable below 9000
- Brownfield or imported records have a governed preserved-identity range
- Reserved-range artifacts do not pollute the normal forward sequence


## Capabilities

### CAP-0045 — Deterministic Corpus Orientation Surface

Provide one supported API and CLI surface for manifest/index/summary access, UUID and alias lookup/resolve paths, alias inventory, and scope-local governed alias_id allocation.

**Acceptance criteria**
- Entity-reference lookup returns UUID as the canonical result
- Explicit UUID, alias_id, alias_ref, and URI resolve paths are available
- Normal-band alias_id values allocate monotonically and are never reused
- Alias allocation never replaces UUIDs or rewrites UUID references




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0069 | Forward-authoring governed alias_id allocation MUST be monotonic and non-reusable. Previously allocated aliases and… | MUST / design | automated |
| INV-0071 | Reserved ADR alias IDs `9000-9999` MUST NOT participate in standard forward alias allocation and MUST NOT be treated… | MUST / design | automated |

### INV-0069

**Statement**

Forward-authoring governed alias_id allocation MUST be monotonic and non-reusable. Previously allocated aliases and historical gaps remain consumed history and MUST NOT be reissued or used to replace UUID identity.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Reusing ADR identities corrupts provenance, historical references, and
deterministic traceability.

### INV-0071

**Statement**

Reserved ADR alias IDs `9000-9999` MUST NOT participate in standard forward alias allocation and MUST NOT be treated as UUID machine-identity allocation.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Exceptional identities need a governed range that does not distort the
normal forward allocation sequence.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0017](ADR-L-0017-forward-authoring-ergonomics-for-split-physical-adr-types.md)

**References**
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0017](ADR-L-0017-forward-authoring-ergonomics-for-split-physical-adr-types.md)






---

*Generated from ADR-L-0016 by ADR Architecture Kit (projection v3)*