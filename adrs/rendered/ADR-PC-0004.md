<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: 1ba02529b44559b7f25d4f65c4d4cee32e0d88ffc51844efee4bae949c1d4a65
rendered_hash: d7868449e98473b60f2ae8f127e09d3b1aa6a9b08d1045dbeca7d7ee8c8396b0
-->

# ADR-PC-0004: Repository Boundary and Normalized Semantic Model

**Status:** proposed  
**Created:** 2026-03-15  
**Modified:** 2026-08-05  **Authors:** adr-architecture-kit  
**Domains:** repository, semantic-model, tooling  

**Implements Logical:** ADR-L-0013  
**Technologies:** python, yaml, pydantic


---

## Context

ArchitectureRepository and NormalizedArchitectureModel are now the stable
in-process semantic boundary for consumers. This component captures that
consumer contract and keeps interpretation centralized without creating a
broader SDK facade or changing the normalized model in Phase 0.


## Technology Stack

### Python (language)

**Version:** 3.11

**Rationale:**
Existing implementation language.

### Pydantic (library)

**Version:** 2.x

**Rationale:**
Typed normalized semantic models.



## Component Specifications

### COMP-0013: Repository Boundary Component (service)

**Responsibilities:**
- Load compiled architecture bundle artifacts
- Expose normalized semantic queries to in-process consumers
- Centralize provenance, unresolved, and ADR/status lookup logic
- Prevent ad hoc re-interpretation of compiled registries


**Interfaces:**
- **IFACE-0014** (library_api): Public surfaces:
- ArchitectureRepository
- NormalizedArchitectureModel
- registry loader and reposi...

**Implementation Identifiers:**
- Module Path: `src/adr_kit/repository/architecture_repository.py`




## Implementation Decisions

### IMPL-0014: Treat the repository/model boundary as a first-class component

**Rationale:**
The repository boundary is stable runtime behavior and should be documented
as its own component authority.




### IMPL-0017: Defer a narrow facade and constrain future Assembler dependencies

**Rationale:**
Phase 0 preserves `ArchitectureRepository` and
`NormalizedArchitectureModel` exactly as the present consumer seam. A later
narrow facade may wrap supported interfaces, but it is not created here.
A future Assembler may depend only on that supported seam and must not bind
to compiler IR, compiler passes, raw ADR parsing, or generated-file layout.








---

*Generated from ADR-PC-0004 by ADR Architecture Kit*