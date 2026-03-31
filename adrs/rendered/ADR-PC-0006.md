<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: 8cb16f696a38b3c40ce6fe46946d1154f099cbbb89cdfad1fa7cc1d05f363dea
rendered_hash: bf8093767ec9a7bfcc714e7c866e8368e4b45bd97f8ba94b3723f420be8b9288
-->

# ADR-PC-0006: Brownfield Onboarding and Canonical Normalization

**Status:** proposed  
**Created:** 2026-03-15  
**Authors:** adr-architecture-kit  
**Domains:** migration, onboarding, normalization  

**Implements Logical:** ADR-L-0011, ADR-L-0014  
**Technologies:** python, yaml, click


---

## Context

adr-architecture-kit already includes migration and normalization behavior in
its migrator and CLI surfaces. This component makes brownfield onboarding and
canonical normalization an explicit part of the compiler/validation runtime.


## Technology Stack

### Python (language)

**Version:** 3.11

**Rationale:**
Existing implementation language.

### Click (tooling)

**Version:** 8.x

**Rationale:**
Existing CLI surface for migration workflows.



## Component Specifications

### COMP-0015: Brownfield Onboarding and Canonical Normalization (service)

**Responsibilities:**
- Detect canonical entity ID collisions
- Apply deterministic canonical ID remaps
- Write canonical migration ledgers
- Support brownfield onboarding cleanup as governed normalization rather than ad hoc editing


**Interfaces:**
- **IFACE-0016** (CLI): Commands:
- adr normalize-canonical-ids
Public modules:
- src/adr_kit/migrators/canonical_id_normali...

**Implementation Identifiers:**
- Module Path: `src/adr_kit/migrators/canonical_id_normalizer.py`




## Implementation Decisions

### IMPL-0016: Treat brownfield onboarding and canonical normalization as an explicit component capability

**Rationale:**
Migration logic is part of the usable onboarding path for STE adoption and
should be documented as an intentional system capability rather than hidden
utility behavior.








---

*Generated from ADR-PC-0006 by ADR Architecture Kit*