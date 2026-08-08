<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: ace28f2bb60de0ec6a6e0af2826aa3714aed63cb582c35dd12d8f09c74810eeb
rendered_hash: bcf2a9d04ab90e8b9aee15079cbfa57672cce1db59dddd2946802c0b04b79e83
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

ArchitectureRepository and NormalizedArchitectureModel are the stable
in-process semantic boundary for consumers. Phase 1 adds a narrow supported
authoring facade that reuses those contracts without wrapping or changing the
normalized model and without making registry loaders or path helpers public.


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
...- **IFACE-0019** (library_api): `adr_kit.api.open_repository` resolves an explicit project root, eagerly
loads it, and returns the e...

**Implementation Identifiers:**
- Module Path: `src/adr_kit/repository/architecture_repository.py`




## Implementation Decisions

### IMPL-0014: Treat the repository/model boundary as a first-class component

**Rationale:**
The repository boundary is stable runtime behavior and should be documented
as its own component authority.




### IMPL-0017: Record the Phase 0 facade deferral and constrain future Assembler dependencies

**Rationale:**
Phase 0 preserved `ArchitectureRepository` and
`NormalizedArchitectureModel` exactly as the consumer seam and deferred a
facade. Phase 1 completes that bounded deferral through IFACE-0019 without
wrapping or changing either contract.
A future Assembler may depend only on that supported seam and must not bind
to compiler IR, compiler passes, raw ADR parsing, or generated-file layout.




### IMPL-0020: Reuse private normalized-bundle assembly across repository and SDK compilation

**Rationale:**
Constructing the detached SDK model from the same emitted registry bytes and
private assembly logic used by ArchitectureRepository prevents semantic and
fingerprint drift while preserving the normalized model's existing shape and
behavior.








---

*Generated from ADR-PC-0004 by ADR Architecture Kit*