# ADR-Kit Architecture Evolution

## Purpose

This document defines the architectural evolution path from the current adr-architecture-kit
(a toolkit for machine-verifiable ADRs) into a deterministic **architecture compiler** that
produces normalized, kernel-consumable registries from ADR source artifacts.

---

## 1. Current State Analysis

### What the Repository Is Today

The adr-architecture-kit is a Python library (`src/adr_kit/`) with a Click CLI (`adr` command)
that performs:

| Responsibility | Implementation | Maturity |
|---|---|---|
| ADR schema authority | JSON Schema v1.0 + v1.1 (17 schemas) | Stable |
| ADR parsing | `parser/yaml_parser.py` — YAML to Pydantic with JSON Schema gate | Stable |
| Source ADR generation | `generators/{logical,physical_system,physical_component}_generator.py` | Stable |
| Manifest generation | `generators/manifest_generator.py` — statistics, hashes, indexes | Stable |
| Entity extraction | `generators/architecture_index_generator.py` — 8 entity types from ADRs | Functional |
| Relationship normalization | Same generator — 12 relationship types with evidence + confidence | Functional |
| Registry generation | 9 output files in `adrs/index/` | Functional |
| Validation | `validators/` — schema, business logic, cross-refs, integrity | Stable |
| Integrity verification | `integrity/` — SHA256 headers, staleness, tamper detection | Stable |
| Multi-scope support | `scope/resolver.py` — recursive project boundary detection | Stable |
| Repository abstraction | `repository/architecture_repository.py` — load/query registries | Early |
| Markdown rendering | `generators/views/markdown.py` — Jinja2 human-readable views | Stable |
| Legacy compatibility | v1.0 entity-registry alongside v1.1 normalized model | Present |

### Architectural Shape

The current system follows a **generate-on-demand** pattern:

```
CLI command
  -> ScopeResolver (find project root)
  -> ADRParser (YAML -> Pydantic)
  -> Generator (model -> output artifact)
  -> Validator (optional post-check)
  -> Disk write (with integrity header)
```

Each generator operates independently. There is no unified compilation pipeline,
no intermediate representation (IR), and no formal pass ordering.

### What Works Well

1. **Schema-first design** — JSON Schema + Pydantic provides strong type guarantees
2. **Deterministic output** — integrity headers with SHA256 enable reproducibility checks
3. **Entity extraction** — 8 entity types (CAP, DEC, INV, COMP, SYS, BOUND, NFR, GAP) with provenance
4. **Relationship graph** — 12 typed relationships with confidence scoring and evidence
5. **Multi-scope** — recursive workspace support via INV-0019
6. **Completeness tracking** — entities flagged as complete/partial/reference_only/conflicted

---

## 2. Architectural Gaps

### 2.1 No Unified Compilation Pipeline

**Problem:** Generators are independent CLI commands (`generate-manifest`, `generate-architecture-index`,
`generate-entity-registry`, `generate-rendered-docs`). There is no single `compile` entry point
that orchestrates all stages in dependency order.

**Impact:** Users must know the correct invocation order. No guarantee that all registries
are mutually consistent at any point in time. No pipeline-level error propagation.

### 2.2 No Intermediate Representation (IR)

**Problem:** Each generator independently parses ADR YAML and extracts its own view.
`ManifestGenerator` and `ArchitectureIndexGenerator` both discover and parse the same files
but do not share a common intermediate model.

**Impact:** Duplicated work, risk of divergent extraction logic, no place to attach
cross-cutting analysis (e.g., dead entity detection, cycle analysis).

### 2.3 No Formal Compilation Passes

**Problem:** Entity extraction, relationship normalization, completeness scoring, and
unresolved detection are all embedded within `ArchitectureIndexGenerator._generate_discovery_artifacts()`.
There is no separation into discrete, testable, composable passes.

**Impact:** Difficult to extend with new analysis passes (e.g., graph consistency,
invariant coverage, architecture drift detection). Hard to test individual stages in isolation.

### 2.4 Missing Kernel Interface Contract

**Problem:** The output registries are YAML files on disk. There is no formal contract
defining what the STE Kernel expects — no versioned output schema, no contract tests,
no handshake protocol.

**Impact:** Kernel integration will be fragile. Schema evolution could silently break
downstream consumers. No way to validate that output satisfies kernel requirements
without the kernel being present.

### 2.5 No Graph Export

**Problem:** The relationship registry captures a graph, but there is no export to
standard graph formats (DOT, GraphML, JSON-LD, Cypher). The `ArchitectureRepository`
provides flat list queries but no graph traversal API.

**Impact:** The architecture graph — the most valuable output — is locked in a
YAML-list representation with no path to visualization, querying, or semantic reasoning.

### 2.6 No Incremental Compilation

**Problem:** Every generation run re-parses all ADR files from scratch. For small
repositories this is fine, but the architecture does not support incremental builds
(only recompile what changed).

**Impact:** Acceptable now. Will become a scaling concern when the kit is used
across many STE workspaces with hundreds of ADRs.

### 2.7 Validator-Generator Coupling

**Problem:** Validation is available as separate CLI commands but is not integrated
into the generation pipeline as a mandatory gate. You can generate registries from
invalid ADRs.

**Impact:** Output registries may contain entities derived from structurally invalid
source artifacts. No fail-fast guarantee.

### 2.8 No Schema Migration Framework

**Problem:** Schema versions (v1.0 → v1.1) exist but there is no formal migration
framework for evolving registry schemas. The legacy v1.0 entity-registry is maintained
alongside v1.1 through separate code paths.

**Impact:** Each schema version bump requires manual dual-path maintenance.
No automated migration or compatibility checking.

---

## 3. Proposed Subsystem Structure

### Target Architecture: Compiler Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADR Architecture Compiler                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌────────────┐  │
│  │  Frontend │──>│    IR    │──>│   Passes  │──>│  Backend   │  │
│  └──────────┘   └──────────┘   └───────────┘   └────────────┘  │
│                                                                  │
│  Frontend:        IR:             Passes:         Backend:       │
│  - Source         - ArchModel     - Validate      - Registry    │
│    Discovery      - EntityGraph   - Extract       - Graph       │
│  - YAML Parse     - RelGraph      - Normalize     - Manifest    │
│  - Schema Gate    - Diagnostics   - Resolve       - Markdown    │
│  - Scope Resolve                  - Score         - Kernel      │
│                                   - Lint            Contract    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Cross-cutting: Integrity | Diagnostics | Scope | Config        │
└─────────────────────────────────────────────────────────────────┘
```

### Subsystem Definitions

#### 3.1 Frontend (`compiler/frontend/`)

Responsible for: source discovery, parsing, schema validation, scope resolution.

- `discovery.py` — Find all ADR/invariant files within scope boundaries
- `parser.py` — YAML parse + JSON Schema gate (refactored from current `parser/`)
- `scope.py` — Project scope resolution (current `scope/resolver.py`)
- Output: raw parsed models (current Pydantic ADR models)

#### 3.2 Intermediate Representation (`compiler/ir/`)

Responsible for: a unified in-memory model that all passes operate on.

- `arch_model.py` — `ArchModel` containing all parsed ADRs, invariants, metadata
- `entity_graph.py` — Mutable entity collection with typed nodes
- `rel_graph.py` — Mutable relationship collection with typed edges
- `diagnostics.py` — Accumulated warnings, errors, unresolved references

The IR is the single source of truth during compilation. Passes read from and
write to the IR. No pass re-parses source files.

#### 3.3 Compilation Passes (`compiler/passes/`)

Ordered, composable, independently testable transformations on the IR.

| Pass | Input | Output | Current Location |
|------|-------|--------|-----------------|
| `validate` | ArchModel | Diagnostics | `validators/adr_validator.py` |
| `extract_entities` | ArchModel | EntityGraph | `architecture_index_generator.py` (inline) |
| `extract_relationships` | ArchModel + EntityGraph | RelGraph | `architecture_index_generator.py` (inline) |
| `normalize` | EntityGraph + RelGraph | Normalized IDs, deduplication | `canonical_id_normalizer.py` |
| `resolve_references` | EntityGraph + RelGraph | Unresolved list, cross-ref links | `architecture_index_generator.py` (inline) |
| `score_completeness` | EntityGraph | Completeness metadata | `architecture_index_generator.py` (inline) |
| `lint` | ArchModel + EntityGraph | Diagnostics (warnings) | New |
| `graph_analysis` | EntityGraph + RelGraph | Cycle detection, orphan detection | New |

Each pass is a function: `(IR) -> IR` with accumulated diagnostics.

#### 3.4 Backend (`compiler/backend/`)

Responsible for: serializing the IR into output artifacts.

- `registry_emitter.py` — Emit all 9 registry YAML files from IR
- `manifest_emitter.py` — Emit manifest.yaml from IR
- `graph_emitter.py` — Emit graph exports (DOT, JSON-LD, GraphML)
- `markdown_emitter.py` — Emit rendered markdown from IR
- `kernel_contract.py` — Emit kernel-interface bundle with version contract

#### 3.5 Driver (`compiler/driver.py`)

The orchestrator. Runs frontend → IR construction → passes → backend in order.
Single entry point: `compile(scope, config) -> CompilationResult`.

```python
class CompilationResult:
    success: bool
    diagnostics: list[Diagnostic]
    artifacts: list[OutputArtifact]
    ir: ArchModel  # available for programmatic consumers
```

---

## 4. Phased Implementation Plan

### Phase 1: IR Introduction (Foundation)

**Goal:** Introduce `ArchModel` IR without breaking existing generators.

1. Define `ArchModel`, `EntityGraph`, `RelGraph` data structures
2. Refactor `ArchitectureIndexGenerator` to populate IR first, then emit from IR
3. Ensure all existing tests pass against the refactored path
4. No CLI changes — existing commands work unchanged

**Exit criteria:** `generate-architecture-index` produces identical output via IR path.

### Phase 2: Pass Decomposition

**Goal:** Extract compilation logic into discrete passes.

1. Extract entity extraction into `extract_entities` pass
2. Extract relationship building into `extract_relationships` pass
3. Extract normalization into `normalize` pass
4. Extract completeness scoring into `score_completeness` pass
5. Extract unresolved detection into `resolve_references` pass
6. Wire passes through a `PassManager` with ordering constraints

**Exit criteria:** Each pass independently testable. Pipeline produces identical output.

### Phase 3: Unified Driver + Validation Gate

**Goal:** Single `adr compile` command. Validation as mandatory first pass.

1. Implement `compiler/driver.py` with ordered pass execution
2. Integrate `ADRValidator` as the first pass (fail-fast on invalid source)
3. Add `adr compile [--scope] [--output]` CLI command
4. Existing commands remain as aliases

**Exit criteria:** `adr compile` produces all registries + manifest + markdown in one invocation.

### Phase 4: Kernel Interface Contract

**Goal:** Formal output contract for STE Kernel consumption.

1. Define kernel contract schema (versioned, with compatibility guarantees)
2. Implement `kernel_contract.py` emitter
3. Add contract validation tests (can run without kernel present)
4. Document contract in a dedicated ADR

**Exit criteria:** Kernel can consume compiler output with version-checked contract.

### Phase 5: Graph Export + Analysis

**Goal:** Architecture graph becomes a first-class queryable artifact.

1. Add graph export backends (DOT, JSON-LD)
2. Add `graph_analysis` pass (cycle detection, orphan detection, coverage gaps)
3. Add `adr graph export [--format]` CLI command
4. Add `adr graph query` for basic traversals

**Exit criteria:** Architecture graph exportable and analyzable.

---

## 5. Risks and Constraints

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| IR introduction breaks existing output determinism | Medium | High | Bit-for-bit comparison tests against current output |
| Pass ordering creates subtle dependencies | Medium | Medium | Explicit dependency declarations in PassManager |
| Kernel contract designed without kernel team input | High | High | Define contract collaboratively; use contract tests |
| Over-engineering compiler model for current scale | Medium | Low | Keep phases incremental; ship each phase independently |
| Schema v1.1 → v2.0 migration needed for IR model | Low | Medium | IR is internal; registry schemas are the contract |

### Constraints

1. **Python 3.11+ only** — established by `pyproject.toml`
2. **Pydantic v2** — all models use Pydantic; IR must be compatible
3. **Deterministic output** — integrity headers require byte-stable YAML serialization
4. **Backward compatibility** — v1.0 entity-registry must remain available during transition
5. **No runtime dependencies beyond current set** — pydantic, pyyaml, jsonschema, jinja2, click
6. **Multi-scope** — compiler must respect INV-0019 scope boundaries
7. **STE governance** — changes must be traceable to ADRs per PRIME-1/PRIME-2
