<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: c6ddad32aece61860fdb070e5763c738aafe403b0cd67fd5548e0948550d46d4
rendered_hash: cc784dee4ae026195e4e1344e9f3916daaf32a1a9f8a92e4ea6146da159a29a6
-->

# ADR-PC-0003: Compiler Pipeline and Driver

**Status:** proposed  
**Created:** 2026-03-15  
**Authors:** adr-architecture-kit  
**Domains:** compiler, pipeline, tooling  

**Implements Logical:** ADR-L-0007, ADR-L-0009, ADR-L-0013  
**Technologies:** python, yaml, click


---

## Context

The compiler driver and explicit pipeline now own deterministic architecture
compilation across parse, analysis, emission, and recursive scope
orchestration. This component documents that public compile boundary.


## Technology Stack

### Python (language)

**Version:** 3.11

**Rationale:**
Existing compiler implementation language.

### Click (tooling)

**Version:** 8.x

**Rationale:**
CLI orchestration for compile entrypoints.



## Component Specifications

### COMP-0012: Compiler Pipeline and Driver (service)

**Responsibilities:**
- Build compiler pipeline state from canonical scope inputs
- Execute deterministic pass ordering
- Emit architecture bundle, manifest, graph, and rendered outputs
- Support recursive multi-scope compilation and reporting


**Interfaces:**
- **IFACE-0013** (CLI): Commands:
- adr compile
- adr generate-architecture-index
- adr generate-manifest
- adr generate-ren...

**Implementation Identifiers:**
- Service Name: `adr-compiler`
- Module Path: `src/adr_kit/compiler/driver.py`




## Implementation Decisions

### IMPL-0013: Keep compiler orchestration as a dedicated component

**Rationale:**
The explicit pipeline and driver are now stable public runtime behavior and
should not remain implicit inside a generic toolkit ADR.








---

*Generated from ADR-PC-0003 by ADR Architecture Kit*