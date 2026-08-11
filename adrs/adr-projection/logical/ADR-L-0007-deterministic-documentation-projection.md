<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 2
hash_algorithm: sha256
source_hash: 3aa4a8b22f34533b41868e5fdb4b271ad2f83afce3c364db5f47d5d0a6e9ea33
rendered_hash: a4be2052f280b465506b3a4fec242ba5aaf1b0c5ff66474b535152cb1994247e
-->

# ADR-L-0007: Deterministic Documentation Projection

**Status:** accepted  
**Created:** 2026-03-12  
**Authors:** adr-architecture-kit  
**Domains:** documentation, governance, determinism, projection  
**Tags:** generated-documentation, deterministic, ai-first, drift-prevention  
**Alias name:** adr-l-0007-deterministic-documentation-projection  

## Context

The repository already treats several human-readable artifacts as derived state:
ADR human projections under adrs/adr-projection/, manifest summaries, and the AI-first SYSTEM-OVERVIEW
are generated from structured or code-defined sources. That behavior now needs
explicit architectural authority so future contributors do not reintroduce
manually maintained documentation that drifts from canonical artifacts.

The canonical source of truth in this system is structured architecture state:
ADR YAML, invariant YAML, project metadata, schema definitions, and generator
source code where projection rules are intentionally encoded. Human-readable
documentation exists to improve orientation and inspection, but it is not the
authoritative state.

Manual maintenance of generated documentation creates several risks:
- drift between canonical artifacts and human-readable views
- ambiguity over whether readers should trust rendered output or source artifacts
- AI contributors missing generators and editing rendered outputs directly
- inconsistent updates across manifest summaries, indexes, and overview files

This rule applies to all human-readable architecture documentation projections,
including:
- ADR human projections (adrs/adr-projection/)
- SYSTEM-OVERVIEW
- manifest summaries
- architecture diagrams
- documentation indexes
- future documentation projections introduced later

The repository therefore needs an explicit logical rule: structured artifacts
are canonical, documentation renderings are derived, and projection consistency
must be enforced through generators, validators, tests, and CI.


## Relationship graph

```mermaid
flowchart LR
  n_019fee89_e615_70a5_861b_b2dde147e5af["ADR-L-0001"]
  n_019fee89_e615_7564_933f_0bb0cbbcf41b["CAP-0014"]
  n_019fee89_e615_758b_b03f_e4a3dc338589["DEC-0012"]
  n_019fee89_e615_77f6_9b1f_695732d25443["ADR-L-0003"]
  n_019fee89_e615_796c_ae1d_a27f1fff021b["DEC-0026"]
  n_019fee89_e615_7b9c_8e3f_32ceeda01491["ADR-L-0007"]
  n_019fee89_e615_7e55_972f_14dd7da851c0["DEC-0019"]
  n_019fee89_e616_744f_b63e_5ecddf344faa["ADR-L-0012"]
  n_019fee89_e616_77e0_992d_25764a1ed5a2["INV-0039"]
  n_019fee89_e616_7abd_ad17_f29edbd30959["INV-0038"]
  n_019fee89_e616_7bf6_a63f_2fdbec175790["INV-0037"]
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37["ADR-PC-0005"]
  n_019fee89_e618_79ed_9d2d_cc35c63bc99a["ADR-P-0001"]
  n_019fee89_e618_7a2f_aa3e_1f892cdf9410["ADR-P-0002"]
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6["ADR-PC-0003"]
  n_019fee89_e618_7d04_9337_4aa2d3258507["ADR-PS-0002"]
  n_019ff142_dd48_72ff_9e3f_81ca4a779db7["DEC-0108"]
  n_019ff142_dd48_7ef8_8d3e_576f4bb02dc3["DEC-0109"]
  n_019fee89_e615_7564_933f_0bb0cbbcf41b -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e615_758b_b03f_e4a3dc338589 -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e615_796c_ae1d_a27f1fff021b -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e615_7e55_972f_14dd7da851c0 -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e616_77e0_992d_25764a1ed5a2 -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e616_7abd_ad17_f29edbd30959 -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e616_7bf6_a63f_2fdbec175790 -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019ff142_dd48_72ff_9e3f_81ca4a779db7 -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019ff142_dd48_7ef8_8d3e_576f4bb02dc3 -->|"declared_in"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e615_758b_b03f_e4a3dc338589 -->|"enforces"| n_019fee89_e616_77e0_992d_25764a1ed5a2
  n_019fee89_e615_758b_b03f_e4a3dc338589 -->|"enforces"| n_019fee89_e616_7abd_ad17_f29edbd30959
  n_019fee89_e615_758b_b03f_e4a3dc338589 -->|"enforces"| n_019fee89_e616_7bf6_a63f_2fdbec175790
  n_019fee89_e615_796c_ae1d_a27f1fff021b -->|"enforces"| n_019fee89_e616_77e0_992d_25764a1ed5a2
  n_019fee89_e615_796c_ae1d_a27f1fff021b -->|"enforces"| n_019fee89_e616_7abd_ad17_f29edbd30959
  n_019fee89_e615_7e55_972f_14dd7da851c0 -->|"enforces"| n_019fee89_e616_77e0_992d_25764a1ed5a2
  n_019fee89_e615_7e55_972f_14dd7da851c0 -->|"enforces"| n_019fee89_e616_7bf6_a63f_2fdbec175790
  n_019ff142_dd48_72ff_9e3f_81ca4a779db7 -->|"enforces"| n_019fee89_e616_77e0_992d_25764a1ed5a2
  n_019ff142_dd48_72ff_9e3f_81ca4a779db7 -->|"enforces"| n_019fee89_e616_7abd_ad17_f29edbd30959
  n_019ff142_dd48_72ff_9e3f_81ca4a779db7 -->|"enforces"| n_019fee89_e616_7bf6_a63f_2fdbec175790
  n_019ff142_dd48_7ef8_8d3e_576f4bb02dc3 -->|"enforces"| n_019fee89_e616_7abd_ad17_f29edbd30959
  n_019ff142_dd48_7ef8_8d3e_576f4bb02dc3 -->|"enforces"| n_019fee89_e616_7bf6_a63f_2fdbec175790
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37 -->|"implements_logical"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6 -->|"implements_logical"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e618_7d04_9337_4aa2d3258507 -->|"implements_logical"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
  n_019fee89_e615_7b9c_8e3f_32ceeda01491 -->|"references"| n_019fee89_e615_70a5_861b_b2dde147e5af
  n_019fee89_e615_7b9c_8e3f_32ceeda01491 -->|"references"| n_019fee89_e615_77f6_9b1f_695732d25443
  n_019fee89_e615_7b9c_8e3f_32ceeda01491 -->|"references"| n_019fee89_e618_79ed_9d2d_cc35c63bc99a
  n_019fee89_e615_7b9c_8e3f_32ceeda01491 -->|"references"| n_019fee89_e618_7a2f_aa3e_1f892cdf9410
  n_019fee89_e616_744f_b63e_5ecddf344faa -->|"references"| n_019fee89_e615_7b9c_8e3f_32ceeda01491
```

## Related ADRs

### ADR-L-0001 — STE-Compliant Machine-Verifiable Architecture Decision Record System

**Relationships:**
- this ADR -[:references]-> 019fee89-e615-70a5-861b-b2dde147e5af

**Context:** # ADR Architecture Kit — STE Authoring Subsystem

[Open projection](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
### ADR-L-0003 — Quality Assurance and Testing Strategy

**Relationships:**
- this ADR -[:references]-> 019fee89-e615-77f6-9b1f-695732d25443

**Context:** The ADR Architecture Kit is a foundational tool for machine-verifiable architecture
documentation. As such, it must maintain high quality standards to ensure reliability,
correctness, and trust in the architectural governance it provides.

[Open projection](ADR-L-0003-quality-assurance-and-testing-strategy.md)
### ADR-L-0012 — Federation Authority and Qualified Identity Model

**Relationships:**
- 019fee89-e616-744f-b63e-5ecddf344faa -[:references]-> this ADR

**Context:** The compiler and recursive multi-scope model preserve repository-local
compilation boundaries, while STE federation spans independently compiled
repositories. Federation therefore requires global identity without weakening
provider authority or allowing the aggregation layer to rewrite canonical
repository state.

[Open projection](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
### ADR-P-0001 — Python Toolkit Implementation for ADR Kit

**Relationships:**
- this ADR -[:references]-> 019fee89-e618-79ed-9d2d-cc35c63bc99a

**Context:** This ADR specifies the implementation of ADR Kit using Python ecosystem and modern
Python tooling. The implementation must support schema validation, YAML parsing,
Pydantic models, and view generation.

[Open projection](../physical/ADR-P-0001-python-toolkit-implementation-for-adr-kit.md)
### ADR-P-0002 — JSON Schema Validation with YAML Document Format

**Relationships:**
- this ADR -[:references]-> 019fee89-e618-7a2f-aa3e-1f892cdf9410

**Context:** This ADR specifies the use of JSON Schema for validation with YAML as the document
format. This combination provides deterministic validation (JSON Schema) with
human-readable authoring (YAML with embedded markdown).

[Open projection](../physical/ADR-P-0002-json-schema-validation-with-yaml-document-format.md)
### ADR-PC-0003 — Compiler Pipeline and Driver

**Relationships:**
- 019fee89-e618-7b76-843f-cfe21ceb2ea6 -[:implements_logical]-> this ADR

**Context:** The compiler driver and explicit pipeline now own deterministic architecture
compilation across parse, analysis, emission, and recursive scope
orchestration. The command-line behavior is compatibility-relevant, while the
Python compiler pipeline, passes, `ArchModel`, emitters, and result plumbing are
internal reference implementation and are not a supported SDK facade.

[Open projection](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)
### ADR-PC-0005 — Generated Artifact Integrity Validation

**Relationships:**
- 019fee89-e618-74b2-a83e-e41c7d8c9f37 -[:implements_logical]-> this ADR

**Context:** Generated artifact integrity validation verifies freshness, tamper status,
integrity headers, and scope-local generated outputs. It is a distinct public
subsystem used by validator and governance flows.

[Open projection](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md)
### ADR-PS-0002 — ADR Kit Authoring Compiler and Validation System

**Relationships:**
- 019fee89-e618-7d04-9337-4aa2d3258507 -[:implements_logical]-> this ADR

**Context:** adr-architecture-kit operates as an authoring-time compiler and validation system rather
than a collection of unrelated generators. The implementation includes an
explicit compiler pipeline, contract validation, normalized repository/model
access, integrity verification, and CLI orchestration over those surfaces.

[Open projection](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

## Capabilities

### CAP-0014: Deterministic Documentation Projection

The system can generate human-readable architecture documentation from
structured source artifacts and verify that rendered output remains in sync.





## Constraints

### CONST-0001 (technical)

**Description:**
Human-readable architecture documentation must be produced from structured
artifacts or explicit projection code rather than maintained as an
independent source of truth.


**Rationale:**
Independent manual documentation introduces drift risk and authority
ambiguity in an architecture governance repository.



## Invariants

### INV-0037

**Statement:** INV-DOC-001: All human-readable architecture documentation must be generated
from structured artifacts or explicit projection code that is itself
governed as source state.
  
**Scope:** global  
**Enforcement:** must (design)  
**Verification:** automated

**Rationale:**
Documentation must remain a projection of canonical architecture state, not
a competing authority.




### INV-0038

**Statement:** INV-DOC-002: Generated documentation must be deterministic given identical
source artifacts and generator inputs.
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
Deterministic rendering is required for reliable drift detection, CI
enforcement, and reproducible AI orientation.




### INV-0039

**Statement:** INV-DOC-003: Rendered documentation must never be edited manually; changes
must be made through generators, templates, or structured source artifacts.
  
**Scope:** global  
**Enforcement:** must (policy)  
**Verification:** automated

**Rationale:**
Manual edits to generated documentation destroy traceability and create
ambiguity over what is authoritative.






## Decisions

### DEC-0012: Treat human-readable architecture documentation as deterministic derived state

**Rationale:**
Structured architecture artifacts are the canonical source of truth in this
repository. Human-readable documentation is valuable for comprehension, but
it must be a deterministic rendering derived from those structured artifacts
rather than a parallel authority.

This preserves:
- doctrinal clarity about what is authoritative
- deterministic regeneration of documentation from source state
- drift prevention through validation and CI
- reliable AI target discovery, because generators remain the primary workflow



**Consequences:**

**Positive:**
- Canonical architecture state remains explicit and machine-verifiable
- Rendered documentation can be regenerated consistently
- Documentation drift becomes detectable and enforceable
- AI contributors are directed toward generators rather than manual edits

**Negative:**
- Documentation changes may require generator or template updates instead of direct edits
- Small wording changes in rendered documentation now require structured source changes

**Related Invariants:** 019fee89-e616-7bf6-a63f-2fdbec175790, 019fee89-e616-7abd-ad17-f29edbd30959, 019fee89-e616-77e0-992d-25764a1ed5a2
### DEC-0019: Prohibit manual edits to generated documentation

**Rationale:**
Once an artifact is declared generated, manual edits create ambiguity over
whether the generated output or the source artifact should be trusted. That
ambiguity is architecturally unacceptable in a governance repository.

Manual edits are therefore prohibited for generated documentation. Changes
must be made by editing the structured source, generator, template, or
projection rules, followed by regeneration and validation.



**Consequences:**

**Positive:**
- Rendered artifacts stay traceable to their generation pipeline
- Reviewers can reason about documentation changes from source changes
- CI can enforce freshness deterministically

**Negative:**
- Contributors must learn the generator path for documentation updates

**Related Invariants:** 019fee89-e616-7bf6-a63f-2fdbec175790, 019fee89-e616-77e0-992d-25764a1ed5a2
### DEC-0026: Require generator, validator, test, and CI enforcement for documentation projection

**Rationale:**
The rule is only durable if it is automated. Deterministic documentation
projection must therefore be enforced through:
- generators that produce rendered documentation
- validators that compare rendered output to generator output
- tests that prove deterministic generation
- CI checks that fail when rendered artifacts drift

This makes documentation projection a governed architectural pipeline rather
than a best-effort editorial process.



**Consequences:**

**Positive:**
- Projection consistency becomes automatically enforceable
- Drift is surfaced immediately in development and CI
- Future AI-first artifacts can adopt the same pattern

**Negative:**
- Additional generator and validator maintenance is required as documentation artifacts expand

**Related Invariants:** 019fee89-e616-7abd-ad17-f29edbd30959, 019fee89-e616-77e0-992d-25764a1ed5a2
### DEC-0108: Emit ADR human projections under typed adr-projection paths with stable SDK artifact identity

**Rationale:**
Human-facing ADR markdown must be navigable after UUID machine identity.
Projections live under adrs/adr-projection/{logical,physical,physical-system,physical-component}/
with filenames {alias_id}-{slug}.md. The SDK markdown group remains markdown;
artifact_kind remains rendered_adr_markdown; logical artifact_id is
rendered-adr:{adr.id} and must not become slug-dependent. relative_path values
migrate intentionally; generate-adr-projection is preferred with
generate-rendered-docs retained as a compatibility alias. Hard cutover replaces
adrs/rendered/ after the new tree validates. Projections remain disposable and
non-authoritative.



**Consequences:**

**Positive:**
- Humans can locate and navigate ADR projections by alias and type
- SDK logical identity stays stable across title/slug changes
- Path migration is explicit and regenerable

**Negative:**
- Existing relative_path consumers must accept the adr-projection layout

**Related Invariants:** 019fee89-e616-7bf6-a63f-2fdbec175790, 019fee89-e616-7abd-ad17-f29edbd30959, 019fee89-e616-77e0-992d-25764a1ed5a2
### DEC-0109: Human ADR projections render compiler-derived relationship semantics only

**Rationale:**
The human projection must not invent a second relationship ontology.
Mermaid edges and peer-card relationship verbs come from shared compiler
derivation (RelGraph / RelationshipType). Required gap closes include ADR-level
supersedes/superseded_by and implements_logical as a first-class RelationshipType
(implementing ADR to logical ADR). HumanAdrProjectionContext may enrich with
prose and aliases but must not reinterpret source fields into alternate graph
meaning. Presentation-only nesting is limited to the subject ADR authored body.



**Consequences:**

**Positive:**
- One relationship ontology for registries, graphs, and human projections
- Peer cards explain how ADRs relate using compiled verbs
- Integrity hashes cover the actual render dependency set

**Negative:**
- Derivation and relationship-type surfaces must stay aligned when fields change

**Related Invariants:** 019fee89-e616-7bf6-a63f-2fdbec175790, 019fee89-e616-7abd-ad17-f29edbd30959


---

*Generated from ADR-L-0007 by ADR Architecture Kit*