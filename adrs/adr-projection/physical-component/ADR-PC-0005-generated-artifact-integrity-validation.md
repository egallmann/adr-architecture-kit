<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 54e20292b924708fbb956e747bd89e200df48b30c0591856afcec4ccf9188930
rendered_hash: 9a8eba1608b09a6c0694dcdd88592e1a1f38a697a308c3ce5f85978fe733e80a
-->

# ADR-PC-0005: Generated Artifact Integrity Validation

## Identity / Status

**Type:** physical-component  
**Status:** accepted  
**Alias:** ADR-PC-0005  
**Alias name:** adr-pc-0005-generated-artifact-integrity-validation  
**Created:** 2026-03-15  
**Implements Logical:** [ADR-L-0007](../logical/ADR-L-0007-deterministic-documentation-projection.md), [ADR-L-0013](../logical/ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)  
**Implements System:** [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)  

## Architecture Position

Physical-component ADRs author component, interface, and implementation entities. Topology is not authored here; neighborhood uses compiled semantic architecture edges plus structural bridges.

## Architecture Neighborhood

```mermaid
flowchart LR
  n_019fee89_e617_76ad_9336_b3615a6e4bde["COMP-0012"]
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37["ADR-PC-0005"]
  n_019fee89_e618_781c_831f_0d5fe24f7d85["COMP-0014"]
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6["ADR-PC-0003"]
  n_019fee89_e617_76ad_9336_b3615a6e4bde -->|"declared_in"| n_019fee89_e618_7b76_843f_cfe21ceb2ea6
  n_019fee89_e618_781c_831f_0d5fe24f7d85 -->|"declared_in"| n_019fee89_e618_74b2_a83e_e41c7d8c9f37
  n_019fee89_e618_781c_831f_0d5fe24f7d85 -->|"depends_on"| n_019fee89_e617_76ad_9336_b3615a6e4bde
```

```mermaid
flowchart LR
  n_019fee89_e615_7b9c_8e3f_32ceeda01491["ADR-L-0007"]
  n_019fee89_e616_7c4e_953c_b7349412a784["ADR-L-0013"]
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37["ADR-PC-0005"]
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37 -->|"implements_logical"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37 -->|"implements_logical"| n_019fee89_e616_7c4e_953c_b7349412a784
```


### Semantic architecture inventory

- `depends_on`: COMP-0014 → COMP-0012
- `implements_logical`: ADR-PC-0005 → ADR-L-0007
- `implements_logical`: ADR-PC-0005 → ADR-L-0013

## Neighbor Relationships

### ADR-L-0007 — Deterministic Documentation Projection

- ADR-PC-0005 -[:implements_logical]-> ADR-L-0007 (peer ADR-L-0007)

**Context:** The repository already treats several human-readable artifacts as derived state:
ADR human projections under adrs/adr-projection/, manifest summaries, and the AI-first SYSTEM-OVERVIEW
are generated from structured or code-defined sources. That behavior now needs
explicit architectural authority so future contributors do not reintroduce
manually maintained documentation that drifts from canonical artifacts.

[Open projection](../logical/ADR-L-0007-deterministic-documentation-projection.md)
### ADR-L-0013 — Architecture Repository Boundary and Normalized Semantic Model

- ADR-PC-0005 -[:implements_logical]-> ADR-L-0013 (peer ADR-L-0013)

**Context:** adr-architecture-kit now has an explicit compiler pipeline, a compiler IR
(`ArchModel`), compiled registry bundles, and an additive architecture graph.
Those pieces are sufficient to produce deterministic machine-facing artifacts,
and ArchitectureRepository already defines the semantic in-process boundary.
Phase 1 adds a narrow supported authoring facade that reuses that seam without
expanding the normalized model or exposing compiler internals.

[Open projection](../logical/ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
### ADR-PC-0003 — Compiler Pipeline and Driver

- COMP-0014 -[:depends_on]-> COMP-0012 (peer ADR-PC-0003)

**Context:** The compiler driver and explicit pipeline now own deterministic architecture
compilation across parse, analysis, emission, and recursive scope
orchestration. The command-line behavior is compatibility-relevant, while the
Python compiler pipeline, passes, `ArchModel`, emitters, and result plumbing are
internal reference implementation and are not a supported SDK facade.

[Open projection](ADR-PC-0003-compiler-pipeline-and-driver.md)

## Context

Generated artifact integrity validation verifies freshness, tamper status,
integrity headers, and scope-local generated outputs. It is a distinct public
subsystem used by validator and governance flows.


## Internal Structure

```mermaid
flowchart TB
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37["ADR-PC-0005"]
  subgraph sg_component["component"]
    n_019fee89_e618_781c_831f_0d5fe24f7d85["COMP-0014"]
  end
  subgraph sg_interface["interface"]
    n_019fee89_e618_783a_8511_196b6a627b3e["IFACE-0015"]
  end
  subgraph sg_implementation_decision["implementation_decision"]
    n_019fee89_e618_7d0d_ae2e_d65c2d83b72d["IMPL-0015"]
  end
  n_019fee89_e618_781c_831f_0d5fe24f7d85 -->|"declared_in"| n_019fee89_e618_74b2_a83e_e41c7d8c9f37
  n_019fee89_e618_783a_8511_196b6a627b3e -->|"declared_in"| n_019fee89_e618_74b2_a83e_e41c7d8c9f37
  n_019fee89_e618_7d0d_ae2e_d65c2d83b72d -->|"declared_in"| n_019fee89_e618_74b2_a83e_e41c7d8c9f37
  n_019fee89_e618_781c_831f_0d5fe24f7d85 -->|"provides_interface"| n_019fee89_e618_783a_8511_196b6a627b3e
```

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


**Implementation Identifiers:**
- Module Path: `src/adr_kit/integrity/validation.py`


- `component` COMP-0014 — Generated Artifact Integrity Validation
- `implementation_decision` IMPL-0015 — Separate artifact integrity validation from discovery/indexing authority
- `interface` IFACE-0015 — 019fee89-e618-783a-8511-196b6a627b3e

## Technology Stack

### Python (language)

**Version:** >=3.14

**Rationale:**
Minimum supported Python minor is 3.14 (`requires-python >=3.14`); currently qualified released minor line is 3.14; repository reference interpreter is currently 3.14.7; new GA Python minors require explicit qualification before support is advertised. 

### PyYAML (library)

**Version:** 6.x

**Rationale:**
Generated artifact inspection and parsing.



---

*Generated from ADR-PC-0005 by ADR Architecture Kit (projection v3)*