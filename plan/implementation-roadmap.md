# Implementation Roadmap

## Purpose

This roadmap reflects the **current implementation state** of
`adr-architecture-kit` and separates already-landed compiler work from the
remaining open slices. It replaces the earlier boundary-only roadmap with a
status-driven view that can be used directly for execution planning.

---

## 1. Completed Work

### C1. Compiler convergence and emission authority

Status: complete

Completed:
- compiler-owned manifest rendering
- compiler-owned rendered markdown rendering
- backend emitters routed through compiler renderers
- compatibility wrappers retained for `ManifestGenerator` and
  `MarkdownGenerator`
- integrity inspection converged on compiler-owned rendering

Outcome:
- compiler-owned rendering is now authoritative for emitted manifest and
  rendered markdown bytes
- legacy generator classes remain compatibility surfaces rather than owning
  emission logic

### C2. Explicit compiler pipeline

Status: complete

Completed:
- explicit pipeline abstraction added under `compiler/pipeline.py`
- `ArchitectureCompiler` and frontend build flow routed through the pipeline
- `ArchModelBuilder` reduced to a compatibility facade over pipeline-owned
  orchestration
- compiler guidance updated to reflect pipeline architecture

Outcome:
- ADR compilation now has an explicit deterministic pipeline shape without
  introducing a second competing IR

### C3. Additive architecture graph

Status: complete

Completed:
- compiler-owned `architecture-graph.yaml` artifact
- graph emission added to compiler/CLI surface
- integrity and inspection support added for graph artifacts

Outcome:
- the graph exists as an additive machine-navigation surface without replacing
  current registry authority

### C4. Intent attribution groundwork

Status: complete

Completed:
- `ADR-L-0004` strengthened as the authority for implementation intent
  attribution
- `INV-0006` added for required implementation attribution governance
- implementation attribution evidence schema/model/validation groundwork added
- repo-local legacy onboarding audit added

Outcome:
- ADR-Kit now owns the attribution rule and evidence contract, while extraction
  remains downstream

### C5. System overview rendering fix

Status: complete

Completed:
- hidden metadata comment rendering for `SYSTEM-OVERVIEW.md`
- validator and generator tests updated accordingly

Outcome:
- generated system overview renders correctly in GitHub without losing
  machine-readable metadata

### C6. Architecture Repository Boundary

Status: complete

Completed:
- `ADR-L-0013` and `INV-0007`
- hardened `ArchitectureRepository`
- added `NormalizedArchitectureModel`
- migrated CLI entity flows and `validate-contract` onto the repository boundary
- migrated semantic validators/helpers onto normalized semantic inputs

Outcome:
- in-process consumer semantics now have a stable boundary:
  `ArchitectureRepository` + `NormalizedArchitectureModel`

### C7. Consumer-side semantic convergence

Status: complete

Completed:
- migrated CLI entity flows and `validate-contract` onto the repository boundary
- migrated semantic validators onto normalized semantic inputs
- centralized semantic adaptation, provenance traversal, unresolved traversal,
  and ADR/status/domain lookup on the normalized boundary
- removed remaining normal consumer-side direct traversal of semantic fields in
  `EntityValidator`

Outcome:
- normal in-process semantic consumers now default to
  `ArchitectureRepository` + `NormalizedArchitectureModel` rather than
  reconstructing local semantics

### C8. Boundary resilience and compatibility coverage

Status: complete

Completed:
- strengthened repository load and fingerprint resilience coverage
- deepened legacy-to-normalized adaptation parity coverage
- added namespace / colon-bearing-ID landing seam protection
- verified current strict schema expectations without adding version-negotiation
  behavior

Outcome:
- the boundary is now hardened against the main near-term drift risks:
  legacy adaptation regression, semantically irrelevant ordering noise, and
  file-layout / namespace handling mistakes

---

## 2. Active Open Work

### O1. Decorate-forward and attribution operationalization

Status: open
Priority: high

Still needed:
- keep decorating all newly touched public implementation surfaces
- tighten new/changed-code expectations around `ADR-L-0004` / `INV-0006`
- perform targeted legacy decoration waves for high-value uncovered public
  surfaces in `src/adr_kit`

Exit criteria:
- touched public code consistently carries implementation intent attribution
- narrow retrofit waves reduce future bulk-churn without forcing a repo-wide
  annotation pass prematurely

### O2. Boundary compatibility and resilience

Status: open
Priority: high

Still needed:
- add a final small regression net if any new helper/report surfaces appear
- keep the boundary stable as new consumer/query/report code is added
- extend qualified-identity landing coverage only where a new boundary feature
  actually requires it

Exit criteria:
- new in-process consumer code does not bypass the semantic boundary
- future landing seams stay additive rather than forcing repository redesign

### O3. Provenance and embodiment join readiness

Status: open
Priority: medium

Still needed:
- expand model-level provenance expectations only where required for downstream
  RECON, implementation attribution, and future EDR joins
- keep provenance centralized in the semantic boundary rather than scattered
  across validators and inspectors

Exit criteria:
- semantic model preserves the provenance fields needed for near-term ADR-Kit
  and downstream RECON attribution joins

### O4. Intent-attribution downstream consumption

Status: open
Priority: medium

Still needed:
- consume ADR-Kit implementation attribution evidence through repository/model
  semantics where appropriate
- add ADR-Kit-side consumer/query/report surfaces only after downstream
  extraction is stable

Exit criteria:
- attribution evidence can be validated and joined against canonical ADR state
  without introducing a second semantic interpretation path

---

## Legacy Registry Note

`adrs/entities/registry.yaml` remains a **legacy compatibility projection**.
Its explicit empty lists are currently intentional.

Why those empty fields appear:
- the legacy registry model emits deterministic list-shaped fields even when no
  values exist
- many logical entities legitimately have no declared values for:
  `domains`, `related_adrs`, `realized_by`, or forward relationship lists
- those fields only populate when canonical artifacts actually declare the
  corresponding discovery or relationship data

Interpretation rule:
- use `adrs/index/*` and the repository boundary for richer semantic consumer
  behavior
- do not treat the legacy entity registry as the richest machine surface

---

## 3. Deferred Future Work

### D1. Federation and qualified identity

Status: deferred

Deferred items:
- federation loader
- cross-repo merge behavior
- qualified/global identity materialization
- multi-repo conflict handling

Reason:
- ADR-Kit should expose the landing zone for these features, not implement the
  federation engine itself

### D2. Kernel graph materialization

Status: deferred

Deferred items:
- graph-native query behavior
- kernel execution semantics
- supergraph runtime traversal APIs

Reason:
- these belong in downstream kernel work once the semantic boundary is stable

### D3. Rich embodiment / provenance joins

Status: deferred

Deferred items:
- full RECON merge semantics
- code/IaC embodiment graph materialization
- broader EDR-style evidence joining

Reason:
- ADR-Kit should preserve compatibility hooks now and avoid becoming a
  proto-kernel

---

## 4. Recommended Next Execution Order

1. Continue decorate-forward operationalization for new and newly touched code.
2. Add ADR-Kit-side attribution consumption only after downstream extraction is
   stable enough to join safely.
3. Tighten provenance expectations only where required for attribution joins.
4. Defer federation, kernel graph behavior, and richer embodiment merge logic
   to downstream repositories and later ADRs.

---

## 5. Current Definition of Done for the Boundary Phase

The current boundary phase is considered complete when all of the following are
true:

- compiler-owned emission is authoritative
- compiler pipeline is explicit and stable
- additive graph artifact exists
- repository boundary exists and is documented by ADR and invariant
- CLI and validator semantic consumers use the boundary
- raw compiled registries are not the preferred in-process semantic API

As of the current repo state, that definition is met in practice. The remaining
work is now about **attribution operationalization and future landing seams**,
not first introduction of the boundary.
