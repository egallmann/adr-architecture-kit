<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 4ada5c4f365c526a638144ef9f9ecda73a0548f290e7bcb6209f688de7ccb478
rendered_hash: fcd5187090b5bd7ac9d6eab2c8b4eaa6c1f2bec2313cde03f9e09120c140276d
-->

# ADR-L-0007: Deterministic Documentation Projection

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0007  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-12  
**Authors:** adr-architecture-kit  
**Domains:** documentation, governance, determinism, projection  
**Tags:** generated-documentation, deterministic, ai-first, drift-prevention  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0007 |
| Status | accepted |
| Decisions | 12 |
| Capabilities | 1 |
| Invariants | 7 |
| Physical realizations | [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md), [ADR-PC-0005](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md), [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md) |


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
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0012 | Treat human-readable architecture documentation as deterministic derived state | Related INV-0037, INV-0038, INV-0039 |
| DEC-0019 | Prohibit manual edits to generated documentation | Related INV-0037, INV-0039 |
| DEC-0026 | Require generator, validator, test, and CI enforcement for documentation projection | Related INV-0038, INV-0039 |
| DEC-0108 | Emit ADR human projections under typed adr-projection paths with stable SDK artifact identity | Related INV-0037, INV-0038, INV-0039 |
| DEC-0109 | Human ADR projections render compiler-derived relationship semantics only | Related INV-0037, INV-0038 |
| DEC-0110 | Classify documentation-projection inputs as derived facts or authored orientation | Related INV-0099, INV-0100 |
| DEC-0111 | Allow a deterministic semantic intermediate model for documentation projection | Related INV-0038, INV-0101 |
| DEC-0112 | Require projection-source closure for generated documentation freshness | Related INV-0101, INV-0038 |
| DEC-0113 | Documentation projections reflect supported boundaries without redefining them | Related INV-0037, INV-0100 |
| DEC-0114 | Isolate repository-specific documentation-projection orientation by scope | Related INV-0102 |
| DEC-0115 | Preserve legacy generic SYSTEM-OVERVIEW generation as compatibility-only | Related INV-0102, INV-0100 |
| DEC-0176 | Encode projection v3 renderer contract for normalized v2.2 topology semantics | Related INV-0038, INV-0039 |

### DEC-0012 — Treat human-readable architecture documentation as deterministic derived state

**Rationale**

Structured architecture artifacts are the canonical source of truth in this
repository. Human-readable documentation is valuable for comprehension, but
it must be a deterministic rendering derived from those structured artifacts
rather than a parallel authority.

This preserves:
- doctrinal clarity about what is authoritative
- deterministic regeneration of documentation from source state
- drift prevention through validation and CI
- reliable AI target discovery, because generators remain the primary workflow

**Consequences**

Positive:
- Canonical architecture state remains explicit and machine-verifiable
- Rendered documentation can be regenerated consistently
- Documentation drift becomes detectable and enforceable
- AI contributors are directed toward generators rather than manual edits

Negative:
- Documentation changes may require generator or template updates instead of direct edits
- Small wording changes in rendered documentation now require structured source changes

**Traceability**
- Related invariants: INV-0037
- Related invariants: INV-0038
- Related invariants: INV-0039

### DEC-0019 — Prohibit manual edits to generated documentation

**Rationale**

Once an artifact is declared generated, manual edits create ambiguity over
whether the generated output or the source artifact should be trusted. That
ambiguity is architecturally unacceptable in a governance repository.

Manual edits are therefore prohibited for generated documentation. Changes
must be made by editing the structured source, generator, template, or
projection rules, followed by regeneration and validation.

**Consequences**

Positive:
- Rendered artifacts stay traceable to their generation pipeline
- Reviewers can reason about documentation changes from source changes
- CI can enforce freshness deterministically

Negative:
- Contributors must learn the generator path for documentation updates

**Traceability**
- Related invariants: INV-0037
- Related invariants: INV-0039

### DEC-0026 — Require generator, validator, test, and CI enforcement for documentation projection

**Rationale**

The rule is only durable if it is automated. Deterministic documentation
projection must therefore be enforced through:
- generators that produce rendered documentation
- validators that compare rendered output to generator output
- tests that prove deterministic generation
- CI checks that fail when rendered artifacts drift

This makes documentation projection a governed architectural pipeline rather
than a best-effort editorial process.

**Consequences**

Positive:
- Projection consistency becomes automatically enforceable
- Drift is surfaced immediately in development and CI
- Future AI-first artifacts can adopt the same pattern

Negative:
- Additional generator and validator maintenance is required as documentation artifacts expand

**Traceability**
- Related invariants: INV-0038
- Related invariants: INV-0039

### DEC-0108 — Emit ADR human projections under typed adr-projection paths with stable SDK artifact identity

**Rationale**

Human-facing ADR markdown must be navigable after UUID machine identity.
Projections live under adrs/adr-projection/{logical,physical,physical-system,physical-component}/
with filenames {alias_id}-{slug}.md. The SDK markdown group remains markdown;
artifact_kind remains rendered_adr_markdown; logical artifact_id is
rendered-adr:{adr.id} and must not become slug-dependent. relative_path values
migrate intentionally; generate-adr-projection is preferred with
generate-rendered-docs retained as a compatibility alias. Hard cutover replaces
adrs/rendered/ after the new tree validates. Projections remain disposable and
non-authoritative.

**Consequences**

Positive:
- Humans can locate and navigate ADR projections by alias and type
- SDK logical identity stays stable across title/slug changes
- Path migration is explicit and regenerable

Negative:
- Existing relative_path consumers must accept the adr-projection layout

**Traceability**
- Related invariants: INV-0037
- Related invariants: INV-0038
- Related invariants: INV-0039

### DEC-0109 — Human ADR projections render compiler-derived relationship semantics only

**Rationale**

The human projection must not invent a second relationship ontology.
Mermaid edges and peer-card relationship verbs come from shared compiler
derivation (RelGraph / RelationshipType). Required gap closes include ADR-level
supersedes/superseded_by and implements_logical as a first-class RelationshipType
(implementing ADR to logical ADR). HumanAdrProjectionContext may enrich with
prose and aliases but must not reinterpret source fields into alternate graph
meaning. Presentation-only nesting is limited to the subject ADR authored body.

**Consequences**

Positive:
- One relationship ontology for registries, graphs, and human projections
- Peer cards explain how ADRs relate using compiled verbs
- Integrity hashes cover the actual render dependency set

Negative:
- Derivation and relationship-type surfaces must stay aligned when fields change

**Traceability**
- Related invariants: INV-0037
- Related invariants: INV-0038

### DEC-0110 — Classify documentation-projection inputs as derived facts or authored orientation

**Rationale**

A generated documentation projection must not establish a second authored
copy of machine-verifiable facts when an owning structured or provider surface
already exists. Those facts must be obtained from their owning machine-readable
source.

Some orientation is inherently explanatory and cannot reasonably be mechanically
inferred. That authored orientation may be intentional projection input only when
it is explicit, governed as source state, non-authoritative, distinguishable from
derived facts, and unable to silently override canonical architecture.

Authored orientation must not become a hidden second authority layer.

**Consequences**

Positive:
- Overview and other projections stay aligned with owning provider/schema surfaces
- Explanatory guidance remains intentional without competing with canonical ADRs

Negative:
- Projection authors must classify each input as derived or authored

**Traceability**
- Related invariants: INV-0099
- Related invariants: INV-0100

### DEC-0111 — Allow a deterministic semantic intermediate model for documentation projection

**Rationale**

Projection generation may assemble governed inputs into an explicit deterministic
intermediate model that represents the complete semantic basis of the rendered
artifact. That model is derived projection state, not independent architecture
authority. It must be deterministic and must not carry environmental noise such
as timestamps or machine-specific absolute paths unless those are part of the
projection contract.

The intermediate model is the complete semantic basis of rendered content. It is
not necessarily the complete integrity or freshness basis, because governed
projection-rule inputs can also change the rendered artifact.

**Consequences**

Positive:
- Projection pipelines can separate semantic assembly from presentation
- Tests can assert semantic completeness without treating the model as authority

Negative:
- Implementers must keep semantic model and projection-rule inputs distinct

**Traceability**
- Related invariants: INV-0038
- Related invariants: INV-0101

### DEC-0112 — Require projection-source closure for generated documentation freshness

**Rationale**

Generated documentation freshness must close over all governed inputs capable
of changing the rendered artifact. That includes semantic inputs that determine
document meaning and projection-rule inputs that can change rendering from the
same semantic model (templates, generator or renderer rules, and profile
interpretation logic).

Changing a semantic or projection-rule input must invalidate the projection.
Unrelated repository changes must not. Whole-repository hashing is not required
or desirable. Aggregate sources such as a full manifest need not invalidate a
projection when an unrelated record changes if that record is not part of the
selected semantic input.

**Consequences**

Positive:
- Freshness tracks true render dependencies rather than coarse repository churn
- Template and projection-rule changes remain detectable as stale projections

Negative:
- Source-basis declarations must enumerate semantic and projection-rule inputs

**Traceability**
- Related invariants: INV-0101
- Related invariants: INV-0038

### DEC-0113 — Documentation projections reflect supported boundaries without redefining them

**Rationale**

A documentation projection may describe and route consumers to existing
supported interfaces, authority boundaries, and lifecycle surfaces. It must not
create, promote, or redefine those interfaces or authorities. Ownership remains
with the existing accepted authority for each surface.

**Consequences**

Positive:
- Orientation stays subordinate to provider, repository, and stewardship authority
- Overview content cannot silently invent public surfaces

Negative:
- Projection authors must cite existing authority rather than invent boundaries

**Traceability**
- Related invariants: INV-0037
- Related invariants: INV-0100

### DEC-0114 — Isolate repository-specific documentation-projection orientation by scope

**Rationale**

Repository-specific orientation semantics must not leak into an unrelated
repository scope. When ADR Kit generates SYSTEM-OVERVIEW for a consuming
repository, ADR Kit provider orientation must not be rendered into that consumer
merely because ADR Kit produced the file.

Explicit repository profiles may specialize orientation. Unsupported or
non-profiled scopes must follow the supported projection-scope rule rather than
silently inheriting another repository's provider identity.

**Consequences**

Positive:
- Consumer repositories are not mis-oriented as ADR Kit itself
- Profile and scope routing become architecturally mandatory

Negative:
- Generators must select profile or compatibility path by project identity

**Traceability**
- Related invariants: INV-0102

### DEC-0115 — Preserve legacy generic SYSTEM-OVERVIEW generation as compatibility-only

**Rationale**

Evidence on the active branch shows generate-system-overview currently succeeds
for non-kit, non-runtime project identities and is listed among generation
commands whose success/failure behavior is preserved. Fail-closed unsupported
routing would change that observable CLI behavior.

Therefore generic-project generation remains a compatibility obligation for this
refinement. The legacy generic path must preserve emission success without ADR
Kit provider framing, without becoming a third product-level generic consumer
overview design, and without new semantic inference beyond the minimum needed to
keep the existing contract. Richer corpus-driven generic assembly remains
deferred. Absence of SYSTEM-OVERVIEW remains valid; integrity validates the file
only when present.

**Consequences**

Positive:
- Existing CLI success behavior for generic scopes is preserved
- Provider isolation remains enforceable for non-kit scopes
- Future generic-consumer design stays explicitly deferred

Negative:
- A bounded legacy path must be maintained until replaced by later design

**Traceability**
- Related invariants: INV-0102
- Related invariants: INV-0100

### DEC-0176 — Encode projection v3 renderer contract for normalized v2.2 topology semantics

**Rationale**

Projection v3 renders deterministic human documentation from normalized v2.2 inputs using compiler-derived relationship semantics only. Topology inventory, compatibility rows, and peer-card verbs must follow ADR-L-0025 topology and contract succession authority without inventing pseudo-edges or ADR-level fake topology. Coverage registry posture and SYSTEM-OVERVIEW integration remain sequenced post-substrate; this decision governs authority only, not implementation modules or templates.

**Consequences**

Positive:
- v3 projection authority is durable and cross-references topology contract succession
- Renderer work can proceed against promoted schema and ADR authority

Negative:
- Production renderer implementation remains deferred to the implementation plan

**Traceability**
- Related invariants: INV-0038
- Related invariants: INV-0039


## Capabilities

### CAP-0014 — Deterministic Documentation Projection

The system can generate human-readable architecture documentation from
structured source artifacts and verify that rendered output remains in sync.




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0037 | INV-DOC-001: All human-readable architecture documentation must be generated from structured artifacts or explicit… | MUST / design | automated |
| INV-0038 | INV-DOC-002: Generated documentation must be deterministic given identical source artifacts and generator inputs. | MUST / test | automated |
| INV-0039 | INV-DOC-003: Rendered documentation must never be edited manually; changes must be made through generators,… | MUST / policy | automated |
| INV-0099 | INV-DOC-004: A documentation projection must obtain machine-verifiable facts from their owning structured or… | MUST / design | automated |
| INV-0100 | INV-DOC-005: Authored orientation used by a documentation projection must remain explicit, non-authoritative, and… | MUST / design | manual |
| INV-0101 | INV-DOC-006: Generated documentation freshness must close over all governed semantic inputs and projection-rule… | MUST / test | automated |
| INV-0102 | INV-DOC-007: Repository-specific documentation-projection orientation must not leak into an unrelated repository… | MUST / test | automated |

### INV-0037

**Statement**

INV-DOC-001: All human-readable architecture documentation must be generated
from structured artifacts or explicit projection code that is itself
governed as source state.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Documentation must remain a projection of canonical architecture state, not
a competing authority.

### INV-0038

**Statement**

INV-DOC-002: Generated documentation must be deterministic given identical
source artifacts and generator inputs.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Deterministic rendering is required for reliable drift detection, CI
enforcement, and reproducible AI orientation.

### INV-0039

**Statement**

INV-DOC-003: Rendered documentation must never be edited manually; changes
must be made through generators, templates, or structured source artifacts.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Manual edits to generated documentation destroy traceability and create
ambiguity over what is authoritative.

### INV-0099

**Statement**

INV-DOC-004: A documentation projection must obtain machine-verifiable
facts from their owning structured or provider surfaces and must not establish
an independent authored duplicate of those facts.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Derived facts already have an owning machine-readable source. Duplicating
them in projection configuration creates silent drift.

### INV-0100

**Statement**

INV-DOC-005: Authored orientation used by a documentation projection must
remain explicit, non-authoritative, and unable to override canonical architecture
authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Explanatory orientation is legitimate only when it cannot become a hidden
second authority layer.

### INV-0101

**Statement**

INV-DOC-006: Generated documentation freshness must close over all governed
semantic inputs and projection-rule inputs capable of changing the rendered
artifact, and must not require whole-repository hashing.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Freshness must track true render dependencies, including templates and
projection rules, without invalidating on unrelated repository churn.

### INV-0102

**Statement**

INV-DOC-007: Repository-specific documentation-projection orientation must
not leak into an unrelated repository scope, including ADR Kit provider
semantics rendered into an arbitrary consuming repository.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Scope isolation prevents consumer repositories from being mis-oriented as
the authoring provider.



## Decision / Intent Traceability

### Decision Traceability

```mermaid
flowchart LR
  %% Decision traceability
  n_019fee89_e615_758b_b03f_e4a3dc338589["Treat human-readable architecture documentation as deterministic derived state (DEC-0012)"]
  n_019fee89_e615_796c_ae1d_a27f1fff021b["Require generator, validator, test, and CI enforcement for documentation projection (DEC-0026)"]
  n_019fee89_e615_7e55_972f_14dd7da851c0["Prohibit manual edits to generated documentation (DEC-0019)"]
  n_019fee89_e616_77e0_992d_25764a1ed5a2["INV-0039"]
  n_019fee89_e616_7abd_ad17_f29edbd30959["INV-0038"]
  n_019fee89_e616_7bf6_a63f_2fdbec175790["INV-0037"]
  n_019ff142_dd48_72ff_9e3f_81ca4a779db7["Emit ADR human projections under typed adr-projection paths with stable SDK artifact identity (DEC-0108)"]
  n_019ff142_dd48_7ef8_8d3e_576f4bb02dc3["Human ADR projections render compiler-derived relationship semantics only (DEC-0109)"]
  n_019ff22a_bb5f_7214_8818_40820f8c553e["Allow a deterministic semantic intermediate model for documentation projection (DEC-0111)"]
  n_019ff22a_bb5f_76eb_8a31_546eeba55dcb["Documentation projections reflect supported boundaries without redefining them (DEC-0113)"]
  n_019ff22a_bb5f_7779_912f_040cdf1b54b8["INV-0100"]
  n_019ff22a_bb5f_77ed_a63f_98f0455fdd1e["Isolate repository-specific documentation-projection orientation by scope (DEC-0114)"]
  n_019ff22a_bb5f_7926_a33c_b66f72343219["Preserve legacy generic SYSTEM-OVERVIEW generation as compatibility-only (DEC-0115)"]
  n_019ff22a_bb5f_7b93_a600_f587022aeffd["INV-0101"]
  n_019ff22a_bb5f_7bfc_851d_938bffc81281["Classify documentation-projection inputs as derived facts or authored orientation (DEC-0110)"]
  n_019ff22a_bb5f_7c77_a223_1dab5e8c814d["INV-0099"]
  n_019ff22a_bb5f_7d9e_973f_b9008898a8c9["Require projection-source closure for generated documentation freshness (DEC-0112)"]
  n_019ff22a_bb5f_7fca_b021_b3cbc68ddde2["INV-0102"]
  n_01a048f5_b197_75ab_a812_6e3361333731["Encode projection v3 renderer contract for normalized v2.2 topology semantics (DEC-0176)"]
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
  n_019ff22a_bb5f_7214_8818_40820f8c553e -->|"enforces"| n_019fee89_e616_7abd_ad17_f29edbd30959
  n_019ff22a_bb5f_7214_8818_40820f8c553e -->|"enforces"| n_019ff22a_bb5f_7b93_a600_f587022aeffd
  n_019ff22a_bb5f_76eb_8a31_546eeba55dcb -->|"enforces"| n_019fee89_e616_7bf6_a63f_2fdbec175790
  n_019ff22a_bb5f_76eb_8a31_546eeba55dcb -->|"enforces"| n_019ff22a_bb5f_7779_912f_040cdf1b54b8
  n_019ff22a_bb5f_77ed_a63f_98f0455fdd1e -->|"enforces"| n_019ff22a_bb5f_7fca_b021_b3cbc68ddde2
  n_019ff22a_bb5f_7926_a33c_b66f72343219 -->|"enforces"| n_019ff22a_bb5f_7779_912f_040cdf1b54b8
  n_019ff22a_bb5f_7926_a33c_b66f72343219 -->|"enforces"| n_019ff22a_bb5f_7fca_b021_b3cbc68ddde2
  n_019ff22a_bb5f_7bfc_851d_938bffc81281 -->|"enforces"| n_019ff22a_bb5f_7779_912f_040cdf1b54b8
  n_019ff22a_bb5f_7bfc_851d_938bffc81281 -->|"enforces"| n_019ff22a_bb5f_7c77_a223_1dab5e8c814d
  n_019ff22a_bb5f_7d9e_973f_b9008898a8c9 -->|"enforces"| n_019fee89_e616_7abd_ad17_f29edbd30959
  n_019ff22a_bb5f_7d9e_973f_b9008898a8c9 -->|"enforces"| n_019ff22a_bb5f_7b93_a600_f587022aeffd
  n_01a048f5_b197_75ab_a812_6e3361333731 -->|"enforces"| n_019fee89_e616_77e0_992d_25764a1ed5a2
  n_01a048f5_b197_75ab_a812_6e3361333731 -->|"enforces"| n_019fee89_e616_7abd_ad17_f29edbd30959
```


## Physical Realization

**Systems**
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**Components**
- [ADR-PC-0005](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md)
- [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)


## Constraints

### CONST-0001 — technical

Human-readable architecture documentation must be produced from structured
artifacts or explicit projection code rather than maintained as an
independent source of truth.

**Rationale**

Independent manual documentation introduces drift risk and authority
ambiguity in an architecture governance repository.



## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-PC-0005](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)

**References**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0005](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0003 — Compiler Pipeline and Driver](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md) | implements this logical authority | `ADR-PC-0003 -[:implements_logical]-> ADR-L-0007` |
| [ADR-PC-0005 — Generated Artifact Integrity Validation](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md) | implements this logical authority | `ADR-PC-0005 -[:implements_logical]-> ADR-L-0007` |
| [ADR-PS-0002 — ADR Kit Authoring Compiler and Validation System](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md) | implements this logical authority | `ADR-PS-0002 -[:implements_logical]-> ADR-L-0007` |





---

*Generated from ADR-L-0007 by ADR Architecture Kit (projection v3)*