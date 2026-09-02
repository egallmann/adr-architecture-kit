<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 8c3421d71bc355f6050425f821d7527c46bb50867ab521e5fbae0ecf6463e4e0
rendered_hash: a3d8896b4a7eb0eeeea49af793f0ce0ef922f4f21049a5e7972dee11987fba73
-->

# ADR-L-0023: Consumer Semantic Extension Contract

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0023  
**Authoring contract:** authoring v1.5  
**Created:** 2026-08-21  
**Authors:** adr-architecture-kit  
**Domains:** architecture, schema-governance, extensibility  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0023 |
| Status | accepted |
| Decisions | 8 |
| Invariants | 8 |


## Context

ADR-Kit owns the universal envelope, structural validation, references,
provenance eligibility, and deterministic projections, while consumers have
legitimate semantic types that are not universal enough for first-class
ontology promotion. A safe extension must preserve those boundaries without
creating a second graph or a schema-less metadata escape hatch.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0147 | Canonize the universal envelope while opening a qualified consumer semantic namespace | — |
| DEC-0148 | Author extensions through explicit extension_entities and extension_relationships sections | — |
| DEC-0149 | Require consumer extension types to be qualified by the owning architecture namespace | — |
| DEC-0150 | Bound extension properties to scalar JSON-like values and require rationale | — |
| DEC-0151 | Require authored extension relationships for graph semantics | — |
| DEC-0152 | Validate consumer-owned alias registrations without centralizing them in ADR-Kit | — |
| DEC-0153 | Keep persisted canonical relationship identity mechanically distinct from hash compatibility projections | — |
| DEC-0154 | Preserve every valid unknown extension through parse, compile, normalization, and repository loading | — |

### DEC-0147 — Canonize the universal envelope while opening a qualified consumer semantic namespace

**Rationale**

ADR-Kit can preserve unknown consumer meaning without interpreting it.

### DEC-0148 — Author extensions through explicit extension_entities and extension_relationships sections

**Rationale**

Explicit sections preserve strict first-class schemas and prevent arbitrary field escape hatches.

### DEC-0149 — Require consumer extension types to be qualified by the owning architecture namespace

**Rationale**

Qualification prevents future collision with ADR-Kit controlled vocabulary.

### DEC-0150 — Bound extension properties to scalar JSON-like values and require rationale

**Rationale**

ADR-Kit validates deterministic shape while leaving domain meaning opaque.

### DEC-0151 — Require authored extension relationships for graph semantics

**Rationale**

Property values never imply graph edges.

### DEC-0152 — Validate consumer-owned alias registrations without centralizing them in ADR-Kit

**Rationale**

Each architecture corpus retains authority for its own alias allocation scope.

### DEC-0153 — Keep persisted canonical relationship identity mechanically distinct from hash compatibility projections

**Rationale**

Hash identifiers cannot become canonical graph identity by implication.

### DEC-0154 — Preserve every valid unknown extension through parse, compile, normalization, and repository loading

**Rationale**

Downstream consumers must not pre-register semantic types to consume validated records.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0141 | Every extension entity and canonical extension relationship has UUID identity and governed alias orientation before… | MUST / design | automated |
| INV-0142 | Every locally authored extension semantic type is qualified by the containing architecture namespace and validated… | MUST / design | automated |
| INV-0143 | Extension property values never imply graph relationships. | MUST / design | automated |
| INV-0144 | Normalized extension payload is represented in a typed extension field and is preserved without ADR-Kit semantic… | MUST / design | automated |
| INV-0145 | A relationship lacking persisted canonical UUID identity cannot enter the canonical v2.1 graph surface. | MUST / design | automated |
| INV-0146 | Valid extension types, properties, rationale, and explicit relationships round-trip deterministically through… | MUST / test | automated |
| INV-0147 | Compiler and projection stages never mint authoritative extension entity or relationship UUIDs. | MUST / design | automated |
| INV-0148 | v1.4 authored extension relationship endpoints are local UUIDv7 references; future cross-namespace support uses the… | MUST / design | automated |

### INV-0141

**Statement**

Every extension entity and canonical extension relationship has UUID identity and governed alias orientation before graph admission.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Extensions participate in the same identity system as first-class entities.

### INV-0142

**Statement**

Every locally authored extension semantic type is qualified by the containing architecture namespace and validated against consumer-owned allocation state.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

ADR-Kit validates ownership without becoming a central semantic registry.

### INV-0143

**Statement**

Extension property values never imply graph relationships.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Explicit authored relationships keep graph construction deterministic.

### INV-0144

**Statement**

Normalized extension payload is represented in a typed extension field and is preserved without ADR-Kit semantic interpretation.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Generic metadata must not become the extension contract.

### INV-0145

**Statement**

A relationship lacking persisted canonical UUID identity cannot enter the canonical v2.1 graph surface.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Compatibility hashes remain derived projections only.

### INV-0146

**Statement**

Valid extension types, properties, rationale, and explicit relationships round-trip deterministically through normalized repository surfaces.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Unknown valid types are a supported consumer capability.

### INV-0147

**Statement**

Compiler and projection stages never mint authoritative extension entity or relationship UUIDs.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Identity allocation remains canonical-authority work.

### INV-0148

**Statement**

v1.4 authored extension relationship endpoints are local UUIDv7 references; future cross-namespace support uses the qualified external-reference contract.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

The local-only v1 boundary must not create an alias or hidden-property reference path.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)

**References**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)






---

*Generated from ADR-L-0023 by ADR Architecture Kit (projection v3)*