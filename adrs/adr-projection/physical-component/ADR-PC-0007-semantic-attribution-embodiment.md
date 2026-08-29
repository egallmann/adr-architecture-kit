<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 2f67cf2de5306a040f3cea7b9486b6eda125be02799f03ddec5f1f4145eed6e7
rendered_hash: 2f673ff2b6c6721e5f1a3c4aa520b75f268b19ec58fcab92f5c0e77d29db0f2b
-->

# ADR-PC-0007: Semantic Attribution Embodiment

## Identity / Status

**Type:** physical-component  
**Status:** accepted  
**Alias:** ADR-PC-0007  
**Authoring contract:** authoring v1.5  
**Created:** 2026-08-13  
**Modified:** 2026-08-27  
**Authors:** adr-architecture-kit  
**Domains:** attribution, validation, decorators  
**Implements Logical:** [ADR-L-0004](../logical/ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md), [ADR-L-0020](../logical/ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)  
**Implements System:** [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)  

## Architecture Position

Physical-component ADRs author component, interface, and implementation entities. Topology is not authored here; neighborhood uses compiled semantic architecture edges plus structural bridges.

**Containing system(s):**
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**Logical authority implemented:**
- [ADR-L-0004](../logical/ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0020](../logical/ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)

**Component(s) owned by this ADR:**
- COMP-0022 — Semantic Attribution Embodiment (library)

**Component type(s):** library

**Authored purpose:**
- Embody ADR-L-0020 without moving source parsing into this repository.

**Provided interface types:** library_api, CLI

**Implementation location(s):**
- Primary implementation: src/adr_kit/decorators.py
- Entry point: src/adr_kit/cli/main.py
- Primary tests: tests/test_semantic_attribution_vocabulary_parity.py


## Architecture Neighborhood

```mermaid
flowchart LR
  n_019fee89_e615_7577_8d37_dd0df031bec9["ADR-L-0004<br/>ADR-to-Implementation Traceability via Decorators and Metadata Attribution"]
  n_019ffdba_3c42_70da_b33d_efc003269c42["ADR-PC-0007<br/>Semantic Attribution Embodiment"]
  n_019ffdba_3c42_7c4a_a737_f6751a265d60["ADR-L-0020<br/>Semantic Implementation Attribution and Cross-Layer Architecture Relationships"]
  n_019ffdba_3c42_70da_b33d_efc003269c42 -->|"implements_logical"| n_019fee89_e615_7577_8d37_dd0df031bec9
  n_019ffdba_3c42_70da_b33d_efc003269c42 -->|"implements_logical"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
```


### Semantic architecture inventory

- `implements_logical`: ADR-PC-0007 → ADR-L-0004
- `implements_logical`: ADR-PC-0007 → ADR-L-0020

### Component Relationships

**Provides interface**
- library_api (IFACE-0034)
  - `COMP-0022 -[:provides_interface]-> IFACE-0034`
- CLI (IFACE-0035)
  - `COMP-0022 -[:provides_interface]-> IFACE-0035`

**Implements logical authority**
- ADR-to-Implementation Traceability via Decorators and Metadata Attribution (ADR-L-0004)
  - `ADR-PC-0007 -[:implements_logical]-> ADR-L-0004`
- Semantic Implementation Attribution and Cross-Layer Architecture Relationships (ADR-L-0020)
  - `ADR-PC-0007 -[:implements_logical]-> ADR-L-0020`


## Neighbor Relationships

### ADR-L-0004 — ADR-to-Implementation Traceability via Decorators and Metadata Attribution

Semantic Attribution Embodiment (ADR-PC-0007)
    -[:implements_logical]->
ADR-to-Implementation Traceability via Decorators and Metadata Attribution (ADR-L-0004)

`ADR-PC-0007 -[:implements_logical]-> ADR-L-0004`

**Peer context:** Architecture Decision Records document why implementation artifacts exist, but
the repo still lacks a universal, machine-verifiable way to trace code,
infrastructure, configuration, schemas, pipelines, and scripts back to the
ADRs that justify them.

[Open projection](../logical/ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
### ADR-L-0020 — Semantic Implementation Attribution and Cross-Layer Architecture Relationships

Semantic Attribution Embodiment (ADR-PC-0007)
    -[:implements_logical]->
Semantic Implementation Attribution and Cross-Layer Architecture Relationships (ADR-L-0020)

`ADR-PC-0007 -[:implements_logical]-> ADR-L-0020`

**Peer context:** ADR-L-0004 established implementation attribution as an explicit intent
surface. ADR-L-0019 made canonical machine identity a lowercase UUIDv7.
Attribution evidence still cited human aliases (`ADR-L-*`, `INV-*`) and
could not name typed relationships to nested architecture entities.

[Open projection](../logical/ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)

## Context

Semantic attribution needs a kit-owned embodiment for vocabulary, evidence
models, UUID decorators, standalone shims, architecture-aware validation,
repository-aware versioned normalization, and a supported bidirectional
linkage facade. This component does not parse consumer source code, does not
own RECON extraction, and does not admit evidence to the architecture graph.


## Internal Structure

```mermaid
flowchart TB
  n_019ffdba_3c42_70da_b33d_efc003269c42["ADR-PC-0007<br/>Semantic Attribution Embodiment"]
  subgraph sg_component["component"]
    n_019ffdba_3c42_75d5_b93b_f32f35152e32["COMP-0022<br/>Semantic Attribution Embodiment"]
  end
  subgraph sg_interface["interface"]
    n_019ffdba_3c42_77f6_903f_7753342c5b5f["IFACE-0034<br/>library_api"]
    n_019ffdba_3c42_7d5b_b52f_b36c3000f299["IFACE-0035<br/>CLI"]
  end
  subgraph sg_implementation_decision["implementation_decision"]
    n_019ffdba_3c42_7e86_a03e_f7df07da6757["IMPL-0028<br/>Generate Python and TypeScript shims from the v1.5 vocabulary"]
    n_019ffdba_3c42_7021_923f_bf8e6bd06d07["IMPL-0029<br/>Keep legacy alias decorators separate from UUID claim composition"]
  end
  n_019ffdba_3c42_7021_923f_bf8e6bd06d07 -->|"declared_in"| n_019ffdba_3c42_70da_b33d_efc003269c42
  n_019ffdba_3c42_75d5_b93b_f32f35152e32 -->|"declared_in"| n_019ffdba_3c42_70da_b33d_efc003269c42
  n_019ffdba_3c42_77f6_903f_7753342c5b5f -->|"declared_in"| n_019ffdba_3c42_70da_b33d_efc003269c42
  n_019ffdba_3c42_7d5b_b52f_b36c3000f299 -->|"declared_in"| n_019ffdba_3c42_70da_b33d_efc003269c42
  n_019ffdba_3c42_7e86_a03e_f7df07da6757 -->|"declared_in"| n_019ffdba_3c42_70da_b33d_efc003269c42
  n_019ffdba_3c42_75d5_b93b_f32f35152e32 -->|"provides_interface"| n_019ffdba_3c42_77f6_903f_7753342c5b5f
  n_019ffdba_3c42_75d5_b93b_f32f35152e32 -->|"provides_interface"| n_019ffdba_3c42_7d5b_b52f_b36c3000f299
```

- `component` COMP-0022 — Semantic Attribution Embodiment
- `implementation_decision` IMPL-0028 — Generate Python and TypeScript shims from the v1.5 vocabulary
- `implementation_decision` IMPL-0029 — Keep legacy alias decorators separate from UUID claim composition
- `interface` IFACE-0034 — library_api
- `interface` IFACE-0035 — CLI

## Type-specific Detail

### Before You Change This Component
**Must preserve:**
- Must not load architecture state from legacy decorators or shim generation
- Must not write relationship registries or Architecture IR from evidence verbs
- Must expose only immutable supported contracts through `adr_kit.api`
- Must not write evidence input, Architecture IR relationships, or graph state

**Public / exposed interfaces:**
- IFACE-0034 — library_api
- IFACE-0035 — CLI

**Verify with:**
- 1.0/1.2 callers of validate_implementation_attribution_evidence remain compatible
- v1.5 validation keeps historical behavior; v1.6 adds declared-only enforcement
- Python and TypeScript shims are generated from one vocabulary
- installed-wheel consumers use the linkage feature without private imports
- tests/test_semantic_attribution_vocabulary_parity.py
- >= 80%
- - Vocabulary parity across schema, Pydantic, decorators, and shims
- Version-aware confidence and loss-aware normalization matrices
- Public bidirectional linkage and partial-result behavior
- Retained-wheel public consumer and packaged v1.6 resource checks
- Legacy decorator no architecture load
- Repository-aware 1.0/1.2 normalization idempotency


### COMP-0022: Semantic Attribution Embodiment

**Type:** library

**Purpose:**

Embody ADR-L-0020 without moving source parsing into this repository.

**Responsibilities:**

- Load versioned mechanical v1.5/v1.6 semantic attribution vocabularies
- Parse and validate 1.0/1.2/1.5/1.6 implementation attribution evidence
- Provide UUID claim decorators and vocabulary-driven Python/TypeScript shims
- Resolve claim targets against ArchitectureRepository / model 2.0
- Normalize supported evidence into explicitly selected lossless targets
- Build a deterministic non-authoritative bidirectional linkage projection

**Key Responsibilities:**
- Keep legacy alias decorators as metadata-only producers
- Compose `__architecture_attribution_claims__` only from UUID decorators
- Fail closed on unresolved UUIDs, illegal matrix pairs, and true duplicates
- Preserve independent evidence occurrences behind unique semantic links

**Must Remain True:**
- Must not load architecture state from legacy decorators or shim generation
- Must not write relationship registries or Architecture IR from evidence verbs
- Must expose only immutable supported contracts through `adr_kit.api`
- Must not write evidence input, Architecture IR relationships, or graph state

**Success Criteria:**
- 1.0/1.2 callers of validate_implementation_attribution_evidence remain compatible
- v1.5 validation keeps historical behavior; v1.6 adds declared-only enforcement
- Python and TypeScript shims are generated from one vocabulary
- installed-wheel consumers use the linkage feature without private imports


### IFACE-0034 — library_api

**Type:** library_api

**Specification:**

Public and de facto public surfaces:

- adr_kit.decorators implements/enforces/embodies UUID APIs
- adr_kit.decorators legacy implements_adr / enforces_invariant APIs
- validate_implementation_attribution_evidence
- normalize_attribution_evidence
- adr_kit.api build_embodiment_linkage and immutable request/result contracts
- schema/evidence-attribution/v1.5 and v1.6 vocabulary/evidence JSON

### IFACE-0035 — CLI

**Type:** CLI

**Specification:**

Commands:

- adr attribution check
- adr attribution coverage
- adr attribution generate-shim
- adr attribution workspace-report
- adr attribution normalize-evidence --scope --input [--output] [--target-version]
- adr attribution linkage-report --scope --evidence [direction filters]


### IMPL-0028 — Generate Python and TypeScript shims from the v1.5 vocabulary

**Decision:**

Generate Python and TypeScript shims from the v1.5 vocabulary

**Rationale:**

Hand-copied shim strings drift from native decorators. One mechanical
versioned vocabulary is the source for relationship names, allowed types,
confidence policy, and generated standalone shims. Explicit native
functions remain stable and parity tests prevent runtime vocabulary drift.

### IMPL-0029 — Keep legacy alias decorators separate from UUID claim composition

**Decision:**

Keep legacy alias decorators separate from UUID claim composition

**Rationale:**

Last-write-wins legacy metadata remains a Stable surface. New UUID
decorators compose `__architecture_attribution_claims__` with
`confidence: declared` and must not overwrite `__implements_adrs__` or
`__enforces_invariants__`.


## Engineering Contract

### Failure Semantics

Fail closed on invalid schema, unresolved UUID, illegal matrix pair, and true duplicate evidence.

### Observability

**Logging:**
- Level: info
- Structured: false

**Metrics:**
- attribution_validations_total (counter)

### Verification

**Unit test coverage:** >= 80%

**Integration tests:**

- Vocabulary parity across schema, Pydantic, decorators, and shims
- Version-aware confidence and loss-aware normalization matrices
- Public bidirectional linkage and partial-result behavior
- Retained-wheel public consumer and packaged v1.6 resource checks
- Legacy decorator no architecture load
- Repository-aware 1.0/1.2 normalization idempotency


## Implementation Locations

| Role | Location |
| --- | --- |
| Primary implementation | `src/adr_kit/decorators.py` |
| Entry point | `src/adr_kit/cli/main.py` |
| Primary tests | `tests/test_semantic_attribution_vocabulary_parity.py` |



## Technology Stack

### Python (language)
**Version:** >=3.14

**Rationale:**
Minimum supported Python minor is 3.14 (`requires-python >=3.14`); currently qualified released minor line is 3.14; repository reference interpreter is currently 3.14.7; new GA Python minors require explicit qualification before support is advertised.

### Pydantic (library)
**Version:** 2.x

**Rationale:**
Typed evidence and claim models.

### jsonschema (library)
**Version:** 4.x

**Rationale:**
Structural schema validation for 1.0/1.2/1.5/1.6 evidence.






---

*Generated from ADR-PC-0007 by ADR Architecture Kit (projection v3)*