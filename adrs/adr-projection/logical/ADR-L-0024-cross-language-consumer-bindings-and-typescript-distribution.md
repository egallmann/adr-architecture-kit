<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: f8169b4be41791a17b60753261dea97c76a44a49d2df983f46c2fa5a3fb7f685
rendered_hash: 9d726a637272cf7b9e4bad03c1d08918d11d72d953caa7613f1ee0318f17f87a
-->

# ADR-L-0024: Cross-Language Consumer Bindings and TypeScript Distribution

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0024  
**Authoring contract:** authoring v1.5  
**Created:** 2026-08-23  
**Authors:** adr-architecture-kit  
**Domains:** architecture, consumer-bindings, schema-governance, distribution  
**Tags:** consumer-binding, typescript, node, browser, conformance, read-only  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0024 |
| Status | accepted |
| Decisions | 13 |
| Capabilities | 2 |
| Invariants | 8 |


## Context

ADR-Kit already owns accepted ADR authority, canonical schema bytes, semantic
vocabularies, the repository discovery contract, the normalized model, and
validated derived embodiment evidence. Python is the existing implementation
of those contracts, but it is not their semantic owner. Node services,
engineering-agent integrations, and browser applications need a supported
read-only consumer binding without reparsing ADR source YAML, depending on
compiler internals, or importing Node authority into browser applications.

A language binding must therefore be governed by one explicit consumer contract,
advertise only the capabilities it actually implements, and be qualified by
semantic and behavioral equivalence over overlapping capabilities. Binding-local
implementation details and deterministic fingerprints are not cross-language
identity. A first TypeScript distribution must preserve the repository boundary,
keep Node filesystem and linkage behavior behind explicit Node subpaths, and
remain framework-neutral for browser and Angular consumers.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0155 | Accepted ADRs canonical schemas vocabularies and promoted binding contracts are language-neutral semantic authority | — |
| DEC-0156 | The official TypeScript consumer binding is distributed as @system-of-thought/adr-kit from this repository | — |
| DEC-0157 | Consumer Binding Contract 1.0 governs conformance across supported language bindings | — |
| DEC-0158 | Conformance is required only for the intersection of capabilities and contract versions advertised by bindings | — |
| DEC-0159 | Consumer Binding Contract 1.0 distinguishes structural semantic behavioral diagnostic and serialization equivalence | — |
| DEC-0160 | TypeScript consumes copy-exact generated mirrors of canonical schema bytes from schema/ | — |
| DEC-0161 | The first TypeScript release is read-only and excludes authoring identity allocation graph admission CLI MCP and repository writes | — |
| DEC-0162 | Browser-safe entry points exclude Node built-ins and filesystem behavior is available only through explicit Node subpaths | — |
| DEC-0163 | TypeScript v1 supports normalized model 2.1 evidence attribution 1.5 and 1.6 discovery loading and normalized semantic extensions | — |
| DEC-0164 | Binding-local deterministic fingerprints may be exposed but Python and TypeScript fingerprint equality is not a contract | — |
| DEC-0165 | Node repository loading is index-first manifest-aware additive-safe and never reparses source ADR YAML as a fallback | — |
| DEC-0166 | Node embodiment linkage preserves validated-derived-evidence authority ceiling and not-admitted graph status | — |
| DEC-0167 | PyPI and npm artifacts represent one ADR-Kit source release and do not create independent semantic version lineages | — |

### DEC-0155 — Accepted ADRs canonical schemas vocabularies and promoted binding contracts are language-neutral semantic authority

**Rationale**

Python and TypeScript implement authority; neither implementation becomes authoritative by existing.

### DEC-0156 — The official TypeScript consumer binding is distributed as @system-of-thought/adr-kit from this repository

**Rationale**

A shared repository and release lineage prevent a sibling semantic authority and independent language versioning.

### DEC-0157 — Consumer Binding Contract 1.0 governs conformance across supported language bindings

**Rationale**

An explicit contract makes capability overlap and observable equivalence testable without requiring implementation identity.

### DEC-0158 — Conformance is required only for the intersection of capabilities and contract versions advertised by bindings

**Rationale**

A narrow binding may qualify honestly without implementing every operation exposed by another binding.

### DEC-0159 — Consumer Binding Contract 1.0 distinguishes structural semantic behavioral diagnostic and serialization equivalence

**Rationale**

Structural and semantic agreement must not silently impose exact exception classes, bytes, hashes, or object layout.

### DEC-0160 — TypeScript consumes copy-exact generated mirrors of canonical schema bytes from schema/

**Rationale**

Generated mirrors can serve packaging but cannot become a second schema authority.

### DEC-0161 — The first TypeScript release is read-only and excludes authoring identity allocation graph admission CLI MCP and repository writes

**Rationale**

Consumer safety and authority ownership require a deliberately bounded first release.

### DEC-0162 — Browser-safe entry points exclude Node built-ins and filesystem behavior is available only through explicit Node subpaths

**Rationale**

Angular is a consumer environment, not an ADR-Kit framework dependency, and the browser is not filesystem authority.

### DEC-0163 — TypeScript v1 supports normalized model 2.1 evidence attribution 1.5 and 1.6 discovery loading and normalized semantic extensions

**Rationale**

Unsupported versions must fail explicitly rather than being accepted through historical implementation parity.

### DEC-0164 — Binding-local deterministic fingerprints may be exposed but Python and TypeScript fingerprint equality is not a contract

**Rationale**

A portable architecture snapshot digest would require a separate promoted decision and must not be invented here.

### DEC-0165 — Node repository loading is index-first manifest-aware additive-safe and never reparses source ADR YAML as a fallback

**Rationale**

Cross-language consumers must preserve compiler-owned discovery authority and required baseline ingestion.

### DEC-0166 — Node embodiment linkage preserves validated-derived-evidence authority ceiling and not-admitted graph status

**Rationale**

Evidence declarations and validated links do not become canonical architecture graph authority.

### DEC-0167 — PyPI and npm artifacts represent one ADR-Kit source release and do not create independent semantic version lineages

**Rationale**

Consumers need one release identity while package publication remains an operational release step.


## Capabilities

### CAP-9001 — Capability-Scoped Consumer Binding

Provide an explicit contract and capability manifest for conforming language bindings over ADR-Kit authority.

### CAP-9002 — TypeScript Node and Browser Consumer Distribution

Provide a read-only framework-neutral TypeScript package with explicit browser-safe and Node-only subpaths.




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0149 | Language bindings MUST implement accepted ADR schema vocabulary and explicitly promoted consumer contracts without… | MUST / design | automated |
| INV-0150 | Cross-language qualification MUST compare only capabilities and contract versions advertised by both bindings. | MUST / test | automated |
| INV-0151 | Packaged TypeScript schema assets MUST preserve the bytes of their canonical counterparts under root schema/. | MUST / test | automated |
| INV-0152 | Browser-safe package entry points MUST have no reachable Node built-in dependency and MUST have no Angular framework… | MUST / test | automated |
| INV-0153 | TypeScript v1 MUST perform no repository writes identity allocation graph admission authoring mutation network… | MUST / test | automated |
| INV-0154 | Node repository loading MUST require architecture-index.yaml manifest.yaml and the primary entity relationship and… | MUST / test | automated |
| INV-0155 | Embodiment linkage MUST preserve authority_ceiling validated_derived_evidence and graph_admission_status… | MUST / test | automated |
| INV-0156 | A binding MUST reject unsupported schema or contract versions explicitly and MUST NOT silently coerce them into a… | MUST / test | automated |

### INV-0149

**Statement**

Language bindings MUST implement accepted ADR schema vocabulary and explicitly promoted consumer contracts without redefining canonical identity or architecture semantics.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Semantic ownership remains in the repository authority corpus.

### INV-0150

**Statement**

Cross-language qualification MUST compare only capabilities and contract versions advertised by both bindings.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Capability discovery is part of the supported binding contract.

### INV-0151

**Statement**

Packaged TypeScript schema assets MUST preserve the bytes of their canonical counterparts under root schema/.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

A generated mirror must not drift into independent authority.

### INV-0152

**Statement**

Browser-safe package entry points MUST have no reachable Node built-in dependency and MUST have no Angular framework dependency.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Browser and Angular compatibility requires a framework-neutral ESM boundary.

### INV-0153

**Statement**

TypeScript v1 MUST perform no repository writes identity allocation graph admission authoring mutation network access or import-time side effects.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

The first binding is a safe consumer surface only.

### INV-0154

**Statement**

Node repository loading MUST require architecture-index.yaml manifest.yaml and the primary entity relationship and unresolved registries, while treating additive subsets as non-authoritative.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Required baseline ingestion is fixed by ADR-L-0013.

### INV-0155

**Statement**

Embodiment linkage MUST preserve authority_ceiling validated_derived_evidence and graph_admission_status not_admitted and MUST perform no graph writes.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

ADR-L-0020 keeps semantic linkage as derived evidence.

### INV-0156

**Statement**

A binding MUST reject unsupported schema or contract versions explicitly and MUST NOT silently coerce them into a supported semantic version.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Explicit failure prevents historical implementation behavior from becoming accidental authority.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0020](ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)

**References**
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0020](ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)





## Notes

Promoted from the locked Consumer Binding design brief by the ADR Kit promotion boundary.


---

*Generated from ADR-L-0024 by ADR Architecture Kit (projection v3)*