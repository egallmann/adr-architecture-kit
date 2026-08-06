<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: a83ade634d2e75c85f571ff19a7b80b35b7f6fc2b0fc29577892b55dfa63ba21
rendered_hash: eeaafb2d25255a1153f4aec8ce3635f70518454104b5a11f30f7c7395244d452
-->

# ADR-PC-0002: Schema and Contract Validation

**Status:** proposed  
**Created:** 2026-03-15  
**Modified:** 2026-08-06  **Authors:** adr-architecture-kit  
**Domains:** validation, schema, contracts  

**Implements Logical:** ADR-L-0008, ADR-L-0010, ADR-L-0011  
**Technologies:** python, jsonschema, pydantic

**Related ADRs:** ADR-P-0002

---

## Context

Schema and contract validation is now a stable component boundary rather than
a generic legacy physical slice. It validates canonical ADR structure,
profile-specific contract requirements, project metadata, and implementation
attribution evidence.


## Technology Stack

### Python (language)

**Version:** 3.11

**Rationale:**
Existing implementation language.

### jsonschema (library)

**Version:** 4.x

**Rationale:**
Structural schema validation.

### Pydantic (library)

**Version:** 2.x

**Rationale:**
Typed contract and validation result models.



## Component Specifications

### COMP-0011: Schema and Contract Validation Surface (service)

**Responsibilities:**
- Validate canonical ADR artifacts against schema and business rules
- Validate kernel-facing contract profiles
- Validate project metadata and implementation attribution evidence
- Provide CLI entrypoints for validation workflows


**Interfaces:**
- **IFACE-0012** (CLI): Commands:
- adr validate
- adr validate-contract
- adr validate-project-metadata
- adr validate-gene...- **IFACE-0017** (library_api): A private validation application service supports both the compatibility-
preserved CLI adapter and ...

**Implementation Identifiers:**
- Module Path: `src/adr_kit/schema/contract_validation.py`




## Implementation Decisions

### IMPL-0012: Treat schema and contract validation as a component boundary

**Rationale:**
Validation surfaces are independently public, stable, and reused across CLI
and downstream canonicalization workflows.




### IMPL-0018: Translate shared validation service results at the public SDK boundary

**Rationale:**
CLI presentation and public SDK contracts have different compatibility
responsibilities. One private application service prevents divergent
validation semantics while adapters preserve CLI bytes and exclude validator
implementation objects from the SDK result graph.








---

*Generated from ADR-PC-0002 by ADR Architecture Kit*