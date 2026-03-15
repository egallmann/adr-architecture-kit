<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: 1156c7298140084fb9bb7ecefb96288258366e0215dba030e00da49e1af12ac4
rendered_hash: 4b7fdad632772dc847be674d3ef4e3df36d555760fa4980e0b6d72e51946498e
-->

# ADR-PC-0005: Generated Artifact Integrity Validation

**Status:** proposed  
**Created:** 2026-03-15  
**Authors:** adr-architecture-kit  
**Domains:** integrity, validation, projections  

**Implements Logical:** ADR-L-0007, ADR-L-0013  
**Technologies:** python, sha256, yaml


---

## Context

Generated artifact integrity validation verifies freshness, tamper status,
integrity headers, and scope-local generated outputs. It is a distinct public
subsystem used by validator and governance flows.


## Technology Stack

### Python (language)

**Version:** 3.11

**Rationale:**
Existing implementation language.

### PyYAML (library)

**Version:** 6.x

**Rationale:**
Generated artifact inspection and parsing.



## Component Specifications

### COMP-0014: Generated Artifact Integrity Validation (service)

**Responsibilities:**
- Enumerate scope-local generated artifacts
- Validate integrity headers and source hashes
- Detect stale, tampered, or malformed generated outputs
- Support governance checks over generated artifacts


**Interfaces:**
- **IFACE-0015** (library_api): Public surfaces:
- GeneratedArtifactValidator
- generated artifact integrity result models
...

**Implementation Identifiers:**
- Module Path: `src/adr_kit/integrity/validation.py`




## Implementation Decisions

### IMPL-0015: Separate artifact integrity validation from discovery/indexing authority

**Rationale:**
Integrity validation is a runtime concern shared across generated artifact
kinds and deserves its own component authority.








---

*Generated from ADR-PC-0005 by ADR Architecture Kit*