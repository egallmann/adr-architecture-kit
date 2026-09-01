<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 71fea80a3646739fd377052280568bbd73a9b17eed3a3042877e2c00f5c3592d
rendered_hash: 1ee486757b597caa5395787efabbe71abe82c163f5e33aae15c117f4b89ac497
-->

# ADR-PS-0001: ADR Architecture Kit Discovery and Indexing System

## Identity / Status

**Type:** physical-system  
**Status:** accepted  
**Alias:** ADR-PS-0001  
**System:** SYS-0001 — ADR Architecture Kit Discovery and Indexing System  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-13  
**Modified:** 2026-08-27  
**Authors:** adr-architecture-kit  
**Domains:** discovery, indexing, tooling  
**Implements Logical:** [ADR-L-0009](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md), [ADR-L-0012](../logical/ADR-L-0012-federation-authority-and-qualified-identity-model.md), [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)  

## Architecture at a Glance

| | |
| --- | --- |
| System | SYS-0001 — ADR Architecture Kit Discovery and Indexing System |
| Components | 1 |
| Boundaries | 1 |
| Internal relationships | 0 |
| External dependencies | 2 |
| Exposed surfaces | 7 |

**Logical authority**
- [ADR-L-0009](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0012](../logical/ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)


## Change Safety

**Logical contracts**
- [ADR-L-0009](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0012](../logical/ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)

**Constituent components**
- COMP-0010 — Entity Registry Generator and Query Surface

**External dependencies**
- Canonical ADR artifacts
- Standalone invariant artifacts

**Exposed interfaces**
- `adr compile`
- `adr generate-architecture-index`
- `adr generate-manifest`
- `adr generate-adr-projection`
- `adr generate-rendered-docs`
- `adr generate-entity-registry`
- `adr entities *`


## Context

The discovery and indexing subsystem provides the derived surfaces that agents
query instead of scanning raw ADR bodies by default. It now includes
normalized discovery bundle generation under `adrs/index/`, legacy
compatibility registry generation under `adrs/entities/registry.yaml`,
manifest generation, rendered ADR markdown generation, CLI query surfaces over
generated registry state, and the unified `adr compile` orchestration path
that emits these derived discovery artifacts together.


## Internal System Architecture

### System Components

| Component | Type | Role in this System | Authority |
| --- | --- | --- | --- |
| COMP-0010 — Entity Registry Generator and Query Surface | service | Compile, emit, and query derived discovery artifacts for architecture indexing. | [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md) |

*Topology handles are local authoring labels, not graph identities.*

Local topology handles:
- `TOPO-0001` → COMP-0010 — Entity Registry Generator and Query Surface


## System Boundaries

### SYSBOUND-0001 — Discovery and Indexing Boundary

Encapsulates generation and query of derived discovery artifacts without
changing canonical ADR authority.

**External Dependencies**
- Canonical ADR artifacts
- Standalone invariant artifacts

**Exposed Interfaces**
- `adr compile`
- `adr generate-architecture-index`
- `adr generate-manifest`
- `adr generate-adr-projection`
- `adr generate-rendered-docs`
- `adr generate-entity-registry`
- `adr entities *`



## Architecture Relationships

```mermaid
flowchart LR
  n_019fee89_e616_7c4e_953c_b7349412a784["ADR-L-0013<br/>Architecture Repository Boundary and Normalized Semantic Model"]
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712["CAP-0044<br/>Cross-Language Runtime Ingestion Contract"]
  n_019fee89_e617_7270_ab2f_58a756d2530e["ADR-PC-0001<br/>Entity Registry and Discovery Index"]
  n_019fee89_e617_76d8_a333_e21361cd6602["COMP-0010<br/>Entity Registry Generator and Query Surface"]
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e617_76d8_a333_e21361cd6602 -->|"declared_in"| n_019fee89_e617_7270_ab2f_58a756d2530e
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712 -->|"implemented_by"| n_019fee89_e617_76d8_a333_e21361cd6602
```

```mermaid
flowchart LR
  n_019fee89_e615_7f19_810b_c7b33a9d9e0d["ADR-L-0002<br/>Multi-Scope ADR Architecture for Sub-Module Development"]
  n_019fee89_e616_744f_b63e_5ecddf344faa["ADR-L-0012<br/>Federation Authority and Qualified Identity Model"]
  n_019fee89_e616_770c_a025_2c241a720730["ADR-L-0009<br/>Derived Architecture Discovery Surfaces"]
  n_019fee89_e618_7b3e_813b_a449881b6adb["ADR-PS-0001<br/>ADR Architecture Kit Discovery and Indexing System"]
  n_019fee89_e618_7b3e_813b_a449881b6adb -->|"implements_logical"| n_019fee89_e615_7f19_810b_c7b33a9d9e0d
  n_019fee89_e618_7b3e_813b_a449881b6adb -->|"implements_logical"| n_019fee89_e616_744f_b63e_5ecddf344faa
  n_019fee89_e618_7b3e_813b_a449881b6adb -->|"implements_logical"| n_019fee89_e616_770c_a025_2c241a720730
```

```mermaid
flowchart LR
  n_019fee89_e617_70e7_bb17_27b693ad01a8["IFACE-0011<br/>CLI"]
  n_019fee89_e617_7270_ab2f_58a756d2530e["ADR-PC-0001<br/>Entity Registry and Discovery Index"]
  n_019fee89_e617_76d8_a333_e21361cd6602["COMP-0010<br/>Entity Registry Generator and Query Surface"]
  n_019fee89_e617_70e7_bb17_27b693ad01a8 -->|"declared_in"| n_019fee89_e617_7270_ab2f_58a756d2530e
  n_019fee89_e617_76d8_a333_e21361cd6602 -->|"declared_in"| n_019fee89_e617_7270_ab2f_58a756d2530e
  n_019fee89_e617_76d8_a333_e21361cd6602 -->|"provides_interface"| n_019fee89_e617_70e7_bb17_27b693ad01a8
```


## Technology

### Python (language)
**Version:** >=3.14

**Rationale:**
Minimum supported Python minor is 3.14 (`requires-python >=3.14`); currently qualified released minor line is 3.14; repository reference interpreter is currently 3.14.7; new GA Python minors require explicit qualification before support is advertised.

### PyYAML (library)
**Version:** 6.x

**Rationale:**
Deterministic YAML parsing and rendering for derived artifacts.

### Click (tooling)
**Version:** 8.x

**Rationale:**
Existing CLI surface for agent and human invocation.




## Neighbor Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-L-0002 — Multi-Scope ADR Architecture for Sub-Module Development](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md) | ADR Architecture Kit Discovery and Indexing System (ADR-PS-0001) → Multi-Scope ADR Architecture for Sub-Module Development (ADR-L-0002) | `ADR-PS-0001 -[:implements_logical]-> ADR-L-0002` |
| [ADR-L-0009 — Derived Architecture Discovery Surfaces](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md) | ADR Architecture Kit Discovery and Indexing System (ADR-PS-0001) → Derived Architecture Discovery Surfaces (ADR-L-0009) | `ADR-PS-0001 -[:implements_logical]-> ADR-L-0009` |
| [ADR-L-0012 — Federation Authority and Qualified Identity Model](../logical/ADR-L-0012-federation-authority-and-qualified-identity-model.md) | ADR Architecture Kit Discovery and Indexing System (ADR-PS-0001) → Federation Authority and Qualified Identity Model (ADR-L-0012) | `ADR-PS-0001 -[:implements_logical]-> ADR-L-0012` |
| [ADR-L-0013 — Architecture Repository Boundary and Normalized Semantic Model](../logical/ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md) | Cross-Language Runtime Ingestion Contract (CAP-0044) → Entity Registry Generator and Query Surface (COMP-0010) | `CAP-0044 -[:implemented_by]-> COMP-0010` |
| [ADR-PC-0001 — Entity Registry and Discovery Index](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md) | Entity Registry Generator and Query Surface (COMP-0010) → CLI (IFACE-0011) | `COMP-0010 -[:provides_interface]-> IFACE-0011` |



---

*Generated from ADR-PS-0001 by ADR Architecture Kit (projection v3)*