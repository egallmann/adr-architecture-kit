# ADR-Kit Development Roadmap

## Purpose

This document defines the multi-phase development roadmap for evolving adr-architecture-kit
from its current state into a stable architecture compiler for the STE ecosystem.
Each phase is scoped for independent delivery and backward compatibility.

---

## 1. Current State Summary

### Repository Vital Signs

| Metric | Value |
|--------|-------|
| Python package | `src/adr_kit/` — 52 source files |
| Schemas | 17 JSON Schema files (v1.0 + v1.1) |
| Models | 13 Pydantic model files |
| Generators | 10 generator files |
| Validators | 4 validator files + 3 integrity files |
| CLI commands | 16 commands across generate/validate/query groups |
| Tests | 20+ test files |
| Source ADRs | 31 artifacts (23 logical, 4 physical, 1 system, 1 component, 2 invariants) |
| Output registries | 9 YAML files in `adrs/index/` |
| Dependencies | pydantic, pyyaml, jsonschema, jinja2, click |

### Current Capabilities vs Compiler Target

| Compiler Stage | Current State | Gap |
|---|---|---|
| Source discovery | Present (per-generator) | Not shared; no caching |
| Parsing + schema gate | Present (`ADRParser`) | No fail-fast integration with generation |
| Entity extraction | Present (inline in `ArchitectureIndexGenerator`) | Not decomposed into testable pass |
| Relationship extraction | Present (inline) | Not decomposed |
| Normalization | Present (`canonical_id_normalizer.py`) | Not integrated into pipeline |
| Reference resolution | Present (inline) | Not decomposed |
| Completeness scoring | Present (inline) | Not decomposed |
| Registry emission | Present (inline) | Not separated from extraction logic |
| Manifest emission | Present (`ManifestGenerator`) | Independent; no shared IR |
| Markdown emission | Present (`MarkdownGenerator`) | Independent; no shared IR |
| Intermediate representation | **Missing** | Core gap |
| Unified pipeline driver | **Missing** | Core gap |
| Diagnostics model | **Missing** | Errors are exceptions or print statements |
| Graph export | **Missing** | Relationship data locked in YAML lists |
| Kernel interface contract | **Missing** | No formal handoff specification |
| Incremental compilation | **Missing** | Full reparse every run |
| Architecture linting | **Missing** | No quality analysis beyond validation |

---

## 2. Development Phases

### Phase 0: Stabilization + Test Hardening

**Timeline:** Immediate prerequisite
**Risk:** Low
**Breaking changes:** None

**Objective:** Establish a regression safety net before any refactoring begins.

#### Deliverables

1. **Golden-file test suite**
   - Snapshot all 9 current registry outputs + manifest as golden files
   - Test: regenerate and assert byte-identical output
   - These tests become the refactoring safety net for all subsequent phases

2. **Pipeline integration test**
   - Single test that runs: validate → generate-manifest → generate-architecture-index → generate-rendered-docs
   - Asserts: all outputs consistent, no errors, integrity headers valid
   - Simulates what `adr compile` will eventually do

3. **Test coverage baseline**
   - Measure current coverage
   - Identify untested paths in `ArchitectureIndexGenerator` (entity extraction, relationship building)
   - Add targeted unit tests for extraction logic

#### Exit Criteria
- Golden-file tests pass on current output
- Integration test passes end-to-end
- Coverage report generated and gaps documented

---

### Phase 1: Diagnostics Model + Shared Parse Cache

**Timeline:** After Phase 0
**Risk:** Low
**Breaking changes:** None (additive only)

**Objective:** Introduce foundational infrastructure that all subsequent phases depend on.

#### Deliverables

1. **`compiler/diagnostics.py`**
   ```python
   class DiagnosticLevel(Enum):
       ERROR = "error"
       WARNING = "warning"

   @dataclass
   class Diagnostic:
       level: DiagnosticLevel
       stage: str
       source: Optional[str]
       message: str
       code: str

   class DiagnosticLog:
       def error(self, stage, source, message, code): ...
       def warning(self, stage, source, message, code): ...
       def has_errors(self) -> bool: ...
       def summary(self) -> str: ...
   ```

2. **Shared parse cache in `ADRParser`**
   - Cache keyed on `(path, mtime, file_size)`
   - All generators that parse ADRs use the same cache instance
   - Cache is scope-local (cleared on scope change)

3. **Refactor existing generators to use shared cache**
   - `ManifestGenerator` uses cached parse results
   - `ArchitectureIndexGenerator` uses cached parse results
   - `MarkdownGenerator` uses cached parse results

4. **Refactor warnings to use `DiagnosticLog`**
   - Replace `print()` warnings in generators with `DiagnosticLog.warning()`
   - Replace exception-based error reporting with `DiagnosticLog.error()` where appropriate

#### Exit Criteria
- All golden-file tests still pass (output unchanged)
- Diagnostics model used by all generators
- Parse cache eliminates redundant file reads

---

### Phase 2: Intermediate Representation

**Timeline:** After Phase 1
**Risk:** Medium (core structural change)
**Breaking changes:** None (internal refactoring)

**Objective:** Introduce `ArchModel` as the unified in-memory representation.

#### Deliverables

1. **`compiler/ir/arch_model.py`**
   ```python
   @dataclass
   class ArchModel:
       corpus: ParsedCorpus          # all parsed ADRs + invariants
       entities: EntityGraph          # mutable node collection
       relationships: RelGraph        # mutable edge collection
       diagnostics: DiagnosticLog     # accumulated diagnostics
       metadata: CompilationMeta      # scope, timestamps, version
   ```

2. **`compiler/ir/entity_graph.py`**
   - Typed node collection with add/get/query operations
   - Supports entity types: ADR, Capability, Decision, Invariant, Component, System, Boundary, NFR, Gap
   - Each node carries provenance, completeness, metadata

3. **`compiler/ir/rel_graph.py`**
   - Typed edge collection with add/get/query operations
   - Supports 12 relationship types
   - Each edge carries evidence, confidence, provenance

4. **`compiler/ir/parsed_corpus.py`**
   - Container for all parsed source models
   - Provides iteration by type, lookup by ID

5. **Refactor `ArchitectureIndexGenerator`**
   - Step 1: Build `ArchModel` from parsed ADRs (IR construction)
   - Step 2: Extract entities into `EntityGraph` (still inline, but operating on IR)
   - Step 3: Build relationships into `RelGraph` (still inline)
   - Step 4: Emit registries from IR (backend)
   - Output must be identical to pre-refactor (golden-file tests enforce this)

#### Exit Criteria
- `ArchModel` exists and is populated during generation
- `ArchitectureIndexGenerator` operates through IR
- All golden-file tests pass
- IR is unit-testable independently

---

### Phase 3: Pass Decomposition

**Timeline:** After Phase 2
**Risk:** Medium
**Breaking changes:** None (internal refactoring)

**Objective:** Extract compilation logic from `ArchitectureIndexGenerator` into discrete,
testable, composable passes.

#### Deliverables

1. **Pass interface**
   ```python
   class CompilationPass(Protocol):
       name: str
       depends_on: list[str]

       def run(self, model: ArchModel, config: CompilerConfig) -> None: ...
   ```

2. **`compiler/passes/validate.py`**
   - Wraps `ADRValidator` + `EntityValidator`
   - Appends diagnostics to `model.diagnostics`
   - In strict mode: halts pipeline on any error

3. **`compiler/passes/extract_entities.py`**
   - Extracted from `ArchitectureIndexGenerator`
   - Populates `model.entities` from `model.corpus`
   - One extraction function per ADR type

4. **`compiler/passes/extract_relationships.py`**
   - Extracted from `ArchitectureIndexGenerator`
   - Populates `model.relationships` from `model.corpus` + `model.entities`

5. **`compiler/passes/normalize.py`**
   - Wraps `canonical_id_normalizer.py`
   - Operates on `model.entities` + `model.relationships`

6. **`compiler/passes/resolve_references.py`**
   - Extracted from `ArchitectureIndexGenerator`
   - Marks unresolved references in `model.diagnostics`

7. **`compiler/passes/score_completeness.py`**
   - Extracted from `ArchitectureIndexGenerator`
   - Annotates each entity with completeness metadata

8. **`compiler/pass_manager.py`**
   ```python
   class PassManager:
       def register(self, pass_: CompilationPass) -> None: ...
       def run_all(self, model: ArchModel, config: CompilerConfig) -> None: ...
       # Resolves ordering from depends_on; detects cycles
   ```

#### Exit Criteria
- Each pass independently unit-testable
- `PassManager` runs all passes in correct order
- Full pipeline through passes produces identical output (golden-file tests)
- `ArchitectureIndexGenerator` is now a thin wrapper: build IR → run passes → emit

---

### Phase 4: Unified Compiler Driver + CLI

**Timeline:** After Phase 3
**Risk:** Low (composition of existing parts)
**Breaking changes:** None (new command; existing commands preserved)

**Objective:** Single `adr compile` entry point that orchestrates the full pipeline.

#### Deliverables

1. **`compiler/driver.py`**
   ```python
   class ArchitectureCompiler:
       def compile(self, scope: Path, config: CompilerConfig) -> CompilationResult: ...
       # Runs: frontend → IR build → passes → backend → finalize
   ```

2. **`CompilationResult`**
   ```python
   @dataclass
   class CompilationResult:
       success: bool
       artifacts: list[OutputArtifact]
       diagnostics: DiagnosticLog
       statistics: CompilationStatistics
       duration_ms: int
   ```

3. **Backend emitters** (extracted from generators)
   - `compiler/backend/registry_emitter.py`
   - `compiler/backend/manifest_emitter.py`
   - `compiler/backend/markdown_emitter.py`

4. **CLI command**
   ```
   adr compile [--scope PATH] [--strict] [--output DIR] [--skip-markdown] [--timestamp ISO]
   ```

5. **Existing commands as aliases**
   - `adr generate-architecture-index` → calls compiler with registry-only backend
   - `adr generate-manifest` → calls compiler with manifest-only backend
   - `adr validate` → calls compiler frontend + validate pass only

#### Exit Criteria
- `adr compile` produces all artifacts in one invocation
- Existing commands still work (backward compatible)
- Compilation report printed to stdout
- `--strict` flag fails on any warning

---

### Phase 5: Kernel Interface Contract

**Timeline:** After Phase 4
**Risk:** High (requires alignment with ste-kernel)
**Breaking changes:** New output artifact (additive)

**Objective:** Define and implement the formal contract between adr-kit compiler output
and ste-kernel consumption.

#### Deliverables

1. **Contract schema definition**
   - Versioned schema for kernel-consumable bundle
   - Semantic versioning (breaking change = major bump)
   - Schema published as JSON Schema in `schema/kernel/`

2. **Contract ADR**
   - New logical ADR documenting the contract decision
   - Specifies: what the kernel expects, what the compiler guarantees

3. **`compiler/backend/kernel_emitter.py`**
   - Emits kernel-bundle artifact from IR
   - Includes: entity graph, relationship graph, validation summary, schema version
   - Format: single YAML file or structured directory

4. **Contract tests**
   - Tests that validate compiler output against kernel contract schema
   - Runnable without ste-kernel present (schema-only validation)
   - Mirror tests in ste-kernel that validate input against same schema

5. **CLI command**
   ```
   adr compile --emit kernel-bundle [--contract-version 1.0]
   ```

#### Exit Criteria
- Contract schema defined and published
- Kernel emitter produces valid contract bundles
- Contract tests pass in adr-kit CI
- Documentation for ste-kernel integration

---

### Phase 6: Graph Export + Architecture Analysis

**Timeline:** After Phase 4 (parallel with Phase 5)
**Risk:** Low
**Breaking changes:** None (additive)

**Objective:** Make the architecture graph a first-class, exportable, analyzable artifact.

#### Deliverables

1. **Graph export backends**
   - `compiler/backend/graph_emitter.py`
   - DOT format (Graphviz visualization)
   - JSON-LD format (semantic web interoperability)
   - Adjacency-list JSON (lightweight programmatic access)

2. **Analysis passes**
   - `compiler/passes/lint.py` — architecture quality warnings
     - Orphan entities (no relationships)
     - Entities with only inbound or only outbound relationships
     - Missing descriptions on public entities
     - Naming convention violations
   - `compiler/passes/graph_analysis.py` — structural analysis
     - Cycle detection in dependency relationships
     - Strongly-connected component identification
     - Reachability analysis (can every entity reach a root ADR?)
     - Layer violation detection (physical referencing logical internals)

3. **CLI commands**
   ```
   adr compile --emit graph --format dot
   adr compile --emit graph --format json-ld
   adr graph stats          # entity/relationship counts, density, diameter
   ```

4. **Graph query (stretch goal)**
   - Simple path queries: "what does CAP-0001 depend on?"
   - Impact queries: "what is affected if we change ADR-L-0005?"

#### Exit Criteria
- Graph exportable in DOT and JSON-LD
- Lint pass produces actionable warnings
- Graph analysis detects cycles and orphans

---

### Phase 7: Incremental Compilation (Future)

**Timeline:** When scale demands it
**Risk:** Medium
**Breaking changes:** None

**Objective:** Only recompile what changed since last compilation.

#### Deliverables

1. **Compilation cache**
   - Store last compilation IR + source fingerprints
   - On next compile: compare source fingerprints, identify changed files
   - Re-parse only changed files; merge into cached IR

2. **Incremental pass execution**
   - Passes track which entities they produced from which sources
   - Changed source → invalidate derived entities → re-run affected passes

3. **Cache invalidation**
   - Schema change → full recompile
   - Generator version change → full recompile
   - Source file change → incremental
   - `--clean` flag → force full recompile

#### Exit Criteria
- Incremental compile is at least 3x faster than full compile for single-file changes
- Output identical to full compile (golden-file tests)

---

## 3. Cross-Cutting Concerns

### 3.1 Backward Compatibility Strategy

| Phase | Compatibility Guarantee |
|-------|------------------------|
| 0-3 | All existing CLI commands produce identical output |
| 4 | New `adr compile` command added; existing commands become aliases |
| 5+ | Existing commands still work; new output artifacts are additive |

**Rule:** No existing CLI command changes its output format or behavior without a deprecation
cycle (warn for one release, remove in the next).

### 3.2 Testing Strategy

| Test Type | Purpose | When |
|-----------|---------|------|
| Golden-file tests | Detect output drift during refactoring | Phase 0 onward |
| Pass unit tests | Verify each pass in isolation | Phase 3 onward |
| Pipeline integration tests | End-to-end compilation correctness | Phase 0 onward |
| Contract tests | Validate kernel interface compliance | Phase 5 onward |
| Determinism tests | Reproducible output with pinned timestamps | Phase 4 onward |
| Performance tests | Compilation stays within time budget | Phase 4 onward |

### 3.3 Schema Evolution

- v1.0 schemas: frozen (source ADR format)
- v1.1 schemas: may evolve through Phase 2-3 as IR stabilizes
- v2.0 schemas: introduced only if breaking changes required (Phase 5+)
- Kernel contract schema: independently versioned

### 3.4 Module Layout (Target)

```
src/adr_kit/
├── cli/
│   └── main.py              (existing — add compile command)
├── compiler/
│   ├── driver.py             (Phase 4 — orchestrator)
│   ├── config.py             (Phase 1 — compiler configuration)
│   ├── diagnostics.py        (Phase 1 — diagnostic model)
│   ├── pass_manager.py       (Phase 3 — pass ordering)
│   ├── ir/
│   │   ├── arch_model.py     (Phase 2)
│   │   ├── entity_graph.py   (Phase 2)
│   │   ├── rel_graph.py      (Phase 2)
│   │   └── parsed_corpus.py  (Phase 2)
│   ├── frontend/
│   │   ├── discovery.py      (Phase 2 — from scope + parser)
│   │   └── parser.py         (Phase 1 — cached parser)
│   ├── passes/
│   │   ├── validate.py       (Phase 3)
│   │   ├── extract_entities.py    (Phase 3)
│   │   ├── extract_relationships.py (Phase 3)
│   │   ├── normalize.py      (Phase 3)
│   │   ├── resolve_references.py  (Phase 3)
│   │   ├── score_completeness.py  (Phase 3)
│   │   ├── lint.py           (Phase 6)
│   │   └── graph_analysis.py (Phase 6)
│   └── backend/
│       ├── registry_emitter.py    (Phase 4)
│       ├── manifest_emitter.py    (Phase 4)
│       ├── markdown_emitter.py    (Phase 4)
│       ├── graph_emitter.py       (Phase 6)
│       └── kernel_emitter.py      (Phase 5)
├── generators/               (existing — gradually delegates to compiler/)
├── validators/               (existing — wrapped by compiler/passes/)
├── models/                   (existing — unchanged)
├── integrity/                (existing — unchanged)
├── parser/                   (existing — wrapped by compiler/frontend/)
├── repository/               (existing — reads compiler output)
├── scope/                    (existing — used by compiler/frontend/)
├── migrators/                (existing — unchanged)
└── templates/                (existing — used by backend/markdown_emitter)
```

**Migration strategy:** New `compiler/` package grows alongside existing packages.
Existing generators are gradually thinned to delegate to compiler subsystems.
No big-bang rewrite.

---

## 4. Risks and Constraints

### Risks by Phase

| Phase | Key Risk | Likelihood | Mitigation |
|-------|----------|-----------|------------|
| 0 | Golden files are fragile (whitespace, ordering) | Medium | Normalize before comparison; use semantic diff |
| 1 | Parse cache introduces stale data | Low | Cache keyed on mtime+size; invalidate aggressively |
| 2 | IR design doesn't accommodate future entity types | Medium | Keep IR extensible (dict-based metadata, not fixed fields) |
| 3 | Pass extraction introduces subtle ordering bugs | Medium | Integration tests + golden files catch regressions |
| 4 | `adr compile` performance regression from unified pipeline | Low | Profile; lazy backend emission |
| 5 | Kernel contract designed without kernel team | High | Define contract collaboratively; iterate |
| 6 | Graph analysis scales poorly on large architectures | Low | O(V+E) algorithms; defer expensive analysis to opt-in |
| 7 | Incremental cache invalidation misses edge cases | High | Always validate against full-compile golden output |

### Hard Constraints

1. **Python 3.11+** — established, non-negotiable
2. **No new runtime dependencies** — pydantic, pyyaml, jsonschema, jinja2, click only
3. **Deterministic output** — bit-identical output for identical input (modulo timestamps)
4. **Multi-scope support** — all phases must respect INV-0019 scope boundaries
5. **STE governance** — architectural changes require ADRs per PRIME-1/PRIME-2
6. **Backward compatibility** — existing CLI commands and output formats preserved

### Decision Points

| Decision | When | Options | Recommended |
|----------|------|---------|-------------|
| IR mutability model | Phase 2 | Mutable dataclass vs immutable+copy | Mutable (simpler, fits pass pattern) |
| Pass error semantics | Phase 3 | Fail-fast vs accumulate-all | Accumulate with configurable strict mode |
| Kernel contract format | Phase 5 | Single YAML vs directory bundle | Decide with kernel team |
| Graph format primary | Phase 6 | DOT vs JSON-LD vs custom | DOT for visualization, JSON-LD for interop |
| Cache storage format | Phase 7 | Pickle vs JSON vs SQLite | JSON (inspectable, portable) |

---

## 5. Success Metrics

| Metric | Target | Measured By |
|--------|--------|-------------|
| Single-command compilation | `adr compile` produces all artifacts | Phase 4 delivery |
| Zero redundant parsing | Each source file parsed exactly once per compile | Parse cache hit rate = 100% after first pass |
| Pass isolation | Each pass testable with synthetic IR (no file I/O) | Phase 3 test suite |
| Output determinism | Bit-identical output across runs (pinned timestamp) | Determinism test in CI |
| Kernel readiness | Contract schema defined and validated | Phase 5 delivery |
| Graph exportable | DOT + JSON-LD export working | Phase 6 delivery |
| Compilation time | < 5 seconds for 31 ADRs | Performance test in CI |
| Diagnostic coverage | All pipeline errors have diagnostic codes | Phase 1-3 cumulative |
