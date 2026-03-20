<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: b81cf9555f2115819ab5eb18923c45eb30272437bf8a797ca3a629c591be0aed
rendered_hash: 41c04bc145b9bb2feb5ac86073790ff91b7e2ff2300529ae848da32e3435803e
-->

# ADR-PC-0004: Repository Boundary and Normalized Semantic Model

**Status:** proposed  
**Created:** 2026-03-15  
**Authors:** adr-architecture-kit  
**Domains:** repository, semantic-model, tooling  

**Implements Logical:** ADR-L-0013  
**Technologies:** python, yaml, pydantic


---

## Context

ArchitectureRepository and NormalizedArchitectureModel are now the stable
in-process semantic boundary for consumers. This component captures that
runtime contract and keeps consumer-side interpretation centralized.


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








---

*Generated from ADR-PC-0004 by ADR Architecture Kit*