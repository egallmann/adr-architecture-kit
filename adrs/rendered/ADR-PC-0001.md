<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: 30a8d9affb55079c4edbd4a93c312337749b26254a000775cb4b97dbfb0925e7
rendered_hash: a2bedadadff2b8ba74b79f5c5c533d28d6fcf107f87304f9f71c7d6339062487
-->

# ADR-PC-0001: Entity Registry and Discovery Index

**Status:** proposed  
**Created:** 2026-03-13  
**Authors:** adr-architecture-kit  
**Domains:** discovery, indexing, tooling  

**Implements Logical:** ADR-L-0009, ADR-L-0012  
**Technologies:** python, pyyaml, click


---

## Context

The discovery/indexing component now centers on the unified compiler path. It
generates the normalized discovery bundle under `adrs/index/`, emits the
legacy compatibility registry at `adrs/entities/registry.yaml`, generates
manifest and rendered ADR markdown outputs through the same compiler-owned
path for single-scope use, and exposes exact-ID and filtered CLI query
operations over generated registry state.


## Technology Stack

### Python (language)

**Version:** 3.11

**Rationale:**
Existing adr-architecture-kit implementation language.

### PyYAML (library)

**Version:** 6.x

**Rationale:**
Stable YAML parsing and rendering for registry artifacts.

### Click (tooling)

**Version:** 8.x

**Rationale:**
Existing CLI framework for scope-aware commands.



## Component Specifications

### COMP-0010: Entity Registry Generator and Query Surface (service)

**Responsibilities:**
- Compile canonical ADR and invariant artifacts into a normalized discovery bundle
- Emit deterministic `adrs/index/*.yaml` registry artifacts
- Emit deterministic legacy compatibility registry output at `adrs/entities/registry.yaml`
- Support manifest and rendered markdown emission through the unified compile path
- Provide CLI query access over generated registry state


**Interfaces:**
- **IFACE-0011** (CLI): Commands:
- adr compile
- adr generate-architecture-index
- adr generate-manifest
- adr generate-ren...

**Implementation Identifiers:**
- Service Name: `adr-compiler`
- Module Path: `src/adr_kit/compiler/driver.py`




## Implementation Decisions

### IMPL-0011: Route single-scope discovery generation through the unified compiler driver

**Rationale:**
The unified compiler path keeps normalized registries, the legacy
compatibility registry, manifest generation, and rendered markdown emission
aligned while preserving the older single-scope commands as compatibility
wrappers. Registry backend emission remains compiler-owned rather than
isolated in the older standalone registry generator.








---

*Generated from ADR-PC-0001 by ADR Architecture Kit*