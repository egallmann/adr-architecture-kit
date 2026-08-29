<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 871a2e2162e25a38dbd6d8536779f2704ff67a71f523ed6e43200b526bbb272a
rendered_hash: 32b5b036a18783a71377dbbc74527c8573e37e858b25902a44df5340280fc3b1
-->

# ADR-PC-0003: Compiler Pipeline and Driver

## Identity / Status

**Type:** physical-component  
**Status:** accepted  
**Alias:** ADR-PC-0003  
**Alias name:** adr-pc-0003-compiler-pipeline-and-driver  
**Created:** 2026-03-15  
**Implements Logical:** [ADR-L-0007](../logical/ADR-L-0007-deterministic-documentation-projection.md), [ADR-L-0009](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md), [ADR-L-0013](../logical/ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md), [ADR-L-0002](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)  
**Implements System:** [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)  

## Architecture Position

Physical-component ADRs author component, interface, and implementation entities. Topology is not authored here; neighborhood uses compiled semantic architecture edges plus structural bridges.

## Architecture Neighborhood

```mermaid
flowchart LR
  n_019fee89_e617_7060_8f3f_4ecd46a719da["COMP-0011"]
  n_019fee89_e617_76ad_9336_b3615a6e4bde["COMP-0012"]
  n_019fee89_e617_7d2b_8325_cd85ff814477["ADR-PC-0002"]
  n_019fee89_e618_73ce_aa2d_101276d64e33["ADR-PC-0004"]
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37["ADR-PC-0005"]
  n_019fee89_e618_74d1_9a1f_37e2c2982a51["COMP-0013"]
  n_019fee89_e618_781c_831f_0d5fe24f7d85["COMP-0014"]
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6["ADR-PC-0003"]
  n_019fee89_e617_7060_8f3f_4ecd46a719da -->|"declared_in"| n_019fee89_e617_7d2b_8325_cd85ff814477
  n_019fee89_e617_76ad_9336_b3615a6e4bde -->|"declared_in"| n_019fee89_e618_7b76_843f_cfe21ceb2ea6
  n_019fee89_e618_74d1_9a1f_37e2c2982a51 -->|"declared_in"| n_019fee89_e618_73ce_aa2d_101276d64e33
  n_019fee89_e618_781c_831f_0d5fe24f7d85 -->|"declared_in"| n_019fee89_e618_74b2_a83e_e41c7d8c9f37
  n_019fee89_e617_76ad_9336_b3615a6e4bde -->|"depends_on"| n_019fee89_e617_7060_8f3f_4ecd46a719da
  n_019fee89_e618_74d1_9a1f_37e2c2982a51 -->|"depends_on"| n_019fee89_e617_76ad_9336_b3615a6e4bde
  n_019fee89_e618_781c_831f_0d5fe24f7d85 -->|"depends_on"| n_019fee89_e617_76ad_9336_b3615a6e4bde
```

```mermaid
flowchart LR
  n_019fee89_e615_7b9c_8e3f_32ceeda01491["ADR-L-0007"]
  n_019fee89_e615_7f19_810b_c7b33a9d9e0d["ADR-L-0002"]
  n_019fee89_e616_770c_a025_2c241a720730["ADR-L-0009"]
  n_019fee89_e616_7c4e_953c_b7349412a784["ADR-L-0013"]
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6["ADR-PC-0003"]
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6 -->|"implements_logical"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6 -->|"implements_logical"| n_019fee89_e615_7f19_810b_c7b33a9d9e0d
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6 -->|"implements_logical"| n_019fee89_e616_770c_a025_2c241a720730
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6 -->|"implements_logical"| n_019fee89_e616_7c4e_953c_b7349412a784
```


### Semantic architecture inventory

- `depends_on`: COMP-0012 → COMP-0011
- `depends_on`: COMP-0013 → COMP-0012
- `depends_on`: COMP-0014 → COMP-0012
- `implements_logical`: ADR-PC-0003 → ADR-L-0007
- `implements_logical`: ADR-PC-0003 → ADR-L-0002
- `implements_logical`: ADR-PC-0003 → ADR-L-0009
- `implements_logical`: ADR-PC-0003 → ADR-L-0013

## Neighbor Relationships

### ADR-L-0002 — Multi-Scope ADR Architecture for Sub-Module Development

- ADR-PC-0003 -[:implements_logical]-> ADR-L-0002 (peer ADR-L-0002)

**Context:** The adr-architecture-kit is being actively developed in a single workspace alongside
multiple sub-modules (ste-runtime, future services) that will eventually become
independent services. Each sub-module needs to leverage the ADR system for its own
architectural documentation while being developed in parallel within the monorepo.

[Open projection](../logical/ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
### ADR-L-0007 — Deterministic Documentation Projection

- ADR-PC-0003 -[:implements_logical]-> ADR-L-0007 (peer ADR-L-0007)

**Context:** The repository already treats several human-readable artifacts as derived state:
ADR human projections under adrs/adr-projection/, manifest summaries, and the AI-first SYSTEM-OVERVIEW
are generated from structured or code-defined sources. That behavior now needs
explicit architectural authority so future contributors do not reintroduce
manually maintained documentation that drifts from canonical artifacts.

[Open projection](../logical/ADR-L-0007-deterministic-documentation-projection.md)
### ADR-L-0009 — Derived Architecture Discovery Surfaces

- ADR-PC-0003 -[:implements_logical]-> ADR-L-0009 (peer ADR-L-0009)

**Context:** adr-architecture-kit is primarily machine-facing tooling used by agents to
reason over canonical architecture artifacts. Relying on agents to scan raw
ADR bodies for discovery is inconsistent with the toolkit's AI-first design
theory: discovery surfaces should be explicit, deterministic, cheap to query,
and derived from canonical authority.

[Open projection](../logical/ADR-L-0009-derived-architecture-discovery-surfaces.md)
### ADR-L-0013 — Architecture Repository Boundary and Normalized Semantic Model

- ADR-PC-0003 -[:implements_logical]-> ADR-L-0013 (peer ADR-L-0013)

**Context:** adr-architecture-kit now has an explicit compiler pipeline, a compiler IR
(`ArchModel`), compiled registry bundles, and an additive architecture graph.
Those pieces are sufficient to produce deterministic machine-facing artifacts,
and ArchitectureRepository already defines the semantic in-process boundary.
Phase 1 adds a narrow supported authoring facade that reuses that seam without
expanding the normalized model or exposing compiler internals.

[Open projection](../logical/ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
### ADR-PC-0002 — Schema and Contract Validation

- COMP-0012 -[:depends_on]-> COMP-0011 (peer ADR-PC-0002)

**Context:** Schema and contract validation is now a stable component boundary rather than
a generic legacy physical slice. It validates canonical ADR structure,
profile-specific contract requirements, project metadata, and implementation
attribution evidence. Validation of that evidence is structural for schema shape and architecture-aware when claims must resolve to canonical UUIDs and entity types. Legacy 1.0/1.2 evidence normalizes to the v1.5 claim shape only with repository or model 2.0 context.

[Open projection](ADR-PC-0002-schema-and-contract-validation.md)
### ADR-PC-0004 — Repository Boundary and Normalized Semantic Model

- COMP-0013 -[:depends_on]-> COMP-0012 (peer ADR-PC-0004)

**Context:** ArchitectureRepository and NormalizedArchitectureModel are the stable
in-process semantic boundary for consumers. Phase 1 adds a narrow supported
authoring facade that reuses those contracts without wrapping or changing the
normalized model and without making registry loaders or path helpers public.

[Open projection](ADR-PC-0004-repository-boundary-and-normalized-semantic-model.md)
### ADR-PC-0005 — Generated Artifact Integrity Validation

- COMP-0014 -[:depends_on]-> COMP-0012 (peer ADR-PC-0005)

**Context:** Generated artifact integrity validation verifies freshness, tamper status,
integrity headers, and scope-local generated outputs. It is a distinct public
subsystem used by validator and governance flows.

[Open projection](ADR-PC-0005-generated-artifact-integrity-validation.md)

## Context

The compiler driver and explicit pipeline now own deterministic architecture
compilation across parse, analysis, emission, and recursive scope
orchestration. The command-line behavior is compatibility-relevant, while the
Python compiler pipeline, passes, `ArchModel`, emitters, and result plumbing are
internal reference implementation and are not a supported SDK facade.


## Internal Structure

```mermaid
flowchart TB
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6["ADR-PC-0003"]
  subgraph sg_component["component"]
    n_019fee89_e617_76ad_9336_b3615a6e4bde["COMP-0012"]
  end
  subgraph sg_interface["interface"]
    n_019fee89_e617_779d_a12e_7713d58fbc21["IFACE-0013"]
    n_019fee89_e618_7e7b_813b_2a48de1d809a["IFACE-0018"]
  end
  subgraph sg_implementation_decision["implementation_decision"]
    n_019fee89_e618_7c0b_852f_c6d7f5b57322["IMPL-0013"]
    n_019fee89_e618_7113_9b36_4437b97cd744["IMPL-0019"]
  end
  n_019fee89_e617_76ad_9336_b3615a6e4bde -->|"declared_in"| n_019fee89_e618_7b76_843f_cfe21ceb2ea6
  n_019fee89_e617_779d_a12e_7713d58fbc21 -->|"declared_in"| n_019fee89_e618_7b76_843f_cfe21ceb2ea6
  n_019fee89_e618_7113_9b36_4437b97cd744 -->|"declared_in"| n_019fee89_e618_7b76_843f_cfe21ceb2ea6
  n_019fee89_e618_7c0b_852f_c6d7f5b57322 -->|"declared_in"| n_019fee89_e618_7b76_843f_cfe21ceb2ea6
  n_019fee89_e618_7e7b_813b_2a48de1d809a -->|"declared_in"| n_019fee89_e618_7b76_843f_cfe21ceb2ea6
  n_019fee89_e617_76ad_9336_b3615a6e4bde -->|"provides_interface"| n_019fee89_e617_779d_a12e_7713d58fbc21
  n_019fee89_e617_76ad_9336_b3615a6e4bde -->|"provides_interface"| n_019fee89_e618_7e7b_813b_2a48de1d809a
```

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
- adr generate-adr-projection - adr generate-rendered-docs

- **IFACE-0018** (library_api): A private compilation application service supports a restricted
`adr_kit.api.compile_architecture` adapter and a compatibility CLI adapter.
The public adapter accepts one explicit scope and only registries, manifest,
and markdown groups. The CLI adapter retains graph, recursive, check,
strict/lenient, contract-profile, output, diagnostic, and exit behavior.


**Implementation Identifiers:**
- Module Path: `src/adr_kit/compiler/driver.py`


- `component` COMP-0012 — Compiler Pipeline and Driver
- `implementation_decision` IMPL-0013 — Keep compiler orchestration as a dedicated component
- `implementation_decision` IMPL-0019 — Contain compiler internals behind public and CLI application-service adapters
- `interface` IFACE-0013 — 019fee89-e617-779d-a12e-7713d58fbc21
- `interface` IFACE-0018 — 019fee89-e618-7e7b-813b-2a48de1d809a

## Technology Stack

### Python (language)

**Version:** >=3.14

**Rationale:**
Minimum supported Python minor is 3.14 (`requires-python >=3.14`); currently qualified released minor line is 3.14; repository reference interpreter is currently 3.14.7; new GA Python minors require explicit qualification before support is advertised. 

### Click (tooling)

**Version:** 8.x

**Rationale:**
CLI orchestration for compile entrypoints.



---

*Generated from ADR-PC-0003 by ADR Architecture Kit (projection v3)*