<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: 5c14ecfd15f4fd656f9e9e72285df4b9ee674b8115a3a923368b2ba152e4b8fa
rendered_hash: b8cb812226027141d9254c6c70286f08b0dfc9cb9826265e52224822aeefd90c
-->

# ADR-PC-0002: Schema and Contract Validation

**Status:** proposed  
**Created:** 2026-03-15  
**Authors:** adr-architecture-kit  
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
- adr validate-gene...

**Implementation Identifiers:**
- Module Path: `src/adr_kit/schema/contract_validation.py`




## Implementation Decisions

### IMPL-0012: Treat schema and contract validation as a component boundary

**Rationale:**
Validation surfaces are independently public, stable, and reused across CLI
and downstream canonicalization workflows.








---

*Generated from ADR-PC-0002 by ADR Architecture Kit*