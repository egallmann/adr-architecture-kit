# Design Readiness Review

## Purpose

This document assesses whether the adr-architecture-kit architecture design is
ready for implementation. It evaluates the canonical model, convergence review,
and implementation sequencing against the actual codebase to identify
underspecified areas, implementation risks, required ADRs, and graph model
alignment gaps.

**Verdict: The design is implementation-ready for IP-0 through IP-3.
IP-4 onward has specific gaps that must be resolved before work begins.**

---

## 1. Architecture Completeness Assessment

### 1.1 What Is Fully Specified

| Area | Status | Evidence |
|---|---|---|
| ArchModel structure (6 fields) | Complete | Canonical model §5.1; all fields typed with clear roles |
| Pass protocol (4-field Protocol) | Complete | Canonical model §4.3; run() signature, depends_on, required, halts_on_error |
| Pass dependency chain (M1–M11) | Complete | Canonical model §4.2; strictly sequential, no ambiguity |
| Entity type system (3 scopes) | Complete | Canonical model §2.2; 18 ID patterns, 14 IR types, 6 registry types |
| Relationship type system (12 types) | Complete | Canonical model §3.1; closed set, direction and provenance defined |
| Kernel contract (4 files, 14 invariants) | Complete | Canonical model §8; contract files, invariants, versioning rules |
| Diagnostic model (3 levels, error code ranges) | Complete | Canonical model §6; code allocation E0xx–E4xx |
| CompilationResult (6 fields) | Complete | Canonical model §7.1 |
| CompilerConfig (mode enum) | Complete | Canonical model §7.2; CompilationMode replaces bool pair |
| Implementation sequencing (IP-0 through IP-9) | Complete | Sequencing doc; dependency graph, exit criteria per phase |
| Federation stages (FF-1 through FF-8) | Complete | Canonical model §10.4 |
| QualifiedEntityId design | Complete | Multi-repo-entity-identity.md; parse rules, separator analysis |

### 1.2 What Is Partially Specified

| Area | Gap | Severity |
|---|---|---|
| EntityGraph API | Method signatures listed but no error semantics for add() conflicts | Medium |
| RelGraph.add() | Returns Optional[RelationshipRecord] but rejection criteria underspecified | Medium |
| Backend emitter interface | No formal protocol — B1–B7 described narratively, not as a typed interface | Medium |
| PassManager | Dependency resolution algorithm described but cycle detection not specified | Low |
| Parse cache invalidation | Key is "path + mtime + size" but no eviction policy or max cache size | Low |
| Federation manifest discovery | Two options listed (well-known path, ste.config.json) but no priority order | Low |

### 1.3 What Is Unspecified

| Area | Gap | Severity | Blocks |
|---|---|---|---|
| Extended entity type integration in NormalizedEntity | How 8 extended types enter the IR when NormalizedEntity.entity_type is a 6-value Literal | **High** | IP-2 |
| Corpus immutability contract | Whether passes may modify ParsedCorpus or only read it | **High** | IP-3 |
| Entity relationship summary update contract | Whether RelGraph.add() or passes are responsible for maintaining EntityRelationshipSummary consistency | **High** | IP-3 |
| Backend emitter protocol | No typed interface for emitters — no shared contract for input/output | Medium | IP-4 |
| NORMAL mode error semantics | What happens when mode=NORMAL and an ERROR diagnostic is emitted (neither halt nor exclude) | Medium | IP-4 |
| Legacy registry deprecation timeline | entities/registry.yaml (v1.0) is produced but no plan for when to stop | Low | — |
| Federation manifest schema version constraints | What happens when repos have different schema versions (1.1 vs 1.2) at federation time | Low | IP-8 |

---

## 2. Underspecified Areas (Detailed)

### US-1: Extended Entity Types Cannot Enter NormalizedEntity

**Severity: High — Blocks IP-2**

The canonical model states the compiler IR stores 14 entity types (§2.2).
But `NormalizedEntity.entity_type` is defined as:

```python
entity_type: Literal["adr", "system", "component", "decision", "capability", "invariant"]
```

This is a Pydantic Literal — it will raise `ValidationError` if given
`"constraint"`, `"boundary"`, `"nfr"`, `"contract"`, `"gap"`, `"interface"`,
`"integration"`, or `"impl_decision"`.

The legacy `EntityType` enum in `entity_registry.py` has 12 types (including
boundary, contract, constraint, nfr, gap, interface, integration,
implementation_decision) but this enum is **not used by NormalizedEntity**. It
belongs to the v1.0 Entity model.

**Options:**
1. **Widen the Literal to 14 values.** Simple, but changes the Pydantic model
   used in registry serialization. Registry YAML would accept extended types,
   potentially confusing kernel consumers.
2. **Create a separate IR entity model.** IR uses `IREntity` with 14 types;
   backend emitter maps to `NormalizedEntity` with 6 types for output. Clean
   separation but introduces a second entity model.
3. **Use `NormalizedEntity` with 6 types; carry extended types in a parallel
   structure.** EntityGraph stores both `NormalizedEntity` (core 6) and a
   new `ExtendedEntity` (remaining 8) in separate indexes. Passes see both.

**Recommendation:** Option 2. The IR entity model is an internal type that
never appears in YAML output. It can carry all 14 types, full provenance, and
pass-specific metadata. The backend emitter performs the projection to
NormalizedEntity (6 types) for registry output. This preserves the existing
Pydantic model as the serialization contract and avoids widening the Literal.

**Required decision:** This must be resolved in an ADR before IP-2 begins.

---

### US-2: Corpus Immutability During Pass Execution

**Severity: High — Blocks IP-3**

The ArchModel contains `corpus: ParsedCorpus`. Passes operate on the ArchModel.
No document states whether passes may modify the corpus.

If M1 (Validate Business Rules) runs in lenient mode and excludes an invalid
ADR from the corpus, subsequent passes (M3, M4) will not see it. This is
correct behavior. But the mutation mechanism is unspecified:

- Does M1 remove entries from `corpus.logical_adrs`?
- Does M1 mark entries with a "skip" flag?
- Does M1 create a new filtered corpus?

The current code never modifies parsed ADRs after parsing. Validation runs
separately and does not feed back into the generator's ADR list.

**Recommendation:** ParsedCorpus should be **immutable after construction**.
Lenient-mode exclusion should work through a parallel structure — e.g., a
`model.excluded_sources: set[str]` containing ADR IDs that failed validation.
Extraction passes (M3, M4) check this set and skip excluded sources. This
avoids corpus mutation while supporting lenient mode.

**Required decision:** Specify in the ArchModel design before IP-3.

---

### US-3: EntityRelationshipSummary Maintenance Responsibility

**Severity: High — Blocks IP-3**

The current code maintains `EntityRelationshipSummary` inside `_add_relationship()`:

```python
summary = getattr(entities[from_id].relationships, relationship_type)
if to_id not in summary:
    summary.append(to_id)
    summary.sort()
```

The canonical model describes `RelGraph.add()` as:
> "Updates the entity's relationship summary automatically."

But passes also operate on `EntityGraph`. If M6 (Derive Relationships) calls
`RelGraph.add()` and it updates the entity's summary, then the summary is
tightly coupled to the relationship graph. This means:

1. RelGraph must hold a reference to EntityGraph (or vice versa).
2. Adding a relationship has side effects on a different data structure.
3. If a relationship is rejected (from_id not in entities), the summary is
   not updated — but who checks for consistency?

The current code handles this because `_add_relationship()` has access to both
dicts. In the decomposed design, RelGraph and EntityGraph are separate objects
on ArchModel, and the coupling must be explicit.

**Options:**
1. **RelGraph.add() takes EntityGraph as parameter** (as shown in
   compiler-internal-model.md) and mutates the entity summary. Coupling is
   explicit in the method signature.
2. **Summary is computed lazily from RelGraph.** Entity summaries are derived
   at serialization time by querying RelGraph. Eliminates mutation coupling
   but changes the current data flow.
3. **M9 (Validate Bundle) rebuilds summaries.** Passes add relationships
   to RelGraph only; M9 or the backend emitter builds summaries from RelGraph.

**Recommendation:** Option 1 (matches current behavior and the internal-model
doc). The coupling is already explicit in the RelGraph.add() signature. The
risk is manageable because M9 validates consistency.

**Required decision:** Confirm in implementation before IP-3.

---

### US-4: Backend Emitter Protocol

**Severity: Medium — Blocks IP-4**

The pass protocol is well-defined (`CompilationPass`). The backend emitter
protocol is not. There is no equivalent of:

```python
class BackendEmitter(Protocol):
    name: str
    def emit(self, model: ArchModel, config: CompilerConfig) -> list[OutputArtifact]: ...
```

Without this, each emitter is ad-hoc. The driver cannot generically iterate
over enabled emitters.

**Recommendation:** Define a `BackendEmitter` protocol before IP-4:

```python
class BackendEmitter(Protocol):
    name: str
    artifact_kind: str          # "registry", "manifest", "markdown", "graph"

    def emit(self, model: ArchModel, config: CompilerConfig) -> list[OutputArtifact]:
        """Produce output artifacts from the finalized model."""
        ...
```

The driver checks `config.emit` to select which emitters to run.

---

### US-5: NORMAL Mode Error Semantics

**Severity: Medium — Blocks IP-4**

`CompilationMode` has three values: NORMAL, STRICT, LENIENT.

- STRICT: halt on first ERROR.
- LENIENT: exclude invalid artifacts, continue.
- NORMAL: ?

The current code always continues after validation errors — generation proceeds
regardless. This is effectively LENIENT behavior.

What should NORMAL do when M1 emits an ERROR? If it doesn't halt and doesn't
exclude, then it includes invalid ADRs in the output. This is the current
behavior but it arguably violates the compiler's integrity guarantees.

**Recommendation:** NORMAL should **continue compilation but report errors**.
Invalid ADRs are included in the corpus (unlike LENIENT which excludes them).
The CompilationResult.success field is set to `false` if any ERRORs exist.
This matches the current behavior and preserves backward compatibility.

Document this explicitly in CompilationMode:
- STRICT: halt on ERROR, produce no output
- NORMAL: continue on ERROR, produce output, success=false
- LENIENT: exclude on ERROR, produce output from valid subset, success=true if no remaining errors

---

## 3. Graph Model Alignment Analysis

### 3.1 Three Graph Representations

| Model | Location | Entity Type | Relationship Storage | Mutability | Lifecycle |
|---|---|---|---|---|---|
| Compiler IR (`ArchModel`) | In-memory during compilation | 14 types (planned) | `RelGraph` (adjacency indexes) | Mutable | Compilation run |
| Kernel Runtime (`KernelArchitectureModel`) | In-memory in ste-kernel | 6 types | `RelIndex` (adjacency indexes) | Immutable | Loaded on demand |
| Super Graph (`SuperGraph`) | In-memory during federation | 6 types + qualified IDs | `GlobalRelIndex` | Immutable | Federation assembly |

### 3.2 Schema Alignment Assessment

**Current state: No shared schema definition exists between the three models.**

The three models are connected only through the serialized YAML registries:

```
Compiler IR ──[serialize]──> Registry YAML ──[deserialize]──> Kernel Model
                                  │
                                  └──[deserialize]──> Federation Engine ──> Super Graph
```

The registry YAML is the **integration contract**. It is defined by Pydantic
models in `models/architecture_discovery.py`:
- `NormalizedEntity` (6-type Literal)
- `RelationshipRecord` (12-type Literal)
- `UnresolvedRecord`

The kernel and federation engine both consume these same Pydantic models.
Schema alignment is enforced **by sharing the Pydantic model definitions**
at import time. If ste-kernel imports `NormalizedEntity` from `adr_kit.models`,
changes to the model break both producer and consumer simultaneously.

### 3.3 Drift Vectors

| Drift Vector | Likelihood | Impact | Current Mitigation |
|---|---|---|---|
| Compiler IR entity type expansion (6→14) | **Certain** (planned) | IR model diverges from registry model. If IR entity model is separate (US-1 Option 2), the mapping function becomes the alignment surface. | None — US-1 must be resolved first |
| Field additions to NormalizedEntity | Medium | Minor version bump. Kernel ignores unknown fields. | Schema versioning (1.1 → 1.2) |
| Kernel builds its own index types (EntityIndex, RelIndex) | **Certain** (planned) | Index structures are kernel-internal. No drift risk to the contract. | Contract specifies field semantics, not index structure |
| Federation adds qualified_id fields | **Certain** (planned, IP-7) | Additive fields. Old consumers unaffected. | Schema 1.2 minor bump |
| ste-kernel forks Pydantic models | Medium | Kernel has its own NormalizedEntity with different fields. Contract check fails silently. | No mitigation exists today |
| Relationship type set divergence | Low (closed set) | Federation uses a type not in the 12-type Literal. Currently prevented by Pydantic validation. | Literal constraint on RelationshipRecord |
| Metadata schema per entity_type | **Certain** | `metadata: Dict[str, Any]` is untyped. Kernel accesses fields defensively. Different entity types have different metadata keys. No schema enforces this. | None — metadata is a bag |

### 3.4 Compatibility Enforcement Mechanism Assessment

| Mechanism | Exists Today | Planned | Gap |
|---|---|---|---|
| Shared Pydantic models (import-time) | Yes — both compiler and repo use same models | Continues | Only works if kernel imports from adr_kit |
| JSON Schema for contract validation | No | IP-5 (B7 contract validator) | **Not yet built** |
| Contract invariant tests | No | IP-5 (contract tests in CI) | **Not yet built** |
| Schema version check at load | Partial — ArchitectureIndex has schema_version but no version gate | Planned (kernel version negotiation) | **No enforcement code** |
| Fingerprint validation | Yes — SHA-256 fingerprint exists | Continues | Works for staleness, not schema drift |

### 3.5 Recommended Alignment Mechanism

The design relies on three mechanisms for long-term compatibility:

**Mechanism 1: Shared type package (existing, sufficient for IP-0–IP-5)**

The Pydantic models in `adr_kit.models.architecture_discovery` are the single
source of truth for the registry schema. Both the compiler and the kernel (via
`ArchitectureRepository`) import these models. Changes propagate to all
consumers at package-update time.

**Risk:** If ste-kernel copies these models rather than importing them, drift
is immediate and silent.

**Mechanism 2: JSON Schema contract tests (planned, IP-5)**

B7 validates compiler output against JSON Schema. Mirror tests in ste-kernel
validate input against the same schema. Schema lives in `schema/kernel/` and
is the formal contract.

**Risk:** JSON Schema must be generated from or validated against the Pydantic
models. Manual maintenance of both creates drift.

**Mechanism 3: Schema version gate (planned, kernel-side)**

The kernel checks `schema_version` at load time and rejects incompatible
versions. This catches major-version drift.

**Risk:** Minor version drift (new fields) is silently accepted. If a new
field becomes load-bearing without a major bump, the kernel may malfunction.

**Recommended addition: Contract conformance test generator**

Add a single test that:
1. Loads the Pydantic models (source of truth)
2. Generates JSON Schema from them (`model.model_json_schema()`)
3. Compares against the committed JSON Schema in `schema/kernel/`
4. Fails if they diverge

This closes the loop: Pydantic models → JSON Schema → contract tests.
Any change to the models forces a schema update, which forces a contract
version decision.

This should be part of IP-5 deliverables.

---

### 3.6 Graph Model Alignment Gate

The architecture contains three distinct graph representations:

1. Compiler Intermediate Representation (ArchModel)
2. Registry Schema (entity-registry.yaml, relationship-registry.yaml)
3. Kernel Runtime Model (KernelArchitectureModel)

These models intentionally differ in capability and lifecycle:

| Model | Owner | Mutability | Entity Types |
|---|---|---|---|
| Compiler IR | adr-architecture-kit | Mutable | 14 types |
| Registry Schema | Contract surface | Serialized | 6 types |
| Kernel Model | ste-kernel | Immutable | 6 types |

The registry schema is the integration contract between the compiler
and the kernel.

However the compiler IR introduces additional entity types and internal
analysis metadata that do not appear in the registry schema. This creates
a structural projection step between the IR and the registry model.

If this projection is not explicitly defined, long-term schema drift
between the compiler, kernel, and federation layers becomes likely.

To prevent this drift, the following readiness gate is introduced.

#### Design Gate Requirement

Implementation may not proceed past **IP-2 (Intermediate Representation)**
until the IR → Registry projection is formally defined.

This decision must be captured in **ADR-REQUIRED-1 (IR Entity Model Design)**.

The ADR must define:

- The internal IR entity model used during compilation
- The projection rules mapping IR entities to registry entities
- The filtering rules for extended entity types
- The metadata fields preserved across the projection boundary
- The invariants guaranteeing registry compatibility

The registry schema remains the authoritative contract surface
between adr-architecture-kit and ste-kernel.

#### Verification Requirement

Once ADR-REQUIRED-1 is approved:

1. The compiler must implement a deterministic IR → Registry projection.
2. Registry output must validate against the kernel contract schema.
3. Contract conformance tests must ensure the projection remains stable.

Implementation phases depending on this decision:

- IP-2 — IR construction
- IP-3 — pass decomposition
- IP-4 — registry emitters
- IP-5 — kernel contract validation

These phases must not proceed until the IR projection model is finalized.

---

## 4. Implementation Risks

### IR-1: NormalizedEntity Literal Expansion (Critical)

**Risk:** The planned 14-type IR cannot use the existing `NormalizedEntity`
Pydantic model without widening the `entity_type` Literal. Widening the Literal
changes the serialization schema, breaking the contract guarantee that registries
contain only 6 types.

**Impact:** Blocks IP-2 if not resolved. If resolved incorrectly (widening the
Literal), registry consumers silently receive unknown entity types.

**Mitigation:** Resolve US-1 with an ADR before IP-2. Recommended: separate IR
entity model.

### IR-2: Mutable IR Cross-Reference Hazards (High)

**Risk:** RelGraph.add() mutates both the relationship collection and entity
summaries on EntityGraph. If a pass calls add() after M9 has validated, the
post-validation IR state may be inconsistent.

**Impact:** Subtle corruption. M10 and M11 (optional passes) run after M9.
If they add diagnostic-only data to the model, the validated state is still
correct. But if a future pass modifies relationships after M9, the bundle
invariants are violated.

**Mitigation:** Enforce an IR freeze after M9. Passes after M9 (M10, M11)
receive a read-only view or a separate diagnostic sink. The ArchModel could
expose a `freeze()` method that makes EntityGraph and RelGraph reject mutations.

### IR-3: Pass Extraction Ordering During IP-3 (High)

**Risk:** The generator's `generate_from_directory()` interleaves entity
extraction, relationship derivation, and unresolved detection in a single
method. The extraction order proposed in IP-3 (M9 first, then M8, then M3...)
extracts passes in a bottom-up order that may not match the data flow.

**Impact:** Intermediate states during IP-3 (when some passes are extracted
but others remain inline) must produce identical output. A pass extracted too
early may depend on inline code that hasn't been extracted yet.

**Mitigation:** The sequencing doc's extraction order is correct: extract M9
first (validation — can run on any well-formed model), then scoring (M8),
then extractions (M3/M4/M5), then relationship derivation (M6/M7). Each
extraction step must be followed by golden-file tests.

### IR-4: YAML Serialization Determinism (Medium)

**Risk:** The determinism guarantee requires bit-identical YAML output.
PyYAML's `safe_dump` behavior can vary across versions for edge cases:
multi-line strings, special characters, numeric formatting, None representation.

**Impact:** Golden-file tests fail across PyYAML versions. CI and dev machines
produce different output.

**Mitigation:** Pin PyYAML version in dependencies. Add a determinism test
(IP-0) that runs two compilations with pinned timestamp and asserts byte
identity. Run this test on all target platforms in CI.

### IR-5: Qualified ID Parsing Ambiguity (Medium)

**Risk:** The relationship ID format `{type}:{from}:{to}` uses colon as both
the segment separator and the namespace separator in qualified IDs. The parsing
heuristic (namespace=lowercase, bare_id=uppercase) works for standard IDs but
fails for:
- ADR-D (deprecated type — "D" is uppercase, but `adr-d` could be a namespace)
- Hypothetical entity IDs that start with lowercase
- Component IDs like `COMP-API-GATEWAY` where the ID contains hyphens (fine,
  but the parser must not split mid-ID)

**Impact:** Federation-time parsing errors. Wrong entity resolution.

**Mitigation:** The parsing heuristic is sound for the current ID format
because namespaces match `^[a-z]` and bare IDs match `^[A-Z]`. However, this
invariant is not enforced anywhere. Add a validation rule to the federation
engine (FF-1) that rejects namespaces starting with uppercase and bare IDs
starting with lowercase. Document this as a hard constraint.

### IR-6: Entity Metadata Schema Drift (Medium)

**Risk:** `NormalizedEntity.metadata` is `Dict[str, Any]`. Different entity
types have different metadata keys (e.g., capability has `implemented_by_components`,
decision has `enforces_invariants`). No schema validates per-type metadata.

**Impact:** The kernel accesses metadata defensively with `.get()`, but there
is no contract for which keys exist on which types. A refactor that renames a
metadata key silently breaks kernel queries.

**Mitigation:** Define typed metadata schemas per entity type as part of IP-5.
These don't need to be Pydantic models — JSON Schema fragments in the contract
schema suffice. The contract validator (B7) checks per-type metadata
conformance.

### IR-7: Federation Engine — Partial Load Failure (Low)

**Risk:** If one repository in the federation manifest fails to load (corrupt
registry, missing file), the federation engine halts entirely (FF-1 errors are
fatal). For large federations, a single repo's bad compile blocks all queries.

**Impact:** Fragile federation in production.

**Mitigation:** Add a `partial: bool` option to the federation engine. When
`partial=true`, failed repos are excluded with a WARNING and the Super Graph
is built from available repos. Cross-repo references to the failed repo remain
unresolved. This is a federation-time concern (IP-8) and not urgent.

---

## 5. Required ADRs

The following architectural decisions require formal ADRs per STE governance
(PRIME-1/PRIME-2) before implementation:

### ADR-REQUIRED-1: IR Entity Model Design

**Decision:** How extended entity types (14 vs 6) are represented in the
compiler IR.

**Options:** (a) Widen NormalizedEntity Literal, (b) Separate IR entity model,
(c) Parallel ExtendedEntity structure.

**Why ADR:** This decision affects the core data model, the backend emitter
contract, and the kernel contract boundary. It cannot be changed easily once
passes are built against the IR.

**Blocks:** IP-2

---

### ADR-REQUIRED-2: Kernel Interface Contract

**Decision:** Formal acceptance of the 4-file contract, contract invariants
(RI-1 through RI-7, DET-1 through DET-4, COMP-1 through COMP-3), and schema
versioning protocol.

**Why ADR:** This is the primary integration contract between adr-kit and
ste-kernel. It defines what the compiler guarantees and what the kernel may
depend on. Changes after kernel integration are expensive.

**Blocks:** IP-5

---

### ADR-REQUIRED-3: Compiler Architecture Decision

**Decision:** Adoption of the compilation pipeline model (frontend → IR →
passes → backend), the ArchModel as the intermediate representation, and
the pass protocol as the extension mechanism.

**Why ADR:** This is the foundational architectural change from toolkit to
compiler. It introduces new subsystems (`compiler/`), a new CLI command
(`adr compile`), and changes the internal data flow.

**Blocks:** IP-2 (could be written during IP-1)

---

### ADR-RECOMMENDED-4: Namespace and Qualified ID Scheme

**Decision:** Adoption of `{namespace}:{bare_id}` as the qualified entity ID
format, colon as separator, and the character class parsing heuristic.

**Why ADR:** This decision is permanent once cross-repo references exist.
Changing the separator or parsing rules after federation deployment would
require migrating all qualified IDs in all federated repos.

**Blocks:** IP-7

---

### ADR-RECOMMENDED-5: Entity Metadata Schema Contracts

**Decision:** Define per-entity-type metadata schemas and validation profiles
(`greenfield`, `brownfield`, `migration`) that specify which keys are
guaranteed, optional, deprecated, or temporarily tolerated during legacy import.
Reserved sentinel values (`__LEGACY_UNSPECIFIED__`, `__NOT_YET_MODELED__`,
`__MIGRATION_PLACEHOLDER__`) are valid only in `brownfield` and `migration`,
and produce a `sentinel_compliant` validation state rather than full
`compliant`.
Sentinel remediation is monotonic: once approved canonical content replaces a
sentinel, the field may not regress to a sentinel state under normal
validation.
Enforcement should use a separate canonical remediation ledger rather than
embedding approval workflow state into the ADR content itself.
Approval should be staged rather than immediate: replacement content first
enters `pending_approval`, then becomes `approved` only when linked to a
canonical `authority_ref`.
Sentinel usage should be narrow by policy: allowed only in narrative fields and
forbidden in identifiers, relationship structure, and governance fields.

**Why ADR:** `metadata: Dict[str, Any]` is the most fragile part of the
contract. Without per-type schemas, any metadata key rename silently breaks
kernel consumers. Without validation profiles, brownfield imports fail on
target-state quality requirements that were never satisfied by legacy data.
This ADR establishes the metadata, sentinel policy, monotonic remediation
rules, remediation ledger, and enforcement profiles as part of the contract.

Current 0.x schema baseline should align to the generator's observed metadata
surface for `adr`, `capability`, `decision`, `invariant`, `system`, and
`component` entities, rather than introducing speculative keys.
The contract conformance test generator should treat the Pydantic contract
models as the source of truth and the committed `schema/kernel/` files as
derived verification artifacts checked in CI.

**Blocks:** IP-5 (recommended, not strictly required)

---

## 6. Recommended Next Actions

### Before IP-0 (Immediate)

1. **Write ADR-REQUIRED-3** (Compiler Architecture Decision). This is
   foundational and its content is fully defined in the plan documents. It
   requires no further design work — only formal documentation.

2. **Write ADR-REQUIRED-1** (IR Entity Model Design). Resolve US-1 by
   choosing between the three options. Recommendation: Option 2 (separate IR
   entity model). This unblocks IP-2.

### During IP-0

3. **Implement golden-file test suite.** Capture all 10 registry files +
   manifest as golden snapshots. Include a determinism test (two compilations,
   byte-identical check).

4. **Add a YAML serialization stability test.** Run `yaml.safe_dump` on a
   representative payload and compare to a committed snapshot. This catches
   PyYAML version drift.

### During IP-1

5. **Specify corpus immutability** (US-2). Add to the ArchModel design:
   ParsedCorpus is immutable; lenient-mode exclusion uses an exclusion set.

6. **Confirm RelGraph.add() coupling** (US-3). Confirm Option 1 (RelGraph.add
   takes EntityGraph parameter) and document the coupling.

### Before IP-4

7. **Define BackendEmitter protocol** (US-4). Write the typed interface before
   extracting emitters.

8. **Document NORMAL mode semantics** (US-5). Add to CompilationMode
   documentation.

### Before IP-5

9. **Write ADR-REQUIRED-2** (Kernel Interface Contract). Formalize the 4-file
   contract, 0.x pre-stable versioning, and validator-vs-kernel load semantics.

10. **Implement contract conformance test generator** (§3.5). Ensure Pydantic
    models and JSON Schema stay aligned.

11. **Define per-entity-type metadata schemas and validation profiles** (IR-6).
    Write ADR-RECOMMENDED-5 or include the profiles and metadata schemas in the
    contract JSON Schema and validator config.

### Before IP-7

12. **Write ADR-RECOMMENDED-4** (Namespace and Qualified ID Scheme). Formalize
    the separator, parsing heuristic, and namespace format rules.

13. **Add namespace format validation** (IR-5). Enforce `^[a-z]` for namespaces
    and `^[A-Z]` for bare IDs in the parser.

---

## 7. Summary Verdict

| Phase | Readiness | Blockers |
|---|---|---|
| IP-0 (Golden Files) | **Ready** | None |
| IP-1 (Diagnostics + Cache) | **Ready** | None |
| IP-2 (IR) | **Blocked** | ADR-REQUIRED-1 (IR entity model), ADR-REQUIRED-3 (compiler architecture) |
| IP-3 (Pass Decomposition) | **Blocked** | US-2 (corpus immutability), US-3 (summary maintenance) |
| IP-4 (Driver + CLI) | **Needs work** | US-4 (emitter protocol), US-5 (NORMAL mode) |
| IP-5 (Kernel Contract) | **Needs work** | ADR-REQUIRED-2, metadata schemas, contract test generator |
| IP-6 (Graph + Analysis) | **Ready** (once IP-4 complete) | None beyond IP-4 prerequisites |
| IP-7 (Super Graph Prep) | **Needs work** | ADR-RECOMMENDED-4 (namespace scheme) |
| IP-8 (Federation) | **Needs work** | IR-5 (parsing validation), IR-7 (partial load) |
| IP-9 (Incremental) | **Not assessed** | Future scope |

**The design is architecturally sound.** The convergence pass resolved all
inter-document contradictions. The remaining gaps are specification-level
details that can be resolved through targeted ADRs and focused design
decisions — not architectural rework.

The critical path item is **ADR-REQUIRED-1** (IR entity model design).
Everything from IP-2 onward depends on this decision. Write it first.
