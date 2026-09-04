<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 69144126c58c5e3aca55a93439fe189de087dc0901eefae567974816ff8adb4e
rendered_hash: 89bc502b90640c7d757e40fd6b16985653d66e471ee98d5d74b4db91e77ba28c
-->

# ADR-L-0026: Authoring Domain Contract Discovery Authority

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0026  
**Authoring contract:** authoring v1.5  
**Created:** 2026-09-02  
**Authors:** erik.gallmann  
**Domains:** architecture, authoring, schema-governance, consumer-bindings  
**Tags:** authoring-domain, adc, discovery, consumer-binding  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0026 |
| Status | accepted |
| Decisions | 6 |
| Invariants | 6 |


## Context

The forward authoring taxonomy and cross-language consumer binding now need a
language-neutral semantic authority for authoring discovery. Persistence schema
versions and binding package versions do not provide that authority: they describe
different compatibility dimensions. The locked Slice-1 design therefore promotes
Authoring Domain Contract (ADC) 1.0 as a separate contract family.

This ADR promotes discovery authority only. It does not define construction,
composition, mutation, repository writes, identity allocation, or persistence
materialization. The canonical contract artifact is maintained independently of
Python and TypeScript implementation models.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0177 | ADC is a separately versioned language-neutral contract family | — |
| DEC-0178 | ADC 1.0 defines authoring discovery only | — |
| DEC-0179 | ADC 1.0 admits exactly 27 explicit types addressed by kind and name | — |
| DEC-0180 | ADC descriptors preserve admission, composition, identity, and policy maturity | — |
| DEC-0181 | ADC cross-language qualification extends Consumer Binding Contract 1.0 | — |
| DEC-0182 | Keep consumes_interface outside ADC 1.0 pending authority and substrate reconciliation | — |

### DEC-0177 — ADC is a separately versioned language-neutral contract family

**Rationale**

ADC versions describe authoring semantics and are independent of canonical ADR persistence-schema versions and package implementation versions.

### DEC-0178 — ADC 1.0 defines authoring discovery only

**Rationale**

The first slice limits the public contract to authoring.discovery and describe_contract, list_types, and describe_type. Later construction and mutation semantics require separate authority.

### DEC-0179 — ADC 1.0 admits exactly 27 explicit types addressed by kind and name

**Rationale**

The catalog is curated contract authority, not a projection of Python enums, schemas, registries, compiler IR, or nesting. The selector is the exact, case-sensitive pair (kind, name); no persisted global type_id is introduced.

### DEC-0180 — ADC descriptors preserve admission, composition, identity, and policy maturity

**Rationale**

Descriptors distinguish defined, deferred, and not_applicable policy state; preserve logical-only Invariant declaration, three-parent NormativeProposition declaration, owner-local topology values, consumer-owned extensions, and the non-admission of NFR, Constraint, Requirement, and derived relationship forms.

### DEC-0181 — ADC cross-language qualification extends Consumer Binding Contract 1.0

**Rationale**

Python and TypeScript qualify against the same checked-in ADC evidence for structural, semantic, behavioral, and diagnostic equivalence. ADC 1.0 makes no byte-identical discovery serialization declaration.

### DEC-0182 — Keep consumes_interface outside ADC 1.0 pending authority and substrate reconciliation

**Rationale**

ADR-L-0025 names the vocabulary item while the v1.5 authored topology substrate does not admit it consistently and its endpoint meaning is unresolved. This promotion records the conflict and does not silently add, remove, or rewrite either authority.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0157 | ADC 1.0 MUST NOT imply semantic construction, composition, mutation, identity allocation, persistence, or repository… | MUST / design | automated |
| INV-0158 | ADC discovery MUST resolve an exact contract version and exact case-sensitive (kind, name) selector, and type… | MUST / design | automated |
| INV-0159 | Python and TypeScript ADC discovery MUST consume or faithfully project one promoted language-neutral contract… | MUST / test | automated |
| INV-0160 | ADC 1.0 MUST preserve distinct NormativeProposition and Invariant semantics, the shared normative_force vocabulary,… | MUST / design | automated |
| INV-0161 | The unresolved consumes_interface authority and substrate reconciliation MUST remain explicit, and… | MUST / design | automated |
| INV-0162 | ADC 1.0 cross-language discovery conformance MUST require structural, semantic, behavioral, and diagnostic… | MUST / test | automated |

### INV-0157

**Statement**

ADC 1.0 MUST NOT imply semantic construction, composition, mutation, identity allocation, persistence, or repository writes.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Discovery authority is intentionally separated from later authoring lifecycle capabilities.

### INV-0158

**Statement**

ADC discovery MUST resolve an exact contract version and exact case-sensitive (kind, name) selector, and type enumeration MUST be deterministically ordered by that pair.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Bindings must not normalize, alias, fuzzily match, or infer authoring types.

### INV-0159

**Statement**

Python and TypeScript ADC discovery MUST consume or faithfully project one promoted language-neutral contract artifact and MUST NOT maintain independent semantic catalogs.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Accepted ADRs, contract artifacts, and checked-in evidence remain semantic authority; implementations are consumers.

### INV-0160

**Statement**

ADC 1.0 MUST preserve distinct NormativeProposition and Invariant semantics, the shared normative_force vocabulary, canonical UUIDv7 entity identity, and owner-local topology_component identity.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Semantic type and identity boundaries are inherited from accepted identity and topology authority.

### INV-0161

**Statement**

The unresolved consumes_interface authority and substrate reconciliation MUST remain explicit, and relationship/consumes_interface MUST remain absent from ADC 1.0.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Slice 1 does not choose among topology, derived normalized, or dual endpoint semantics.

### INV-0162

**Statement**

ADC 1.0 cross-language discovery conformance MUST require structural, semantic, behavioral, and diagnostic equivalence and MUST NOT require byte-identical serialization.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

JSON-compatible semantic projections are contract values; property order and binding-local serialization are not ADC semantics.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0017](ADR-L-0017-forward-authoring-ergonomics-for-split-physical-adr-types.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)

**References**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0017](ADR-L-0017-forward-authoring-ergonomics-for-split-physical-adr-types.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)





## Notes

{'canonical_contract': 'contracts/authoring-domain/v1.0/contract.json', 'design_input': 'ADR-Kit-Authoring-Domain-Slice-1-Design-Journal.md', 'implementation_boundary': 'ADC discovery bindings and authoring mutation APIs are deferred to a later implementation-plan phase.', 'reconciliation': 'ADC-RECON-001 remains open. ADR-L-0025 includes consumes_interface in its\nphysical-system topology vocabulary, while authoring v1.5 model/schema support\ndoes not expose it consistently as an authored relationship. Its endpoint\nsemantics (topology occurrence, derived normalized relationship, or explicitly\ndistinct dual forms) require an authority-preserving follow-up. ADC 1.0 excludes\nrelationship/consumes_interface and does not alter ADR-L-0025 or v1.5 substrate.\n'}


---

*Generated from ADR-L-0026 by ADR Architecture Kit (projection v3)*