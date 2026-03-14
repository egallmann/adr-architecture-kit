# Architecture Convergence Review

## Purpose

This document is the result of a convergence and hardening pass across all 12
plan documents in `/plan/`. It identifies inconsistencies, terminology drift,
contradictions, duplicated responsibilities, and boundary ambiguities. Each
finding includes a recommended amendment. The existing plan documents are
**not modified** — this review serves as the authoritative correction layer.

---

## 1. Structural Inconsistencies

### SI-1: Phase Numbering Divergence

**Documents:** `adr-kit-architecture-evolution.md`, `adr-kit-development-roadmap.md`, `adr-kit-compilation-pipeline.md`

| Document | Phase Scheme | Range |
|---|---|---|
| evolution | Phase 1–5 | Foundation → Kernel interface → Graph + analysis → Federation → Incremental |
| roadmap | Phase 0–7 | Golden files → Diagnostics → IR → Pass decomposition → Driver/CLI → Kernel contract → Graph → Incremental |
| pipeline | Phase 1–5 | Same as evolution (referenced, not independently defined) |

**Problem:** The evolution doc's 5 phases describe *what* changes architecturally.
The roadmap's 8 phases describe *how* to implement. These are orthogonal
dimensions (architectural intent vs implementation schedule) but share the word
"Phase", creating confusion about which phase scheme a reference targets.

**Amendment:** The roadmap phases are the **implementation phases** (IP-0 through
IP-7). The evolution phases are the **architecture phases** (AP-1 through AP-5).
All cross-document references must use the prefixed form. The canonical
implementation sequencing is defined in `implementation-sequencing.md`.

---

### SI-2: ArchModel Field Count Divergence

**Documents:** `adr-kit-compilation-pipeline.md` (§4), `architecture-compiler-internal-model.md` (§2)

| Document | ArchModel Fields |
|---|---|
| pipeline | 5: corpus, entities, relationships, diagnostics, metadata |
| internal-model | 6: corpus, entities (EntityGraph), relationships (RelGraph), unresolved (UnresolvedList), diagnostics (DiagnosticLog), metadata (CompilationMeta) |

**Problem:** The pipeline omits `unresolved` as a top-level ArchModel field.
In the pipeline's description, unresolved records are implied to live somewhere
but their container is not explicit.

**Amendment:** The internal-model document is **authoritative** for ArchModel
structure. The canonical fields are:

```
ArchModel:
    corpus: ParsedCorpus
    entities: EntityGraph
    relationships: RelGraph
    unresolved: UnresolvedList
    diagnostics: DiagnosticLog
    metadata: CompilationMeta
```

The pipeline's 5-field version is an earlier draft and should not be referenced.

---

### SI-3: CompilationResult Field Divergence

**Documents:** `adr-kit-architecture-evolution.md`, `adr-kit-development-roadmap.md`, `architecture-compiler-internal-model.md`

| Document | CompilationResult Fields |
|---|---|
| evolution | success, diagnostics, artifacts, ir |
| roadmap | success, artifacts, diagnostics, statistics, duration_ms |
| internal-model | success, artifacts, diagnostics, statistics, model (ArchModel), duration_ms |

**Problem:** Three different definitions of the same type.

**Amendment:** The internal-model document is **authoritative**. The canonical
`CompilationResult` is:

```python
@dataclass
class CompilationResult:
    success: bool
    artifacts: list[OutputArtifact]
    diagnostics: DiagnosticLog
    statistics: CompilationStatistics
    model: ArchModel
    duration_ms: int
```

Key resolution:
- `ir` (evolution) and `model` (internal-model) are the same thing. The canonical
  name is `model` (type: `ArchModel`).
- `statistics` is present in roadmap and internal-model but absent in evolution.
  It is **required** — the canonical model includes it.
- `duration_ms` is present in roadmap and internal-model. It is **required**.

---

### SI-4: Diagnostic Level Count

**Documents:** `adr-kit-compilation-pipeline.md`, `adr-kit-development-roadmap.md`, `architecture-compiler-internal-model.md`

| Document | Levels Defined |
|---|---|
| pipeline | 4: ERROR, WARNING, INFO, HINT |
| roadmap (Phase 1) | 2: ERROR, WARNING |
| internal-model | 3: ERROR, WARNING, INFO |

**Problem:** HINT appears in the pipeline but nowhere else. The roadmap's
Phase 1 deliberately starts with only 2 levels as a simplification.

**Amendment:** The canonical diagnostic levels are **3: ERROR, WARNING, INFO**.
HINT is deferred. The roadmap's Phase 1 is a valid implementation stepping
stone (start with 2, add INFO in Phase 2). The pipeline's HINT level is
aspirational and should not appear in initial implementation.

---

### SI-5: Pass Interface Divergence

**Documents:** `adr-kit-development-roadmap.md` (§Phase 3), `architecture-compiler-stages.md` (§Pass Architecture)

| Document | CompilationPass Protocol |
|---|---|
| roadmap | `name: str`, `depends_on: list[str]`, `run(model, config) -> None` |
| stages | `name: str`, `required: bool`, `depends_on: tuple[str, ...]`, `halts_on_error: bool`, `run(model, config) -> None` |

**Problem:** The stages document adds `required` and `halts_on_error` fields
not present in the roadmap. The roadmap uses `list[str]` for depends_on;
stages uses `tuple[str, ...]`.

**Amendment:** The stages document is **authoritative** for the pass protocol.
The canonical protocol is:

```python
class CompilationPass(Protocol):
    name: str
    required: bool
    depends_on: tuple[str, ...]
    halts_on_error: bool
    def run(self, model: ArchModel, config: CompilerConfig) -> None: ...
```

`required` and `halts_on_error` are necessary for the optional passes (M10: Lint,
M11: Graph Analysis). Using `tuple` over `list` for `depends_on` signals
immutability, which is correct for a protocol declaration.

---

### SI-6: Backend Emitter Count

**Documents:** `architecture-compiler-overview.md` (§4.1), `architecture-compiler-stages.md` (§B1–B7), `adr-kit-development-roadmap.md` (§Phase 4)

| Document | Emitters Listed |
|---|---|
| overview | 7: registries, manifest, legacy, index, markdown, graph, kernel bundle |
| stages | 7: B1 (registries), B2 (manifest), B3 (legacy), B4 (index), B5 (markdown), B6 (graph), B7 (kernel bundle) |
| roadmap Phase 4 | 3: registry_emitter, manifest_emitter, markdown_emitter |

**Problem:** The roadmap only introduces 3 emitters in Phase 4. The overview
and stages list 7 (including 2 future). The roadmap introduces graph and kernel
emitters in Phase 6 and Phase 5 respectively, but doesn't call them "backend
emitters" — creating an impression that Phase 4 is the complete backend.

**Amendment:** Phase 4 introduces the **backend framework** with 3 initial
emitters. Phases 5 and 6 add emitters to the existing framework:
- Phase 4: B1 (registries as single combined emitter for all 10 files), B2 (manifest), B5 (markdown). B3 (legacy) and B4 (index) are part of B1.
- Phase 5: B7 (kernel bundle)
- Phase 6: B6 (graph export)

Clarification: B1 (Registry Emission) produces 10 files including the
architecture index, subset registries, and legacy registry. B3 (legacy) and
B4 (index) from the stages document are sub-responsibilities of B1, not
independent emitters. The canonical emitter count is **5 independent emitters**:
registries (B1), manifest (B2), markdown (B5), kernel bundle (B7), graph (B6).

---

## 2. Terminology Drift

### TD-1: "Phase" / "Stage" / "Pass" Overloading

| Term | Used For | Documents |
|---|---|---|
| Phase | Implementation milestones | roadmap, evolution |
| Phase | Super Graph preparation steps | super-graph-preparation (S0–S3) |
| Stage | Compiler pipeline segments | compiler-overview, compiler-stages |
| Stage | Federation engine steps | registry-federation-model (F1–F8) |
| Pass | Middle-end compilation operations | compiler-stages (M1–M11), roadmap |

**Amendment:** Canonical terminology:
- **Implementation Phase (IP-N):** A milestone in the development roadmap
- **Architecture Phase (AP-N):** An evolutionary stage of the system's architecture
- **Super Graph Phase (SP-N):** A preparation step for federation support
- **Compiler Stage:** A named step in the compilation pipeline (F1–F4, M1–M11, B1–B7)
- **Federation Stage:** A named step in the federation engine (FF1–FF8)
- **Pass:** Synonym for middle-end compiler stage (M1–M11 only)

---

### TD-2: "Kernel Bundle" vs "Contract Registries"

**Documents:** `adr-kit-compilation-pipeline.md`, `adr-kit-development-roadmap.md`, `kernel-interface-contract.md`, `architecture-compiler-stages.md`

| Document | What the Kernel Consumes |
|---|---|
| pipeline | "kernel-bundle" — a single artifact emitted by KernelEmitter |
| roadmap Phase 5 | "kernel-bundle artifact" — format "single YAML file or structured directory" |
| kernel-interface-contract | 4 existing registry files directly (architecture-index.yaml + 3 registries) |
| compiler-stages B7 | "kernel bundle emission (future)" — format TBD |

**Problem:** The kernel contract document explicitly states the kernel loads
the **existing 4 registry files** — no separate bundle. But the pipeline,
roadmap, and compiler-stages all reference a separate "kernel bundle" emitter.
These are contradictory.

**Amendment:** The kernel-interface-contract is **authoritative**. The kernel
consumes the 4 existing contract files:
1. `architecture-index.yaml`
2. `entity-registry.yaml`
3. `relationship-registry.yaml`
4. `unresolved-registry.yaml`

There is **no separate kernel bundle**. The "KernelEmitter" (B7) in the compiler
stages should be reframed as:
- A **contract validation emitter** that verifies registry output conforms to
  the kernel contract schema.
- Optionally, a **contract packaging emitter** that creates a redistributable
  archive of the 4 contract files with a fingerprint manifest.

The kernel never loads a proprietary bundle format. It loads standard YAML
registries. B7's purpose is validation and packaging, not format transformation.

---

### TD-3: "NormalizedEntity" Entity Type Scope

| Context | Entity Types in Scope |
|---|---|
| `NormalizedEntity.entity_type` Literal (code) | 6: adr, system, component, decision, capability, invariant |
| `EntityType` enum (legacy v1.0 model) | 12 types |
| compiler-overview Entity ID Namespace | 18 ID patterns (14 entity types + ADR subtypes) |
| compiler-internal-model §11 | 6 core + 8 extended = 14 types |
| kernel-interface-contract §4.2 | 6 types (matches current Literal) |

**Problem:** The IR (internal-model) wants 14 entity types. The kernel contract
guarantees 6. The compiler-overview counts 18 ID patterns. These numbers refer
to different things but are conflated across documents.

**Amendment:** Three distinct entity type scopes:

1. **ID Patterns (18):** Regex patterns for entity ID validation. Includes ADR
   subtypes (ADR-L, ADR-V, ADR-P, ADR-PS, ADR-PC) counted separately.
2. **IR Entity Types (14):** Types tracked in the compiler's EntityGraph. Includes
   core 6 + extended 8 (constraint, boundary, nfr, contract, gap, interface,
   integration, impl_decision).
3. **Registry Entity Types (6):** Types emitted to registries and guaranteed by
   the kernel contract. The `entity_type` field in registry YAML is one of:
   adr, system, component, decision, capability, invariant.

The IR carries all 14 types. The backend registry emitter filters to 6 for
registry output. Extended types are available for analysis passes (lint, graph
analysis) but are not part of the kernel contract.

---

### TD-4: "Scope" vs "Namespace" vs "Repository"

| Term | Meaning in Code | Meaning in Super Graph |
|---|---|---|
| Scope | Project boundary within a workspace (INV-0019) | Compilation boundary |
| Namespace | `architecture_namespace` from PROJECT.yaml | Federation identity qualifier |
| Repository | Git repository | Unit of independent compilation |

**Problem:** In multi-scope workspaces, a single repository can contain multiple
scopes. Each scope compiles independently. But the Super Graph documents use
"namespace" and "repository" interchangeably, assuming one namespace per
repository. If a repository has multiple scopes, each scope needs its own
namespace.

**Amendment:** The correct hierarchy is:
```
Repository (git repo)
  └── Scope (PROJECT.yaml boundary)
        └── Namespace (architecture_namespace, globally unique)
```

A repository may contain multiple scopes. Each scope has its own namespace.
The federation manifest references **scopes** (by namespace), not repositories.
Documents that say "per-repository" should be read as "per-scope."

---

## 3. Contradictions

### C-1: Relationship Type "implements" Does Not Exist

**Documents:** `registry-federation-model.md` (§6.1 example, §6.4 table)

The federation model's cross-repo examples use `implements` as a relationship
type:

```yaml
relationship_id: implements:ste-kernel:COMP-GRAPH-ENGINE:adr-architecture-kit:CAP-0001
relationship_type: implements
```

The canonical 12 relationship types (defined in compiler-overview §4.2 and
compiler-internal-model §12) do **not** include `implements`. The correct
type is `implemented_by` with reversed direction:

```yaml
# Correct: capability → implemented_by → component
relationship_id: implemented_by:adr-architecture-kit:CAP-0001:ste-kernel:COMP-GRAPH-ENGINE
relationship_type: implemented_by
from_qualified_id: adr-architecture-kit:CAP-0001
to_qualified_id: ste-kernel:COMP-GRAPH-ENGINE
```

**Amendment:** Replace all occurrences of `relationship_type: implements` with
`relationship_type: implemented_by` and reverse the from/to direction. The 12
canonical relationship types are closed — no new types introduced by federation.

---

### C-2: Super Graph Diagram Uses Non-Existent Relationship Type "uses"

**Document:** `super-graph-preparation.md` (§1 diagram, line 44-45)

```
beta:COMP-X --uses--> alpha:CAP-0001
```

There is no `uses` relationship type. The correct relationship is
`implemented_by` (from capability to component) or `enables` (from decision
to capability).

**Amendment:** The diagram label should read:
```
alpha:CAP-0001 --implemented_by--> beta:COMP-X
```

---

### C-3: DiagnosticLog Sort Order Bug

**Document:** `architecture-compiler-internal-model.md` (§7)

```python
def all_sorted(self) -> list[Diagnostic]:
    return sorted(self._items, key=lambda d: (d.level.value, d.stage, d.source or "", d.code))
```

The `level.value` strings are `"error"`, `"warning"`, `"info"`. Alphabetically:
`error < info < warning`. This places INFO before WARNING, which is incorrect
for a severity-descending sort.

**Amendment:** Use an explicit severity ordering:

```python
_LEVEL_ORDER = {DiagnosticLevel.ERROR: 0, DiagnosticLevel.WARNING: 1, DiagnosticLevel.INFO: 2}

def all_sorted(self) -> list[Diagnostic]:
    return sorted(self._items, key=lambda d: (_LEVEL_ORDER[d.level], d.stage, d.source or "", d.code))
```

---

### C-4: Registry File Count in B1

**Document:** `architecture-compiler-stages.md` (§B1)

B1 says it produces "9 files" in its output table, but the table lists 9 rows.
The actual output is **10 files** (9 in `adrs/index/` + 1 legacy in
`adrs/entities/registry.yaml`). B3 (Legacy Registry Emission) is listed as a
separate backend stage for the 10th file.

**Amendment:** B1 produces **9 files** (all in `adrs/index/`). B3 produces
**1 file** (`adrs/entities/registry.yaml`). Total registry output: 10 files.
This is consistent. The confusion arises from B1's "9 files" wording — it is
correct as stated; the 10th file is B3's responsibility.

No change needed — this is consistent on close reading. Noted for clarity.

---

## 4. Duplicated Responsibilities

### DR-1: Entity Extraction: Single Pass vs Three Passes

**Documents:** `adr-kit-architecture-evolution.md`, `adr-kit-compilation-pipeline.md`, `architecture-compiler-stages.md`

| Document | Extraction Structure |
|---|---|
| evolution | Single "extract_entities" step |
| pipeline | Single "entity extraction" stage |
| stages | M3 (logical entities), M4 (physical entities), M5 (invariant canonical resolution) |

**Problem:** The early documents describe one extraction step. The stages
document decomposes it into three. Both are valid at their respective
abstraction levels, but intermediate documents should not reference "extract
entities" as a single pass.

**Amendment:** The canonical extraction is **three passes** (M3, M4, M5) as
defined in compiler-stages. References to a single "extract_entities" step
describe the same work at a higher abstraction level and should be understood
as encompassing M3+M4+M5.

---

### DR-2: Discovery Implementation Duplication

**Document:** `architecture-compiler-stages.md` (§F1)

The stages document notes: "ArchitectureIndexGenerator._discover_source_files()
and ADRValidator._discover_adr_files() are duplicated — the compiler should
have exactly one discovery implementation."

**Amendment:** This is already identified as a known issue. The compiler's F1
stage provides the single authoritative implementation. When F1 is implemented,
both existing discovery methods should delegate to it.

---

### DR-3: Bundle Validation: M9 vs _validate_bundle()

The existing `_validate_bundle()` method (lines 190-229 of the generator) and
the proposed M9 pass perform identical checks. M9 replaces `_validate_bundle()`
completely.

**Amendment:** When M9 is implemented, `_validate_bundle()` should be deleted.
M9 is the authoritative location for post-compilation consistency checks.

---

## 5. Boundary Ambiguities

### BA-1: WorkspaceModel vs SuperGraph

**Documents:** `architecture-compiler-internal-model.md` (§13), `super-graph-preparation.md`, `registry-federation-model.md`

The internal-model defines `WorkspaceModel` for multi-scope compilation within
a single repository. The Super Graph documents define federation across
repositories. Both involve merging entity graphs from multiple sources.

| Concept | Scope | Merge Strategy | When |
|---|---|---|---|
| WorkspaceModel | Intra-repo, multi-scope | Compiler merges at compile time | Phase 3 (pass decomposition) |
| SuperGraph | Cross-repo, multi-namespace | Federation engine merges post-compilation | Phase S3 (federation) |

**Problem:** The boundary between WorkspaceModel and SuperGraph is unclear.
Can a workspace contain scopes from different "namespaces"? If so, WorkspaceModel
is a special case of SuperGraph.

**Amendment:** WorkspaceModel is a **compile-time** concept: the compiler
operates on one scope at a time and emits per-scope registries. Multi-scope
workspaces compile each scope independently (current behavior, INV-0019).
WorkspaceModel is deferred (noted as "future extension" in internal-model §13).

SuperGraph is a **post-compilation** concept: the federation engine merges
independently compiled registries. It operates on serialized YAML, not IR.

The two concepts share no code and operate at different lifecycle stages.
WorkspaceModel should be deprioritized until the compiler is single-scope
complete.

---

### BA-2: Schema Authority — Who Owns the Registry Schema?

**Documents:** `kernel-interface-contract.md` (§4), `architecture-compiler-stages.md` (§B1), `adr-kit-development-roadmap.md` (§3.3)

The kernel contract defines the registry schema as a contract. The compiler
stages define the registry schema as a serialization spec. The roadmap
mentions schema evolution (v1.0, v1.1, v2.0) and independent kernel contract
versioning.

**Problem:** If the compiler changes a registry field, does it break the
kernel contract? Who decides what fields exist?

**Amendment:** The **compiler owns the registry schema**. The kernel contract
is a **subset** of the registry schema — it specifies which fields the kernel
may rely on. The compiler may add fields freely (minor version bump). Removing
or changing contracted field semantics requires a major version bump and kernel
coordination.

Schema authority chain:
```
Compiler registry schema (full) ⊇ Kernel contract schema (subset)
```

The compiler publishes the full schema. The kernel contract document specifies
which parts are guaranteed.

---

### BA-3: Compiler IR vs Registry Model

The compiler operates on `ArchModel` (mutable, in-memory, 14 entity types).
The registries contain `NormalizedEntity` (serialized, 6 entity types).
The kernel loads registries into `KernelArchitectureModel` (read-only, indexed,
6 entity types).

These are three distinct models:

| Model | Owner | Mutable | Entity Types | Lifecycle |
|---|---|---|---|---|
| ArchModel (IR) | Compiler | Yes | 14 | Compilation run |
| Registry (YAML) | Contract | N/A (files) | 6 | Persistent on disk |
| KernelArchitectureModel | Kernel | No | 6 | Loaded on demand |

**Amendment:** This three-model architecture is intentional and correct. The
IR is richer than the registry (captures intermediate analysis state). The
kernel model is an indexed view of the registry. No model should try to be
all three.

---

## 6. Missing Specifications

### MS-1: No Error Code Scheme

The pipeline document references diagnostic codes (E001, W002) but no document
defines the actual code scheme. What error code ranges map to which stages?

**Amendment needed:** Define error code ranges:
- E0xx: Frontend (parse, schema, scope)
- E1xx: Validation (business rules, cross-references)
- E2xx: Extraction (entity, relationship, invariant)
- E3xx: Resolution (unresolved, bundle consistency)
- E4xx: Backend (serialization, emission)
- W0xx–W4xx: Warning counterparts
- I0xx–I4xx: Info counterparts

This should be specified in `architecture-canonical-model.md`.

---

### MS-2: No Determinism Test Specification

Multiple documents reference deterministic output as a hard constraint but none
specifies what constitutes a determinism test.

**Amendment needed:** A determinism test:
1. Compiles the same source with pinned timestamp
2. Compares output byte-for-byte
3. Must pass across: same machine twice, different platforms (if CI is multi-OS)
4. Covers: entity ordering, relationship ordering, unresolved ordering,
   YAML serialization stability

---

### MS-3: CompilerConfig Mutual Exclusion

**Document:** `architecture-compiler-internal-model.md` (§9)

`CompilerConfig` has both `strict: bool` and `lenient: bool`. These are
mutually exclusive but nothing enforces that. Setting both `True` is undefined.

**Amendment:** Replace with a single mode field:

```python
class CompilationMode(Enum):
    NORMAL = "normal"
    STRICT = "strict"
    LENIENT = "lenient"

@dataclass
class CompilerConfig:
    mode: CompilationMode = CompilationMode.NORMAL
    # ...
```

---

## 7. Summary of Amendments

| ID | Category | Authoritative Source | Key Change |
|---|---|---|---|
| SI-1 | Phase numbering | implementation-sequencing.md (new) | Prefix: IP-N (implementation), AP-N (architecture), SP-N (super graph) |
| SI-2 | ArchModel fields | compiler-internal-model | 6 fields (includes `unresolved`) |
| SI-3 | CompilationResult | compiler-internal-model | 6 fields (includes `model` and `duration_ms`) |
| SI-4 | Diagnostic levels | compiler-internal-model | 3 levels: ERROR, WARNING, INFO |
| SI-5 | Pass interface | compiler-stages | 4 protocol fields including `required`, `halts_on_error` |
| SI-6 | Backend emitters | compiler-stages + roadmap | 5 independent emitters, phased introduction |
| TD-1 | Terminology | This document | Phase/Stage/Pass disambiguation |
| TD-2 | Kernel bundle | kernel-interface-contract | No separate bundle — kernel loads 4 existing files |
| TD-3 | Entity types | This document | 3 scopes: 18 ID patterns, 14 IR types, 6 registry types |
| TD-4 | Scope/namespace | This document | Repo → Scope → Namespace hierarchy |
| C-1 | `implements` type | compiler-internal-model §12 | Does not exist — use `implemented_by` with reversed direction |
| C-2 | `uses` in diagram | This document | Replace with `implemented_by` |
| C-3 | Sort order bug | This document | Use explicit severity ordinal |
| C-4 | Registry file count | compiler-stages | B1=9 files, B3=1 file, total=10 |
| DR-1 | Extraction passes | compiler-stages | 3 passes (M3, M4, M5), not 1 |
| BA-1 | Workspace vs SuperGraph | This document | Compile-time vs post-compilation; no shared code |
| BA-2 | Schema authority | kernel-interface-contract | Compiler owns schema ⊇ kernel contract |
| BA-3 | IR vs registry vs kernel | This document | 3 distinct models, intentionally different |
| MS-1 | Error codes | canonical-model (new) | Define E0xx–E4xx ranges |
| MS-2 | Determinism tests | canonical-model (new) | Byte-identical output spec |
| MS-3 | Config mutual exclusion | This document | Replace strict/lenient bools with enum |
