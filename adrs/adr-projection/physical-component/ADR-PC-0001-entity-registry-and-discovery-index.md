<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 957de3faba17833dd9940e70f2822986df2cd677c4f1f3c522793ebe5b3ca4be
rendered_hash: 68e66219fd02389a0e53b0bfe35a4315b60f7070e2b9bc0dd3839b855f9413b1
-->

# ADR-PC-0001: Entity Registry and Discovery Index

## Identity / Status

**Type:** physical-component  
**Status:** accepted  
**Alias:** ADR-PC-0001  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-13  
**Modified:** 2026-08-27  
**Authors:** adr-architecture-kit  
**Domains:** discovery, indexing, tooling  
**Implements Logical:** [ADR-L-0009](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md), [ADR-L-0012](../logical/ADR-L-0012-federation-authority-and-qualified-identity-model.md), [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)  
**Implements System:** [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md)  

## Architecture at a Glance

| | |
| --- | --- |
| Component | COMP-0010 — Entity Registry Generator and Query Surface |
| Type | service |
| System | [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md) |
| Purpose | Generate and query the normalized entity registry for agent discovery. |
| Interfaces | IFACE-0011 — CLI |
| Primary implementation | `src/adr_kit/compiler/driver.py` |

**Logical authority**
- [ADR-L-0009](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0012](../logical/ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)


## Change Safety


**Must preserve**
- Discovery outputs are derived and non-authoritative
- Single-scope generation commands act as compatibility wrappers over `adr compile`
- CLI must read generated registry artifacts instead of rescanning ADRs
- Output must be deterministic when inputs are unchanged
- Cross-language consumers bootstrap from `architecture-index.yaml` and the required registry bundle
- `manifest.yaml` is a guaranteed discovery and freshness surface, not a semantic authority
- `adrs/entities/registry.yaml` must remain compatibility-only for new consumers

**Known architectural surface**
- Provided interfaces: IFACE-0011 — CLI

**Verification**
- Primary tests: `tests/test_compiler_driver.py`
- Unit coverage: >= 80%
- Success criteria: 4
- Integration checks: 2


## Context

The discovery/indexing component now centers on the unified compiler path. It
generates the normalized discovery bundle under `adrs/index/`, emits the
legacy compatibility registry at `adrs/entities/registry.yaml`, generates
manifest and rendered ADR markdown outputs through the same compiler-owned
path for single-scope use, and exposes exact-ID and filtered CLI query
operations over generated registry state.

It also serves as the file-format discovery surface for cross-language or
out-of-process consumers such as `ste-runtime`, which must bootstrap from the
indexed bundle rather than reparsing source ADRs.


## Architecture & Relationships

```mermaid
flowchart LR
  subgraph subject["Owned by this ADR"]
    n_019fee89_e617_76d8_a333_e21361cd6602["COMP-0010<br/>Entity Registry Generator and Query Surface"]
  end
  n_019fee89_e617_70e7_bb17_27b693ad01a8["IFACE-0011<br/>CLI"]
  n_019fee89_e617_76d8_a333_e21361cd6602 -->|"provides_interface"| n_019fee89_e617_70e7_bb17_27b693ad01a8
```

### Component Relationships

**Provides interface**
- CLI (IFACE-0011)

  `COMP-0010 -[:provides_interface]-> IFACE-0011`

**Implements logical authority**
- Multi-Scope ADR Architecture for Sub-Module Development (ADR-L-0002)

  `ADR-PC-0001 -[:implements_logical]-> ADR-L-0002`
- Derived Architecture Discovery Surfaces (ADR-L-0009)

  `ADR-PC-0001 -[:implements_logical]-> ADR-L-0009`
- Federation Authority and Qualified Identity Model (ADR-L-0012)

  `ADR-PC-0001 -[:implements_logical]-> ADR-L-0012`

**Implements**
- Normalized Entity Lookup Surface (CAP-0018)

  `CAP-0018 -[:implemented_by]-> COMP-0010`
- Cross-Language Runtime Ingestion Contract (CAP-0044)

  `CAP-0044 -[:implemented_by]-> COMP-0010`


## Component Contract

### COMP-0010: Entity Registry Generator and Query Surface

**Type:** service

**Purpose:**

Generate and query the normalized entity registry for agent discovery.

**Responsibilities:**

- Compile canonical ADR and invariant artifacts into a normalized discovery bundle
- Emit deterministic `adrs/index/*.yaml` registry artifacts
- Emit deterministic legacy compatibility registry output at `adrs/entities/registry.yaml`
- Support manifest and rendered markdown emission through the unified compile path
- Provide CLI query access over generated registry state
- Preserve an index-first discovery posture for cross-language consumers

**Key Responsibilities:**
- Generate deterministic discovery bundle records from canonical artifacts
- Emit the legacy compatibility registry from the normalized compiler output
- Delegate single-scope generation commands through the unified compiler driver
- Reject duplicate explicitly introduced entity IDs
- Support exact entity lookup and filtered list operations from CLI
- Keep the required discovery bundle and additive indexed artifacts distinct for downstream consumers

**Success Criteria:**
- Discovery bundle and legacy registry generation are deterministic
- ADR-L-0008 entities are present in generated discovery output
- CLI list/get/invariants/capabilities commands query the registry successfully
- Cross-language consumers can rely on the indexed bundle without needing raw ADR traversal

**Implements Capabilities:**
- Normalized Entity Lookup Surface (CAP-0018)
- Cross-Language Runtime Ingestion Contract (CAP-0044)


## Interfaces

### IFACE-0011 — CLI

**Type:** CLI

**Specification:**

Commands:
- adr compile
- adr generate-architecture-index
- adr generate-manifest
- adr generate-adr-projection
- adr generate-rendered-docs
- adr generate-entity-registry
- adr entities list
- adr entities get <id>
- adr entities invariants
- adr entities capabilities


## Implementation Decisions

### IMPL-0011 — Route single-scope discovery generation through the unified compiler driver

**Rationale:**

The unified compiler path keeps normalized registries, the legacy
compatibility registry, manifest generation, and rendered markdown emission
aligned while preserving the older single-scope commands as compatibility
wrappers. Registry backend emission remains compiler-owned rather than
isolated in the older standalone registry generator.


## Engineering Contract

### Failure Semantics

Fail closed on duplicate entity IDs, invalid compiled registry files, and missing generated discovery artifacts.

### Observability

**Logging:**
- Level: info
- Structured: false

**Metrics:**
- entity_registry_generations_total (counter)

### Verification

**Unit test coverage:** >= 80%

**Integration tests:**

- Discovery bundle and legacy registry generation from logical, physical, physical-system, physical-component, and invariant sources
- CLI query flows against generated registry artifacts


## Implementation Map

| Role | Location |
| --- | --- |
| Primary implementation | `src/adr_kit/compiler/driver.py` |
| Service | `adr-compiler` |
| Entry point | `src/adr_kit/cli/main.py` |
| Primary tests | `tests/test_compiler_driver.py` |



## Technology & Dependencies

### Python (language)
**Version:** >=3.14

**Rationale:**
Minimum supported Python minor is 3.14 (`requires-python >=3.14`); currently qualified released minor line is 3.14; repository reference interpreter is currently 3.14.7; new GA Python minors require explicit qualification before support is advertised.

### PyYAML (library)
**Version:** 6.x

**Rationale:**
Stable YAML parsing and rendering for registry artifacts.

### Click (tooling)
**Version:** 8.x

**Rationale:**
Existing CLI framework for scope-aware commands.





## Internal Structure

| Kind | Entity |
| --- | --- |
| Component | COMP-0010 — Entity Registry Generator and Query Surface |
| Implementation Decision | IMPL-0011 — Route single-scope discovery generation through the unified compiler driver |
| Interface | IFACE-0011 — CLI |


## Architecture Neighborhood

```mermaid
flowchart LR
  n_019fee89_e616_7121_a63e_0baad0a61fb3["CAP-0018<br/>Normalized Entity Lookup Surface"]
  n_019fee89_e616_770c_a025_2c241a720730["ADR-L-0009<br/>Derived Architecture Discovery Surfaces"]
  n_019fee89_e616_7c4e_953c_b7349412a784["ADR-L-0013<br/>Architecture Repository Boundary and Normalized Semantic Model"]
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712["CAP-0044<br/>Cross-Language Runtime Ingestion Contract"]
  n_019fee89_e617_7270_ab2f_58a756d2530e["ADR-PC-0001<br/>Entity Registry and Discovery Index"]
  n_019fee89_e617_76d8_a333_e21361cd6602["COMP-0010<br/>Entity Registry Generator and Query Surface"]
  n_019fee89_e616_7121_a63e_0baad0a61fb3 -->|"declared_in"| n_019fee89_e616_770c_a025_2c241a720730
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e617_76d8_a333_e21361cd6602 -->|"declared_in"| n_019fee89_e617_7270_ab2f_58a756d2530e
  n_019fee89_e616_7121_a63e_0baad0a61fb3 -->|"implemented_by"| n_019fee89_e617_76d8_a333_e21361cd6602
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712 -->|"implemented_by"| n_019fee89_e617_76d8_a333_e21361cd6602
```

```mermaid
flowchart LR
  n_019fee89_e615_7f19_810b_c7b33a9d9e0d["ADR-L-0002<br/>Multi-Scope ADR Architecture for Sub-Module Development"]
  n_019fee89_e616_744f_b63e_5ecddf344faa["ADR-L-0012<br/>Federation Authority and Qualified Identity Model"]
  n_019fee89_e617_7270_ab2f_58a756d2530e["ADR-PC-0001<br/>Entity Registry and Discovery Index"]
  n_019fee89_e617_7270_ab2f_58a756d2530e -->|"implements_logical"| n_019fee89_e615_7f19_810b_c7b33a9d9e0d
  n_019fee89_e617_7270_ab2f_58a756d2530e -->|"implements_logical"| n_019fee89_e616_744f_b63e_5ecddf344faa
```


## Neighbor Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-L-0002 — Multi-Scope ADR Architecture for Sub-Module Development](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md) | Entity Registry and Discovery Index (ADR-PC-0001) → Multi-Scope ADR Architecture for Sub-Module Development (ADR-L-0002) | `ADR-PC-0001 -[:implements_logical]-> ADR-L-0002` |
| [ADR-L-0009 — Derived Architecture Discovery Surfaces](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md) | Normalized Entity Lookup Surface (CAP-0018) → Entity Registry Generator and Query Surface (COMP-0010) | `CAP-0018 -[:implemented_by]-> COMP-0010` |
| [ADR-L-0012 — Federation Authority and Qualified Identity Model](../logical/ADR-L-0012-federation-authority-and-qualified-identity-model.md) | Entity Registry and Discovery Index (ADR-PC-0001) → Federation Authority and Qualified Identity Model (ADR-L-0012) | `ADR-PC-0001 -[:implements_logical]-> ADR-L-0012` |
| [ADR-L-0013 — Architecture Repository Boundary and Normalized Semantic Model](../logical/ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md) | Cross-Language Runtime Ingestion Contract (CAP-0044) → Entity Registry Generator and Query Surface (COMP-0010) | `CAP-0044 -[:implemented_by]-> COMP-0010` |



---

*Generated from ADR-PC-0001 by ADR Architecture Kit (projection v3)*