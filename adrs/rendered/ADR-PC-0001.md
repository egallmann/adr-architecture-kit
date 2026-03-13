<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: 2a22ff7965ba74f5e1dc9644c9a967962c235bbf6adea21b5b4dd6df14ce6f11
rendered_hash: 22c913c7239cd304ac73c8f84059712d9842c6fb47cefb2bd2b56b919a33101f
-->

# ADR-PC-0001: Entity Registry and Discovery Index

**Status:** proposed  
**Created:** 2026-03-13  
**Authors:** adr-architecture-kit  
**Domains:** discovery, indexing, tooling  

**Implements Logical:** ADR-L-0009  
**Technologies:** python, pyyaml, click


---

## Context

The Entity Registry component generates `adrs/entities/registry.yaml` from
canonical ADR and standalone invariant artifacts, validates deterministic
regeneration, and exposes exact-ID and filtered CLI query operations over the
generated registry artifact.


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
- Scan canonical ADR and invariant artifacts
- Normalize explicit architecture entities into registry records
- Emit deterministic `adrs/entities/registry.yaml`
- Provide CLI query access over generated registry state


**Interfaces:**
- **IFACE-0011** (CLI): Commands:
- adr generate-entity-registry
- adr entities list
- adr entities get <id>
- adr entities ...

**Implementation Identifiers:**
- Module Path: `src/adr_kit/generators/entity_registry_generator.py`




## Implementation Decisions

### IMPL-0011: Use one normalized entities list for the registry wire shape

**Rationale:**
A single normalized entity collection is easier for agents to filter and
query deterministically than multiple top-level sections with divergent
shapes.








---

*Generated from ADR-PC-0001 by ADR Architecture Kit*