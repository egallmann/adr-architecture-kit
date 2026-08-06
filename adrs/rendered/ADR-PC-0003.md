<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: e35f15575d017ff63c78983057ab02e09256f03287e82c719db12f8485cc43d4
rendered_hash: 4c8aee1f0c8895c1a7e06fba6fcd2a0651a033ff31d61ee64f85bf1480b0c43a
-->

# ADR-PC-0003: Compiler Pipeline and Driver

**Status:** proposed  
**Created:** 2026-03-15  
**Modified:** 2026-08-05  **Authors:** adr-architecture-kit  
**Domains:** compiler, pipeline, tooling  

**Implements Logical:** ADR-L-0007, ADR-L-0009, ADR-L-0013  
**Technologies:** python, yaml, click


---

## Context

The compiler driver and explicit pipeline now own deterministic architecture
compilation across parse, analysis, emission, and recursive scope
orchestration. The command-line behavior is compatibility-relevant, while the
Python compiler pipeline, passes, `ArchModel`, emitters, and result plumbing are
internal reference implementation and are not a supported SDK facade.


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
- Preserve existing CLI commands, options, outputs, diagnostics, and exit behavior


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
The explicit pipeline and driver are a dedicated authoring-time implementation
component. Their CLI behavior and generated compatibility surfaces are guarded,
but their Python internals remain evolvable and must not be described as a
stable public runtime API.








---

*Generated from ADR-PC-0003 by ADR Architecture Kit*