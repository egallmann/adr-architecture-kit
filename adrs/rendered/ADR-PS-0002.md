<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: a2e3a118ebc9f86fa50c8e110dc1af6a66c955a60d2cc5504e6493948e23dd21
rendered_hash: 07ccb310a1f487b3c4bafd8cfb7db305533b3ad19892d40f50b728ab40fb606b
-->

# ADR-PS-0002: ADR Kit Authoring Compiler and Validation System

**Status:** proposed  
**Created:** 2026-03-15  
**Modified:** 2026-08-05  **Authors:** adr-architecture-kit  
**Domains:** compiler, validation, tooling  
**Tags:** compiler, validation, authoring, python  
**Implements Logical:** ADR-L-0001, ADR-L-0007, ADR-L-0008, ADR-L-0010, ADR-L-0011, ADR-L-0013  
**Technologies:** python, click, pydantic, yaml, json-schema

**Related ADRs:** ADR-P-0001, ADR-P-0002

---

## Context

adr-architecture-kit operates as an authoring-time compiler and validation system rather
than a collection of unrelated generators. The implementation includes an
explicit compiler pipeline, contract validation, normalized repository/model
access, integrity verification, and CLI orchestration over those surfaces.

This ADR establishes the concrete authoring/compiler system boundary for those public
capabilities. Discovery and indexing remain covered by ADR-PS-0001; this ADR
covers the authoring/compiler implementation that powers canonical parsing,
compilation, repository loading, contract checks, and artifact integrity.

The boundary explicitly excludes Assembler behavior, runtime observation or
evidence extraction, rules execution, substrate management, admission decisions,
MCP surfaces, and LLM responsibilities. Those belong to later work or sibling
systems and must not be introduced by Phase 0 production hardening.


## Technology Stack

### Python (language)

**Version:** 3.11

**Rationale:**
Existing implementation language for compiler and validator code.

### Click (tooling)

**Version:** 8.x

**Rationale:**
Existing CLI surface for compile and validate operations.

### Pydantic (library)

**Version:** 2.x

**Rationale:**
Typed canonical models and validation.

### jsonschema (library)

**Version:** 4.x

**Rationale:**
Structural schema validation for canonical artifacts.



## Component Specifications






## Operational Requirements

### Monitoring
Deterministic validation and compilation output with explicit diagnostics.

### Logging
CLI-visible diagnostic logging with fail-closed validation behavior.




---

*Generated from ADR-PS-0002 by ADR Architecture Kit*