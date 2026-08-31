<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 215e05f6e952ceb4501e19cf44d4acab387358e9c79d74abf7ef1ea15c72b6b9
rendered_hash: 23df5fd026329864dd4f18a6d3375caab41a112aad692088b2497eab2d9ffed6
-->

# ADR-PC-0008: Project Scope Resolution

## Identity / Status

**Type:** physical-component  
**Status:** accepted  
**Alias:** ADR-PC-0008  
**Authoring contract:** authoring v1.5  
**Created:** 2026-08-28  
**Authors:** adr-architecture-kit  
**Domains:** implementation, adr, python, scope-resolution  
**Tags:** python, scope-resolution, multi-scope  
**Implements Logical:** [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)  
**Implements System:** [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md), [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)  

## Architecture Position

Physical-component ADRs author component, interface, and implementation entities. Topology is not authored here; neighborhood uses compiled semantic architecture edges plus structural bridges.

**Containing system(s):**
- [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**Logical authority implemented:**
- [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)

**Component(s) owned by this ADR:**
- COMP-0017 — Project Scope Resolver (library)

**Component type(s):** library

**Authored purpose:**
- Resolve project scope boundaries for multi-scope ADR operations.

**Provided interface types:** library_api

**Implementation location(s):**
- Primary implementation: src/adr_kit/scope/


## Architecture Neighborhood

```mermaid
flowchart LR
  n_019fee89_e615_7f19_810b_c7b33a9d9e0d["ADR-L-0002<br/>Multi-Scope ADR Architecture for Sub-Module Development"]
  n_01a048d8_454a_7464_bcaa_718fa77bed6a["ADR-PC-0008<br/>Project Scope Resolution"]
  n_01a048d8_454a_7464_bcaa_718fa77bed6a -->|"implements_logical"| n_019fee89_e615_7f19_810b_c7b33a9d9e0d
```


### Semantic architecture inventory

- `implements_logical`: ADR-PC-0008 → ADR-L-0002

### Component Relationships

**Provides interface**
- library_api (IFACE-0021)
  - `COMP-0017 -[:provides_interface]-> IFACE-0021`
- library_api (IFACE-0025)
  - `COMP-0017 -[:provides_interface]-> IFACE-0025`

**Implements logical authority**
- Multi-Scope ADR Architecture for Sub-Module Development (ADR-L-0002)
  - `ADR-PC-0008 -[:implements_logical]-> ADR-L-0002`


## Neighbor Relationships

### ADR-L-0002 — Multi-Scope ADR Architecture for Sub-Module Development

Project Scope Resolution (ADR-PC-0008)
    -[:implements_logical]->
Multi-Scope ADR Architecture for Sub-Module Development (ADR-L-0002)

`ADR-PC-0008 -[:implements_logical]-> ADR-L-0002`

**Peer context:** The adr-architecture-kit is being actively developed in a single workspace alongside
multiple sub-modules (ste-runtime, future services) that will eventually become
independent services. Each sub-module needs to leverage the ADR system for its own
architectural documentation while being developed in parallel within the monorepo.

[Open projection](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)

## Context

Permanent physical-component authority for multi-scope project-root detection,
scope boundary validation, and scope-resolution semantics per ADR-L-0002.
Rehomes preserved nested identity from retired ADR-P-0003 (COMP-0017) into
governed PS+PC authority without topology authoring in this document.


## Internal Structure

```mermaid
flowchart TB
  n_01a048d8_454a_7464_bcaa_718fa77bed6a["ADR-PC-0008<br/>Project Scope Resolution"]
  subgraph sg_component["component"]
    n_019fee89_e618_719b_bb3a_f13ab0906811["COMP-0017<br/>Project Scope Resolver"]
  end
  subgraph sg_interface["interface"]
    n_019fee89_e618_717e_933f_f02a053e8ac5["IFACE-0021<br/>library_api"]
    n_019fee89_e618_79e6_8b3f_27b30946373a["IFACE-0025<br/>library_api"]
  end
  subgraph sg_implementation_decision["implementation_decision"]
    n_019fee89_e618_76f2_b72f_5316b89484aa["IMPL-0022<br/>Adopt Red-Green-Refactor TDD Methodology"]
    n_019fee89_e618_722c_b527_14eb4ee67d88["IMPL-0024<br/>Use Dataclasses for ProjectScope"]
  end
  n_019fee89_e618_717e_933f_f02a053e8ac5 -->|"declared_in"| n_01a048d8_454a_7464_bcaa_718fa77bed6a
  n_019fee89_e618_719b_bb3a_f13ab0906811 -->|"declared_in"| n_01a048d8_454a_7464_bcaa_718fa77bed6a
  n_019fee89_e618_722c_b527_14eb4ee67d88 -->|"declared_in"| n_01a048d8_454a_7464_bcaa_718fa77bed6a
  n_019fee89_e618_76f2_b72f_5316b89484aa -->|"declared_in"| n_01a048d8_454a_7464_bcaa_718fa77bed6a
  n_019fee89_e618_79e6_8b3f_27b30946373a -->|"declared_in"| n_01a048d8_454a_7464_bcaa_718fa77bed6a
  n_019fee89_e618_719b_bb3a_f13ab0906811 -->|"provides_interface"| n_019fee89_e618_717e_933f_f02a053e8ac5
  n_019fee89_e618_719b_bb3a_f13ab0906811 -->|"provides_interface"| n_019fee89_e618_79e6_8b3f_27b30946373a
```

- `component` COMP-0017 — Project Scope Resolver
- `implementation_decision` IMPL-0022 — Adopt Red-Green-Refactor TDD Methodology
- `implementation_decision` IMPL-0024 — Use Dataclasses for ProjectScope
- `interface` IFACE-0021 — library_api
- `interface` IFACE-0025 — library_api

## Type-specific Detail

### Before You Change This Component
**Must preserve:**
- Scope metadata must remain deterministic for unchanged repository layout
- Parent-child scope relationships must be explicit and testable

**Public / exposed interfaces:**
- IFACE-0021 — library_api
- IFACE-0025 — library_api

**Verify with:**
- Scope auto-detection works from any nested working directory
- Recursive discovery returns independent per-scope metadata
- Unit tests for marker detection
- Unit tests for boundary enforcement
- Unit tests for recursive discovery
- Integration tests with real directory structures


### COMP-0017: Project Scope Resolver

**Type:** library

**Description:**

Python module implementing project scope detection and resolution
per ADR-L-0002 INV-0015 marker hierarchy

**Purpose:**

Resolve project scope boundaries for multi-scope ADR operations.

**Responsibilities:**

- Detect project boundaries using marker files
- Enforce workspace boundaries (INV-0018)
- Support explicit scope override
- Discover sub-module scopes recursively
- Maintain parent-child scope relationships

**Key Responsibilities:**
- Detect project boundaries using marker hierarchy (ADR-L-0002 INV-0015)
- Enforce workspace boundaries (INV-0018)
- Support explicit scope override and recursive discovery

**Must Remain True:**
- Scope metadata must remain deterministic for unchanged repository layout
- Parent-child scope relationships must be explicit and testable

**Success Criteria:**
- Scope auto-detection works from any nested working directory
- Recursive discovery returns independent per-scope metadata


### IFACE-0021 — library_api

**Type:** library_api

**Specification:**

ProjectScope dataclass exposes immutable scope metadata: root, adr_dir, manifest_path, marker, name, is_sub_module, parent_scope.

### IFACE-0025 — library_api

**Type:** library_api

**Specification:**

ProjectScopeResolver.resolve(start_dir) -> ProjectScope and resolve_recursive(start_dir) -> List[ProjectScope].


### IMPL-0022 — Adopt Red-Green-Refactor TDD Methodology

**Decision:**

Adopt Red-Green-Refactor TDD Methodology

**Rationale:**

Test-Driven Development is architecturally aligned with STE principles:
1. **SYS-2 (Deterministic Cognition)**: Tests enforce deterministic behavior
2. **SYS-4 (Drift Prevention)**: Tests detect implementation drift immediately
3. **PRIME-1 (No Implicit Assumptions)**: Tests make behavior explicit
4. **INV-0001 (Schema Validation)**: Tests prove validation correctness

This is a governance tool that validates other systems - it MUST be provably
correct. TDD provides executable specification, immediate feedback, refactoring
safety, and living documentation.

### IMPL-0024 — Use Dataclasses for ProjectScope

**Decision:**

Use Dataclasses for ProjectScope

**Rationale:**

Dataclasses provide immutable, type-safe scope metadata with minimal
boilerplate. Aligns with modern Python best practices.

**Alternatives Considered:**

| Alternative | Rejected Because |
| --- | --- |
| Named tuples | Less readable, no default values |
| Regular classes | More boilerplate, mutable by default |

**Consequences:**
- Requires Python 3.7+ (already required)
- Clear, type-checked scope objects
- Easy serialization for debugging


## Engineering Contract

### Verification

**Testing requirements:**
- Unit tests for marker detection
- Unit tests for boundary enforcement
- Unit tests for recursive discovery
- Integration tests with real directory structures

### Dependencies
- pathlib.Path
- dataclasses.dataclass
- typing (Optional, List)
- yaml (for PROJECT.yaml parsing)


## Implementation Locations

| Role | Location |
| --- | --- |
| Primary implementation | `src/adr_kit/scope/` |


## Lineage / Migration

| Entity Type | Historical Alias | Current Alias | Source |
| --- | --- | --- | --- |
| component | COMP-0001 | COMP-0017 | /component_specifications/0/id |
| implementation_decision | IMPL-0001 | IMPL-0022 | /implementation_decisions/0/id |
| implementation_decision | IMPL-0002 | IMPL-0024 | /implementation_decisions/1/id |
| interface | IFACE-0001 | IFACE-0021 | /component_specifications/0/interfaces/0/id |
| interface | IFACE-0002 | IFACE-0025 | /component_specifications/0/interfaces/1/id |


## Technology Stack

### Python (language)
**Version:** >=3.14

**Rationale:**
Minimum supported Python minor is 3.14 (`requires-python >=3.14`); currently qualified released minor line is 3.14; repository reference interpreter is currently 3.14.7; new GA Python minors require explicit qualification before support is advertised.

### Click (library)
**Version:** 8.x

**Rationale:**
CLI framework; consistent with STE ecosystem CLI patterns

### PyYAML (library)
**Version:** 6.x

**Rationale:**
ADR YAML parsing; schema validation

### pathlib (library)
**Version:** stdlib

**Rationale:**
Cross-platform path handling for scope resolution




## Architecture Impact

**Related ADRs:** [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)



---

*Generated from ADR-PC-0008 by ADR Architecture Kit (projection v3)*