# ADR-Kit Compilation Pipeline

## Purpose

This document specifies the architecture compilation pipeline — the core mechanism by which
ADR source artifacts are transformed into normalized, kernel-consumable registries. It defines
each stage, its inputs and outputs, ordering constraints, and error semantics.

---

## 1. Current State Analysis

### Current Pipeline (Implicit)

Today the pipeline exists implicitly across independent generators invoked via separate CLI commands:

```
adr validate              →  ADRValidator        →  pass/fail + diagnostics
adr generate-manifest     →  ManifestGenerator   →  adrs/manifest.yaml
adr generate-architecture-index →  ArchitectureIndexGenerator  →  9 registry files
adr generate-rendered-docs      →  MarkdownGenerator           →  adrs/rendered/*.md
adr generate-system-overview    →  SystemOverviewGenerator     →  SYSTEM-OVERVIEW.md
```

**Key observations:**

1. **No shared parse cache** — each generator independently discovers and parses ADR files
2. **No dependency ordering** — generators can run in any order (or not at all)
3. **No pipeline-level error propagation** — a failing validator does not block generation
4. **No intermediate representation** — each generator builds its own internal model
5. **Manifest and architecture-index extract overlapping information** — both count ADRs,
   both track domains, both enumerate entities

### Current Data Flow

```
                    ┌─ ADRParser ─── ManifestGenerator ──→ manifest.yaml
                    │
ADR YAML files ─────┼─ ADRParser ─── ArchIndexGenerator ─→ 9 registry files
                    │
                    ├─ ADRParser ─── MarkdownGenerator ──→ rendered/*.md
                    │
                    └─ ADRParser ─── SystemOverview ─────→ SYSTEM-OVERVIEW.md
```

Each vertical branch is independent. The ADRParser is invoked 4 times over the same files.

---

## 2. Architectural Gaps

### 2.1 Redundant Source Parsing

The `ManifestGenerator`, `ArchitectureIndexGenerator`, `EntityRegistryGenerator`, and
`MarkdownGenerator` each call the parser independently. In the architecture-index generator
alone, file discovery + parsing happens in `_discover_adrs()` which walks `logical/`,
`physical/`, `physical-system/`, `physical-component/`, and `invariants/` directories.

**Cost:** 4x parse overhead. More critically, if parsing logic diverges between generators,
output registries become inconsistent.

### 2.2 No Validation Gate

Generation proceeds regardless of validation state. Running `adr generate-architecture-index`
on a repository with invalid ADRs produces registries containing entities derived from
malformed source — silently.

### 2.3 Monolithic Index Generation

`ArchitectureIndexGenerator._generate_discovery_artifacts()` is a ~500-line method that:
- Parses all ADR types
- Extracts entities (capabilities, decisions, invariants, components, systems, etc.)
- Builds relationships (12 types)
- Detects unresolved references
- Scores completeness
- Generates subset registries
- Writes 9 output files

This is the entire "middle" and "back" of the compiler in one method.

### 2.4 No Compilation Diagnostics Model

Errors are either:
- Exceptions (crash the generator)
- `ValidationResult` objects (from validators only)
- Print statements (informal warnings)

There is no unified diagnostic model that accumulates warnings, errors, and informational
messages across the full pipeline.

### 2.5 No Output Consistency Guarantee

Since generators run independently, there is no guarantee that `manifest.yaml` and
`architecture-index.yaml` reflect the same source state. A user could modify an ADR,
regenerate the manifest but not the index, and have divergent artifacts.

---

## 3. Proposed Compilation Pipeline

### 3.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Compilation Pipeline                              │
│                                                                          │
│  ┌──────────────┐                                                        │
│  │   FRONTEND    │                                                       │
│  │              │                                                        │
│  │  Discover    │──→ file_manifest: list[SourceFile]                     │
│  │  Parse       │──→ parsed_adrs: list[ADRModel]                        │
│  │  Schema Gate │──→ diagnostics (fail-fast on hard errors)              │
│  └──────┬───────┘                                                        │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────┐                                                        │
│  │   IR BUILD    │                                                       │
│  │              │                                                        │
│  │  ArchModel   │──→ Unified in-memory representation                   │
│  │  (entities,  │    containing all parsed data,                        │
│  │   relations, │    accumulated diagnostics,                           │
│  │   metadata)  │    and compilation state                              │
│  └──────┬───────┘                                                        │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────┐                                                        │
│  │   PASSES      │  (ordered, composable, testable)                     │
│  │              │                                                        │
│  │  1. validate          →  hard errors halt pipeline                   │
│  │  2. extract_entities  →  populate EntityGraph                        │
│  │  3. extract_relations →  populate RelGraph                           │
│  │  4. normalize         →  canonical IDs, dedup                        │
│  │  5. resolve_refs      →  cross-link, detect unresolved              │
│  │  6. score_complete    →  completeness metadata                      │
│  │  7. lint              →  soft warnings (optional)                    │
│  │  8. graph_analysis    →  cycles, orphans (optional)                 │
│  └──────┬───────┘                                                        │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────┐                                                        │
│  │   BACKEND     │  (parallel emission from shared IR)                  │
│  │              │                                                        │
│  │  RegistryEmitter   →  9 registry YAML files                         │
│  │  ManifestEmitter   →  manifest.yaml                                 │
│  │  MarkdownEmitter   →  rendered/*.md                                 │
│  │  GraphEmitter      →  DOT / JSON-LD (future)                        │
│  │  KernelEmitter     →  kernel contract bundle (future)               │
│  └──────┬───────┘                                                        │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────┐                                                        │
│  │   FINALIZE    │                                                       │
│  │              │                                                        │
│  │  Integrity   │──→ compute + write integrity headers                  │
│  │  Verify      │──→ round-trip hash check                              │
│  │  Report      │──→ CompilationResult summary                         │
│  └──────────────┘                                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Stage Specifications

#### Stage 1: Frontend — Discovery

**Responsibility:** Find all source artifacts within scope boundaries.

```
Input:  scope_root: Path, config: CompilerConfig
Output: SourceManifest
          .logical_adrs:    list[SourceFile]
          .physical_adrs:   list[SourceFile]
          .system_adrs:     list[SourceFile]
          .component_adrs:  list[SourceFile]
          .invariants:      list[SourceFile]
          .project_meta:    Optional[SourceFile]  (PROJECT.yaml)
```

**Behavior:**
- Walk directories per scope resolver rules (INV-0019)
- Classify files by directory and frontmatter `type` field
- Physical subtype classification by frontmatter, not directory (current behavior)
- Return deterministic ordering (sorted by path)

#### Stage 2: Frontend — Parse + Schema Gate

**Responsibility:** Parse all discovered files into typed Pydantic models. Reject
structurally invalid artifacts.

```
Input:  SourceManifest
Output: ParsedCorpus
          .adrs:        list[TypedADR]  (union of Logical|Physical|System|Component)
          .invariants:  list[StandaloneInvariant]
          .metadata:    Optional[ProjectMetadata]
          .diagnostics: list[Diagnostic]
```

**Error semantics:**
- Schema validation failure → `Diagnostic(level=ERROR)` → artifact excluded from corpus
- Parse warning (e.g., deprecated field) → `Diagnostic(level=WARNING)` → artifact included
- Pipeline continues with valid subset (configurable: `--strict` to fail on any error)

#### Stage 3: IR Construction

**Responsibility:** Build the unified `ArchModel` from the parsed corpus.

```python
@dataclass
class ArchModel:
    corpus: ParsedCorpus
    entities: EntityGraph       # mutable, populated by passes
    relationships: RelGraph     # mutable, populated by passes
    diagnostics: DiagnosticLog  # accumulated across all stages
    metadata: CompilationMeta   # timestamps, generator version, scope
```

This is a simple assembly step — no analysis. Passes operate on this model.

#### Stage 4: Passes

Each pass is a callable with signature:

```python
def pass_name(model: ArchModel, config: CompilerConfig) -> None:
    """Mutates model in place. Appends to model.diagnostics."""
```

**Pass ordering and dependencies:**

```
validate           (depends on: corpus)
  ↓
extract_entities   (depends on: validated corpus)
  ↓
extract_relations  (depends on: entities)
  ↓
normalize          (depends on: entities + relations)
  ↓
resolve_refs       (depends on: normalized entities + relations)
  ↓
score_completeness (depends on: resolved entities)
  ↓
lint               (depends on: all above — optional)
  ↓
graph_analysis     (depends on: all above — optional)
```

**Pass details:**

| Pass | What It Does | Current Code Location |
|------|-------------|----------------------|
| `validate` | Cross-reference validation, business rules, ID format checks | `validators/adr_validator.py`, `validators/entity_validator.py` |
| `extract_entities` | Walk each ADR's sections, create typed entity nodes (CAP, DEC, INV, COMP, SYS, BOUND, NFR, GAP) with provenance | `architecture_index_generator.py` lines that build `entities` list |
| `extract_relations` | Identify relationships from `related_adrs`, `realizes`, `implements`, `enforced_by`, cross-references | `architecture_index_generator.py` lines that build `relationships` list |
| `normalize` | Canonical ID assignment, collision detection, deduplication | `canonical_id_normalizer.py` |
| `resolve_refs` | For each entity reference, find target or mark unresolved. Build cross-reference links. | `architecture_index_generator.py` unresolved detection logic |
| `score_completeness` | Evaluate each entity's field coverage, assign complete/partial/reference_only | `architecture_index_generator.py` completeness logic |
| `lint` | Architecture quality warnings: orphan entities, missing descriptions, naming conventions | **New** |
| `graph_analysis` | Cycle detection in relationships, strongly-connected components, dead-end analysis | **New** |

#### Stage 5: Backend — Emission

Each emitter reads the finalized IR and produces output artifacts.

```
Input:  ArchModel (after all passes)
Output: list[OutputArtifact]
          .path: Path
          .content: bytes
          .kind: ArtifactKind
```

**Emitters:**

| Emitter | Output | Source of Truth |
|---------|--------|----------------|
| `RegistryEmitter` | architecture-index.yaml, entity-registry.yaml, relationship-registry.yaml, unresolved-registry.yaml, capability-registry.yaml, decision-registry.yaml, invariant-registry.yaml, component-registry.yaml, system-registry.yaml | `model.entities`, `model.relationships` |
| `ManifestEmitter` | manifest.yaml | `model.corpus` + `model.entities` (statistics) |
| `MarkdownEmitter` | adrs/rendered/*.md | `model.corpus` |
| `GraphEmitter` | architecture-graph.dot, architecture-graph.json | `model.entities`, `model.relationships` |
| `KernelEmitter` | kernel-bundle.yaml (or directory) | Full IR |

All emitters use the same `_yaml_support.py` deterministic serialization.

#### Stage 6: Finalize — Integrity + Reporting

**Responsibility:** Compute integrity headers, verify round-trip stability, produce
compilation summary.

```python
@dataclass
class CompilationResult:
    success: bool
    artifacts: list[OutputArtifact]
    diagnostics: DiagnosticLog
    statistics: CompilationStatistics
    integrity: dict[Path, IntegrityHeader]
    duration_ms: int
```

**Integrity protocol:**
1. Serialize artifact content
2. Compute SHA256 of serialized bytes (source hash from corpus, rendered hash from output)
3. Prepend integrity header
4. Write to disk
5. Re-read and verify hash matches (round-trip check)

---

## 4. Diagnostics Model

### Diagnostic Structure

```python
@dataclass
class Diagnostic:
    level: DiagnosticLevel  # ERROR, WARNING, INFO, HINT
    stage: str              # "frontend.parse", "pass.validate", "backend.registry"
    source: Optional[str]   # file path or entity ID
    message: str
    code: str               # machine-readable: "E001", "W042"
    suggestion: Optional[str]
```

### Error Codes (Initial Set)

| Code | Level | Stage | Meaning |
|------|-------|-------|---------|
| E001 | ERROR | frontend | YAML parse failure |
| E002 | ERROR | frontend | Schema validation failure |
| E003 | ERROR | validate | Invalid ADR ID format |
| E004 | ERROR | validate | Referenced ADR not found |
| E005 | ERROR | normalize | Entity ID collision |
| W001 | WARNING | extract | Entity missing description |
| W002 | WARNING | resolve | Unresolved entity reference |
| W003 | WARNING | score | Entity marked reference_only (no source definition) |
| W004 | WARNING | lint | Orphan entity (no relationships) |
| W005 | WARNING | graph | Cycle detected in relationship graph |

### Diagnostic Reporting

```
$ adr compile --scope .

Compiling architecture from 31 source artifacts...

  Frontend:    31 parsed, 0 errors
  Validate:    0 errors, 2 warnings
  Extract:     147 entities, 89 relationships
  Normalize:   0 collisions
  Resolve:     9 unresolved references
  Score:       128 complete, 14 partial, 5 reference_only

  Output:      12 artifacts written to adrs/index/

  W002: ADR-L-0015 references CAP-0099 which has no source definition
  W002: ADR-P-0003 references COMP-MESH-ROUTER which is not defined

Compilation succeeded with 2 warnings.
```

---

## 5. Schema Authority Boundaries

### Who Owns What

```
┌────────────────────────────┐
│  adr-architecture-kit      │
│  (this repository)         │
│                            │
│  OWNS:                     │
│  - ADR source schemas      │
│    (v1.0: adr-logical,     │
│     adr-physical, etc.)    │
│  - Discovery schemas       │
│    (v1.1: architecture-    │
│     index, registries)     │
│  - Invariant schema        │
│  - Manifest schema         │
│  - Compilation pipeline    │
│  - Registry generation     │
│                            │
│  DOES NOT OWN:             │
│  - Kernel consumption      │
│    schema (owned by        │
│    ste-kernel)             │
│  - Graph query language    │
│  - Runtime entity model    │
│    (owned by ste-runtime)  │
└──────────┬─────────────────┘
           │
           │  kernel contract
           │  (shared schema)
           │
┌──────────▼─────────────────┐
│  ste-kernel                 │
│                             │
│  OWNS:                      │
│  - Kernel input contract    │
│  - RECON consumption logic  │
│  - Runtime entity graph     │
│  - Query/reasoning over     │
│    architecture state       │
└─────────────────────────────┘
```

### Contract Boundary

The **kernel interface contract** is the handoff point. It should be:

1. **Co-owned** — schema defined collaboratively, versioned independently
2. **Tested from both sides** — adr-kit has contract-output tests, kernel has contract-input tests
3. **Versioned with semver** — breaking changes require major version bump
4. **Documented as an ADR** — the contract itself is an architecture decision

---

## 6. Phased Implementation Plan

### Phase 1: Diagnostics + Parse Cache

**Scope:** Introduce `DiagnosticLog` and shared parse cache without restructuring generators.

1. Define `Diagnostic` and `DiagnosticLog` classes
2. Refactor `ADRParser` to cache parsed results per scope
3. Have all generators use shared parser cache
4. Replace print-based warnings with `Diagnostic` emissions
5. Add `--diagnostics` flag to CLI commands

**Deliverables:** `compiler/diagnostics.py`, refactored parser with cache.

### Phase 2: IR + Pass Extraction

**Scope:** Introduce `ArchModel` and extract passes from `ArchitectureIndexGenerator`.

(See architecture-evolution.md Phase 1 + Phase 2 for details.)

### Phase 3: Unified Pipeline Driver

**Scope:** Single `adr compile` command with validation gate.

(See architecture-evolution.md Phase 3.)

### Phase 4: Backend Refactoring

**Scope:** Extract emitters from generators into backend subsystem.

1. `RegistryEmitter` — extracted from `ArchitectureIndexGenerator`
2. `ManifestEmitter` — extracted from `ManifestGenerator`
3. `MarkdownEmitter` — extracted from `MarkdownGenerator`
4. All emitters consume the same `ArchModel`

### Phase 5: Graph Export + Kernel Contract

**Scope:** New backend emitters for graph formats and kernel consumption.

(See architecture-evolution.md Phase 4 + Phase 5.)

---

## 7. Deterministic Artifact Generation

### Current Guarantees

- YAML output uses `_yaml_support.py` for stable key ordering
- Integrity headers encode SHA256 of source + rendered content
- Line endings normalized before hashing
- Generated timestamps use UTC ISO 8601

### Required Additional Guarantees

1. **Pass ordering determinism** — passes must execute in fixed order; no parallel passes
   that could introduce non-determinism
2. **Entity ordering** — entities in registries sorted by canonical ID
3. **Relationship ordering** — relationships sorted by `relationship_id`
4. **Diagnostic ordering** — diagnostics sorted by (stage, source, code)
5. **Floating-point avoidance** — confidence scores use string-encoded decimals in YAML
6. **Timestamp pinning** — `generated_at` either from wall clock (non-deterministic but
   useful) or pinnable via `--timestamp` flag for reproducible builds

### Reproducibility Test

```bash
# Two consecutive compilations with pinned timestamp must produce identical output
adr compile --timestamp 2026-01-01T00:00:00Z --output /tmp/run1
adr compile --timestamp 2026-01-01T00:00:00Z --output /tmp/run2
diff -r /tmp/run1 /tmp/run2  # must be empty
```

---

## 8. Risks and Constraints

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Refactoring `ArchitectureIndexGenerator` introduces output drift | Registries silently change, breaking downstream | Golden-file tests: snapshot current output, assert bit-identical after refactor |
| Pass ordering sensitivity (pass B depends on pass A's side effects) | Subtle bugs when passes reordered | Explicit dependency graph in PassManager; integration tests for full pipeline |
| Diagnostics model grows too complex | Over-engineering | Start with ERROR/WARNING only; add INFO/HINT later |
| Shared parse cache introduces stale-read bugs | Incorrect compilation from cached stale data | Cache keyed on (path, mtime, size); invalidate on any change |

### Constraints

1. **Backward compatibility** — existing CLI commands must continue to work during transition
2. **No new dependencies** — pipeline must use existing pydantic/pyyaml/jsonschema stack
3. **Determinism is non-negotiable** — integrity headers are load-bearing for STE trust model
4. **Multi-scope must work** — pipeline must handle recursive scope compilation
5. **Performance budget** — full compilation of 31 ADRs must complete in < 5 seconds
