# Architecture Compiler Overview

## Purpose

This document defines the architecture compiler — a system that transforms
ADR source artifacts into a deterministic, normalized architecture model
consumable by the STE Kernel. The design follows classical compiler theory:
frontend (parsing), middle-end (analysis and transformation), backend (emission).

---

## 1. Compiler Identity

**What it compiles:**
Architecture intent expressed as typed YAML artifacts (ADRs, invariants)

**What it produces:**
A normalized architecture knowledge model — entities, relationships, gaps,
and provenance — serialized as deterministic registry artifacts

**Analogy to a language compiler:**

| Language Compiler | Architecture Compiler |
|---|---|
| Source files (.c, .rs) | ADR artifacts (.yaml) |
| Lexing + parsing | YAML parse + JSON Schema validation |
| AST | Parsed Pydantic models (typed ADR trees) |
| IR (SSA, MIR) | ArchModel (entity graph + relationship graph) |
| Optimization passes | Analysis passes (normalize, resolve, score, lint) |
| Code generation | Registry emission (YAML registries, graph exports) |
| Linker | Cross-scope resolution (multi-scope compilation) |
| Object files | Per-scope registry bundles |
| Executable | Architecture index (kernel-consumable bundle) |

---

## 2. Current Compilation System (Implicit)

The repository already implements a compilation pipeline, but it is not
structured as one. The logic lives across these files:

### Frontend (Discovery + Parsing)

| Component | File | Role |
|---|---|---|
| File discovery | `architecture_index_generator.py:66-75` | Walk `logical/`, `physical/`, `invariants/` directories |
| YAML parsing | `parser/yaml_parser.py` | YAML → dict with JSON Schema validation |
| Model construction | `parser/yaml_parser.py` (parse_adr, parse_logical_adr, parse_invariant) | dict → Pydantic model with type discrimination |
| Schema gate | `parser/yaml_parser.py` (validate_against_schema) | JSON Schema Draft-07 structural + complete modes |
| Scope resolution | `scope/resolver.py` | Find project root, ADR directory, namespace |

### Middle-End (Extraction + Analysis)

All currently embedded in `ArchitectureIndexGenerator.generate_from_directory()`:

| Stage | Lines (approx) | What It Does |
|---|---|---|
| ADR entity extraction | 313-324 | Create NormalizedEntity for each ADR |
| Capability extraction | 325-341 | Extract CAP-XXXX from logical ADR capabilities |
| Decision extraction | 342-361 | Extract DEC-XXXX from logical ADR decisions |
| Invariant collection | 362-437 | Collect INV-XXXX from ADRs + standalone files, merge duplicates |
| Physical ADR extraction | 439-484 | Extract systems (SYS-XXXX), components (COMP-XXXX) |
| Declared-in linking | 486-490 | Entity → parent ADR relationships |
| Cross-reference linking | 492-553 | Decision→invariant, capability→component, decision→capability, etc. |
| Unresolved detection | 500-546 | Missing targets → UnresolvedRecord |
| Gap extraction | 379-390 | Author-declared gaps → unresolved records |
| Bundle validation | 190-229 | Post-hoc consistency check (no dangling refs) |
| Subset filtering | 558-562 | Split entity registry into type-specific registries |
| Legacy mapping | 563 | v1.1 entities → v1.0 Entity model |

### Backend (Emission)

| Component | File | Role |
|---|---|---|
| Registry serialization | `architecture_index_generator.py:598-632` | ArchModel → 10 YAML files |
| Manifest generation | `manifest_generator.py` | Source statistics → manifest.yaml |
| Markdown rendering | `generators/views/markdown.py` | Pydantic models → Jinja2 → markdown |
| Integrity headers | `integrity/core.py` | SHA256 source/rendered hash computation |

### Validation (Separate Pipeline)

| Component | File | Role |
|---|---|---|
| Per-file validation | `validators/adr_validator.py` | Schema + business rules per ADR |
| Cross-reference validation | `validators/adr_validator.py:463-592` | implements_logical exists, related_adrs exist |
| Entity validation | `validators/entity_validator.py` | Entity ID formats, relationship consistency |
| Integrity validation | `integrity/validation.py` | Generated artifact hash verification |

**Critical observation:** Validation and generation are decoupled. You can generate
registries from invalid ADRs. The validator does not feed into the generator.

---

## 3. Identified Compilation Stages

Analyzing the existing code, 14 discrete compilation stages can be identified:

### Stage 1: Source Discovery
**Current:** `_discover_source_files()` in both `ArchitectureIndexGenerator` and `ADRValidator`
**Input:** Scope root path
**Output:** Classified file lists (logical, physical-system, physical-component, invariant)

### Stage 2: Source Parsing
**Current:** `ADRParser.parse_adr()`, `parse_logical_adr()`, `parse_invariant()`
**Input:** File paths
**Output:** Typed Pydantic models (LogicalADR, PhysicalSystemADR, PhysicalComponentADR, StandaloneInvariant)

### Stage 3: Schema Validation
**Current:** `ADRParser.validate_against_schema()` (called during parsing)
**Input:** Raw YAML dict + schema name
**Output:** Pass/fail with JSON Schema errors

### Stage 4: Business Rule Validation
**Current:** `ADRValidator._validate_logical_adr()`, `_validate_physical_*()` methods
**Input:** Typed Pydantic models
**Output:** ValidationError list (errors + warnings)

### Stage 5: Cross-Reference Validation
**Current:** `ADRValidator.validate_cross_references()`
**Input:** All parsed ADRs
**Output:** Cross-reference errors (missing implements_logical targets, etc.)

### Stage 6: ADR Entity Extraction
**Current:** Lines 313-451 of `generate_from_directory()`
**Input:** Parsed ADR models
**Output:** NormalizedEntity nodes for ADRs, capabilities, decisions, invariants

### Stage 7: Physical Entity Extraction
**Current:** Lines 439-484 of `generate_from_directory()`
**Input:** Parsed physical ADR models
**Output:** NormalizedEntity nodes for systems, components

### Stage 8: Invariant Canonical Resolution
**Current:** Lines 362-437 (invariant_mentions collection + merge)
**Input:** Invariants from ADRs + standalone invariant files
**Output:** Deduplicated invariant entities with canonical source assignment

### Stage 9: Relationship Derivation
**Current:** Lines 486-553 of `generate_from_directory()`
**Input:** All entities + parsed ADR cross-references
**Output:** RelationshipRecord edges (12 typed relationships with evidence + confidence)

### Stage 10: Unresolved Reference Detection
**Current:** Inline within relationship derivation (lines 500-546)
**Input:** Relationship targets that don't resolve to known entities
**Output:** UnresolvedRecord list

### Stage 11: Bundle Consistency Validation
**Current:** `_validate_bundle()` (lines 190-229)
**Input:** Complete entity registry + relationship registry + unresolved registry
**Output:** Pass/fail (ValueError on inconsistency)

### Stage 12: Subset Registry Generation
**Current:** Lines 558-562 (`_filtered()` calls)
**Input:** Full entity registry
**Output:** capability-registry, decision-registry, invariant-registry, component-registry, system-registry

### Stage 13: Legacy Compatibility Mapping
**Current:** Lines 563 + `_legacy_entity()` method
**Input:** v1.1 NormalizedEntity
**Output:** v1.0 Entity (subset of types, simplified relationships)

### Stage 14: Registry Emission
**Current:** `save_bundle()` (lines 601-632)
**Input:** Complete ArchitectureDiscoveryBundle
**Output:** 10 YAML files on disk

---

## 4. Complete Compiler Architecture

### 4.1 Pipeline Structure

```
                    ┌──────────────────────────────────┐
                    │         COMPILER FRONTEND          │
                    │                                    │
  ADR YAML ────────>│  1. Discover   (file enumeration) │
  Invariant YAML ──>│  2. Parse      (YAML → AST)       │
  PROJECT.yaml ────>│  3. Validate   (schema gate)      │
                    │                                    │
                    └──────────────┬───────────────────┘
                                   │
                                   │  ParsedCorpus
                                   │  (typed AST forest)
                                   │
                    ┌──────────────▼───────────────────┐
                    │         IR CONSTRUCTION            │
                    │                                    │
                    │  Assemble ArchModel from corpus    │
                    │  Initialize empty EntityGraph      │
                    │  Initialize empty RelGraph         │
                    │  Initialize DiagnosticLog          │
                    │                                    │
                    └──────────────┬───────────────────┘
                                   │
                                   │  ArchModel (mutable)
                                   │
                    ┌──────────────▼───────────────────┐
                    │         COMPILER MIDDLE-END        │
                    │                                    │
                    │  Pass 1: validate_business_rules   │
                    │  Pass 2: validate_cross_refs       │
                    │  Pass 3: extract_logical_entities  │
                    │  Pass 4: extract_physical_entities │
                    │  Pass 5: resolve_invariant_canon   │
                    │  Pass 6: derive_relationships      │
                    │  Pass 7: detect_unresolved         │
                    │  Pass 8: score_completeness        │
                    │  Pass 9: validate_bundle           │
                    │  Pass 10: lint (optional)          │
                    │  Pass 11: graph_analysis (optional)│
                    │                                    │
                    └──────────────┬───────────────────┘
                                   │
                                   │  ArchModel (populated)
                                   │
                    ┌──────────────▼───────────────────┐
                    │         COMPILER BACKEND           │
                    │                                    │
                    │  Emitter: registries (9 files)     │
                    │  Emitter: manifest                 │
                    │  Emitter: legacy registry          │
                    │  Emitter: architecture index       │
                    │  Emitter: markdown views           │
                    │  Emitter: graph export (future)    │
                    │  Emitter: kernel bundle (future)   │
                    │                                    │
                    └──────────────┬───────────────────┘
                                   │
                                   │  OutputBundle
                                   │
                    ┌──────────────▼───────────────────┐
                    │         FINALIZATION               │
                    │                                    │
                    │  Compute integrity headers         │
                    │  Write to disk                     │
                    │  Round-trip verification            │
                    │  Emit CompilationResult            │
                    │                                    │
                    └──────────────────────────────────┘
```

### 4.2 Key Design Decisions

**D1: Single IR, multiple passes.**
All analysis operates on one `ArchModel`. No pass re-reads source files.
This eliminates the current redundant parsing and guarantees all stages
see the same data.

**D2: Passes are pure functions on mutable state.**
Each pass mutates the `ArchModel` in place and appends diagnostics.
This is simpler than an immutable-copy model and matches the existing
code's mutation patterns.

**D3: Validation is the first pass, not a separate pipeline.**
The current system allows generation from invalid ADRs. In the compiler
model, validation is Pass 1. In `--strict` mode, any error halts the
pipeline. In `--lenient` mode, invalid artifacts are excluded from the
corpus with a WARNING diagnostic.

**D4: Entity extraction precedes relationship derivation.**
This is the current implicit ordering. Making it explicit prevents
relationships from referencing entities that haven't been extracted yet.

**D5: Invariant canonical resolution is a distinct pass.**
Currently, invariants are collected during logical ADR extraction and
then merged in a second loop. This two-phase pattern deserves its own
pass because it handles multi-source invariants (standalone + ADR-local)
with deduplication and canonical source assignment.

**D6: Backend emitters are independent.**
Each emitter reads the finalized IR and produces output. Emitters can
be selectively enabled (e.g., `--emit registries,manifest` skips markdown).
This replaces the current model where each generator is a separate CLI command.

---

## 5. Source Type System

The compiler processes a typed source language. The type hierarchy:

```
SourceArtifact
├── LogicalADR          (ADR-L-XXXX, ADR-V-XXXX)
│   ├── .capabilities       → Capability[]     (CAP-XXXX)
│   ├── .decisions           → Decision[]       (DEC-XXXX)
│   ├── .invariants          → Invariant[]      (INV-XXXX)
│   ├── .constraints         → Constraint[]     (CONST-XXXX)
│   ├── .boundaries          → Boundary[]       (BOUND-XXXX)
│   ├── .nfrs                → NFR[]            (NFR-XXXX)
│   ├── .contracts           → Contract[]       (CONTRACT-XXXX)
│   └── .gaps                → Gap[]            (GAP-XXXX)
│
├── PhysicalSystemADR   (ADR-PS-XXXX)
│   ├── .implements_logical  → [ADR-L-XXXX]
│   ├── .technologies        → [string]
│   ├── .system_boundaries   → [string]
│   └── .references_components → [ADR-PC-XXXX]
│
├── PhysicalComponentADR (ADR-PC-XXXX)
│   ├── .implements_system   → [ADR-PS-XXXX]
│   ├── .implements_logical  → [ADR-L-XXXX]
│   ├── .component_specs     → ComponentSpec[]  (COMP-XXXX)
│   │   ├── .interfaces          → Interface[]  (IFACE-XXXX)
│   │   ├── .implements_capabilities → [CAP-XXXX]
│   │   └── .dependencies        → [COMP-XXXX]
│   ├── .integration_points  → IntegrationPoint[] (INTEG-XXXX)
│   └── .impl_decisions      → ImplDecision[]  (IMPL-XXXX)
│
├── PhysicalADR          (ADR-P-XXXX) — legacy
│   ├── .implements_logical  → [ADR-L-XXXX]
│   └── .component_specs     → ComponentSpec[]
│
└── StandaloneInvariant  (INV-XXXX)
    ├── .defined_in          → ADR-L-XXXX
    ├── .enforced_by         → [target IDs]
    └── .upheld_by_decisions → [DEC-XXXX]
```

### Entity ID Namespace

| Prefix | Entity Type | Source |
|--------|------------|--------|
| ADR-L-XXXX | Logical ADR | File identity |
| ADR-V-XXXX | Vision ADR | File identity |
| ADR-PS-XXXX | Physical System ADR | File identity |
| ADR-PC-XXXX | Physical Component ADR | File identity |
| ADR-P-XXXX | Physical ADR (legacy) | File identity |
| CAP-XXXX | Capability | LogicalADR.capabilities |
| DEC-XXXX | Decision | LogicalADR.decisions |
| INV-XXXX | Invariant | LogicalADR.invariants OR StandaloneInvariant |
| CONST-XXXX | Constraint | LogicalADR.constraints |
| BOUND-XXXX | Boundary | LogicalADR.boundaries |
| NFR-XXXX | Non-functional requirement | LogicalADR.nfrs |
| CONTRACT-XXXX | Interaction contract | LogicalADR.contracts |
| GAP-XXXX | Gap (author-declared) | LogicalADR.gaps |
| COMP-XXXX | Component | PhysicalComponentADR.component_specs |
| SYS-XXXX | System | Derived from ADR-PS-XXXX |
| IFACE-XXXX | Interface | ComponentSpec.interfaces |
| INTEG-XXXX | Integration point | PhysicalComponentADR.integration_points |
| IMPL-XXXX | Implementation decision | PhysicalComponentADR.impl_decisions |

### Relationship Type System

| Relationship | Semantics | Direction | Provenance |
|---|---|---|---|
| declared_in | Entity is defined within this ADR | entity → ADR | explicit |
| references | ADR cites another ADR | ADR → ADR | explicit |
| related_to | General association | any → any | derived |
| enforces | Decision/invariant enforces a constraint | decision → invariant | explicit |
| enabled_by | Capability enabled by a decision | capability → decision | derived (inverse of enables) |
| enables | Decision enables a capability | decision → capability | explicit |
| governs | Decision governs a component | decision → component | explicit |
| implemented_by | Capability implemented by component | capability → component | explicit |
| embodied_in | Component belongs to a system | component → system | explicit |
| supersedes | Entity replaces another | entity → entity | explicit |
| superseded_by | Entity replaced by another | entity → entity | derived (inverse) |
| refines | Decision refines another | decision → decision | explicit |

---

## 6. Compiler Modes

### Full Compilation (default)
```
adr compile
```
Runs all stages. Produces all output artifacts.

### Strict Mode
```
adr compile --strict
```
Any validation error (stage 1-2 of middle-end) halts the pipeline.
No output produced on failure.

### Lenient Mode
```
adr compile --lenient
```
Invalid artifacts excluded from corpus with WARNING.
Compilation continues with valid subset.

### Selective Emission
```
adr compile --emit registries
adr compile --emit manifest,registries
adr compile --emit graph --format dot
```
Only run backend emitters for requested outputs.
Middle-end passes always run (analysis is cheap; correctness requires it).

### Dry Run
```
adr compile --dry-run
```
Run full pipeline but don't write files. Report what would be produced.

### Check Mode
```
adr compile --check
```
Run full pipeline and compare against existing output.
Exit 0 if identical, exit 1 if drift detected.
Useful in CI to enforce that committed registries match source.

---

## 7. Risks and Constraints

### Risks

| Risk | Description | Mitigation |
|---|---|---|
| Output drift during refactoring | Restructuring the pipeline could subtly change entity ordering, relationship evidence, or YAML formatting | Golden-file tests: snapshot all current outputs, assert bit-identical after each refactoring phase |
| Pass coupling | Passes may develop implicit dependencies on execution order beyond declared deps | Integration tests that run full pipeline; property tests that verify pass idempotency |
| IR bloat | ArchModel accumulates all state; memory pressure on large repos | Profile with synthetic large corpus (1000 ADRs); add lazy loading if needed |
| Kernel contract mismatch | Compiler output schema may not match what kernel actually needs | Co-design contract schema with kernel team; contract tests on both sides |

### Constraints

1. **Determinism** — identical input must produce identical output (modulo `generated_at` timestamp, which can be pinned via `--timestamp`)
2. **Python 3.11+** — project baseline
3. **Pydantic v2** — all models already use Pydantic; IR must be Pydantic-compatible
4. **No new runtime deps** — pipeline built on pydantic, pyyaml, jsonschema, jinja2, click
5. **Multi-scope** — compiler must handle recursive scope boundaries (INV-0019)
6. **Backward compatible** — existing CLI commands must continue working during transition
7. **STE governance** — compiler changes traceable to ADRs per PRIME-1/PRIME-2
