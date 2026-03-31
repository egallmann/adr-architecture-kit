<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: 68d6b052ed91d897467a63a0cc45fe7d3ce51043efbb375ce78582d93dc2b502
rendered_hash: 815051175ff9542379b7a014976c27fd3276b5edece9eb0a26cf69ac95b3516e
-->

# ADR-PS-0002: ADR Kit Compiler and Validation Runtime

**Status:** proposed  
**Created:** 2026-03-15  
**Authors:** adr-architecture-kit  
**Domains:** compiler, validation, tooling  
**Tags:** compiler, validation, runtime, python  
**Implements Logical:** ADR-L-0001, ADR-L-0007, ADR-L-0008, ADR-L-0010, ADR-L-0011, ADR-L-0013  
**Technologies:** python, click, pydantic, yaml, json-schema

**Related ADRs:** ADR-P-0001, ADR-P-0002

---

## Context

adr-architecture-kit now operates as a compiler and validation runtime rather
than a collection of unrelated generators. The implementation includes an
explicit compiler pipeline, contract validation, normalized repository/model
access, integrity verification, and CLI orchestration over those surfaces.

This ADR establishes the concrete runtime system boundary for those public
capabilities. Discovery and indexing remain covered by ADR-PS-0001; this ADR
covers the compiler/validation runtime that powers canonical parsing,
compilation, repository loading, contract checks, and artifact integrity.


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