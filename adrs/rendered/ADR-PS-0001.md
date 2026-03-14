<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-rendered-markdown
generator_version: 1
hash_algorithm: sha256
source_hash: 09b7408071a5fec62389b5eebab1e78defc3786e81e73e4273dbccd358ef10a3
rendered_hash: 4a32d70a08eed5f95fcdff61f5e73ce75f1a9138de238c06d6efc4eaab0ac676
-->

# ADR-PS-0001: ADR Architecture Kit Discovery and Indexing System

**Status:** proposed  
**Created:** 2026-03-13  
**Authors:** adr-architecture-kit  
**Domains:** discovery, indexing, tooling  

**Implements Logical:** ADR-L-0009  
**Technologies:** python, pyyaml, click


---

## Context

The discovery and indexing subsystem provides the derived surfaces that agents
query instead of scanning raw ADR bodies by default. It now includes
normalized discovery bundle generation under `adrs/index/`, legacy
compatibility registry generation under `adrs/entities/registry.yaml`,
manifest generation, rendered ADR markdown generation, CLI query surfaces over
generated registry state, and the unified `adr compile` orchestration path
that emits these derived discovery artifacts together.


## Technology Stack

### Python (language)

**Version:** 3.11

**Rationale:**
Existing adr-architecture-kit implementation language.

### PyYAML (library)

**Version:** 6.x

**Rationale:**
Deterministic YAML parsing and rendering for derived artifacts.

### Click (tooling)

**Version:** 8.x

**Rationale:**
Existing CLI surface for agent and human invocation.



## Component Specifications








---

*Generated from ADR-PS-0001 by ADR Architecture Kit*