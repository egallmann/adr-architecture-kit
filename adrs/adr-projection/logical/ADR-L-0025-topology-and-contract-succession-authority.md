<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: abf17bba20247402db4b0248f0dfa7fd2b7af286125e3eb7dfcef7e097b080f7
rendered_hash: cca52db0281f0e0d7d73d5d0b62e095af162ac19b7e03fd045ad239ccdb7921d
-->

# ADR-L-0025: Topology and Contract Succession Authority (Authoring v1.5 / Normalized v2.2)

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0025  
**Authoring contract:** authoring v1.5  
**Created:** 2026-08-28  
**Authors:** adr-architecture-kit  
**Domains:** architecture, schema-governance, topology, normalization  
**Tags:** projection-v3, authoring-v1.5, normalized-v2.2, topology  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0025 |
| Status | accepted |
| Decisions | 8 |


## Context

Projection v3 and the ADR-P retirement boundary require durable logical authority
for authoring contract succession (v1.5) and normalized model succession (v2.2).
This ADR governs topology semantics, cross-document invariants, and endpoint-type
rules without encoding production implementation.

Authoring v1.5 extends v1.4 and retires generic physical ADR authoring. Normalized
v2.2 extends v2.1 and introduces topology verb vocabulary with explicit provenance.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0168 | Authoring v1.5 succeeds v1.4 as current authoring contract | — |
| DEC-0169 | Normalized model v2.2 succeeds v2.1 as topology-capable semantic contract | — |
| DEC-0170 | TOPO handles are local; component_ref resolves to admitted COMP entity UUID | — |
| DEC-0171 | composed_of is SYS UUID to COMP UUID only | — |
| DEC-0172 | Six topology verbs with grammatical FROM verb TO direction | — |
| DEC-0173 | Topology-sourced compatibility relationships use explicit provenance and stable identity posture | — |
| DEC-0174 | PS topology component_ref must agree with owning PC implements_system | — |
| DEC-0175 | v2.2 endpoint-type semantics are normative beyond JSON Schema shape | — |

### DEC-0168 — Authoring v1.5 succeeds v1.4 as current authoring contract

**Rationale**

v1.4 remains released and frozen (ADR-L-0023 extension semantics). v1.5 extends
v1.4 preserving extension_entities and extension_relationships while introducing
slim topology component records and closed ADR taxonomy (logical, physical-system,
physical-component only).

### DEC-0169 — Normalized model v2.2 succeeds v2.1 as topology-capable semantic contract

**Rationale**

v2.1 remains released and frozen. v2.2 preserves canonical and compatibility
relationship identity classes and extension payloads while adding topology verbs,
consumes_interface, composed_of, and explicit provenance posture.

### DEC-0170 — TOPO handles are local; component_ref resolves to admitted COMP entity UUID

**Rationale**

Topology components in physical-system ADRs use local TOPO handles (id, component_ref,
purpose). component_ref is the canonical admitted component entity UUIDv7, not an
ADR document UUID. TOPO must not become normalized component entities.

### DEC-0171 — composed_of is SYS UUID to COMP UUID only

**Rationale**

Normalized composed_of relationships connect system entities to component entities.
TOPO handles never appear as normalized relationship endpoints.

### DEC-0172 — Six topology verbs with grammatical FROM verb TO direction

**Rationale**

Physical-system topology relationships use depends_on, calls, publishes_to,
subscribes_to, reads_from, writes_to, and consumes_interface with explicit
FROM -> VERB -> TO grammatical direction.

### DEC-0173 — Topology-sourced compatibility relationships use explicit provenance and stable identity posture

**Rationale**

Compatibility relationships derived from authored topology carry
provenance_classification explicit and preserve protocol/description metadata.

### DEC-0174 — PS topology component_ref must agree with owning PC implements_system

**Rationale**

Cross-document invariant: every component_ref in a physical-system topology must
reference a component entity whose owning physical-component ADR implements_system
includes that system. Contradiction fails validation. JSON Schema validates local
structure only; mechanical enforcement belongs to production validator implementation.

### DEC-0175 — v2.2 endpoint-type semantics are normative beyond JSON Schema shape

**Rationale**

Schema-valid relationship records do not prove endpoint entity type. composed_of
requires system source and component target. Topology verbs require component endpoints.
Production semantic validation must prove endpoint existence and permitted types.











## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0007](ADR-L-0007-deterministic-documentation-projection.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)

**References**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0007](ADR-L-0007-deterministic-documentation-projection.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)






---

*Generated from ADR-L-0025 by ADR Architecture Kit (projection v3)*